from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import time
import logging
import traceback
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

from scraper.base_scraper import BaseScraper
from debug.logger import setup_logger, log_action

class LoopNetScraper(BaseScraper):
    """Scraper for LoopNet.com"""
    
    # CSS Selectors
    SELECTORS = {
        'location_box': "#dataSection > section.wrap.hero > div.module.clearfix.wrapper-container > div > div > form > div > div > div.quick-search-container.search-location-container > div.typeahead-container > div > input",
        'sale_lease_dropdown': "#quickSearchFilters > div.criteria-inputs > div.search-filter.search-type-container > div > button",
        'for_sale_button': "#quickSearchFilters > div.criteria-inputs > div.search-filter.search-type-container > div > ul > li:nth-child(2) > button",
        'property_type_dropdown': "#quickSearchFilters > div.filters > div:nth-child(1) > div > button",
        'multifamily_checkbox': "#quickSearchFilters > div.filters > div:nth-child(1) > div > div > ul > li:nth-child(7) > label > input",
        'retail_checkbox': "#quickSearchFilters > div.filters > div:nth-child(1) > div > div > ul > li:nth-child(4) > label > input",
        'industrial_checkbox': "#quickSearchFilters > div.filters > div:nth-child(1) > div > div > ul > li:nth-child(3) > label > input",
        'office_checkbox': "#quickSearchFilters > div.filters > div:nth-child(1) > div > div > ul > li:nth-child(2) > label > input",
        'other_filters_button': "#quickSearchFilters > div.filters > div:nth-child(15) > button",
        'min_price_box': ".price-range .range-from input",
        'max_price_box': ".price-range .range-to input",
        'custom_date_checkbox': ".date-entered .pill-group > div:nth-child(2) label",
        'start_date_box': ".date-entered .custom-time-period input",
        'search_button': "div.csgp-modal.advanced-filters-modal button.button.primary.submit",
        'search_results_container': "#dataSection > div.main-content > div.placard-container",
        'popup_close_button': "#top > section.master > div.csgp-modal.ng-isolate-scope.light.sso-form-modal-secondary.reg-overlay-target.ng-hide > div.csgp-modal-container.csgp-modal-dialog.container > button"
    }
    
    # Listing extraction selectors
    LISTING_SELECTORS = {
        'address': "h4 a, a[title*='More details for']",
        'location': "a.subtitle-beta, span.location",
        'price': "li[name='Price'], span.price, div.price",
        'property_type': "ul.data-points-2c li:nth-child(3), span.property-type",
        'details_link': "#placardSec > div.placards > ul > li > article > div.placard-pseudo > a, a[title*='More details for']"
    }
    
    def __init__(self, debug_mode: bool = False):
        """Initialize the LoopNet scraper
        
        Args:
            debug_mode: Whether to run in debug mode (shows browser)
        """
        super().__init__(debug_mode)
        self.logger = setup_logger("loopnet_scraper")
        self.base_url = "https://www.loopnet.com/"
        
    def _try_close_popup(self) -> bool:
        """Try to close any popup that appears"""
        try:
            # First try to remove overlays using JavaScript
            self._remove_overlays()
            
            # Then try to find and click any close buttons
            close_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.csgp-modal-close.ln-icon-close-hollow")
            for button in close_buttons:
                try:
                    if button.is_displayed():
                        # Use standardized click method for better reliability
                        self.click_element(button, "popup close button")
                except:
                    continue
            
            return True
        except Exception as e:
            if self.logger:
                self.logger.debug(f"No popup to close: {str(e)}")
            return False

    def search(self, property_types: List[str], location: str, min_price: str = None,
              max_price: str = None, start_date: datetime = None, end_date: datetime = None,
              progress_callback: Optional[Callable[[float], None]] = None) -> List[Dict[str, Any]]:
        """Search for listings with the given parameters"""
        try:
            # Set up the driver
            self._setup_driver()
            
            # Initialize progress
            self.update_progress(0.05, progress_callback)
            
            # Navigate to LoopNet
            if self.logger:
                self.logger.info("Navigating to LoopNet...")
            self.driver.get(self.base_url)
            
            # Update progress after loading the site
            self.update_progress(0.1, progress_callback)
            
            # Verify we reached the page
            if not self.verify_page_load("loopnet.com"):
                return []
            
            # Enter location - close popup if this fails
            try:
                self.input_text_with_wait(self.SELECTORS['location_box'], location, "location input", press_enter=True)
                log_action(self.logger, f"Entering location: {location}")
            except Exception:
                self._try_close_popup()
                self.input_text_with_wait(self.SELECTORS['location_box'], location, "location input", press_enter=True)
                
            self.update_progress(0.2, progress_callback)
            
            # Click sale/lease dropdown and select For Sale
            try:
                self.click_element(self.SELECTORS['sale_lease_dropdown'], "sale/lease dropdown")
                self.click_element(self.SELECTORS['for_sale_button'], "for sale button")
                log_action(self.logger, "Setting search to For Sale")
            except Exception:
                self._try_close_popup()
                self.click_element(self.SELECTORS['sale_lease_dropdown'], "sale/lease dropdown")
                self.click_element(self.SELECTORS['for_sale_button'], "for sale button")
                
            self.update_progress(0.25, progress_callback)
            
            # Select property types
            try:
                self.click_element(self.SELECTORS['property_type_dropdown'], "property type dropdown")
            except Exception:
                self._try_close_popup()
                self.click_element(self.SELECTORS['property_type_dropdown'], "property type dropdown")
            
            # Update progress after opening property type dropdown
            self.update_progress(0.3, progress_callback)
            
            # Map property types to selectors
            property_type_selectors = {
                'multifamily': self.SELECTORS['multifamily_checkbox'],
                'retail': self.SELECTORS['retail_checkbox'],
                'industrial': self.SELECTORS['industrial_checkbox'],
                'office': self.SELECTORS['office_checkbox']
            }
            
            # Click appropriate checkboxes
            for prop_type in property_types:
                prop_type_lower = prop_type.lower()
                if prop_type_lower in property_type_selectors:
                    try:
                        self.click_element(property_type_selectors[prop_type_lower], f"{prop_type} checkbox")
                        log_action(self.logger, f"Selecting property type: {prop_type}")
                    except Exception:
                        self._try_close_popup()
                        self.click_element(property_type_selectors[prop_type_lower], f"{prop_type} checkbox")
            
            # Click outside to close dropdown
            self.driver.execute_script("document.activeElement.blur();")
            self.update_progress(0.35, progress_callback)
            
            # Open Other Filters
            try:
                self.click_element(self.SELECTORS['other_filters_button'], "other filters button")
                log_action(self.logger, "Opening Other Filters popup")
                
                # Update progress after opening filters popup
                self.update_progress(0.4, progress_callback)
                
                # Set price range if provided
                if min_price or max_price:
                    log_action(self.logger, "Setting price range filters")
                    
                    # Set min price if provided
                    if min_price:
                        try:
                            log_action(self.logger, f"Setting minimum price: {min_price}")
                            self.input_text_with_wait(self.SELECTORS['min_price_box'], min_price, "minimum price input", clear_first=True)
                        except Exception as e:
                            self.logger.warning(f"Setting min price failed: {str(e)}")
                    
                    # Update progress after setting min price
                    self.update_progress(0.45, progress_callback)
                    
                    # Set max price if provided
                    if max_price:
                        try:
                            log_action(self.logger, f"Setting maximum price: {max_price}")
                            self.input_text_with_wait(self.SELECTORS['max_price_box'], max_price, "maximum price input", clear_first=True)
                        except Exception as e:
                            self.logger.warning(f"Setting max price failed: {str(e)}")
                    
                    # Update progress after setting max price
                    self.update_progress(0.5, progress_callback)
                
                # Set date filter if start_date is provided
                if start_date:
                    # First click the custom date option
                    self.click_element(self.SELECTORS['custom_date_checkbox'], "custom date checkbox")
                    
                    # Format the date string (MM/DD/YYYY)
                    date_str = start_date.strftime("%m/%d/%Y")
                    log_action(self.logger, f"Setting start date: {date_str}")
                    self.input_text_with_wait(self.SELECTORS['start_date_box'], date_str, "start date input", clear_first=True)
                    
                    # Update progress after setting date filter
                    self.update_progress(0.55, progress_callback)
                
                # Click Search button to apply filters
                self.click_element(self.SELECTORS['search_button'], "search button")
                log_action(self.logger, "Applying filters and searching")
                
                # Update progress after clicking search button
                self.update_progress(0.6, progress_callback)
            except Exception as e:
                self.logger.error(f"Error setting filters: {str(e)}")
                self.logger.error(traceback.format_exc())
                
                # Try to close popup if there was an error
                try:
                    self.click_element(self.SELECTORS['popup_close_button'], "popup close button")
                except:
                    pass
            
            self.update_progress(0.65, progress_callback)
            
            # Update progress before extracting listings
            self.update_progress(0.7, progress_callback)
            
            # Extract listings from search results
            results = self._extract_listings()
            
            # Update progress after extracting listings
            self.update_progress(0.9, progress_callback)
            
            # Log the specific listings found for debugging
            for i, listing in enumerate(results):
                self.logger.info(f"Listing {i+1}:")
                for key, value in listing.items():
                    self.logger.info(f"  {key}: {value}")
            
            self.update_progress(1.0, progress_callback)
            
        except Exception as e:
            self.logger.error(f"Error during LoopNet search: {str(e)}")
            self.logger.error(traceback.format_exc())
        finally:
            self._close_driver()
        
        return results
    
    def _extract_listing_details(self, card: Any, selectors: Dict[str, str]) -> Dict[str, str]:
        """Extract listing details from a card element using provided selectors
        
        Args:
            card: The BeautifulSoup card element
            selectors: Dictionary mapping field names to CSS selectors
            
        Returns:
            Dict[str, str]: Dictionary of extracted details
        """
        details = {}
        for field, selector in selectors.items():
            try:
                element = card.select_one(selector)
                if element:
                    # Clean up the text
                    text = element.text.strip()
                    # Remove any extra whitespace
                    text = ' '.join(text.split())
                    details[field] = text
                else:
                    details[field] = f"{field} not available"
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error extracting {field}: {str(e)}")
                details[field] = f"{field} not available"
        return details
    
    def _extract_listings(self) -> List[Dict[str, Any]]:
        """Extract listing details from search results page"""
        listings = []
        processed_urls = set()  # Track URLs to avoid duplicates
        log_action(self.logger, "Extracting listings")
        
        try:
            # Wait for search results page to fully load and stabilize
            self.smart_wait("page_load", timeout=15)
            
            # Wait for listing elements to be present and stable
            self.logger.info("Waiting for listing content to stabilize...")
            if not self.smart_wait("stable", "a[title*='More details for']", min_count=1, timeout=20, stable_time=2.0):
                self.logger.warning("Listing content did not stabilize, trying alternative approach")
                # Try waiting for placard containers as fallback
                if not self.smart_wait("min_count", "div.placard-content, .property-card, article.placard", min_count=1, timeout=15):
                    self.logger.warning("No listing containers found, proceeding with extraction anyway")
            
            # Get the page source and parse with BeautifulSoup
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # First try to find all listing links directly
            detail_links = soup.select("a[title*='More details for']")
            log_action(self.logger, f"Found {len(detail_links)} detail links directly")
            
            for link in detail_links:
                try:
                    if 'href' not in link.attrs:
                        continue
                        
                    listing_url = link['href']
                    if listing_url in processed_urls:
                        continue
                        
                    processed_urls.add(listing_url)
                    
                    # Extract information from the title attribute
                    title = link.get('title', '')
                    if 'More details for ' in title:
                        # Extract address and property type from title
                        title_content = title.replace('More details for ', '')
                        parts = title_content.split(' - ')
                        
                        full_address = parts[0] if parts else "Address not available"
                        property_type = "Type not available"
                        
                        # Try to extract property type from title
                        if len(parts) > 1 and 'for ' in parts[1]:
                            property_type = parts[1].split('for ')[0].strip()
                        
                        # Try to find price in nearby elements
                        price = "Price not available"
                        parent = link.parent
                        for _ in range(5):  # Check a few levels up
                            if not parent:
                                break
                                
                            # Look for price elements
                            price_elem = parent.select_one("[name='Price'], [class*='price'], span.price, div.price")
                            if price_elem and price_elem.text and '$' in price_elem.text:
                                price = price_elem.text.strip()
                                break
                                
                            parent = parent.parent
                        
                        # Create listing
                        listing = {
                            'address': full_address,
                            'price': price,
                            'property_type': property_type,
                            'url': listing_url
                        }
                        
                        listings.append(listing)
                        log_action(self.logger, f"Added listing from title: {full_address}")
                        
                except Exception as e:
                    self.logger.error(f"Error extracting from link title: {str(e)}")
            
            # If no listings found, try the placard-content approach
            if not listings:
                # Based on the HTML structure, look for placard-content divs
                placard_contents = soup.select("div.placard-content")
                log_action(self.logger, f"Found {len(placard_contents)} placard-content elements")
                
                # If no placard-content divs found, try alternative containers
                if not placard_contents:
                    placard_contents = soup.select(".property-card, article.placard")
                    log_action(self.logger, f"Found {len(placard_contents)} alternative property cards")
                
                for card in placard_contents:
                    try:
                        # Extract listing URL - look for any "More details" links
                        links = card.select(self.LISTING_SELECTORS['details_link'])
                        if not links:
                            continue
                            
                        # Use the first link with an href attribute
                        listing_url = None
                        for link in links:
                            if 'href' in link.attrs:
                                listing_url = link['href']
                                break
                                
                        if not listing_url or listing_url in processed_urls:
                            continue
                            
                        processed_urls.add(listing_url)
                        
                        # Extract details using the class method
                        details = self._extract_listing_details(card, self.LISTING_SELECTORS)
                        
                        # Combine address and location
                        full_address = details['address']
                        if full_address != "Address not available" and details['location']:
                            full_address = f"{full_address}, {details['location']}"
                        
                        # Create listing
                        listing = {
                            'address': full_address,
                            'price': details['price'],
                            'property_type': details['property_type'],
                            'url': listing_url
                        }
                        
                        listings.append(listing)
                        log_action(self.logger, f"Added listing from placard: {full_address}")
                        
                    except Exception as e:
                        self.logger.error(f"Error extracting listing from placard: {str(e)}")
            
            # Last resort - use Selenium to find elements
            if not listings and self.driver:
                try:
                    # Try to find "More details" links
                    elements = self.driver.find_elements(By.CSS_SELECTOR, "a[title^='More details for']")
                    log_action(self.logger, f"Found {len(elements)} detail links with Selenium")
                    
                    for element in elements:
                        try:
                            listing_url = element.get_attribute('href')
                            if not listing_url or listing_url in processed_urls:
                                continue
                                
                            processed_urls.add(listing_url)
                            
                            # Extract address from title
                            title = element.get_attribute('title')
                            address = title.replace('More details for ', '').split(' - ')[0] if title else "Address not available"
                            
                            # Create listing
                            listing = {
                                'address': address,
                                'price': "Price not extracted directly",
                                'property_type': "Type not extracted directly", 
                                'url': listing_url
                            }
                            
                            listings.append(listing)
                            log_action(self.logger, f"Added listing via Selenium: {address}")
                            
                        except Exception as e:
                            self.logger.error(f"Error in Selenium extraction: {str(e)}")
                            
                except Exception as e:
                    self.logger.error(f"Error in Selenium approach: {str(e)}")
        
        except Exception as e:
            self.logger.error(f"Error extracting listings: {str(e)}")
            self.logger.error(traceback.format_exc())
        
        # Also print them directly to console for immediate visibility
        print(f"\nExtracted {len(listings)} unique listings:")
        for i, listing in enumerate(listings):
            print(f"\nListing {i+1}:")
            for key, value in listing.items():
                print(f"  {key}: {value}")
        
        return listings 