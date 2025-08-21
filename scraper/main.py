from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
import json
import os
import sys
import traceback
import logging
from time import sleep
from database import init_database, get_db_session
from data_parser import DataParser
from models import Subject, Offering, Program
import re
import time


load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def _str_to_bool(x: str) -> bool:
    return str(x).strip().lower() in ("1", "true", "t", "yes", "y")


class Scraper:
    """Base scraper class with common web scraping functionality."""
    
    def __init__(self, browser: str = "firefox", debug: bool = False):
        self.browser = browser.strip().lower()
        self.debug = debug
        self.driver = None
        self.wait = None
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _get_options(self, browser: str):
        """Get browser-specific options."""
        if browser == "chrome":
            options = ChromeOptions()
            if not self.debug:
                options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            return options
        # default firefox
        options = FirefoxOptions()
        if not self.debug:
            options.add_argument("--headless")
        return options
    
    def build_driver(self) -> webdriver.Remote:
        """Build and return the appropriate web driver."""
        if self.browser == "chrome":
            return webdriver.Chrome(options=self._get_options("chrome"))
        # default to firefox for unknown values
        return webdriver.Firefox(options=self._get_options("firefox"))
    
    def start_driver(self):
        """Initialize the web driver and wait object."""
        self.driver = self.build_driver()
        self.wait = WebDriverWait(self.driver, 60)
        self.logger.info(f"Started {self.browser} driver")
    
    def stop_driver(self):
        """Close the web driver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.logger.info("Driver stopped")
    
    def scroll_to_bottom(self):
        """Scroll to the bottom of the page."""
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    
    def hover_by_text(self, text: str):
        """Hover over an element by its text."""
        el = self.wait.until(
            EC.presence_of_element_located((By.LINK_TEXT, text))
        )
        ActionChains(self.driver).move_to_element(el).perform()
    
    def run(self):
        """Main method to run the scraper. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement the run method")


class Bedelias(Scraper):
    """Bedelías scraper for extracting academic data."""
    
    def __init__(self, username: str, password: str, browser: str = "firefox", debug: bool = False):
        super().__init__(browser, debug)
        self.username = username
        self.password = password
        self.login_url = "https://bedelias.udelar.edu.uy/views/private/desktop/evaluarPrevias/evaluarPrevias02.xhtml?cid=2"
        self.data_parser = DataParser()
        self.total_pages = 0
        
        # Map JSF nodetype to a readable group type
        self.NODETYPE_MAP = {
            "y": "ALL",       # debe tener todas
            "o": "ANY",       # debe tener alguna
            "no": "NONE",     # no debe tener
            "default": "LEAF" # leaf node (a concrete requirement)
        }
        
        # Regex patterns for parsing
        self.APPROVAL_RE = re.compile(r"(\d+)\s+aprobaci[oó]n(?:/|)es?\s+entre:?", re.IGNORECASE)
        self.CREDITS_RE = re.compile(r"(\d+)\s+cr[eé]ditos?\s+en\s+el\s+Plan:?\s*(.*)", re.IGNORECASE)
        self.ITEM_PREFIX_RE = re.compile(
            r"^(?:(Examen|Curso)\s+de\s+la\s+U\.C\.B|U\.C\.B\s+aprobada)\s*:\s*(.+)$",
            re.IGNORECASE
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
                    row_data[f"Column {idx + 1}"] = [self.extract_table_info(nt) for nt in nested_tables]
                else:
                    txt = cell.text.strip()
                    if txt:
                        row_data[f"Column {idx + 1}"] = txt
            if row_data:
                table_data.append(row_data)
        return table_data
    
    def get_total_pages(self) -> int:
        """Get the total number of pages in the paginator."""
        self.scroll_to_bottom()
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@class,'ui-paginator-last')]"))).click()
        active_anchor_xpath = "//a[contains(@class,'ui-paginator-page') and contains(@class,'ui-state-active')]"
        active = self.wait.until(EC.presence_of_element_located((By.XPATH, active_anchor_xpath)))
        total = int(active.text.strip())
        self.logger.info(f"Total pages: {total}")
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@class='ui-paginator-first ui-state-default ui-corner-all']"))).click()
        self.total_pages = total
        return total
    # ----------------------------
