from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime

from scraper.loopnet_scraper import LoopNetScraper
from scraper.commercialmls_scraper import CommercialMLSScraper
from debug.logger import setup_logger, log_action

class ScraperManager:
    """Manages all real estate scrapers and coordinates searches."""
    
    def __init__(self, debug_mode: bool = False):
        """Initialize the scraper manager
        
        Args:
            debug_mode: Whether to run scrapers in debug mode (shows browser)
        """
        self.debug_mode = debug_mode
        self.logger = setup_logger("scraper_manager")
        
        # Initialize scrapers
        self.scrapers = {
            "loopnet": LoopNetScraper(debug_mode=debug_mode),
            "commercialmls": CommercialMLSScraper(debug_mode=debug_mode)
        }
    
    def search(self, property_types: List[str], location: str, min_price: str = None,
              max_price: str = None, start_date: datetime = None, end_date: datetime = None,
              websites: List[str] = None, 
              progress_callbacks: Dict[str, Callable[[float], None]] = None) -> Union[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]]:
        """Execute search across specified or all scrapers
        
        Args:
            property_types: List of property types to search for
            location: Location to search in
            min_price: Minimum price (optional)
            max_price: Maximum price (optional)
            start_date: Start date for listings (optional)
            end_date: End date for listings (optional)
            websites: List of websites to search on. If None, search all.
            progress_callbacks: Dictionary mapping website names to progress callback functions
            
        Returns:
            Dictionary mapping websites to their results lists, or just a list of results if single site
        """
        websites_to_search = {}
        results = {}
        single_site = False
        
        # Determine which websites to search
        if websites:
            for website in websites:
                website_key = website.split('.')[0].lower()
                if website_key in self.scrapers:
                    websites_to_search[website_key] = self.scrapers[website_key]
            if len(websites_to_search) == 1:
                single_site = True
        else:
            websites_to_search = self.scrapers
        
        # Execute searches
        for website_key, scraper in websites_to_search.items():
            log_action(self.logger, f"Starting search on {website_key}")
            
            # Get progress callback for this website if available
            progress_callback = None
            if progress_callbacks and website_key in progress_callbacks:
                progress_callback = progress_callbacks[website_key]
            
            # Execute search
            website_results = scraper.search(
                property_types=property_types,
                location=location,
                min_price=min_price,
                max_price=max_price,
                start_date=start_date,
                end_date=end_date,
                progress_callback=progress_callback
            )
            
            results[website_key] = website_results
            log_action(self.logger, f"Found {len(website_results)} results on {website_key}")
        
        # Return list if single site, dict otherwise
        if single_site and len(results) == 1:
            return list(results.values())[0]
        return results 