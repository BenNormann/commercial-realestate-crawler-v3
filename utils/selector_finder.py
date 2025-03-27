from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time

class SelectorFinder:
    def __init__(self, url):
        self.url = url
        self.driver = None
        self.wait = None
    
    def start(self):
        """Start the interactive selector finder"""
        try:
            # Initialize the browser
            options = webdriver.ChromeOptions()
            options.add_argument('--start-maximized')
            self.driver = webdriver.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, 10)
            
            # Navigate to the URL
            print(f"\nNavigating to {self.url}...")
            self.driver.get(self.url)
            
            print("\nSelector Finder is ready!")
            print("Enter CSS selectors to test (press Enter without input to exit):")
            
            while True:
                selector = input("\nEnter selector: ").strip()
                
                if not selector:
                    break
                
                try:
                    # Try to find elements with the selector
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if elements:
                        print(f"\nFound {len(elements)} elements with selector '{selector}':")
                        
                        # Highlight each element
                        for i, element in enumerate(elements[:5], 1):
                            try:
                                # Scroll element into view
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                                time.sleep(0.5)
                                
                                # Highlight element
                                self.driver.execute_script(
                                    "arguments[0].style.border = '2px solid red';", element
                                )
                                
                                # Get element text
                                text = element.text.strip()
                                print(f"\nElement {i}:")
                                print(f"Text: {text[:100]}{'...' if len(text) > 100 else ''}")
                                
                                # Wait a moment before highlighting next element
                                time.sleep(1)
                                
                                # Remove highlight
                                self.driver.execute_script(
                                    "arguments[0].style.border = '';", element
                                )
                                
                            except Exception as e:
                                print(f"Error highlighting element {i}: {str(e)}")
                        
                        if len(elements) > 5:
                            print(f"\n... and {len(elements) - 5} more elements")
                    else:
                        print(f"\nNo elements found with selector '{selector}'")
                
                except Exception as e:
                    print(f"Error testing selector: {str(e)}")
            
            print("\nSelector Finder finished!")
            
        except Exception as e:
            print(f"Error: {str(e)}")
        
        finally:
            if self.driver:
                self.driver.quit() 