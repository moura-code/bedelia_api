# Organized Bedelías Scraper

This is the refactored and organized version of the Bedelías scraper with clean separation of concerns.

## 📁 Project Structure

```
scraper/
├── __init__.py                 # Package initialization
├── main_organized.py           # New main entry point
├── bedelias_scraper.py         # Main scraper class (composition)
│
├── core/                       # Universal web scraping functionality
│   ├── __init__.py
│   └── base_scraper.py         # Base scraper with universal methods
│
├── handlers/                   # Page-specific functionality
│   ├── __init__.py
│   ├── page_handlers.py        # Page interaction handlers
│   ├── pagination_handler.py   # Pagination-specific logic
│   └── requirements_processor.py # Requirements tree parsing
│
├── models/                     # Data models
│   ├── __init__.py
│   └── subject.py              # Subject and requirements data models
│
├── config/                     # Configuration
│   ├── __init__.py
│   └── constants.py            # All configuration constants
│
└── utils/                      # Utility functions
    ├── __init__.py
    └── helpers.py              # Helper functions
```

## 🎯 Key Improvements

### **Separation of Concerns**
- **Universal Functions**: In `core/base_scraper.py` - reusable across any web scraping project
- **Page-Specific Functions**: In `handlers/` - specific to Bedelías website interactions
- **Data Models**: In `models/` - structured data representation
- **Configuration**: In `config/` - centralized constants and settings

### **Clean Architecture**
- **Composition Pattern**: Main scraper inherits from specialized components
- **Single Responsibility**: Each class has one clear purpose
- **Type Safety**: Comprehensive type hints throughout
- **Error Handling**: Proper exception handling with retry mechanisms

### **Better Organization**
- **No More Mixed Code**: Universal and specific functionality clearly separated
- **Centralized Configuration**: All hardcoded values in one place
- **Modular Design**: Easy to test, maintain, and extend
- **Clear Interfaces**: Well-defined contracts between components

## 🚀 Usage

### **Using the New Organized Structure:**
```python
from scraper import BedeliasScraper

scraper = BedeliasScraper(
    username="your_username",
    password="your_password",
    browser="firefox",  # or "chrome"
    debug=False
)
scraper.run()
```

### **Running from Command Line:**
```bash
python scraper/main_organized.py
```

## 📊 Component Breakdown

### **Universal Components (Reusable)**
- `BaseScraper`: Browser management, element interaction, waiting strategies
- `extract_table_info()`: Generic table parsing
- `retry_on_exception()`: Retry mechanism for unreliable operations
- Logging and utility functions

### **Bedelías-Specific Components**
- `PageHandlers`: Login, faculty selection, navigation workflows
- `PaginationHandler`: Page navigation specific to Bedelías UI
- `RequirementsProcessor`: Tree parsing specific to PrimeFaces tree structure
- `BedeliasConfig`: All website-specific constants and selectors

### **Data Models**
- `SubjectInfo`: Structured representation of subject data
- `RequirementNode`: Tree structure for requirements

## 🔧 Migration from Old Structure

The old `main.py` mixed everything together. The new structure separates:

1. **What was universal** → `core/base_scraper.py`
2. **What was page-specific** → `handlers/*.py`  
3. **What was configuration** → `config/constants.py`
4. **What was data** → `models/*.py`

This makes the code:
- ✅ Easier to maintain
- ✅ More testable
- ✅ Better documented
- ✅ Cleaner to extend
- ✅ Properly organized

## 🧪 Testing

Each component can now be tested independently:
- Mock the `BaseScraper` for testing page handlers
- Test `RequirementsProcessor` with sample HTML
- Unit test data models and utilities
- Integration test the full `BedeliasScraper`
