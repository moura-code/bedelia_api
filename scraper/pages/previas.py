import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from time import sleep
import json
import re
from typing import List, Dict, Any, Optional
from scraper import Scraper
from common.navigation import PlanSection

# Non-breaking space constant
NBSP = "\u00a0"


class Previas(Scraper, PlanSection):

    def __init__(self, driver, wait, browser: str = "firefox", debug: bool = False, home_url: str = None):
        Scraper.__init__(self, driver, wait, browser, debug)
        self.home_url = home_url
 
        url = f"{home_url}views/public/desktop/consultaOfertaAcademica/consultaOfertaAcademica01.xhtml?cid=6"
        PlanSection.__init__(self, url)
                # Map JSF nodetype to a readable group type
        self.NODETYPE_MAP = {
            "default": "LEAF",
            "and": "ALL",
            "or": "ANY",
            "not": "NOT"
        }
        # Regex for required approvals
        self.RE_REQUIRED = re.compile(r"(?i)(\d+)\s+aprobaci[oó]n(?:/es)?\s+entre\s*:\s*$")

    def norm_spaces(self, s: str) -> str:
        """Normalize spaces and line breaks in text."""
        if s is None:
            return ""
        # Replace NBSP with normal spaces, trim, and collapse spaces
        s = s.replace(NBSP, " ")
        # Keep line breaks to separate items, but clean multiple spaces
        s = re.sub(r"[ \t]+", " ", s)
        # Normalize CRLF
        s = s.replace("\r\n", "\n").replace("\r", "\n")
        # Strip per line
        lines = [ln.strip() for ln in s.split("\n")]
        # Remove empty lines
        lines = [ln for ln in lines if ln]
        return "\n".join(lines)

    def safe_text(self, el) -> str:
        """Safely extract text from an element."""
        try:
            return self.norm_spaces(el.text)
        except Exception:
            return ""

    def _split_code_name(self, body: str):
        """
        Split "CODE - NAME (possible notes)" into (code, name, notes[])
        - code: first sequence before ' - '
        - name: rest
        - notes: simple heuristic: final parentheses or suffixes like " (P. 74)" etc.
        """
        body = body.strip()
        code = None
        title = body
        notes: List[str] = []

        # Detect "CODE - NAME"
        m = re.match(r"^\s*([A-Za-z0-9]+)\s*-\s*(.+?)\s*$", body)
        if m:
            code = m.group(1).strip()
            title = m.group(2).strip()

        # Extract notes in parentheses at the end (e.g. "(P. 74)")
        m2 = re.search(r"\(([^)]{1,80})\)\s*$", title)
        if m2:
            notes.append(m2.group(1).strip())
            title = re.sub(r"\s*\([^)]*\)\s*$", "", title).strip()

        return code, title, notes

    def parse_item_line(self, line: str, prefix_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse a textual line (e.g. "Examen de la U.C.B: 1121 - FISICA GENERAL 2")
        into a structured dict.
        Recognizes: exam | course | ucb_module | course_enrollment | exam_enrollment | unknown
        """
        original = line.strip()
        norm = re.sub(r"\s+", " ", original).strip().lower()

        modality = "unknown"
        body = original

        # Order: most specific first
        # Enrollment in exam
        if re.search(r"^inscripci[oó]n\s+a?l?\s*examen\s+de\s+la\s+u\.?c\.?b\s*:\s*", norm):
            modality = "exam_enrollment"
            body = re.sub(r"(?i)^inscripci[oó]n\s+a?l?\s*examen\s+de\s+la\s+u\.?c\.?b\s*:\s*", "", original).strip()
        
        # Enrollment in course
        elif re.search(r"^inscripci[oó]n\s+a?l?\s*curso\s+de\s+la\s+u\.?c\.?b\s*:\s*", norm):
            modality = "course_enrollment"
            body = re.sub(r"(?i)^inscripci[oó]n\s+a?l?\s*curso\s+de\s+la\s+u\.?c\.?b\s*:\s*", "", original).strip()

        elif re.search(r"^examen\s+de\s+la\s+u\.?c\.?b\s*:\s*", norm):
            modality = "exam"
            body = re.sub(r"(?i)^examen\s+de\s+la\s+u\.?c\.?b\s*:\s*", "", original).strip()

        elif re.search(r"^curso\s+de\s+la\s+u\.?c\.?b\s*:\s*", norm):
            modality = "course"
            body = re.sub(r"(?i)^curso\s+de\s+la\s+u\.?c\.?b\s*:\s*", "", original).strip()

        elif re.search(r"^u\.?c\.?b\s+aprobad[ao]\s*:\s*", norm):
            modality = "ucb_module"
            body = re.sub(r"(?i)^u\.?c\.?b\s+aprobad[ao]\s*:\s*", "", original).strip()

        elif prefix_hint:
            # If the header has a prefix (e.g. "Curso aprobado de la U.C.B:"),
            # use it as a hint for modality and clean the body.
            hint = prefix_hint.strip()
            low_hint = hint.lower()
            if "inscripción" in low_hint and "examen" in low_hint:
                modality = "exam_enrollment"
            elif "inscripción" in low_hint and "curso" in low_hint:
                modality = "course_enrollment"
            elif "examen" in low_hint:
                modality = "exam"
            elif "curso" in low_hint and "aprob" not in low_hint:
                modality = "course"
            elif "u.c.b" in low_hint and "aprob" in low_hint:
                modality = "ucb_module"
            # Remove the hint if it comes attached to the line (some leaves have it in bold)
            body = re.sub(re.escape(hint), "", original, flags=re.I).strip(" :")

        code, title, notes = self._split_code_name(body)

        return {
            "source": "UCB",
            "modality": modality,  # exam | course | ucb_module | course_enrollment | exam_enrollment | unknown
            "code": code,
            "title": title,
            "notes": notes,
            "raw": original
        }

    def parse_leaf_json(self, label_text: str) -> Dict[str, Any]:
        """
        Convert the complete text of a LEAF into:
        {
          "type": "LEAF",
          "required_count": int,
          "items": [ { item_struct }, ... ],
          "title": "..."   # clean header
        }
        Cases:
          - "N aprobación/es entre:" + multiple lines ("Examen de la U.C.B: ...", "Curso de la U.C.B: ...", etc.)
          - "Examen aprobado de la U.C.B: 1026 - MATEMATICA DISCRETA 2" (single item => required_count=1)
          - "Curso aprobado de la U.C.B: 1144 - VIBRACIONES Y ONDAS"
          - "Inscripción a(l) Curso de la U.C.B: MI2 - MATEMATICA INICIAL"
          - "N créditos en el Plan: YEAR - PLAN_NAME" (e.g., "140 créditos en el Plan: 1997 - INGENIERIA EN COMPUTACION")
        """
        lines = self.norm_spaces(label_text).split("\n")
        if not lines:
            return {
                "type": "LEAF",
                "required_count": 1,
                "items": [],
                "title": label_text.strip()
            }

        first = lines[0].strip()

        # 1) Case "N aprobación/es entre:"
        m = self.RE_REQUIRED.search(first)
        if m:
            required_count = int(m.group(1))
            items: List[Dict[str, Any]] = []

            # Other lines are items (each starts with "Examen de la U.C.B: ..." etc.)
            for ln in lines[1:]:
                if not ln.strip():
                    continue
                items.append(self.parse_item_line(ln))

            return {
                "type": "LEAF",
                "required_count": required_count,
                "items": items,
                "title": first  # keep the header clean
            }

        # 2) Case "N créditos en el Plan: YEAR - PLAN_NAME"
        #    e.g., "140 créditos en el Plan: 1997 - INGENIERIA EN COMPUTACION"
        credits_pattern = r"^(\d+)\s+cr[eé]ditos?\s+en\s+el\s+[Pp]lan\s*:\s*(.+)$"
        m_credits = re.search(credits_pattern, first, re.IGNORECASE)
        if m_credits:
            credits_required = int(m_credits.group(1))
            plan_info = m_credits.group(2).strip()
            
            # Parse plan_info which should be "YEAR - PLAN_NAME"
            plan_year = ""
            plan_name = ""
            if " - " in plan_info:
                parts = plan_info.split(" - ", 1)
                plan_year = parts[0].strip()
                plan_name = parts[1].strip()
            else:
                plan_name = plan_info
            
            # Create an item representing the credit requirement
            item = {
                "source": "PLAN",
                "modality": "credits_in_plan",
                "credits_required": credits_required,
                "plan_year": plan_year,
                "plan_name": plan_name,
                "code": "",
                "title": plan_info,
                "raw": first
            }
            
            return {
                "type": "LEAF",
                "required_count": 1,
                "items": [item],
                "title": first
            }

        # 3) Cases "X aprobado de la U.C.B: CODE - NAME" (single one)
        #    or "Inscripción a Curso/Examen de la U.C.B: CODE - NAME"
        # Typical headers that come in <span class="negrita">...</span>
        APPROVED_PREFIXES = [
            r"(?i)^inscripci[oó]n\s+a?l?\s*examen\s+de\s+la\s+u\.?c\.?b\s*:\s*",
            r"(?i)^examen\s+aprobado\s+de\s+la\s+u\.?c\.?b\s*:\s*",
            r"(?i)^curso\s+aprobado\s+de\s+la\s+u\.?c\.?b\s*:\s*",
            r"(?i)^u\.?c\.?b\s+aprobada?\s*:\s*",
            r"(?i)^inscripci[oó]n\s+a?l?\s*curso\s+de\s+la\s+u\.?c\.?b\s*:\s*",
        ]

        # If it's a single line (header + item attached) or two lines,
        # build required_count=1 and a single item
        for rx in APPROVED_PREFIXES:
            if re.search(rx, first):
                # 2a) Title in first and the "CODE - NAME" attached at the end of first
                after = re.sub(rx, "", first, flags=re.I).strip()
                item_text = after if after else (lines[1].strip() if len(lines) > 1 else "")
                # Give a modality hint using the hint (first)
                item = self.parse_item_line(item_text, prefix_hint=first)
                return {
                    "type": "LEAF",
                    "required_count": 1,
                    "items": [item] if item_text else [],
                    "title": first if after else (first + " " + item_text).strip()
                }

            # 2b) There's a header in first and the item in the next line(s)
            if len(lines) > 1 and re.search(rx, lines[0]):
                item = self.parse_item_line(lines[1], prefix_hint=first)
                return {
                    "type": "LEAF",
                    "required_count": 1,
                    "items": [item],
                    "title": first
                }

        # 3) Fallback: treat all lines after the first as items with required_count=1
        items = []
        if len(lines) > 1:
            for ln in lines[1:]:
                items.append(self.parse_item_line(ln))
            return {
                "type": "LEAF",
                "required_count": 1,
                "items": items,
                "title": first
            }

        # 4) Last resort: a LEAF without clear items
        return {
            "type": "LEAF",
            "required_count": 1,
            "items": [],
            "title": first
        }

    def node_type_from_title(self, title: str) -> Optional[str]:
        """Determine node type from title text."""
        t = title.strip().lower()
        if "no debe tener" in t:
            return "NOT"
        if "debe tener todas" in t:
            return "ALL"
        if "debe tener alguna" in t:
            return "ANY"
        return None

    def find_label_text(self, td_node) -> str:
        """Return the label text of the node: span.ui-treenode-label"""
        try:
            label = td_node.find_element(By.CSS_SELECTOR, ".ui-treenode-label")
            return self.safe_text(label)
        except NoSuchElementException:
            return self.safe_text(td_node)

    def is_leaf(self, td_node) -> bool:
        """Check if a node is a leaf node."""
        cls = td_node.get_attribute("class") or ""
        return "ui-treenode-leaf" in cls

    def get_direct_child_tds(self, parent_td) -> List[Any]:
        """
        Return the DIRECT child TDs (not grandchildren) of the 'parent_td' node.
        In the HTML, children live in the sibling TD with class
        '.ui-treenode-children-container' -> div.ui-treenode-children -> (multiple) table > tbody > tr
          Each tr has:
            [td.connector] [td.ui-treenode (THE CHILD)] [td.children-container (if that child is a parent)]
        We select the td with @data-rowkey in each tr.
        """
        try:
            cont = parent_td.find_element(By.XPATH, './following-sibling::td[contains(@class,"ui-treenode-children-container")]')
        except NoSuchElementException:
            return []

        # Search for direct child tds at the first level of tables under .ui-treenode-children
        child_tds = cont.find_elements(
            By.XPATH,
            './div[contains(@class,"ui-treenode-children")]/table/tbody/tr/td[@data-rowkey]'
        )
        return child_tds

    def parse_node(self, td_node) -> Dict[str, Any]:
        """Recursively parse a tree node."""
        title = self.find_label_text(td_node)

        # If it's a LEAF, parse the leaf and return
        if self.is_leaf(td_node):
            leaf = self.parse_leaf_json(title)
            return leaf

        # If it's not a leaf, it's a parent: recognize logical type by title or default
        logic_type = self.node_type_from_title(title) or "GROUP"

        node: Dict[str, Any] = {
            "type": logic_type,
            "title": title,
            "children": []
        }

        # Collect direct children
        for child_td in self.get_direct_child_tds(td_node):
            node["children"].append(self.parse_node(child_td))

        return node

    def _validate_tree(self, node: Dict[str, Any], path: str = "root") -> None:
        """
        Validate the requirements tree structure.
        Raises exception if a non-leaf parent node has empty children.
        """
        node_type = node.get("type", "")
        
        # If this node has children key (parent node), validate it's not empty
        if "children" in node:
            children = node.get("children", [])
            if not children:
                raise ValueError(
                    f"Parent node at '{path}' has empty children array. "
                    f"Type: {node_type}, Title: {node.get('title', 'N/A')}"
                )
            
            # Recursively validate children
            for idx, child in enumerate(children):
                self._validate_tree(child, f"{path}/child[{idx}]")

    def extract_requirements(self, root_id: str = "arbol") -> Dict[str, Any]:
        """
        Extract the requirements tree from the page.
        From the driver (already on the page), find the tree by id=root_id
        and return the root JSON (ALL/ANY/NOT according to the root title).
        """
        # 1) locate the root td
        root_td = self.driver.find_element(
            By.CSS_SELECTOR,
            f'#{root_id} td[data-rowkey="root"]'
        )
        root = self.parse_node(root_td)

        # Root type adjustment: if not explicit in the label, convert "GROUP" to "ALL"
        if root.get("type") == "GROUP":
            root["type"] = "ALL"
        
        # Validate tree structure
        self._validate_tree(root)
        
        return root

    def expand_all_requirements(self):
        """Expand all tree nodes in the requirements tree."""
        
        # Wait for modal overlay to disappear
        self.wait.until(
            EC.invisibility_of_element_located((By.ID, "j_idt22_modal"))
        )

        plus_elements = self.driver.find_elements(
            By.XPATH, '//span[@class="ui-tree-toggler ui-icon ui-icon-plus"]'
        )

        if not plus_elements:
            return
        tries = 0
        while self.try_find_element(
            (By.XPATH, '//span[@class="ui-tree-toggler ui-icon ui-icon-plus"]'), 0.2
        ):  
            if tries >=50:
                self.driver.refresh()
            if tries >= 90:
                raise Exception("Failed to expand all requirements")
            tries += 1
            plus_elements = self.driver.find_elements(
                By.XPATH, '//span[@class="ui-tree-toggler ui-icon ui-icon-plus"]'
            )
            for plus_element in plus_elements:
                self.scroll_to_element_and_click(plus_element)

    def _load_backup_data(self, backup_file: str) -> dict:
        """Load existing backup data if available."""
        if os.path.exists(backup_file):
            try:
                with open(backup_file, "r", encoding="utf-8") as fp:
                    return json.load(fp)
            except json.JSONDecodeError:
                self.logger.warning(f"Backup file {backup_file} is corrupted, starting fresh")
                return {}
        return {}
    
    def _save_backup_data(self, backup_file: str, data: dict):
        """Save data to backup file."""
        with open(backup_file, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
        self.logger.info(f"Backup saved to {backup_file}")
    
    def _process_plan_with_retry(self, plan: str, year: str, max_retries: int = 3) -> dict:
        """
        Process a single plan with retry logic for Selenium errors.
        Returns the extracted data for this plan.
        """
        retry_count = 0
        last_exception = None
        
        while retry_count < max_retries:
            try:
                self.logger.info(f"Processing plan {plan} {year} (attempt {retry_count + 1}/{max_retries})")
                
                # Navigate to the plan section
                self.open_plan_section(
                    log_message=f"Starting to extract previas (prerequisites) data for {plan} {year}",
                    plan_name=plan,
                    plan_year=year,
                )
                self.logger.info("Clicking sistema de previaturas")

                self.wait_for_element_to_be_clickable((By.XPATH, '//span[text()="Sistema de previaturas"]')).click()
                sleep(1)

                # Check if plan has no previaturas
                if self.try_find_element((By.XPATH, '//span[text()="No se pueden mostrar los Sistemas de Previaturas del Plan"]')):
                    self.logger.info("No se pueden mostrar los Sistemas de Previaturas del Plan")
                    return {}

                self.logger.info("Getting total pages...")
                self.get_total_pages()
                sleep(1)
        
                data = {}
                current_page = 1
                
                # Extract previas data for all pages
                while current_page <= self.total_pages:
                    self.go_to_page(current_page)
                    self.logger.info(f"Processing previas page {current_page}/{self.total_pages}")
                            
                    rows_len = len(
                        self.driver.find_elements(
                            By.XPATH, '//tr[contains(@class, "ui-datatable-even") or contains(@class, "ui-datatable-odd")]'
                        )
                    )
                    
                    i = 0
                    
                    while i < rows_len:
                        self.go_to_page(current_page)
                                
                        # Re-find rows to avoid stale element references
                        rows = self.wait_for_all_elements_to_be_visible(
                            (
                                By.XPATH,
                                '//tr[contains(@class, "ui-datatable-even") or contains(@class, "ui-datatable-odd")]',
                            )
                        )
                        
                        row = rows[i]
                        
                        # Extract row data with retry
                        max_cell_retries = 5
                        cell_retry = 0
                        while cell_retry < max_cell_retries:
                            try:
                                cells = row.find_elements(By.TAG_NAME, "td")
                                if len(cells) < 3:
                                    raise Exception("Less than 3 cells found in row")
                    
                                # Extract text immediately before any other operations
                                code,name ,_= self._split_code_name(cells[0].text.strip() if cells[0].text else "")
                                
                                type_previas = cells[1].text.strip() if cells[1].text else ""

                                break
                            except Exception as cell_error:
                                cell_retry += 1
                                if cell_retry >= max_cell_retries:
                                    raise cell_error
                                row = rows[i]
                                sleep(0.1)
                        # Example "2231 - CAMINOS Y CALLES 1 - Examen"
                        subject_info = {
                            "code": code,
                            "name": name,
                            "type_previas": type_previas,
                            "full": f"{code}-{name}-{type_previas}",
                        }

                        # Re-find the row and link to avoid stale element
                        fresh_rows = self.driver.find_elements(
                            By.XPATH,
                            '//tr[contains(@class, "ui-datatable-even") or contains(@class, "ui-datatable-odd")]'
                        )
                        fresh_cells = fresh_rows[i].find_elements(By.TAG_NAME, "td")
                        ver_mas_link = fresh_cells[2].find_element(By.TAG_NAME, "a")
                        
                        # Click Ver Más
                        self.scroll_to_element_and_click(ver_mas_link)

                        # Wait for the table to be visible
                        self.wait_for_element_to_be_visible(
                            (
                                By.XPATH,
                                "/html/body/div[3]/div[7]/div/form/div[1]/div/div/table/tbody/tr/td[1]/div",
                            )
                        )

                        self.expand_all_requirements()
                        subject_info["requirements"] = self.extract_requirements()

                        data[subject_info["full"]] = subject_info
                        self.logger.info(f"Requirements extracted for {subject_info['code']}")
                        
                        # Wait for modal overlay to disappear before clicking Volver
                        self.wait.until(
                            EC.invisibility_of_element_located((By.ID, "j_idt22_modal"))
                        )
                        self.scroll_to_element_and_click(
                            self.driver.find_element(
                                By.XPATH, "//span[normalize-space(.)='Volver']"
                            )
                        )
                        i += 1
                
                    current_page += 1
                
                # Successfully processed the plan
                self.logger.info(f"Successfully processed plan {plan} {year}")
                return data
                    
            except Exception as e:
                last_exception = e
                retry_count += 1
                self.logger.error(f"Error processing plan {plan} {year} (attempt {retry_count}/{max_retries}): {e}")
                
                # Check if we returned to main page
                if self.try_find_element((By.XPATH, '//span[@class="tituloNoticia"]')):
                    self.logger.info("Returned to main page, will retry")
                
                if retry_count < max_retries:
                    self.logger.info(f"Retrying plan {plan} {year}...")
                    sleep(2)  # Wait before retrying
                else:
                    self.logger.error(f"Failed to process plan {plan} {year} after {max_retries} attempts")
                    raise last_exception
        
        raise last_exception
    
    def run(self):
        """Extract prerequisite (previas) data and store in database."""
        backup_file = "../data/previas_data_backup.json"
        
        # Load existing backup data
        all_plans_data = self._load_backup_data(backup_file)
        self.logger.info(f"Loaded {len(all_plans_data)} plans from backup")
        
        # Get all available plans
        plans_data = self.get_total_plan_sections()
        self.logger.info(f"Total plans available: {len(plans_data)}")
        
        # Process each plan
        for j in range(len(plans_data)):
            plan, year = plans_data[j]
            plan_key = f"{plan}_{year}"
            
            # Skip if already processed
            if plan_key in all_plans_data:
                self.logger.info(f"Skipping already processed plan: {plan_key}")
                continue
            
            try:
                # Process plan with retry logic
                plan_data = self._process_plan_with_retry(plan, year, max_retries=3)
                
                # Save data for this plan
                all_plans_data[plan_key] = plan_data
                
                # Save backup after each successful plan
                self._save_backup_data(backup_file, all_plans_data)
                self.logger.info(f"✓ Completed and saved plan {j+1}/{len(plans_data)}: {plan_key}")
                
            except Exception as e:
                self.logger.error(f"✗ Failed to process plan {plan_key} after all retries: {e}")
                # Continue with next plan instead of crashing
                continue
        
        self.logger.info(f"Previas extraction completed! Processed {len(all_plans_data)} plans total")
        self.logger.info(f"Final data saved to {backup_file}")
