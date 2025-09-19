from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import logging


class Scraper:
    """Base scraper class with common web scraping functionality."""

    def __init__(self, driver, wait, browser: str = "firefox", debug: bool = False):
        self.browser = browser.strip().lower()
        self.debug = debug
        self.driver = driver
        self.wait = wait
        self.logger = logging.getLogger(self.__class__.__name__)


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

