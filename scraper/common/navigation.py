from __future__ import annotations

from time import sleep
from typing import Any

from selenium.webdriver.common.by import By


class PlanSection:

    def __init__(self, link, plan_name):
        self.plan_name = plan_name
        self.link = link

    def open_plan_section(self, *, log_message: str) -> None:
        """Navigate to the previas listing shared by previas and credits pages."""
    
        self.logger.info(log_message)
        self.driver.get(self.link)
        self.driver.get(self.link)
        
        # TODO replace sleep with an explicit wait for the modal to disappear when feasible.
        sleep(0.5)
        self.wait_for_element_to_be_clickable((By.XPATH, f'//*[text()= "TECNOLOGÍA Y CIENCIAS DE LA NATURALEZA"]')).click()
        self.scroll_to_element_and_click(self.wait_for_element_to_be_clickable((By.XPATH, '//*[text()= "FING - FACULTAD DE INGENIER\u00cdA"]')))
    
        filter_input = self.wait_for_element_to_be_clickable(
            (By.XPATH, "//span[contains(@class,'ui-column-title')]/following-sibling::input[1]")
        )
        filter_input.clear()
        filter_input.send_keys(self.plan_name)
    
        self.wait_for_element_to_be_clickable(
            (By.XPATH, f'//*[text()="{self.plan_name}"]/preceding-sibling::td[1]')
        ).click()
    
        self.wait_for_element_to_be_clickable((By.XPATH, '//tr[td[3][text()="Si"]]//i[contains(@class, "pi-info-circle") or contains(@class, "pi-calendar")]')).click()
