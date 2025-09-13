"""
Utility helper functions for the scraper.
Contains reusable utility functions that don't fit into specific categories.
"""

import logging
import functools
from time import sleep
from typing import Callable, Any, Type, Tuple


def str_to_bool(value: str) -> bool:
    """
    Convert string representation to boolean.
    
    Args:
        value: String value to convert
        
    Returns:
        Boolean value
    """
    return str(value).strip().lower() in ("1", "true", "t", "yes", "y")


def retry_on_exception(
    max_retries: int = 3,
    delay: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    """
    Decorator to retry function calls on specific exceptions.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
        exceptions: Tuple of exception types to catch and retry on
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logging.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay} seconds..."
                        )
                        sleep(delay)
                    else:
                        logging.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}: {e}"
                        )
                        break
            
            # Re-raise the last exception if all retries failed
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def setup_logging(level: int = logging.INFO, format_str: str = None) -> None:
    """
    Setup logging configuration for the application.
    
    Args:
        level: Logging level (default: INFO)
        format_str: Custom format string (optional)
    """
    if format_str is None:
        format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(level=level, format=format_str)
    
    # Suppress overly verbose selenium logs
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
