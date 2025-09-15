"""
Simplified session persistence implementation for Flipkart automation.
Handles login and browser profile management without complex ORM type issues.
"""

import os
import json
import shutil
import tempfile
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
import logging

class FlipkartSessionManager:
    """Simplified session manager for Flipkart automation."""
    
    def __init__(self, base_profile_dir: str = "flipkart_profiles"):
        self.base_profile_dir = base_profile_dir
        self.sessions_file = "sessions.json"
        self.logger = logging.getLogger(__name__)
        self.ensure_profiles_directory()
    
    def ensure_profiles_directory(self):
        """Create profiles directory if it doesn't exist."""
        if not os.path.exists(self.base_profile_dir):
            os.makedirs(self.base_profile_dir)
    
    def load_sessions(self) -> Dict[str, Any]:
        """Load sessions from JSON file."""
        try:
            if os.path.exists(self.sessions_file):
                with open(self.sessions_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"Failed to load sessions: {e}")
            return {}
    
    def save_sessions(self, sessions: Dict[str, Any]):
        """Save sessions to JSON file."""
        try:
            with open(self.sessions_file, 'w') as f:
                json.dump(sessions, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save sessions: {e}")
    
    def get_user_input(self, prompt: str) -> str:
        """Get user input with prompt."""
        return input(f"\n🔐 {prompt}: ").strip()
    
    def setup_session_login(self) -> Optional[str]:
        """
        Interactive session setup with login.
        Returns user_identifier if successful.
        """
        print("\n" + "="*70)
        print("🔐 FLIPKART LOGIN SETUP FOR SESSION PERSISTENCE")
        print("="*70)
        print("This will create a persistent login session for future automation runs.")
        print("You'll complete the login process through the browser window.\n")
        
        # Get user identifier
        user_identifier = self.get_user_input(
            "Enter your email address or mobile number for Flipkart"
        )
        
        if not user_identifier:
            print("❌ No identifier provided. Login cancelled.")
            return None
        
        # Create profile path
        safe_identifier = user_identifier.replace('@', '_').replace('+', '_').replace(' ', '_')
        profile_name = f"profile_{safe_identifier}"
        profile_path = os.path.join(self.base_profile_dir, profile_name)
        
        # Create temporary profile for login
        temp_profile = tempfile.mkdtemp(prefix="flipkart_login_")
        
        try:
            # Setup Chrome with temporary profile
            chrome_options = Options()
            chrome_options.add_argument(f"--user-data-dir={temp_profile}")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            print(f"\n🌐 Opening Chrome browser for login...")
            driver = webdriver.Chrome(options=chrome_options)
            driver.get("https://www.flipkart.com/account/login")
            
            print("🔍 Navigate to login page and complete the following steps:")
            print("   1. Enter your email/mobile in the login field")
            print("   2. Click 'Request OTP' or 'Send OTP'")
            print("   3. Enter the OTP you receive")
            print("   4. Complete any additional verification")
            print("   5. Wait until you're successfully logged in")
            print("\n⏳ The automation will detect when you're logged in...")
            
            # Wait for login completion
            login_success = self._wait_for_login_completion(driver)
            
            if login_success:
                print("✅ Login detected! Saving session...")
                
                # Save the logged-in profile
                driver.quit()
                if os.path.exists(profile_path):
                    shutil.rmtree(profile_path)
                shutil.copytree(temp_profile, profile_path)
                
                # Save session info
                sessions = self.load_sessions()
                sessions[user_identifier] = {
                    'profile_path': profile_path,
                    'profile_name': profile_name,
                    'created_at': datetime.now().isoformat(),
                    'last_used': datetime.now().isoformat(),
                    'valid': True
                }
                self.save_sessions(sessions)
                
                print(f"✅ Session saved successfully for {user_identifier}")
                print(f"📂 Profile saved at: {profile_path}")
                return user_identifier
            else:
                print("❌ Login timeout or failed. Please try again.")
                driver.quit()
                return None
                
        except Exception as e:
            print(f"❌ Login setup failed: {str(e)}")
            return None
        finally:
            # Cleanup temporary profile
            if os.path.exists(temp_profile):
                shutil.rmtree(temp_profile, ignore_errors=True)
    
    def _wait_for_login_completion(self, driver: webdriver.Chrome, timeout: int = 300) -> bool:
        """Wait for login to complete by detecting URL change or user elements."""
        wait = WebDriverWait(driver, 1)
        start_time = datetime.now()
        
        print("⏳ Waiting for login completion...")
        
        while (datetime.now() - start_time).seconds < timeout:
            try:
                current_url = driver.current_url
                
                # Check if redirected away from login page
                if "/account/login" not in current_url and "flipkart.com" in current_url:
                    print("✅ Login successful - redirected from login page")
                    return True
                
                # Check for account/user elements
                user_elements = [
                    "//div[contains(@class, 'exehdJ')]",  # Account dropdown
                    "//span[text()='Account & Settings']",
                    "//a[contains(@aria-label, 'Account')]",
                    "//div[contains(@class, '_1us9w0')]"  # User menu
                ]
                
                for elem_selector in user_elements:
                    try:
                        element = driver.find_element(By.XPATH, elem_selector)
                        if element and element.is_displayed():
                            print("✅ Login successful - user elements detected")
                            return True
                    except:
                        continue
                
                # Check for specific success indicators
                success_indicators = [
                    "//div[contains(text(), 'Hi')]",  # Welcome message
                    "//span[contains(@class, 'account')]",
                    "//a[@href='/account/orders']"  # My orders link
                ]
                
                for indicator in success_indicators:
                    try:
                        element = driver.find_element(By.XPATH, indicator)
                        if element and element.is_displayed():
                            print("✅ Login successful - success indicators found")
                            return True
                    except:
                        continue
                
                # Show progress
                elapsed = (datetime.now() - start_time).seconds
                if elapsed % 15 == 0:  # Show progress every 15 seconds
                    print(f"⏳ Still waiting for login... ({elapsed}/{timeout}s)")
                
                # Wait a bit before next check
                driver.implicitly_wait(2)
                
            except Exception as e:
                self.logger.debug(f"Login check error: {e}")
                continue
        
        return False
    
    def get_session_profile(self, user_identifier: str) -> Optional[str]:
        """Get existing session profile path if valid."""
        sessions = self.load_sessions()
        session = sessions.get(user_identifier)
        
        if session and session.get('valid', False):
            profile_path = session['profile_path']
            if os.path.exists(profile_path):
                # Update last used
                session['last_used'] = datetime.now().isoformat()
                sessions[user_identifier] = session
                self.save_sessions(sessions)
                return profile_path
        
        return None
    
    def list_available_sessions(self) -> list:
        """List all available sessions."""
        sessions = self.load_sessions()
        return [
            {
                'user': user,
                'created': info.get('created_at', 'Unknown'),
                'last_used': info.get('last_used', 'Unknown'),
                'valid': info.get('valid', False)
            }
            for user, info in sessions.items()
        ]
    
    def delete_session(self, user_identifier: str) -> bool:
        """Delete a session and its profile."""
        try:
            sessions = self.load_sessions()
            session = sessions.get(user_identifier)
            
            if session:
                profile_path = session.get('profile_path')
                if profile_path and os.path.exists(profile_path):
                    shutil.rmtree(profile_path)
                
                del sessions[user_identifier]
                self.save_sessions(sessions)
                print(f"✅ Deleted session for {user_identifier}")
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"Failed to delete session: {e}")
            return False
    
    def create_driver_with_session(self, user_identifier: str) -> Optional[webdriver.Chrome]:
        """Create Chrome driver with existing session if available."""
        profile_path = self.get_session_profile(user_identifier)
        
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage") 
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        if profile_path:
            chrome_options.add_argument(f"--user-data-dir={profile_path}")
            print(f"🔐 Using saved session for {user_identifier}")
        else:
            print("🔓 No saved session found, will run without login")
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            return driver
        except Exception as e:
            self.logger.error(f"Failed to create driver: {e}")
            return None