"""
Session persistence manager for Flipkart automation.
Handles user login, OTP verification, and browser profile management.
"""

import os
import json
import shutil
from typing import Optional, Dict, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from models import UserSession, LoginAttempt, get_db_session
from datetime import datetime
import logging

class SessionManager:
    """Manages user sessions, login, and browser profile persistence."""
    
    def __init__(self, base_profile_dir: str = "profiles"):
        self.base_profile_dir = base_profile_dir
        self.logger = logging.getLogger(__name__)
        self.ensure_profiles_directory()
    
    def ensure_profiles_directory(self):
        """Create profiles directory if it doesn't exist."""
        if not os.path.exists(self.base_profile_dir):
            os.makedirs(self.base_profile_dir)
    
    def get_user_input(self, prompt: str) -> str:
        """Get user input with prompt. In VNC this will show in terminal."""
        return input(f"\n{prompt}: ").strip()
    
    def interactive_login(self, driver: webdriver.Chrome) -> Optional[str]:
        """
        Interactive login flow that asks user for email/mobile and handles OTP.
        Returns user_identifier if successful, None if failed.
        """
        print("\n" + "="*60)
        print("🔐 FLIPKART LOGIN SETUP")
        print("="*60)
        print("This will set up persistent login for future automation runs.")
        print("You'll need to complete OTP verification through the browser.")
        print()
        
        # Get user identifier
        user_identifier = self.get_user_input(
            "Enter your email address or mobile number for Flipkart"
        )
        
        if not user_identifier:
            print("❌ No identifier provided. Login cancelled.")
            return None
        
        # Record login attempt
        db_session = get_db_session()
        attempt_type = 'email' if '@' in user_identifier else 'mobile'
        login_attempt = LoginAttempt(
            user_identifier=user_identifier,
            attempt_type=attempt_type,
            otp_requested=False,
            otp_verified=False
        )
        db_session.add(login_attempt)
        db_session.commit()
        
        try:
            print(f"\n🌐 Opening Flipkart login page...")
            driver.get("https://www.flipkart.com/account/login")
            
            # Wait for login page to load
            wait = WebDriverWait(driver, 15)
            
            # Find and fill the login input field
            print("🔍 Looking for login input field...")
            login_input = None
            
            # Try different selectors for the login input
            login_selectors = [
                "//input[@class='_2IX_2-']",
                "//input[contains(@class, 'email')]",
                "//input[@type='text']",
                "//input[@placeholder and (contains(@placeholder, 'Email') or contains(@placeholder, 'Mobile'))]"
            ]
            
            for selector in login_selectors:
                try:
                    login_input = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                    break
                except TimeoutException:
                    continue
            
            if not login_input:
                print("❌ Could not find login input field")
                return None
            
            # Fill the login field
            login_input.clear()
            login_input.send_keys(user_identifier)
            print(f"✅ Entered identifier: {user_identifier}")
            
            # Look for and click "Request OTP" or similar button
            print("🔍 Looking for OTP request button...")
            otp_selectors = [
                "//button[contains(text(), 'Request OTP')]",
                "//button[contains(text(), 'Send OTP')]",
                "//button[@type='submit']",
                "//span[contains(text(), 'Request OTP')]/parent::button"
            ]
            
            otp_button = None
            for selector in otp_selectors:
                try:
                    otp_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    break
                except TimeoutException:
                    continue
            
            if otp_button:
                otp_button.click()
                login_attempt.otp_requested = True
                db_session.commit()
                print("✅ OTP request sent")
            else:
                print("⚠️ Could not find OTP button, but continuing...")
            
            # Wait for OTP input field to appear
            print("\n📱 Waiting for OTP input field...")
            print("💡 Complete the OTP verification in the browser window you can see through VNC")
            print("💡 The automation will wait for you to complete the login process")
            
            # Wait for login completion by detecting URL change or specific elements
            print("\n⏳ Waiting for login completion...")
            print("   - Enter your OTP in the browser")
            print("   - Click submit/verify")
            print("   - The automation will detect when you're logged in")
            
            # Wait for successful login (URL change or account elements)
            login_success = False
            timeout = 300  # 5 minutes timeout
            
            for _ in range(timeout):
                try:
                    # Check if we're redirected away from login page
                    current_url = driver.current_url
                    if "/account/login" not in current_url:
                        login_success = True
                        break
                    
                    # Check for account/user elements that indicate successful login
                    user_elements = [
                        "//div[contains(@class, 'account') or contains(@class, 'user')]",
                        "//span[contains(text(), 'Account')]",
                        "//a[contains(@aria-label, 'Account')]"
                    ]
                    
                    for elem_selector in user_elements:
                        try:
                            if driver.find_element(By.XPATH, elem_selector):
                                login_success = True
                                break
                        except:
                            continue
                    
                    if login_success:
                        break
                    
                    driver.implicitly_wait(1)
                    
                except Exception as e:
                    self.logger.debug(f"Login check error: {e}")
                    continue
            
            if login_success:
                login_attempt.otp_verified = True
                login_attempt.success = True
                db_session.commit()
                print("✅ Login completed successfully!")
                return user_identifier
            else:
                print("❌ Login timeout. Please try again.")
                return None
                
        except Exception as e:
            self.logger.error(f"Interactive login failed: {str(e)}")
            print(f"❌ Login error: {str(e)}")
            return None
        finally:
            db_session.close()
    
    def save_session(self, user_identifier: str, driver: webdriver.Chrome) -> bool:
        """Save current session and browser profile."""
        try:
            db_session = get_db_session()
            
            # Create unique profile directory
            profile_name = f"profile_{user_identifier.replace('@', '_').replace('+', '_')}"
            profile_path = os.path.join(self.base_profile_dir, profile_name)
            
            # Get current Chrome user data directory
            current_profile = None
            
            # Try to find user data directory from Chrome capabilities
            try:
                caps = driver.capabilities
                if 'chrome' in caps and 'userDataDir' in caps['chrome']:
                    current_profile = caps['chrome']['userDataDir']
            except:
                pass
            
            if current_profile and os.path.exists(current_profile):
                # Copy the Chrome profile
                if os.path.exists(profile_path):
                    shutil.rmtree(profile_path)
                shutil.copytree(current_profile, profile_path)
                print(f"✅ Browser profile saved to: {profile_path}")
            else:
                print("⚠️ Could not locate current Chrome profile, saving cookies only")
            
            # Get cookies as backup
            cookies = driver.get_cookies()
            cookies_json = json.dumps(cookies)
            
            # Save or update session in database
            existing_session = db_session.query(UserSession).filter_by(
                user_identifier=user_identifier
            ).first()
            
            if existing_session:
                existing_session.profile_path = profile_path
                existing_session.cookies_data = cookies_json
                existing_session.session_valid = True
                existing_session.last_used = datetime.utcnow()
                print(f"✅ Updated existing session for {user_identifier}")
            else:
                new_session = UserSession(
                    user_identifier=user_identifier,
                    session_name=profile_name,
                    profile_path=profile_path,
                    cookies_data=cookies_json,
                    session_valid=True
                )
                db_session.add(new_session)
                print(f"✅ Created new session for {user_identifier}")
            
            db_session.commit()
            db_session.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save session: {str(e)}")
            print(f"❌ Failed to save session: {str(e)}")
            return False
    
    def load_session(self, user_identifier: str) -> Optional[str]:
        """Load existing session profile path."""
        try:
            db_session = get_db_session()
            session = db_session.query(UserSession).filter_by(
                user_identifier=user_identifier
            ).first()
            
            if session and session.is_valid():
                session.update_last_used()
                db_session.commit()
                db_session.close()
                
                if os.path.exists(session.profile_path):
                    print(f"✅ Loading existing session for {user_identifier}")
                    return session.profile_path
                else:
                    print(f"⚠️ Profile path not found: {session.profile_path}")
            
            db_session.close()
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to load session: {str(e)}")
            return None
    
    def list_sessions(self) -> list:
        """List all available sessions."""
        try:
            db_session = get_db_session()
            sessions = db_session.query(UserSession).filter_by(session_valid=True).all()
            db_session.close()
            return [(s.user_identifier, s.last_used, s.is_valid()) for s in sessions]
        except Exception as e:
            self.logger.error(f"Failed to list sessions: {str(e)}")
            return []
    
    def delete_session(self, user_identifier: str) -> bool:
        """Delete a session and its profile data."""
        try:
            db_session = get_db_session()
            session = db_session.query(UserSession).filter_by(
                user_identifier=user_identifier
            ).first()
            
            if session:
                # Remove profile directory
                if os.path.exists(session.profile_path):
                    shutil.rmtree(session.profile_path)
                
                # Remove from database
                db_session.delete(session)
                db_session.commit()
                print(f"✅ Deleted session for {user_identifier}")
                
            db_session.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete session: {str(e)}")
            return False