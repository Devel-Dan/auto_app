import os
import logging
from src.managers.browser_manager import BrowserManager
from src.managers.authentication_manager import AuthenticationManager
from src.managers.job_search_manager import JobSearchManager
from src.handlers.form_handler import FormHandler
from src.managers.application_manager import ApplicationManager
from src.managers.form_manager import FormResponseManager
from src.handlers.custom_resume import CustomResumeHandler
from src.core.logger import setup_logger

class ApplicationApp:
    """
    Main application class that coordinates the entire job application process.
    This class is a slimmed-down version that delegates to specialized managers.
    """
    def __init__(self, application_type, headless=False, time_filter="day"):
        self.application_type = application_type
        self.headless = headless
        self.time_filter = time_filter  # Store time filter
        
        # Initialize logger
        self.logger = setup_logger(
            name="ApplicationApp", 
            log_level=logging.DEBUG,
            log_file=f"logs/application_{application_type}.log",
            add_timestamp=True
        )
        
        self.logger.info(f"Initializing ApplicationApp for {application_type} with time filter: {time_filter}")
        
        # Load configuration
        self.load_config()
        
        # Initialize response manager and resume handler
        self.response_manager = FormResponseManager()
        self.resume_handler = CustomResumeHandler()
        
        # Initialize component managers (but don't start browser yet)
        self.browser_manager = None
        self.auth_manager = None
        self.job_search_manager = None
        self.form_handler = None
        self.application_manager = None

    def load_config(self):
        """Load application configuration"""
        # Job filters - positions to avoid
        self.job_filters = [
            "machine learning",
            "manager",
            "principal",
            "staff",
            "embedded",
            "bioinformatics",
            "electrical",
            "mechanical",
            "data scientist",
            "founding",
            "c++",
            "AI engineer"
        ]
        
        # Application-specific configurations
        self.application_mapping = {
            "linkedin": {
                "url": 'https://www.linkedin.com',
                "login": "/login/",
                "jobs": "/jobs/",
                "username": os.getenv('USERNAME'),
                "password": os.getenv("PASSWORD"),
                "authenticator": True,
                "logged_in_selector": "div[data-control-name='nav.homepage']",
                "search_keyword_selector": "input[aria-label='Search by title, skill, or company']",
                "search_location_selector": "input[aria-label='City, state, or zip code']",
                "time_filter_button": "button[aria-label='Date posted filter. Clicking this button displays all Date posted filter options.']",
                "time_filter_enter": '.reusable-search-filters-buttons > .artdeco-button--primary',
                "easy_apply_button": "button[aria-label='Easy Apply filter.']",
                "close": "button[aria-label='Dismiss']"
            }
        }
        
        # Common selectors
        self.selectors = {
            "MODAL": "div.artdeco-modal.jobs-easy-apply-modal",
            "CLOSE_BUTTON": [
                "button[aria-label='Dismiss']",
                ".artdeco-modal__dismiss",
                "button.artdeco-button--circle.artdeco-modal__dismiss",
                "button.artdeco-button--tertiary[aria-label='Dismiss']",
                "#ember1266",
                ".artdeco-modal button[aria-label='Dismiss']"
            ],
            "JOB_CARDS": "li.ember-view.occludable-update.scaffold-layout__list-item",
            # More specific selectors for the job details page
            "JOB_DETAILS_TITLE": ".job-details-jobs-unified-top-card__job-title h1 a",
            "JOB_DETAILS_TITLE_ALT": ".job-details-jobs-unified-top-card__job-title h1",
            "JOB_DETAILS_COMPANY": ".job-details-jobs-unified-top-card__company-name a",
            "JOB_DETAILS_COMPANY_ALT": ".job-details-jobs-unified-top-card__company-name",
            "JOB_DESCRIPTION": "div.jobs-description-content__text--stretch",
            "EASY_APPLY_BUTTON": ".jobs-apply-button",
            "RESUME_SECTION": ".jobs-document-upload-redesign-card__container",
            "RESUME_UPLOAD_BUTTON": "label.jobs-document-upload__upload-button",
            "ERROR_INDICATORS": [
                ".artdeco-inline-feedback--error",
                ".fb-dash-form-element-error",
                ".invalid-input",
                "[role='alert']"
            ],
            "PAGINATION": ".jobs-search-results-list__pagination",
            "ACTIVE_PAGE": ".artdeco-pagination__indicator--number.active",
            "NAVIGATION": {
                "SUBMIT": "button.artdeco-button--primary:has-text('Submit application')",
                "REVIEW": "button.artdeco-button--primary:has-text('Review')",
                "NEXT": "button.artdeco-button--primary:has-text('Next')",
                "NOT_NOW": "button:has-text('Not now')"
            }
        }
        
        # Get app-specific config
        self.app_config = self.application_mapping[self.application_type]
        
        # Browser user data directory
        self.user_data_dir = os.getenv("BROWSER_DATA")

    def __enter__(self):
        try:
            # Initialize browser
            self.browser_manager = BrowserManager(
                user_data_dir=self.user_data_dir,
                headless=self.headless,
                logger=self.logger
            ).__enter__()
            
            # Initialize managers with browser and config
            self.auth_manager = AuthenticationManager(
                browser_manager=self.browser_manager,
                config=self.app_config,
                logger=self.logger
            )
            
            self.job_search_manager = JobSearchManager(
                browser_manager=self.browser_manager,
                config=self.app_config,
                selectors=self.selectors,
                logger=self.logger
            )
            
            # Set the time filter from constructor
            self.job_search_manager.time_filter = self.time_filter
            self.logger.info(f"Setting time filter to: {self.time_filter}")
            
            self.form_handler = FormHandler(
                browser_manager=self.browser_manager,
                response_manager=self.response_manager,
                selectors=self.selectors,
                logger=self.logger
            )
            
            self.application_manager = ApplicationManager(
                browser_manager=self.browser_manager,
                job_search_manager=self.job_search_manager,
                form_handler=self.form_handler,
                resume_handler=self.resume_handler,
                selectors=self.selectors,
                job_filters=self.job_filters,
                logger=self.logger
            )
            
            # Ensure we're logged in
            self.auth_manager.ensure_logged_in()
                
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
        """Clean up resources"""
        if self.browser_manager:
            self.browser_manager.__exit__(None, None, None)

    def search_jobs(self, keywords: str, location: str, remote_only=True, work_types=None):
        """
        Search for jobs with specific keywords and location, with enhanced work type filtering
        
        Args:
            keywords: Search keywords/query
            location: Location to search in
            remote_only: Whether to only show remote jobs (default: True)
            work_types: List of work types to filter for (valid values: 'remote', 'onsite', 'hybrid')
        """
        self.job_search_manager.search_jobs(keywords, location, remote_only, work_types)

    def find_top_picks_and_easy_apply_jobs(self, remote_only=True, work_types=None):
        """
        Navigate to top picks jobs with Easy Apply filter and enhanced work type filtering
        
        Args:
            remote_only: Whether to only show remote jobs (default: True)
            work_types: List of work types to filter for (valid values: 'remote', 'onsite', 'hybrid')
        """
        return self.job_search_manager.find_top_picks_and_easy_apply_jobs(remote_only, work_types)

    def apply(self):
        """Apply to all eligible jobs on the page"""
        self.application_manager.apply()