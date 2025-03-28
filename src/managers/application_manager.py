import time
import logging
import os
import uuid
from datetime import datetime

class ApplicationManager:
    """
    Manages the job application process
    """
    def __init__(self, browser_manager, job_search_manager, form_handler, resume_handler, selectors, job_filters, logger=None):
        self.browser_manager = browser_manager
        self.page = browser_manager.page
        self.job_search_manager = job_search_manager
        self.form_handler = form_handler
        self.resume_handler = resume_handler
        self.selectors = selectors
        self.job_filters = job_filters
        self.logger = logger or logging.getLogger(__name__)
        
        # Generate a unique session ID for this application run
        self.session_id = str(uuid.uuid4())[:8]
        
        # Statistics counters
        self.stats = {
            "processed": 0,
            "skipped": 0, 
            "already_applied": 0
        }
        
        self.start_time = datetime.now()
        self.logger.info(f"[SESSION:{self.session_id}] ApplicationManager initialized at {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"[SESSION:{self.session_id}] Using {len(self.job_filters)} job filters: {', '.join(self.job_filters[:5])}{'...' if len(self.job_filters) > 5 else ''}")

    def close_dialog(self):
        """Close any open dialog, handling both application form and confirmation dialogs"""
        try:
            self.logger.info("Attempting to close dialog...")

            # Try different close button selectors
            for selector in self.selectors["CLOSE_BUTTON"]:
                try:
                    # Check if the selector exists and is visible
                    if self.browser_manager.is_element_visible(selector, timeout=1000):
                        self.logger.info(f"Found close button with selector: {selector}")

                        # Wait for any loaders to disappear
                        loader = self.page.query_selector(".jobs-loader")
                        if loader and loader.is_visible():
                            self.logger.info("Waiting for loader to disappear...")
                            self.page.wait_for_selector(".jobs-loader", state="hidden", timeout=5000)

                        # Click the button
                        self.page.click(selector, timeout=5000)
                        self.logger.info("Successfully clicked close button")

                        # Verify dialog is closed
                        if not self.browser_manager.is_element_visible(".artdeco-modal", timeout=1000):
                            self.logger.info("Dialog closed successfully")
                            return True
                except Exception as e:
                    self.logger.error(f"Error with selector {selector}", e)
                    continue
                
            # If direct clicks fail, try alternative approaches
            self.logger.info("Direct close button clicks failed, trying alternatives...")

            # Try the "Not now" button in the confirmation dialog
            if self.browser_manager.is_element_visible(self.selectors["NAVIGATION"]["NOT_NOW"]):
                self.logger.info("Clicking 'Not now' button")
                self.page.click(self.selectors["NAVIGATION"]["NOT_NOW"])
                return True

            # Try Escape key as last resort
            self.logger.info("Trying Escape key")
            self.page.keyboard.press("Escape")

            # Final check if dialog closed
            if not self.browser_manager.is_element_visible(".artdeco-modal", timeout=2000):
                self.logger.info("Dialog closed with alternative method")
                return True

            self.logger.info("Failed to close dialog with all methods")
            return False

        except Exception as e:
            self.logger.error("Error closing dialog", e)
            return False

    def click_easy_apply(self):
        """
        Check if the job has an Easy Apply button and click it if present.
        Skip jobs that require external application.
        """
        try:
            self.logger.info("Checking if job has Easy Apply button...")

            if not self.job_search_manager.is_easy_apply_job():
                self.logger.info("This job requires external application - SKIPPING")
                return False

            self.logger.info("Job has Easy Apply button - proceeding with application")

            # Find and click the Easy Apply button
            easy_apply_button = self.page.query_selector(self.selectors["EASY_APPLY_BUTTON"])
            if easy_apply_button:
                # Ensure the page is stable before clicking
                time.sleep(1)
                self.logger.info("Easy Apply button found, clicking...")
                easy_apply_button.click()

                # Wait for any scrolling animations to complete
                time.sleep(2)

                # Check if ANY modal dialog appeared - either regular form or safety dialog
                any_modal_visible = self.browser_manager.is_element_visible("div[role='dialog']", timeout=5000)

                if any_modal_visible:
                    self.logger.info("A modal dialog appeared after clicking Easy Apply")
                    return True
                else:
                    # Try JavaScript as fallback
                    self.logger.info("No modal detected, trying JavaScript approach...")
                    clicked = self.page.evaluate("""
                        () => { 
                            const buttons = Array.from(document.querySelectorAll('button'));
                            const easyApplyButton = buttons.find(b => 
                                (b.textContent.includes('Easy Apply') || b.textContent.trim() === 'Apply') && 
                                !b.querySelector('svg[data-test-icon="link-external-small"]')
                            );
                            if (easyApplyButton) {
                                easyApplyButton.click();
                                return true;
                            }
                            return false;
                        }
                    """)

                    if clicked:
                        self.logger.info("Successfully clicked Easy Apply button via JavaScript")
                    else:
                        self.logger.info("JavaScript click failed to find an Easy Apply button")

                    # Wait and check for any modal again
                    time.sleep(3)
                    any_modal_visible = self.browser_manager.is_element_visible("div[role='dialog']", timeout=2000)

                    if any_modal_visible:
                        self.logger.info("Modal dialog appeared after JavaScript click")
                        return True
                    else:
                        self.logger.info("No modal dialog appeared after clicking")
                        return False
            else:
                self.logger.info("No Easy Apply button found")
                return False

        except Exception as e:
            self.logger.error("Error in click_easy_apply", e)
            return False

    def upload_custom_resume(self, resume_file_path):
        """
        Upload custom resume using generic selectors instead of brittle IDs
        """
        try:
            self.logger.info(f"Attempting to upload custom resume: {resume_file_path}")

            # Method 1: Find any input[type=file] with appropriate accept attribute
            file_inputs = self.page.query_selector_all('input[type="file"][accept*="pdf"]')
            if file_inputs:
                self.logger.info(f"Found {len(file_inputs)} file inputs that accept PDFs")
                for file_input in file_inputs:
                    try:
                        file_input.set_input_files(resume_file_path)
                        self.logger.info("Successfully uploaded resume using direct file input selector")
                        time.sleep(3)
                        return self.verify_resume_upload(resume_file_path)
                    except Exception as e:
                        self.logger.error("Error with this file input, trying next one", e)
                        continue

            # Method 2: Find by specific class and hidden attribute which is consistent
            hidden_inputs = self.page.query_selector_all('input.hidden[name="file"]')
            if hidden_inputs:
                self.logger.info(f"Found {len(hidden_inputs)} hidden file inputs")
                for hidden_input in hidden_inputs:
                    try:
                        hidden_input.set_input_files(resume_file_path)
                        self.logger.info("Successfully uploaded resume using hidden input selector")
                        time.sleep(3)
                        return self.verify_resume_upload(resume_file_path)
                    except Exception as e:
                        self.logger.error("Error with hidden input, trying next one", e)
                        continue

            # Method 3: Click the "Upload resume" label and try to handle it via keyboard events
            # (this is a fallback and may not work in all environments)
            upload_label = self.page.query_selector('label.jobs-document-upload__upload-button')
            if upload_label:
                self.logger.info("Found upload button label, trying alternative method")
                # Try to click the label to activate the file dialog
                upload_label.click()
                self.logger.info("Clicked upload button, but cannot programmatically set file via dialog")
                # This will only work in headed mode with manual intervention
                time.sleep(3)

            # Method 4: If upload fails, check if we have existing resumes to select
            self.logger.info("Checking for existing resumes to select")
            resume_cards = self.page.query_selector_all('.jobs-document-upload-redesign-card__container')
            if resume_cards and len(resume_cards) > 0:
                self.logger.info(f"Found {len(resume_cards)} existing resume cards")

                # Try to find a resume card that's not already selected
                for card in resume_cards:
                    # Check if this card is already selected
                    is_selected = 'jobs-document-upload-redesign-card__container--selected' in card.get_attribute('class')
                    if not is_selected:
                        # Find the radio input inside this card
                        radio = card.query_selector('input[type="radio"]')
                        if radio:
                            self.logger.info("Found unselected resume, selecting it")
                            radio.click()
                            time.sleep(1)
                            return True

                # If all cards were checked and none could be selected, just verify the current selection
                self.logger.info("All resume cards checked, using currently selected resume")
                return True

            self.logger.info("WARNING: Could not upload or select any resume")
            # Return true anyway to continue the application - some jobs allow proceeding without resume
            return True

        except Exception as e:
            self.logger.error("Error in resume upload process", e)
            # Continue anyway as some applications allow proceeding without resume
            return True

    def verify_resume_upload(self, resume_file_path):
        """Verify that a resume was successfully uploaded by checking for file name in HTML."""
        try:
            # Wait a bit for the upload to complete and UI to update
            time.sleep(2)
            
            import os
            filename = os.path.basename(resume_file_path)

            # Look for file name in the card titles
            file_names = self.page.query_selector_all('.jobs-document-upload-redesign-card__file-name')

            for name_element in file_names:
                try:
                    resume_name = name_element.inner_text().strip()
                    self.logger.info(f"Found resume: {resume_name}")

                    # Check for partial match of the filename (case insensitive)
                    filename_base = os.path.splitext(filename)[0].lower()
                    if filename_base in resume_name.lower():
                        self.logger.info(f"Found our uploaded resume: {resume_name}")

                        # Find the parent card
                        parent = name_element
                        card = None

                        # Try to traverse up to find the card container
                        for _ in range(5):  # Try up to 5 levels up
                            try:
                                parent = parent.query_selector(':scope ..')  # Get parent
                                if not parent:
                                    break

                                # Check if this is the card container
                                parent_class = parent.get_attribute("class") or ""
                                if "jobs-document-upload-redesign-card__container" in parent_class:
                                    card = parent
                                    break
                            except Exception:
                                break
                            
                        if card:
                            # Check if it's selected
                            try:
                                card_class = card.get_attribute("class") or ""
                                is_selected = "jobs-document-upload-redesign-card__container--selected" in card_class

                                # If not selected, find and click the radio button
                                if not is_selected:
                                    radio = card.query_selector('input[type="radio"]')
                                    if radio:
                                        self.logger.info("Selecting our uploaded resume")
                                        radio.click()
                                        time.sleep(1)
                            except Exception as selection_error:
                                self.logger.error(f"Error checking selection status: {selection_error}")

                        return True
                except Exception as element_error:
                    self.logger.error(f"Error processing resume name element: {element_error}")

            # If we didn't find our uploaded resume but there's at least one resume
            if len(file_names) > 0:
                self.logger.info("Didn't find our uploaded resume, but found other resumes")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error verifying resume upload: {e}")
            return False

    def select_any_resume(self):
        """Select any available resume if upload fails."""
        try:
            self.logger.info("Trying to select any available resume")

            # Find all resume cards
            resume_cards = self.page.query_selector_all('.jobs-document-upload-redesign-card__container')

            if not resume_cards or len(resume_cards) == 0:
                self.logger.info("No resume cards found")
                return False

            self.logger.info(f"Found {len(resume_cards)} resume cards")

            # Find the first card that's not selected
            for card in resume_cards:
                is_selected = 'jobs-document-upload-redesign-card__container--selected' in card.get_attribute('class')

                # If it's already selected, we're good
                if is_selected:
                    name_element = card.query_selector('.jobs-document-upload-redesign-card__file-name')
                    if name_element:
                        resume_name = name_element.inner_text().strip()
                        self.logger.info(f"Resume already selected: {resume_name}")
                    return True

                # Otherwise, try to select it
                radio = card.query_selector('input[type="radio"]')
                if radio:
                    self.logger.info("Selecting available resume")
                    radio.click()
                    time.sleep(1)
                    return True

            self.logger.info("Could not select any resume")
            return False
        
        except Exception as e:
            self.logger.error("Error selecting resume", e)
            return False

    def fill_in_details(self):
        """Handle form filling for LinkedIn Easy Apply with resume already generated."""
        try:
            # Click Easy Apply button if we haven't already
            if not self.browser_manager.is_element_visible(self.selectors["MODAL"]):
                self.click_easy_apply()

            # Process the application form
            while True:
                time.sleep(2)  # Wait for form to load

                # Check if this is an education section
                education_section = self.page.query_selector("h3.t-16.mb2:has-text('Education')")
                
                # Check for resume upload/selection section at each step
                resume_section_visible = (
                    self.browser_manager.is_element_visible(self.selectors["RESUME_SECTION"]) or
                    self.browser_manager.is_element_visible(self.selectors["RESUME_UPLOAD_BUTTON"])
                )

                if resume_section_visible:
                    self.logger.info("Detected resume section, handling resume upload/selection")
                    custom_resume_path = None

                    # Check if we have a custom resume for this job
                    if self.resume_handler.current_job_id:
                        custom_resume_path = os.path.join(
                            self.resume_handler.resume_dir, 
                            f"{self.resume_handler.current_job_id}.pdf"
                        )

                    if custom_resume_path and os.path.exists(custom_resume_path):
                        self.logger.info(f"Using custom resume: {custom_resume_path}")
                        self.upload_custom_resume(custom_resume_path)
                    else:
                        self.logger.info("No custom resume available, using default")
                        # Use a default resume path here
                        default_resume_path = os.getenv('DEFAULT_RESUME_PATH', "default_resume.pdf")  # Update this to your default resume path
                        self.upload_custom_resume(default_resume_path)

                if education_section:
                    # Handle the education section with our specialized function
                    self.form_handler.handle_education_date_fields()

                    # Skip general form handling for this step
                    self.logger.info("Education section detected and handled, skipping general form handling")
                else:
                    # Fill all form fields with the general handler
                    self.form_handler.handle_form_fields()

                # Handle navigation
                if self.form_handler.handle_navigation():
                    break

            return True

        except Exception as e:
            self.logger.error("Error in fill_in_details", e)
            return False

    def is_already_applied(self):
        """
        Check if the current job has already been applied to by looking for
        'Applied' indicators on the job details page.
        Uses pure Python/Playwright methods without JavaScript.
        
        Returns:
            bool: True if the job has already been applied to, False otherwise
        """
        try:
            self.logger.info("Checking if job has already been applied to...")
            
            # Method 1: Look for the success feedback element which appears when a job has been applied to
            applied_indicator = self.page.query_selector(".artdeco-inline-feedback--success")
            if applied_indicator:
                try:
                    applied_text = applied_indicator.inner_text().strip()
                    self.logger.info(f"Found applied indicator: '{applied_text}'")
                    return True
                except Exception as e:
                    self.logger.info("Found applied indicator but couldn't extract text")
                    return True
            
            # Method 2: Look for the "See application" link
            application_link = self.page.query_selector("#jobs-apply-see-application-link")
            if application_link:
                self.logger.info("Found 'See application' link - job has already been applied to")
                return True
            
            # Method 3: Check for common elements that contain "Applied" text
            # Use specific selectors instead of text search
            applied_selectors = [
                ".jobs-s-apply__application-link", # "See application" link (broader selector)
                ".artdeco-inline-feedback__message", # Success message
                ".jobs-details__main-content .artdeco-inline-feedback" # Another common container
            ]
            
            for selector in applied_selectors:
                elements = self.page.query_selector_all(selector)
                for element in elements:
                    try:
                        if element.is_visible():
                            text = element.inner_text().strip()
                            if "applied" in text.lower():
                                self.logger.info(f"Found element containing applied text: '{text}'")
                                return True
                    except Exception:
                        continue
                    
            # Method 4: Try to find elements with specific text pattern
            # This works by looking for specific HTML patterns rather than using CSS text selector
            potential_containers = [
                ".jobs-details-top-card__container",
                ".jobs-unified-top-card",
                ".jobs-s-apply",
                ".jobs-company__box" 
            ]
            
            for container in potential_containers:
                elements = self.page.query_selector_all(f"{container} div, {container} span, {container} p")
                for element in elements:
                    try:
                        if element.is_visible():
                            text = element.inner_text().strip()
                            # Check for variations of "Applied" message
                            if ("applied" in text.lower() and 
                                not "apply now" in text.lower() and 
                                not "easy apply" in text.lower()):
                                self.logger.info(f"Found text indicating already applied: '{text}'")
                                return True
                    except Exception:
                        continue
                        
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking if job already applied: {e}")
            # In case of error, assume not applied to avoid skipping potentially new jobs
            return False

    def process_job_card(self, card, ember_id, ember_num, sorted_cards):
        """Process an individual job card"""
        card_start_time = datetime.now()
        job_trace_id = str(uuid.uuid4())[:6]  # Generate unique trace ID for this job
        self.logger.info(f"[JOB:{job_trace_id}] Starting to process job card #{ember_id} at position {ember_num}")
        
        try:
            # Verify card is still connected to DOM
            try:
                is_connected = card.evaluate('node => !!node.isConnected')
                if not is_connected:
                    self.logger.info(f"[JOB:{job_trace_id}] Card #{ember_id} is no longer connected to DOM, skipping")
                    self.job_search_manager.processed_ids.add(ember_id)
                    return False
            except Exception as e:
                self.logger.error(f"[JOB:{job_trace_id}] Error checking if card is connected: {e}")
                self.job_search_manager.processed_ids.add(ember_id)
                return False

            # Scroll to job card
            self.logger.debug(f"[JOB:{job_trace_id}] Scrolling to job card #{ember_id}")
            self.job_search_manager.scroll_to_job_card(card, ember_id, ember_num, sorted_cards)
            time.sleep(0.5)  # Wait for scroll to complete

            # Get fresh reference by ember ID - with more verification
            try:
                self.logger.debug(f"[JOB:{job_trace_id}] Getting fresh reference to card #{ember_id}")
                fresh_card = self.page.query_selector(f"#{ember_id}")
                if not fresh_card:
                    self.logger.info(f"[JOB:{job_trace_id}] Card #{ember_id} no longer in DOM after scroll, skipping")
                    self.job_search_manager.processed_ids.add(ember_id)
                    return False

                # Make sure it's visible
                is_visible = fresh_card.is_visible()
                self.logger.debug(f"[JOB:{job_trace_id}] Card visibility check: {is_visible}")
                if not is_visible:
                    self.logger.info(f"[JOB:{job_trace_id}] Card #{ember_id} is not visible, skipping")
                    self.job_search_manager.processed_ids.add(ember_id)
                    return False
            except Exception as e:
                self.logger.error(f"[JOB:{job_trace_id}] Error getting fresh card reference: {e}")
                self.job_search_manager.processed_ids.add(ember_id)
                return False
            
            # Click on the job card to view details
            self.logger.debug(f"[JOB:{job_trace_id}] Attempting to click job card #{ember_id}")
            if not self._click_job_card(fresh_card, ember_id, job_trace_id):
                self.logger.info(f"[JOB:{job_trace_id}] Failed to click job card #{ember_id}, skipping")
                self.job_search_manager.processed_ids.add(ember_id)
                return False

            # Wait for job details page to load
            self.logger.debug(f"[JOB:{job_trace_id}] Waiting for job details to load")
            if not self._wait_for_job_details(job_trace_id):
                self.logger.info(f"[JOB:{job_trace_id}] Job details did not load properly, skipping")
                self.job_search_manager.processed_ids.add(ember_id)
                return False

            # Check if job has already been applied to
            self.logger.debug(f"[JOB:{job_trace_id}] Checking if already applied")
            if self.is_already_applied():
                self.logger.info(f"[JOB:{job_trace_id}] Job #{ember_id} has already been applied to - SKIPPING")
                self.job_search_manager.processed_ids.add(ember_id)
                self.stats["already_applied"] += 1
                return False

            time.sleep(2)  # Give extra time for content to settle

            # Extract information from the job details page
            self.logger.debug(f"[JOB:{job_trace_id}] Extracting job details")
            job_title, company_name = self.job_search_manager.extract_job_details()

            # Filter out jobs based on title
            if any([x in job_title.lower() for x in self.job_filters]):
                matched_filters = [x for x in self.job_filters if x in job_title.lower()]
                self.logger.info(f"[JOB:{job_trace_id}] Filtered out job: {job_title} (matched filters: {', '.join(matched_filters)})")
                self.job_search_manager.processed_ids.add(ember_id)
                return False

            self.logger.info(f"[JOB:{job_trace_id}] JOB TITLE: {job_title}")
            self.logger.info(f"[JOB:{job_trace_id}] COMPANY NAME: {company_name}")

            # Get job description - but don't generate resume yet
            self.logger.debug(f"[JOB:{job_trace_id}] Getting job description")
            job_description = self.job_search_manager.get_job_description()
            if job_description:
                desc_length = len(job_description)
                self.logger.debug(f"[JOB:{job_trace_id}] Job description retrieved: {desc_length} chars")
                self.form_handler.response_manager.current_job_description = job_description
                self.resume_handler.current_job_description = job_description
            else:
                self.logger.warning(f"[JOB:{job_trace_id}] No job description found!")

            # Check if this is an Easy Apply job and click the button if it is
            self.logger.debug(f"[JOB:{job_trace_id}] Attempting to click Easy Apply button")
            if self.click_easy_apply():
                self.logger.info(f"[JOB:{job_trace_id}] Successfully clicked Easy Apply button")
                
                # Only generate resume after clicking Easy Apply button
                if job_description and job_title and company_name:
                    self.logger.info(f"[JOB:{job_trace_id}] Generating custom resume for {job_title} at {company_name}")
                    resume_generation_start = datetime.now()
                    resume_id = self.resume_handler.generate_custom_resume(
                        job_title, company_name, job_description
                    )
                    resume_generation_time = (datetime.now() - resume_generation_start).total_seconds()
                    self.logger.info(f"[JOB:{job_trace_id}] Generated custom resume ID: {resume_id} in {resume_generation_time:.2f} seconds")
                else:
                    self.logger.warning(f"[JOB:{job_trace_id}] Missing info for resume generation: title={bool(job_title)}, company={bool(company_name)}, description={bool(job_description)}")

                # Handle application process with retry
                self.logger.debug(f"[JOB:{job_trace_id}] Starting application process with retry")
                application_start = datetime.now()
                success = self._apply_with_retry(job_title, job_trace_id)
                application_time = (datetime.now() - application_start).total_seconds()

                if success:
                    self.stats["processed"] += 1
                    self.logger.info(f"[JOB:{job_trace_id}] Successfully applied to job: {job_title} in {application_time:.2f} seconds")
                else:
                    self.logger.warning(f"[JOB:{job_trace_id}] Failed to apply to job: {job_title} after retries")
            else:
                self.logger.info(f"[JOB:{job_trace_id}] Skipping job '{job_title}' - not an Easy Apply job")
                self.stats["skipped"] += 1

            # Clean up after application
            self.logger.debug(f"[JOB:{job_trace_id}] Cleaning up after application")
            self.close_dialog()
            
            # Reset job-specific data
            self.form_handler.response_manager.current_job_description = None
            self.resume_handler.current_job_description = None
            self.resume_handler.current_job_id = None

            # Mark as processed regardless of success
            self.job_search_manager.processed_ids.add(ember_id)
            
            # Calculate and log total processing time
            processing_time = (datetime.now() - card_start_time).total_seconds()
            self.logger.info(f"[JOB:{job_trace_id}] Completed processing job #{ember_id} in {processing_time:.2f} seconds")
            
            return True

        except Exception as e:
            self.logger.error(f"[JOB:{job_trace_id}] Error processing job {ember_id}: {str(e)}", exc_info=True)
            
            # Calculate and log failure time
            failure_time = (datetime.now() - card_start_time).total_seconds()
            self.logger.error(f"[JOB:{job_trace_id}] Failed processing job #{ember_id} after {failure_time:.2f} seconds")
            
            try:
                self.close_dialog()
            except Exception as dialog_error:
                self.logger.error(f"[JOB:{job_trace_id}] Error closing dialog after failure: {str(dialog_error)}")
                
            self.job_search_manager.processed_ids.add(ember_id)
            return False

    def _click_job_card(self, card, ember_id, job_trace_id):
        """Try to click on a job card with multiple fallbacks"""
        self.logger.info(f"[JOB:{job_trace_id}] Attempting to click job card #{ember_id}")
        click_successful = False
        click_start_time = datetime.now()

        try:
            # Method 1: Try to find and click on any link in the card
            self.logger.debug(f"[JOB:{job_trace_id}] Method 1: Trying to click link in card")
            link = card.query_selector("a")
            if link:
                link_visible = link.is_visible()
                self.logger.debug(f"[JOB:{job_trace_id}] Found link in card, visible: {link_visible}")
                if link_visible:
                    link.click()
                    click_successful = True
                    self.logger.info(f"[JOB:{job_trace_id}] Method 1 successful: Clicked link in card #{ember_id}")
                    return True
                else:
                    self.logger.debug(f"[JOB:{job_trace_id}] Link found but not visible")
            else:
                self.logger.debug(f"[JOB:{job_trace_id}] No link found in card")
        except Exception as e:
            self.logger.error(f"[JOB:{job_trace_id}] Method 1 failed: Link click failed: {str(e)}")

        try:
            # Method 2: Click the card itself
            if not click_successful:
                self.logger.debug(f"[JOB:{job_trace_id}] Method 2: Trying to click card directly")
                card.click()
                click_successful = True
                self.logger.info(f"[JOB:{job_trace_id}] Method 2 successful: Clicked card #{ember_id} directly")
                return True
        except Exception as e:
            self.logger.error(f"[JOB:{job_trace_id}] Method 2 failed: Direct card click failed: {str(e)}")

        # Method 3: JavaScript fallback
        if not click_successful:
            try:
                self.logger.debug(f"[JOB:{job_trace_id}] Method 3: Trying JavaScript fallback click")
                clicked = self.page.evaluate(f"""
                    (() => {{
                        const card = document.getElementById('{ember_id}');
                        if (card) {{
                            const link = card.querySelector('a');
                            if (link) {{
                                link.click();
                                return true;
                            }}
                            card.click();
                            return true;
                        }}
                        return false;
                    }})()
                """)

                if clicked:
                    self.logger.info(f"[JOB:{job_trace_id}] Method 3 successful: JavaScript click worked for card #{ember_id}")
                    click_successful = True
                    return True
                else:
                    self.logger.warning(f"[JOB:{job_trace_id}] Method 3 failed: JavaScript click returned false for card #{ember_id}")
            except Exception as e:
                self.logger.error(f"[JOB:{job_trace_id}] Method 3 failed: JavaScript click error: {str(e)}")

        # Log the total time spent trying to click
        click_duration = (datetime.now() - click_start_time).total_seconds()
        if click_successful:
            self.logger.info(f"[JOB:{job_trace_id}] Successfully clicked card #{ember_id} in {click_duration:.2f} seconds")
        else:
            self.logger.error(f"[JOB:{job_trace_id}] Failed to click card #{ember_id} after {click_duration:.2f} seconds and 3 attempts")
            
        return click_successful

    def _wait_for_job_details(self, job_trace_id):
        """Wait for job details page to load"""
        self.logger.info(f"[JOB:{job_trace_id}] Waiting for job details page to load...")
        start_wait_time = datetime.now()
        try:
            # Try each selector individually with timeout
            found_selector = False
            
            # First try the primary selector
            primary_selector = self.selectors["JOB_DETAILS_TITLE"]
            self.logger.debug(f"[JOB:{job_trace_id}] Trying primary selector: {primary_selector}")
            try:
                self.page.wait_for_selector(primary_selector, timeout=10000)
                wait_time = (datetime.now() - start_wait_time).total_seconds()
                self.logger.info(f"[JOB:{job_trace_id}] Job details page loaded (primary selector found) in {wait_time:.2f} seconds")
                found_selector = True
            except Exception as primary_error:
                self.logger.info(f"[JOB:{job_trace_id}] Primary job title selector not found after {(datetime.now() - start_wait_time).total_seconds():.2f} seconds: {str(primary_error)}")

            # If primary not found, try the fallback selector
            if not found_selector:
                fallback_selector = self.selectors["JOB_DETAILS_TITLE_ALT"]
                self.logger.debug(f"[JOB:{job_trace_id}] Trying fallback selector: {fallback_selector}")
                try:
                    self.page.wait_for_selector(fallback_selector, timeout=5000)
                    wait_time = (datetime.now() - start_wait_time).total_seconds()
                    self.logger.info(f"[JOB:{job_trace_id}] Job details page loaded (fallback selector found) in {wait_time:.2f} seconds")
                    found_selector = True
                except Exception as fallback_error:
                    self.logger.info(f"[JOB:{job_trace_id}] Fallback job title selector also not found: {str(fallback_error)}")

            # If neither selector was found, raise an exception
            if not found_selector:
                total_wait_time = (datetime.now() - start_wait_time).total_seconds()
                self.logger.error(f"[JOB:{job_trace_id}] Could not find any job details selectors after {total_wait_time:.2f} seconds")
                raise Exception("Could not find any job details selectors")

            # Do an additional check for "Page not found" indicators
            try:
                not_found_indicator = self.page.query_selector("div.artdeco-empty-state__message:has-text('Page not found')")
                if not_found_indicator and not_found_indicator.is_visible():
                    self.logger.error(f"[JOB:{job_trace_id}] 'Page not found' message detected on job details page")
                    return False
            except Exception:
                pass  # Ignore errors in this additional check
                
            # Do a check for server error indicators
            try:
                server_error = self.page.query_selector("div.artdeco-empty-state__message:has-text('server error')")
                if server_error and server_error.is_visible():
                    self.logger.error(f"[JOB:{job_trace_id}] Server error detected on job details page")
                    return False
            except Exception:
                pass  # Ignore errors in this additional check

            return True

        except Exception as e:
            total_wait_time = (datetime.now() - start_wait_time).total_seconds()
            self.logger.error(f"[JOB:{job_trace_id}] Error waiting for job details after {total_wait_time:.2f} seconds: {str(e)}")
            return False

    def process_job_cards_batch(self, sorted_cards):
        """Process a batch of job cards"""
        batch_trace_id = str(uuid.uuid4())[:6]  # Generate unique trace ID for this batch
        batch_start_time = datetime.now()
        self.logger.info(f"[BATCH:{batch_trace_id}] Starting to process batch of {len(sorted_cards)} job cards")
        
        # Track if we processed any new cards in this batch
        new_cards_processed = False
        cards_processed = 0
        cards_skipped = 0

        for card, ember_num, ember_id in sorted_cards:
            # Skip already processed cards
            if ember_id in self.job_search_manager.processed_ids:
                cards_skipped += 1
                continue
            
            card_processed = self.process_job_card(card, ember_id, ember_num, sorted_cards)
            if card_processed:
                new_cards_processed = True
                cards_processed += 1
        
        batch_duration = (datetime.now() - batch_start_time).total_seconds()
        self.logger.info(f"[BATCH:{batch_trace_id}] Batch processing completed in {batch_duration:.2f} seconds")
        self.logger.info(f"[BATCH:{batch_trace_id}] Cards processed: {cards_processed}, cards skipped: {cards_skipped}")
                
        return new_cards_processed

    def process_page(self, page_number):
        """Process all jobs on a single page"""
        page_trace_id = str(uuid.uuid4())[:6]  # Generate unique trace ID for this page
        page_start_time = datetime.now()
        self.logger.info(f"[PAGE:{page_trace_id}] ===== Starting to process page {page_number} =====")
        
        page_stats = {"processed": 0, "skipped": 0, "already_applied": 0}
        
        # Get starting stats to calculate page stats later
        start_processed = self.stats["processed"]
        start_skipped = self.stats["skipped"]
        start_already_applied = self.stats["already_applied"]
        
        batch_count = 0
        total_cards_found = 0

        while True:
            batch_count += 1
            self.logger.info(f"[PAGE:{page_trace_id}] Processing batch {batch_count} on page {page_number}")
            
            # Get fresh job cards sorted by ember ID
            sorted_cards = self.job_search_manager.get_job_cards()
            total_cards_found = len(sorted_cards)

            if not sorted_cards:
                self.logger.info(f"[PAGE:{page_trace_id}] No job cards found in batch {batch_count}")
                break
            
            # Add a stability delay
            self.logger.debug(f"[PAGE:{page_trace_id}] Found {len(sorted_cards)} job cards, stabilizing before processing...")
            time.sleep(2)  # Give LinkedIn DOM time to stabilize

            # Process the batch of cards
            self.logger.debug(f"[PAGE:{page_trace_id}] Processing batch {batch_count} with {len(sorted_cards)} cards")
            new_cards_processed = self.process_job_cards_batch(sorted_cards)
            self.logger.debug(f"[PAGE:{page_trace_id}] Batch {batch_count} processing result: new_cards_processed={new_cards_processed}")

            # If no new cards were processed, try to load more or exit
            if not new_cards_processed:
                self.logger.info(f"[PAGE:{page_trace_id}] No new cards processed in batch {batch_count}, attempting to load more...")
                if not self.job_search_manager.load_more_cards(sorted_cards):
                    self.logger.info(f"[PAGE:{page_trace_id}] No more cards could be loaded, exiting page processing")
                    break
                self.logger.info(f"[PAGE:{page_trace_id}] Successfully loaded more cards, continuing to next batch")

        # Calculate page stats
        page_stats["processed"] = self.stats["processed"] - start_processed
        page_stats["skipped"] = self.stats["skipped"] - start_skipped
        page_stats["already_applied"] = self.stats["already_applied"] - start_already_applied
        
        page_duration = (datetime.now() - page_start_time).total_seconds()
        
        self.logger.info(f"[PAGE:{page_trace_id}] ===== Page {page_number} processing summary =====")
        self.logger.info(f"[PAGE:{page_trace_id}] Processed {page_stats['processed']} jobs on page {page_number}")
        self.logger.info(f"[PAGE:{page_trace_id}] Skipped {page_stats['skipped']} jobs on page {page_number} (not Easy Apply)")
        self.logger.info(f"[PAGE:{page_trace_id}] Skipped {page_stats['already_applied']} jobs on page {page_number} (already applied)")
        self.logger.info(f"[PAGE:{page_trace_id}] Total job cards found: {total_cards_found}")
        self.logger.info(f"[PAGE:{page_trace_id}] Total batches processed: {batch_count}")
        self.logger.info(f"[PAGE:{page_trace_id}] Total page processing time: {page_duration:.2f} seconds")
        self.logger.info(f"[PAGE:{page_trace_id}] Average time per job: {page_duration / max(page_stats['processed'] + page_stats['skipped'] + page_stats['already_applied'], 1):.2f} seconds")
        
        return page_stats

    def navigate_pages(self):
        """Navigate through multiple pages of job listings"""
        session_trace_id = str(uuid.uuid4())[:6]  # Generate unique trace ID for this session
        session_start_time = datetime.now()
        self.logger.info(f"[SESSION:{session_trace_id}] Starting multi-page job application session")
        
        current_page = 1
        total_pages_processed = 0
        
        while True:
            # Process the current page
            self.logger.info(f"[SESSION:{session_trace_id}] Starting to process page {current_page}")
            page_start_time = datetime.now()
            
            page_stats = self.process_page(current_page)
            
            page_duration = (datetime.now() - page_start_time).total_seconds()
            self.logger.info(f"[SESSION:{session_trace_id}] Completed page {current_page} in {page_duration:.2f} seconds")
            total_pages_processed += 1
            
            # Navigate to next page if available
            self.logger.info(f"[SESSION:{session_trace_id}] Checking for next page after page {current_page}")
            if self.job_search_manager.navigate_to_next_page():
                current_page += 1
                self.logger.info(f"[SESSION:{session_trace_id}] Successfully navigated to page {current_page}")
            else:
                self.logger.info(f"[SESSION:{session_trace_id}] No more pages available or reached the last page")
                break
                
        # Log overall statistics
        session_duration = (datetime.now() - session_start_time).total_seconds()
        minutes = int(session_duration // 60)
        seconds = int(session_duration % 60)
        
        self.logger.info(f"[SESSION:{session_trace_id}] ===== Session Summary =====")
        self.logger.info(f"[SESSION:{session_trace_id}] Session completed in {minutes} minutes, {seconds} seconds")
        self.logger.info(f"[SESSION:{session_trace_id}] Total pages processed: {total_pages_processed}")
        self.logger.info(f"[SESSION:{session_trace_id}] Total jobs processed: {self.stats['processed']}")
        self.logger.info(f"[SESSION:{session_trace_id}] Total jobs skipped (not Easy Apply): {self.stats['skipped']}")
        self.logger.info(f"[SESSION:{session_trace_id}] Total jobs skipped (already applied): {self.stats['already_applied']}")
        
        # Calculate rates
        if self.stats['processed'] > 0:
            avg_time_per_application = session_duration / self.stats['processed']
            self.logger.info(f"[SESSION:{session_trace_id}] Average time per successful application: {avg_time_per_application:.2f} seconds")
            applications_per_hour = (3600 / avg_time_per_application) if avg_time_per_application > 0 else 0
            self.logger.info(f"[SESSION:{session_trace_id}] Estimated applications per hour: {applications_per_hour:.2f}")
        
        total_jobs_encountered = self.stats['processed'] + self.stats['skipped'] + self.stats['already_applied']
        if total_jobs_encountered > 0:
            success_rate = (self.stats['processed'] / total_jobs_encountered) * 100
            self.logger.info(f"[SESSION:{session_trace_id}] Application success rate: {success_rate:.2f}%")
        
        self.logger.info(f"[SESSION:{session_trace_id}] ===== End of Session =====")

    def apply(self):
        """Apply to all eligible jobs on the page"""
        try:
            # Generate a unique run ID for this application run
            run_id = str(uuid.uuid4())[:8]
            self.logger.info(f"[RUN:{run_id}] Starting new application run")
            start_time = datetime.now()
            
            # Reset statistics
            self.stats = {
                "processed": 0,
                "skipped": 0, 
                "already_applied": 0
            }
            
            # Navigate through pages and process jobs
            self.navigate_pages()
            
            # Log run completion
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            self.logger.info(f"[RUN:{run_id}] Application run completed after {duration:.2f} seconds")
            self.logger.info(f"[RUN:{run_id}] Successfully applied to {self.stats['processed']} jobs")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Critical error in apply method: {str(e)}", exc_info=True)
            return False


    def _apply_with_retry(self, job_title, job_trace_id, max_attempts=2):
        """Apply to a job with retry logic"""
        for attempt in range(max_attempts):
            try:
                self.logger.info(f"[JOB:{job_trace_id}] Application attempt {attempt+1}/{max_attempts} for job: {job_title}")
                attempt_start_time = datetime.now()
                
                if self.fill_in_details():
                    attempt_duration = (datetime.now() - attempt_start_time).total_seconds()
                    self.logger.info(f"[JOB:{job_trace_id}] Successfully applied to job: {job_title} on attempt {attempt+1} in {attempt_duration:.2f} seconds")
                    time.sleep(2)
                    return True
                else:
                    attempt_duration = (datetime.now() - attempt_start_time).total_seconds()
                    self.logger.warning(f"[JOB:{job_trace_id}] Application attempt {attempt+1} returned False after {attempt_duration:.2f} seconds")
            except Exception as e:
                attempt_duration = (datetime.now() - attempt_start_time).total_seconds()
                self.logger.error(f"[JOB:{job_trace_id}] Application attempt {attempt+1} failed after {attempt_duration:.2f} seconds: {str(e)}", exc_info=True)
                
                try:
                    self.logger.debug(f"[JOB:{job_trace_id}] Attempting to close dialog after failed attempt {attempt+1}")
                    self.close_dialog()
                except Exception as cleanup_error:
                    self.logger.error(f"[JOB:{job_trace_id}] Error cleaning up after failed attempt: {str(cleanup_error)}")
                    
                time.sleep(2)
        
        self.logger.error(f"[JOB:{job_trace_id}] Failed to apply to job: {job_title} after {max_attempts} attempts")
        return False