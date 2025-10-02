import os
import sys
from typing import Optional
import re
import json
from selenium.webdriver.common.by import By
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.navigation import PlanSection
from scraper import Scraper


class Credits(Scraper, PlanSection):
    """Placeholder page object responsible for extracting course credits."""

    def __init__(self, driver, wait, browser: str = "firefox", debug: bool = False, home_url: Optional[str] = None, plan_name: str = "INGENIERIA EN COMPUTACION"):
        Scraper.__init__(self, driver, wait, browser, debug)
        PlanSection.__init__(self, plan_name)
        self.home_url = home_url

    def run(self):
        """Navigate to the credits section and trigger extraction logic."""
        self.logger.info("Starting credits data extraction...")
        
        self.open_plan_section(
            self,
            log_message="Navigating to credits section...",
        )

        items = []
        try:
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
                try:
                    self.logger.debug(f"Processing material {idx}/{len(materia_elements)}")
                    
                    # Get the span that holds the line "CODE - NAME - whatever"
                    span = li.find_element(By.XPATH, './/td/span[@title="Código - Nombre - Créd.aportado"]')
                    raw = span.text
                    self.logger.debug(f"Raw material text: {raw}")

                    # Split by hyphen into exactly 3 parts: [codigo, nombre, tail]
                    parts = re.split(r"\s*-\s*", raw, maxsplit=2)
                    if len(parts) < 3:
                        # If something odd, pad to always have 3 fields
                        self.logger.warning(f"Unexpected format for material: {raw}")
                        continue

                    codigo, nombre, creditos = [p.strip() for p in parts]
                    creditos = creditos.replace("créditos: ", "")
                    
                    item = {
                        "codigo": codigo,
                        "nombre": nombre,
                        "creditos": creditos,        # e.g., "créditos: 12" — left intact on purpose
                    }
                    
                    items.append(item)
                    self.logger.debug(f"Processed material: {codigo} - {nombre}")
                    
                except Exception as e:
                    self.logger.error(f"Error processing material {idx}: {e}")
                    self.logger.debug(f"Raw material data: {li.get_attribute('outerHTML')[:200]}...")
                    continue
            
            self.logger.info(f"Successfully processed {len(items)} course materials")

        except Exception as e:
            self.logger.error(f"Error during credits extraction: {e}")
            raise
        finally:
            # save to JSON as backup
            backup_file = "credits_data_backup.json"
            try:
                with open(backup_file, "w", encoding="utf-8") as fp:
                    json.dump(items, fp, ensure_ascii=False, indent=2)
                self.logger.info(f"Backup saved to {backup_file} with {len(items)} items")
            except Exception as e:
                self.logger.error(f"Failed to save backup file {backup_file}: {e}")



