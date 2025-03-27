from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import time
import re
import logging
import traceback
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

# Import the BaseScraper class
from scraper.base_scraper import BaseScraper
from debug.logger import setup_logger, log_action

class CommercialMLSScraper(BaseScraper):
    """Scraper for CommercialMLS.com property listings"""
    
    def __init__(self, debug_mode: bool = False):
        """Initialize the CommercialMLS scraper
        
        Args:
            debug_mode: Whether to run in debug mode (shows browser)
        """
        super().__init__(debug_mode)
        self.logger = setup_logger("commercialmls_scraper")
        self.base_url = "https://www.commercialmls.com/"
        
        # Define selectors for the search page
        self.selectors = {
            "search_button": "#content > div:nth-child(1) > div.row.mb-5.title-container > div > div > div.row.mt-3 > div:nth-child(1) > a",
            "location_dropdown": "#crroot > div > div.js-main-content > div:nth-child(1) > div:nth-child(1) > div > div > div:nth-child(1) > div:nth-child(1) > div",
            "location_input": "#crroot > div > div.js-main-content > div:nth-child(1) > div:nth-child(1) > div > div > div:nth-child(1) > div:nth-child(1) > div.dropdown.p2.rounded--bottom.js-dropdown > div > div:nth-child(1) > div.mb2.clearfix > div > input",
            "type_dropdown": "#crroot > div > div.js-main-content > div:nth-child(1) > div:nth-child(1) > div > div > div:nth-child(1) > div:nth-child(2) > div.p2.js-dropdown-toggle",
            "for_sale_checkbox": "#crroot > div > div.js-main-content > div:nth-child(1) > div:nth-child(1) > div > div > div:nth-child(1) > div:nth-child(2) > div.dropdown.p2.rounded--bottom.js-dropdown > div.grid-row > div.grid-column.span-6 > div.control-group > div:nth-child(1) > label > span.control-indicator",
            "multifamily_checkbox": "#crroot > div > div.js-main-content > div:nth-child(1) > div:nth-child(1) > div > div > div:nth-child(1) > div:nth-child(2) > div.dropdown.p2.rounded--bottom.js-dropdown > div.grid-row > div.grid-column.span-10.border--left > div > div:nth-child(9) > label > span.control-indicator",
            "industrial_checkbox": "#crroot > div > div.js-main-content > div:nth-child(1) > div:nth-child(1) > div > div > div:nth-child(1) > div:nth-child(2) > div.dropdown.p2.rounded--bottom.js-dropdown > div.grid-row > div.grid-column.span-10.border--left > div > div:nth-child(3) > label > span.control-indicator",
            "office_checkbox": "#crroot > div > div.js-main-content > div:nth-child(1) > div:nth-child(1) > div > div > div:nth-child(1) > div:nth-child(2) > div.dropdown.p2.rounded--bottom.js-dropdown > div.grid-row > div.grid-column.span-10.border--left > div > div:nth-child(2) > label > span.control-indicator",
            "retail_checkbox": "#crroot > div > div.js-main-content > div:nth-child(1) > div:nth-child(1) > div > div > div:nth-child(1) > div:nth-child(2) > div.dropdown.p2.rounded--bottom.js-dropdown > div.grid-row > div.grid-column.span-10.border--left > div > div:nth-child(1) > label > span.control-indicator",
            "price_dropdown": "#crroot > div > div.js-main-content > div:nth-child(1) > div:nth-child(1) > div > div > div:nth-child(1) > div:nth-child(3) > div.p2.js-dropdown-toggle",
            "price_checkbox": "#crroot > div > div.js-main-content > div:nth-child(1) > div:nth-child(1) > div > div > div:nth-child(1) > div:nth-child(3) > div.dropdown.p2.rounded--bottom.js-dropdown > div > div:nth-child(1) > div > label > span.control-indicator",
            "min_price_input": "#crroot > div > div.js-main-content > div:nth-child(1) > div:nth-child(1) > div > div > div:nth-child(1) > div:nth-child(3) > div.dropdown.p2.rounded--bottom.js-dropdown > div > div:nth-child(1) > div > div > input:nth-child(2)",
            "max_price_input": "#crroot > div > div.js-main-content > div:nth-child(1) > div:nth-child(1) > div > div > div:nth-child(1) > div:nth-child(3) > div.dropdown.p2.rounded--bottom.js-dropdown > div > div:nth-child(1) > div > div > input:nth-child(4)",
            "more_dropdown": "#crroot > div > div.js-main-content > div:nth-child(1) > div:nth-child(1) > div > div > div:nth-child(1) > div:nth-child(4) > div.p2.js-dropdown-toggle",
            "date_added_checkbox": "#crroot > div > div.js-main-content > div:nth-child(1) > div:nth-child(1) > div > div > div:nth-child(1) > div:nth-child(4) > div.dropdown.p2.rounded--bottom.js-dropdown > div > div.grid-column.span-12.border--right > div:nth-child(2) > label > span.control-indicator",
            "start_date_input": "#crroot > div > div.js-main-content > div:nth-child(1) > div:nth-child(1) > div > div > div:nth-child(1) > div:nth-child(4) > div.dropdown.p2.rounded--bottom.js-dropdown > div > div.grid-column.span-12.border--right > div.border--bottom.pb2.mb2 > div.mbs.clearfix > input",
            "listing_card": ".map-panel .pt0.m0.full-width.centered > div > div > div",
            "grid_button": "#crroot > div > div.js-main-content > div:nth-child(1) > div:nth-child(1) > div > div > div.float-right.p1.bgh--shade.pointer > a",
            "grid_container": "#crroot > div > div.js-main-content > div:nth-child(1) > div:nth-child(2) > div.container--huge.pt3",
            "listing_cards": "div.grid-column.grid-card div.rounded.pointer.card a.link",
            "property_type_badge": "div.rounded.pointer.card div.badge",
            "property_name": "div.rounded.pointer.card div.bottom0.left0.text--white p.bold",
            "property_price": "div.rounded.pointer.card div.relative.p1 p.mb0.ellipsis span span span"
        }
        
        # Property type mapping - reordered as requested
        self.property_type_map = {
            "multifamily": self.selectors["multifamily_checkbox"],
            "industrial": self.selectors["industrial_checkbox"],
            "office": self.selectors["office_checkbox"],
            "retail": self.selectors["retail_checkbox"]
        }
    
    def search(self, property_types: List[str], location: str, min_price: str = None,
              max_price: str = None, start_date: datetime = None, end_date: datetime = None,
              progress_callback: Optional[Callable[[float], None]] = None) -> List[Dict[str, Any]]:
        """Search for listings with the given parameters
        
        Args:
            property_types: List of property types to search for
            location: Location to search in
            min_price: Minimum price (optional)
            max_price: Maximum price (optional)
            start_date: Start date for listings (optional)
            end_date: End date for listings (optional)
            progress_callback: Optional callback to report progress
            
        Returns:
            List of dictionaries containing listing details
        """
        results = []
        try:
            # Set up the driver
            self._setup_driver()
            
            # Initialize progress
            self.update_progress(0.05, progress_callback)
            
            # Maximize window or set a reasonable size to ensure all elements are visible
            try:
                self.logger.info("Adjusting browser window size for optimal viewing")
                self.driver.maximize_window()  # First try maximizing
                # If maximizing doesn't work well, set a specific size
                current_size = self.driver.get_window_size()
                if current_size['width'] < 1200 or current_size['height'] < 800:
                    self.driver.set_window_size(1366, 768)  # Standard laptop resolution
                    self.logger.info(f"Set window size to 1366x768")
                else:
                    self.logger.info(f"Window maximized to {current_size['width']}x{current_size['height']}")
            except Exception as e:
                self.logger.warning(f"Failed to adjust window size: {str(e)}")
            
            # Navigate to the base URL
            self.logger.info("Navigating to CommercialMLS.com...")
            self.driver.get(self.base_url)
            
            # Update progress after loading site
            self.update_progress(0.1, progress_callback)
            
            # Verify we reached the page
            if not self.verify_page_load("commercialmls.com"):
                return results
            
            # Update progress
            self.update_progress(0.15, progress_callback)
            
            # Click on the search button
            log_action(self.logger, "Clicking search button to start search")
            if not self.click_element(self.selectors["search_button"], "search button"):
                self.logger.error("Failed to click search button")
                return results
            
            # Update progress after clicking search button
            self.update_progress(0.2, progress_callback)
            
            # Set up search criteria
            self._setup_search_criteria(location, property_types, min_price, max_price, start_date, progress_callback)
            
            # Update progress
            self.update_progress(0.6, progress_callback)
            
            # Press Enter to submit the search
            log_action(self.logger, "Submitting search...")
            # Use a more standardized approach for pressing Enter
            try:
                # First try focusing on the body element and pressing Enter
                body = self.driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.ENTER)
            except Exception:
                # If direct approach fails, try executing JavaScript to submit the form
                self.logger.info("Using JavaScript to submit the search form")
                self.driver.execute_script("document.querySelector('form').submit();")
            
            # Update progress after submitting search
            self.update_progress(0.65, progress_callback)
            
            time.sleep(5)  # Wait for search results to load
            
            # Update progress after initial results load
            self.update_progress(0.7, progress_callback)
            
            # Click the grid button to switch to grid view
            log_action(self.logger, "Switching to grid view...")
            
            try:
                # Use standardized method instead of direct manipulation
                self.click_element(self.selectors["grid_button"], "grid view button")
                
                # Add a significant sleep to ensure grid view fully loads
                self.logger.info("Waiting for grid view to load completely...")
                time.sleep(5)  # Longer consistent sleep for both debug and normal modes
                
                self.logger.info("Successfully switched to grid view")
            except Exception as e:
                self.logger.warning(f"Failed to click grid button: {str(e)}")
                self.logger.warning("Continuing with current view")
            
            # Update progress after grid view loads
            self.update_progress(0.8, progress_callback)
            
            # Extract listing information
            self.logger.info("Extracting listings from grid view...")
            results = self._extract_listings_from_grid()
            
            # Update progress after extraction
            self.update_progress(0.9, progress_callback)
            
            # Log the specific listings found for debugging
            self.logger.info(f"Found {len(results)} listings")
            for i, listing in enumerate(results):
                self.logger.info(f"Listing {i+1}:")
                for key, value in listing.items():
                    self.logger.info(f"  {key}: {value}")
            
            # Update progress
            self.update_progress(1.0, progress_callback)
            
        except Exception as e:
            self.logger.error(f"Error during CommercialMLS search: {str(e)}")
            self.logger.error(traceback.format_exc())
        finally:
            # Close the driver
            self._close_driver()
            
        return results
    
    def _setup_search_criteria(self, location: str, property_types: List[str], 
                              min_price: str = None, max_price: str = None, 
                              start_date: datetime = None,
                              progress_callback: Optional[Callable[[float], None]] = None) -> None:
        """Set up the search criteria on the website
        
        Args:
            location: Location to search in
            property_types: List of property types to search for
            min_price: Minimum price (optional)
            max_price: Maximum price (optional)
            start_date: Start date for listings (optional)
            progress_callback: Optional callback to report progress
        """
        # Set location
        log_action(self.logger, f"Setting location to: {location}")
        self.click_element(self.selectors["location_dropdown"], "location dropdown")
        self.input_text_with_wait(self.selectors["location_input"], location, "location input", press_enter=False)
        time.sleep(1)
        
        # Update progress after setting location
        self.update_progress(0.25, progress_callback)
        
        # Press down arrow and then enter to select the first suggestion
        self.logger.info("Selecting location from dropdown suggestions")
        element = self.driver.find_element(By.CSS_SELECTOR, self.selectors["location_input"])
        element.send_keys(Keys.DOWN)
        time.sleep(0.5)
        element.send_keys(Keys.ENTER)
        time.sleep(1)
        
        # Update progress after confirming location
        self.update_progress(0.3, progress_callback)
        
        # Set property types
        log_action(self.logger, "Setting property types")
        self.click_element(self.selectors["type_dropdown"], "property type dropdown")
        
        # Select 'For Sale' checkbox
        log_action(self.logger, "Selecting For Sale option")
        self.click_element(self.selectors["for_sale_checkbox"], "For Sale checkbox")
        
        # Update progress after selecting for sale
        self.update_progress(0.35, progress_callback)
        
        # Select property types
        for prop_type in property_types:
            prop_type = prop_type.lower()
            if prop_type in self.property_type_map:
                log_action(self.logger, f"Selecting property type: {prop_type}")
                self.click_element(self.property_type_map[prop_type], f"{prop_type} checkbox")
                time.sleep(0.5)
        
        # Update progress after setting property types
        self.update_progress(0.4, progress_callback)
        
        # Set price range if provided
        if min_price or max_price:
            log_action(self.logger, "Setting price range filters")
            self.click_element(self.selectors["price_dropdown"], "price dropdown")
            time.sleep(1)  # Wait for dropdown to fully expand
            
            # Enable price checkbox
            self.click_element(self.selectors["price_checkbox"], "price checkbox")
            time.sleep(1)  # Wait for checkbox to take effect
            
            # Update progress after opening price filters
            self.update_progress(0.45, progress_callback)
            
            # Set min price if provided
            if min_price:
                try:
                    log_action(self.logger, f"Setting minimum price: {min_price}")
                    self.input_text_with_wait(self.selectors["min_price_input"], min_price, "minimum price input")
                    time.sleep(1)  # Increased pause between min and max price
                except Exception as e:
                    self.logger.warning(f"Standard approach for min price failed: {str(e)}")

            # Update progress after setting min price
            self.update_progress(0.5, progress_callback)

            # Set max price if provided
            if max_price:
                log_action(self.logger, f"Setting maximum price: {max_price}")
                try:
                    # Use the standardized method for input
                    self.input_text_with_wait(self.selectors["max_price_input"], max_price, "maximum price input")
                    time.sleep(1)  # Longer wait after inputting value
                    
                    # Send tab key to element to ensure value is applied
                    element = self.driver.find_element(By.CSS_SELECTOR, self.selectors["max_price_input"])
                    element.send_keys(Keys.TAB)
                    time.sleep(1)  # Longer wait after tabbing out
                    
                except Exception as e:
                    self.logger.warning(f"Standard approach for max price failed: {str(e)}")
            
            # Update progress after setting max price
            self.update_progress(0.52, progress_callback)
            
            # Add a delay before moving on to other dropdowns to ensure values persist
            time.sleep(2)
        
        # Set date range if provided
        if start_date:
            log_action(self.logger, "Setting date filter")
            self.click_element(self.selectors["more_dropdown"], "more filters dropdown")
            
            # Update progress after opening more dropdown
            self.update_progress(0.54, progress_callback)
            
            # Enable date added checkbox
            self.click_element(self.selectors["date_added_checkbox"], "date added checkbox")
            
            # Format date as mm/dd/yyyy and enter
            formatted_date = start_date.strftime("%m/%d/%Y")
            log_action(self.logger, f"Setting start date: {formatted_date}")
            self.input_text_with_wait(self.selectors["start_date_input"], formatted_date, "start date input")
            
            # Update progress after setting date filter
            self.update_progress(0.58, progress_callback)
    
    def _extract_listings_from_grid(self) -> List[Dict[str, Any]]:
        """Extract listing information from the grid view"""
        results = []
        processed_urls = set()
        
        try:
            # Wait for grid listings to load
            wait = WebDriverWait(self.driver, self.wait_time)
            
            # Wait for and get grid container
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors["grid_container"])))
            grid_container = self.driver.find_element(By.CSS_SELECTOR, self.selectors["grid_container"])
            
            # Add extra wait time to ensure all listing cards are fully rendered
            self.logger.info("Waiting for listing cards to fully load...")
            time.sleep(3)
            
            # Find all listing cards within the grid
            listing_cards = grid_container.find_elements(By.CSS_SELECTOR, self.selectors["listing_cards"])
            
            if not listing_cards:
                self.logger.warning("No listings found in grid view")
                return results
            
            self.logger.info(f"Found {len(listing_cards)} listings")
            
            # Extract details from each listing card
            for card in listing_cards:
                try:
                    listing = {}
                    
                    # Extract property type from the badge
                    property_type_elem = card.find_element(By.CSS_SELECTOR, self.selectors["property_type_badge"])
                    listing["property_type"] = property_type_elem.text.strip()
                    
                    # Extract name/address from the bold text
                    name_elem = card.find_element(By.CSS_SELECTOR, self.selectors["property_name"])
                    listing["address"] = name_elem.text.strip()
                    
                    # Extract price from the nested spans
                    price_elem = card.find_element(By.CSS_SELECTOR, self.selectors["property_price"])
                    listing["price"] = price_elem.text.strip()
                    
                    # Extract URL and convert to full property URL
                    href = card.get_attribute("href")
                    if href and href.startswith('#'):
                        property_id = href.split('/')[-1]
                        listing["url"] = f"https://www.commercialmls.com/property/{property_id}"
                    else:
                        listing["url"] = href
                    
                    # Skip if URL is invalid or duplicate
                    if not listing["url"] or listing["url"] in processed_urls:
                        continue
                    
                    processed_urls.add(listing["url"])
                    
                    # Add listing if it has valid information
                    if all(listing.get(key) for key in ["property_type", "address", "price"]):
                        results.append(listing)
                        self.logger.debug(f"Added listing: {listing['address']} - {listing['price']}")
                    
                except Exception as e:
                    self.logger.error(f"Error extracting listing: {str(e)}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error in grid extraction: {str(e)}")
        
        return results
        