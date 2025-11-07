

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
from selenium.common.exceptions import ElementClickInterceptedException

class UseTable():
    
    def get_total_pages(self) -> int:
        """Get the total number of pages in the paginator."""
        self.scroll_to_bottom()
        # Wait for any element to be clickable, then click the first visible one
        elements = self.wait.until(
            EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@class,'ui-paginator-last')]"))
        )

        # Find the first visible and clickable one
        for element in elements:
            if element.is_displayed():
                if not self.scroll_to_element_and_click(element):
                    self.total_pages = 1
                    return 1
                break
            
        active_anchor_xpath = "//a[contains(@class,'ui-paginator-page') and contains(@class,'ui-state-active')]"
        # TODO: remover esse sleep
        sleep(0.2)
        active_elements = self.wait.until(
            EC.presence_of_all_elements_located((By.XPATH, active_anchor_xpath))
        )
        # Get the first displayed active element
        active = None
        for element in active_elements:
            if element.is_displayed():
                active = element
                break
        total = int(active.text.strip())
        self.logger.info(f"Total pages: {total}")
        
        # Wait for modal to disappear before clicking first page
        self.wait.until(
            EC.invisibility_of_element_located((By.ID, "j_idt22_modal"))
        )
        
        self.wait_for_element_to_be_clickable((By.XPATH, "//a[@class='ui-paginator-first ui-state-default ui-corner-all']")).click()
        self.total_pages = total
        return total

    def go_to_page(self, page: int):
        page_text_element = self.wait_for_element_to_be_visible((
                By.XPATH,
                '//a[contains(@class, "ui-state-active")]',
            ))
        
        page_text = page_text_element.get_attribute("aria-label")
        if page_text is None:
            page_text = page_text_element.text.strip()
        if (
            page_text == f"Page {page}"
        ):
            return
        if page > 10 and (page_text == "Page 1" or page_text == "1"):
            self.scroll_to_element_and_click(self.wait_for_element_to_be_clickable((By.XPATH, f'//a[contains(@class,"ui-paginator-last")]')))
            self.wait_for_page_to_load()
        self.wait.until(EC.invisibility_of_element_located((By.XPATH, '//div[@id="j_idt22_modal"]')))
        self.scroll_to_element_and_click(self.wait_for_element_to_be_clickable((By.XPATH, f'//a[@aria-label="Page {page}"]')))
        self.wait_for_page_to_load()
        self.logger.info("Waiting for loading to finish")
        self.wait.until(EC.invisibility_of_element_located((By.XPATH, "//img[@src='/jakarta.faces.resource/img/cargando.gif.xhtml?ln=default']")))
        self.logger.info("Loading finished")
