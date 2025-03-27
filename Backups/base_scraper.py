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
        
    def _setup_driver(self) -> None:
        """Set up the Chrome WebDriver with appropriate options."""
        options = webdriver.ChromeOptions()
        if not self.debug_mode:
            options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-logging')
        options.add_argument('--log-level=3')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        # Create service with suppressed output
        service = webdriver.ChromeService(log_output=os.devnull)
        
        # Create the driver with the configured options and service
        self.driver = webdriver.Chrome(options=options, service=service)
        self.driver.set_window_size(1920, 1080)
        self.driver.implicitly_wait(self.wait_time)
    
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
    
    def _click_element(self, selector: str, wait_time: Optional[int] = None) -> bool:
        """Click an element safely with wait
        
        Args:
            selector: CSS selector for the element
            wait_time: Override the default wait time if needed
            
        Returns:
            bool: True if clicked successfully, False otherwise
        """
        try:
            wait = WebDriverWait(self.driver, wait_time or self.wait_time)
            element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            time.sleep(0.5)  # Small delay to ensure element is truly clickable
            
            # Log action
            if self.logger:
                self.logger.info(f"Clicking {selector}")
            
            element.click()
            time.sleep(1)  # Wait for action to complete
            return True
        except (TimeoutException, NoSuchElementException) as e:
            if self.logger:
                self.logger.error(f"Error clicking element {selector}: {str(e)}")
            return False
    
    def _send_keys(self, selector: str, text: str, press_enter: bool = False,
                  wait_time: Optional[int] = None) -> bool:
        """Send keys to an element safely with wait
        
        Args:
            selector: CSS selector for the element
            text: Text to send
            press_enter: Whether to press Enter after sending text
            wait_time: Override the default wait time if needed
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            wait = WebDriverWait(self.driver, wait_time or self.wait_time)
            element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            element.clear()
            
            # Log action
            if self.logger:
                self.logger.info(f"Entering text in {selector}")
            
            element.send_keys(text)
            
            if press_enter:
                time.sleep(0.5)  # Short pause
                element.send_keys(Keys.ENTER)
                
            time.sleep(1)  # Wait for action to complete
            return True
        except (TimeoutException, NoSuchElementException) as e:
            if self.logger:
                self.logger.error(f"Error sending keys to element {selector}: {str(e)}")
            return False
    
    def _wait_for_element(self, selector: str, wait_time: Optional[int] = None) -> bool:
        """Wait for an element to be present
        
        Args:
            selector: CSS selector for the element
            wait_time: Override the default wait time if needed
            
        Returns:
            bool: True if element is present, False otherwise
        """
        try:
            wait = WebDriverWait(self.driver, wait_time or self.wait_time)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            return True
        except TimeoutException:
            return False
    
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