import json
import time
import logging
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re

class FlipkartAutomation:
    def __init__(self, config_file: str = "config.json"):
        """Initialize the Flipkart automation with configuration."""
        self.config = self.load_config(config_file)
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.setup_logging()
        
    def load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file {config_file} not found")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in configuration file {config_file}")
    
    def setup_logging(self):
        """Setup logging for the automation."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('flipkart_automation.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_driver(self) -> webdriver.Chrome:
        """Setup Chrome WebDriver with appropriate options."""
        chrome_options = Options()
        
        # Add options for better automation
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        if self.config["automation_settings"]["headless_mode"]:
            chrome_options.add_argument("--headless")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(self.config["automation_settings"]["page_load_timeout"])
            self.wait = WebDriverWait(self.driver, self.config["automation_settings"]["wait_time"])
            self.logger.info("Chrome WebDriver initialized successfully")
            return self.driver
        except Exception as e:
            self.logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise
    
    def navigate_to_flipkart(self):
        """Navigate to Flipkart homepage."""
        try:
            if not self.driver:
                raise ValueError("WebDriver not initialized")
                
            self.logger.info("Navigating to Flipkart...")
            self.driver.get("https://www.flipkart.com")
            
            # Wait for page to load
            if self.wait:
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Handle login if credentials are provided
            if self.config["user_credentials"]["email"] and self.config["user_credentials"]["password"]:
                self.login()
            else:
                self.close_login_popup()
                
        except Exception as e:
            self.logger.error(f"Failed to navigate to Flipkart: {str(e)}")
            raise
    
    def search_iphones(self, search_query: str) -> List[Dict]:
        """Search for iPhones and return list of products with prices."""
        try:
            if not self.driver or not self.wait:
                raise ValueError("WebDriver not initialized")
                
            self.logger.info(f"Searching for: {search_query}")
            
            # Find search box and enter search query
            search_selectors = ["//input[@name='q']", "//input[@placeholder='Search for products, brands and more']", "//input[@class='_3704LK']"]
            search_box = None
            
            for selector in search_selectors:
                try:
                    search_box = self.wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                    break
                except TimeoutException:
                    continue
                    
            if not search_box:
                raise Exception("Could not find search box")
                
            search_box.clear()
            search_box.send_keys(search_query)
            
            # Click search button
            search_button_selectors = ["//button[@type='submit']", "//button[@class='L0Z3Pu']", "//button[contains(@class, 'submit')]"]
            
            for selector in search_button_selectors:
                try:
                    search_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    search_button.click()
                    break
                except TimeoutException:
                    continue
            
            # Wait for results to load
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//div[@data-id or contains(@class, '_13oc-S') or contains(@class, '_1AtVbE')]")))
            
            # Apply filters from configuration
            self.apply_filters()
            
            return self.extract_product_info()
            
        except Exception as e:
            self.logger.error(f"Failed to search for products: {str(e)}")
            return []
    
    def apply_filters(self):
        """Apply filters from configuration."""
        try:
            filters = self.config.get("filters", {})
            
            # Apply brand filter
            brand = filters.get("brand")
            if brand:
                self.apply_brand_filter(brand)
                
            # Apply sort order
            sort_by = filters.get("sort_by", "price_low_to_high")
            self.apply_sort_filter(sort_by)
            
            # Apply price range filter via UI if available
            self.apply_price_range_filter()
            
        except Exception as e:
            self.logger.warning(f"Failed to apply some filters: {str(e)}")
    
    def apply_brand_filter(self, brand: str):
        """Apply brand filter in the UI."""
        try:
            # Look for brand filter section
            brand_filter_selectors = [
                f"//div[contains(text(), 'Brand')]//following::div//label[contains(text(), '{brand}')]",
                f"//div[@class='_3879cV']//label[contains(text(), '{brand}')]//input[@type='checkbox']",
                f"//input[@type='checkbox' and @value='{brand}']"
            ]
            
            for selector in brand_filter_selectors:
                try:
                    brand_checkbox = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    if not brand_checkbox.is_selected():
                        brand_checkbox.click()
                        self.logger.info(f"Applied brand filter: {brand}")
                        time.sleep(2)  # Wait for filter to apply
                    return
                except TimeoutException:
                    continue
                    
            self.logger.warning(f"Could not find brand filter for: {brand}")
            
        except Exception as e:
            self.logger.warning(f"Failed to apply brand filter: {str(e)}")
    
    def apply_sort_filter(self, sort_by: str):
        """Apply sort filter."""
        try:
            # Map sort options
            sort_mapping = {
                "price_low_to_high": "Price -- Low to High",
                "price_high_to_low": "Price -- High to Low",
                "popularity": "Popularity",
                "newest": "Newest First"
            }
            
            sort_text = sort_mapping.get(sort_by, sort_mapping["price_low_to_high"])
            
            # Click sort dropdown
            sort_selectors = [
                "//div[contains(text(), 'Sort By')]",
                "//div[@class='_10UF8M']//div[contains(text(), 'Sort')]",
                "//select[contains(@class, 'sort') or @name='sort']"
            ]
            
            for selector in sort_selectors:
                try:
                    sort_dropdown = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    sort_dropdown.click()
                    
                    # Select sort option
                    sort_option = self.wait.until(EC.element_to_be_clickable((By.XPATH, f"//div[contains(text(), '{sort_text}')]")))
                    sort_option.click()
                    
                    self.logger.info(f"Applied sort filter: {sort_text}")
                    time.sleep(2)  # Wait for sort to apply
                    return
                    
                except TimeoutException:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"Failed to apply sort filter: {str(e)}")
    
    def apply_price_range_filter(self):
        """Apply price range filter via UI if available."""
        try:
            min_price = self.config["search_settings"]["min_price"]
            max_price = self.config["search_settings"]["max_price"]
            
            # Try to find price filter inputs
            min_price_input = None
            max_price_input = None
            
            price_input_selectors = [
                "//input[@placeholder='Min' or @name='min' or contains(@class, 'min-price')]",
                "//input[@placeholder='Max' or @name='max' or contains(@class, 'max-price')]"
            ]
            
            try:
                min_price_input = self.driver.find_element(By.XPATH, price_input_selectors[0])
                max_price_input = self.driver.find_element(By.XPATH, price_input_selectors[1])
                
                if min_price_input and max_price_input:
                    min_price_input.clear()
                    min_price_input.send_keys(str(min_price))
                    
                    max_price_input.clear()
                    max_price_input.send_keys(str(max_price))
                    
                    # Apply filter
                    apply_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Apply') or contains(@class, 'apply')]")
                    apply_button.click()
                    
                    self.logger.info(f"Applied price range filter: ₹{min_price} - ₹{max_price}")
                    time.sleep(2)
                    
            except NoSuchElementException:
                self.logger.info("Price range filter inputs not found, using client-side filtering")
                
        except Exception as e:
            self.logger.warning(f"Failed to apply price range filter: {str(e)}")
    
    def extract_product_info(self) -> List[Dict]:
        """Extract product information from search results."""
        products = []
        try:
            # Wait for product listings to load
            if not self.wait:
                raise ValueError("WebDriverWait not initialized")
            product_containers = self.wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[@data-id]")))
            
            for container in product_containers[:10]:  # Limit to first 10 products
                try:
                    # Extract product title
                    title_element = container.find_element(By.XPATH, ".//div[@class='_4rR01T']")
                    title = title_element.text
                    
                    # Extract price
                    price_element = container.find_element(By.XPATH, ".//div[@class='_30jeq3 _1_WHN1']")
                    price_text = price_element.text
                    price = self.extract_price_from_text(price_text)
                    
                    # Extract product link
                    link_element = container.find_element(By.XPATH, ".//a[@class='_1fQZEK']")
                    product_url = link_element.get_attribute('href')
                    
                    # Check if price meets criteria
                    min_price = self.config["search_settings"]["min_price"]
                    max_price = self.config["search_settings"]["max_price"]
                    
                    if min_price <= price <= max_price:
                        products.append({
                            'title': title,
                            'price': price,
                            'url': product_url,
                            'container': container
                        })
                        self.logger.info(f"Found product: {title} - ₹{price}")
                
                except (NoSuchElementException, ValueError) as e:
                    # Skip products where we can't extract info
                    continue
                    
        except TimeoutException:
            self.logger.error("No product containers found")
        
        return products
    
    def close_login_popup(self):
        """Close login popup if it appears."""
        try:
            if self.wait:
                # Multiple possible close button selectors
                close_selectors = [
                    "//button[@class='_2KpZ6l _2doB4z']",
                    "//button[contains(@class, '_2doB4z')]",
                    "//span[text()='✕']/parent::button",
                    "//button[contains(text(), '✕')]"
                ]
                
                for selector in close_selectors:
                    try:
                        close_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        close_button.click()
                        self.logger.info("Closed login popup")
                        return
                    except TimeoutException:
                        continue
                        
                self.logger.info("No login popup found")
        except Exception as e:
            self.logger.warning(f"Error handling login popup: {str(e)}")
    
    def login(self):
        """Login to Flipkart using credentials from config."""
        try:
            if not self.driver or not self.wait:
                raise ValueError("WebDriver not initialized")
                
            self.logger.info("Attempting to login...")
            
            # Click login button
            login_selectors = [
                "//a[text()='Login']",
                "//a[contains(@class, '_1_3w1N') and contains(text(), 'Login')]",
                "//button[contains(text(), 'Login')]"
            ]
            
            login_button = None
            for selector in login_selectors:
                try:
                    login_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    break
                except TimeoutException:
                    continue
                    
            if not login_button:
                self.logger.warning("Could not find login button")
                return
                
            login_button.click()
            
            # Enter email
            email_input = self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@class='_2IX_2- VJZDxU' or contains(@class, 'email') or @type='text']")))
            email_input.clear()
            email_input.send_keys(self.config["user_credentials"]["email"])
            
            # Enter password
            password_input = self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='password']")))
            password_input.clear()
            password_input.send_keys(self.config["user_credentials"]["password"])
            
            # Click login submit
            submit_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' or contains(@class, '_2KpZ6l _2HKlqd _3AWRsL')]")))
            submit_button.click()
            
            # Wait for login to complete
            self.wait.until(EC.url_changes(self.driver.current_url))
            self.logger.info("Login completed")
            
        except Exception as e:
            self.logger.error(f"Login failed: {str(e)}")
            # Continue without login
            self.close_login_popup()
    
    def extract_price_from_text(self, price_text: str) -> float:
        """Extract numeric price from price text."""
        # Remove currency symbol and commas, extract number
        price_match = re.search(r'[\d,]+', price_text.replace('₹', '').replace(',', ''))
        if price_match:
            return float(price_match.group())
        raise ValueError(f"Could not extract price from: {price_text}")
    
    def add_to_cart(self, product: Dict) -> bool:
        """Add a product to cart with verification."""
        max_retries = self.config["automation_settings"]["max_retries"]
        
        for attempt in range(max_retries):
            try:
                if not self.driver or not self.wait:
                    raise ValueError("WebDriver not initialized")
                    
                self.logger.info(f"Attempting to add to cart (attempt {attempt + 1}/{max_retries}): {product['title']}")
                
                # Navigate to product page
                self.driver.get(product['url'])
                
                # Wait for page to load
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                
                # Find and click "Add to Cart" button - multiple selectors
                add_to_cart_selectors = [
                    "//button[contains(text(), 'ADD TO CART')]",
                    "//button[contains(@class, '_2KpZ6l') and contains(@class, '_2U9uOA')]",
                    "//button[contains(text(), 'Add to Cart')]",
                    "//li[@class='col col-6-12']//button[contains(@class, '_2KpZ6l')]"
                ]
                
                add_to_cart_button = None
                for selector in add_to_cart_selectors:
                    try:
                        add_to_cart_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        break
                    except TimeoutException:
                        continue
                        
                if not add_to_cart_button:
                    self.logger.error("Could not find Add to Cart button")
                    continue
                    
                add_to_cart_button.click()
                
                # Verify cart addition with multiple success indicators
                if self.verify_cart_addition():
                    self.logger.info(f"Successfully added to cart: {product['title']}")
                    return True
                else:
                    self.logger.warning(f"Cart addition not verified for: {product['title']}")
                    
            except Exception as e:
                self.logger.error(f"Failed to add product to cart (attempt {attempt + 1}): {str(e)}")
                
            # Wait before retry
            if attempt < max_retries - 1:
                time.sleep(2)
                
        return False
    
    def verify_cart_addition(self) -> bool:
        """Verify that item was successfully added to cart."""
        try:
            if not self.driver or not self.wait:
                return False
                
            # Check for success indicators
            success_indicators = [
                # Cart page redirect
                "/viewcart" in self.driver.current_url.lower(),
                "/cart" in self.driver.current_url.lower(),
            ]
            
            # Check URL first
            if any(success_indicators):
                return True
                
            # Check for success toast/notification
            try:
                success_elements = [
                    "//div[contains(text(), 'added to cart')]",
                    "//div[contains(text(), 'Added to Cart')]",
                    "//span[contains(text(), 'Item added to cart')]"
                ]
                
                for selector in success_elements:
                    try:
                        self.wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                        return True
                    except TimeoutException:
                        continue
                        
            except Exception:
                pass
                
            # Check cart count increment (if visible)
            try:
                cart_count = self.wait.until(EC.presence_of_element_located((By.XPATH, "//span[@class='_1LgLqK' or contains(@class, 'cart-count')]")))
                count = int(cart_count.text) if cart_count.text.isdigit() else 0
                if count > 0:
                    return True
            except (TimeoutException, ValueError):
                pass
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error verifying cart addition: {str(e)}")
            return False
    
    def run_automation(self) -> bool:
        """Main automation workflow. Returns True if successful, False otherwise."""
        added_count = 0
        try:
            # Setup driver
            self.setup_driver()
            
            # Navigate to Flipkart
            self.navigate_to_flipkart()
            
            # Search for products
            search_query = self.config["search_settings"]["search_query"]
            products = self.search_iphones(search_query)
            
            if not products:
                self.logger.warning("No products found matching criteria")
                return False
            
            self.logger.info(f"Found {len(products)} products matching criteria")
            
            # Add products to cart based on price criteria
            max_items_to_add = min(3, len(products))  # Limit to prevent excessive additions
            
            for i, product in enumerate(products[:max_items_to_add]):
                self.logger.info(f"Processing product {i+1}/{max_items_to_add}")
                
                if self.add_to_cart(product):
                    added_count += 1
                    self.logger.info(f"Successfully added {added_count} product(s) to cart")
                else:
                    self.logger.warning(f"Failed to add product: {product['title']}")
                
                # Add delay between additions to avoid being flagged
                if i < max_items_to_add - 1:  # Don't wait after the last item
                    time.sleep(5)
            
            self.logger.info(f"Automation completed. Added {added_count} out of {max_items_to_add} products to cart.")
            
            # Return success if at least one product was added
            return added_count > 0
            
        except Exception as e:
            self.logger.error(f"Automation failed: {str(e)}")
            return False
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                    self.logger.info("WebDriver closed")
                except Exception as e:
                    self.logger.warning(f"Error closing WebDriver: {str(e)}")

if __name__ == "__main__":
    automation = FlipkartAutomation()
    automation.run_automation()