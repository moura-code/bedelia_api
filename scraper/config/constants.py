"""
Configuration constants for Bedelías scraper.
All hardcoded values are centralized here for easy maintenance.
"""

class BedeliasConfig:
    """Configuration constants specific to Bedelías website."""
    
    # URLs
    LOGIN_URL = "https://bedelias.udelar.edu.uy/views/private/desktop/evaluarPrevias/evaluarPrevias02.xhtml?cid=2"
    HOME_URL = "https://bedelias.udelar.edu.uy/"
    
    # Form Field IDs
    USERNAME_FIELD_ID = "username"
    PASSWORD_FIELD_ID = "password"
    LOGIN_BUTTON_NAME = "_eventId_proceed"
    
    # Menu Navigation
    STUDY_PLANS_MENU_TEXT = "PLANES DE ESTUDIO"
    PREREQUISITES_LINK_TEXT = "Planes de estudio / Previas"
    
    # Faculty Selection
    TECHNOLOGY_FACULTY_TEXT = "TECNOLOGÍA Y CIENCIAS DE LA NATURALEZA"
    FING_FACULTY_TEXT = "FING - FACULTAD DE INGENIERÍA"
    COMPUTER_ENGINEERING_TEXT = "INGENIERIA EN COMPUTACION"
    
    # Modal and UI Elements
    MODAL_ID = "j_idt22_modal"
    COLUMN_FILTER_XPATH = "//span[contains(@class,'ui-column-title')]/following-sibling::input[1]"
    SUBJECT_SELECT_XPATH = '//*[text()="INGENIERIA EN COMPUTACION"]/preceding-sibling::td[1]'
    INFO_BUTTON_XPATH = '//i[@class="pi  pi-info-circle"]'
    PREREQUISITES_SYSTEM_SPAN_TEXT = "Sistema de previaturas"
    
    # Pagination
    PAGINATOR_LAST_XPATH = "//a[contains(@class,'ui-paginator-last')]"
    PAGINATOR_FIRST_XPATH = "//a[@class='ui-paginator-first ui-state-default ui-corner-all']"
    ACTIVE_PAGE_XPATH = "//a[contains(@class,'ui-paginator-page') and contains(@class,'ui-state-active')]"
    PAGE_LINK_XPATH_TEMPLATE = '//a[@aria-label="Page {page}"]'
    
    # Data Table
    DATA_ROW_XPATH = '//tr[@class="ui-widget-content ui-datatable-even"]'
    
    # Requirements Tree
    TREE_ROOT_ID = "arbol"
    TREE_PLUS_ICON_XPATH = '//span[@class="ui-tree-toggler ui-icon ui-icon-plus"]'
    TREE_ROOT_SELECTOR = 'td.ui-treenode[data-rowkey="root"]'
    TREE_LABEL_SELECTOR = ".ui-treenode-label"
    TREE_CHILDREN_CONTAINER_XPATH = 'following-sibling::td[contains(@class,"ui-treenode-children-container")]'
    TREE_CHILDREN_SELECTOR = "div.ui-treenode-children > table > tbody > tr > td.ui-treenode"
    
    # Requirements Dialog
    REQUIREMENTS_DIALOG_XPATH = "/html/body/div[3]/div[7]/div/form/div[1]/div/div/table/tbody/tr/td[1]/div"
    BACK_BUTTON_XPATH = "//span[normalize-space(.)='Volver']"
    
    # File Names
    BACKUP_FILENAME = "previas_data_backup.json"


class RegexPatterns:
    """Regular expression patterns for parsing Bedelías data."""
    
    # Pattern for "N aprobación/es entre:"
    APPROVAL_PATTERN = r"(\d+)\s+aprobaci[oó]n(?:/|)es?\s+entre:?"
    
    # Pattern for "N créditos en el Plan: <plan>"
    CREDITS_PATTERN = r"(\d+)\s+cr[eé]ditos?\s+en\s+el\s+Plan:?\s*(.*)"
    
    # Pattern for UCB requirements
    ITEM_PREFIX_PATTERN = r"^(?:(Examen|Curso)\s+de\s+la\s+U\.C\.B|U\.C\.B\s+aprobada)\s*:\s*(.+)$"


class NodeTypeMap:
    """Mapping for JSF node types to readable group types."""
    
    MAPPING = {
        "y": "ALL",      # debe tener todas
        "o": "ANY",      # debe tener alguna
        "no": "NONE",    # no debe tener
        "default": "LEAF"  # leaf node (a concrete requirement)
    }
