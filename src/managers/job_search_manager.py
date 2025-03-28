import logging
import urllib.parse
import time

# Import from config
from src.config.config import TIME_FILTER_MAPPING, WORK_TYPE_MAPPING

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
            params.append("f_AL=true")
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
                    work_types.append("2")  # Remote
                else:
                    # Include multiple work types if not strictly remote
                    work_types.extend(["2", "1", "3"])  # Remote, Onsite, Hybrid

            if work_types:
                params.append(f"f_WT={urllib.parse.quote('%2C'.join(work_types))}")
                self.logger.debug(f"Added work type filter: {work_types}")

            # Add refresh and origin parameters
            params.extend([
                "refresh=true",
                "origin=JOB_SEARCH_PAGE_SEARCH_BUTTON"
            ])

            # Combine all parameters into final URL
            search_url = f"{base_url}?{'&'.join(params)}"

            self.logger.info(f"Navigating to search URL: {search_url[:100]}...")

            # Navigate to the constructed URL
            self.browser_manager.navigate(search_url)

            # Navigate to the constructed URL
            self.browser_manager.navigate(search_url)

            # Improved page load waiting strategy
            self.logger.debug("Waiting for DOM content to load")
            self.page.wait_for_load_state("domcontentloaded")
            
            # Add a small delay for page stability
            self.logger.debug("Adding a small delay for page stability...")
            time.sleep(3)

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
                params.append("f_AL=true")
                self.logger.debug("Added Easy Apply filter")

                # Add time filter - using TIME_FILTER_MAPPING from config
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
                        params.append("f_WT=2")  # 2 = Remote work
                        self.logger.debug("Added remote work filter")
                    # If remote_only is False and no work_types specified, don't add any filter (show all)
                else:
                    # Map string work types to LinkedIn's numeric codes - using WORK_TYPE_MAPPING from config
                    # Convert string work types to codes and filter out invalid ones
                    type_codes = [WORK_TYPE_MAPPING.get(wt.lower(), "") for wt in work_types 
                                if wt.lower() in WORK_TYPE_MAPPING]

                    if type_codes:
                        # Join multiple work types with commas for URL
                        work_type_param = "%2C".join(type_codes)  # URL-encoded comma ","
                        params.append(f"f_WT={work_type_param}")
                        self.logger.debug(f"Added work type filter: {work_type_param} (from {work_types})")

                # Add other useful parameters
                params.append("refresh=true")

                # Construct URL with parameters
                filtered_url = f"{self.url}/jobs/collections/recommended/?{'&'.join(params)}"

                self.logger.info(f"Navigating to filtered top picks: {filtered_url}")
                self.browser_manager.navigate(filtered_url)

                # Wait for page to load
                self.logger.debug("Waiting for page to load")
                self.page.wait_for_load_state("networkidle")
                time.sleep(3)

                # Log some information about the results
                try:
                    job_count_element = self.page.query_selector(".jobs-search-results-list__title-heading")
                    if job_count_element:
                        job_count_text = job_count_element.inner_text()
                        self.logger.info(f"Recommended jobs header: {job_count_text}")
                except Exception as e:
                    self.logger.debug(f"Could not extract job count: {e}")

                self.logger.info("Successfully set up jobs with filters! Ready for job processing.")
                return True

            except Exception as e:
                self.logger.error(f"Error finding top picks and applying filters: {e}", exc_info=True)
                return False

    def get_job_cards(self):
        """Get all job cards from the current page with better error handling"""
        try:
            # Wait for the job cards to appear with a generous timeout
            self.logger.debug(f"Waiting for job cards with selector: {self.selectors['JOB_CARDS']}")
            self.page.wait_for_selector(self.selectors["JOB_CARDS"], timeout=10000)

            # Add a small delay to ensure everything is rendered
            time.sleep(1)

            # Query all job cards
            job_cards = self.page.query_selector_all(self.selectors["JOB_CARDS"])
            self.logger.info(f"Found {len(job_cards)} job cards")

            if not job_cards:
                # If no cards found, try scrolling a bit and retry
                self.logger.debug("No job cards found initially, scrolling and retrying")
                self.page.evaluate("window.scrollBy(0, 300)")
                time.sleep(2)
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
            self.page.wait_for_selector(self.selectors["JOB_DESCRIPTION"], timeout=5000)

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
                time.sleep(1 + attempts * 0.5)
                self.logger.debug(f"Scroll attempt {attempts+1} successful")
                break
            except Exception as e:
                self.logger.error(f"Scroll attempt {attempts+1} failed: {e}")
                time.sleep(1 + attempts)

                # If last attempt, try a different approach
                if attempts == 2:
                    self.logger.info("Using alternative scroll method...")
                    # Scroll by position estimation
                    self.page.evaluate(f"""
                        window.scrollBy(0, {250 * (sorted_cards.index((card, ember_num, ember_id)) + 1)});
                    """)
                    time.sleep(2)

    def load_more_cards(self, current_cards):
        """Load more job cards by scrolling down."""
        self.logger.info("No new cards processed, scrolling to load more...")
        self.page.evaluate("window.scrollBy(0, 500)")
        time.sleep(3)

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
            self.logger.info("Checking for pagination controls...")

            # Look for the pagination container
            pagination = self.page.query_selector(self.selectors["PAGINATION"])
            if not pagination:
                self.logger.info("Pagination controls not found")
                return False

            # Find the current active page number
            active_page_element = pagination.query_selector(self.selectors["ACTIVE_PAGE"])
            if not active_page_element:
                self.logger.info("Could not determine the current active page")
                return False

            # Extract current page number
            current_page_button = active_page_element.query_selector("button")
            if not current_page_button:
                self.logger.info("Could not find the current page button")
                return False

            # Get the page number from the aria-label attribute
            aria_label = current_page_button.get_attribute("aria-label")
            if not aria_label or not aria_label.startswith("Page "):
                self.logger.info(f"Unexpected aria-label format: {aria_label}")
                return False

            # Parse the current page number
            try:
                current_page = int(aria_label.replace("Page ", ""))
                self.logger.info(f"Currently on page {current_page}")
            except ValueError:
                self.logger.info(f"Could not parse page number from: {aria_label}")
                return False

            # Find the total number of pages
            page_state = pagination.query_selector(".artdeco-pagination__page-state")
            if page_state:
                state_text = page_state.inner_text()
                try:
                    total_pages = int(state_text.split("of ")[1].strip())
                    self.logger.info(f"Total pages: {total_pages}")

                    if current_page >= total_pages:
                        self.logger.info("Already on the last page")
                        return False
                except (IndexError, ValueError):
                    self.logger.info(f"Could not parse total pages from: {state_text}")
                    # Continue anyway since we can still try to find the next page button

            # Try to find and click the next page
            next_page_number = current_page + 1
            self.logger.debug(f"Looking for page {next_page_number} button")

            # First try: Look for a button with aria-label="Page X" where X is the next page number
            next_page_selector = f"button[aria-label='Page {next_page_number}']"
            next_page_button = pagination.query_selector(next_page_selector)

            if next_page_button:
                self.logger.info(f"Found button for page {next_page_number}")
                next_page_button.click()
                self.logger.info(f"Clicked to navigate to page {next_page_number}")

                # Wait for page to load
                self.page.wait_for_load_state()
                time.sleep(5)  # Give some extra time for results to load

                return True

            self.logger.info(f"Could not find button for page {next_page_number}")
            return False

        except Exception as e:
            self.logger.error(f"Error navigating to next page: {e}", exc_info=True)
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
            self.page.wait_for_selector(".jobs-apply-button", timeout=5000)
            
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