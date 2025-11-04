from __future__ import annotations

from functools import total_ordering
from time import sleep
from typing import Any

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from .usetable import UseTable

class PlanSection(UseTable):

    def __init__(self, link):
        self.link = link
        super().__init__()


    def open_faculty(self):
        self.driver.get(self.link)
        while self.try_find_element((By.XPATH, f'//span[@class="tituloNoticia"]')):
            self.driver.get(self.link)
            print("Retrying...")
            sleep(0.1)
        self.wait_loading_to_finish()
        
        # Wait for modal to disappear        
        self.wait_for_element_to_be_clickable((By.XPATH, f'//*[text()= "TECNOLOGÍA Y CIENCIAS DE LA NATURALEZA"]')).click()
        sleep(1)
        self.scroll_to_element_and_click(self.wait_for_element_to_be_clickable((By.XPATH, '//*[text()= "FING - FACULTAD DE INGENIER\u00cdA"]')))
    
    def get_total_plan_sections(self):
        self.open_faculty()
        self.get_total_pages()
        plans_data = []
        for current_page in range(1, self.total_pages + 1):
            self.go_to_page(current_page)
            rows_len = len(
                [row for row in self.driver.find_elements(
                    By.XPATH, 
                    '//tr[contains(@class, "ui-datatable-even") or contains(@class, "ui-datatable-odd")]'
                ) if row.is_displayed()]
            )
            self.logger.info(f"Rows length: {rows_len}")
            
            number_planes_div = 0
            for i in range(rows_len):
                self.go_to_page(current_page)
                rows = [row for row in self.driver.find_elements(
                    By.XPATH, 
                    '//tr[contains(@class, "ui-datatable-even") or contains(@class, "ui-datatable-odd")]'
                ) if row.is_displayed()]
                row = rows[i]
                # Wait for modal to disappear before clicking
                if row.find_element(By.XPATH, "./td[3]").text.strip() != "Grado":
                    self.logger.info(f"Skipping row {i} because it is not a Grado")
                    continue
                
                toggler = row.find_element(
                    By.XPATH, 
                    "./td[1]"
                )
                
                self.scroll_to_element_and_click(toggler)
                self.wait.until(
                    lambda d: len(d.find_elements(By.XPATH, '//div[contains(@class, "ui-datatable ui-widget tablanivel2")]')) > number_planes_div
                )
                planes_div_list = self.driver.find_elements(By.XPATH, '//div[contains(@class, "ui-datatable ui-widget tablanivel2")]')
                
                planes_div = planes_div_list[-1]
                
                # Extract vigent plans
                tbody = planes_div.find_element(By.CLASS_NAME, "ui-datatable-data")
                plan_rows = tbody.find_elements(By.TAG_NAME, "tr")
                for plan_row in plan_rows:
                    cells = plan_row.find_elements(By.TAG_NAME, "td")
                    year = cells[0].text.strip()
                    plan_name = row.find_element(By.XPATH, "./td[2]").text.strip()
                    vigente = cells[2].get_attribute("innerHTML").strip()
                    if vigente.lower() in ["sí", "si"]:
                        plans_data.append((plan_name, year))
                
                if plans_data:
                    self.logger.info(f"Found {len(plans_data)} vigent plan(s):")
                number_planes_div += 1
                self.scroll_to_element_and_click(toggler)
   
        return plans_data
    
    def open_plan_section(self, *, log_message: str, plan_name: str, plan_year: str) -> None:
        """Navigate to the previas listing shared by previas and credits pages."""
        self.logger.info(log_message)
        self.open_faculty()
        
    
        filter_input = self.wait_for_element_to_be_clickable(
            (By.XPATH, "//span[contains(@class,'ui-column-title')]/following-sibling::input[1]")
        )
        filter_input.clear()
        filter_input.send_keys(plan_name)
    
        self.scroll_to_element_and_click(self.wait_for_element_to_be_clickable(
            (By.XPATH, f'//*[text()="{plan_name}"]/preceding-sibling::td[1]')
        ))
        
        # Click on the info icon for the row that has both the matching year AND "Si" in vigente
        xpath = f'//tr[td[1][text()="{plan_year}"]][td[3][text()="Si"]]//i[contains(@class, "pi-info-circle") or contains(@class, "pi-calendar")]'
        self.logger.info(f"Clicking plan: year={plan_year}, vigente=Si")
        self.scroll_to_element_and_click(self.wait_for_element_to_be_clickable((By.XPATH, xpath)))
