from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from time import sleep
import logging
import traceback

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

    def scroll_to_element(self, element, behavior="auto", block="center", inline="nearest"):
        """
        Scroll to element with configurable options.
        
        Args:
            element: WebElement to scroll to
            behavior: 'smooth' or 'auto' (instant)
            block: 'start', 'center', 'end', or 'nearest'
            inline: 'start', 'center', 'end', or 'nearest'
        """
        try:
            # Modern approach with scrollIntoView options
            self.driver.execute_script(
                """
                arguments[0].scrollIntoView({
                    behavior: arguments[1],
                    block: arguments[2],
                    inline: arguments[3]
                });
                """,
                element, behavior, block, inline
            )
            # Small pause to allow smooth scrolling to complete
            if behavior == "smooth":
                sleep(0.3)
        except Exception as e:
            # Fallback to basic scrollIntoView for older browsers
            self.logger.warning(f"Modern scroll failed, using fallback: {e}")
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            sleep(0.2)

    def scroll_to_element_and_click(self, element):
        """Scroll to element and click, waiting for modal to disappear first."""
        # Always wait for the persistent modal overlay to disappear
        trys_number = 0
        while trys_number < 3:
            trys_number += 1
            try:
                self.wait.until(
                    EC.invisibility_of_element_located((By.ID, "j_idt22_modal"))
                )
                self.scroll_to_element(element)
                self.wait_for_element_to_be_clickable(element).click()
                return True
            except:
                pass
        traceback.print_exc()
        return False



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
    
    def try_find_element(self, locator: tuple, wait: int = 2):
        try:
            return  WebDriverWait(self.driver, wait).until(EC.presence_of_element_located(locator))
        except:
            return None
    def wait_loading_to_finish(self):
        loading_path = "//img[@src='/jakarta.faces.resource/img/cargando.gif.xhtml?ln=default']"
        self.wait.until(EC.invisibility_of_element_located((By.XPATH, loading_path)))

    def remove_element(self, element):
        self.driver.execute_script("""
        var element = arguments[0];
        element.remove();
        """, element)