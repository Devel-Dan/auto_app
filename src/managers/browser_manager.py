from playwright.sync_api import sync_playwright, Page
import time
import logging
import os

class BrowserManager:
    """
    Manages browser interactions, setup, and UI operations
    """
    def __init__(self, user_data_dir, headless=False, logger=None):
        self.user_data_dir = user_data_dir
        self.headless = headless
        self.logger = logger or logging.getLogger(__name__)
        
        self.playwright = None
        self.browser = None
        self.page = None

    def __enter__(self):
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=self.headless
            )
            
            self.page = self.browser.new_page()
            self.logger.info("Browser initialized")
            
            return self
            
        except Exception as e:
            self.logger.error("Error during initialization", e)
            self.cleanup()
            raise e

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.logger.error("Error during execution", exc_val)
        self.cleanup()

    def cleanup(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def navigate(self, url):
        """Navigate to a URL with proper error handling"""
        try:
            self.logger.info(f"Navigating to: {url}")
            self.page.goto(url)
            self.page.wait_for_load_state()
            return True
        except Exception as e:
            self.logger.error(f"Error navigating to {url}", e)
            return False

    def wait_and_click(self, selector, timeout=5000, description="element"):
        """Wait for an element and click it with proper error handling"""
        try:
            self.logger.info(f"Waiting for {description}...")
            self.page.wait_for_selector(selector, timeout=timeout)
            self.page.click(selector)
            self.logger.info(f"Clicked {description}")
            return True
        except Exception as e:
            self.logger.error(f"Error clicking {description}", e)
            return False
            
    def safe_fill(self, selector, value, description="field"):
        """Fill a field with proper error handling"""
        try:
            self.logger.info(f"Filling {description} with value: {value}")
            self.page.fill(selector, value)
            return True
        except Exception as e:
            self.logger.error(f"Error filling {description}", e)
            return False

    def is_element_visible(self, selector, timeout=2000):
        """Check if an element is visible with error handling"""
        try:
            return self.page.is_visible(selector, timeout=timeout)
        except Exception:
            return False

    def safe_set_value(self, element, value, element_type="input"):
        """Set a value on an input element safely using Python methods with fallbacks."""
        try:
            # First approach: Direct Playwright method
            try:
                if element_type == "select":
                    element.select_option(value=value)
                elif element_type == "input":
                    element.fill(str(value))
                elif element_type == "radio":
                    element.check()
                self.logger.info(f"Set value using direct method: {value}")
                return True
            except Exception as e:
                self.logger.error(f"Direct method failed: {e}")

            # Second approach: Try with evaluate as a fallback
            try:
                # For select elements
                if element_type == "select":
                    success = element.evaluate(f'(el) => {{ try {{ el.value = "{value}"; return true; }} catch(e) {{ return false; }} }}')
                    if success:
                        self.logger.info(f"Set select value using evaluate: {value}")
                        return True
                # For input elements
                elif element_type == "input":
                    success = element.evaluate(f'(el) => {{ try {{ el.value = "{value}"; return true; }} catch(e) {{ return false; }} }}')
                    if success:
                        self.logger.info(f"Set input value using evaluate: {value}")
                        return True
                # For radio elements
                elif element_type == "radio":
                    success = element.evaluate('(el) => { try { el.checked = true; return true; } catch(e) { return false; } }')
                    if success:
                        self.logger.info("Set radio checked using evaluate")
                        return True
            except Exception as e:
                self.logger.error(f"Evaluate method failed: {e}")

            # Third approach: Try to use type() for text inputs
            if element_type == "input":
                try:
                    element.click()
                    time.sleep(0.2)
                    element.press("Control+a")  # Select all existing text
                    time.sleep(0.2)
                    element.press("Backspace")  # Delete selected text
                    time.sleep(0.2)
                    element.type(str(value))  # Type new value
                    self.logger.info(f"Set value using type method: {value}")
                    return True
                except Exception as e:
                    self.logger.error(f"Type method failed: {e}")

            self.logger.info(f"All methods to set value failed")
            return False

        except Exception as e:
            self.logger.error(f"Error in safe_set_value: {e}")
            return False
    

    def safe_click(self, element, fallback_selector=None):
        """Click an element safely using multiple approaches."""
        try:
            # First approach: Direct Playwright click
            try:
                element.click()
                self.logger.info("Clicked element directly")
                return True
            except Exception as e:
                self.logger.error("Direct click failed", e)

            # Second approach: JavaScript click using ID
            element_id = element.get_attribute("id")
            if element_id:
                js_result = self.page.evaluate(f'''
                    const el = document.getElementById("{element_id}");
                    if (el) {{
                        el.click();
                        return true;
                    }}
                    return false;
                ''')
                if js_result:
                    self.logger.info("Clicked element with JavaScript")
                    return True

            # Third approach: Try fallback selector if provided
            if fallback_selector:
                try:
                    self.page.click(fallback_selector)
                    self.logger.info(f"Clicked using fallback selector: {fallback_selector}")
                    return True
                except Exception as e:
                    self.logger.error(f"Fallback selector click failed", e)

            return False

        except Exception as e:
            self.logger.error("Error in safe_click", e)
            return False   

    def clear_field(self, input_field):
        """Thoroughly clear a field using multiple approaches"""
        try:
            field_id = input_field.get_attribute("id")
            field_type = input_field.get_attribute("type") or "text"
            self.logger.info(f"Clearing {field_type} field with ID: {field_id}")
    
            # Try multiple clearing methods in sequence
    
            # Method 1: Basic fill with empty string
            try:
                input_field.fill("")
                time.sleep(0.3)
            except Exception as e:
                self.logger.error("Basic fill clearing failed", e)
    
            # Method 2: JavaScript clearing
            if field_id:
                try:
                    js_result = self.page.evaluate(f"""
                        (() => {{
                            const el = document.getElementById("{field_id}");
                            if (el) {{
                                el.value = "";
                                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                return true;
                            }}
                            return false;
                        }})()
                    """)
                    if js_result:
                        self.logger.info("JavaScript clearing succeeded")
                    time.sleep(0.3)
                except Exception as e:
                    self.logger.error("JavaScript clearing failed", e)
    
            # Method 3: Click and select all + delete
            try:
                input_field.click()
                time.sleep(0.2)
    
                # Select all text (Ctrl+A or Cmd+A depending on OS)
                input_field.press("Control+a")
                time.sleep(0.2)
    
                # Delete selected text
                input_field.press("Delete")
                time.sleep(0.2)
            except Exception as e:
                self.logger.error("Select-all clearing failed", e)
    
            # Method 4: Try rapid backspaces
            try:
                input_field.click()
                # Press end to go to end of text
                input_field.press("End")
                # Send multiple backspaces
                for _ in range(30):  # Plenty to clear most fields
                    input_field.press("Backspace")
            except Exception as e:
                self.logger.error("Backspace clearing failed", e)
    
            # Check if the field is now empty
            try:
                current_value = input_field.evaluate('(el) => el.value')
                if current_value:
                    self.logger.info(f"Field still contains: '{current_value}'")
                    return False
                else:
                    self.logger.info("Field successfully cleared")
                    return True
            except Exception as e:
                self.logger.error("Error checking field value", e)
    
            return True
    
        except Exception as e:
            self.logger.error("Error in clear_field", e)
            return False

    def escape_css_selector(self, selector):
        """
        Properly escapes CSS selectors that contain special characters.
        """
        if not selector or not isinstance(selector, str):
            return selector

        # For IDs that start with #, extract the ID part and escape it
        if selector.startswith('#'):
            id_value = selector[1:]  # Remove the # prefix

            # Use JavaScript's CSS.escape to properly escape the ID
            try:
                escaped_id = self.page.evaluate(f'CSS.escape("{id_value}")')
                return f'#{escaped_id}'
            except Exception as e:
                self.logger.error(f"Failed to escape selector: {e}")

                # Fallback method - handle common special characters
                special_chars = [':', '.', '(', ')', ',', "'", '"', '[', ']', '=', '+']
                for char in special_chars:
                    id_value = id_value.replace(char, f'\\{char}')
                return f'#{id_value}'

        return selector