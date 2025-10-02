from __future__ import annotations

from time import sleep
from typing import Any

from selenium.webdriver.common.by import By


class PlanSection:

    def __init__(self, plan_name: str = "INGENIERIA EN COMPUTACION"):
        self.plan_name = plan_name

    def open_plan_section(self, *, log_message: str) -> None:
        """Navigate to the previas listing shared by previas and credits pages."""
        home_url = getattr(self, "home_url", None)
        if not home_url:
            raise ValueError("home_url must be set on the page object before navigation")
    
        self.logger.info(log_message)
        self.driver.get(home_url)
    
        self.wait_for_page_to_load()
    
        self.hover_by_text("PLANES DE ESTUDIO")
        self.wait_for_element_to_be_clickable((By.LINK_TEXT, "Planes de estudio / Previas")).click()
    
        # TODO replace sleep with an explicit wait for the modal to disappear when feasible.
        sleep(0.5)
        self.wait_for_element_to_be_clickable((By.XPATH, f'//*[text()= "TECNOLOGÍA Y CIENCIAS DE LA NATURALEZA"]')).click()
        self.wait_for_element_to_be_clickable((By.XPATH, '//*[text()= "FING - FACULTAD DE INGENIER\u00cdA"]')).click()
    
        filter_input = self.wait_for_element_to_be_clickable(
            (By.XPATH, "//span[contains(@class,'ui-column-title')]/following-sibling::input[1]")
        )
        filter_input.clear()
        filter_input.send_keys(self.plan_name)
    
        self.wait_for_element_to_be_clickable(
            (By.XPATH, f'//*[text()="{self.plan_name}"]/preceding-sibling::td[1]')
        ).click()
    
        self.wait_for_element_to_be_clickable((By.XPATH, '//i[@class="pi  pi-info-circle"]')).click()
