from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
import logging


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
        el = self.wait_for_element_to_be_present((By.LINK_TEXT, text))
        ActionChains(self.driver).move_to_element(el).perform()

    def scroll_to_element(self, element):
        self.driver.execute_script("arguments[0].scrollIntoView();", element)

    def scroll_to_element_and_click(self, element):
        self.scroll_to_element(element)
        self.wait_for_element_to_be_clickable(element).click()


    def wait_for_element_to_be_clickable(self, locator: tuple):
        return self.wait.until(EC.element_to_be_clickable(locator))

    def wait_for_element_to_be_visible(self, locator: tuple):
        return self.wait.until(EC.visibility_of_element_located(locator))

    def wait_for_all_elements_to_be_visible(self, locator: tuple):
        return self.wait.until(EC.visibility_of_all_elements_located(locator))

    def wait_for_element_to_be_present(self, locator: tuple):
        return self.wait.until(EC.presence_of_element_located(locator))

    def run(self):
        """Main method to run the scraper. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement the run method")

    def wait_for_page_to_load(self):
        self.wait.until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    
    def try_find_element(self, locator: tuple):
        try:
            return  WebDriverWait(self.driver, 2).until(EC.presence_of_element_located(locator))
        except:
            return None

