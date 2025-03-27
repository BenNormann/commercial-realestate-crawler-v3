from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

class BaseScraper(ABC):
    """Base scraper class for real estate websites"""
    
    def __init__(self, debug_mode: bool = False):
        """Initialize the scraper
        
        Args:
            debug_mode: Whether to run in debug mode (shows browser)
        """
        self.debug_mode = debug_mode
        self.driver = None
        self.wait_time = 10  # Default wait time in seconds
        self.logger = None
        self.base_url = None  # Should be set by child classes
        
    def _setup_driver(self) -> None:
        """Set up the Chrome WebDriver with appropriate options."""
        options = webdriver.ChromeOptions()
        if not self.debug_mode:
            options.add_argument('--headless=new')  # Use new headless mode
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-logging')
        options.add_argument('--log-level=3')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--enable-unsafe-swiftshader')        # Add a flag to disable WebGL completeSwitches', ['enable-logging', 'enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Create service with suppressed output
        service = webdriver.ChromeService(log_output=os.devnull)
        
        # Create the driver with the configured options and service
        self.driver = webdriver.Chrome(options=options, service=service)
        self.driver.set_window_size(1920, 1080)
        self.driver.implicitly_wait(self.wait_time)
        
        # Execute CDP commands to prevent detection
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        })
    
    def _close_driver(self) -> None:
        """Close the WebDriver if it exists"""
        if self.driver:
            # In debug mode, keep window open until user input
            if self.debug_mode:
                if self.logger:
                    self.logger.info("Debug mode: Browser window will stay open. Press Enter to close...")
                try:
                    input("Debug mode: Browser window will stay open. Press Enter to close...")
                except EOFError:
                    pass  # Handle EOFError in case running in non-interactive context
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error waiting for input: {str(e)}")
            
            # Now close the driver
            self.driver.quit()
            self.driver = None
    
    def _remove_overlays(self) -> None:
        """Remove any overlays using JavaScript"""
        self.driver.execute_script("""
            // Only remove overlays that are not the filters modal
            var overlays = document.querySelectorAll('div.csgp-modal-overlay, div.csgp-modal.ng-isolate-scope');
            overlays.forEach(function(overlay) {
                // Skip the filters modal
                if (!overlay.classList.contains('advanced-filters-modal')) {
                    overlay.remove();
                }
            });
            
            // Remove any fixed position elements that might block interaction
            // but not if they're part of the filters modal
            var fixedElements = document.querySelectorAll('div[style*="position: fixed"]');
            fixedElements.forEach(function(element) {
                if (!element.closest('.advanced-filters-modal')) {
                    element.remove();
                }
            });
            
            // Ensure body is scrollable unless filters modal is open
            if (!document.querySelector('.advanced-filters-modal')) {
                document.body.style.overflow = 'auto';
                document.body.style.position = 'relative';
                document.body.style.height = 'auto';
            }
        """)
        time.sleep(0.5)  # Short wait for DOM updates

    def _wait_for_element_interactable(self, selector: str, timeout: int = 10) -> bool:
        """Wait for an element to be truly interactable (not blocked by overlays)"""
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                # First remove any overlays
                self._remove_overlays()
                
                # Check if element exists and is interactable
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_displayed():
                    # Check if element is actually clickable
                    try:
                        # Try to scroll element into view
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                        time.sleep(0.2)
                        
                        # Check if element is in viewport
                        is_in_viewport = self.driver.execute_script("""
                            var element = arguments[0];
                            var rect = element.getBoundingClientRect();
                            return (
                                rect.top >= 0 &&
                                rect.left >= 0 &&
                                rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                                rect.right <= (window.innerWidth || document.documentElement.clientWidth)
                            );
                        """, element)
                        
                        if is_in_viewport:
                            return True
                    except:
                        pass
                
                time.sleep(0.5)
            return False
        except:
            return False

    def click_element(self, selector_or_element, element_name: str = "", max_retries: int = 3) -> bool:
        """Click an element with comprehensive retry logic and multiple click strategies
        
        Args:
            selector_or_element: Either a CSS selector string or a WebElement
            element_name: Name of the element for logging (optional)
            max_retries: Maximum number of retry attempts
            
        Returns:
            bool: True if clicked successfully, False otherwise
        """
        # Set element description for logging
        element_desc = element_name if element_name else (
            selector_or_element if isinstance(selector_or_element, str) else "element"
        )
        
        for attempt in range(max_retries):
            try:
                # First remove any overlays
                self._remove_overlays()
                time.sleep(0.3)
                
                if self.logger:
                    self.logger.debug(f"Clicking {element_desc} (attempt {attempt+1}/{max_retries})")
                
                # Get the element if a selector was provided
                if isinstance(selector_or_element, str):
                    wait = WebDriverWait(self.driver, self.wait_time)
                    element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector_or_element)))
                else:
                    element = selector_or_element
                
                # Make sure element is in viewport
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.3)
                
                # Try multiple click strategies
                click_methods = [
                    # Method 1: JavaScript click
                    lambda: self.driver.execute_script("arguments[0].click();", element),
                    # Method 2: Standard click
                    lambda: element.click(),
                    # Method 3: Action chains
                    lambda: ActionChains(self.driver).move_to_element(element).click().perform()
                ]
                
                for i, click_method in enumerate(click_methods):
                    try:
                        click_method()
                        time.sleep(0.3)  # Wait for click to register
                        return True
                    except Exception as e:
                        if i == len(click_methods) - 1:  # If this was the last method
                            if self.logger:
                                self.logger.warning(f"All click methods failed for {element_desc} on attempt {attempt+1}: {str(e)}")
                            break
                        # Otherwise continue to next method
                
                # If we reach here, all click methods failed on this attempt
                time.sleep(0.5)  # Wait before retry
                
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Click attempt {attempt+1} failed for {element_desc}: {str(e)}")
                time.sleep(0.5)  # Wait before retry
        
        # If we reach here, all attempts failed
        if self.logger:
            self.logger.error(f"Failed to click {element_desc} after {max_retries} attempts")
        return False

    def _handle_intercepted_click(self, selector: str, overlay_selector: str = "div.csgp-modal-overlay") -> bool:
        """Handle a click that was intercepted by an overlay
        
        Args:
            selector: The selector of the element we want to click
            overlay_selector: The selector of the overlay to remove
            
        Returns:
            bool: True if click was successful, False otherwise
        """
        try:
            # Try clicking on the overlay to close it
            overlay = self.driver.find_element(By.CSS_SELECTOR, overlay_selector)
            overlay.click()
            time.sleep(1)
            
            # Try clicking the element again
            return self.click_element(selector)
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Error handling overlay: {str(e)}")
            return False

    def input_text_with_wait(self, selector: str, text: str, element_name: str = "", press_enter: bool = False, clear_first: bool = True) -> bool:
        """Input text into an element with wait and robust handling
        
        Args:
            selector: The CSS selector for the element
            text: Text to input
            element_name: Name of the element for logging (optional)
            press_enter: Whether to press Enter after inputting text
            clear_first: Whether to clear the input field first
            
        Returns:
            bool: True if input successful, False otherwise
        """
        element_desc = element_name if element_name else selector
        
        try:
            # First remove any overlays
            self._remove_overlays()
            time.sleep(0.5)
            
            if self.logger:
                self.logger.debug(f"Entering text in {element_desc}")
            
            # Wait for element to be present and clickable
            wait = WebDriverWait(self.driver, self.wait_time)
            element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            
            # Click to focus the element
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            element.click()
            time.sleep(0.2)
            
            # Clear the field if requested
            if clear_first:
                element.clear()
                time.sleep(0.2)
                # Double check it's cleared with JavaScript
                self.driver.execute_script("arguments[0].value = '';", element)
                time.sleep(0.2)
            
            # Try multiple methods to input text
            try:
                # Method 1: Direct send_keys
                element.send_keys(text)
            except Exception:
                try:
                    # Method 2: JavaScript value setting
                    self.driver.execute_script("arguments[0].value = arguments[1];", element, text)
                    # Trigger input event
                    self.driver.execute_script("""
                        var element = arguments[0];
                        var event = new Event('input', { bubbles: true });
                        element.dispatchEvent(event);
                    """, element)
                except Exception:
                    # Method 3: Action chains
                    ActionChains(self.driver).move_to_element(element).click().send_keys(text).perform()
            
            # Press Enter if requested
            if press_enter:
                time.sleep(0.3)
                element.send_keys(Keys.ENTER)
            
            time.sleep(0.5)  # Wait for input to register
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error inputting text to {element_desc}: {str(e)}")
            return False
    
    def verify_page_load(self, domain: str, wait_time: int = 5, exact_match: bool = False) -> bool:
        """Verify that the page has loaded correctly and we're on the right domain
        
        Args:
            domain: The domain or URL part we expect to be in the current URL
            wait_time: How long to wait for the page to load
            exact_match: Whether to require an exact match (True) or partial match (False)
            
        Returns:
            bool: True if we're on the right page, False otherwise
        """
        try:
            # Wait for page to load
            time.sleep(wait_time)
            
            # Get current URL
            current_url = self.driver.current_url.lower()
            domain = domain.lower()
            
            # Check if we're on the right page
            is_match = (current_url == domain) if exact_match else (domain in current_url)
            
            if not is_match:
                if self.logger:
                    self.logger.error(f"Failed to reach {domain}. Current URL: {current_url}")
                return False
                
            if self.logger:
                self.logger.info(f"Successfully loaded page: {current_url}")
                self.logger.info(f"Page title: {self.driver.title}")
                
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error verifying page load: {str(e)}")
            return False
    
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
                details[field] = element.text.strip() if element else f"{field} not available"
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error extracting {field}: {str(e)}")
                details[field] = f"{field} not available"
        return details

    def update_progress(self, progress: float, progress_callback: Optional[Callable[[float], None]] = None) -> None:
        """Update progress with callback if provided
        
        Args:
            progress: Progress value from 0.0 to 1.0
            progress_callback: Optional callback to report progress
        """
        if progress_callback:
            progress_callback(progress)
    
    @abstractmethod
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
        pass 