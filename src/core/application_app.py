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
# Import config
from src.config.config import APPLICATION_MAPPING, SELECTORS, JOB_FILTERS

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
        # Job filters from config
        self.job_filters = JOB_FILTERS
        
        # Application-specific configurations from config
        self.application_mapping = APPLICATION_MAPPING
        
        # Common selectors from config
        self.selectors = SELECTORS
        
        # Get app-specific config
        self.app_config = self.application_mapping[self.application_type]
        
        # Browser user data dir
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