# High-level API you’ll call
# ----------------------------
    def extract_requirements(self, root_id="arbol"):
        """
        Scrape the PrimeFaces horizontal tree (#arbol) into a nested JSON-able dict.
        - driver: Selenium WebDriver, already on the page with the HTML.
        - root_id: id of the tree root container (defaults to 'arbol').
        - expand: click all togglers first so content is present in DOM.
        """
    

    
        # find the root treenode (data-rowkey="root")
        root_node_td = self.driver.find_element(By.CSS_SELECTOR, 'td.ui-treenode[data-rowkey="root"]')
        return self._parse_node(root_node_td)
    
    # ----------------------------
    # Implementation details
    # ----------------------------
    
    def _expand_all(self, root_elem):
        """
        Repeatedly click all '+' togglers until none remain.
        Works even if tree loads collapsed or partially expanded.
        """
        # primefaces uses 'ui-icon-plus' when collapsed, 'ui-icon-minus' when expanded
        for _ in range(10):  # safety loop to avoid infinite clicking
            pluses = root_elem.find_elements(By.CSS_SELECTOR, ".ui-tree-toggler.ui-icon.ui-icon-plus")
            if not pluses:
                break
            for p in pluses:
                try:
                    self.driver.execute_script("arguments[0].click();", p)
                    time.sleep(0.05)
                except Exception:
                    pass
                
    def _parse_node(self, td_node):
        nodetype = td_node.get_attribute("data-nodetype") or "default"
        label_text = self._get_label_text(td_node).strip()
        kind = self.NODETYPE_MAP.get(nodetype, "LEAF")
    
        if "ui-treenode-leaf" in td_node.get_attribute("class"):
            # Parse a concrete requirement leaf
            return {
                "type": "LEAF",
                "label": label_text,
                **self._parse_leaf_payload(td_node)
            }
    
        # Otherwise: parent group node
        children = []
        for child_td in self._direct_children_of(td_node):
            children.append(self._parse_node(child_td))
    
        return {
            "type": kind,
            "label": label_text,
            "children": children
        }
    
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
                By.XPATH, 'following-sibling::td[contains(@class,"ui-treenode-children-container")]'
            )
        except Exception:
            return []
    
        return container.find_elements(
            By.CSS_SELECTOR, 'div.ui-treenode-children > table > tbody > tr > td.ui-treenode'
        )
    
    # ---------- Leaf parsing ----------
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
                "raw": raw
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
                "raw": raw
            }
    
        # Fallback: just return the text
        return {"rule": "raw_text", "value": raw}
    
    
    
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
                "kind": prefix.lower(),   # "examen", "curso", or "u.c.b aprobada"
                "code": code or None,
                "name": name or None,
                "raw": line
            }
    
        # If it doesn't match known prefixes, still try to split "CODE - NAME"
        parts = [p.strip() for p in line.split(" - ")]
        if len(parts) >= 2:
            return {"code": " - ".join(parts[:-1]), "name": parts[-1], "raw": line}
    
        return {"raw": line}
    def login_and_navigate(self):
        """Login to Bedelías and navigate to the main interface."""
        self.logger.info("Starting login process...")
        self.driver.get(self.login_url)
        
        username_field = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
        username_field.send_keys(self.username)
        
        password_field = self.driver.find_element(By.ID, "password")
        password_field.send_keys(self.password)
        
        self.wait.until(EC.element_to_be_clickable((By.NAME, "_eventId_proceed"))).click()
        sleep(0.5)
       

                # Wait for a known menu link to indicate post-login
        self.wait.until(
            EC.presence_of_element_located(
                (By.LINK_TEXT, "PLANES DE ESTUDIO")
            )
        )
        self.logger.info("Login successful")
    
    def get_previas(self):
        """Extract prerequisite (previas) data and store in database."""
        self.logger.info("Starting to extract previas (prerequisites) data...")
        
        self.hover_by_text("PLANES DE ESTUDIO")
        link = self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Planes de estudio / Previas")))
        link.click()
        sleep(0.5)

        # Expand and open info
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@class='ui-row-toggler ui-icon ui-icon-circle-triangle-e']"))).click()
        sleep(1)
        self.logger.info("Clicking info circle")
        self.wait.until(EC.element_to_be_clickable((By.XPATH, '//i[@class="pi  pi-info-circle"]'))).click()
        sleep(1)
        self.logger.info("Clicking sistema de previaturas")
        self.wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="Sistema de previaturas"]'))).click()
        sleep(0.3)

        self.logger.info("Getting total pages...")
        # Ensure paginator is in known state and get total pages
        self.get_total_pages()

        data = {}
        
        # Extract previas data
        for current_page in range(1, self.total_pages + 1):

            self.logger.info(f"Processing previas page {current_page}/{self.total_pages}")
            sleep(0.1)
            rows_len = len(self.driver.find_elements(By.XPATH, '//tr[@class="ui-widget-content ui-datatable-even"]'))
            for i in range(rows_len):
                try:
                    row = self.driver.find_elements(By.XPATH, '//tr[contains(@class, "ui-widget-content")]')[i]
                    
                    sleep(3)
                    # Extract row data for processing table data
                    cells = row.find_elements(By.TAG_NAME, "td")
                    self.logger.info(f"Cells length: {len(cells)}")
                    if len(cells) >= 3:
                        subject_info = {
                            'code': cells[0].text.strip() if cells[0].text else '',
                            'name': cells[1].text.strip() if cells[1].text else '',
                            'prerequisites': []  # Will be populated with detailed data
                        }
                        self.logger.info(f"Subject info: {subject_info}")
                        sleep(3)
                        
                        # Click for details if available
                        detail_links = cells[2].find_elements(By.TAG_NAME, "a")
                        
                        if detail_links:
                            detail_links[0].click()
                            sleep(0.2)
                            sleep(3)

                            # Extract prerequisite details from the expanded view
                            # This would need to be implemented based on the actual page structure
                            # For now, we'll store the basic info
                            
                            if subject_info['code']:
                                data[subject_info['code']] = subject_info
                            
                            # Close detail view if needed
                            # (Implementation depends on UI behavior)

                        self.logger.info("Clicking +")
                        plus_elements = self.driver.find_elements(By.XPATH, '//span[@class="ui-tree-toggler ui-icon ui-icon-plus"]')
                        if plus_elements:
                            for i in range(len(plus_elements)):
                                self.wait.until(EC.element_to_be_clickable((By.XPATH, f'//span[@class="ui-tree-toggler ui-icon ui-icon-plus"][{i+1}]'))).click()
                                sleep(0.1)
                        else:
                            self.logger.info("No + found")
                        
                            
                            
                            
                except Exception as e:
                    self.logger.warning(f"Error processing previas row {i}: {e}")
                    continue
        
        # Store in database
        requirements_count = self.data_parser.store_previas_data(data)
        
        self.logger.info(f"Successfully stored {requirements_count} prerequisite requirements to database")
        
        # Also save to JSON as backup
        backup_file = "previas_data_backup.json"
        with open(backup_file, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
        self.logger.info(f"Backup saved to {backup_file}")
    
    def run(self):
        """Main method to run the Bedelías scraper."""
        try:
            self.logger.info("Starting Bedelía scraper with ORM database integration...")
            
            # Initialize database
            self.logger.info("Initializing database connection...")
            #init_database()
            self.logger.info("Database initialized successfully")
            
            # Start driver
            self.start_driver()
            
            # Login and navigate
            self.login_and_navigate()
            
            # Extract previas (prerequisites) data
            self.get_previas()

            
            self.logger.info("Scraping completed successfully!")
            
        except Exception as e:
            self.logger.error(f"Scraping error: {e}")
            traceback.print_exc()
        finally:
            self.logger.info("Cleaning up and closing browser...")
            self.stop_driver()


def main():
    # Get configuration from environment
    username = os.getenv("DOCUMENTO", "")
    password = os.getenv("CONTRASENA", "")
    browser = os.getenv("BROWSER", "firefox").strip().lower()
    debug = _str_to_bool(os.getenv("DEBUG", "False"))
    
    if not username or not password:
        logger.error("USERNAME or PASSWORD not set in environment.")
        sys.exit(1)
    
    # Create and run the Bedelías scraper
    scraper = Bedelias(username=username, password=password, browser=browser, debug=debug)
    scraper.run()


if __name__ == "__main__":
    main()