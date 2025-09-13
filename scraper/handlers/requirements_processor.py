"""
Requirements processing handler for Bedelías website.
Handles parsing of the requirements tree structure and data extraction.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
import re
import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from time import sleep

from ..config import BedeliasConfig, RegexPatterns, NodeTypeMap
from ..models import RequirementNode

if TYPE_CHECKING:
    from ..core.base_scraper import BaseScraper


class RequirementsProcessor:
    """Handles requirements tree parsing and processing."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Compile regex patterns for better performance
        self.approval_re = re.compile(RegexPatterns.APPROVAL_PATTERN, re.IGNORECASE)
        self.credits_re = re.compile(RegexPatterns.CREDITS_PATTERN, re.IGNORECASE)
        self.item_prefix_re = re.compile(RegexPatterns.ITEM_PREFIX_PATTERN, re.IGNORECASE)

    # ========================================
    # TREE EXPANSION AND NAVIGATION
    # ========================================

    def expand_all_requirements(self, scraper):
        """Expand all collapsible nodes in the requirements tree."""
        self.logger.info("Expanding all requirements...")
        
        # Find all expandable elements (plus icons)
        plus_elements = scraper.driver.find_elements(
            By.XPATH, BedeliasConfig.TREE_PLUS_ICON_XPATH
        )
        
        if not plus_elements:
            self.logger.info("No expandable elements found - tree may already be fully expanded")
            return
        
        # Wait for all plus elements to be visible and click them
        visible_plus_elements = scraper.wait_for_all_elements_to_be_visible(
            (By.XPATH, BedeliasConfig.TREE_PLUS_ICON_XPATH)
        )
        
        for plus_element in visible_plus_elements:
            try:
                scraper.scroll_to_element_and_click(plus_element)
                sleep(0.1)  # Brief pause between clicks
            except Exception as e:
                self.logger.warning(f"Could not click expand element: {e}")
                continue
        
        self.logger.info("Requirements expansion completed")

    # ========================================
    # MAIN TREE EXTRACTION
    # ========================================

    def extract_requirements(self, scraper, root_id: str = None) -> RequirementNode:
        """
        Extract the requirements tree structure into a RequirementNode.
        
        Args:
            root_id: ID of the tree root container (defaults to 'arbol')
            
        Returns:
            Root RequirementNode with complete tree structure
        """
        if root_id is None:
            root_id = BedeliasConfig.TREE_ROOT_ID
            
        self.logger.info(f"Extracting requirements from tree root: {root_id}")
        
        # Find the root tree node
        root_node_td = scraper.driver.find_element(
            By.CSS_SELECTOR, BedeliasConfig.TREE_ROOT_SELECTOR
        )
        
        return self._parse_node(root_node_td)

    # ========================================
    # NODE PARSING IMPLEMENTATION
    # ========================================

    def _parse_node(self, td_node: WebElement) -> RequirementNode:
        """
        Parse a tree node element into a RequirementNode.
        
        Args:
            td_node: WebElement representing the tree node
            
        Returns:
            Parsed RequirementNode
        """
        nodetype = td_node.get_attribute("data-nodetype") or "default"
        label_text = self._get_label_text(td_node).strip()
        kind = NodeTypeMap.MAPPING.get(nodetype, "LEAF")
        
        # Check if this is a leaf node
        if "ui-treenode-leaf" in td_node.get_attribute("class"):
            return self._parse_leaf_node(td_node, label_text)
        
        # Parse parent node with children
        children = []
        for child_td in self._get_direct_children(td_node):
            children.append(self._parse_node(child_td))
        
        return RequirementNode(
            type=kind,
            label=label_text,
            children=children
        )

    def _parse_leaf_node(self, td_node: WebElement, label_text: str) -> RequirementNode:
        """Parse a leaf node with specific requirements."""
        leaf_data = self._parse_leaf_payload(label_text)
        
        return RequirementNode(
            type="LEAF",
            label=label_text,
            rule=leaf_data.get("rule"),
            required_count=leaf_data.get("required_count"),
            credits=leaf_data.get("credits"),
            plan=leaf_data.get("plan"),
            items=leaf_data.get("items", []),
            value=leaf_data.get("value"),
            raw=leaf_data.get("raw")
        )

    def _get_label_text(self, td_node: WebElement) -> str:
        """
        Extract the label text from a tree node.
        
        Args:
            td_node: Tree node element
            
        Returns:
            Cleaned label text
        """
        try:
            label_el = td_node.find_element(By.CSS_SELECTOR, BedeliasConfig.TREE_LABEL_SELECTOR)
            # Use innerText to preserve line breaks
            txt = label_el.get_attribute("innerText") or label_el.text
            
            # Normalize whitespace
            lines = [line.strip() for line in txt.replace("\r", "\n").split("\n")]
            return "\n".join([line for line in lines if line])
        except Exception:
            return ""

    def _get_direct_children(self, parent_td: WebElement) -> List[WebElement]:
        """
        Get direct child nodes of a parent tree node.
        
        Args:
            parent_td: Parent tree node element
            
        Returns:
            List of direct child elements
        """
        try:
            container = parent_td.find_element(
                By.XPATH, BedeliasConfig.TREE_CHILDREN_CONTAINER_XPATH
            )
        except Exception:
            return []
        
        return container.find_elements(By.CSS_SELECTOR, BedeliasConfig.TREE_CHILDREN_SELECTOR)

    # ========================================
    # LEAF NODE DATA PARSING
    # ========================================

    def _parse_leaf_payload(self, raw_text: str) -> Dict[str, Any]:
        """
        Parse leaf node text into structured data.
        
        Args:
            raw_text: Raw text from the leaf node
            
        Returns:
            Dictionary with parsed rule data
        """
        # Split by lines, preserving order
        lines = [line for line in raw_text.split("\n") if line.strip()]
        if not lines:
            return {"rule": "raw_text", "value": raw_text}
        
        first_line = lines[0]
        
        # Check for approval pattern: "N aprobación/es entre:"
        approval_match = self.approval_re.search(first_line)
        if approval_match:
            required = int(approval_match.group(1))
            items = [self._parse_item_line(line) for line in lines[1:]]
            items = [item for item in items if item]  # Remove None values
            
            return {
                "rule": "min_approvals",
                "required_count": required,
                "items": items,
                "raw": raw_text,
            }
        
        # Check for credits pattern: "N créditos en el Plan: <plan>"
        credits_match = self.credits_re.search(first_line)
        if credits_match:
            credits = int(credits_match.group(1))
            plan_inline = (credits_match.group(2) or "").strip()
            plan_tail = " ".join(lines[1:]).strip()
            plan = plan_inline if plan_inline else plan_tail
            
            return {
                "rule": "credits_in_plan",
                "credits": credits,
                "plan": plan or None,
                "raw": raw_text,
            }
        
        # Fallback: return as raw text
        return {"rule": "raw_text", "value": raw_text}

    def _parse_item_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse individual requirement item lines.
        
        Args:
            line: Single line from requirements list
            
        Returns:
            Parsed item data or None if parsing fails
        """
        line = line.strip()
        
        # Check for UCB pattern
        ucb_match = self.item_prefix_re.match(line)
        if ucb_match:
            prefix = ucb_match.group(1) or "U.C.B aprobada"
            payload = ucb_match.group(2).strip()
            
            # Split "CODE - NAME" allowing multiple " - " in CODE
            parts = [part.strip() for part in payload.split(" - ")]
            if len(parts) >= 2:
                code = " - ".join(parts[:-1])
                name = parts[-1]
            else:
                code, name = payload, None
            
            return {
                "source": "UCB",
                "kind": prefix.lower(),
                "code": code or None,
                "name": name or None,
                "raw": line,
            }
        
        # Fallback: try to split CODE - NAME
        parts = [part.strip() for part in line.split(" - ")]
        if len(parts) >= 2:
            return {
                "code": " - ".join(parts[:-1]),
                "name": parts[-1],
                "raw": line
            }
        
        return {"raw": line}
