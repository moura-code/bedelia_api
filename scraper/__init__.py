"""
Bedelías Scraper Package

A well-organized web scraper for extracting academic data from Bedelías.
This package follows a clean architecture with separated concerns.
"""

from .bedelias_scraper import BedeliasScraper
from .utils import setup_logging, str_to_bool

__version__ = "2.0.0"
__all__ = ['BedeliasScraper', 'setup_logging', 'str_to_bool']
