"""Core scraper components."""

from .base_scraper import BaseScraper
from .enhanced_scraper import EnhancedScraper
from .browser_factory import BrowserFactory
from .progress_tracker import ProgressTracker, TaskInfo, TaskStatus
from .exceptions import (
    ScraperError, BrowserError, DriverNotStartedError, DriverStartError,
    ElementNotFoundError, PageLoadError, AuthenticationError, NavigationError,
    DataExtractionError, PaginationError, RequirementsParsingError,
    InvalidConfigurationError
)
from .interfaces import (
    ScraperProtocol, WebDriverProtocol, WaitProtocol, PageHandlerProtocol,
    DataProcessorProtocol, ProgressTrackerProtocol
)

__all__ = [
    # Base classes
    'BaseScraper', 'EnhancedScraper',
    
    # Utility classes
    'BrowserFactory', 'ProgressTracker', 'TaskInfo', 'TaskStatus',
    
    # Exceptions
    'ScraperError', 'BrowserError', 'DriverNotStartedError', 'DriverStartError',
    'ElementNotFoundError', 'PageLoadError', 'AuthenticationError', 'NavigationError',
    'DataExtractionError', 'PaginationError', 'RequirementsParsingError',
    'InvalidConfigurationError',
    
    # Protocols
    'ScraperProtocol', 'WebDriverProtocol', 'WaitProtocol', 'PageHandlerProtocol',
    'DataProcessorProtocol', 'ProgressTrackerProtocol'
]
