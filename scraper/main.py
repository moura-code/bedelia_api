from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import json
import os
import sys
import traceback
import logging
import re
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium import webdriver

# Import page classes
from pages.login import LoginPage
from pages.previas import Previas
from pages.posprevias import PosPrevias

load_dotenv()
# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _get_options(browser: str, debug: bool):
        """Get browser-specific options."""
        if browser == "chrome":
            options = ChromeOptions()
            if not debug:
                options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            return options
        # default firefox
        options = FirefoxOptions()
        if not debug:
            options.add_argument("--headless")
        return options

def build_driver(browser: str, debug: bool = False):
    """Build and return the appropriate web driver."""
    options = _get_options(browser, debug)
    
    if browser == "chrome":
        return webdriver.Chrome(options=options)
    else:  # firefox
        return webdriver.Firefox(options=options)

def _str_to_bool(value: str) -> bool:
    """Convert string to boolean."""
    return value.lower() in ('true', '1', 'yes', 'on')
class Bedelias():
    """Bedelías scraper for extracting academic data."""

    def __init__(
        self,
        username: str = None,
        password: str = None,
        debug: bool = False,
        browser: str = "firefox",
    ):
        self.username = username
        self.password = password
        self.login_url = "https://bedelias.udelar.edu.uy/views/private/desktop/evaluarPrevias/evaluarPrevias02.xhtml?cid=2"
        self.home_url = "https://bedelias.udelar.edu.uy/"
        self.debug = debug
        self.browser = browser
        self.driver = None
        self.wait = None
        
        # Initialize logger
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize page objects (will be set up after driver is created)
        self.login_page = None
        self.previas_page = None
        self.posprevias_page = None
        

   
    def start_driver(self):
        """Initialize the web driver and wait object."""
        self.logger.info(f"Starting {self.browser} browser...")
        self.driver = build_driver(self.browser, self.debug)
        self.wait = WebDriverWait(self.driver, 60)
        
        # Initialize page objects with driver and wait
        self.login_page = LoginPage(self.driver, self.wait, self.browser, self.debug, self.username, self.password, self.login_url, self.home_url )
        
        self.previas_page = Previas(self.driver, self.wait, self.browser, self.debug, self.home_url)
        
        self.posprevias_page = PosPrevias(self.driver, self.wait, self.browser, self.debug, self.home_url)

    def stop_driver(self):
        """Close the web driver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.wait = None

    def login_and_navigate(self):
        """Login to Bedelías using the LoginPage class."""
        if self.login_page:
            self.login_page.run()
        else:
            raise RuntimeError("Login page not initialized. Call start_driver() first.")

    def get_previas(self):
        """Extract previas data using the Previas page class."""
        if self.previas_page:
            return self.previas_page.run()
        else:
            raise RuntimeError("Previas page not initialized. Call start_driver() first.")

    def get_posprevias(self):
        """Extract posprevias data using the PosPrevias page class."""
        if self.posprevias_page:
            return self.posprevias_page.run()
        else:
            raise RuntimeError("PosPrevias page not initialized. Call start_driver() first.")
        
    def run(self, extract_previas: bool = True, extract_posprevias: bool = True):
        """Main method to run the Bedelías scraper."""
        try:
            self.logger.info(
                "Starting Bedelía scraper..."
            )

            # Start driver
            self.start_driver()

            # Login and navigate
            # self.login_and_navigate()

            # Extract data based on parameters
            if extract_previas:
                self.logger.info("Extracting previas data...")
                self.get_previas()
                
            if extract_posprevias:
                self.logger.info("Extracting posprevias data...")
                self.get_posprevias()
                
            self.logger.info("Scraping completed successfully!")

        except Exception as e:
            if self.debug:
                traceback.print_exc()
            else:
                self.logger.error(f"Scraping error: {e}")
            raise
        finally:
            self.logger.info("Cleaning up and closing browser...")
            self.stop_driver()


def main():
    """Main entry point for the Bedelías scraper application."""
    # Get configuration from environment
    username = os.getenv("DOCUMENTO", "")
    password = os.getenv("CONTRASENA", "")
    browser = os.getenv("BROWSER", "firefox").strip().lower()
    debug = _str_to_bool(os.getenv("DEBUG", "False"))
    
    # Get extraction options from environment
    extract_previas = _str_to_bool(os.getenv("EXTRACT_PREVIAS", "True"))
    extract_posprevias = _str_to_bool(os.getenv("EXTRACT_POSPREVIAS", "True"))


    try:
        # Create and run the Bedelías scraper
        logger.info("Initializing Bedelías scraper...")
        scraper = Bedelias(
            username=username, 
            password=password, 
            browser=browser, 
            debug=debug
        )
        scraper.run(extract_previas=extract_previas, extract_posprevias=extract_posprevias)
        logger.info("✓ Scraping completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"✗ Scraping failed: {e}")
        if debug:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
