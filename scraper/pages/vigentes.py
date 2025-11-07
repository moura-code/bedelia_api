from re import DEBUG
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from selenium.webdriver.common.by import By
from time import sleep
import json
from scraper import Scraper
from common.navigation import PlanSection
import traceback

class Vigentes(Scraper, PlanSection):

    def __init__(self, driver, wait, browser: str = "firefox", debug: bool = False, home_url: str = None):
        Scraper.__init__(self, driver, wait, browser, debug)
       
        self.home_url = home_url
        url = f"{home_url}views/public/desktop/consultarCalendario/consultarCalendario01.xhtml?cid=1"
        PlanSection.__init__(self, url)
    
    def _load_backup_data(self, backup_file: str) -> dict:
        """Load existing backup data if available."""
        if os.path.exists(backup_file):
            try:
                with open(backup_file, "r", encoding="utf-8") as fp:
                    return json.load(fp)
            except json.JSONDecodeError:
                self.logger.warning(f"Backup file {backup_file} is corrupted, starting fresh")
                return {}
        return {}
    
    def _save_backup_data(self, backup_file: str, data: dict):
        """Save data to backup file."""
        with open(backup_file, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
        self.logger.info(f"Backup saved to {backup_file}")
       
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
        print(text)
        print(parts)
        raise Exception("Course text not found")
    
    def process_table(self):
        numero = self.get_total_pages()
        
        # List to store all course data
        courses_data = {}
        
        for current_page in range(1, numero + 1):
            self.logger.debug(f"Processing page {current_page}/{numero}")
            self.go_to_page(current_page)
            sleep(0.5)
            rows = self.wait_for_all_elements_to_be_visible(
                (By.XPATH, '//tr[contains(@class, "ui-datatable-even") or contains(@class, "ui-datatable-odd")]'))
            
            for i in range(len(rows)):
                row = self.wait_for_all_elements_to_be_visible(
                    (By.XPATH, '//tr[contains(@class, "ui-datatable-even") or contains(@class, "ui-datatable-odd")]')
                )[i]
                course_info = self.parse_course_text(row.text)
                courses_data[course_info["course_code"]] = course_info
        
        return courses_data

    def _process_plan_with_retry(self, plan: str, year: str, max_retries: int = 3) -> list:
        """
        Process a single plan with retry logic for Selenium errors.
        Returns the extracted course data for this plan.
        """
        retry_count = 0
        last_exception = None
        
        while retry_count < max_retries:
            try:
                self.logger.info(f"Processing plan {plan} {year} (attempt {retry_count + 1}/{max_retries})")
                
                # Navigate to the plan section
                self.open_plan_section(
                    log_message=f"Starting to extract materias vigentes for {plan} {year}",
                    plan_name=plan,
                    plan_year=year,
                )
                self.logger.info("Sacando instancias de dictado con período disponible")
                
                data_disponibles = {}
                if not self.try_find_element((By.XPATH, '//td[text()= "No existen instancias de evaluación con período de inscripción/desistimiento habilitado."]')):
                    data_disponibles = self.process_table()
                self.remove_element(self.driver.find_element(By.XPATH, '//div[@id="accordDict:tabDictH_header"]'))
                self.remove_element(self.driver.find_element(By.XPATH, '//div[@id="accordDict:tabDictH"]'))
                self.logger.info("Sacando instancias de dictado con período finalizado")
                self.wait_for_element_to_be_clickable((By.XPATH, '//div[contains(text(), "Instancias de dictado con período finalizado")]')).click()
                sleep(1)
             
                data_finalizadas = self.process_table()
                
                combined_data = {**data_disponibles, **data_finalizadas}
                return combined_data
            except Exception as e:
                last_exception = e
                retry_count += 1
                self.logger.error(f"Error processing plan {plan} {year} (attempt {retry_count}/{max_retries}): {e}")
                traceback.print_exc()
                
                # Check if we returned to main page
                if self.try_find_element((By.XPATH, '//span[@class="tituloNoticia"]')):
                    self.logger.info("Returned to main page, will retry")
                
                if retry_count < max_retries:
                    self.logger.info(f"Retrying plan {plan} {year}...")
                    sleep(2)  # Wait before retrying
                else:
                    self.logger.error(f"Failed to process plan {plan} {year} after {max_retries} attempts")
                    raise last_exception
        
        raise last_exception
        
    # TODO: Essa pagina nao esta consistente, da muito erro as veses
    def run(self):
        """Extract prerequisite (materias vigentes) data and store in database."""
        backup_file = "../../data/vigentes_data_backup.json"
        
        # Load existing backup data
        all_plans_data = self._load_backup_data(backup_file)
        self.logger.info(f"Loaded {len(all_plans_data)} plans from backup")
        
        # Get all available plans
        plans_data = self.get_total_plan_sections()
        self.logger.info(f"Total plans available: {len(plans_data)}")
        
        # Process each plan
        for j in range(len(plans_data)):
            plan, year = plans_data[j]
            plan_key = f"{plan}_{year}"
            
            # Skip if already processed
            if plan_key in all_plans_data:
                self.logger.info(f"Skipping already processed plan: {plan_key}")
                continue
            
            try:
                # Process plan with retry logic
                plan_data = self._process_plan_with_retry(plan, year, max_retries=3)
                
                # Save data for this plan
                all_plans_data[plan_key] = plan_data
                
                # Save backup after each successful plan
                self._save_backup_data(backup_file, all_plans_data)
                self.logger.info(f"✓ Completed and saved plan {j+1}/{len(plans_data)}: {plan_key}")
                
            except Exception as e:
                self.logger.error(f"✗ Failed to process plan {plan_key} after all retries: {e}")
                # Continue with next plan instead of crashing
                continue
        
        self.logger.info(f"Vigentes extraction completed! Processed {len(all_plans_data)} plans total")
        self.logger.info(f"Final data saved to {backup_file}")
