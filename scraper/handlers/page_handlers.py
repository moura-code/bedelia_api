"""
Page-specific handlers for Bedelías website interactions.
Contains methods that are specific to particular pages or workflows.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
import logging
from typing import TYPE_CHECKING

from ..config import BedeliasConfig

if TYPE_CHECKING:
    from ..core.base_scraper import BaseScraper


class PageHandlers:
    """Mixin class containing page-specific interaction handlers."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    # ========================================
    # AUTHENTICATION PAGE HANDLERS
    # ========================================

    def handle_login_page(self: 'BaseScraper', username: str, password: str):
        """
        Handle the login page workflow.
        
        Args:
            username: User's document number
            password: User's password
        """
        self.logger.info("Handling login page...")
        
        # Navigate to login URL
        self.driver.get(BedeliasConfig.LOGIN_URL)
        
        # Fill username
        username_field = self.wait.until(
            EC.presence_of_element_located((By.ID, BedeliasConfig.USERNAME_FIELD_ID))
        )
        username_field.send_keys(username)
        
        # Fill password
        password_field = self.driver.find_element(By.ID, BedeliasConfig.PASSWORD_FIELD_ID)
        password_field.send_keys(password)
        
        # Click login button
        self.wait.until(
            EC.element_to_be_clickable((By.NAME, BedeliasConfig.LOGIN_BUTTON_NAME))
        ).click()
        
        sleep(0.5)  # Brief pause for login processing
        
        # Verify login success by waiting for menu
        self.wait.until(
            EC.presence_of_element_located((By.LINK_TEXT, BedeliasConfig.STUDY_PLANS_MENU_TEXT))
        )
        self.logger.info("Login successful")

    def login_and_navigate(self: 'BaseScraper', username: str, password: str):
        """
        Complete login workflow and navigate to home page.
        
        Args:
            username: User's document number
            password: User's password
        """
        self.handle_login_page(username, password)
        
        # Navigate to home after login
        self.driver.get(BedeliasConfig.HOME_URL)
        self.wait_for_page_to_load()
        self.logger.info("Navigation completed")

    # ========================================
    # FACULTY SELECTION PAGE HANDLERS
    # ========================================

    def handle_faculty_selection_page(self: 'BaseScraper'):
        """Handle the faculty and program selection workflow."""
        self.logger.info("Handling faculty selection...")
        
        # Navigate to study plans section
        self.hover_by_text(BedeliasConfig.STUDY_PLANS_MENU_TEXT)
        self.wait_for_element_to_be_clickable(
            (By.LINK_TEXT, BedeliasConfig.PREREQUISITES_LINK_TEXT)
        ).click()
        
        # Wait for modal to appear
        sleep(0.5)  # Brief pause for modal animation
        
        # Select Technology faculty
        self.wait_for_element_to_be_clickable(
            (By.XPATH, f'//*[text()= "{BedeliasConfig.TECHNOLOGY_FACULTY_TEXT}"]')
        ).click()
        
        # Select FING faculty
        self.wait_for_element_to_be_clickable(
            (By.XPATH, f'//*[text()= "{BedeliasConfig.FING_FACULTY_TEXT}"]')
        ).click()
        
        self.logger.info("Faculty selection completed")

    def select_computer_engineering_program(self: 'BaseScraper'):
        """Select Computer Engineering program specifically."""
        self.logger.info("Selecting Computer Engineering program...")
        
        # Use search filter
        search_input = self.wait_for_element_to_be_clickable(
            (By.XPATH, BedeliasConfig.COLUMN_FILTER_XPATH)
        )
        search_input.send_keys(BedeliasConfig.COMPUTER_ENGINEERING_TEXT)
        
        # Select the program
        self.wait_for_element_to_be_clickable(
            (By.XPATH, BedeliasConfig.SUBJECT_SELECT_XPATH)
        ).click()
        
        self.logger.info("Computer Engineering program selected")

    def setup_prerequisites_system(self: 'BaseScraper'):
        """Setup access to prerequisites system."""
        self.logger.info("Setting up prerequisites system access...")
        
        # Click info button
        self.wait_for_element_to_be_clickable(
            (By.XPATH, BedeliasConfig.INFO_BUTTON_XPATH)
        ).click()
        
        self.logger.info("Clicking sistema de previaturas")
        # Click prerequisites system
        self.wait_for_element_to_be_clickable(
            (By.XPATH, f'//span[text()="{BedeliasConfig.PREREQUISITES_SYSTEM_SPAN_TEXT}"]')
        ).click()
        
        sleep(2)  # Wait for system to load
        self.logger.info("Prerequisites system setup completed")

    # ========================================
    # COMPLETE NAVIGATION WORKFLOW
    # ========================================

    def navigate_to_prerequisites_page(self: 'BaseScraper'):
        """Complete navigation workflow to prerequisites page."""
        self.handle_faculty_selection_page()
        self.select_computer_engineering_program()
        self.setup_prerequisites_system()
