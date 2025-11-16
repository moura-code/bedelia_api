import os
import sys
from typing import Optional
import re
import json
from time import sleep
from selenium.webdriver.common.by import By
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.navigation import PlanSection
from scraper import Scraper


class Credits(Scraper, PlanSection):
    """Placeholder page object responsible for extracting course credits."""

    def __init__(self, driver, wait, browser: str = "firefox", debug: bool = False, home_url: Optional[str] = None):
        Scraper.__init__(self, driver, wait, browser, debug)
        url = f"{home_url}views/public/desktop/consultaOfertaAcademica/consultaOfertaAcademica01.xhtml?cid=6"
        PlanSection.__init__(self, url)
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
                    log_message=f"Starting to extract credits data for {plan} {year}",
                    plan_name=plan,
                    plan_year=year,
                )
                
                click_button = self.try_find_element((By.XPATH, '//td[@class="ui-selection-column selectionMode"]'))
                if click_button:
                    self.scroll_to_element_and_click(click_button)
                    self.wait_loading_to_finish()
                
                items = {}
                self.logger.info("Open all nodes")

                while self.try_find_element((By.XPATH, '//*[@class="ui-tree-toggler ui-icon ui-icon-triangle-1-e"]')):
                    try:
                        self.scroll_to_element_and_click(self.driver.find_element(By.XPATH, '//*[@class="ui-tree-toggler ui-icon ui-icon-triangle-1-e"]'))
                    except Exception as e:
                        continue

                self.logger.info("Searching for course materials...")
                materia_elements = self.driver.find_elements(By.XPATH, '//*[@data-nodetype="Materia"]')
                self.logger.info(f"Found {len(materia_elements)} course materials to process")
                
                for idx, li in enumerate(materia_elements, 1):
                        self.logger.debug(f"Processing material {idx}/{len(materia_elements)}")
                        # Get the span that holds the line "CODE - NAME - whatever"
                        span = li.find_element(By.XPATH, './/td/span[@title="Código - Nombre - Créd.aportado"]')
                        raw = span.text
                        self.logger.debug(f"Raw material text: {raw}")

                        # Parse format: "CODE - NAME - créditos: X" or "CODE-WITH-HYPHEN - NAME - créditos: X"
                        # We need to handle codes that may contain hyphens (e.g., "FF1-7")
                        
                        # First, extract credits (always at the end with "créditos: ")
                        creditos_match = re.search(r'créditos:\s*(\S+)', raw, re.IGNORECASE)
                        if not creditos_match:
                            self.logger.warning(f"Could not find 'créditos:' in material: {raw}")
                            continue
                        
                        creditos = creditos_match.group(1).strip()
                        
                        # Remove the credits part to get code and name
                        raw_without_creditos = re.sub(r'\s*-\s*créditos:\s*\S+.*$', '', raw, flags=re.IGNORECASE).strip()
                        
                        # Now split the remaining text by the first " - " (space-hyphen-space)
                        # This handles codes with hyphens correctly
                        parts = re.split(r'\s+-\s+', raw_without_creditos, maxsplit=1)
                        
                        if len(parts) == 2:
                            codigo, nombre = [p.strip() for p in parts]
                        elif len(parts) == 1:
                            # Fallback: if no " - " separator, try to split by any hyphen
                            # This handles edge cases where format might be slightly different
                            parts_fallback = raw_without_creditos.split('-', 1)
                            if len(parts_fallback) == 2:
                                codigo, nombre = [p.strip() for p in parts_fallback]
                            else:
                                self.logger.warning(f"Unexpected format for material (no separator found): {raw}")
                                continue
                        else:
                            self.logger.warning(f"Unexpected format for material: {raw}")
                            continue
                        
                        item = {
                            "codigo": codigo,
                            "nombre": nombre,
                            "creditos": creditos,
                        }
                        
                        items[f"{codigo}_{nombre}"] = item
                        self.logger.debug(f"Processed material: {codigo} - {nombre}")
                
                # Successfully processed the plan
                self.logger.info(f"Successfully processed {len(items)} course materials for plan {plan} {year}")
                return items
                
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
        """Navigate to the credits section and trigger extraction logic."""
        backup_file = "../data/credits_data_backup.json"
        
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
        
        self.logger.info(f"Credits extraction completed! Processed {len(all_plans_data)} plans total")
        self.logger.info(f"Final data saved to {backup_file}")



