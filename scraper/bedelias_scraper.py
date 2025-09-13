"""
Main Bedelías scraper class using composition pattern.
This is the refactored scraper that combines all specialized components.
"""

import json
import logging
import traceback
from typing import Dict, Any, Optional
from time import sleep
from selenium.webdriver.common.by import By

from .core.base_scraper import BaseScraper
from .handlers import PageHandlers, RequirementsProcessor, PaginationHandler
from .models import SubjectInfo
from .config import BedeliasConfig
from .utils import retry_on_exception


class BedeliasScraper(BaseScraper, PageHandlers, RequirementsProcessor, PaginationHandler):
    """
    Main Bedelías scraper class that combines all functionality using composition.
    
    This class inherits from:
    - BaseScraper: Universal web scraping functionality
    - PageHandlers: Bedelías-specific page interactions  
    - RequirementsProcessor: Requirements tree parsing logic
    - PaginationHandler: Pagination-specific operations
    """

    def __init__(
        self,
        username: str,
        password: str,
        browser: str = "firefox",
        debug: bool = False,
    ):
        """
        Initialize the Bedelías scraper.
        
        Args:
            username: User's document number
            password: User's password
            browser: Browser type ('chrome' or 'firefox')
            debug: Whether to run in debug mode
        """
        # Initialize all parent classes
        super().__init__(browser, debug)
        PageHandlers.__init__(self)
        RequirementsProcessor.__init__(self)
        PaginationHandler.__init__(self)
        
        self.username = username
        self.password = password
        self.logger = logging.getLogger(self.__class__.__name__)

    # ========================================
    # MAIN WORKFLOW ORCHESTRATION
    # ========================================

    def run(self):
        """Main method to run the Bedelías scraper."""
        try:
            self.logger.info("Starting Bedelía scraper with organized structure...")
            
            # Start driver
            self.start_driver()
            
            # Login and navigate to prerequisites page
            self.login_and_navigate(self.username, self.password)
            
            # Extract prerequisites data
            self.extract_prerequisites_data()
            
            self.logger.info("Scraping completed successfully!")
            
        except Exception as e:
            if self.debug:
                traceback.print_exc()
            else:
                self.logger.error(f"Scraping error: {e}")
        finally:
            self.logger.info("Cleaning up and closing browser...")
            self.stop_driver()

    def extract_prerequisites_data(self):
        """Main method to extract all prerequisites data."""
        self.logger.info("Starting prerequisites data extraction...")
        
        # Navigate to prerequisites page
        self.navigate_to_prerequisites_page()
        
        # Get total pages for processing
        self.get_total_pages()
        sleep(2)  # Wait for page to stabilize
        
        # Extract data from all pages
        extracted_data = self._process_all_pages()
        
        # Save backup
        self._save_backup_data(extracted_data)
        
        return extracted_data

    # ========================================
    # DATA PROCESSING METHODS
    # ========================================

    def _process_all_pages(self) -> Dict[str, SubjectInfo]:
        """
        Process all pages and extract subject data.
        
        Returns:
            Dictionary mapping subject codes to SubjectInfo objects
        """
        data = {}
        
        try:
            for current_page in range(1, self.total_pages + 1):
                self.logger.info(f"Processing page {current_page}/{self.total_pages}")
                page_data = self._process_single_page(current_page)
                data.update(page_data)
        
        except Exception as e:
            self.logger.error(f"Error processing pages: {e}")
            if self.debug:
                traceback.print_exc()
        
        return data

    def _process_single_page(self, page_number: int) -> Dict[str, SubjectInfo]:
        """
        Process a single page of subjects.
        
        Args:
            page_number: Page number to process
            
        Returns:
            Dictionary of extracted subjects from this page
        """
        page_data = {}
        subjects_count = self.get_current_page_subjects_count()
        
        for i in range(subjects_count):
            try:
                subject_info = self._process_subject_row(page_number, i)
                if subject_info:
                    page_data[subject_info.code] = subject_info
                    self.logger.info(f"Successfully processed subject: {subject_info.code}")
            
            except Exception as e:
                self.logger.error(f"Error processing subject row {i} on page {page_number}: {e}")
                if self.debug:
                    traceback.print_exc()
                continue
        
        return page_data

    @retry_on_exception(max_retries=2, delay=1.0)
    def _process_subject_row(self, page_number: int, row_index: int) -> Optional[SubjectInfo]:
        """
        Process a single subject row.
        
        Args:
            page_number: Current page number
            row_index: Index of the row to process
            
        Returns:
            SubjectInfo object or None if processing fails
        """
        # Ensure we're on the correct page
        self.go_to_page(page_number)
        
        # Get the specific row
        rows = self.wait_for_all_elements_to_be_visible(
            (By.XPATH, BedeliasConfig.DATA_ROW_XPATH)
        )
        
        if row_index >= len(rows):
            self.logger.warning(f"Row index {row_index} out of range on page {page_number}")
            return None
        
        row = rows[row_index]
        cells = row.find_elements(By.TAG_NAME, "td")
        
        if len(cells) < 3:
            raise ValueError("Less than 3 cells found in row")
        
        # Extract basic subject information
        subject_info = SubjectInfo(
            code=cells[0].text.strip() if cells[0].text else "",
            name=cells[1].text.strip() if cells[1].text else "",
        )
        
        if not subject_info.code:
            self.logger.warning("Empty subject code found, skipping row")
            return None
        
        # Click "Ver Más" to view requirements
        more_info_link = cells[2].find_element(By.TAG_NAME, "a")
        self.scroll_to_element_and_click(more_info_link)
        
        # Wait for requirements dialog to appear
        self.wait_for_element_to_be_visible(
            (By.XPATH, BedeliasConfig.REQUIREMENTS_DIALOG_XPATH)
        )
        
        # Expand and extract requirements
        self.expand_all_requirements()
        subject_info.requirements = self.extract_requirements()
        
        # Go back to main list
        back_button = self.driver.find_element(By.XPATH, BedeliasConfig.BACK_BUTTON_XPATH)
        self.scroll_to_element_and_click(back_button)
        
        return subject_info

    # ========================================
    # DATA PERSISTENCE
    # ========================================

    def _save_backup_data(self, data: Dict[str, SubjectInfo]):
        """
        Save extracted data as backup JSON file.
        
        Args:
            data: Dictionary of SubjectInfo objects to save
        """
        try:
            # Convert to serializable format
            serializable_data = {
                code: subject.to_dict() for code, subject in data.items()
            }
            
            with open(BedeliasConfig.BACKUP_FILENAME, "w", encoding="utf-8") as fp:
                json.dump(serializable_data, fp, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Backup saved to {BedeliasConfig.BACKUP_FILENAME}")
            self.logger.info(f"Total subjects processed: {len(data)}")
            
        except Exception as e:
            self.logger.error(f"Error saving backup: {e}")
            if self.debug:
                traceback.print_exc()
