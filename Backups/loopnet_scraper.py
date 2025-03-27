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
        'price_dropdown': "#quickSearchFilters > div.filters > div:nth-child(6) > div > button",
        'min_price_box': "#quickSearchFilters > div.filters > div:nth-child(6) > div > div > form > div > div > div > div.range-container > div.range-from > input",
        'max_price_box': "#quickSearchFilters > div.filters > div:nth-child(6) > div > div > form > div > div > div > div.range-container > div.range-to > input",
        'other_filters_button': "#quickSearchFilters > div.filters > div:nth-child(15) > button",
        'custom_date_checkbox': "#top > section.master > div.csgp-modal.ng-isolate-scope.light.advanced-filters-modal > div.csgp-modal-container.csgp-modal-dialog.container > div > click-event-bridge > section > form > div:nth-child(3) > section.column-06.column-medium-12.col-criteria > div:nth-child(8) > section.column-06.date-entered > div > div.pill-group > div:nth-child(2) > label",
        'start_date_box': "#top > section.master > div.csgp-modal.ng-isolate-scope.light.advanced-filters-modal > div.csgp-modal-container.csgp-modal-dialog.container > div > click-event-bridge > section > form > div:nth-child(3) > section.column-06.column-medium-12.col-criteria > div:nth-child(8) > section.column-06.date-entered > div > div.custom-time-period > div > div > div.range-from > datepicker > input",
        'search_button': "#top > section.master > div.csgp-modal.ng-isolate-scope.light.advanced-filters-modal > div.csgp-modal-container.csgp-modal-dialog.container > div > click-event-bridge > div > button.button.primary.submit",
        'search_results_container': "#dataSection > div.main-content > div.placard-container",
        'popup_close_button': "#top > section.master > div.csgp-modal.ng-isolate-scope.light.sso-form-modal-secondary.reg-overlay-target.ng-hide > div.csgp-modal-container.csgp-modal-dialog.container > button"
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
            # First try to find and click the specific close button
            close_button = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#top > section.master > div.csgp-modal.ng-isolate-scope.light.sso-form-modal-secondary.reg-overlay-target.save-search-reg-overlay-show > div.csgp-modal-container.csgp-modal-dialog.container > button"))
            )
            if close_button.is_displayed():
                close_button.click()
                time.sleep(1)
                return True
                
            # If that doesn't work, try the general close button selector
            close_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.csgp-modal-close.ln-icon-close-hollow")
            for button in close_buttons:
                try:
                    if button.is_displayed():
                        button.click()
                        time.sleep(0.5)
                        return True
                except:
                    continue
            
            # If still no success, try to remove overlays using JavaScript
            self.driver.execute_script("""
                var overlays = document.querySelectorAll('div.csgp-modal-overlay, div.csgp-modal.ng-isolate-scope');
                overlays.forEach(function(overlay) {
                    overlay.remove();
                });
            """)
            time.sleep(1)
            
            return True
        except Exception as e:
            if self.logger:
                self.logger.debug(f"No popup to close: {str(e)}")
            return False

    def _click_search_button(self) -> bool:
        """Click the search button with multiple fallback methods"""
        try:
            # First try to remove any overlays
            self._try_close_popup()
            time.sleep(1)
            
            # Try to find the search button
            search_button = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.SELECTORS['search_button']))
            )
            
            # Try multiple methods to click the button
            try:
                # Method 1: Direct click
                search_button.click()
            except:
                try:
                    # Method 2: JavaScript click
                    self.driver.execute_script("arguments[0].click();", search_button)
                except:
                    # Method 3: Move to element and click
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", search_button)
                    time.sleep(0.5)
                    search_button.click()
            
            time.sleep(2)  # Wait for search to start
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to click search button: {str(e)}")
            return False
    
    def search(self, property_types: List[str], location: str, min_price: str = None,
              max_price: str = None, start_date: datetime = None, end_date: datetime = None,
              progress_callback: Optional[Callable[[float], None]] = None) -> List[Dict[str, Any]]:
        """Search for listings on LoopNet with the given parameters"""
        results = []
        
        try:
            # Setup driver
            self._setup_driver()
            self.update_progress(0.1, progress_callback)
            
            # Navigate to LoopNet
            self.driver.get(self.base_url)
            log_action(self.logger, "Navigating to LoopNet")
            time.sleep(2)
            
            # Enter location - close popup if this fails
            try:
                self._send_keys(self.SELECTORS['location_box'], location, press_enter=True)
                log_action(self.logger, f"Entering location: {location}")
            except Exception:
                self._try_close_popup()
                self._send_keys(self.SELECTORS['location_box'], location, press_enter=True)
                
            self.update_progress(0.2, progress_callback)
            time.sleep(1)
            
            # Click sale/lease dropdown and select For Sale
            try:
                self._click_element(self.SELECTORS['sale_lease_dropdown'])
                self._click_element(self.SELECTORS['for_sale_button'])
                log_action(self.logger, "Setting search to For Sale")
            except Exception:
                self._try_close_popup()
                self._click_element(self.SELECTORS['sale_lease_dropdown'])
                self._click_element(self.SELECTORS['for_sale_button'])
                
            self.update_progress(0.3, progress_callback)
            
            # Select property types
            try:
                self._click_element(self.SELECTORS['property_type_dropdown'])
                time.sleep(1)
            except Exception:
                self._try_close_popup()
                self._click_element(self.SELECTORS['property_type_dropdown'])
            
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
                        self._click_element(property_type_selectors[prop_type_lower])
                        log_action(self.logger, f"Selecting property type: {prop_type}")
                    except Exception:
                        self._try_close_popup()
                        self._click_element(property_type_selectors[prop_type_lower])
            
            # Click outside to close dropdown
            self.driver.execute_script("document.activeElement.blur();")
            time.sleep(1)
            self.update_progress(0.4, progress_callback)
            
            # Set price range if provided
            if min_price or max_price:
                try:
                    self._click_element(self.SELECTORS['price_dropdown'])
                    time.sleep(1)
                except Exception:
                    self._try_close_popup()
                    self._click_element(self.SELECTORS['price_dropdown'])
                
                if min_price:
                    self._send_keys(self.SELECTORS['min_price_box'], min_price)
                    log_action(self.logger, f"Setting min price: {min_price}")
                
                if max_price:
                    self._send_keys(self.SELECTORS['max_price_box'], max_price)
                    log_action(self.logger, f"Setting max price: {max_price}")
                
                # Click outside to close dropdown
                self.driver.execute_script("document.activeElement.blur();")
                time.sleep(1)
            
            self.update_progress(0.5, progress_callback)
            
            # Set date filter if start_date is provided
            if start_date:
                # Open Other Filters
                try:
                    self._click_element(self.SELECTORS['other_filters_button'])
                    time.sleep(2)
                except Exception:
                    self._try_close_popup()
                    self._click_element(self.SELECTORS['other_filters_button'])
                
                # Enable custom date range
                try:
                    self._click_element(self.SELECTORS['custom_date_checkbox'])
                    log_action(self.logger, f"Enabling custom date filter")
                    time.sleep(1)
                except Exception:
                    self._try_close_popup()
                    self._click_element(self.SELECTORS['custom_date_checkbox'])
                
                # Format date as mm/dd/yyyy
                formatted_date = start_date.strftime("%m/%d/%Y")
                self._send_keys(self.SELECTORS['start_date_box'], formatted_date)
                log_action(self.logger, f"Setting start date: {formatted_date}")
                time.sleep(1)
                
                # Click search button to apply filters and search
                try:
                    self._click_search_button()
                    log_action(self.logger, f"Clicking search button")
                except ElementClickInterceptedException:
                    # If the search button is intercepted by an overlay, try closing it directly
                    log_action(self.logger, "Search button click intercepted by overlay, trying to close it")
                    try:
                        # Try clicking on the overlay to close it
                        overlay = self.driver.find_element(By.CSS_SELECTOR, "div.csgp-modal-overlay")
                        overlay.click()
                        time.sleep(1)
                        
                        # Try clicking the search button again
                        self._click_search_button()
                    except Exception as e:
                        self.logger.warning(f"Error handling overlay: {str(e)}")
                        
                        # As a last resort, try to click the search button with JavaScript
                        log_action(self.logger, "Trying to click search button with JavaScript")
                        try:
                            self.driver.execute_script("arguments[0].click();", 
                                                     self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS['search_button']))
                        except Exception as js_error:
                            self.logger.error(f"JavaScript click also failed: {str(js_error)}")
            
            self.update_progress(0.7, progress_callback)
            time.sleep(5)  # Wait for search results to load
            
            # Extract listings from search results
            results = self._extract_listings()
            
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
    
    def _click_element(self, selector: str, wait_time: int = 10) -> bool:
        """Click an element with retry logic to handle popups
        
        Args:
            selector: CSS selector for the element to click
            wait_time: How long to wait for the element to be clickable
            
        Returns:
            True if element was successfully clicked, False otherwise
        """
        try:
            # First try using the base class method
            success = super()._click_element(selector, wait_time)
            if success:
                return True
                
            # If it fails, try closing popups and retry
            log_action(self.logger, f"Click failed for {selector}, attempting to close popups and retry")
            if self._try_close_popup():
                time.sleep(0.5)
                # Retry the click after closing popup
                return super()._click_element(selector, wait_time)
                
            return False
        except ElementClickInterceptedException:
            # If element is found but not clickable, likely a popup is in the way
            log_action(self.logger, f"Element click intercepted for {selector}, attempting to close popups")
            if self._try_close_popup():
                time.sleep(0.5)
                # Retry the click after closing popup
                return super()._click_element(selector, wait_time)
            return False
        except Exception as e:
            self.logger.warning(f"Error clicking element {selector}: {str(e)}")
            return False
    
    def _extract_listings(self) -> List[Dict[str, Any]]:
        """Extract listing details from search results page"""
        listings = []
        processed_urls = set()  # Track URLs to avoid duplicates
        log_action(self.logger, "Extracting listings")
        
        try:
            # Get the page source and parse with BeautifulSoup
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
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
                    links = card.select("a[title*='More details']")
                    if not links:
                        continue
                        
                    # Use the first link with an href attribute
                    listing_url = None
                    for link in links:
                        if 'href' in link.attrs:
                            listing_url = link['href']
                            break
                            
                    if not listing_url:
                        continue
                        
                    # Skip duplicates
                    if listing_url in processed_urls:
                        continue
                        
                    processed_urls.add(listing_url)
                    
                    # Extract address - from the h4 header
                    address = "Address not available"
                    header = card.select_one("h4 a")
                    if header:
                        address = header.text.strip()
                    
                    # Extract location (city/state) - from subtitle-beta
                    location = ""
                    subtitle = card.select_one("a.subtitle-beta")
                    if subtitle:
                        location = subtitle.text.strip()
                        
                    # If we have both address and location, combine them
                    if address != "Address not available" and location:
                        full_address = f"{address}, {location}"
                    else:
                        full_address = address
                    
                    # Extract price - from the data-points-2c list
                    price = "Price not available"
                    price_elem = card.select_one("li[name='Price']")
                    if price_elem:
                        price = price_elem.text.strip()
                    
                    # Extract property type - from the data-points-2c list
                    # Usually the third li element contains info like "3,591 SF Retail Building"
                    prop_type = "Type not available"
                    data_points = card.select("ul.data-points-2c li")
                    if len(data_points) >= 3:
                        prop_type_text = data_points[2].text.strip()
                        if "SF" in prop_type_text and any(building_type in prop_type_text.lower() for building_type in ["retail", "office", "industrial", "multifamily"]):
                            prop_type = prop_type_text
                    
                    # Create listing
                    listing = {
                        'address': full_address,
                        'price': price,
                        'property_type': prop_type,
                        'url': listing_url
                    }
                    
                    listings.append(listing)
                    log_action(self.logger, f"Added listing: {full_address} at {listing_url}")
                    
                except Exception as e:
                    self.logger.error(f"Error extracting listing from placard: {str(e)}")
            
            # If no listings found, try a more general approach
            if not listings:
                # Look for any "More details" links on the page
                detail_links = soup.select("a[title*='More details for']")
                log_action(self.logger, f"Found {len(detail_links)} detail links")
                
                for link in detail_links:
                    try:
                        if 'href' not in link.attrs:
                            continue
                            
                        listing_url = link['href']
                        if listing_url in processed_urls:
                            continue
                            
                        processed_urls.add(listing_url)
                        
                        # Extract address from the title attribute
                        full_address = "Address not available"
                        if 'title' in link.attrs and 'More details for ' in link['title']:
                            title_parts = link['title'].replace('More details for ', '').split(' - ')
                            if title_parts:
                                full_address = title_parts[0]
                                # Try to extract type from title if available
                                if len(title_parts) > 1 and 'for ' in title_parts[1]:
                                    prop_type = title_parts[1].split('for ')[0].strip()
                        
                        # Try to find parent elements with price info
                        price = "Price not available"
                        prop_type = "Type not available"
                        
                        # Find any parent with price info
                        parent = link.parent
                        for _ in range(4):  # Check a few levels up
                            if not parent:
                                break
                                
                            # Look for price
                            price_elem = parent.select_one("[name='Price'], [class*='price']")
                            if price_elem and price_elem.text and '$' in price_elem.text:
                                price = price_elem.text.strip()
                                break
                                
                            parent = parent.parent
                        
                        # Create listing
                        listing = {
                            'address': full_address,
                            'price': price,
                            'property_type': prop_type,
                            'url': listing_url
                        }
                        
                        listings.append(listing)
                        log_action(self.logger, f"Added listing from detail link: {full_address}")
                        
                    except Exception as e:
                        self.logger.error(f"Error extracting from detail link: {str(e)}")
            
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
        
        # Log results
        self.logger.info(f"Extracted {len(listings)} unique listings:")
        for i, listing in enumerate(listings):
            self.logger.info(f"Listing {i+1}:")
            for key, value in listing.items():
                self.logger.info(f"  {key}: {value}")
        
        # Also print them directly to console for immediate visibility
        print(f"\nExtracted {len(listings)} unique listings:")
        for i, listing in enumerate(listings):
            print(f"\nListing {i+1}:")
            for key, value in listing.items():
                print(f"  {key}: {value}")
        
        return listings 