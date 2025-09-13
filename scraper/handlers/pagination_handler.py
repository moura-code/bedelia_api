"""
Pagination handler for Bedelías website.
Handles page navigation and pagination-specific logic.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import logging
from typing import TYPE_CHECKING

from ..config import BedeliasConfig

if TYPE_CHECKING:
    from ..core.base_scraper import BaseScraper


class PaginationHandler:
    """Handles pagination operations specific to Bedelías website."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.total_pages = 0

    def get_total_pages(self: 'BaseScraper') -> int:
        """
        Get the total number of pages in the paginator.
        
        Returns:
            Total number of pages
        """
        self.logger.info("Getting total pages...")
        self.scroll_to_bottom()
        
        # Click last page button to get total
        self.wait.until(
            EC.element_to_be_clickable((By.XPATH, BedeliasConfig.PAGINATOR_LAST_XPATH))
        ).click()
        
        # Get the active page number (which should be the last page)
        active_element = self.wait.until(
            EC.presence_of_element_located((By.XPATH, BedeliasConfig.ACTIVE_PAGE_XPATH))
        )
        total = int(active_element.text.strip())
        
        self.logger.info(f"Total pages: {total}")
        
        # Navigate back to first page
        self.wait.until(
            EC.element_to_be_clickable((By.XPATH, BedeliasConfig.PAGINATOR_FIRST_XPATH))
        ).click()
        
        self.total_pages = total
        return total

    def go_to_page(self: 'BaseScraper', page: int):
        """
        Navigate to a specific page number.
        
        Args:
            page: Page number to navigate to
        """
        # Check if we're already on the target page
        try:
            current_active = self.wait_for_element_to_be_visible(
                (By.XPATH, BedeliasConfig.ACTIVE_PAGE_XPATH)
            )
            if current_active.get_attribute("aria-label") == f"Page {page}":
                self.logger.debug(f"Already on page {page}")
                return
        except Exception:
            pass  # Continue with navigation if we can't determine current page
        
        # Handle navigation to pages beyond 10 (need to use last page button first)
        if page > 10:
            last_button = self.wait_for_element_to_be_clickable(
                (By.XPATH, BedeliasConfig.PAGINATOR_LAST_XPATH)
            )
            self.scroll_to_element_and_click(last_button)
            self.wait_for_page_to_load()
        
        # Navigate to specific page
        page_link_xpath = BedeliasConfig.PAGE_LINK_XPATH_TEMPLATE.format(page=page)
        page_link = self.wait_for_element_to_be_clickable((By.XPATH, page_link_xpath))
        self.scroll_to_element_and_click(page_link)
        self.wait_for_page_to_load()
        
        self.logger.debug(f"Navigated to page {page}")

    def get_current_page_subjects_count(self: 'BaseScraper') -> int:
        """
        Get the number of subjects on the current page.
        
        Returns:
            Number of subject rows on current page
        """
        rows = self.driver.find_elements(By.XPATH, BedeliasConfig.DATA_ROW_XPATH)
        return len(rows)
