import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from selenium.webdriver.common.by import By
from time import sleep
import json
from scraper import Scraper
from common.navigation import PlanSection


class Vigentes(Scraper, PlanSection):

    def __init__(self, driver, wait, browser: str = "firefox", debug: bool = False, home_url: str = None, plan_name: str = "INGENIERÍA EN COMPUTACIÓN"):
        Scraper.__init__(self, driver, wait, browser, debug)
       
        self.home_url = home_url
        url = f"{home_url}views/public/desktop/consultarCalendario/consultarCalendario01.xhtml?cid=1"
        PlanSection.__init__(self, url, plan_name)
       
    def parse_course_text(self, text: str) -> dict:
        """Parse course text like 'FING - 5707 IMAGENES MEDICAS: ADQUISICION, INSTRUMENTACION Y GESTION'"""
        # Split by ' - ' to separate university, code, and name
        parts = text.split(' - ', 2)
        
        if len(parts) >= 2:
            university_code = parts[0].strip()
            
            # Extract course code and name from the second part
            remaining = parts[1].strip()
            # Find the first space to separate code from name
            space_index = remaining.find(' ')
            if space_index > 0:
                course_code = remaining[:space_index].strip()
                course_name = remaining[space_index:].strip()
            else:
                course_code = remaining
                course_name = ""
            
            return {
                'university_code': university_code,
                'course_code': course_code,
                'course_name': course_name,
            }
        
        return {
            'university_code': '',
            'course_code': '',
            'course_name': '',
        }
        
        
    # TODO: Essa pagina nao esta consistente, da muito erro as veces
    def run(self):
        """Extract prerequisite (materias vigentes) data and store in database."""
        self.open_plan_section(
            log_message="Starting to extract materias vigentes",
        )
        self.logger.info("Clicking sistema de previaturas")
        self.wait_for_element_to_be_clickable((By.XPATH, '//div[contains(text(), "Instancias de dictado con período finalizado")]')).click()
        sleep(1)
        numero = self.get_total_pages()
        
        # List to store all course data
        courses_data = []
        
        for current_page in range(1, numero + 1):
            self.go_to_page(current_page)
            sleep(0.5)
            rows = self.wait_for_all_elements_to_be_visible(
                (By.XPATH, '//tr[contains(@class, "ui-datatable-even") or contains(@class, "ui-datatable-odd")]')
            )
            
            for i, row in enumerate(rows):
                try:
                    # Parse the row text and add to courses_data
                    course_info = self.parse_course_text(row.text)
                    courses_data.append(course_info)
                except Exception as e:
                    # If element becomes stale, re-find it
                    self.logger.warning(f"Stale element on page {current_page}, row {i}, re-finding...")
                    rows = self.driver.find_elements(
                        By.XPATH, '//tr[contains(@class, "ui-datatable-even") or contains(@class, "ui-datatable-odd")]'
                    )
                    if i < len(rows):
                        course_info = self.parse_course_text(rows[i].text)
                        courses_data.append(course_info)
                    else:
                        self.logger.error(f"Could not re-find row {i} on page {current_page}")
              
        
        # Save to JSON file
        output_file = "../data/vigentes_courses.json"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(courses_data, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Saved {len(courses_data)} courses to {output_file}")
        except Exception as e:
            self.logger.error(f"Failed to save courses data: {e}")