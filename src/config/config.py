"""
Configuration file for LinkedIn Job Application Automation.
Contains all constants, selectors, and settings.
"""
import os
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

# LinkedIn application settings
APPLICATION_TYPE = "linkedin"

# Browser settings
HEADLESS_DEFAULT = False
USER_DATA_DIR = os.getenv('BROWSER_DATA', './browser_data')

# Resume settings
RESUME_DIR = os.getenv('RESUME_DIR', 'custom_resumes')
DEFAULT_RESUME_PATH = os.getenv('DEFAULT_RESUME_PATH', 'path/to/your/default_resume.pdf')

# Form responses settings
FORM_RESPONSES_PATH = os.getenv('FORM_RESPONSES_PATH', 'form_responses.json')

# API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Application settings
APPLICATION_MAPPING = {
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

# Common selectors for DOM elements
SELECTORS = {
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

# Job filters - positions to avoid
JOB_FILTERS = [
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
    "AI engineer",
    "cellular"
]

# Time filter mapping
TIME_FILTER_MAPPING = {
    "day": "r86400",     # Past 24 hours (86400 seconds)
    "week": "r604800",   # Past week (7 days = 604800 seconds)
    "month": "r2592000", # Past month (30 days = 2592000 seconds)
    "any": ""            # Any time (no parameter)
}

# Work type filter mapping
WORK_TYPE_MAPPING = {
    'remote': '2',
    'onsite': '1',
    'on-site': '1',
    'hybrid': '3'
}

# Predefined search queries
SEARCH_QUERIES = {
    "default": {
        "titles_include": [
            "software engineer", 
            "test engineer", 
            "python developer", 
            "qa engineer",
            "devops engineer",
            "data engineer",
            "automation",
            "iot engineer",
            "backend engineer",
            "fullstack engineer",
            "cloud engineer",
            "systems engineer"
        ],
        "titles_exclude": [
            "manager",
            "principal",
            "staff",
            "director",
            "president",
            "founding",
            "lead"
        ],
        "skills_required": [
            "Python", "AWS", "HITL", "pytest", "Flask", "Docker",
            "HIL testing", "Hardware-in-the-Loop", "embedded systems", "real-time systems"
        ],
        "functions_required": [
            "automat", "pipeline", "testing", "data processing", 
            "system validation", "controller design"
        ]
    }
}

# Logging settings
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
