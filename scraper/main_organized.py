"""
Main entry point for the organized Bedelías scraper.
This replaces the old main.py with a clean, organized structure.
"""

import os
import sys
from dotenv import load_dotenv

from scraper import BedeliasScraper, setup_logging, str_to_bool


def main():
    """Main function to run the Bedelías scraper."""
    # Load environment variables
    load_dotenv()
    
    # Setup logging
    setup_logging()
    
    # Get configuration from environment
    username = os.getenv("DOCUMENTO", "")
    password = os.getenv("CONTRASENA", "")
    browser = os.getenv("BROWSER", "firefox").strip().lower()
    debug = str_to_bool(os.getenv("DEBUG", "False"))
    
    # Validate required credentials
    if not username or not password:
        print("ERROR: USERNAME (DOCUMENTO) or PASSWORD (CONTRASENA) not set in environment.")
        print("Please set these environment variables and try again.")
        sys.exit(1)
    
    print(f"Starting Bedelías scraper...")
    print(f"Browser: {browser}")
    print(f"Debug mode: {debug}")
    
    # Create and run the scraper
    scraper = BedeliasScraper(
        username=username,
        password=password,
        browser=browser,
        debug=debug
    )
    
    try:
        scraper.run()
        print("Scraping completed successfully!")
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Scraping failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
