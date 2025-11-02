import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
import json
import re
from scraper import Scraper
from common.navigation import PlanSection


class Previas(Scraper, PlanSection):

    def __init__(self, driver, wait, browser: str = "firefox", debug: bool = False, home_url: str = None, plan_name: str = "INGENIERÍA EN COMPUTACIÓN"):
        Scraper.__init__(self, driver, wait, browser, debug)
        self.home_url = home_url
 
        url = f"{home_url}views/public/desktop/consultaOfertaAcademica/consultaOfertaAcademica01.xhtml?cid=6"
        PlanSection.__init__(self, url, plan_name)
                # Map JSF nodetype to a readable group type
        self.NODETYPE_MAP = {
            "y": "ALL",  # debe tener todas
            "o": "ANY",  # debe tener alguna
            "no": "NONE",  # no debe tener
            "default": "LEAF",  # leaf node (a concrete requirement)
        }

        # Regex patterns for parsing
        self.APPROVAL_RE = re.compile(
            r"(\d+)\s+aprobaci[oó]n(?:/|)es?\s+entre:?", re.IGNORECASE
        )
        self.CREDITS_RE = re.compile(
            r"(\d+)\s+cr[eé]ditos?\s+en\s+el\s+Plan:?\s*(.*)", re.IGNORECASE
        )
        self.ITEM_PREFIX_RE = re.compile(
            r"^(?:(Examen|Curso)\s+de\s+la\s+U\.C\.B|U\.C\.B\s+aprobada)\s*:\s*(.+)$",
            re.IGNORECASE,
        )
    def extract_table_info(self, table_element):
        """Extract information from a table (and nested tables) into a list of row dicts."""
        table_data = []
        rows = table_element.find_elements(By.CSS_SELECTOR, "tbody tr")
        for row in rows:
            row_data = {}
            cells = row.find_elements(By.CSS_SELECTOR, "td")
            for idx, cell in enumerate(cells):
                nested_tables = cell.find_elements(By.CSS_SELECTOR, "table")
                if nested_tables:
                    row_data[f"Column {idx + 1}"] = [
                        self.extract_table_info(nt) for nt in nested_tables
                    ]
                else:
                    txt = cell.text.strip()
                    if txt:
                        row_data[f"Column {idx + 1}"] = txt
            if row_data:
                table_data.append(row_data)
        return table_data

    def _parse_item_line(self, line):
        """
        Convert lines like:
          - "U.C.B aprobada: 2241 - ADMINISTRACION DE EMPRESAS"
          - "Examen de la U.C.B: CP1 - ANALISIS MATEMATICO I"
          - "Curso de la U.C.B: 1321 - PROGRAMACION 2"
          - or anything else -> {"raw": line}
        into a uniform structure.
        """
        line = line.strip()
        m = self.ITEM_PREFIX_RE.match(line)
        if m:
            prefix = m.group(1) or "U.C.B aprobada"
            payload = m.group(2).strip()

            # Split "CODE - NAME" but allow multiple " - " parts in CODE (e.g., "CENURLN - SRN14 - NAME")
            parts = [p.strip() for p in payload.split(" - ")]
            if len(parts) >= 2:
                code = " - ".join(parts[:-1])
                name = parts[-1]
            else:
                code, name = payload, None

            return {
                "source": "UCB",
                "kind": prefix.lower(),  # "examen", "curso", or "u.c.b aprobada"
                "code": code or None,
                "name": name or None,
                "raw": line,
            }

        # If it doesn't match known prefixes, still try to split "CODE - NAME"
        parts = [p.strip() for p in line.split(" - ")]
        if len(parts) >= 2:
            return {"code": " - ".join(parts[:-1]), "name": parts[-1], "raw": line}

        return {"raw": line}

    def _parse_leaf_payload(self, td_leaf):
        """
        Return a dict describing the leaf rule:
          - approvals: {"rule":"min_approvals","required_count":N,"items":[...]}
          - credits:   {"rule":"credits_in_plan","credits":N,"plan": "..."}
          - fallback:  {"rule":"raw_text","value": "..."}
        """
        raw = self._get_label_text(td_leaf)
        # Split by lines, preserving order
        lines = [l for l in (raw.split("\n")) if l.strip()]
        if not lines:
            return {"rule": "raw_text", "value": raw}

        first = lines[0]

        # 1) "N aprobación/es entre:"
        m = self.APPROVAL_RE.search(first)
        if m:
            required = int(m.group(1))
            items = [self._parse_item_line(l) for l in lines[1:]]
            items = [i for i in items if i]  # drop None
            return {
                "rule": "min_approvals",
                "required_count": required,
                "items": items,
                "raw": raw,
            }

        # 2) "N créditos en el Plan: <plan>"
        m = self.CREDITS_RE.search(first)
        if m:
            credits = int(m.group(1))
            plan_inline = (m.group(2) or "").strip()
            plan_tail = " ".join(lines[1:]).strip()
            plan = plan_inline if plan_inline else plan_tail
            return {
                "rule": "credits_in_plan",
                "credits": credits,
                "plan": plan or None,
                "raw": raw,
            }

        # Fallback: just return the text
        return {"rule": "raw_text", "value": raw}
    def extract_requirements(self, root_id="arbol"):
        """
        Scrape the PrimeFaces horizontal tree (#arbol) into a nested JSON-able dict.
        - driver: Selenium WebDriver, already on the page with the HTML.
        - root_id: id of the tree root container (defaults to 'arbol').
        - expand: click all togglers first so content is present in DOM.
        """
        # find the root treenode (data-rowkey="root")
        root_node_td = self.driver.find_element(
            By.CSS_SELECTOR, 'td.ui-treenode[data-rowkey="root"]'
        )
        return self._parse_node(root_node_td)

    # ----------------------------
    # Implementation details
    # ----------------------------

    def expand_all_requirements(self):
        self.logger.info("Expanding all requirements")
        
        # Wait for modal overlay to disappear
        self.wait.until(
            EC.invisibility_of_element_located((By.ID, "j_idt22_modal"))
        )

        plus_elements = self.driver.find_elements(
            By.XPATH, '//span[@class="ui-tree-toggler ui-icon ui-icon-plus"]'
        )

        if not plus_elements:
            self.logger.info(
                "No expandable elements found - tree may already be fully expanded"
            )
            return

        visible_plus_elements = self.wait_for_all_elements_to_be_visible(
            (By.XPATH, '//span[@class="ui-tree-toggler ui-icon ui-icon-plus"]')
        )
        
        for plus_element in visible_plus_elements:
            # Wait for modal to disappear before each click
            self.wait.until(
                EC.invisibility_of_element_located((By.ID, "j_idt22_modal"))
            )
            sleep(0.1)
            self.scroll_to_element_and_click(plus_element)

    def _parse_node(self, td_node):
        nodetype = td_node.get_attribute("data-nodetype") or "default"
        label_text = self._get_label_text(td_node).strip()
        kind = self.NODETYPE_MAP.get(nodetype, "LEAF")

        if "ui-treenode-leaf" in td_node.get_attribute("class"):
            # Parse a concrete requirement leaf
            return {
                "type": "LEAF",
                "label": label_text,
                **self._parse_leaf_payload(td_node),
            }

        # Otherwise: parent group node
        children = []
        for child_td in self._direct_children_of(td_node):
            children.append(self._parse_node(child_td))

        return {"type": kind, "label": label_text, "children": children}

    def _get_label_text(self, td_node):
        # The visible text sits in span.ui-treenode-label
        try:
            label_el = td_node.find_element(By.CSS_SELECTOR, ".ui-treenode-label")
            # innerText preserves line breaks; textContent is similar. Prefer innerText.
            txt = label_el.get_attribute("innerText") or label_el.text
            # Normalize whitespace
            lines = [l.strip() for l in txt.replace("\r", "\n").split("\n")]
            return "\n".join([l for l in lines if l])
        except Exception:
            return ""

    def _direct_children_of(self, parent_td):
        """
        Given a <td.ui-treenode> that is a PARENT, return only its direct child <td.ui-treenode> elements.
        PrimeFaces horizontal tree places children in the next-sibling
        <td class="ui-treenode-children-container"> ... <div class="ui-treenode-children"> with nested tables.
        """
        try:
            container = parent_td.find_element(
                By.XPATH,
                'following-sibling::td[contains(@class,"ui-treenode-children-container")]',
            )
        except Exception:
            return []

        return container.find_elements(
            By.CSS_SELECTOR,
            "div.ui-treenode-children > table > tbody > tr > td.ui-treenode",
        )

   
    def run(self):
        """Extract prerequisite (previas) data and store in database."""
        self.open_plan_section(
            log_message="Starting to extract previas (prerequisites) data...",
        )
        self.logger.info("Clicking sistema de previaturas")

        self.wait_for_element_to_be_clickable((By.XPATH, '//span[text()="Sistema de previaturas"]')).click()
        # TODO remover
        sleep(2)

        self.logger.info("Getting total pages...")
        # Ensure paginator is in known state and get total pages
        self.get_total_pages()
        # TODO remover
        sleep(2)
        
        data = {}
        # Extract previas data
        for current_page in range(1, self.total_pages + 1):
            self.go_to_page(current_page)
            self.logger.info(
                f"Processing previas page {current_page}/{self.total_pages}"
            )
            rows_len = len(
                self.driver.find_elements(
                    By.XPATH, '//tr[contains(@class, "ui-datatable-even") or contains(@class, "ui-datatable-odd")]'
                )
            )
            
            self.logger.info(f"Rows length: {rows_len}")
            for i in range(rows_len):
                self.go_to_page(current_page)
                
                # Re-find rows to avoid stale element references
                rows = self.wait_for_all_elements_to_be_visible(
                    (
                        By.XPATH,
                        '//tr[contains(@class, "ui-datatable-even") or contains(@class, "ui-datatable-odd")]',
                    )
                )
                
                row = rows[i]
                
                # Extract row data immediately to avoid stale elements
                cells = row.find_elements(By.TAG_NAME, "td")

                if len(cells) < 3:
                    raise Exception("Less than 3 cells found in row")

                # Extract text immediately before any other operations
                code = cells[0].text.strip() if cells[0].text else ""
                name = cells[1].text.strip() if cells[1].text else ""
                
                subject_info = {
                    "code": code,
                    "name": name,
                }
                self.logger.info(f"Subject info: {subject_info}")

                # Wait for modal to disappear before clicking Ver Más
                self.wait.until(
                    EC.invisibility_of_element_located((By.ID, "j_idt22_modal"))
                )
                
                # Re-find the row and link to avoid stale element
                fresh_rows = self.driver.find_elements(
                    By.XPATH,
                    '//tr[contains(@class, "ui-datatable-even") or contains(@class, "ui-datatable-odd")]'
                )
                fresh_cells = fresh_rows[i].find_elements(By.TAG_NAME, "td")
                ver_mas_link = fresh_cells[2].find_element(By.TAG_NAME, "a")
                
                # Click in Ver Más
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

                data[subject_info["code"]] = subject_info
                self.logger.info(
                    f"Requriments extracted for {subject_info['code']}"
                )
                
                # Wait for modal overlay to disappear before clicking Volver
                self.wait.until(
                    EC.invisibility_of_element_located((By.ID, "j_idt22_modal"))
                )
                self.scroll_to_element_and_click(
                    self.driver.find_element(
                        By.XPATH, "//span[normalize-space(.)='Volver']"
                    )
                )

        # save to JSON as backup
        backup_file = "previas_data_backup.json"
        with open(backup_file, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
        self.logger.info(f"Backup saved to {backup_file}")