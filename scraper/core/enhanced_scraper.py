"""
Enhanced base scraper with context manager support and improved architecture.
"""

import logging
from contextlib import contextmanager
from typing import Optional, Tuple, List, Any, Union
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from time import sleep

from .interfaces import ScraperProtocol, WebDriverProtocol, WaitProtocol
from .browser_factory import BrowserFactory
from .exceptions import (
    DriverNotStartedError, ElementNotFoundError, PageLoadError,
    BrowserError, ScraperError
)


class EnhancedScraper:
    """
    Enhanced base scraper with context manager support and improved architecture.
    This replaces the old BaseScraper with better patterns and error handling.
    """
    
    def __init__(
        self, 
        browser: str = "firefox", 
        debug: bool = False,
        wait_timeout: int = 10,
        **browser_options
    ):
        """
        Initialize the enhanced scraper.
        
        Args:
            browser: Browser type ('firefox', 'chrome', 'edge')
            debug: Whether to run in debug mode
            wait_timeout: Default timeout for wait operations
            **browser_options: Additional browser-specific options
        """
        self.browser = browser.strip().lower()
        self.debug = debug
        self.wait_timeout = wait_timeout
        self.browser_options = browser_options
        
        # Core components
        self.driver: Optional[WebDriverProtocol] = None
        self.wait: Optional[WaitProtocol] = None
        self.browser_factory = BrowserFactory()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # State tracking
        self._driver_started = False
    
    # ========================================
    # CONTEXT MANAGER SUPPORT
    # ========================================
    
    def __enter__(self):
        """Enter context manager and start driver."""
        self.start_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and stop driver."""
        self.stop_driver()
        if exc_type:
            self.logger.error(f"Exception in scraper context: {exc_val}")
        return False
    
    @contextmanager
    def driver_session(self):
        """Context manager for temporary driver session."""
        if self._driver_started:
            # Already have a driver, just yield self
            yield self
        else:
            # Start driver for this session
            try:
                self.start_driver()
                yield self
            finally:
                self.stop_driver()
    
    # ========================================
    # DRIVER LIFECYCLE MANAGEMENT
    # ========================================
    
    def start_driver(self):
        """Start the web driver with enhanced error handling."""
        if self._driver_started:
            self.logger.warning("Driver already started")
            return
        
        try:
            self.logger.info(f"Starting {self.browser} driver (debug: {self.debug})")
            self.driver = self.browser_factory.create_driver(
                self.browser, 
                debug=self.debug,
                **self.browser_options
            )
            self.wait = WebDriverWait(self.driver, self.wait_timeout)
            self._driver_started = True
            self.logger.info("Driver started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start driver: {e}")
            raise BrowserError(f"Could not start {self.browser} driver: {e}")
    
    def stop_driver(self):
        """Stop the web driver with proper cleanup."""
        if not self._driver_started or not self.driver:
            return
        
        try:
            self.driver.quit()
            self.logger.info("Driver stopped successfully")
        except Exception as e:
            self.logger.warning(f"Error stopping driver: {e}")
        finally:
            self.driver = None
            self.wait = None
            self._driver_started = False
    
    def restart_driver(self):
        """Restart the web driver."""
        self.logger.info("Restarting driver...")
        self.stop_driver()
        self.start_driver()
    
    # ========================================
    # DRIVER STATE VALIDATION
    # ========================================
    
    def _ensure_driver(self):
        """Ensure driver is started, raise exception if not."""
        if not self._driver_started or not self.driver:
            raise DriverNotStartedError("Driver not started. Call start_driver() first.")
    
    # ========================================
    # ENHANCED ELEMENT INTERACTION
    # ========================================
    
    def navigate_to(self, url: str):
        """Navigate to a URL with error handling."""
        self._ensure_driver()
        try:
            self.logger.debug(f"Navigating to: {url}")
            self.driver.get(url)
        except Exception as e:
            raise PageLoadError(f"Failed to navigate to {url}: {e}")
    
    def scroll_to_bottom(self):
        """Scroll to the bottom of the page."""
        self._ensure_driver()
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    
    def scroll_to_element(self, element: WebElement, behavior: str = "smooth"):
        """Scroll to a specific element with configurable behavior."""
        self._ensure_driver()
        script = f"arguments[0].scrollIntoView({{behavior: '{behavior}'}});"
        self.driver.execute_script(script, element)
    
    def scroll_to_element_and_click(self, element: WebElement, pause: float = 0.2):
        """Scroll to an element and click it with configurable pause."""
        self.scroll_to_element(element)
        if pause > 0:
            sleep(pause)
        element.click()
    
    def hover_over_element(self, element: WebElement):
        """Hover over a specific element."""
        self._ensure_driver()
        ActionChains(self.driver).move_to_element(element).perform()
    
    def hover_by_text(self, text: str, link_type: str = "LINK_TEXT"):
        """Hover over an element by its text content."""
        locator = (getattr(By, link_type, By.LINK_TEXT), text)
        element = self.wait_for_element(locator)
        self.hover_over_element(element)
    
    # ========================================
    # ENHANCED WAITING STRATEGIES
    # ========================================
    
    def wait_for_element(
        self, 
        locator: Tuple[By, str], 
        timeout: Optional[int] = None
    ) -> WebElement:
        """Wait for an element to be present with enhanced error handling."""
        self._ensure_driver()
        timeout = timeout or self.wait_timeout
        
        try:
            if timeout != self.wait_timeout:
                # Use custom timeout
                wait = WebDriverWait(self.driver, timeout)
                return wait.until(EC.presence_of_element_located(locator))
            else:
                return self.wait.until(EC.presence_of_element_located(locator))
        except Exception as e:
            raise ElementNotFoundError(locator, timeout)
    
    def wait_for_element_to_be_clickable(
        self, 
        locator: Tuple[By, str], 
        timeout: Optional[int] = None
    ) -> WebElement:
        """Wait for an element to be clickable."""
        self._ensure_driver()
        timeout = timeout or self.wait_timeout
        
        try:
            if timeout != self.wait_timeout:
                wait = WebDriverWait(self.driver, timeout)
                return wait.until(EC.element_to_be_clickable(locator))
            else:
                return self.wait.until(EC.element_to_be_clickable(locator))
        except Exception as e:
            raise ElementNotFoundError(locator, timeout)
    
    def wait_for_element_to_be_visible(
        self, 
        locator: Tuple[By, str], 
        timeout: Optional[int] = None
    ) -> WebElement:
        """Wait for an element to be visible."""
        self._ensure_driver()
        timeout = timeout or self.wait_timeout
        
        try:
            if timeout != self.wait_timeout:
                wait = WebDriverWait(self.driver, timeout)
                return wait.until(EC.visibility_of_element_located(locator))
            else:
                return self.wait.until(EC.visibility_of_element_located(locator))
        except Exception as e:
            raise ElementNotFoundError(locator, timeout)
    
    def wait_for_all_elements_to_be_visible(
        self, 
        locator: Tuple[By, str], 
        timeout: Optional[int] = None
    ) -> List[WebElement]:
        """Wait for all elements matching locator to be visible."""
        self._ensure_driver()
        timeout = timeout or self.wait_timeout
        
        try:
            if timeout != self.wait_timeout:
                wait = WebDriverWait(self.driver, timeout)
                return wait.until(EC.visibility_of_all_elements_located(locator))
            else:
                return self.wait.until(EC.visibility_of_all_elements_located(locator))
        except Exception as e:
            raise ElementNotFoundError(locator, timeout)
    
    def wait_for_page_to_load(self, timeout: Optional[int] = None):
        """Wait for the page to finish loading."""
        self._ensure_driver()
        timeout = timeout or self.wait_timeout
        
        try:
            if timeout != self.wait_timeout:
                wait = WebDriverWait(self.driver, timeout)
                wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
            else:
                self.wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        except Exception as e:
            raise PageLoadError(f"Page failed to load within {timeout} seconds: {e}")
    
    # ========================================
    # ENHANCED DATA EXTRACTION
    # ========================================
    
    def extract_table_data(
        self, 
        table_element: WebElement, 
        header_row: bool = True,
        nested_tables: bool = True
    ) -> List[dict]:
        """
        Enhanced table extraction with configurable options.
        
        Args:
            table_element: Table element to extract from
            header_row: Whether to use first row as headers
            nested_tables: Whether to process nested tables
            
        Returns:
            List of dictionaries representing table rows
        """
        table_data = []
        rows = table_element.find_elements(By.CSS_SELECTOR, "tbody tr")
        
        if not rows:
            # Try to get rows from table directly if no tbody
            rows = table_element.find_elements(By.CSS_SELECTOR, "tr")
        
        headers = []
        start_row = 0
        
        # Extract headers if requested
        if header_row and rows:
            header_cells = rows[0].find_elements(By.CSS_SELECTOR, "th, td")
            headers = [cell.text.strip() for cell in header_cells]
            start_row = 1
        
        # Process data rows
        for row in rows[start_row:]:
            row_data = {}
            cells = row.find_elements(By.CSS_SELECTOR, "td")
            
            for idx, cell in enumerate(cells):
                column_name = headers[idx] if idx < len(headers) else f"Column {idx + 1}"
                
                # Handle nested tables if enabled
                if nested_tables:
                    nested_table_elements = cell.find_elements(By.CSS_SELECTOR, "table")
                    if nested_table_elements:
                        row_data[column_name] = [
                            self.extract_table_data(nt, header_row, nested_tables) 
                            for nt in nested_table_elements
                        ]
                        continue
                
                # Extract text content
                text_content = cell.text.strip()
                if text_content:
                    row_data[column_name] = text_content
            
            if row_data:
                table_data.append(row_data)
        
        return table_data
    
    # ========================================
    # UTILITY METHODS
    # ========================================
    
    def take_screenshot(self, filename: str = "screenshot.png") -> str:
        """Take a screenshot and save it."""
        self._ensure_driver()
        try:
            self.driver.save_screenshot(filename)
            self.logger.info(f"Screenshot saved: {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"Failed to take screenshot: {e}")
            raise ScraperError(f"Screenshot failed: {e}")
    
    def get_page_source(self) -> str:
        """Get the current page source."""
        self._ensure_driver()
        return self.driver.page_source
    
    def get_current_url(self) -> str:
        """Get the current URL."""
        self._ensure_driver()
        return self.driver.current_url
    
    def execute_script(self, script: str, *args) -> Any:
        """Execute JavaScript with error handling."""
        self._ensure_driver()
        try:
            return self.driver.execute_script(script, *args)
        except Exception as e:
            self.logger.error(f"JavaScript execution failed: {e}")
            raise ScraperError(f"Script execution failed: {e}")
    
    # ========================================
    # ABSTRACT METHODS
    # ========================================
    
    def run(self):
        """Main method to run the scraper. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement the run method")
