import sys
import os

from common.navigation import PlanSection
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraper import Scraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
import json

class PosPrevias(Scraper, PlanSection):
    
    def __init__(self, driver, wait, browser: str = "firefox", debug: bool = False, home_url: str = None):
        Scraper.__init__(self, driver, wait, browser, debug)
        link =  f"{home_url}/views/public/desktop/consultarDeQueEsPrevia/consultarDeQueEsPrevia01.xhtml?cid=1"
        PlanSection.__init__(self, link)
        self.home_url = home_url
    
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
    
    def _process_plan_with_retry(self, plan: str, year: str, max_retries: int = 3) -> dict:
        """
        Process a single plan with retry logic for Selenium errors.
        Returns the extracted data for this plan.
        """
        retry_count = 0
        last_exception = None
        
        while retry_count < max_retries:
            try:
                self.logger.info(f"Processing plan {plan} {year} (attempt {retry_count + 1}/{max_retries})")
                
                # Navigate to the plan section
                self.open_plan_section(
                    log_message=f"Starting to extract posprevias data for {plan} {year}",
                    plan_name=plan,
                    plan_year=year,
                )
                
                # Get total pages
                self.get_total_pages()
                
                data = {}
                current_page = 1
                
                # Extract posprevias data for all pages
                while current_page <= self.total_pages:
                    self.logger.info(f"Processing posprevias page {current_page}/{self.total_pages}")
                    self.go_to_page(current_page)
                    
                    # Use updated XPATH to get both even and odd rows
                    rows_len = len(
                        self.driver.find_elements(
                            By.XPATH, '//tr[contains(@class, "ui-datatable-even") or contains(@class, "ui-datatable-odd")]'
                        )
                    )
                    
                    self.logger.info(f"Rows length: {rows_len}")
                    i = 0
                    
                    while i < rows_len:
                        self.go_to_page(current_page)
                        sleep(1)
                        
                        # Re-find rows to avoid stale element references
                        rows = self.wait_for_all_elements_to_be_visible(
                            (
                                By.XPATH,
                                '//tr[contains(@class, "ui-datatable-even") or contains(@class, "ui-datatable-odd")]',
                            )
                        )
                        
                        row = rows[i]
                        
                        # Extract row data with retry
                        max_cell_retries = 5
                        cell_retry = 0
                        codigo = ""
                        nombre = ""
                        
                        while cell_retry < max_cell_retries:
                            try:
                                codigo = row.find_element(By.XPATH, "./td[1]").text.strip()
                                nombre = row.find_element(By.XPATH, "./td[2]").text.strip()
                                break
                            except Exception as cell_error:
                                cell_retry += 1
                                if cell_retry >= max_cell_retries:
                                    raise cell_error
                                row = rows[i]
                                sleep(0.1)
                        
                        self.logger.info(f"Processing {codigo} - {nombre}")
                        data[codigo] = {
                            "code": codigo,
                            "name": nombre,
                            "posprevias": [],
                        }
                        
                        sleep(1)
                        
                        # Re-find info icons
                        info_icons = self.wait_for_all_elements_to_be_visible(
                            (
                                By.XPATH,
                                '//i[@class="pi  pi-info-circle"]',
                            )
                        )
                        self.scroll_to_element_and_click(info_icons[i])
                        
                        self.logger.info("Waiting for loading to finish")
                        self.wait_loading_to_finish()
                        
                        # Try checking if there are previaturas
                        xpath_icon = (
                            "//div[contains(@id,':nombServicio')]"
                            "[contains(normalize-space(.), 'FACULTAD DE INGENIERÍA')]"
                            "//div[contains(@class,'ui-accordion-header')][1]"
                            "//span[contains(@class,'ui-icon')]"
                        )
                        
                        if self.try_find_element((By.XPATH, xpath_icon), 0.5):
                            self.wait_for_page_to_load()
                            self.scroll_to_element_and_click(
                                self.wait_for_element_to_be_clickable((By.XPATH, xpath_icon))
                            )
                            
                            outer_tbody = self.try_find_element(
                                (By.XPATH, "//div[contains(@id,':nombServicio')][contains(normalize-space(.), 'FACULTAD DE INGENIERÍA')]//tbody[contains(@id,':previaturasPlanes_data')]"), 
                                0.1
                            )
                            
                            if outer_tbody is not None:
                                results = []
                                
                                def _txt(el):
                                    return (el.get_attribute("textContent") or "").strip()
                                
                                # Get all rows from the outer table (excluding empty message rows)
                                plan_rows = outer_tbody.find_elements(
                                    By.XPATH, "./tr[not(contains(@class,'ui-datatable-empty-message'))]"
                                )
                                
                                for prow in plan_rows:
                                    # Get the 5 tds: Año | Denominación | Fecha | Descripción | (nested table)
                                    tds = prow.find_elements(By.XPATH, "./td")
                                    
                                    if len(tds) < 5:
                                        continue
                                    
                                    anio_plan = _txt(tds[0])
                                    carrera = _txt(tds[1])
                                    fecha = _txt(tds[2])
                                    descripcion = _txt(tds[3])
                                    
                                    # The 5th td contains the nested datatable
                                    nested_table_container = tds[4]
                                    
                                    # Find the nested tbody within this td
                                    try:
                                        nested_tbody = nested_table_container.find_element(
                                            By.XPATH, ".//tbody[contains(@class,'ui-datatable-data')]"
                                        )
                                    except:
                                        continue
                                    
                                    inner_rows = nested_tbody.find_elements(By.XPATH, "./tr")
                                    for irow in inner_rows:
                                        tds_in = irow.find_elements(By.XPATH, "./td")
                                        
                                        if len(tds_in) < 2:
                                            continue
                                        
                                        tipo = _txt(tds_in[0])
                                        
                                        # Prefer the <span title="CODE-NAME"> if present (more reliable)
                                        span_candidates = tds_in[1].find_elements(By.XPATH, ".//span[@title]")
                                        if span_candidates:
                                            materia_full = span_candidates[0].get_attribute("title").strip()
                                        else:
                                            materia_full = _txt(tds_in[1])
                                        
                                        # Split "1945-PRACTICA ..." into código & nombre (safe even if dash missing)
                                        if "-" in materia_full:
                                            materia_codigo, materia_nombre = [s.strip() for s in materia_full.split("-", 1)]
                                        else:
                                            materia_codigo, materia_nombre = materia_full.strip(), ""
                                        
                                        results.append({
                                            "anio_plan": anio_plan,
                                            "carrera": carrera,
                                            "fecha": fecha,
                                            "descripcion": descripcion,
                                            "tipo": tipo,  # 'Curso' or 'Examen'
                                            "materia_codigo": materia_codigo,
                                            "materia_nombre": materia_nombre,
                                            "materia_full": materia_full,
                                        })
                                
                                data[codigo]["posprevias"] = results
                                self.logger.info(f"Extracted {len(results)} posprevias for {codigo}")
                        
                        # Scroll to bottom and click Volver
                        self.scroll_to_bottom()
                        self.scroll_to_element_and_click(
                            self.driver.find_element(
                                By.XPATH, "//span[normalize-space(.)='Volver']"
                            )
                        )
                        self.wait_for_page_to_load()
                        
                        i += 1
                    
                    current_page += 1
                
                # Successfully processed the plan
                self.logger.info(f"Successfully processed plan {plan} {year}")
                return data
                
            except Exception as e:
                last_exception = e
                retry_count += 1
                self.logger.error(f"Error processing plan {plan} {year} (attempt {retry_count}/{max_retries}): {e}")
                
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
    
    def run(self):
        """Extract posprevias data and store with incremental backup."""
        backup_file = "posprevias_data_backup.json"
        
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
        
        self.logger.info(f"PosPrevias extraction completed! Processed {len(all_plans_data)} plans total")
        self.logger.info(f"Final data saved to {backup_file}")
