"""
Enhanced Bedelías scraper using composition pattern with improved architecture.
This is the next-generation scraper with all architectural improvements.
"""

import json
import logging
import traceback
from typing import Dict, Optional, Any
from time import sleep
from selenium.webdriver.common.by import By

from .core.enhanced_scraper import EnhancedScraper
from .core.progress_tracker import ProgressTracker
from .core.exceptions import (
    ScraperError, AuthenticationError, NavigationError, 
    DataExtractionError, ElementNotFoundError
)
from .handlers import RequirementsProcessor
from .models import SubjectInfo
from .config import BedeliasConfig
from .utils import retry_on_exception


class EnhancedBedeliasScraper:
    """
    Enhanced Bedelías scraper using composition pattern.
    
    This class uses composition instead of multiple inheritance for cleaner architecture:
    - Composes with EnhancedScraper for web scraping capabilities
    - Uses specialized handlers as components
    - Implements proper dependency injection
    - Provides comprehensive error handling and progress tracking
    """
    
    def __init__(
        self,
        username: str,
        password: str,
        browser: str = "firefox",
        debug: bool = False,
        wait_timeout: int = 10,
        **browser_options
    ):
        """
        Initialize the enhanced Bedelías scraper.
        
        Args:
            username: User's document number
            password: User's password
            browser: Browser type ('firefox', 'chrome', 'edge')
            debug: Whether to run in debug mode
            wait_timeout: Default timeout for wait operations
            **browser_options: Additional browser-specific options
        """
        # Core credentials and configuration
        self.username = username
        self.password = password
        
        # Initialize scraper with enhanced capabilities
        self.scraper = EnhancedScraper(
            browser=browser,
            debug=debug,
            wait_timeout=wait_timeout,
            **browser_options
        )
        
        # Initialize specialized components using composition
        self.requirements_processor = RequirementsProcessor()
        self.progress_tracker = ProgressTracker(
            logger=logging.getLogger(f"{self.__class__.__name__}.Progress")
        )
        
        self.logger = logging.getLogger(self.__class__.__name__)
        self.total_pages = 0
    
    # ========================================
    # MAIN WORKFLOW ORCHESTRATION
    # ========================================
    
    def run(self):
        """Main method to run the enhanced Bedelías scraper."""
        try:
            self.progress_tracker.start_task("Scraping Bedelías Data")
            self.logger.info("Starting enhanced Bedelía scraper...")
            
            # Use context manager for driver lifecycle
            with self.scraper:
                # Execute main workflow
                self._execute_scraping_workflow()
                
            self.progress_tracker.complete_task("Scraping completed successfully!")
            self.logger.info("Enhanced scraping completed successfully!")
            
        except Exception as e:
            error_msg = f"Scraping error: {e}"
            self.progress_tracker.fail_task(error_msg)
            
            if self.debug:
                traceback.print_exc()
            else:
                self.logger.error(error_msg)
                
            raise ScraperError(error_msg) from e
    
    def _execute_scraping_workflow(self):
        """Execute the main scraping workflow."""
        # Phase 1: Authentication
        self.progress_tracker.start_task("Authentication", 1)
        self._perform_authentication()
        self.progress_tracker.update_progress(1, "Authentication successful")
        self.progress_tracker.complete_task("Authentication completed")
        
        # Phase 2: Navigation to prerequisites page
        self.progress_tracker.start_task("Navigation", 1)
        self._navigate_to_prerequisites_page()
        self.progress_tracker.update_progress(1, "Navigation completed")
        self.progress_tracker.complete_task("Prerequisites page reached")
        
        # Phase 3: Data extraction
        extracted_data = self._extract_all_prerequisites_data()
        
        # Phase 4: Save results
        self.progress_tracker.start_task("Saving Data", 1)
        self._save_backup_data(extracted_data)
        self.progress_tracker.update_progress(1, f"Saved {len(extracted_data)} subjects")
        self.progress_tracker.complete_task("Data saved successfully")
    
    # ========================================
    # AUTHENTICATION WORKFLOW
    # ========================================
    
    def _perform_authentication(self):
        """Perform authentication workflow."""
        try:
            self.logger.info("Starting authentication...")
            
            # Navigate to login page
            self.scraper.navigate_to(BedeliasConfig.LOGIN_URL)
            
            # Fill and submit login form
            self._fill_login_form()
            
            # Verify successful login
            self._verify_authentication()
            
            self.logger.info("Authentication successful")
            
        except Exception as e:
            raise AuthenticationError(f"Authentication failed: {e}") from e
    
    def _fill_login_form(self):
        """Fill and submit the login form."""
        # Fill username
        username_field = self.scraper.wait_for_element(
            (By.ID, BedeliasConfig.USERNAME_FIELD_ID), timeout=15
        )
        username_field.send_keys(self.username)
        
        # Fill password
        password_field = self.scraper.wait_for_element(
            (By.ID, BedeliasConfig.PASSWORD_FIELD_ID), timeout=5
        )
        password_field.send_keys(self.password)
        
        # Submit form
        login_button = self.scraper.wait_for_element_to_be_clickable(
            (By.NAME, BedeliasConfig.LOGIN_BUTTON_NAME), timeout=5
        )
        login_button.click()
        
        sleep(0.5)  # Brief pause for login processing
    
    def _verify_authentication(self):
        """Verify that authentication was successful."""
        try:
            # Wait for menu that appears after successful login
            self.scraper.wait_for_element(
                (By.LINK_TEXT, BedeliasConfig.STUDY_PLANS_MENU_TEXT),
                timeout=10
            )
        except ElementNotFoundError:
            raise AuthenticationError("Login failed - menu not found after authentication")
    
    # ========================================
    # NAVIGATION WORKFLOW
    # ========================================
    
    def _navigate_to_prerequisites_page(self):
        """Navigate to the prerequisites page."""
        try:
            self.logger.info("Navigating to prerequisites page...")
            
            # Navigate to home page
            self.scraper.navigate_to(BedeliasConfig.HOME_URL)
            self.scraper.wait_for_page_to_load()
            
            # Faculty selection workflow
            self._perform_faculty_selection()
            self._select_program()
            self._setup_prerequisites_system()
            
            self.logger.info("Navigation to prerequisites page completed")
            
        except Exception as e:
            raise NavigationError(f"Navigation failed: {e}") from e
    
    def _perform_faculty_selection(self):
        """Perform faculty selection workflow."""
        # Hover over study plans menu
        self.scraper.hover_by_text(BedeliasConfig.STUDY_PLANS_MENU_TEXT)
        
        # Click prerequisites link
        prerequisites_link = self.scraper.wait_for_element_to_be_clickable(
            (By.LINK_TEXT, BedeliasConfig.PREREQUISITES_LINK_TEXT), timeout=10
        )
        prerequisites_link.click()
        
        sleep(0.5)  # Brief pause for modal animation
        
        # Select technology faculty
        tech_faculty = self.scraper.wait_for_element_to_be_clickable(
            (By.XPATH, f'//*[text()="{BedeliasConfig.TECHNOLOGY_FACULTY_TEXT}"]'), timeout=10
        )
        tech_faculty.click()
        
        # Select FING faculty
        fing_faculty = self.scraper.wait_for_element_to_be_clickable(
            (By.XPATH, f'//*[text()="{BedeliasConfig.FING_FACULTY_TEXT}"]'), timeout=10
        )
        fing_faculty.click()
    
    def _select_program(self):
        """Select Computer Engineering program."""
        # Use search filter
        search_input = self.scraper.wait_for_element_to_be_clickable(
            (By.XPATH, BedeliasConfig.COLUMN_FILTER_XPATH), timeout=10
        )
        search_input.send_keys(BedeliasConfig.COMPUTER_ENGINEERING_TEXT)
        
        # Select the program
        program_select = self.scraper.wait_for_element_to_be_clickable(
            (By.XPATH, BedeliasConfig.SUBJECT_SELECT_XPATH), timeout=10
        )
        program_select.click()
    
    def _setup_prerequisites_system(self):
        """Setup access to prerequisites system."""
        # Click info button
        info_button = self.scraper.wait_for_element_to_be_clickable(
            (By.XPATH, BedeliasConfig.INFO_BUTTON_XPATH), timeout=10
        )
        info_button.click()
        
        # Click prerequisites system
        prereq_system = self.scraper.wait_for_element_to_be_clickable(
            (By.XPATH, f'//span[text()="{BedeliasConfig.PREREQUISITES_SYSTEM_SPAN_TEXT}"]'),
            timeout=10
        )
        prereq_system.click()
        
        sleep(2)  # Wait for system to load
    
    # ========================================
    # DATA EXTRACTION WORKFLOW
    # ========================================
    
    def _extract_all_prerequisites_data(self) -> Dict[str, SubjectInfo]:
        """Extract all prerequisites data from all pages."""
        try:
            self.logger.info("Starting data extraction...")
            
            # Get total pages
            self._get_total_pages()
            
            # Start extraction task
            self.progress_tracker.start_task("Data Extraction", self.total_pages)
            
            extracted_data = {}
            
            for current_page in range(1, self.total_pages + 1):
                page_data = self._process_single_page(current_page)
                extracted_data.update(page_data)
                
                self.progress_tracker.update_progress(
                    current_page, 
                    f"Processed page {current_page}/{self.total_pages}"
                )
            
            self.progress_tracker.complete_task(
                f"Extracted data for {len(extracted_data)} subjects"
            )
            
            return extracted_data
            
        except Exception as e:
            raise DataExtractionError(f"Data extraction failed: {e}") from e
    
    def _get_total_pages(self):
        """Get the total number of pages."""
        self.scraper.scroll_to_bottom()
        
        # Click last page to determine total
        last_page_button = self.scraper.wait_for_element_to_be_clickable(
            (By.XPATH, BedeliasConfig.PAGINATOR_LAST_XPATH), timeout=10
        )
        last_page_button.click()
        
        # Get total from active page
        active_page = self.scraper.wait_for_element(
            (By.XPATH, BedeliasConfig.ACTIVE_PAGE_XPATH), timeout=10
        )
        total = int(active_page.text.strip())
        
        # Navigate back to first page
        first_page_button = self.scraper.wait_for_element_to_be_clickable(
            (By.XPATH, BedeliasConfig.PAGINATOR_FIRST_XPATH), timeout=10
        )
        first_page_button.click()
        
        self.total_pages = total
        self.logger.info(f"Total pages to process: {total}")
    
    def _process_single_page(self, page_number: int) -> Dict[str, SubjectInfo]:
        """Process a single page of subjects."""
        self._navigate_to_page(page_number)
        
        page_data = {}
        rows = self.scraper.driver.find_elements(By.XPATH, BedeliasConfig.DATA_ROW_XPATH)
        
        for i, row in enumerate(rows):
            try:
                subject_info = self._process_subject_row(page_number, i)
                if subject_info:
                    page_data[subject_info.code] = subject_info
                    self.logger.debug(f"Processed subject: {subject_info.code}")
            except Exception as e:
                self.logger.warning(f"Failed to process row {i} on page {page_number}: {e}")
                continue
        
        return page_data
    
    def _navigate_to_page(self, page_number: int):
        """Navigate to a specific page number."""
        # Check if already on the target page
        try:
            active_page = self.scraper.wait_for_element_to_be_visible(
                (By.XPATH, BedeliasConfig.ACTIVE_PAGE_XPATH), timeout=5
            )
            if active_page.get_attribute("aria-label") == f"Page {page_number}":
                return  # Already on correct page
        except ElementNotFoundError:
            pass  # Continue with navigation
        
        # Navigate to page
        if page_number > 10:
            # For high page numbers, go to last page first
            last_button = self.scraper.wait_for_element_to_be_clickable(
                (By.XPATH, BedeliasConfig.PAGINATOR_LAST_XPATH), timeout=10
            )
            self.scraper.scroll_to_element_and_click(last_button)
            self.scraper.wait_for_page_to_load()
        
        # Click specific page
        page_xpath = BedeliasConfig.PAGE_LINK_XPATH_TEMPLATE.format(page=page_number)
        page_link = self.scraper.wait_for_element_to_be_clickable(
            (By.XPATH, page_xpath), timeout=10
        )
        self.scraper.scroll_to_element_and_click(page_link)
        self.scraper.wait_for_page_to_load()
    
    @retry_on_exception(max_retries=2, delay=1.0)
    def _process_subject_row(self, page_number: int, row_index: int) -> Optional[SubjectInfo]:
        """Process a single subject row."""
        # Ensure we're on correct page
        self._navigate_to_page(page_number)
        
        # Get rows and validate index
        rows = self.scraper.wait_for_all_elements_to_be_visible(
            (By.XPATH, BedeliasConfig.DATA_ROW_XPATH), timeout=10
        )
        
        if row_index >= len(rows):
            self.logger.warning(f"Row index {row_index} out of range")
            return None
        
        row = rows[row_index]
        cells = row.find_elements(By.TAG_NAME, "td")
        
        if len(cells) < 3:
            raise ValueError("Insufficient cells in row")
        
        # Extract basic subject info
        subject_info = SubjectInfo(
            code=cells[0].text.strip() if cells[0].text else "",
            name=cells[1].text.strip() if cells[1].text else ""
        )
        
        if not subject_info.code:
            return None
        
        # Extract requirements
        more_info_link = cells[2].find_element(By.TAG_NAME, "a")
        self.scraper.scroll_to_element_and_click(more_info_link)
        
        # Wait for requirements dialog
        self.scraper.wait_for_element_to_be_visible(
            (By.XPATH, BedeliasConfig.REQUIREMENTS_DIALOG_XPATH), timeout=10
        )
        
        # Process requirements using composed component
        self.requirements_processor.expand_all_requirements(self.scraper)
        subject_info.requirements = self.requirements_processor.extract_requirements(self.scraper)
        
        # Return to main list
        back_button = self.scraper.driver.find_element(By.XPATH, BedeliasConfig.BACK_BUTTON_XPATH)
        self.scraper.scroll_to_element_and_click(back_button)
        
        return subject_info
    
    # ========================================
    # DATA PERSISTENCE
    # ========================================
    
    def _save_backup_data(self, data: Dict[str, SubjectInfo]):
        """Save extracted data as backup JSON file."""
        try:
            serializable_data = {
                code: subject.to_dict() for code, subject in data.items()
            }
            
            with open(BedeliasConfig.BACKUP_FILENAME, "w", encoding="utf-8") as fp:
                json.dump(serializable_data, fp, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Backup saved: {BedeliasConfig.BACKUP_FILENAME}")
            self.logger.info(f"Total subjects processed: {len(data)}")
            
        except Exception as e:
            self.logger.error(f"Error saving backup: {e}")
            if self.debug:
                traceback.print_exc()
            raise ScraperError(f"Failed to save data: {e}") from e
