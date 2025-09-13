"""
Interface protocols for better type safety and cleaner architecture.
These define contracts that components must follow.
"""

from typing import Protocol, runtime_checkable, Optional, List, Dict, Any
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By


@runtime_checkable
class WebDriverProtocol(Protocol):
    """Protocol defining the interface for web driver operations."""
    
    def get(self, url: str) -> None:
        """Navigate to a URL."""
        ...
    
    def find_element(self, by: By, value: str) -> WebElement:
        """Find a single element."""
        ...
    
    def find_elements(self, by: By, value: str) -> List[WebElement]:
        """Find multiple elements."""
        ...
    
    def execute_script(self, script: str, *args) -> Any:
        """Execute JavaScript."""
        ...
    
    def quit(self) -> None:
        """Close the driver."""
        ...


@runtime_checkable
class WaitProtocol(Protocol):
    """Protocol for WebDriver wait operations."""
    
    def until(self, method, message: str = "") -> Any:
        """Wait until a condition is met."""
        ...


@runtime_checkable
class ScraperProtocol(Protocol):
    """Protocol defining the core scraper interface."""
    
    driver: Optional[WebDriverProtocol]
    wait: Optional[WaitProtocol]
    
    def start_driver(self) -> None:
        """Start the web driver."""
        ...
    
    def stop_driver(self) -> None:
        """Stop the web driver."""
        ...
    
    def wait_for_element(self, locator: tuple) -> WebElement:
        """Wait for an element to be present."""
        ...


@runtime_checkable
class PageHandlerProtocol(Protocol):
    """Protocol for page-specific handlers."""
    
    def handle_page(self, scraper: ScraperProtocol, **kwargs) -> Any:
        """Handle a specific page interaction."""
        ...


@runtime_checkable
class DataProcessorProtocol(Protocol):
    """Protocol for data processing components."""
    
    def process_data(self, raw_data: Any) -> Any:
        """Process raw data into structured format."""
        ...


@runtime_checkable
class ProgressTrackerProtocol(Protocol):
    """Protocol for progress tracking."""
    
    def start_task(self, task_name: str, total_items: int = 0) -> None:
        """Start tracking a task."""
        ...
    
    def update_progress(self, completed: int, message: str = "") -> None:
        """Update progress."""
        ...
    
    def complete_task(self, message: str = "") -> None:
        """Mark task as completed."""
        ...
