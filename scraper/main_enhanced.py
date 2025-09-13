"""
Enhanced main entry point for the Bedelías scraper.
This demonstrates the improved architecture with better patterns.
"""

import os
import sys
from dotenv import load_dotenv

from scraper.enhanced_bedelias_scraper import EnhancedBedeliasScraper
from scraper.utils import setup_logging, str_to_bool
from scraper.core.exceptions import ScraperError


def main():
    """Main function to run the enhanced Bedelías scraper."""
    # Load environment variables
    load_dotenv()
    
    # Setup enhanced logging
    setup_logging()
    
    # Get configuration from environment
    username = os.getenv("DOCUMENTO", "")
    password = os.getenv("CONTRASENA", "")
    browser = os.getenv("BROWSER", "firefox").strip().lower()
    debug = str_to_bool(os.getenv("DEBUG", "False"))
    wait_timeout = int(os.getenv("WAIT_TIMEOUT", "10"))
    
    # Validate required credentials
    if not username or not password:
        print("ERROR: USERNAME (DOCUMENTO) or PASSWORD (CONTRASENA) not set in environment.")
        print("Please set these environment variables and try again.")
        sys.exit(1)
    
    print("🚀 Starting Enhanced Bedelías Scraper")
    print("=" * 50)
    print(f"Browser: {browser}")
    print(f"Debug mode: {debug}")
    print(f"Wait timeout: {wait_timeout}s")
    print("=" * 50)
    
    # Create and run the enhanced scraper
    scraper = EnhancedBedeliasScraper(
        username=username,
        password=password,
        browser=browser,
        debug=debug,
        wait_timeout=wait_timeout
    )
    
    try:
        scraper.run()
        print("\n✅ Enhanced scraping completed successfully!")
        print(f"Check 'previas_data_backup.json' for results.")
        
    except KeyboardInterrupt:
        print("\n⚠️  Scraping interrupted by user")
        sys.exit(130)
        
    except ScraperError as e:
        print(f"\n❌ Scraping failed: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)
        
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
