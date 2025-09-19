import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.usetable import UseTable
from scraper import Scraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
import json

class PosPrevias(Scraper, UseTable):
    
    def __init__(self, driver, wait, browser: str = "firefox", debug: bool = False, home_url: str = None):
        Scraper.__init__(self, driver, wait, browser, debug)
        UseTable.__init__(self)
        self.home_url = home_url
    
    def run(self):
         # Copiado de get previas
        self.logger.info("Starting to extract previas (prerequisites) data...")
        self.driver.get(self.home_url)
        
        self.wait_for_page_to_load()
        
        self.hover_by_text("PLANES DE ESTUDIO")
        self.wait_for_element_to_be_clickable((By.LINK_TEXT, "Consultar de qué es previa")).click()
        # <div id="j_idt22_modal" > sempre esta na frente TODO> remove esse sleep, talvez self.wait_for_element_to_be_visible((By.ID, "j_idt22_modal")) ou wait_page_to_load
        sleep(0.5)
        # Selecting fing
        self.wait_for_element_to_be_clickable((By.XPATH, '//*[text()= "TECNOLOGÍA Y CIENCIAS DE LA NATURALEZA"]')).click()
        self.scroll_to_element_and_click(self.wait_for_element_to_be_clickable((By.XPATH, '//*[text()= "FING - FACULTAD DE INGENIERÍA"]')))
        
        # Selecting INGENIERIA EN COMPUTACION
        
        self.wait_for_element_to_be_clickable((By.XPATH, "//span[contains(@class,'ui-column-title')]/following-sibling::input[1]")).send_keys("INGENIERIA EN COMPUTACION")
        self.wait_for_element_to_be_clickable((By.XPATH, '//*[text()="INGENIERIA EN COMPUTACION"]/preceding-sibling::td[1]')).click()
        # Expand and open info
        self.wait_for_element_to_be_clickable((By.XPATH, '//i[@class="pi  pi-info-circle"]')).click()
        self.get_total_pages()
        data = {}
        loading_path = "//img[@src='/jakarta.faces.resource/img/cargando.gif.xhtml?ln=default']"
        try:
            # Extract previas data
            #TODO: As vezes total_pages = 1
            for current_page in range(1, self.total_pages + 1):
                self.logger.info(
                    f"Processing previas page {current_page}/{self.total_pages}"
                )
                # TODO: As vezes rows_len = 1
                rows_len = len(
                    self.driver.find_elements(
                        By.XPATH, '//tr[@class="ui-widget-content ui-datatable-even"]'
                    )
                )
                
                for i in range(rows_len):
                    self.go_to_page(current_page)
                    # TODO: remover esse sleep
                    sleep(1)
                    row = self.wait_for_all_elements_to_be_visible(
                                (
                                    By.XPATH,
                                    '//tr[@class="ui-widget-content ui-datatable-even"]',
                                )
                            )[i]
                    codigo = row.find_element(By.XPATH, "./td[1]").text.strip()
                    nombre = row.find_element(By.XPATH, "./td[2]").text.strip()
                    self.logger.info(f"Processing {codigo} - {nombre}")
                    data[codigo] = {
                        "code": codigo,
                        "name": nombre,
                        "posprevias": [],
                    }

                    
                    sleep(1)
                    
                    info_icons = self.wait_for_all_elements_to_be_visible(
                                (
                                    By.XPATH,
                                    '//i[@class="pi  pi-info-circle"]',
                                )
                            )
                    self.scroll_to_element_and_click(info_icons[i])
                
                    self.logger.info("Waiting for loading to finish")
                    self.wait.until(EC.invisibility_of_element_located((By.XPATH, loading_path)))
                    self.logger.info("Loading finished")
                    # try checking if there no previaturas 
                    xpath_icon = (
                            "//div[contains(@id,':nombServicio')]"
                            "[contains(normalize-space(.), 'FACULTAD DE INGENIERÍA')]"
                            "//div[contains(@class,'ui-accordion-header')][1]"
                            "//span[contains(@class,'ui-icon')]"
                        )
                    if self.try_find_element((By.XPATH, xpath_icon)):
                    
                        self.wait_for_page_to_load()
                        self.wait_for_element_to_be_clickable((By.XPATH, xpath_icon)).click()
                        outer_tbody = self.wait_for_element_to_be_visible((By.XPATH, "//div[contains(@id,':nombServicio')][contains(normalize-space(.), 'FACULTAD DE INGENIERÍA')]//tbody[contains(@id,':previaturasPlanes_data')]"))
                        results = []
                        def _txt(el):
                            return (el.get_attribute("textContent") or "").strip()
                        
                        # Get all rows from the outer table (excluding empty message rows)
                        plan_rows = outer_tbody.find_elements(By.XPATH, "./tr[not(contains(@class,'ui-datatable-empty-message'))]")
                        
                        for prow in plan_rows:
                            # Get the 5 tds: Año | Denominación | Fecha | Descripción | (nested table)
                            tds = prow.find_elements(By.XPATH, "./td")
                            
                            if len(tds) < 5:
                                continue
                                
                            anio_plan   = _txt(tds[0])
                            carrera     = _txt(tds[1])
                            fecha       = _txt(tds[2])
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
                    self.scroll_to_bottom()
                    # foot is in front volver
                    self.scroll_to_element_and_click(
                            self.driver.find_element(
                                By.XPATH, "//span[normalize-space(.)='Volver']"
                            )
                        )
                    self.wait_for_page_to_load()
        finally:
            backup_file = "posprevias_data_backup.json"
            
            # Load existing data if file exists
            existing_data = {}
            try:
                with open(backup_file, "r", encoding="utf-8") as fp:
                    existing_data = json.load(fp)
                self.logger.info(f"Loaded existing data with {len(existing_data)} entries")
            except FileNotFoundError:
                self.logger.info("No existing backup file found, creating new one")
            except json.JSONDecodeError:
                self.logger.warning("Existing backup file is corrupted, starting fresh")
            
            # Update existing data with new data
            existing_data.update(data)
            
            # Save updated data
            with open(backup_file, "w", encoding="utf-8") as fp:
                json.dump(existing_data, fp, ensure_ascii=False, indent=2)
            self.logger.info(f"Backup updated with {len(data)} new/updated entries. Total entries: {len(existing_data)}")
