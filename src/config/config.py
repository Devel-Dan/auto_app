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
    },
    "EDUCATION": {
        "SECTION_HEADER": "h3.t-16.mb2:has-text('Education')",
        "START_FIELDSET": 'fieldset[data-test-date-dropdown="start"]',
        "END_FIELDSET": 'fieldset[data-test-date-dropdown="end"]',
        "MONTH_SELECT": 'select[data-test-month-select]',
        "YEAR_SELECT": 'select[data-test-year-select]',
        "CURRENT_CHECKBOX": 'input[type="checkbox"][id*="present"]',
        "SCHOOL_SELECT": ['select[id*="School"]', 'select[id*="multipleChoice"]'],
        "DEGREE_SELECT": 'select[id*="Degree"]',
        "DISCIPLINE_SELECT": 'select[id*="Discipline"]'
    },
    "SAFETY_DIALOG": {
        "CONTAINER": "div[aria-labelledby='header']:has(h2#header:has-text('Job search safety reminder'))",
        "CONTINUE_BUTTON": "button:has-text('Continue applying')",
        "APPLY_BUTTON": ".jobs-apply-button",
        "HEADER": "h2#header:has-text('Job search safety reminder')"
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
    "cellular",
    "photonic",
    "lead"
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

# Education default settings
EDUCATION_DEFAULTS = {
    "start_month": "1",  # January
    "start_year": "2009",
    "end_month": "8",    # August
    "end_year": "2014",
    "university": "North Carolina State University",
    "degree": "Bachelor's Degree",
    "discipline": "Computer Science"
}

# LinkedIn API parameters
LINKEDIN_PARAMS = {
    "EASY_APPLY": "f_AL=true",
    "REMOTE_WORK": "f_WT=2",
    "URL_COMMA": "%2C",
    "REFRESH": "refresh=true",
    "ORIGIN": "origin=JOB_SEARCH_PAGE_SEARCH_BUTTON"
}

# File paths
FILE_PATHS = {
    "FORM_RESPONSES": [
        "src/data/form_responses.json",
        "data/form_responses.json",
        "form_responses.json"
    ],
    "LOGS_DIR": "logs",
    "ROOT_LOG": "logs/all_logs.log",
    "MAIN_LOG": "logs/main.log",
    "APPLICATION_LOG": "logs/application_{}.log"  # Format string for application logs
}

# Network and UI timing settings
TIMING = {
    "STANDARD_TIMEOUT": 5000,  # 5 seconds in ms
    "EXTENDED_TIMEOUT": 10000, # 10 seconds in ms
    "SHORT_SLEEP": 1,          # 1 second
    "MEDIUM_SLEEP": 2,         # 2 seconds
    "LONG_SLEEP": 3,           # 3 seconds
    "PAGE_LOAD_WAIT": 5        # 5 seconds
}

# Logging settings
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Resume prompt templates
PROMPTS = {
    "RESUME_GENERATION": """
I'm applying to a job with the following description:
({job_description})

You are an expert resume writer and ATS optimization specialist. Your task is to create a highly effective, ATS-friendly resume in Markdown format based on the provided job description and attached resume. Follow these guidelines:

1. Analyze the job description for key skills, qualifications, and keywords.
2. Review the existing resume for relevant experience and achievements.
3. Create a new resume that aligns the candidate's qualifications with the job requirements.
4. Use the following structure, formatting it in Markdown:

# [Candidate Name]
[City, State] | [Phone] | [Email] | [LinkedIn]

## Professional Summary
[Concise 2-3 sentence summary tailored to the job description]

## Core Competencies
- [Skill 1]
- [Skill 2]
- [Skill 3]
[List 6-8 key ]

## Professional Experience

### [Job Title], [Company Name]
[Start Date] - [End Date]

- [Achievement/responsibility using action verb and metrics]
- [Achievement/responsibility using action verb and metrics]
- [Achievement/responsibility using action verb and metrics]


[Repeat for each relevant position, focusing on the most recent and relevant roles]

## Education

**[Degree], [Major]**
[University Name], [Location]
[Graduation Date]

## Technical Skills
[List relevant technical skills, separated by commas]

Please generate a tailored, ATS-optimized resume based on these guidelines, the provided job description, and the candidate's existing resume

5. Ensure the resume is concise, typically fitting two pages maximum for extensive experience.
6. Ensure most recent job contains at least one acheivement that can be related to what the job description is looking for, generate a project if need be, but it must also make sense to the current position.
7. Professional summary should tie current skills to job description if no direct experience is there, ensure knowledge gaps can be easily closed
8. Use bullet points for easy readability.
9. Incorporate keywords from the job description naturally throughout the resume.
10. Use action verbs and quantify achievements where possible.
11. Avoid graphics, tables, or complex formatting that may confuse ATS.
12. Use standard section headings for easy parsing by ATS.
13. pretend you are being called like an API endpoint and your payload(reponse) is being directly ported into an .md file, every line has to translate correctly as a markdown file.
14. My linkedin is https://www.linkedin.com/in/dankazaman/
15. DO NOT ADD ANY '```markdown' and '```' LINES IN YOUR RESPONSE
""",

    "FORM_RESPONSE": """
You are an AI assistant helping a software developer fill out a LinkedIn job application. Answer the following question concisely and directly, optimizing for the applicant's chances of being hired. Base your response on the provided context, resume, and job description.

Question: {question_text}

{options_text}

Job Description:
{job_description}

{error_text}

Applicant Context:
- Software Developer with experience in Python, AWS, Testing, and DevOps
- US Citizen based in San Francisco, no sponsorship required
- Currently employed, available immediately
- Open to remote, hybrid, or in-office work
- Bachelor's Degree in Business Administration
- Willing to relocate if needed
- Prefers not to disclose demographic information when possible
- looking for 100k to 120k salary, or hourly equivalent 

Response Guidelines:
1. Provide a direct answer without explanations or additional text.
2. Always align responses with the job description requirements.
3. If there's a negative difference between the applicant's profile and the job requirements, response should match what the job is asking for.
4. For experience-related questions, assume the applicant has relevant experience from their resume or can quickly acquire it.
5. For years of experience, use the job posting's required years if mentioned, otherwise refer to my resume, and if it is not there, default to 2-3 years.
6. For open-ended questions, provide a concise, relevant response based on the resume and job description.
7. For multiple-choice questions, select the most favorable option that aligns with both the applicant's profile and job requirements.
8. Tailor the response to highlight strengths and match job requirements, even if it requires slight exaggeration of skills or experience.
9. do not provide any estimations, always choose more desirable answer, in reference to the job description, if a range is determined (2-3 YOE -> 3)
10. do not add any units. Most questions that ask for an amount are being entered for a database, so only want numbers (2-3 years -> 3, $120,000 a year -> 120000)
11. give human responses not too professional and AI sounding.

Answer:
"""
}

