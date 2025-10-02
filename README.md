# Bedelías API Scraper

An improved web scraper for extracting academic data from the Bedelías system at Universidad de la República (Uruguay).

## Features

- **Modular Design**: Separated page classes for better code organization
- **Improved Error Handling**: Better logging and error management
- **Flexible Configuration**: Environment variable support with sensible defaults
- **Browser Support**: Works with Firefox and Chrome browsers
- **Selective Extraction**: Choose to extract previas, posprevias, or both

## Project Structure

```
scraper/
├── main.py              # Main Bedelias class and entry point
├── scraper.py           # Base Scraper class with common functionality
├── example_usage.py     # Usage examples
├── pages/               # Page-specific scrapers
│   ├── login.py         # Login functionality
│   ├── previas.py       # Prerequisites extraction
│   └── posprevias.py    # Post-prerequisites extraction
└── common/
    └── usetable.py      # Table pagination utilities
```

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your credentials in a `.env` file:
```env
DOCUMENTO=your_document_number
CONTRASENA=your_password
BROWSER=firefox
DEBUG=False
EXTRACT_PREVIAS=True
EXTRACT_POSPREVIAS=True
```

## Usage

### Basic Usage

```python
from main import Bedelias

# Initialize scraper
scraper = Bedelias(
    username="your_document",
    password="your_password",
    browser="firefox",
    debug=True  # Set to False for headless mode
)

# Run complete extraction
scraper.run()
```

### Advanced Usage

```python
# Extract only previas
scraper.run(extract_previas=True, extract_posprevias=False)

# Extract only posprevias
scraper.run(extract_previas=False, extract_posprevias=True)

# Use environment variables
scraper = Bedelias()  # Will load from .env
scraper.run()
```

### Command Line

```bash
# Run with environment variables
python main.py

# Run example
python example_usage.py

# Run minimal example
python example_usage.py minimal
```

## Configuration Options

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `DOCUMENTO` | - | Your document number (required) |
| `CONTRASENA` | - | Your password (required) |
| `BROWSER` | `firefox` | Browser to use (`firefox` or `chrome`) |
| `DEBUG` | `False` | Enable debug mode (show browser) |
| `EXTRACT_PREVIAS` | `True` | Extract prerequisites data |
| `EXTRACT_POSPREVIAS` | `True` | Extract post-prerequisites data |

## Output

The scraper generates JSON backup files:
- `previas_data_backup.json` - Prerequisites data
- `posprevias_data_backup.json` - Post-prerequisites data

## Improvements Made

1. **Fixed Missing Functions**: Completed `build_driver()` and other incomplete functions
2. **Proper Class Integration**: Page classes now properly inherit from base Scraper class
3. **Fixed Imports**: Resolved circular import issues and missing dependencies
4. **Better Error Handling**: Improved logging and error management throughout
5. **Flexible API**: Added parameters to control what data to extract
6. **Documentation**: Added comprehensive documentation and examples

## Error Handling

The scraper includes comprehensive error handling:
- Network timeouts and connection issues
- Missing elements on pages
- Login failures
- Data extraction errors

All errors are logged appropriately, and the browser is properly cleaned up even if errors occur.
