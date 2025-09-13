"""
Custom exceptions for the scraper package.
Provides specific exception types for better error handling.
"""


class ScraperError(Exception):
    """Base exception for all scraper-related errors."""
    pass


class BrowserError(ScraperError):
    """Raised when there are browser-related issues."""
    pass


class DriverNotStartedError(BrowserError):
    """Raised when attempting to use driver before starting it."""
    pass


class DriverStartError(BrowserError):
    """Raised when driver fails to start."""
    pass


class ElementNotFoundError(ScraperError):
    """Raised when a required element cannot be found."""
    
    def __init__(self, locator: tuple, timeout: int = 10):
        self.locator = locator
        self.timeout = timeout
        super().__init__(f"Element not found: {locator} (timeout: {timeout}s)")


class PageLoadError(ScraperError):
    """Raised when a page fails to load properly."""
    pass


class AuthenticationError(ScraperError):
    """Raised when authentication fails."""
    pass


class NavigationError(ScraperError):
    """Raised when navigation between pages fails."""
    pass


class DataExtractionError(ScraperError):
    """Raised when data extraction fails."""
    pass


class PaginationError(ScraperError):
    """Raised when pagination operations fail."""
    pass


class RequirementsParsingError(DataExtractionError):
    """Raised when requirements tree parsing fails."""
    pass


class InvalidConfigurationError(ScraperError):
    """Raised when configuration is invalid."""
    pass
