"""
Base scraper class with universal web scraping functionality.
This class contains reusable methods that can work with any website.
"""

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
import logging
from time import sleep
from typing import Optional, Tuple, List
from selenium.webdriver.remote.webelement import WebElement


class BaseScraper:
    """Base scraper class with common web scraping functionality."""

    def __init__(self, browser: str = "firefox", debug: bool = False):
        """
        Initialize the base scraper.
        
        Args:
            browser: Browser type ('chrome' or 'firefox')
            debug: Whether to run in debug mode (with browser visible)
        """
        self.browser = browser.strip().lower()
        self.debug = debug
        self.driver: Optional[webdriver.Remote] = None
        self.wait: Optional[WebDriverWait] = None
        self.logger = logging.getLogger(self.__class__.__name__)

    # ========================================
    # BROWSER MANAGEMENT (Universal)
    # ========================================

    def _get_options(self, browser: str):
        """Get browser-specific options."""
        if browser == "chrome":
            options = ChromeOptions()
            if not self.debug:
                options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")
            return options
        
        # Default to Firefox
        options = FirefoxOptions()
        if not self.debug:
            options.add_argument("--headless")
        options.add_argument("--width=1920")
        options.add_argument("--height=1080")
        return options

    def build_driver(self) -> webdriver.Remote:
        """Build and return the appropriate web driver."""
        if self.browser == "chrome":
            return webdriver.Chrome(options=self._get_options("chrome"))
        # Default to firefox for unknown values
        return webdriver.Firefox(options=self._get_options("firefox"))

    def start_driver(self):
        """Initialize the web driver and wait object."""
        self.driver = self.build_driver()
        self.wait = WebDriverWait(self.driver, 10)
        self.logger.info(f"Started {self.browser} driver")

    def stop_driver(self):
        """Close the web driver."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.warning(f"Error closing driver: {e}")
            finally:
                self.driver = None
                self.logger.info("Driver stopped")

    # ========================================
    # ELEMENT INTERACTION (Universal)
    # ========================================

    def scroll_to_bottom(self):
        """Scroll to the bottom of the page."""
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def scroll_to_element(self, element: WebElement):
        """Scroll to a specific element."""
        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth'});", element)

    def scroll_to_element_and_click(self, element: WebElement):
        """Scroll to an element and click it."""
        self.scroll_to_element(element)
        sleep(0.2)  # Brief pause for smooth scrolling
        element.click()

    def hover_by_text(self, text: str):
        """Hover over an element by its text content."""
        element = self.wait_for_element((By.LINK_TEXT, text))
        ActionChains(self.driver).move_to_element(element).perform()

    # ========================================
    # ELEMENT WAITING (Universal)
    # ========================================

    def wait_for_element(self, locator: Tuple[By, str]) -> WebElement:
        """Wait for an element to be present in the DOM."""
        return self.wait.until(EC.presence_of_element_located(locator))

    def wait_for_element_to_be_clickable(self, locator: Tuple[By, str]) -> WebElement:
        """Wait for an element to be clickable."""
        return self.wait.until(EC.element_to_be_clickable(locator))

    def wait_for_element_to_be_visible(self, locator: Tuple[By, str]) -> WebElement:
        """Wait for an element to be visible."""
        return self.wait.until(EC.visibility_of_element_located(locator))

    def wait_for_all_elements_to_be_visible(self, locator: Tuple[By, str]) -> List[WebElement]:
        """Wait for all elements matching locator to be visible."""
        return self.wait.until(EC.visibility_of_all_elements_located(locator))

    def wait_for_element_to_be_present(self, locator: Tuple[By, str]) -> WebElement:
        """Wait for an element to be present in the DOM."""
        return self.wait.until(EC.presence_of_element_located(locator))

    def wait_for_page_to_load(self):
        """Wait for the page to finish loading."""
        self.wait.until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

    # ========================================
    # GENERIC DATA EXTRACTION (Universal)
    # ========================================

    def extract_table_info(self, table_element: WebElement) -> List[dict]:
        """
        Extract information from a table (and nested tables) into a list of row dicts.
        This is a generic table parser that works with most HTML tables.
        """
        table_data = []
        rows = table_element.find_elements(By.CSS_SELECTOR, "tbody tr")
        
        for row in rows:
            row_data = {}
            cells = row.find_elements(By.CSS_SELECTOR, "td")
            
            for idx, cell in enumerate(cells):
                # Check for nested tables
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

    # ========================================
    # ABSTRACT METHODS
    # ========================================

    def run(self):
        """Main method to run the scraper. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement the run method")
