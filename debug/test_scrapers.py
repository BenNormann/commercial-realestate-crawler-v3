import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add parent directory to path to import scraper package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.scraper_manager import ScraperManager
from debug.logger import setup_logger

def print_listing(listing: Dict[str, Any]) -> None:
    """Print a property listing in a simple format"""
    print("\n" + "="*50)
    for key, value in listing.items():
        print(f"{key.capitalize()}: {value}")
    print("="*50)

def main() -> None:
    """Main test menu"""
    # Hardcoded search parameters
    location = "Seattle, WA"
    property_types = ["multifamily", "industrial", "office", "retail"]
    min_price = "500000"
    max_price = "1000000"

    # Calculate dates and immediately print them
    print("\n=== Date Calculation Debug ===")
    current_date = datetime.now()
    print(f"Current date: {current_date}")
    print(f"Current date formatted: {current_date.strftime('%Y-%m-%d')}")
    
    start_date = current_date - timedelta(days=30)
    print(f"Start date: {start_date}")
    print(f"Start date formatted: {start_date.strftime('%Y-%m-%d')}")
    print(f"Start date as MM/DD/YYYY: {start_date.strftime('%m/%d/%Y')}")
    print(f"Days difference: {(current_date - start_date).days}")
    print("=============================\n")
    
    # Set up logger
    logger = setup_logger("test_scrapers")
    
    while True:
        print("\nCommercial Real Estate Scraper")
        print("=" * 30)
        print("1. Test LoopNet")
        print("2. Test CommercialMLS")
        print("3. Test Both")
        print("4. Exit")
        
        choice = input("\nChoice (1-4): ").strip()
        
        if choice == "4":
            break
            
        if choice not in ["1", "2", "3"]:
            print("Invalid choice. Please try again.")
            continue
        
        # Run selected test(s)
        manager = ScraperManager(debug_mode=True)
        
        try:
            if choice == "1":
                print("\nTesting LoopNet scraper...")
                print("Browser will stay open for inspection until you press Enter after the test is complete.\n")
                results = manager.scrapers["loopnet"].search(
                    property_types=property_types,
                    location=location,
                    min_price=min_price,
                    max_price=max_price,
                    start_date=start_date
                )
                if not results:
                    print("\nNo results found.")
                else:
                    print(f"\nFound {len(results)} listings:")
                    for listing in results:
                        print_listing(listing)
            elif choice == "2":
                print("\nTesting CommercialMLS scraper...")
                print("Browser will stay open for inspection until you press Enter after the test is complete.\n")
                results = manager.scrapers["commercialmls"].search(
                    property_types=property_types,
                    location=location,
                    min_price=min_price,
                    max_price=max_price,
                    start_date=start_date
                )
                if not results:
                    print("\nNo results found.")
                else:
                    print(f"\nFound {len(results)} listings:")
                    for listing in results:
                        print_listing(listing)
            else:  # choice == "3"
                print("\nTesting both scrapers...")
                print("Browsers will stay open for inspection until you press Enter after each test is complete.\n")
                results = manager.search(
                    property_types=property_types,
                    location=location,
                    min_price=min_price,
                    max_price=max_price,
                    start_date=start_date
                )
                
                if not results or all(not site_results for site_results in results.values()):
                    print("\nNo results found.")
                else:
                    total_count = sum(len(site_results) for site_results in results.values())
                    print(f"\nFound {total_count} listings:")
                    
                    for website, listings in results.items():
                        if listings:
                            print(f"\n--- {website.upper()} ---")
                            for listing in listings:
                                print_listing(listing)
                    
        except Exception as e:
            print(f"\nError: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Ask if user wants to run another test
        if input("\nRun another test? (y/n): ").strip().lower() != 'y':
            break
    
    print("\nTest session completed.")

if __name__ == "__main__":
    main() 