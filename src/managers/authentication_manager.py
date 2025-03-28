import time
import logging

class AuthenticationManager:
    """
    Manages authentication and session handling
    """
    def __init__(self, browser_manager, config, logger=None):
        self.browser_manager = browser_manager
        self.page = browser_manager.page
        
        # Extract config
        self.url = config["url"]
        self.login_endpoint = config["login"]
        self.username = config["username"]
        self.password = config["password"]
        self.authenticator = config["authenticator"]
        self.logged_in_selector = config["logged_in_selector"]
        
        self.logger = logger or logging.getLogger(__name__)

    def is_logged_in(self) -> bool:
        """Check if the user is already logged in"""
        try:
            # Try multiple selectors that indicate logged-in state
            selectors = [
                self.logged_in_selector,
                "div.feed-identity-module",
                "button[data-control-name='nav.settings']",
                "img.global-nav__me-photo"
            ]
            
            for selector in selectors:
                if self.browser_manager.is_element_visible(selector):
                    return True
            return False
        except Exception as e:
            self.logger.error("Error checking login status", e)
            return False

    def perform_login(self):
        """Perform the login process"""
        try:
            login_url = self.url + self.login_endpoint
            self.logger.info(f"Navigating to login page: {login_url}")
            
            self.browser_manager.navigate(login_url)
            
            self.browser_manager.safe_fill('#username', self.username, "username field")
            self.browser_manager.safe_fill('#password', self.password, "password field")
            self.browser_manager.wait_and_click('button[type="submit"]', description="login button")
            self.page.wait_for_load_state()

            if self.authenticator:
                security_pin = input("Enter pin from authenticator app: ")
                self.browser_manager.safe_fill("#input__phone_verification_pin", security_pin, "security pin field")
                self.browser_manager.wait_and_click('button[type="submit"]', description="verification button")
                self.page.wait_for_load_state()
                
            # Verify login was successful
            return self.is_logged_in()
                
        except Exception as e:
            self.logger.error("Error during login", e)
            raise

    def ensure_logged_in(self):
        """Ensure the user is logged in, performing login if necessary"""
        self.logger.info("Checking login status...")
        
        self.browser_manager.navigate(self.url)
        self.page.wait_for_load_state()
        time.sleep(2)  # Give time for page to load fully
        
        logged_in = self.is_logged_in()
        self.logger.info(f"Logged in status: {logged_in}")
        
        if not logged_in:
            self.logger.info("Performing login...")
            return self.perform_login()
        else:
            self.logger.info("Already logged in!")
            return True