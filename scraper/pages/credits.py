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

    def __init__(self, driver, wait, browser: str = "firefox", debug: bool = False, home_url: Optional[str] = None):
        Scraper.__init__(self, driver, wait, browser, debug)
        url = f"{home_url}views/public/desktop/consultaOfertaAcademica/consultaOfertaAcademica02.xhtml?cid=1"
        PlanSection.__init__(self, url)
        self.home_url = home_url

    def run(self):
        """Navigate to the credits section and trigger extraction logic."""
        plans_data = self.get_total_plan_sections()
        data_plans = {}
        for plan, year in plans_data:
            self.open_plan_section(
                log_message=f"Starting to extract credits data for {plan} {year}",
                plan_name=plan,
                plan_year=year,
            )
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
                    
                    items[f"{codigo}_{nombre}"] = item
                    self.logger.debug(f"Processed material: {codigo} - {nombre}")
                    
            data_plans[f"{plan}_{year}"] = items
            self.logger.info(f"Successfully processed {len(items)} course materials")

        backup_file = "credits_data_backup.json"
        with open(backup_file, "w", encoding="utf-8") as fp:
            json.dump(data_plans, fp, ensure_ascii=False, indent=2)
        self.logger.info(f"Backup saved to {backup_file} with {len(items)} items")



