import logging
import urllib.parse
import time

# Import from config
from src.config.config import TIME_FILTER_MAPPING, WORK_TYPE_MAPPING, LINKEDIN_PARAMS, TIMING

class JobSearchManager:
    """
    Manages job search, filtering, and finding job listings
    """
    def __init__(self, browser_manager, config, selectors, logger=None, time_filter="day"):
        self.browser_manager = browser_manager
        self.page = browser_manager.page
        
        # Extract config
        self.url = config["url"]
        self.jobs_endpoint = config["jobs"]
        self.search_keyword_selector = config["search_keyword_selector"]
        self.search_location_selector = config["search_location_selector"]
        self.time_filter_button = config["time_filter_button"]
        self.time_filter_enter = config["time_filter_enter"]
        self.easy_apply_button = config["easy_apply_button"]
        
        # Time filter - now accepts parameter
        self.time_filter = time_filter
        
        # Store selectors
        self.selectors = selectors
        
        self.logger = logger or logging.getLogger(__name__)
        
        # Track processed job IDs
        self.processed_ids = set()
        
        self.logger.info(f"JobSearchManager initialized with time filter: {self.time_filter}")
        self.logger.debug(f"URL: {self.url}, Jobs endpoint: {self.jobs_endpoint}")

    def search_jobs(self, keywords: str, location: str, remote_only=True, work_types=None):
        """
        Search for jobs using direct URL parameters with improved page load handling

        Args:
            keywords: Search keywords/query
            location: Location to search in
            remote_only: Whether to only show remote jobs (default: True)
            work_types: List of work types to filter (default: None)
        """
        try:
            self.logger.info("Using URL parameter approach for job search")
            self.logger.info(f"Search parameters: keywords={keywords[:50]}..., location={location}, remote_only={remote_only}")

            # Encode search parameters for URL
            encoded_keywords = urllib.parse.quote(keywords)
            encoded_location = urllib.parse.quote(location)
            self.logger.debug(f"Encoded keywords length: {len(encoded_keywords)}")

            # Build the base search URL
            base_url = "https://www.linkedin.com/jobs/search/"

            # Add URL parameters based on filters
            params = []

            # Add keywords
            params.append(f"keywords={encoded_keywords}")

            # Always add location if provided
            if location and location.lower() != "remote":
                params.append(f"location={encoded_location}")
                self.logger.debug(f"Added location parameter: {location}")

            # Add Easy Apply filter
            params.append(LINKEDIN_PARAMS["EASY_APPLY"])
            self.logger.debug("Added Easy Apply filter")

            # Add time filter based on setting - using TIME_FILTER_MAPPING from config
            if isinstance(self.time_filter, str) and self.time_filter.startswith('r') and self.time_filter[1:].isdigit():
                time_param = self.time_filter  # Already in correct format
            else:
                time_param = TIME_FILTER_MAPPING.get(self.time_filter, "r86400")
                
            if time_param:
                params.append(f"f_TPR={time_param}")
                self.logger.debug(f"Added time filter parameter: {self.time_filter} ({time_param})")

            # Add work type filters
            if work_types is None:
                work_types = []
                if remote_only or location.lower() == "remote":
                    work_types.append(WORK_TYPE_MAPPING["remote"])  # Use config value for remote
                else:
                    # Include multiple work types if not strictly remote
                    work_types.extend([WORK_TYPE_MAPPING["remote"], WORK_TYPE_MAPPING["onsite"], WORK_TYPE_MAPPING["hybrid"]])  # Use config values

            if work_types:
                params.append(f"f_WT={urllib.parse.quote(LINKEDIN_PARAMS['URL_COMMA'].join(work_types))}")
                self.logger.debug(f"Added work type filter: {work_types}")

            # Add refresh and origin parameters
            params.append(LINKEDIN_PARAMS["REFRESH"])
            params.append(LINKEDIN_PARAMS["ORIGIN"])

            # Combine all parameters into final URL
            search_url = f"{base_url}?{'&'.join(params)}"

            self.logger.info(f"Navigating to search URL: {search_url[:100]}...")

            # Navigate to the constructed URL
            self.browser_manager.navigate(search_url)

            # Improved page load waiting strategy
            self.logger.debug("Waiting for DOM content to load")
            self.page.wait_for_load_state("domcontentloaded")
            
            # Add a small delay for page stability
            self.logger.debug("Adding a small delay for page stability...")
            time.sleep(TIMING["LONG_SLEEP"])

            self.logger.info("Search completed and page appears to be loaded")

            # Verify job cards loaded
            job_cards = self.page.query_selector_all(self.selectors["JOB_CARDS"])
            self.logger.info(f"Found {len(job_cards)} job cards on initial page")

            # Log search results header if available
            try:
                job_count_element = self.page.query_selector(".jobs-search-results-list__title-heading")
                if job_count_element:
                    job_count_text = job_count_element.inner_text()
                    self.logger.info(f"Search results header: {job_count_text}")
            except Exception as e:
                self.logger.debug(f"Could not extract job count: {e}")

        except Exception as e:
            self.logger.error(f"Error during URL-based job search: {e}", exc_info=True)
            # Continue instead of raising to allow the application to proceed with any loaded jobs


    def apply_filters(self):
        """
        This method is now a placeholder since filters are applied directly via URL
        It's kept for compatibility with the existing code structure
        """
        self.logger.info("Filters already applied via URL parameters")
        # No action needed as filters were applied in the URL
        return True

    def find_top_picks_and_easy_apply_jobs(self, remote_only=True, work_types=None):
        """
        Navigate to LinkedIn jobs page, find top picks, and apply filters

        Args:
            remote_only: Whether to filter for remote jobs (default: True)
            work_types: List of work types to filter for (valid values: 'remote', 'onsite', 'hybrid')
                        If None and remote_only=True, defaults to just remote
                        If None and remote_only=False, includes all work types
        """
        try:
            # Navigate to jobs page
            jobs_url = self.url + self.jobs_endpoint
            self.logger.info(f"Navigating to jobs page: {jobs_url}")

            # Build parameters string
            params = []

            # Add Easy Apply filter
            params.append(LINKEDIN_PARAMS["EASY_APPLY"])
            self.logger.debug("Added Easy Apply filter")

            # Add time filter
            if isinstance(self.time_filter, str) and self.time_filter.startswith('r') and self.time_filter[1:].isdigit():
                time_param = self.time_filter  # Already in correct format
            else:
                time_param = TIME_FILTER_MAPPING.get(self.time_filter, "r86400")

            if time_param:
                params.append(f"f_TPR={time_param}")
                self.logger.debug(f"Added time filter parameter: {self.time_filter} ({time_param})")

            # Handle work type filtering
            if work_types is None:
                # Default behavior based on remote_only flag
                if remote_only:
                    params.append(f"f_WT={WORK_TYPE_MAPPING['remote']}")  # Remote work
                    self.logger.debug("Added remote work filter")
                # If remote_only is False and no work_types specified, don't add any filter (show all)
            else:
                # Convert string work types to codes and filter out invalid ones
                type_codes = [WORK_TYPE_MAPPING.get(wt.lower(), "") for wt in work_types 
                            if wt.lower() in WORK_TYPE_MAPPING]

                if type_codes:
                    # Join multiple work types with commas for URL
                    work_type_param = LINKEDIN_PARAMS["URL_COMMA"].join(type_codes)
                    params.append(f"f_WT={work_type_param}")
                    self.logger.debug(f"Added work type filter: {work_type_param} (from {work_types})")

            # Add other useful parameters
            params.append(LINKEDIN_PARAMS["REFRESH"])

            # Construct URL with parameters
            filtered_url = f"{self.url}/jobs/collections/recommended/?{'&'.join(params)}"

            self.logger.info(f"Navigating to filtered top picks: {filtered_url}")
            self.browser_manager.navigate(filtered_url)

            # Step 1: Wait for DOM content to load (faster than networkidle)
            self.logger.debug("Waiting for DOM content to load...")
            self.page.wait_for_load_state("domcontentloaded", timeout=TIMING["EXTENDED_TIMEOUT"])
            
            # Step 2: Wait for job cards to appear (most reliable indicator)
            self.logger.debug(f"Waiting for job cards to appear...")
            job_cards_loaded = False
            
            try:
                # First attempt: Wait for cards with standard timeout
                self.page.wait_for_selector(self.selectors["JOB_CARDS"], timeout=TIMING["STANDARD_TIMEOUT"])
                job_cards_loaded = True
                self.logger.info("Job cards found on first attempt")
            except Exception as e:
                self.logger.warning(f"Job cards not visible yet, waiting longer: {str(e)}")
                # Second attempt: Add a delay and try a second time
                time.sleep(TIMING["MEDIUM_SLEEP"])
                
                try:
                    self.page.wait_for_selector(self.selectors["JOB_CARDS"], timeout=TIMING["EXTENDED_TIMEOUT"])
                    job_cards_loaded = True
                    self.logger.info("Job cards found on second attempt")
                except Exception as e2:
                    self.logger.warning(f"Still no job cards, will try to continue: {str(e2)}")
                    
                    # Failsafe: try scrolling the page to force loading
                    try:
                        self.logger.info("Scrolling page to force loading...")
                        self.page.evaluate("window.scrollBy(0, 500)")
                        time.sleep(TIMING["LONG_SLEEP"])
                        
                        # Check if job cards are visible now
                        visible_cards = self.page.query_selector_all(self.selectors["JOB_CARDS"])
                        if visible_cards and len(visible_cards) > 0:
                            job_cards_loaded = True
                            self.logger.info(f"Found {len(visible_cards)} job cards after scrolling")
                    except Exception as scroll_error:
                        self.logger.error(f"Error during scroll attempt: {str(scroll_error)}")
            
            # Step 3: Add a small delay for any animations to complete
            time.sleep(TIMING["MEDIUM_SLEEP"])
            
            # Step 4: Verify we have content by checking job count
            try:
                job_count_element = self.page.query_selector(".jobs-search-results-list__title-heading")
                if job_count_element:
                    job_count_text = job_count_element.inner_text()
                    self.logger.info(f"Recommended jobs header: {job_count_text}")
            except Exception as e:
                self.logger.debug(f"Could not extract job count: {e}")
            
            # Final check for job cards
            if not job_cards_loaded:
                visible_cards = self.page.query_selector_all(self.selectors["JOB_CARDS"])
                if visible_cards and len(visible_cards) > 0:
                    job_cards_loaded = True
                    self.logger.info(f"Found {len(visible_cards)} job cards in final check")
                else:
                    self.logger.warning("No job cards found, but will continue processing")
            
            self.logger.info("Successfully set up jobs with filters! Ready for job processing.")
            return True

        except Exception as e:
            self.logger.error(f"Error finding top picks and applying filters: {e}", exc_info=True)
            # Continue anyway to allow processing of any jobs that might have loaded
            self.logger.info("Attempting to continue despite error...")
            time.sleep(TIMING["LONG_SLEEP"])
            return True  # Return True to allow processing to continue

    def get_job_cards(self):
        """Get all job cards from the current page with better error handling"""
        try:
            # Wait for the job cards to appear with a generous timeout
            self.logger.debug(f"Waiting for job cards with selector: {self.selectors['JOB_CARDS']}")
            self.page.wait_for_selector(self.selectors["JOB_CARDS"], timeout=TIMING["EXTENDED_TIMEOUT"])

            # Add a small delay to ensure everything is rendered
            time.sleep(TIMING["SHORT_SLEEP"])

            # Query all job cards
            job_cards = self.page.query_selector_all(self.selectors["JOB_CARDS"])
            self.logger.info(f"Found {len(job_cards)} job cards")

            if not job_cards:
                # If no cards found, try scrolling a bit and retry
                self.logger.debug("No job cards found initially, scrolling and retrying")
                self.page.evaluate("window.scrollBy(0, 300)")
                time.sleep(TIMING["MEDIUM_SLEEP"])
                job_cards = self.page.query_selector_all(self.selectors["JOB_CARDS"])
                self.logger.info(f"After scroll, found {len(job_cards)} job cards")

            # Create a list of tuples (card, ember_id_number) for sorting
            sorted_cards = []
            for card in job_cards:
                try:
                    ember_id = card.get_attribute("id")
                    if ember_id and ember_id.startswith("ember"):
                        try:
                            # Extract number from "ember123"
                            ember_num = int(ember_id.replace("ember", ""))
                            sorted_cards.append((card, ember_num, ember_id))
                        except ValueError:
                            continue
                except Exception as e:
                    self.logger.error(f"Error processing card: {e}")
                    continue

            # Sort cards by ember ID number
            sorted_cards.sort(key=lambda x: x[1])
            self.logger.info(f"Sorted {len(sorted_cards)} job cards by ember ID")
            self.logger.debug(f"Card IDs: {[c[2] for c in sorted_cards[:5]]}...")

            return sorted_cards

        except Exception as e:
            self.logger.error(f"Error getting job cards: {e}", exc_info=True)
            return []

    def get_job_description(self):
        """Extract the job description text from the job details panel"""
        try:
            # Wait for the job description to load
            self.logger.debug(f"Waiting for job description with selector: {self.selectors['JOB_DESCRIPTION']}")
            self.page.wait_for_selector(self.selectors["JOB_DESCRIPTION"], timeout=TIMING["STANDARD_TIMEOUT"])

            # Extract the text content
            description_element = self.page.query_selector(self.selectors["JOB_DESCRIPTION"])
            if description_element:
                job_description = description_element.inner_text()
                self.logger.info(f"Successfully extracted job description ({len(job_description)} chars)")
                return job_description
            else:
                self.logger.warning("Job description element not found")
                return ""

        except Exception as e:
            self.logger.error(f"Error extracting job description: {e}", exc_info=True)
            return ""

    def extract_job_details(self):
        """Extract job details from the job details page with multiple fallback methods"""
        try:
            self.logger.debug("Extracting job details from page")
            
            # Extracting job title
            job_title = "General Software Engineer Position"  # Default fallback

            # Try primary selector first
            title_element = self.page.query_selector(self.selectors["JOB_DETAILS_TITLE"])
            if title_element:
                job_title = title_element.inner_text().strip()
                self.logger.debug(f"Found job title with primary selector: {job_title}")
            else:
                # Try fallback selector
                self.logger.debug("Primary job title selector failed, trying fallback")
                title_element_alt = self.page.query_selector(self.selectors["JOB_DETAILS_TITLE_ALT"])
                if title_element_alt:
                    job_title = title_element_alt.inner_text().strip()
                    self.logger.debug(f"Found job title with fallback selector: {job_title}")
                else:
                    self.logger.warning("Could not find job title with any selector")

            # Extracting company name
            company_name = "General Tech Based Company"  # Default fallback

            # Try primary selector first
            company_element = self.page.query_selector(self.selectors["JOB_DETAILS_COMPANY"])
            if company_element:
                company_name = company_element.inner_text().strip()
                self.logger.debug(f"Found company name with primary selector: {company_name}")
            else:
                # Try fallback selector
                self.logger.debug("Primary company name selector failed, trying fallback")
                company_element_alt = self.page.query_selector(self.selectors["JOB_DETAILS_COMPANY_ALT"])
                if company_element_alt:
                    company_name = company_element_alt.inner_text().strip()
                    self.logger.debug(f"Found company name with fallback selector: {company_name}")
                else:
                    self.logger.warning("Could not find company name with any selector")

            # Clean up text
            job_title = job_title.replace('\xa0', ' ').strip()
            company_name = company_name.replace('\xa0', ' ').strip()

            self.logger.info(f"Extracted job title: {job_title}")
            self.logger.info(f"Extracted company name: {company_name}")

            return job_title, company_name

        except Exception as e:
            self.logger.error(f"Error extracting job details: {e}", exc_info=True)
            return "General Software Engineer Position", "General Tech Based Company"

    def scroll_to_job_card(self, card, ember_id, ember_num, sorted_cards):
        """Scroll to a job card with retry logic."""
        self.logger.debug(f"Scrolling to job card: {ember_id}")
        for attempts in range(3):
            try:
                # Use JavaScript to scroll to the element by ID
                self.page.evaluate(f"""
                    const element = document.getElementById('{ember_id}');
                    if (element) {{
                        element.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                    }}
                """)
                time.sleep(TIMING["SHORT_SLEEP"] + attempts * 0.5)
                self.logger.debug(f"Scroll attempt {attempts+1} successful")
                break
            except Exception as e:
                self.logger.error(f"Scroll attempt {attempts+1} failed: {e}")
                time.sleep(TIMING["SHORT_SLEEP"] + attempts)

                # If last attempt, try a different approach
                if attempts == 2:
                    self.logger.info("Using alternative scroll method...")
                    # Scroll by position estimation
                    self.page.evaluate(f"""
                        window.scrollBy(0, {250 * (sorted_cards.index((card, ember_num, ember_id)) + 1)});
                    """)
                    time.sleep(TIMING["MEDIUM_SLEEP"])

    def load_more_cards(self, current_cards):
        """Load more job cards by scrolling down."""
        self.logger.info("No new cards processed, scrolling to load more...")
        self.page.evaluate("window.scrollBy(0, 500)")
        time.sleep(TIMING["LONG_SLEEP"])

        # Check if we loaded new cards
        new_cards = self.page.query_selector_all(self.selectors["JOB_CARDS"])
        if len(new_cards) <= len(current_cards):
            self.logger.info("No more job cards loaded on current page")
            return False
        
        self.logger.info(f"Loaded {len(new_cards) - len(current_cards)} additional cards")
        return True

    def navigate_to_next_page(self):
        """Navigate to the next page of job results if available."""
        try:
            self.logger.info("Checking for next page...")

            # Look for the Next button
            next_button = self.page.query_selector(self.selectors["NEXT_BUTTON"])
            
            if not next_button:
                # Fallback: try finding by aria-label
                next_button = self.page.query_selector("button[aria-label='View next page']")
            
            if not next_button:
                self.logger.info("No Next button found")
                return False

            # Check if the button is disabled (we're on the last page)
            is_disabled = next_button.get_attribute("disabled")
            if is_disabled:
                self.logger.info("Next button is disabled - on last page")
                return False

            # Get current page info before clicking
            page_state = self.page.query_selector(self.selectors["PAGE_STATE"])
            if page_state:
                self.logger.info(f"Current state: {page_state.inner_text().strip()}")

            # Click the Next button
            self.logger.info("Clicking Next button...")
            next_button.click()

            # Wait for the page to load
            self.page.wait_for_load_state()
            time.sleep(TIMING["PAGE_LOAD_WAIT"])

            # Verify we moved to a new page by checking if page state changed
            new_page_state = self.page.query_selector(self.selectors["PAGE_STATE"])
            if new_page_state:
                self.logger.info(f"New state: {new_page_state.inner_text().strip()}")

            self.logger.info("Successfully navigated to next page")
            return True

        except Exception as e:
            self.logger.error(f"Error navigating to next page: {e}")
            return False

    def is_easy_apply_job(self):
        """
        Check if the current job listing has an 'Easy Apply' button rather than a regular 'Apply' button
        that redirects to an external website.
        
        Returns:
            bool: True if it's an Easy Apply job, False if it's an external application
        """
        try:
            self.logger.info("Checking if job has Easy Apply...")
            
            # Wait for any button to appear
            self.page.wait_for_selector(".jobs-apply-button", timeout=TIMING["STANDARD_TIMEOUT"])
            
            # Get the apply button
            apply_button = self.page.query_selector(".jobs-apply-button")
            if not apply_button:
                self.logger.info("No apply button found")
                return False
            
            # SIMPLIFICATION: If we can find a button with class jobs-apply-button,
            # we'll assume it's Easy Apply unless we find clear evidence otherwise
            
            # Definitive check for external link icon - clear sign of NOT Easy Apply
            external_link_icon = apply_button.query_selector("svg[data-test-icon='link-external-small']")
            if external_link_icon:
                self.logger.info("Found external link icon - this is NOT an Easy Apply job")
                return False
                
            # Check aria-label for "website" which indicates external
            aria_label = apply_button.get_attribute("aria-label") or ""
            if "company website" in aria_label.lower() or "external site" in aria_label.lower():
                self.logger.info("Aria-label indicates external application - this is NOT an Easy Apply job")
                return False
                
            # If no clear external indicators found, assume it's Easy Apply
            self.logger.info("No external indicators found - assuming this IS an Easy Apply job")
            return True
                
        except Exception as e:
            self.logger.error(f"Error checking if job is Easy Apply: {e}", exc_info=True)
            # Default to assuming it's an Easy Apply job if there was an error checking
            return True