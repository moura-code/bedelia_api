from __future__ import annotations

from dotenv import load_dotenv
import logging
import sys
import traceback
from typing import Callable, Dict, Tuple

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support.ui import WebDriverWait

from config import ScraperConfig
from pages.login import LoginPage
from pages.previas import Previas
from pages.posprevias import PosPrevias
from pages.credits import Credits
from pages.vigentes import Vigentes
load_dotenv()

# Configure logging with better formatting and levels
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bedelias_scraper.log", encoding="utf-8")
    ]
)

# Set specific log levels for different components
logging.getLogger("selenium").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def _get_options(browser: str, debug: bool):
    """Return browser options configured for headless scraping when requested."""
    if browser == "chrome":
        options = ChromeOptions()
        if not debug:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        return options

    options = FirefoxOptions()
    if not debug:
        options.add_argument("--headless")
    return options


def build_driver(browser: str, debug: bool = False):
    """Build and return the Selenium driver for the requested browser."""
    options = _get_options(browser, debug)

    if browser == "chrome":
        return webdriver.Chrome(options=options)
    if browser == "firefox":
        return webdriver.Firefox(options=options)

    raise ValueError(f"Unsupported browser '{browser}'")


class Bedelias:
    """Bedelias scraper orchestrating page-level extractors."""

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.username = config.username
        self.password = config.password
        self.browser = config.browser
        self.debug = config.debug
        self.login_url = (
            "https://bedelias.udelar.edu.uy/views/private/desktop/"
            "evaluarPrevias/evaluarPrevias02.xhtml?cid=2"
        )
        self.home_url = "https://bedelias.udelar.edu.uy/"

        self.driver = None
        self.wait = None
        self._logged_in = False

        self.logger = logging.getLogger(self.__class__.__name__)

        self.login_page = None
        self.previas_page = None
        self.posprevias_page = None
        self.credits_page = None

    def start_driver(self):
        """Initialize the Selenium driver and page objects."""
        self.logger.info("Starting %s browser in %s mode...", self.browser, "debug" if self.debug else "headless")
        try:
            self.driver = build_driver(self.browser, self.debug)
            self.wait = WebDriverWait(self.driver, 60)
            self.logger.info("Browser started successfully")
        except Exception as e:
            self.logger.error("Failed to start browser: %s", e)
            raise

        self.login_page = LoginPage(
            self.driver,
            self.wait,
            self.browser,
            self.debug,
            self.username,
            self.password,
            self.login_url,
            self.home_url,
        )
        self.previas_page = Previas(
            self.driver,
            self.wait,
            self.browser,
            self.debug,
            self.home_url,
        )
        self.posprevias_page = PosPrevias(
            self.driver,
            self.wait,
            self.browser,
            self.debug,
            self.home_url,
        )
        self.credits_page = Credits(
            self.driver,
            self.wait,
            self.browser,
            self.debug,
            self.home_url,
        )
        self.vigentes_page = Vigentes(
            self.driver,
            self.wait,
            self.browser,
            self.debug,
            self.home_url,
        )
    def stop_driver(self):
        """Cleanly close the Selenium driver."""
        if self.driver:
            self.logger.info("Closing browser...")
            self.logger.info("Browser closed successfully")
            self.driver.quit()
        self._logged_in = False

    def login_and_navigate(self):
        """Perform the initial login and land on the home page."""
        if not self.login_page:
            raise RuntimeError("Login page not initialized. Call start_driver() first.")
        self.logger.info("Starting authentication process...")
        self.config.require_credentials()
        self.login_page.run()
        self._logged_in = True
        self.logger.info("Authentication completed successfully")

    def _ensure_logged_in(self):
        if self._logged_in:
            return
        if not self.login_page:
            raise RuntimeError("Login page not initialized. Call start_driver() first.")
        if not self.username or not self.password:
            raise RuntimeError("Login required but credentials are missing.")
        self.logger.info("Logging in before running data extraction steps...")
        self.login_and_navigate()

    def get_previas(self):
        """Extract previas data using the Previas page class."""
        if not self.previas_page:
            raise RuntimeError("Previas page not initialized. Call start_driver() first.")
        self.previas_page.run()

    def get_posprevias(self):
        """Extract posprevias data using the PosPrevias page class."""
        if not self.posprevias_page:
            raise RuntimeError("PosPrevias page not initialized. Call start_driver() first.")
        self.posprevias_page.run()

    def get_credits(self):
        """Extract credits data using the Credits page class."""
        if not self.credits_page:
            raise RuntimeError("Credits page not initialized. Call start_driver() first.")
        self.credits_page.run()
    def get_vigentes(self):
        """Extract vigentes data using the Vigentes page class."""
        if not self.vigentes_page:
            raise RuntimeError("Vigentes page not initialized. Call start_driver() first.")
        self.vigentes_page.run()

    def run(self):
        """Execute the configured scraping workflow."""
        steps: Dict[str, Tuple[Callable[[], None], bool]] = {
            "login": (self.login_and_navigate, True),
            "previas": (self.get_previas, False),
            "posprevias": (self.get_posprevias, False),
            "credits": (self.get_credits, False),
            "vigentes": (self.get_vigentes, False),
        }
        ordered_pages: list[str] = []
        seen = set()
        for page in self.config.pages:
            if page not in seen:
                ordered_pages.append(page)
                seen.add(page)

        try:
            self.logger.info("Starting Bedelias scraper...")
            self.start_driver()

            for page_name in ordered_pages:
                step = steps.get(page_name)
                if step is None:
                    self.logger.warning("Skipping unknown page '%s'", page_name)
                    continue

                handler, requires_login = step
                if requires_login:
                    self._ensure_logged_in()

                self.logger.info("Running %s step...", page_name)
                handler()

            self.logger.info("Scraping completed successfully!")

        except Exception as exc:
            if self.debug:
                traceback.print_exc()
            else:
                self.logger.error("Scraping error: %s", exc)
            raise
        finally:
            self.logger.info("Cleaning up and closing browser...")
            self.stop_driver()




def main():
    """Main entry point for the Bedelias scraper application."""
    config = ScraperConfig.from_env()
    try:
        logger.info(
            "Initializing Bedelias scraper with pages: %s",
            ", ".join(config.pages) if config.pages else "(none)",
        )
        scraper = Bedelias(config)
        try:
            scraper.run()
        except Exception as exc:
            traceback.print_exc()
            scraper.driver.get_screenshot_as_file("screenshot.png")
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        sys.exit(0)
    except Exception as exc:
        logger.error("Scraping failed: %s", exc)
        if config.debug:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
