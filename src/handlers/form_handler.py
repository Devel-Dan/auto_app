import time
import logging
from datetime import datetime
from src.config.config import SELECTORS, EDUCATION_DEFAULTS, TIMING

class FormHandler:
    """
    Handles interactions with form fields and validation
    """
    def __init__(self, browser_manager, response_manager, selectors, logger=None):
        self.browser_manager = browser_manager
        self.page = browser_manager.page
        self.response_manager = response_manager
        self.selectors = selectors
        self.logger = logger or logging.getLogger(__name__)

    def css_escape(self, string):
        """
        Escapes special characters in a string to be used as a CSS selector.
        Similar to the CSS.escape() function in JavaScript.
        """
        if not string:
            return string
        
        result = ""
        length = len(string)
        
        for i in range(length):
            char = string[i]
            
            # Escape the following characters: !"#$%&'()*+,./:;<=>?@[\]^`{|}~
            if char in '!"#$%&\'()*+,./:;<=>?@[\\]^`{|}~':
                result += '\\' + char
            # Handle control characters and non-ASCII characters
            elif ord(char) < 32 or ord(char) > 126:
                # Use hexadecimal escape
                result += '\\{:x} '.format(ord(char))
            # Handle first character if it's a digit, dash, or begins with two dashes
            elif i == 0 and (char.isdigit() or char == '-' or (char == '-' and i + 1 < length and string[i + 1] == '-')):
                result += '\\' + char
            else:
                result += char
        
        return result

    def check_field_has_error(self, input_field):
        """Check if a field has an error using corrected CSS selectors."""
        try:
            if input_field is None:
                return False, None

            # Handle cases where we incorrectly receive a string
            if isinstance(input_field, str):
                self.logger.info(f"Received string instead of element in check_field_has_error: {input_field}")
                return False, None

            # Method 1: Get field ID and look for corresponding error element
            field_id = None
            try:
                field_id = input_field.get_attribute("id")
            except Exception:
                # Fallback
                try:
                    field_id = input_field.evaluate('el => el.id || ""')
                except Exception:
                    pass

            if field_id:
                escaped_field_id = self.css_escape(field_id)
                error_id = f"{escaped_field_id}-error"
                error_element = self.page.query_selector(f"#{error_id}")

                if error_element:
                    error_visible = False
                    try:
                        error_visible = error_element.is_visible()
                    except Exception:
                        error_visible = True  # Default to visible if we can't check

                    if error_visible:
                        # Try to find the error message text
                        error_message = None
                        try:
                            # Try to find a specific error message element
                            message_element = error_element.query_selector('.artdeco-inline-feedback__message')
                            if message_element:
                                error_message = message_element.inner_text().strip()
                            else:
                                # If no specific message element, use the whole error container text
                                error_message = error_element.inner_text().strip()
                        except Exception:
                            error_message = "Unknown error"

                        self.logger.info(f"Found error: {error_message}")
                        return True, error_message

            # Method 2: Check parent elements for error classes - FIXED APPROACH
            try:
                # Check if element itself has error classes
                element_classes = input_field.get_attribute("class") or ""
                if "artdeco-text-input--error" in element_classes or "invalid-input" in element_classes:
                    error_message = "Field has error class"
                    self.logger.info(f"Found error via element class: {error_message}")
                    return True, error_message

                # Use JavaScript to check parent elements for error classes
                # This avoids the problematic CSS selector
                has_error = input_field.evaluate("""
                    (el) => {
                        // Check parent for error classes
                        let parent = el.parentElement;
                        if (parent) {
                            let parentClasses = parent.className || '';
                            if (parentClasses.includes('artdeco-text-input--error') || 
                                parentClasses.includes('fb-dash-form-element-error')) {
                                return true;
                            }

                            // Check for error elements within parent
                            let errorElements = parent.querySelectorAll('[role="alert"], .artdeco-inline-feedback--error');
                            return errorElements && errorElements.length > 0;
                        }
                        return false;
                    }
                """)

                if has_error:
                    # Get error message if available
                    error_message = input_field.evaluate("""
                        (el) => {
                            let parent = el.parentElement;
                            if (parent) {
                                let errorEl = parent.querySelector('[role="alert"], .artdeco-inline-feedback--error');
                                return errorEl ? errorEl.textContent.trim() : "Parent contains error";
                            }
                            return "Unknown error";
                        }
                    """)
                    self.logger.info(f"Found error in parent container: {error_message}")
                    return True, error_message

                # No error found
                return False, None

            except Exception as parent_error:
                self.logger.error(f"Error checking parent for errors", parent_error)
                return False, None

        except Exception as e:
            self.logger.error(f"Error checking for field errors", e)
            return False, None

    def check_existing_value(self, element):
        """Check if an input element already has a value."""
        try:
            current_value = element.evaluate('(element) => element.value')
            has_value = current_value and current_value.strip() and current_value != "Select an option"
            if has_value:
                self.logger.info(f"Field already has value: {current_value}")
            return has_value
        except Exception as e:
            self.logger.error("Error checking existing value", e)
            return False

    def get_label_text(self, element, fieldset=False):
        """Get the label text for an input element with enhanced detection for different HTML structures."""
        try:
            # Handle fieldset elements
            if fieldset:
                legend = element.query_selector("legend")
                if legend:
                    text = legend.inner_text().lower().strip()
                    text = self.response_manager.clean_question_text(text)
                    self.logger.info(f"Found fieldset label: {text}")
                    return text
                return None

            # Get the element ID for label matching
            element_id = element.get_attribute('id')

            # Method 1: Standard "for" attribute on label
            if element_id:
                escaped_element_id = self.css_escape(element_id)
                label = self.page.query_selector(f'label[for="{escaped_element_id}"]')
                if label:
                    text = label.inner_text().lower().strip()
                    text = self.response_manager.clean_question_text(text)
                    self.logger.info(f"Found label via 'for' attribute: {text}")
                    return text

            # Method 2: Artdeco label within parent container
            parent = element.query_selector('xpath=./ancestor::div[contains(@class, "artdeco-text-input--container")]')
            if parent:
                label = parent.query_selector('.artdeco-text-input--label')
                if label:
                    text = label.inner_text().lower().strip()
                    text = self.response_manager.clean_question_text(text)
                    self.logger.info(f"Found label via artdeco container: {text}")
                    return text

            # Method 3: Look for nearby section title (common in LinkedIn forms)
            # First go up to find a common container
            # This specifically targets LinkedIn's structure with "jobs-easy-apply-form-section__group-title"
            section_title = element.evaluate("""(el) => {
                // Go up several levels to find potential container
                let current = el;
                for (let i = 0; i < 7; i++) {
                    if (!current || current.tagName === 'BODY') break;

                    // Go up one level
                    current = current.parentElement;
                    if (!current) break;

                    // Look for section title elements
                    const titleSpan = current.querySelector('.jobs-easy-apply-form-section__group-title');
                    if (titleSpan) return titleSpan.textContent.trim();

                    // Also look for h3 titles nearby
                    const h3 = current.querySelector('h3.t-16');
                    if (h3) return h3.textContent.trim();

                    // Look for any label that might be related
                    const labels = current.querySelectorAll('label, .fb-dash-form-element__label');
                    for (const label of labels) {
                        // Check if this label is not associated with another input
                        const forAttr = label.getAttribute('for');
                        if (!forAttr || forAttr === el.id) {
                            return label.textContent.trim();
                        }
                    }
                }
                return null;
            }""")

            if section_title:
                text = section_title.lower().strip()
                text = self.response_manager.clean_question_text(text)
                self.logger.info(f"Found section title: {text}")
                return text

            # Method 4: Check for aria-label on the element itself
            aria_label = element.get_attribute('aria-label')
            if aria_label:
                text = aria_label.lower().strip()
                text = self.response_manager.clean_question_text(text)
                self.logger.info(f"Found aria-label: {text}")
                return text

            # Method 5: Check placeholder text as a last resort
            placeholder = element.get_attribute('placeholder')
            if placeholder:
                text = placeholder.lower().strip()
                text = self.response_manager.clean_question_text(text)
                self.logger.info(f"Found placeholder: {text}")
                return text

            # If all methods fail, try to extract field name from the ID itself
            if element_id:
                # Extract meaningful parts from IDs like "single-line-text-form-component-formElement-..."
                parts = element_id.split('-')
                meaningful_parts = [p for p in parts if len(p) > 3 and p not in ['form', 'component', 'element', 'text']]
                if meaningful_parts:
                    # Convert camelCase or snake_case to spaces
                    import re
                    text = ' '.join(meaningful_parts)
                    text = re.sub(r'([A-Z])', r' \1', text).lower()  # camelCase to spaces
                    text = text.replace('_', ' ')  # snake_case to spaces
                    text = self.response_manager.clean_question_text(text)
                    self.logger.info(f"Extracted field name from ID: {text}")
                    return text

            self.logger.info("Could not find any label text for this element")
            # If no label found at all, return a default value based on field type
            field_type = element.get_attribute("type") or "text"
            default_text = f"{field_type} field"
            return default_text

        except Exception as e:
            self.logger.error("Error getting label text", e)
            return "Unknown field"

    def determine_field_type(self, element):
        """Determine field type using Python methods with improved checkbox detection."""
        try:
            # Get the element's tag name with reliable method
            tag_name = None
            try:
                # Use evaluate instead of tag_name() 
                tag_name = element.evaluate('el => el.tagName.toLowerCase()')
            except Exception as e:
                self.logger.error(f"Error getting tag name via evaluate: {e}")
                tag_name = "input"  # Default fallback
                self.logger.warning("Could not determine tag name, assuming 'input'")

            if not tag_name:
                self.logger.warning("Could not determine tag name, assuming 'input'")
                tag_name = "input"

            # Handle fieldsets specially - look inside for checkbox or radio inputs
            if tag_name == "fieldset":
                try:
                    # Check if it contains checkboxes
                    has_checkboxes = element.evaluate('el => el.querySelector("input[type=\'checkbox\']") !== null')
                    if has_checkboxes:
                        self.logger.info("Identified fieldset containing checkboxes")
                        return "checkbox-group"

                    # Check if it contains radio buttons
                    has_radios = element.evaluate('el => el.querySelector("input[type=\'radio\']") !== null')
                    if has_radios:
                        self.logger.info("Identified fieldset containing radio buttons")
                        return "radio"
                except Exception as e:
                    self.logger.error(f"Error checking fieldset contents: {e}")

                # Default fieldset type if specific content not identified
                return "fieldset"

            # Handle select elements
            if tag_name == "select":
                return "select"

            # Handle textarea elements
            if tag_name == "textarea":
                return "textarea"

            # Handle input elements - most common case
            if tag_name == "input":
                # Get input type - the most important attribute for inputs
                input_type = None
                try:
                    input_type = element.evaluate('el => el.getAttribute("type") || "text"')
                except Exception as e:
                    self.logger.error(f"Error getting input type: {e}")
                    input_type = "text"  # Default

                # Check for checkbox type first (high priority)
                if input_type == "checkbox":
                    self.logger.info("Identified input as checkbox")
                    return "checkbox"

                # Check for radio type
                if input_type == "radio":
                    return "radio"

                # Check for typeahead inputs
                try:
                    is_typeahead = element.evaluate('el => el.closest(".search-basic-typeahead") !== null')

                    if is_typeahead:
                        self.logger.info("Identified input as typeahead")
                        return "typeahead"
                except Exception as e:
                    self.logger.error(f"Error checking for typeahead container: {e}")

                # Check for date inputs
                try:
                    is_date = element.evaluate('el => el.closest(".artdeco-datepicker") !== null')
                    if is_date or input_type == "date":
                        return "date"
                except Exception:
                    pass

                # Return the input type for other inputs
                return input_type

            # Default to the tag name if we couldn't determine a specific type
            return tag_name

        except Exception as e:
            self.logger.error(f"Error determining field type: {e}")
            return "unknown"

    def should_skip_checkbox(self, element):
        """
        Determine if a checkbox should be skipped based on its label or context.
        Returns True if the checkbox should be skipped.
        """
        try:
            # Get the checkbox's label text
            checkbox_id = element.get_attribute("id") or ""
            label_text = ""

            # Try to find associated label
            if checkbox_id:
                escaped_checkbox_id = self.css_escape(checkbox_id)
                label = self.page.query_selector(f'label[for="{escaped_checkbox_id}"]')
                if label:
                    label_text = label.inner_text().strip().lower()

            # If no label found by ID, try parent fieldset's legend
            if not label_text:
                fieldset = element.evaluate("""(el) => {
                    let node = el;
                    for (let i = 0; i < 5 && node; i++) {
                        if (node.tagName && node.tagName.toLowerCase() === 'fieldset') {
                            return node;
                        }
                        node = node.parentElement;
                    }
                    return null;
                }""")

                if fieldset:
                    legend = fieldset.query_selector("legend")
                    if legend:
                        label_text = legend.inner_text().strip().lower()

            # List of checkbox labels/text to skip
            skip_texts = [
                "mark this job as a top choice",
                "mark as top choice",
                "add to top choice",
                "flag as a top choice",
                "newsletter",
                "subscribe",
                "marketing",
                "promotional",
                "communications",
                "emails"
            ]

            # Check if any skip text is in the label
            for skip_text in skip_texts:
                if skip_text in label_text:
                    self.logger.info(f"Skipping optional checkbox: '{label_text}'")
                    return True

            # If label mentions "top choice" AND "optional", skip it
            if "top choice" in label_text and "optional" in label_text:
                self.logger.info(f"Skipping top choice optional checkbox: '{label_text}'")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error checking if checkbox should be skipped: {e}")
            return False

    def find_fields_with_errors(self, modal):
        """Find form fields with errors using proper CSS selector syntax and escaping."""
        all_fields_with_errors = []

        try:
            # Find error indicators
            error_selectors = [
                '.artdeco-inline-feedback--error', 
                '.fb-dash-form-element-error', 
                '.invalid-input', 
                "[role='alert']"
            ]

            for selector in error_selectors:
                error_elements = modal.query_selector_all(selector)

                for error_element in error_elements:
                    try:
                        # Check if error is visible
                        is_visible = False
                        try:
                            is_visible = error_element.is_visible()

                        except Exception:
                            is_visible = True  # Default to visible if we can't check

                        if not is_visible:
                            continue
                        
                        # Get error message
                        error_message = None
                        try:
                            error_message = error_element.inner_text().strip()
                        except Exception:
                            error_message = "Unknown error"

                        self.logger.info(f"Found error: {error_message}")

                        # Check if this is a checkbox error
                        if "checkbox" in error_message.lower() or "check box" in error_message.lower():
                            self.logger.info("This appears to be a checkbox error")

                            # Handle checkbox errors with JavaScript rather than CSS selectors
                            # We'll process these separately in the process_all_form_fields method
                            continue

                        # Method 1: Find field by error ID pattern using JavaScript instead of CSS selector
                        field = None
                        error_id = None
                        try:
                            error_id = error_element.get_attribute("id")
                        except Exception as e:
                            self.logger.error(str(e))
                            pass
                        
                        if error_id and "-error" in error_id:
                            field_id = error_id.replace("-error", "")
                            escaped_field_id = self.css_escape(field_id)

                            # Use JavaScript to safely get the element by ID to avoid CSS selector issues
                            field_el = self.page.evaluate(f"""
                                () => {{
                                    // Get the field element by ID directly with JavaScript
                                    const fieldEl = document.getElementById("{field_id}");

                                    // If found, mark it for easy selection
                                    if (fieldEl) {{
                                        fieldEl.setAttribute('data-field-with-error', 'true');
                                        return true;
                                    }}
                                    return false;
                                }}
                            """)

                            if field_el:
                                # Now get the marked element without complex CSS selectors
                                field = self.page.query_selector('[data-field-with-error="true"]')

                                # Remove the marker attribute
                                if field:
                                    self.page.evaluate("""
                                        () => {
                                            const el = document.querySelector('[data-field-with-error="true"]');
                                            if (el) el.removeAttribute('data-field-with-error');
                                        }
                                    """)

                        # If we found a field, add it to our list
                        if field:
                            self.logger.info(f"Found field with error: {error_message}")
                            all_fields_with_errors.append((field, error_message))
                        else:
                            # If we couldn't find by ID, try using JavaScript to find related input fields
                            self.logger.info("Could not find field by ID, trying alternative approaches")

                            if error_id:
                                # Use JavaScript to mark a suitable input based on location in DOM
                                found_input = self.page.evaluate(f"""
                                    () => {{
                                        const errorEl = document.getElementById("{error_id}");
                                        if (!errorEl) return false;

                                        // Function to find the closest input-like element from a starting element
                                        function findNearestInputFrom(startEl) {{
                                            // Look at parent container first
                                            let parent = startEl.parentElement;
                                            if (!parent) return null;

                                            // Try to find an input in this container
                                            let inputs = parent.querySelectorAll('input, select, textarea');
                                            if (inputs && inputs.length > 0) {{
                                                inputs[0].setAttribute('data-field-with-error', 'true');
                                                return inputs[0];
                                            }}

                                            // If no inputs found, try one level up 
                                            parent = parent.parentElement;
                                            if (parent) {{
                                                inputs = parent.querySelectorAll('input, select, textarea');
                                                if (inputs && inputs.length > 0) {{
                                                    inputs[0].setAttribute('data-field-with-error', 'true');
                                                    return inputs[0];
                                                }}
                                            }}

                                            return null;
                                        }}

                                        // Try to find from error element
                                        return !!findNearestInputFrom(errorEl);
                                    }}
                                """)

                                if found_input:
                                    # Get the marked field
                                    field = self.page.query_selector('[data-field-with-error="true"]')

                                    # Remove the marker
                                    if field:
                                        self.page.evaluate("""
                                            () => {
                                                const el = document.querySelector('[data-field-with-error="true"]');
                                                if (el) el.removeAttribute('data-field-with-error');
                                            }
                                        """)

                                        self.logger.info(f"Found field with error using DOM proximity")
                                        all_fields_with_errors.append((field, error_message))

                    except Exception as e:
                        self.logger.error(f"Error processing error element: {e}")

            # Special handling for textarea fields that are commonly used for text questions
            if len(all_fields_with_errors) == 0:
                # Use JavaScript to find textareas with errors
                textareas_with_errors = self.page.evaluate("""
                    () => {
                        const results = [];
                        // Find all textareas
                        const textareas = document.querySelectorAll('textarea');
                        for (const textarea of textareas) {
                            // Check if it has an associated error
                            const textareaId = textarea.id;
                            if (textareaId) {
                                const errorId = textareaId + '-error';
                                const errorEl = document.getElementById(errorId);
                                if (errorEl) {
                                    const isVisible = window.getComputedStyle(errorEl).display !== 'none';
                                    if (isVisible) {
                                        // Mark the textarea
                                        textarea.setAttribute('data-has-error', 'true');
                                        results.push(textareaId);
                                    }
                                }
                            }
                        }
                        return results;
                    }
                """)

                for textarea_id in textareas_with_errors:
                    # Find the textarea by the data-has-error attribute
                    textarea = self.page.query_selector('textarea[data-has-error="true"]')
                    if textarea:
                        # Remove the marker
                        self.page.evaluate("""
                            () => {
                                const el = document.querySelector('textarea[data-has-error="true"]');
                                if (el) el.removeAttribute('data-has-error');
                            }
                        """)

                        # Get error message if possible
                        error_id = f"{textarea_id}-error"
                        error_message = self.page.evaluate(f"""
                            () => {{
                                const errorEl = document.getElementById("{error_id}");
                                if (errorEl) return errorEl.innerText || "Invalid input";
                                return "Invalid input";
                            }}
                        """)

                        self.logger.info(f"Found textarea with error: {error_message}")
                        all_fields_with_errors.append((textarea, error_message))

            return all_fields_with_errors

        except Exception as e:
            self.logger.error(f"Error finding fields with errors: {e}")
            return []

    # Field type handlers
    def handle_select(self, select):
        """Handle select dropdown fields with clean question text."""
        if self.check_existing_value(select):
            self.logger.info("Select field already has a value, skipping")
            return
            
        # Get and clean question text
        raw_question_text = self.get_label_text(select)
        if not raw_question_text:
            return
        
        # Clean the question text
        question_text = self.response_manager.clean_question_text(raw_question_text)
        self.logger.info(f"\nProcessing select field: {question_text}")
        
        # Get available options
        options = [
            option.get_attribute('value') 
            for option in select.query_selector_all('option')
            if option.get_attribute('value') != "Select an option"
        ]
        self.logger.info(f"Available options: {options}")
        
        # Try saved responses with clean question text
        self.logger.info("Checking response database...")
        answer = self.response_manager.find_best_match(question_text, options)
        
        if not answer and options:
            # Try Gemini if no saved response
            self.logger.info("No match found, consulting Gemini...")
            answer = self.response_manager.get_gemini_response(question_text, options)
        
        if answer:
            self.logger.info(f"Using answer: {answer}")
            if self.browser_manager.safe_set_value(select, answer, "select"):
                self.logger.info(f"Successfully set select to: {answer}")

    def handle_radio(self, fieldset):
        """Handle radio button fields with improved tag name detection."""
        try:
            # Check if the fieldset has an error
            has_error = False
            error_message = None
    
            # Check for error indicators within or near the fieldset
            for indicator in self.selectors["ERROR_INDICATORS"]:
                error_element = fieldset.query_selector(indicator)
                if error_element and error_element.is_visible():
                    has_error = True
                    message_element = error_element.query_selector(".artdeco-inline-feedback__message")
                    error_message = message_element.inner_text().strip() if message_element else "Unknown error"
                    self.logger.info(f"Found error in radio fieldset: {error_message}")
                    break
                
            # Get and clean question text - IMPROVED METHOD
            raw_question_text = None
            
            # Method 1: Try standard fieldset legend
            legend = fieldset.query_selector("legend")
            if legend:
                raw_question_text = legend.inner_text().strip()
                self.logger.info(f"Found question from legend: {raw_question_text}")
            
            # Method 2: If no legend, look for the jobs-easy-apply-form-section__group-title span
            if not raw_question_text:
                # Try looking up a few levels to find the container with the question text
                section_title = fieldset.evaluate("""(element) => {
                    let container = element;
                    // Look up to 5 levels up
                    for (let i = 0; i < 5; i++) {
                        if (!container || container.tagName === 'BODY') break;
                        container = container.parentElement;
                        
                        if (container) {
                            // Look for the specific span with the question
                            const titleSpan = container.querySelector('.jobs-easy-apply-form-section__group-title');
                            if (titleSpan) return titleSpan.innerText;
                            
                            // Also check for h3 titles
                            const h3 = container.querySelector('h3');
                            if (h3) return h3.innerText;
                        }
                    }
                    return null;
                }""")
                
                if section_title:
                    raw_question_text = section_title
                    self.logger.info(f"Found question from section title: {raw_question_text}")
            
            # Method 3: Final fallback - try to extract anything useful from the fieldset's parent elements
            if not raw_question_text:
                container_text = fieldset.evaluate("""(element) => {
                    let container = element.parentElement;
                    if (container) {
                        // Get the text content of the container
                        return container.innerText;
                    }
                    return null;
                }""")
                
                if container_text:
                    # Try to extract a reasonable question from the container text
                    # Often the first line is the question
                    lines = container_text.split('\n')
                    # Find the first non-empty line
                    for line in lines:
                        if line.strip():
                            raw_question_text = line.strip()
                            self.logger.info(f"Extracted question from container text: {raw_question_text}")
                            break
                        
            # If still no question text, use a default
            if not raw_question_text:
                raw_question_text = "Radio button selection required"
                self.logger.info("Using default question text")
    
            # Clean the question text
            question_text = self.response_manager.clean_question_text(raw_question_text)
            self.logger.info(f"\nProcessing radio field: {question_text}")
    
            # Get available options from radio labels - IMPROVED METHOD
            options = []
            label_texts = []
            
            # Method 1: Try to get from label elements
            radio_labels = fieldset.query_selector_all("label")
            if radio_labels:
                for label in radio_labels:
                    try:
                        option_text = label.inner_text().strip()
                        if option_text:
                            options.append(option_text)
                            label_texts.append((label, option_text))
                    except Exception as e:
                        self.logger.error("Error getting label text", e)
            
            # Method 2: If no options found, try to get values from input elements
            if not options:
                radios = fieldset.query_selector_all('input[type="radio"]')
                for radio in radios:
                    try:
                        value = radio.get_attribute("value")
                        if value:
                            # Try to get the associated label
                            radio_id = radio.get_attribute("id")
                            if radio_id:
                                escaped_radio_id = self.css_escape(radio_id)
                                label = self.page.query_selector(f'label[for="{escaped_radio_id}"]')
                                if label:
                                    text = label.inner_text().strip()
                                    options.append(text)
                                    label_texts.append((label, text))
                                    continue
                                
                            # If we can't find a label, use the value
                            # Format camelCase or PascalCase values with spaces
                            import re
                            formatted_value = re.sub(r'([A-Z])', r' \1', value).strip()
                            options.append(formatted_value)
                            label_texts.append((radio, formatted_value))
                    except Exception as e:
                        self.logger.error("Error getting radio value", e)
                        
            self.logger.info(f"Available options: {options}")
    
            # Use response manager to get the best response
            answer = None
                    
            # Get response, with special handling for errors
            self.logger.info("Checking response database...")
            if has_error and error_message:
                # For errors, include the error message in the query
                answer = self.response_manager.find_best_match(question_text, options)
    
                if not answer and options:
                    self.logger.info("No match found with error context, consulting Gemini...")
                    answer = self.response_manager.get_gemini_response(question_text, options, error=error_message)
            else:
                # Normal flow without errors
                answer = self.response_manager.find_best_match(question_text, options)
    
                if not answer and options:
                    self.logger.info("No match found, consulting Gemini...")
                    answer = self.response_manager.get_gemini_response(question_text, options)
    
            # If we still don't have an answer but have options, pick one (default to first)
            if not answer and options:
                answer = options[0]
                self.logger.info(f"No answer found, using first option: {answer}")
    
            if answer:
                self.logger.info(f"Using answer: {answer}")
    
                # Find the matching label
                matched_label = None
                for label, text in label_texts:
                    # Check for exact match or if one contains the other
                    if answer.lower() == text.lower() or text.lower() in answer.lower() or answer.lower() in text.lower():
                        matched_label = label
                        break
                    
                if matched_label:
                    # Try multiple selection methods
                    success = False
    
                    # Determine if this is an input or label using evaluate instead of tag_name
                    is_input = matched_label.evaluate("el => el.tagName.toLowerCase() === 'input'")
                    
                    # Method 1: Direct click
                    try:
                        self.logger.info(f"Clicking element (is_input={is_input})")
                        matched_label.click()
                        time.sleep(0.5)
                        success = True
                    except Exception as e:
                        self.logger.error("Direct click failed", e)
    
                    # Method 2: If it's a label, try to find and click the radio input
                    if not success and not is_input:
                        try:
                            input_id = matched_label.get_attribute("for")
                            if input_id:
                                escaped_input_id = self.css_escape(input_id)
                                radio_input = self.page.query_selector(f"#{escaped_input_id}")
                                if radio_input:
                                    self.logger.info(f"Clicking radio input with id: {input_id}")
                                    radio_input.click()
                                    time.sleep(0.5)
                                    success = True
                        except Exception as e:
                            self.logger.error("Radio input click failed", e)
    
                    # Method 3: Use JavaScript
                    if not success:
                        try:
                            if is_input:
                                input_id = matched_label.get_attribute("id")
                            else:
                                input_id = matched_label.get_attribute("for")
                                
                            if input_id:
                                js_result = self.page.evaluate(f"""
                                    const radio = document.getElementById("{input_id}");
                                    if (radio) {{
                                        radio.click();
                                        radio.checked = true;
                                        radio.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                        return true;
                                    }}
                                    return false;
                                """)
                                if js_result:
                                    self.logger.info(f"Selected radio via JavaScript")
                                    success = True
                        except Exception as e:
                            self.logger.error("JavaScript radio selection failed", e)
    
                    if success:
                        self.logger.info(f"Successfully selected radio option: {answer}")
                    else:
                        self.logger.info(f"Failed to select radio option: {answer}")
                else:
                    self.logger.info(f"Could not find label matching answer: {answer}")
    
                    # Special handling for GDPR questions
                    if "reside" in question_text.lower() or "gdpr" in question_text.lower() or "data consent" in question_text.lower():
                        self.logger.info("This appears to be a GDPR question, using special handling")
                        
                        # Try to find the "No" option directly
                        no_option_found = False
                        
                        # First try: Find by label text "No"
                        for label in radio_labels:
                            if label.inner_text().strip().lower() == "no":
                                self.logger.info("Found 'No' option by label text")
                                label.click()
                                time.sleep(0.5)
                                no_option_found = True
                                break
                            
                        # Second try: Find by radio value containing "Other" (common for GDPR "No" options)
                        if not no_option_found:
                            js_result = self.page.evaluate("""
                                const radios = Array.from(document.querySelectorAll('input[type="radio"]'));
                                const noOption = radios.find(input => {
                                    const value = input.getAttribute('value') || '';
                                    return value.includes('Other');
                                });
                                
                                if (noOption) {
                                    noOption.click();
                                    noOption.checked = true;
                                    noOption.dispatchEvent(new Event('change', { bubbles: true }));
                                    return true;
                                }
                                return false;
                            """)
                            if js_result:
                                self.logger.info("Selected 'No' option by value containing 'Other'")
                                no_option_found = True
                        
                        # Last resort: Just click the second radio (common pattern for "No")
                        if not no_option_found:
                            radios = fieldset.query_selector_all('input[type="radio"]')
                            if len(radios) >= 2:
                                self.logger.info("Clicking second radio button as fallback for 'No'")
                                radios[1].click()
                                time.sleep(0.5)
    
        except Exception as e:
            self.logger.error(f"Error in handle_radio: {e}")

    def handle_text_input(self, input_field):
        """Handle text input fields with special handling for numeric fields."""
        try:
            # First check if the field has an error
            has_error, error_message = self.check_field_has_error(input_field)

            # Check if it's a numeric field with "whole number" error
            input_type = None
            try:
                input_type = input_field.get_attribute("type")
            except Exception:
                input_type = "text"  # Default

            # Skip if field is already filled and has no errors
            if not has_error:
                has_value = False
                try:
                    value = input_field.get_attribute("value")
                    has_value = value and value.strip()
                except Exception:
                    pass

                if has_value:
                    self.logger.info("Text field already has a valid value, skipping")
                    return True

            # If field has an error, clear it
            if has_error:
                self.logger.info(f"Field has error: {error_message} - clearing and refilling")
                self.browser_manager.clear_field(input_field)

            # Get and clean question text
            raw_question_text = self.get_label_text(input_field)

            # Fallback if no label found: try to use placeholder or name attribute
            if not raw_question_text:
                try:
                    placeholder = input_field.get_attribute("placeholder")
                    if placeholder:
                        raw_question_text = placeholder
                        self.logger.info(f"Using placeholder as label: {raw_question_text}")
                    else:
                        name = input_field.get_attribute("name")
                        if name:
                            raw_question_text = name
                            self.logger.info(f"Using name attribute as label: {raw_question_text}")
                        else:
                            # Last resort: just use the field type
                            raw_question_text = f"{input_type} field"
                            self.logger.info(f"Using generic label: {raw_question_text}")
                except Exception:
                    raw_question_text = f"{input_type} field"
                    self.logger.info(f"Using generic label: {raw_question_text}")

            # Clean the question text
            question_text = self.response_manager.clean_question_text(raw_question_text)
            self.logger.info(f"\nProcessing text field: {question_text}")

            # Try saved responses first
            self.logger.info(f"Looking for match for question: {question_text}")
            answer = self.response_manager.find_best_match(question_text)

            if answer:
                self.logger.info(f"Found match! Answer: {answer[:100]}{'...' if len(answer) > 100 else ''}")

            # If no saved response or we have an error, get a new response
            if not answer or has_error:
                # Construct a better prompt if we have an error message
                if has_error:
                    self.logger.info(f"Getting response with error context: {error_message}")
                    answer = self.response_manager.get_gemini_response(question_text, error=error_message)
                else:
                    answer = self.response_manager.get_gemini_response(question_text)

            # For numeric fields with "whole number" error, just use a safe number
            if input_type == "number" and has_error and error_message and "whole number" in error_message.lower():
                self.logger.info("Using '5' for numeric field with whole number error")
                answer = "5"

            # Fill the field
            if answer:
                self.logger.info(f"Setting field to: {answer[:100]}{'...' if len(answer) > 100 else ''}")
                success = self.browser_manager.safe_set_value(input_field, answer, "input")

                # Check if error persists after setting value
                if success:
                    time.sleep(0.5)
                    still_has_error, new_error = self.check_field_has_error(input_field)
                    if still_has_error:
                        self.logger.info(f"Error persists: {new_error}")

                        # For numeric fields, try a different value
                        if input_type == "number":
                            self.logger.info("Trying alternative numeric value")
                            try:
                                # Try several standard values
                                for alt_value in ["5", "10", "1", "0"]:
                                    self.browser_manager.safe_set_value(input_field, alt_value, "input")
                                    time.sleep(0.5)
                                    if not self.check_field_has_error(input_field)[0]:
                                        self.logger.info(f"Alternative value {alt_value} worked")
                                        break
                            except Exception as alt_error:
                                self.logger.error(f"Error trying alternative numeric values: {alt_error}")

                return success

            return True

        except Exception as e:
            self.logger.error(f"Error in handle_text_input: {e}")
            return False

    def handle_typeahead(self, input_field):
        """Handle typeahead input fields with clean question text and error detection."""
        # First check if the field has an error
        has_error, error_message = self.check_field_has_error(input_field)

        # Skip if field is already filled and has no errors
        if not has_error and self.check_existing_value(input_field):
            self.logger.info("Typeahead field already has a valid value, skipping")
            return

        # If field has an error, we need to clear it and refill
        if has_error:
            self.logger.info(f"Field has error: {error_message} - clearing and refilling")
            self.browser_manager.clear_field(input_field)

        # Get and clean question text
        raw_question_text = self.get_label_text(input_field)
        if not raw_question_text:
            return

        # Clean the question text
        question_text = self.response_manager.clean_question_text(raw_question_text)
        self.logger.info(f"\nProcessing typeahead field: {question_text}")

        # For location fields specifically, use a default if we have an error
        is_location_field = any(location_term in question_text.lower() for location_term in 
                               ["location", "city", "address", "where"])

        # Try saved responses with clean question text
        self.logger.info("Checking response database...")
        answer = self.response_manager.find_best_match(question_text)

        if not answer:
            # Use a more specific prompt for Gemini if this is a location field with an error
            if is_location_field and has_error:
                self.logger.info("Location field with error - getting specific location response...")
                location_prompt = question_text
                answer = self.response_manager.get_gemini_response(location_prompt, error=f"need a valid city and state. Previous gemini response received an error: {error_message}")
            else:
                # Try Gemini with normal prompt
                self.logger.info("No match found, consulting Gemini...")
                answer = self.response_manager.get_gemini_response(question_text)

        # Default to San Francisco for location fields if we still don't have an answer
        if not answer and is_location_field:
            answer = "San Francisco, California"
            self.logger.info(f"Using default location: {answer}")

        if answer:
            self.logger.info(f"Using answer: {answer}")
            # For typeaheads, we need to:
            # 1. Fill the field
            # 2. Wait for suggestions
            # 3. Press down/enter to select the first suggestion

            try:
                # Fill the field
                self.browser_manager.safe_set_value(input_field, answer, "input")

                # Wait for suggestions to appear (LinkedIn typically shows a dropdown)
                time.sleep(1.5)

                # Press down and then enter to select the first suggestion
                input_field.press('ArrowDown')
                time.sleep(0.5)
                input_field.press('Enter')

                # Wait to see if the error is resolved
                time.sleep(1)

                # Check if error persists
                still_has_error, new_error = self.check_field_has_error(input_field)
                if still_has_error:
                    self.logger.info(f"Error persists: {new_error} - trying alternative approach")

                    # Try a different format or more specific value
                    if is_location_field:
                        # For location fields, try just the city
                        city_only = answer.split(',')[0].strip()
                        self.logger.info(f"Trying with city only: {city_only}")

                        # Clear field again
                        input_field.fill("")
                        time.sleep(0.5)

                        # Fill with city only
                        self.browser_manager.safe_set_value(input_field, city_only, "input")
                        time.sleep(1.5)

                        # Try to select from dropdown
                        input_field.press('ArrowDown')
                        time.sleep(0.5)
                        input_field.press('Enter')

                self.logger.info(f"Filled typeahead field with: {answer}")

            except Exception as e:
                self.logger.error("Error handling typeahead field", e)

    def handle_date_input(self, input_field):
        """Handle date input fields by detecting and filling with current date."""
        try:
            # First check if the field has an error
            has_error, error_message = self.check_field_has_error(input_field)

            # Skip if field is already filled and has no errors
            if not has_error and self.check_existing_value(input_field):
                self.logger.info("Date field already has a valid value, skipping")
                return True

            # Get and clean question text for logging
            raw_question_text = self.get_label_text(input_field)
            question_text = self.response_manager.clean_question_text(raw_question_text) if raw_question_text else "Date field"
            self.logger.info(f"\nProcessing date field: {question_text}")

            # Check if the calendar widget is open
            calendar_widget = self.page.query_selector('.artdeco-datepicker__widget-container')
            calendar_visible = calendar_widget and calendar_widget.is_visible()

            # Get today's date in MM/DD/YYYY format
            today = datetime.now()
            formatted_date = today.strftime('%m/%d/%Y')
            self.logger.info(f"Using today's date: {formatted_date}")

            # Approach 1: Try to directly fill the input field
            if not calendar_visible:
                self.logger.info("Directly filling date input field")
                input_field.fill(formatted_date)
                time.sleep(0.5)

                # Check if calendar appears after filling
                calendar_widget = self.page.query_selector('.artdeco-datepicker__widget-container')
                calendar_visible = calendar_widget and calendar_widget.is_visible()

                if not calendar_visible:
                    self.logger.info("Successfully set date by direct input")
                    return True

            # Approach 2: If calendar is visible, select today's date from the widget
            if calendar_visible:
                self.logger.info("Calendar widget is visible, selecting today's date")

                # Look for the "today" button which often has a special class
                today_button = self.page.query_selector('button.artdeco-calendar-day-btn--today')

                if today_button:
                    self.logger.info("Found today button, clicking it")
                    today_button.click()
                    time.sleep(0.5)

                    # Check if calendar disappeared (date was selected)
                    calendar_still_visible = self.page.is_visible('.artdeco-datepicker__widget-container')

                    if not calendar_still_visible:
                        self.logger.info("Successfully selected today's date from calendar")
                        return True

                # If no today button or it didn't work, try to find the current day by aria-label
                today_day = today.day
                today_str = today.strftime('%A, %B %d, %Y')

                # Try to find by aria-label containing today's date
                day_buttons = self.page.query_selector_all('button[data-calendar-day]')
                for button in day_buttons:
                    aria_label = button.get_attribute('aria-label')
                    if aria_label and "This is today" in aria_label:
                        self.logger.info(f"Found today button by aria-label: {aria_label}")
                        button.click()
                        time.sleep(0.5)
                        return True

                    # Also check just for matching day number
                    day_num = button.inner_text().strip()
                    if day_num == str(today_day):
                        # Further verify if this is in current month
                        if "diff-month" not in button.get_attribute('class'):
                            self.logger.info(f"Found potential today button by day number: {day_num}")
                            button.click()
                            time.sleep(0.5)
                            return True

                # Last resort: Try clicking the cancel button to close the calendar, then set text directly
                cancel_button = self.page.query_selector('.artdeco-calendar__footer-btn:has-text("Cancel")')
                if cancel_button:
                    self.logger.info("Clicking cancel button to close calendar")
                    cancel_button.click()
                    time.sleep(0.5)

                    # Try direct input again
                    self.logger.info("Trying direct input after closing calendar")
                    input_field.fill(formatted_date)
                    time.sleep(0.5)

            # Final verification - check if there are still errors
            has_error, error_message = self.check_field_has_error(input_field)
            if has_error:
                self.logger.info(f"Error persists after date selection: {error_message}")
                return False

            return True

        except Exception as e:
            self.logger.error("Error handling date input", e)
            return False

    def handle_checkbox(self, element):
        """
        Handle checkbox fields using response manager to select the best options.
        """
        try:
            # Type safety and conversion check
            if isinstance(element, str):
                self.logger.warning(f"Received string instead of element: {element}")
                
                # Try to find the fieldset with this text
                fieldset = self.page.query_selector(f'fieldset:has(legend:has-text("{element}"))')
                if fieldset:
                    element = fieldset
                else:
                    self.logger.error(f"Could not find fieldset for text: {element}")
                    return False

            # Determine if this is a fieldset or a checkbox
            element_type = None
            try:
                element_type = element.evaluate('el => el.tagName.toLowerCase()')
            except Exception as e:
                self.logger.error(f"Error determining element type: {e}")
                return False
                    
            # Initialize variables
            fieldset = None
            checkbox_field = None
            has_error = False
            error_message = None
            
            # If it's a checkbox (not a fieldset), find its parent fieldset
            if element_type == 'input':
                # This is a single checkbox
                checkbox_field = element
                
                # Check for errors on this checkbox
                has_error, error_message = self.check_field_has_error(checkbox_field)
                
                # Find parent fieldset (if this is part of a checkbox group)
                fieldset = checkbox_field.evaluate("""(el) => {
                    let node = el;
                    for (let i = 0; i < 5 && node; i++) {
                        if (node.tagName && node.tagName.toLowerCase() === 'fieldset') {
                            return node;
                        }
                        node = node.parentElement;
                    }
                    return null;
                }""")
            else:
                # This is a fieldset - check for errors on the fieldset
                fieldset = element
                has_error, error_message = self.check_field_has_error(fieldset)

            # Get question text for the checkbox or group
            question_text = ""
            available_options = []

            if fieldset:
                # First try: For a checkbox group, get the legend text
                legend = fieldset.query_selector("legend")
                if legend:
                    raw_question_text = legend.inner_text().strip()
                    question_text = self.response_manager.clean_question_text(raw_question_text)
                    self.logger.info(f"\nProcessing checkbox group: {question_text}")
                else:
                    # Second try: Look for section title span outside the fieldset
                    self.logger.warning("No legend found for checkbox group, looking for section title")
                    section_title = fieldset.evaluate("""(fieldset) => {
                        // Go up a few levels to find container
                        let container = fieldset;
                        for (let i = 0; i < 5; i++) {
                            if (!container || container.tagName === 'BODY') break;
                            container = container.parentElement;
                            
                            if (container) {
                                // Look for the section title span (LinkedIn's pattern)
                                const title = container.querySelector('.jobs-easy-apply-form-section__group-title');
                                if (title) return title.textContent.trim();
                                
                                // Also try h3 titles which are sometimes used
                                const h3 = container.querySelector('h3.t-16');
                                if (h3) return h3.textContent.trim();
                            }
                        }
                        return null;
                    }""")
                    
                    if section_title:
                        question_text = self.response_manager.clean_question_text(section_title)
                        self.logger.info(f"Found section title as question: {question_text}")
                    else:
                        # Fallback
                        self.logger.warning("No section title found, using default text")
                        question_text = "Checkbox group selection"

                # Get all available options from the fieldset
                checkboxes = fieldset.query_selector_all('input[type="checkbox"]')
                for checkbox in checkboxes:
                    try:
                        # Get option text from associated label
                        checkbox_id = checkbox.get_attribute("id")
                        if checkbox_id:
                            # Use CSS.escape for IDs with special characters
                            escaped_id = self.css_escape(checkbox_id)
                            label = self.page.query_selector(f"label[for='{escaped_id}']")
                            if label:
                                option_text = label.inner_text().strip()
                                available_options.append(option_text)
                    except Exception as e:
                        self.logger.error(f"Error getting checkbox option: {e}")

                self.logger.info(f"Available options: {available_options}")
            elif checkbox_field:
                # For a single checkbox, get its label
                checkbox_id = checkbox_field.get_attribute("id")
                if checkbox_id:
                    # Use CSS.escape for IDs with special characters
                    escaped_id = self.css_escape(checkbox_id)
                    label = self.page.query_selector(f'label[for="{escaped_id}"]')
                    if label:
                        raw_question_text = label.inner_text().strip()
                        question_text = self.response_manager.clean_question_text(raw_question_text)
                        self.logger.info(f"\nProcessing single checkbox: {question_text}")
                        available_options = ["Yes", "No"]  # For single checkbox, options are Yes (check) or No (uncheck)
                    else:
                        self.logger.warning("No label found for checkbox")
                        question_text = "Checkbox selection"
                        available_options = ["Yes", "No"]
                else:
                    self.logger.warning("Checkbox has no ID")
                    question_text = "Checkbox selection"
                    available_options = ["Yes", "No"]
            else:
                self.logger.warning("Neither fieldset nor checkbox detected")
                return False

            # Check if we should clear checkboxes due to errors
            if has_error:
                self.logger.info(f"Checkbox has error: {error_message} - clearing selections")
                if fieldset:
                    # Uncheck all checkboxes in the group
                    checkboxes = fieldset.query_selector_all('input[type="checkbox"]')
                    for checkbox in checkboxes:
                        if checkbox.is_checked():
                            checkbox.uncheck()
                elif checkbox_field:
                    # Uncheck the single checkbox
                    if checkbox_field.is_checked():
                        checkbox_field.uncheck()

            # Try saved responses with clean question text
            self.logger.info("Checking response database...")
            answer = self.response_manager.find_best_match(question_text, available_options)

            if not answer:
                # If no saved response or we have an error, get a new response
                if has_error:
                    self.logger.info(f"Getting response with error context: {error_message}")
                    answer = self.response_manager.get_gemini_response(question_text, available_options, error=error_message)
                else:
                    self.logger.info("No match found, consulting Gemini...")
                    answer = self.response_manager.get_gemini_response(question_text, available_options)

            if answer:
                self.logger.info(f"Using answer: {answer}")

                if fieldset:
                    # For checkbox groups, the answer could be a single option or multiple options
                    selected_options = []

                    # Parse the answer to identify selected options
                    if isinstance(answer, list):
                        selected_options = answer
                    else:
                        # Try to parse comma-separated or newline-separated options
                        if "," in answer:
                            selected_options = [opt.strip() for opt in answer.split(",")]
                        elif "\n" in answer:
                            selected_options = [opt.strip() for opt in answer.split("\n")]
                        else:
                            # Single option
                            selected_options = [answer]

                    # Make sure we have at least one selection for required fields with errors
                    if has_error and not selected_options:
                        self.logger.info("No options identified in answer but field has error - selecting first option")
                        if available_options:
                            selected_options = [available_options[0]]

                    # Find and check the matching checkboxes
                    success = False
                    checkboxes = fieldset.query_selector_all('input[type="checkbox"]')

                    for option in selected_options:
                        option_matched = False

                        for checkbox in checkboxes:
                            checkbox_id = checkbox.get_attribute("id")
                            if checkbox_id:
                                # Use CSS.escape for IDs with special characters
                                escaped_id = self.css_escape(checkbox_id)
                                label = self.page.query_selector(f"label[for='{escaped_id}']")

                                if label:
                                    label_text = label.inner_text().strip()

                                    # Check for exact match or contains relationship
                                    if (label_text.lower() == option.lower() or 
                                        label_text.lower() in option.lower() or 
                                        option.lower() in label_text.lower()):

                                        self.logger.info(f"Checking option: {label_text}")
                                        
                                        # Try multiple methods to check the checkbox
                                        option_matched = self._try_check_checkbox(checkbox, checkbox_id, label)
                                        if option_matched:
                                            success = True
                                            break
                                        
                        if not option_matched:
                            self.logger.warning(f"Could not find checkbox matching option: {option}")

                    # If we couldn't match any options but need to check something (required with error)
                    if has_error and not success and checkboxes and len(checkboxes) > 0:
                        self.logger.info("No matches found but field is required - checking first checkbox")
                        
                        # Get the first checkbox
                        first_checkbox = checkboxes[0]
                        checkbox_id = first_checkbox.get_attribute("id")
                        label = None
                        
                        if checkbox_id:
                            escaped_id = self.css_escape(checkbox_id)
                            label = self.page.query_selector(f"label[for='{escaped_id}']")
                        
                        success = self._try_check_checkbox(first_checkbox, checkbox_id, label)
                        if not success:
                            self.logger.error("All attempts to check checkbox failed")

                    return success
                elif checkbox_field:
                    # For single checkbox, check if answer is affirmative
                    affirmative = answer.lower() in ["yes", "true", "checked", "selected", "enable", "1"]

                    if affirmative:
                        self.logger.info("Checking single checkbox")
                        # Get associated label for the checkbox
                        checkbox_id = checkbox_field.get_attribute("id")
                        label = None
                        if checkbox_id:
                            escaped_id = self.css_escape(checkbox_id)
                            label = self.page.query_selector(f"label[for='{escaped_id}']")
                        
                        # Use multiple methods to check the checkbox
                        success = self._try_check_checkbox(checkbox_field, checkbox_id, label)
                        return success
                    else:
                        self.logger.info("Unchecking single checkbox")
                        checkbox_field.uncheck()
                        return True
                else:
                    self.logger.warning("No fieldset or checkbox field to act on")
                    return False
            else:
                # Default behavior for required fields with errors
                if has_error:
                    self.logger.info("No response but field has error - checking first checkbox or the single checkbox")
                    if fieldset:
                        checkboxes = fieldset.query_selector_all('input[type="checkbox"]')
                        if checkboxes and len(checkboxes) > 0:
                            first_checkbox = checkboxes[0]
                            checkbox_id = first_checkbox.get_attribute("id")
                            label = None
                            if checkbox_id:
                                escaped_id = self.css_escape(checkbox_id)
                                label = self.page.query_selector(f"label[for='{escaped_id}']")
                            return self._try_check_checkbox(first_checkbox, checkbox_id, label)
                    elif checkbox_field:
                        checkbox_id = checkbox_field.get_attribute("id")
                        label = None
                        if checkbox_id:
                            escaped_id = self.css_escape(checkbox_id)
                            label = self.page.query_selector(f"label[for='{escaped_id}']")
                        return self._try_check_checkbox(checkbox_field, checkbox_id, label)
                    return True
                
                return False

        except Exception as e:
            self.logger.error(f"Error in handle_checkbox: {e}")
            return False

    def _try_check_checkbox(self, checkbox, checkbox_id, label=None):
        """
        Optimized function to check checkboxes that prioritizes direct DOM manipulation
        for checkboxes with intercepted pointer events.
        
        Args:
            checkbox: The checkbox element
            checkbox_id: The ID of the checkbox
            label: The associated label element (if available)
        
        Returns:
            bool: True if successfully checked, False otherwise
        """
        # Method 1: JavaScript direct property manipulation - fastest and most reliable
        if checkbox_id:
            try:
                self.logger.info("Method 1: Direct JavaScript property manipulation")
                result = self.page.evaluate(f"""
                    (() => {{
                        const checkbox = document.getElementById('{checkbox_id}');
                        if (checkbox) {{
                            checkbox.checked = true;
                            checkbox.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            return checkbox.checked;
                        }}
                        return false;
                    }})()
                """)
                
                if result:
                    self.logger.info("✓ Method 1 succeeded: checkbox checked via JavaScript")
                    return True
            except Exception as e:
                self.logger.error(f"✗ Method 1 failed: {e}")
        
        # Method 2: Try force with set_checked - also doesn't use pointer events
        try:
            self.logger.info("Method 2: Using set_checked(True) with force=True")
            checkbox.set_checked(True, force=True)
            time.sleep(0.2)
            
            # Verify if checked
            is_checked = checkbox.is_checked()
            if is_checked:
                self.logger.info("✓ Method 2 succeeded: checkbox checked via force")
                return True
        except Exception as e:
            self.logger.error(f"✗ Method 2 failed: {e}")
        
        # Method 3: Click the label instead of the checkbox with very short timeout
        if label:
            try:
                self.logger.info("Method 3: Clicking the label with short timeout")
                # Just 1.5 second timeout
                label.click(timeout=1500)
                time.sleep(0.2)
                
                # Verify if checked
                is_checked = checkbox.is_checked()
                if is_checked:
                    self.logger.info("✓ Method 3 succeeded: checkbox checked via label")
                    return True
            except Exception as e:
                self.logger.error(f"✗ Method 3 failed: {e}")
        
        # Method 4: Standard check method but with very short timeout
        try:
            self.logger.info("Method 4: Using standard check() with short timeout")
            # Just 1.5 second timeout
            checkbox.check(timeout=1500)
            time.sleep(0.2)
            
            # Verify if checked
            is_checked = checkbox.is_checked()
            if is_checked:
                self.logger.info("✓ Method 4 succeeded: checkbox checked")
                return True
        except Exception as e:
            self.logger.error(f"✗ Method 4 failed: {e}")
        
        # Method 5: Last resort - evaluate directly on element
        try:
            self.logger.info("Method 5: Element evaluate approach")
            result = checkbox.evaluate("""
                (el) => {
                    try {
                        el.checked = true;
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        return el.checked;
                    } catch (e) {
                        return false;
                    }
                }
            """)
            
            if result:
                self.logger.info("✓ Method 5 succeeded: checkbox checked via element evaluate")
                return True
        except Exception as e:
            self.logger.error(f"✗ Method 5 failed: {e}")
        
        self.logger.error("All checkbox interaction methods failed")
        return False

    def handle_education_date_fields(self):
        """
        Specifically handle the education date fields which are complex with multiple select dropdowns.
        """
        try:
            # Check for education section header using selector from config
            education_header = self.page.query_selector(SELECTORS["EDUCATION"]["SECTION_HEADER"])
    
            if not education_header:
                return False
    
            self.logger.info("Detected education section, handling with default values...")
    
            # Find the date-range fieldsets using selectors from config
            from_fieldset = self.page.query_selector(SELECTORS["EDUCATION"]["START_FIELDSET"])
            to_fieldset = self.page.query_selector(SELECTORS["EDUCATION"]["END_FIELDSET"])
    
            if not from_fieldset or not to_fieldset:
                self.logger.info("Could not find date range fieldsets")
                return False
    
            # Find month and year selects in "From" date
            from_month_select = from_fieldset.query_selector(SELECTORS["EDUCATION"]["MONTH_SELECT"])
            from_year_select = from_fieldset.query_selector(SELECTORS["EDUCATION"]["YEAR_SELECT"])
    
            # Find month and year selects in "To" date
            to_month_select = to_fieldset.query_selector(SELECTORS["EDUCATION"]["MONTH_SELECT"])
            to_year_select = to_fieldset.query_selector(SELECTORS["EDUCATION"]["YEAR_SELECT"])
    
            # Make sure we found all selects
            if not all([from_month_select, from_year_select, to_month_select, to_year_select]):
                self.logger.info("Could not find all date select dropdowns")
                return False
    
            # Set education start date using values from config
            self.logger.info(f"Setting education start date to month {EDUCATION_DEFAULTS['start_month']} year {EDUCATION_DEFAULTS['start_year']}...")
            self.browser_manager.safe_set_value(from_month_select, EDUCATION_DEFAULTS["start_month"], "select")
            self.browser_manager.safe_set_value(from_year_select, EDUCATION_DEFAULTS["start_year"], "select")
    
            # Set education end date using values from config
            self.logger.info(f"Setting education end date to month {EDUCATION_DEFAULTS['end_month']} year {EDUCATION_DEFAULTS['end_year']}...")
            self.browser_manager.safe_set_value(to_month_select, EDUCATION_DEFAULTS["end_month"], "select")
            self.browser_manager.safe_set_value(to_year_select, EDUCATION_DEFAULTS["end_year"], "select")
    
            # Check for "I currently attend" checkbox
            current_attend_checkbox = self.page.query_selector(SELECTORS["EDUCATION"]["CURRENT_CHECKBOX"])
            if current_attend_checkbox:
                # Make sure it's unchecked
                if current_attend_checkbox.is_checked():
                    current_attend_checkbox.uncheck()
                    self.logger.info("Unchecked 'I currently attend this institution' checkbox")
                else:
                    self.logger.info("'I currently attend this institution' checkbox already unchecked")
    
            # Find and fill school field - using selectors from config
            for selector in SELECTORS["EDUCATION"]["SCHOOL_SELECT"]:
                school_select = self.page.query_selector(selector)
                if school_select:
                    self.browser_manager.safe_set_value(school_select, EDUCATION_DEFAULTS["university"], "select")
                    self.logger.info(f"Set school to {EDUCATION_DEFAULTS['university']}")
                    break
                
            # Find and fill degree field
            degree_select = self.page.query_selector(SELECTORS["EDUCATION"]["DEGREE_SELECT"])
            if not degree_select:
                # Try alternative selector based on the HTML
                degree_select = self.page.query_selector(SELECTORS["EDUCATION"]["SCHOOL_SELECT"][1])
    
            if degree_select:
                self.browser_manager.safe_set_value(degree_select, EDUCATION_DEFAULTS["degree"], "select")
                self.logger.info(f"Set degree to {EDUCATION_DEFAULTS['degree']}")
    
            # Find and fill discipline field
            discipline_select = self.page.query_selector(SELECTORS["EDUCATION"]["DISCIPLINE_SELECT"])
            if not discipline_select:
                # Try to find it with a more general selector if not found directly
                all_selects = self.page.query_selector_all(SELECTORS["EDUCATION"]["SCHOOL_SELECT"][1])
                if len(all_selects) >= 3:  # If we have at least 3 dropdown fields, the 3rd is likely discipline
                    discipline_select = all_selects[2]
    
            if discipline_select:
                self.browser_manager.safe_set_value(discipline_select, EDUCATION_DEFAULTS["discipline"], "select")
                self.logger.info(f"Set discipline to {EDUCATION_DEFAULTS['discipline']}")
    
            self.logger.info("Successfully handled education fields with default values")
            return True
    
        except Exception as e:
            self.logger.error("Error handling education date fields", e)
            return False

    def process_all_form_fields(self, modal):
        """
        Comprehensive processing of all form fields in the modal.
        Handles different field types systematically.
        """
        self.logger.info("\n=== Processing All Form Fields ===")
    
        # Process Checkbox Fields
        self._process_checkbox_fields(modal)
    
        # Process Radio Button Fields
        self._process_radio_fields(modal)
    
        # Process Select Dropdowns
        self._process_select_fields(modal)
    
        # Process Text Inputs and Textareas
        self._process_text_inputs(modal)
    
        # Final error check
        self._final_error_validation(modal)
    
        self.logger.info("=== Completed Processing All Form Fields ===")
        return True
    
    def _process_checkbox_fields(self, modal):
        """Process all checkbox fields in the modal."""
        checkbox_fieldsets = modal.query_selector_all('fieldset:has(input[type="checkbox"])')
        self.logger.info(f"Total checkbox fieldsets found: {len(checkbox_fieldsets)}")
    
        for fieldset in checkbox_fieldsets:
            try:
                # Ensure we have a valid fieldset
                if not fieldset:
                    continue
                
                # Log fieldset details
                legend = fieldset.query_selector('legend')
                question_text = legend.inner_text().strip() if legend else "Unnamed Checkbox Group"
                self.logger.info(f"\nProcessing Checkbox Fieldset: {question_text}")
    
                # Get checkbox inputs
                checkboxes = fieldset.query_selector_all('input[type="checkbox"]')
                self.logger.info(f"Number of checkboxes: {len(checkboxes)}")
    
                # Log checkbox options
                for checkbox in checkboxes:
                    try:
                        checkbox_id = checkbox.get_attribute('id')
                        label = self.page.query_selector(f'label[for="{self.css_escape(checkbox_id)}"]')
                        option_text = label.inner_text().strip() if label else "No label found"
                        self.logger.info(f"  Checkbox option: {option_text}")
                    except Exception as label_error:
                        self.logger.error(f"Error getting checkbox label: {label_error}")
    
                # Process the entire fieldset
                self.handle_checkbox(fieldset)
    
            except Exception as e:
                self.logger.error(f"Error processing checkbox fieldset: {e}", exc_info=True)
    
    def _process_radio_fields(self, modal):
        """Process all radio button fields in the modal."""
        radio_fieldsets = modal.query_selector_all("fieldset:has(input[type='radio'])")
        self.logger.info(f"Found {len(radio_fieldsets)} radio button fieldsets")
    
        for fieldset in radio_fieldsets:
            try:
                # Verify it contains radio inputs
                radio_inputs = fieldset.query_selector_all('input[type="radio"]')
                if radio_inputs and len(radio_inputs) > 0:
                    self.handle_radio(fieldset)
            except Exception as e:
                self.logger.error(f"Error processing radio fieldset: {e}", exc_info=True)
    
    def _process_select_fields(self, modal):
        """Process all select dropdown fields in the modal."""
        select_fields = modal.query_selector_all("select")
        self.logger.info(f"Found {len(select_fields)} select fields")
    
        for select in select_fields:
            try:
                # Skip if already has a valid value
                if self.check_existing_value(select):
                    select_id = select.get_attribute("id") or "unknown"
                    self.logger.info(f"Select {select_id} already has a value, skipping")
                    continue
                
                # Process the select field
                self.handle_select(select)
            except Exception as e:
                self.logger.error(f"Error processing select field: {e}", exc_info=True)
    
    def _process_text_inputs(self, modal):
        """Process all text inputs and textareas in the modal."""
        input_selectors = [
            'input[type="text"]', 
            'input[type="email"]', 
            'input[type="tel"]', 
            'input[type="url"]',
            'input[type="number"]',
            'textarea'
        ]
    
        for selector in input_selectors:
            inputs = modal.query_selector_all(selector)
            self.logger.info(f"Found {len(inputs)} fields for selector: {selector}")
    
            for input_field in inputs:
                try:
                    # Skip date inputs
                    if selector != 'textarea':
                        is_date_input = input_field.evaluate('el => !!el.closest(".artdeco-datepicker")')
                        if is_date_input:
                            self.logger.info("Skipping already handled date input")
                            continue
                        
                    # Skip if already has a value and no errors
                    has_error, _ = self.check_field_has_error(input_field)
    
                    if not has_error:
                        value = input_field.evaluate('el => el.value || ""')
                        if value and value.strip():
                            self.logger.info("Field already has a valid value, skipping")
                            continue
                        
                    # Determine and handle field type
                    field_type = self.determine_field_type(input_field)
    
                    if field_type == "typeahead":
                        self.handle_typeahead(input_field)
                    elif field_type == "date":
                        self.handle_date_input(input_field)
                    else:
                        self.handle_text_input(input_field)
                except Exception as e:
                    self.logger.error(f"Error processing input field: {e}", exc_info=True)
    
    def _final_error_validation(self, modal):
        """Perform final validation and log any remaining errors."""
        error_elements = modal.query_selector_all('.artdeco-inline-feedback--error:not([style*="display: none"])')
        visible_errors = [e for e in error_elements if e.is_visible()]
    
        if visible_errors:
            self.logger.info(f"\nWARNING: {len(visible_errors)} errors remain after processing")
            for error_element in visible_errors:
                try:
                    error_text = error_element.inner_text().strip()
                    self.logger.info(f"Remaining error: {error_text}")
                except:
                    self.logger.info("Could not read error text")
    
    
    def handle_form_fields(self):
        """
        Coordinate the overall form fields processing.
        Handles special cases and calls the main processing method.
        """
        self.logger.info("\n=== Processing Form Fields ===")

        # Define the modal selector
        modal = self.page.query_selector(self.selectors["MODAL"])
        if not modal:
            self.logger.info("Easy Apply modal not found!")
            return False

        self.logger.info("Found Easy Apply modal, processing its form fields...")

        try:
            # Proactively handle required fields first
            self.handle_required_fields(modal)

            # Main processing of all form fields
            self.process_all_form_fields(modal)

            # Handle any remaining errors or unhandled fields
            self.handle_remaining_errors(modal)

            self.logger.info("\n=== Completed Form Fields Processing ===")
            return True

        except Exception as e:
            self.logger.error(f"Error during form fields processing: {e}", exc_info=True)
            return False

    def handle_required_fields(self, modal):
        """
        Proactively handle required fields, especially checkboxes.
        """
        # Find required fieldsets
        required_fieldsets = modal.query_selector_all('fieldset:has(legend:has(.fb-dash-form-element__label-title--is-required))')
        self.logger.info(f"Found {len(required_fieldsets)} required fieldsets")

        for fieldset in required_fieldsets:
            try:
                # Check if this contains checkboxes
                checkboxes = fieldset.query_selector_all('input[type="checkbox"]')
                if checkboxes and len(checkboxes) > 0:
                    self.logger.info(f"Found required fieldset with {len(checkboxes)} checkboxes")

                    # Check if any checkbox is already checked
                    any_checked = any(checkbox.is_checked() for checkbox in checkboxes)

                    # If none are checked, find the first non-optional checkbox
                    if not any_checked:
                        for checkbox in checkboxes:
                            if not self.should_skip_checkbox(checkbox):
                                self.logger.info("Proactively checking first non-optional checkbox")
                                self.handle_checkbox(fieldset)  # Pass the entire fieldset
                                break
            except Exception as e:
                self.logger.error(f"Error handling required fieldset: {e}", exc_info=True)

    def handle_remaining_errors(self, modal):
        """
        Handle any remaining errors after main processing.
        """
        # Check for selection errors
        selection_errors = modal.query_selector_all(
            '.artdeco-inline-feedback--error:has-text("selection"), '
            '.artdeco-inline-feedback--error:has-text("make a selection"), '
            '.artdeco-inline-feedback--error:has-text("select")'
        )

        if selection_errors and len(selection_errors) > 0:
            self.logger.info(f"Found {len(selection_errors)} remaining selection errors")

            for error in selection_errors:
                try:
                    # Try to handle the error by finding and checking a checkbox
                    self._handle_selection_error(error)
                except Exception as e:
                    self.logger.error(f"Error processing selection error: {e}", exc_info=True)

        # Final error check
        error_elements = modal.query_selector_all('.artdeco-inline-feedback--error:not([style*="display: none"])')
        visible_errors = [e for e in error_elements if e.is_visible()]

        if visible_errors:
            self.logger.info(f"\nWARNING: {len(visible_errors)} errors still remain after processing")
            for error_element in visible_errors:
                try:
                    error_text = error_element.inner_text().strip()
                    self.logger.info(f"Remaining error: {error_text}")
                except:
                    pass
        else:
            self.logger.info("\nNo errors detected after processing")

    def _handle_selection_error(self, error):
        """
        Handle a specific selection error by finding and checking an appropriate checkbox.
        """
        error_id = error.get_attribute("id") or ""
        if error_id and "-error" in error_id:
            fieldset_id = error_id.replace("-error", "")

            # Use JavaScript to safely handle the error
            self.page.evaluate(f"""
                () => {{
                    const fieldset = document.getElementById("{fieldset_id}");
                    if (!fieldset) return false;

                    // Skip optional fieldsets
                    const legend = fieldset.querySelector('legend');
                    if (legend) {{
                        const legendText = legend.textContent.toLowerCase();
                        if (legendText.includes('optional') || legendText.includes('top choice')) {{
                            return false;
                        }}
                    }}

                    // Find checkboxes
                    const checkboxes = fieldset.querySelectorAll('input[type="checkbox"]');
                    if (checkboxes.length === 0) return false;

                    // Check if any are already checked
                    const anyChecked = Array.from(checkboxes).some(cb => cb.checked);

                    // If none are checked, check the first one
                    if (!anyChecked) {{
                        checkboxes[0].checked = true;
                        checkboxes[0].dispatchEvent(new Event('change', {{ bubbles: true }}));
                        return true;
                    }}

                    return false;
                }}
            """)

    def handle_navigation(self):
        """Handle navigation buttons within the modal and return True if form is complete."""
        self.logger.info("\nHandling form navigation...")

        # Check for job safety reminder dialog first using selectors from config
        safety_dialog = self.page.query_selector(self.selectors["SAFETY_DIALOG"]["CONTAINER"])
        if safety_dialog:
            self.logger.info("Job safety reminder dialog detected during navigation!")
            continue_button = safety_dialog.query_selector(self.selectors["SAFETY_DIALOG"]["CONTINUE_BUTTON"])

            if continue_button:
                self.logger.info("Clicking 'Continue applying' button")
                continue_button.click()
                time.sleep(TIMING["MEDIUM_SLEEP"])  # Wait for transition using timing from config
                return False  # Return false to continue the application process
            else:
                # Fallback to any apply button in the dialog
                apply_button = safety_dialog.query_selector(self.selectors["SAFETY_DIALOG"]["APPLY_BUTTON"])
                if apply_button:
                    self.logger.info("Clicking apply button from safety dialog")
                    apply_button.click()
                    time.sleep(TIMING["MEDIUM_SLEEP"])  # Using timing from config
                    return False  # Continue the process

                self.logger.warning("Could not find button to proceed in safety dialog")
                # Try to close the dialog and retry
                self.close_dialog()
                return False  # Try to continue with the process

        # Define the modal selector
        modal = self.page.query_selector(self.selectors["MODAL"])

        if not modal:
            self.logger.info("Easy Apply modal not found!")
            return True
    
        # Rest of your existing code for handling normal navigation buttons
        # First, check if this is a resume selection screen that we need to handle
        resume_section = modal.query_selector(self.selectors["RESUME_SECTION"])
        upload_button = modal.query_selector(self.selectors["RESUME_UPLOAD_BUTTON"])
    
        if resume_section or upload_button:
            self.logger.info("Resume selection/upload screen detected during navigation")
            # Let the fill_in_details method handle this in the next iteration
    
        # Continue with normal button checks
        submit_button = modal.query_selector(self.selectors["NAVIGATION"]["SUBMIT"])
        review_button = modal.query_selector(self.selectors["NAVIGATION"]["REVIEW"])
        next_button = modal.query_selector(self.selectors["NAVIGATION"]["NEXT"])
    
        if submit_button:
            self.logger.info("Found Submit button - Application ready to submit!")
            submit_button.click()
            return True
        elif review_button:
            self.logger.info("Found Review button - Moving to review page")
            review_button.click()
        elif next_button:
            self.logger.info("Found Next button - Moving to next section")
            next_button.click()
        else:
            self.logger.info("No navigation buttons found, form might be incomplete")
            return True
    
        return False

    def detect_required_fields(self, modal):
        """
        Proactively detect and handle required fields before errors appear.
        """
        self.logger.info("Proactively checking for required fields...")

        # 1. Detect required checkbox fields
        self.logger.info("Looking for required checkbox fields...")
        required_checkboxes = modal.query_selector_all('fieldset:has(legend:has(.fb-dash-form-element__label-title--is-required)), fieldset:has(span[data-test-checkbox-form-required="true"])')

        self.logger.info(f"Found {len(required_checkboxes)} required checkbox fieldsets")

        for fieldset in required_checkboxes:
            try:
                # Get fieldset ID for logging
                fieldset_id = fieldset.get_attribute("id") or "unknown"
                self.logger.info(f"Processing required checkbox fieldset: {fieldset_id}")

                # Check if any checkboxes in this fieldset are already checked
                any_checked = fieldset.evaluate("""(el) => {
                    const checkboxes = el.querySelectorAll('input[type="checkbox"]');
                    for (const checkbox of checkboxes) {
                        if (checkbox.checked) return true;
                    }
                    return false;
                }""")

                if any_checked:
                    self.logger.info("At least one checkbox is already checked - skipping")
                    continue
                
                # Find all checkboxes in this fieldset
                checkboxes = fieldset.query_selector_all('input[type="checkbox"]')

                if checkboxes and len(checkboxes) > 0:
                    self.logger.info(f"Found {len(checkboxes)} checkboxes, checking the first one")

                    # Check the first checkbox
                    checkboxes[0].check()
                    self.logger.info("Checked first checkbox proactively")
            except Exception as e:
                self.logger.error(f"Error processing required checkbox fieldset: {e}")

        # 2. Detect required select fields
        self.logger.info("Looking for required select fields...")
        required_selects = modal.query_selector_all('select[required], select[aria-required="true"]')

        self.logger.info(f"Found {len(required_selects)} required select fields")

        for select in required_selects:
            try:
                # Skip if already has a value
                if self.check_existing_value(select):
                    self.logger.info("Select already has a value - skipping")
                    continue
                
                # Process the select field
                self.handle_select(select)
            except Exception as e:
                self.logger.error(f"Error processing required select: {e}")

        # 3. Detect required text inputs
        self.logger.info("Looking for required text inputs...")
        required_inputs = modal.query_selector_all('input[required], input[aria-required="true"], textarea[required], textarea[aria-required="true"]')

        self.logger.info(f"Found {len(required_inputs)} required text inputs")

        for input_field in required_inputs:
            try:
                # Skip if already has a value
                has_value = False
                try:
                    value = input_field.evaluate('el => el.value || ""')
                    has_value = value and value.strip()
                except Exception:
                    pass

                if has_value:
                    self.logger.info("Input already has a value - skipping")
                    continue
                
                # Determine field type
                field_type = self.determine_field_type(input_field)

                # Handle based on field type
                if field_type == "typeahead":
                    self.handle_typeahead(input_field)
                elif field_type == "date":
                    self.handle_date_input(input_field)
                else:
                    self.handle_text_input(input_field)
            except Exception as e:
                self.logger.error(f"Error processing required input: {e}")

        return True

    def get_label_for_checkbox(self, checkbox):
        """Helper method to find a label for a checkbox"""
        try:
            # Try finding by 'for' attribute
            checkbox_id = checkbox.get_attribute('id')
            if checkbox_id:
                label = self.page.query_selector(f'label[for="{checkbox_id}"]')
                if label:
                    return label

            # Try finding parent label
            parent_label = checkbox.query_selector('xpath=../label')
            if parent_label:
                return parent_label

            return None
        except Exception as e:
            self.logger.error(f"Error finding label for checkbox: {e}")
            return None