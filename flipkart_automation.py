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
import os
import tempfile
from session_persistence import FlipkartSessionManager

class FlipkartAutomation:
    def __init__(self, config_file: str = "config.json", use_session: Optional[str] = None):
        """Initialize the Flipkart automation with configuration."""
        self.config = self.load_config(config_file)
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.session_manager = FlipkartSessionManager()
        self.use_session = use_session
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
    
    def _build_chrome_options(self, profile_path: Optional[str] = None) -> Options:
        """Build Chrome options with consistent settings."""
        chrome_options = Options()
        
        # Create temporary profile directory for this session
        temp_profile = tempfile.mkdtemp(prefix="chrome_profile_")
        
        # If we have a saved session profile, copy essential data to avoid conflicts
        if profile_path and os.path.exists(profile_path):
            try:
                self._copy_session_data(profile_path, temp_profile)
                self.logger.info(f"Using session profile data in temporary directory: {temp_profile}")
            except Exception as e:
                self.logger.warning(f"Failed to copy session data: {e}, using fresh profile")
        else:
            self.logger.info(f"Using fresh temporary profile: {temp_profile}")
        
        chrome_options.add_argument(f"--user-data-dir={temp_profile}")
        
        # Essential Chrome options for automation in Replit environment
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage") 
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-field-trial-config")
        chrome_options.add_argument("--disable-ipc-flooding-protection")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Use modern headless mode for better compatibility
        if self.config["automation_settings"]["headless_mode"]:
            chrome_options.add_argument("--headless=new")
            
        return chrome_options
    
    def _copy_session_data(self, source_profile: str, dest_profile: str):
        """Copy essential session data while avoiding Chrome lock files."""
        import shutil
        
        # Create Default directory structure in destination
        dest_default = os.path.join(dest_profile, "Default")
        source_default = os.path.join(source_profile, "Default")
        
        os.makedirs(dest_default, exist_ok=True)
        
        # Files to copy for session persistence (cookies, login data, etc.)
        essential_files = [
            "Cookies",
            "Cookies-journal", 
            "Login Data",
            "Login Data-journal",
            "Web Data",
            "Web Data-journal",
            "Local Storage",
            "Session Storage",
            "Preferences"
        ]
        
        # Copy essential session files
        for file_name in essential_files:
            source_file = os.path.join(source_default, file_name)
            dest_file = os.path.join(dest_default, file_name)
            
            try:
                if os.path.exists(source_file):
                    if os.path.isfile(source_file):
                        shutil.copy2(source_file, dest_file)
                    elif os.path.isdir(source_file):
                        shutil.copytree(source_file, dest_file, dirs_exist_ok=True)
                    self.logger.info(f"Copied session data: {file_name}")
            except Exception as e:
                self.logger.warning(f"Could not copy {file_name}: {e}")
        
        # Copy Local State file from root profile directory  
        local_state_src = os.path.join(source_profile, "Local State")
        local_state_dest = os.path.join(dest_profile, "Local State")
        try:
            if os.path.exists(local_state_src):
                shutil.copy2(local_state_src, local_state_dest)
                self.logger.info("Copied Local State")
        except Exception as e:
            self.logger.warning(f"Could not copy Local State: {e}")
    
    def setup_driver(self) -> webdriver.Chrome:
        """Setup Chrome WebDriver with appropriate options and session persistence."""
        profile_path = None
        
        # Get session profile if using session
        if self.use_session:
            profile_path = self.session_manager.get_session_profile(self.use_session)
            if profile_path:
                self.logger.info(f"Using saved session profile: {profile_path}")
            else:
                self.logger.warning(f"No valid session found for {self.use_session}, running without session")
        
        # Build consistent Chrome options
        chrome_options = self._build_chrome_options(profile_path)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(self.config["automation_settings"]["page_load_timeout"])
            self.wait = WebDriverWait(self.driver, self.config["automation_settings"]["wait_time"])
            
            if self.use_session and profile_path:
                self.logger.info("Chrome WebDriver initialized with session persistence")
            else:
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
                
            # Check if we have a direct search URL
            direct_url = self.config["search_settings"].get("direct_search_url")
            
            if direct_url:
                self.logger.info(f"Using direct search URL for: {search_query}")
                self.driver.get(direct_url)
                
                # Wait for results to load
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(3)  # Additional wait for dynamic content
                
            else:
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
                    if not self.wait:
                        raise ValueError("WebDriverWait not initialized")
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
                    if not self.wait:
                        raise ValueError("WebDriverWait not initialized")
                    sort_dropdown = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    sort_dropdown.click()
                    
                    # Select sort option
                    if not self.wait:
                        raise ValueError("WebDriverWait not initialized")
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
                if not self.driver:
                    raise ValueError("WebDriver not initialized")
                min_price_input = self.driver.find_element(By.XPATH, price_input_selectors[0])
                max_price_input = self.driver.find_element(By.XPATH, price_input_selectors[1])
                
                if min_price_input and max_price_input:
                    min_price_input.clear()
                    min_price_input.send_keys(str(min_price))
                    
                    max_price_input.clear()
                    max_price_input.send_keys(str(max_price))
                    
                    # Apply filter
                    if not self.driver:
                        raise ValueError("WebDriver not initialized")
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
            
            # Try multiple selectors for product containers
            container_selectors = [
                "//div[@data-id]",
                "//div[contains(@class, '_1AtVbE')]",  # Common product container
                "//div[contains(@class, '_13oc-S')]",  # Alternative container
                "//div[contains(@class, 'col-7-12')]",  # Grid layout
                "//div[contains(@class, '_1xHGtK')]",   # Product row
                "//div[contains(@class, 'col-12-12')]//div[contains(@class, '_1AtVbE')]"  # Nested containers
            ]
            
            product_containers = None
            for selector in container_selectors:
                try:
                    product_containers = self.wait.until(EC.presence_of_all_elements_located((By.XPATH, selector)))
                    if product_containers:
                        self.logger.info(f"Found {len(product_containers)} product containers using selector: {selector}")
                        break
                except TimeoutException:
                    continue
            
            if not product_containers:
                self.logger.error("No product containers found with any selector")
                return products
            
            for i, container in enumerate(product_containers[:10]):  # Limit to first 10 products
                try:
                    self.logger.info(f"Processing product container {i+1}")
                    
                    # Extract product title - try multiple selectors
                    title = None
                    title_selectors = [
                        ".//div[@class='_4rR01T']",  # Old selector
                        ".//a[contains(@class, 'IRpwTa')]",  # Link title
                        ".//div[contains(@class, '_4rR01T')]",  # Partial class match
                        ".//a[contains(@class, '_1fQZEK')]",  # Product link
                        ".//div[contains(@class, 'KzDlHZ')]",  # New title class
                        ".//span[contains(@class, 'B_NuCI')]",  # Span title
                        ".//h2//a",  # H2 link
                        ".//div[contains(text(), 'iPhone') or contains(text(), 'Apple')]",  # Text content
                        ".//a[@title]"  # Any link with title attribute
                    ]
                    
                    for title_selector in title_selectors:
                        try:
                            title_element = container.find_element(By.XPATH, title_selector)
                            title = title_element.text or title_element.get_attribute('title')
                            if title and title.strip():
                                break
                        except NoSuchElementException:
                            continue
                    
                    if not title:
                        self.logger.warning(f"Could not extract title for product {i+1}")
                        continue
                    
                    # Extract sale prices using new detection method
                    current_price, original_price = self.detect_sale_prices(container)
                    
                    if not current_price:
                        self.logger.warning(f"Could not extract price for product {i+1}: {title}")
                        continue
                    
                    # Check sale criteria
                    meets_criteria, discount_percentage, sale_message = self.meets_sale_criteria(current_price, original_price)
                    
                    if not meets_criteria:
                        self.logger.info(f"Product doesn't meet sale criteria: {title} - {sale_message}")
                        continue
                    
                    # Extract product link - try multiple selectors
                    product_url = None
                    link_selectors = [
                        ".//a[@class='_1fQZEK']",  # Old selector
                        ".//a[contains(@class, '_1fQZEK')]",  # Partial class match
                        ".//a[contains(@class, 'IRpwTa')]",  # Alternative link class
                        ".//a[@href]",  # Any link
                        ".//a[contains(@href, '/p/')]"  # Product page link
                    ]
                    
                    for link_selector in link_selectors:
                        try:
                            link_element = container.find_element(By.XPATH, link_selector)
                            product_url = link_element.get_attribute('href')
                            if product_url and ('flipkart.com' in product_url or product_url.startswith('/')):
                                if product_url.startswith('/'):
                                    product_url = 'https://www.flipkart.com' + product_url
                                break
                        except NoSuchElementException:
                            continue
                    
                    if not product_url:
                        self.logger.warning(f"Could not extract URL for product {i+1}: {title}")
                        continue
                    
                    # Check if price meets criteria
                    min_price = self.config["search_settings"]["min_price"]
                    max_price = self.config["search_settings"]["max_price"]
                    
                    if min_price <= current_price <= max_price:
                        product_info = {
                            'title': title,
                            'price': current_price,
                            'original_price': original_price,
                            'discount_percentage': discount_percentage,
                            'url': product_url,
                            'container': container
                        }
                        products.append(product_info)
                        
                        if original_price and discount_percentage > 0:
                            self.logger.info(f"Found qualifying sale product: {title} - ₹{current_price} (was ₹{original_price}, {discount_percentage:.1f}% off)")
                        else:
                            self.logger.info(f"Found qualifying product: {title} - ₹{current_price}")
                    else:
                        self.logger.info(f"Product price ₹{current_price} outside range ₹{min_price}-₹{max_price}: {title}")
                
                except Exception as e:
                    self.logger.warning(f"Error processing product {i+1}: {str(e)}")
                    continue
                    
        except TimeoutException:
            self.logger.error("No product containers found")
        except Exception as e:
            self.logger.error(f"Error in extract_product_info: {str(e)}")
        
        self.logger.info(f"Total products found matching criteria: {len(products)}")
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
    
    def detect_sale_prices(self, container):
        """Detect original and sale prices for a product."""
        current_price = None
        original_price = None
        
        # Look for original/strikethrough price first (indicates a sale)
        original_price_selectors = [
            ".//div[contains(@style, 'text-decoration: line-through')]",
            ".//span[contains(@style, 'text-decoration: line-through')]",
            ".//div[contains(@class, 'strike')]",
            ".//span[contains(@class, 'strike')]",
            ".//div[contains(@class, '_3I9_wc') and contains(@class, '_2p6lqe')]",  # Flipkart strikethrough class
            ".//span[contains(@class, '_3I9_wc')]",
            ".//div[contains(@style, 'line-through')]",
            ".//span[contains(@style, 'line-through')]"
        ]
        
        # Extract original price (if on sale)
        for selector in original_price_selectors:
            try:
                price_element = container.find_element(By.XPATH, selector)
                price_text = price_element.text
                if price_text and '₹' in price_text:
                    original_price = self.extract_price_from_text(price_text)
                    break
            except (NoSuchElementException, ValueError):
                continue
        
        # Use comprehensive price selectors (same as original method) for current price
        price_selectors = [
            ".//div[@class='_30jeq3 _1_WHN1']",  # Old selector
            ".//div[contains(@class, '_30jeq3')]",  # Partial class match
            ".//div[contains(@class, '_1_WHN1')]",  # Alternative price class
            ".//span[contains(@class, '_30jeq3')]",  # Span price
            ".//div[contains(text(), '₹')]",  # Text containing rupee
            ".//span[contains(text(), '₹')]",  # Span containing rupee
            ".//div[contains(@class, 'price')]",  # Generic price class
            ".//div[text()[contains(., '₹')]]"  # Direct text with rupee
        ]
        
        # Extract current price using comprehensive selectors
        for selector in price_selectors:
            try:
                price_element = container.find_element(By.XPATH, selector)
                price_text = price_element.text
                if price_text and '₹' in price_text:
                    # Skip if this is the strikethrough price we already found
                    if original_price:
                        potential_price = self.extract_price_from_text(price_text)
                        if potential_price != original_price:
                            current_price = potential_price
                            break
                    else:
                        current_price = self.extract_price_from_text(price_text)
                        break
            except (NoSuchElementException, ValueError):
                continue
        
        return current_price, original_price
    
    def calculate_discount_percentage(self, original_price: float, current_price: float) -> float:
        """Calculate discount percentage."""
        if original_price and current_price and original_price > current_price:
            return ((original_price - current_price) / original_price) * 100
        return 0.0
    
    def meets_sale_criteria(self, current_price: float, original_price: Optional[float] = None) -> tuple:
        """Check if product meets sale criteria."""
        sale_settings = self.config.get("sale_settings", {})
        
        if not sale_settings.get("enable_sale_detection", False):
            return True, 0.0, "Sale detection disabled"
        
        if not original_price:
            # No original price found, consider as regular price
            if sale_settings.get("prefer_sale_items", False):
                return False, 0.0, "No sale detected, prefer_sale_items enabled"
            return True, 0.0, "No sale detected, but accepted"
        
        discount_percentage = self.calculate_discount_percentage(original_price, current_price)
        min_discount = sale_settings.get("min_discount_percentage", 0)
        max_discount = sale_settings.get("max_discount_percentage", 100)
        
        if min_discount <= discount_percentage <= max_discount:
            return True, discount_percentage, f"Sale discount {discount_percentage:.1f}% within range"
        else:
            return False, discount_percentage, f"Sale discount {discount_percentage:.1f}% outside range {min_discount}-{max_discount}%"
    
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
                
                # Find and click "Add to Cart" button - working selectors
                add_to_cart_selectors = [
                    # Primary working selector (case-insensitive cart detection, excluding buy)
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'cart') and not(contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'buy'))]",
                    # Backup specific text matches
                    "//button[contains(text(), 'ADD TO CART')]",
                    "//button[contains(text(), 'Add to Cart')]",
                    "//button[contains(text(), 'Go to Cart')]",  # Already in cart scenario
                    "//button[@data-testid='add-to-cart']",
                    "//input[@value='ADD TO CART']"
                ]
                
                add_to_cart_button = None
                for i, selector in enumerate(add_to_cart_selectors):
                    try:
                        add_to_cart_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        self.logger.info(f"Found Add to Cart button: {add_to_cart_button.text}")
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
                
            # Navigate to cart page to verify items
            try:
                self.driver.get("http://flipkart.com/viewcart?marketplace=FLIPKART")
                time.sleep(2)
                
                # Check if cart has items
                cart_item_selectors = [
                    "//div[contains(@class, '_1AtVbE')]",  # Cart item container
                    "//div[contains(@class, '_13oc-S')]",  # Alternative cart item
                    "//div[contains(@class, 'cart-item')]",  # Generic cart item
                    "//div[contains(text(), 'iPhone')]",   # iPhone in cart
                    "//a[contains(@href, '/p/')]"         # Product links in cart
                ]
                
                for selector in cart_item_selectors:
                    try:
                        cart_items = self.driver.find_elements(By.XPATH, selector)
                        if cart_items:
                            self.logger.info(f"Found {len(cart_items)} items in cart")
                            return True
                    except NoSuchElementException:
                        continue
                        
            except Exception as e:
                self.logger.warning(f"Could not verify cart via cart page: {str(e)}")
                
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
            max_items_to_add = min(1, len(products))  # Add only 1 item as requested
            
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