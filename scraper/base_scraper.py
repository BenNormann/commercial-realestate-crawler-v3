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
import random

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
        options.add_argument('--enable-unsafe-swiftshader')
        
        # Suppress voice transcription and accessibility logs
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-features=TranslateUI')
        options.add_argument('--disable-features=VoiceTranscription')
        options.add_argument('--disable-accessibility-logging')
        options.add_argument('--disable-speech-api')
        options.add_argument('--suppress-message-center-popups')
        
        options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
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
        time.sleep(0.1)  # Quick wait for DOM updates

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
                # Quick delay after overlay removal
                time.sleep(random.uniform(0.1, 0.2))
                
                if self.logger:
                    self.logger.debug(f"Clicking {element_desc} (attempt {attempt+1}/{max_retries})")
                
                # Get the element if a selector was provided
                if isinstance(selector_or_element, str):
                    # Use smart wait for clickable element
                    if not self.smart_wait("clickable", selector_or_element, timeout=self.wait_time):
                        if self.logger:
                            self.logger.warning(f"Element not clickable within timeout: {element_desc}")
                        continue
                    element = self.driver.find_element(By.CSS_SELECTOR, selector_or_element)
                else:
                    element = selector_or_element
                
                # Make sure element is in viewport
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                # Quick delay after scrolling
                time.sleep(random.uniform(0.1, 0.2))
                
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
                        # Quick delay after click to let it register
                        time.sleep(random.uniform(0.1, 0.2))
                        return True
                    except Exception as e:
                        if i == len(click_methods) - 1:  # If this was the last method
                            if self.logger:
                                self.logger.warning(f"All click methods failed for {element_desc} on attempt {attempt+1}: {str(e)}")
                            break
                        # Otherwise continue to next method
                
                # If we reach here, all click methods failed on this attempt
                # Quick delay before retry
                time.sleep(random.uniform(0.1, 0.2))
                
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Click attempt {attempt+1} failed for {element_desc}: {str(e)}")
                # Quick delay before retry
                time.sleep(random.uniform(0.1, 0.2))
        
        # If we reach here, all attempts failed
        if self.logger:
            self.logger.error(f"Failed to click {element_desc} after {max_retries} attempts")
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
            # Quick delay after overlay removal
            time.sleep(random.uniform(0.1, 0.2))
            
            if self.logger:
                self.logger.debug(f"Entering text in {element_desc}")
            
            # Use smart wait for element to be clickable
            if not self.smart_wait("clickable", selector, timeout=self.wait_time):
                if self.logger:
                    self.logger.error(f"Input element not clickable within timeout: {element_desc}")
                return False
            
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            
            # Click to focus the element
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            element.click()
            # Quick delay after click
            time.sleep(random.uniform(0.05, 0.1))
            
            # Clear the field if requested
            if clear_first:
                element.clear()
                # Quick delay after clear
                time.sleep(random.uniform(0.05, 0.1))
                # Double check it's cleared with JavaScript
                self.driver.execute_script("arguments[0].value = '';", element)
                # Quick delay after JS clear
                time.sleep(random.uniform(0.05, 0.1))
            
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
            
            # Quick delay for input to register
            time.sleep(random.uniform(0.1, 0.2))
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
            # Use smart wait for page to load instead of fixed sleep
            if not self.smart_wait("page_load", timeout=wait_time):
                if self.logger:
                    self.logger.warning(f"Page did not fully load within {wait_time} seconds")
            
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
    
    def update_progress(self, progress: float, progress_callback: Optional[Callable[[float], None]] = None) -> None:
        """Update progress with callback if provided
        
        Args:
            progress: Progress value from 0.0 to 1.0
            progress_callback: Optional callback to report progress
        """
        if progress_callback:
            progress_callback(progress)
    
    def smart_wait(self, 
                   condition_type: str = "presence", 
                   selector: str = None, 
                   expected_count: int = None,
                   min_count: int = 1,
                   timeout: int = 15,
                   stable_time: float = 1.0,
                   human_delay: bool = True) -> bool:
        """Smart wait function that waits for specific conditions with dynamic timeouts
        
        Args:
            condition_type: Type of condition to wait for:
                - "presence": Wait for element(s) to be present in DOM
                - "visible": Wait for element(s) to be visible
                - "clickable": Wait for element to be clickable
                - "count": Wait for a specific number of elements
                - "min_count": Wait for at least min_count elements
                - "stable": Wait for content to stabilize (no changes for stable_time)
                - "page_load": Wait for page to finish loading
            selector: CSS selector for elements (required for most conditions)
            expected_count: Expected number of elements (for "count" condition)
            min_count: Minimum number of elements (for "min_count" condition)
            timeout: Maximum time to wait in seconds
            stable_time: Time to wait for stability in seconds
            human_delay: Whether to add small human-like delays
            
        Returns:
            bool: True if condition was met, False if timeout occurred
        """
        start_time = time.time()
        
        if self.logger:
            self.logger.debug(f"Smart wait: {condition_type} for '{selector}' (timeout: {timeout}s)")
        
        # Add initial human-like delay
        if human_delay:
            time.sleep(random.uniform(0.05, 0.1))
        
        try:
            if condition_type == "page_load":
                # Wait for page to finish loading
                WebDriverWait(self.driver, timeout).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                if human_delay:
                    time.sleep(random.uniform(0.1, 0.2))
                return True
                
            elif condition_type == "presence":
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if human_delay:
                    time.sleep(random.uniform(0.05, 0.1))
                return True
                
            elif condition_type == "visible":
                WebDriverWait(self.driver, timeout).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
                )
                if human_delay:
                    time.sleep(random.uniform(0.05, 0.1))
                return True
                
            elif condition_type == "clickable":
                WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                if human_delay:
                    time.sleep(random.uniform(0.05, 0.1))
                return True
                
            elif condition_type in ["count", "min_count"]:
                # Wait for specific number of elements
                target_count = expected_count if condition_type == "count" else min_count
                
                def count_condition(driver):
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    current_count = len(elements)
                    if condition_type == "count":
                        return current_count == target_count
                    else:  # min_count
                        return current_count >= target_count
                
                WebDriverWait(self.driver, timeout).until(count_condition)
                if human_delay:
                    time.sleep(random.uniform(0.1, 0.2))
                return True
                
            elif condition_type == "stable":
                # Wait for content to stabilize (no changes for stable_time)
                last_count = 0
                stable_start = None
                
                while time.time() - start_time < timeout:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        current_count = len(elements)
                        
                        if current_count == last_count and current_count >= min_count:
                            if stable_start is None:
                                stable_start = time.time()
                            elif time.time() - stable_start >= stable_time:
                                if self.logger:
                                    self.logger.debug(f"Content stabilized at {current_count} elements")
                                if human_delay:
                                    time.sleep(random.uniform(0.1, 0.2))
                                return True
                        else:
                            stable_start = None
                            last_count = current_count
                        
                        time.sleep(0.1)  # Check every 100ms for faster response
                        
                    except Exception:
                        time.sleep(0.1)
                        continue
                
                return False
                
        except TimeoutException:
            if self.logger:
                self.logger.warning(f"Smart wait timeout after {timeout}s for {condition_type}: '{selector}'")
            return False
        except Exception as e:
            if self.logger:
                self.logger.error(f"Smart wait error: {str(e)}")
            return False
        
        return False

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