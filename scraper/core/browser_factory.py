"""
Browser factory using strategy pattern for creating different browser instances.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Type
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions

from .exceptions import BrowserError, InvalidConfigurationError


class BrowserStrategy(ABC):
    """Abstract base class for browser strategies."""
    
    @abstractmethod
    def create_driver(self, debug: bool = False, **options) -> webdriver.Remote:
        """Create and return a configured web driver."""
        pass
    
    @abstractmethod
    def get_options(self, debug: bool = False, **options):
        """Get browser-specific options."""
        pass


class FirefoxStrategy(BrowserStrategy):
    """Strategy for creating Firefox browser instances."""
    
    def get_options(self, debug: bool = False, **options) -> FirefoxOptions:
        """Get Firefox-specific options."""
        firefox_options = FirefoxOptions()
        
        if not debug:
            firefox_options.add_argument("--headless")
        
        # Default options
        firefox_options.add_argument("--width=1920")
        firefox_options.add_argument("--height=1080")
        firefox_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Custom options
        for key, value in options.items():
            if isinstance(value, bool) and value:
                firefox_options.add_argument(f"--{key}")
            elif isinstance(value, str):
                firefox_options.add_argument(f"--{key}={value}")
        
        return firefox_options
    
    def create_driver(self, debug: bool = False, **options) -> webdriver.Firefox:
        """Create Firefox driver."""
        try:
            return webdriver.Firefox(options=self.get_options(debug, **options))
        except Exception as e:
            raise BrowserError(f"Failed to create Firefox driver: {e}")


class ChromeStrategy(BrowserStrategy):
    """Strategy for creating Chrome browser instances."""
    
    def get_options(self, debug: bool = False, **options) -> ChromeOptions:
        """Get Chrome-specific options."""
        chrome_options = ChromeOptions()
        
        if not debug:
            chrome_options.add_argument("--headless=new")
        
        # Default options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Custom options
        for key, value in options.items():
            if isinstance(value, bool) and value:
                chrome_options.add_argument(f"--{key}")
            elif isinstance(value, str):
                chrome_options.add_argument(f"--{key}={value}")
        
        return chrome_options
    
    def create_driver(self, debug: bool = False, **options) -> webdriver.Chrome:
        """Create Chrome driver."""
        try:
            return webdriver.Chrome(options=self.get_options(debug, **options))
        except Exception as e:
            raise BrowserError(f"Failed to create Chrome driver: {e}")


class EdgeStrategy(BrowserStrategy):
    """Strategy for creating Edge browser instances."""
    
    def get_options(self, debug: bool = False, **options) -> EdgeOptions:
        """Get Edge-specific options."""
        edge_options = EdgeOptions()
        
        if not debug:
            edge_options.add_argument("--headless=new")
        
        # Default options
        edge_options.add_argument("--no-sandbox")
        edge_options.add_argument("--disable-dev-shm-usage")
        edge_options.add_argument("--window-size=1920,1080")
        edge_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Custom options
        for key, value in options.items():
            if isinstance(value, bool) and value:
                edge_options.add_argument(f"--{key}")
            elif isinstance(value, str):
                edge_options.add_argument(f"--{key}={value}")
        
        return edge_options
    
    def create_driver(self, debug: bool = False, **options) -> webdriver.Edge:
        """Create Edge driver."""
        try:
            return webdriver.Edge(options=self.get_options(debug, **options))
        except Exception as e:
            raise BrowserError(f"Failed to create Edge driver: {e}")


class BrowserFactory:
    """Factory class for creating browser instances using strategy pattern."""
    
    def __init__(self):
        self._strategies: Dict[str, Type[BrowserStrategy]] = {
            'firefox': FirefoxStrategy,
            'chrome': ChromeStrategy,
            'edge': EdgeStrategy,
        }
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def register_strategy(self, browser_name: str, strategy_class: Type[BrowserStrategy]):
        """Register a new browser strategy."""
        self._strategies[browser_name.lower()] = strategy_class
        self.logger.info(f"Registered browser strategy: {browser_name}")
    
    def create_driver(self, browser: str, debug: bool = False, **options) -> webdriver.Remote:
        """
        Create a web driver using the appropriate strategy.
        
        Args:
            browser: Browser type ('firefox', 'chrome', 'edge')
            debug: Whether to run in debug mode (visible browser)
            **options: Additional browser-specific options
            
        Returns:
            Configured web driver instance
            
        Raises:
            InvalidConfigurationError: If browser type is not supported
            BrowserError: If driver creation fails
        """
        browser = browser.lower().strip()
        
        if browser not in self._strategies:
            available = ', '.join(self._strategies.keys())
            raise InvalidConfigurationError(
                f"Unsupported browser: {browser}. Available: {available}"
            )
        
        strategy = self._strategies[browser]()
        self.logger.info(f"Creating {browser} driver (debug: {debug})")
        
        return strategy.create_driver(debug=debug, **options)
    
    def get_supported_browsers(self) -> list:
        """Get list of supported browser names."""
        return list(self._strategies.keys())
