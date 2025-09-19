import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraper import Scraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from time import sleep

class LoginPage(Scraper):
    
    def __init__(self, driver, wait, browser: str = "firefox", debug: bool = False, username: str = None, password: str = None, login_url: str = None, home_url: str = None):
        super().__init__(driver, wait, browser, debug)
        self.username = username
        self.password = password
        self.login_url = login_url
        self.home_url = home_url

    def run(self):
        """Login to Bedelías and navigate to the main interface."""
        self.logger.info("Starting login process...")
        self.driver.get(self.login_url)

        username_field = self.wait.until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        username_field.send_keys(self.username)

        password_field = self.driver.find_element(By.ID, "password")
        password_field.send_keys(self.password)

        self.wait.until(
            EC.element_to_be_clickable((By.NAME, "_eventId_proceed"))
        ).click()
        sleep(0.5)

        # Wait for a known menu link to indicate post-login
        self.wait.until(
            EC.presence_of_element_located((By.LINK_TEXT, "PLANES DE ESTUDIO"))
        )
        self.logger.info("Login successful")