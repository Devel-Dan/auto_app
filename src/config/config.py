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

# Stop words for form response keyword extraction
FORM_STOP_WORDS = [
    # Basic articles, conjunctions and pronouns
    'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
    'which', 'this', 'that', 'these', 'those', 'then', 'just', 'so', 'than',
    'such', 'both', 'through', 'about', 'into', 'between', 'after', 'since',
    'without', 'within', 'along', 'across', 'behind', 'beyond', 'plus',
    'except', 'up', 'out', 'around', 'down', 'off', 'above', 'below',
    
    # Prepositions
    'to', 'from', 'in', 'on', 'by', 'at', 'for', 'with', 
    
    # Common verbs
    'do', 'does', 'did', 'have', 'has', 'had', 'am', 'is', 'are', 'was', 'were', 
    'be', 'been', 'being', 'can', 'could', 'shall', 'should', 'will', 'would',
    'may', 'might', 'must', 'get', 'gets', 'got', 'make', 'makes', 'made',
    
    # Personal pronouns
    'of', 'you', 'your', 'we', 'our', 'i', 'me', 'my', 'he', 'him', 'his', 
    'she', 'her', 'hers', 'they', 'them', 'their', 'theirs', 'it', 'its',
    
    # Quantifiers
    'many', 'much', 'few', 'some', 'all', 'any', 'each', 'every',
    
    # Question words
    'who', 'whom', 'whose', 'when', 'where', 'why', 'how',
    
    # Common adverbs
    'very', 'really', 'quite', 'simply', 'now', 'here', 'there', 'always', 
    'never', 'ever', 'again', 'already', 'soon', 'too', 'also', 'only',
    
    # Form-specific common words
    'please', 'following', 'would', 'like', 'tell', 'us', 'let', 'know',
    'provide', 'submit', 'describe', 'explain', 'list', 'share', 'select',
    'choose', 'check', 'enter', 'confirm', 'answer', 'question', 'option',
    'optional', 'required', 'prefer', 'statement'
]

# Important keywords for form response matching by category
FORM_IMPORTANT_KEYWORDS = {
    # Work and employment
    'work': ['work', 'job', 'career', 'position', 'employ', 'company', 'organization', 
             'business', 'occupation', 'sector', 'industry', 'role', 'title', 'function',
             'full-time', 'part-time', 'contract', 'permanent', 'temporary', 'w2', 'c2c',
             'corp', 'contractor', 'consultant', 'manager', 'management', 'lead', 'team'],
    
    # Location and relocation
    'location': ['location', 'relocate', 'remote', 'onsite', 'on-site', 'hybrid', 
                 'city', 'state', 'country', 'region', 'address', 'residence', 
                 'commute', 'distance', 'travel', 'local', 'global', 'international',
                 'domestic', 'regional', 'where', 'area', 'currently', 'based',
                 'office', 'live', 'living', 'reside', 'resident', 'bay'],
    
    # Experience and skills
    'experience': ['experience', 'year', 'skill', 'ability', 'competence', 'proficiency',
                   'expertise', 'knowledge', 'capability', 'strength', 'talent',
                   'professional', 'qualification', 'specialist', 'expert', 
                   'background', 'history', 'track', 'record', 'portfolio',
                   'prior', 'previous', 'hands-on', 'practical', 'technical',
                   'designing', 'developing', 'implementing', 'architecture'],
    
    # Education and credentials
    'education': ['education', 'degree', 'bachelor', 'master', 'phd', 'doctorate',
                  'university', 'college', 'school', 'academy', 'institute', 'credential',
                  'certification', 'certificate', 'graduate', 'undergraduate', 'alumni',
                  'major', 'minor', 'study', 'student', 'gpa', 'academic', 'diploma',
                  'field', 'graduation', 'graduated', 'bs', 'ba', 'ms', 'mba', 'bsc'],
    
    # Authorization and legal
    'legal': ['authorize', 'authorization', 'legal', 'sponsor', 'sponsorship', 'visa', 
              'citizen', 'citizenship', 'green', 'card', 'permanent', 'resident', 
              'immigration', 'status', 'work', 'permit', 'right', 'law', 'regulation',
              'eligibility', 'eligible', 'requirement', 'comply', 'compliance',
              'background', 'check', 'clearance', 'security', 'verification', 'h1b'],
    
    # Languages and programming
    'languages': ['language', 'programming', 'code', 'coding', 'software', 'development',
                 'python', 'java', 'javascript', 'c++', 'c#', 'ruby', 'php', 'go', 'golang',
                 'swift', 'kotlin', 'typescript', 'html', 'css', 'sql', 'nosql', 'web',
                 'mobile', 'cloud', 'frontend', 'backend', 'fullstack', 'algorithm',
                 'framework', 'library', 'api', 'rest', 'graphql', 'microservice'],
    
    # Technologies and tools
    'technologies': ['technology', 'tool', 'framework', 'library', 'platform', 'system',
                    'database', 'aws', 'azure', 'gcp', 'react', 'angular', 'vue', 'node',
                    'django', 'flask', 'spring', 'kubernetes', 'docker', 'terraform',
                    'jenkins', 'git', 'ci/cd', 'devops', 'agile', 'scrum', 'kanban',
                    'ai', 'ml', 'machine', 'learning', 'data', 'analytics', 'testing',
                    'automation', 'infrastructure', 'pipeline', 'security'],
    
    # Personal information and demographics
    'personal': ['name', 'phone', 'email', 'address', 'contact', 'birth', 'age', 'gender',
                'ethnicity', 'race', 'demographic', 'diversity', 'veteran', 'disability',
                'disabled', 'handicap', 'accommodation', 'military', 'service', 'identity',
                'orientation', 'lgbtq', 'transgender', 'specify', 'prefer', 'disclosure'],
    
    # Salary and compensation
    'compensation': ['salary', 'compensation', 'wage', 'pay', 'earning', 'income', 'bonus',
                    'benefit', 'stock', 'option', 'equity', 'rate', 'hourly', 'annual',
                    'yearly', 'monthly', 'package', 'total', 'expectation', 'range',
                    'desired', 'expected', 'requirement', 'negotiable', 'budget', 'band'],
    
    # Availability and scheduling
    'availability': ['available', 'availability', 'start', 'notice', 'schedule', 'shift',
                    'flexible', 'flexibility', 'hour', 'day', 'week', 'weekend', 'holiday',
                    'vacation', 'leave', 'pto', 'balance', 'commitment', 'duration',
                    'period', 'immediately', 'urgently', 'urgent', 'timeframe', 'term'],
    
    # Application and interview
    'application': ['apply', 'application', 'interview', 'resume', 'cv', 'cover',
                   'letter', 'portfolio', 'sample', 'reference', 'recommendation',
                   'assessment', 'test', 'evaluation', 'screen', 'submission',
                   'linkedin', 'profile', 'github', 'writing', 'process', 'hiring'],
                   
    # Domain-specific
    'domains': ['banking', 'finance', 'healthcare', 'medical', 'insurance', 'retail',
               'ecommerce', 'manufacturing', 'automotive', 'aerospace', 'defense',
               'energy', 'telecom', 'media', 'entertainment', 'education', 'government',
               'nonprofit', 'startup', 'enterprise', 'consulting', 'research',
               'pharmaceutical', 'biotechnology', 'food', 'beverage', 'hospitality',
               'transportation', 'logistics', 'construction', 'real', 'estate']
}

# Flatten the important keywords for direct usage
FORM_IMPORTANT_KEYWORDS_FLAT = []
for category in FORM_IMPORTANT_KEYWORDS.values():
    FORM_IMPORTANT_KEYWORDS_FLAT.extend(category)

# Common compound terms that should be matched as single concepts
FORM_COMPOUND_PATTERNS = [
    r'\b(work|job)\s+experience\b',
    r'\b(total|overall)\s+experience\b', 
    r'\b(bachelor\'?s?|master\'?s?|phd|doctorate)\s+degree\b',
    r'\b(software|web|mobile|backend|fullstack|frontend)\s+(developer|engineer)\b',
    r'\b(onsite|on-site|on\s+site)\b',
    r'\b(remote|hybrid)\s+work\b',
    r'\bwork\s+(authorization|permit|visa|eligibility)\b',
    r'\blegal(ly)?\s+(authorized|eligible)\b',
    r'\b(us|u\.s\.|united\s+states)\s+(citizen|citizenship)\b',
    r'\bgreen\s+card\b',
    r'\bcurrent(ly)?\s+(employ|employed|work|location)\b',
    r'\bsecurity\s+clearance\b',
    r'\bhourly\s+rate\b',
    r'\bdata\s+(science|scientist|engineer|engineering|analytics)\b',
    r'\bmachine\s+learning\b',
    r'\bdevops\s+engineer\b',
    r'\btest(ing)?\s+automation\b',
    r'\bci/cd\b',
    r'\bcloud\s+(computing|infrastructure|platform|service)\b'
]

# Matching thresholds and weights
MATCH_THRESHOLDS = {
    "KEYWORD_MATCH_THRESHOLD": 0.5,      # Threshold for considering keyword matches
    "COMBINED_SCORE_THRESHOLD": 0.6,     # Threshold for accepting combined matches
    "FUZZY_MATCH_THRESHOLD": 0.8,        # Threshold for traditional fuzzy matching
}

MATCH_WEIGHTS = {
    "KEYWORD_WEIGHT": 0.7,               # Weight for keyword similarity
    "STRING_WEIGHT": 0.3,                # Weight for string similarity
}

# Word stemming/lemmatization settings
NLP_SETTINGS = {
    "USE_STEMMING": True,                # Enable word stemming
    "STEM_CACHE_SIZE": 1000,             # Size of the stemming cache
}

# Common question types for specialized handling
QUESTION_TYPES = {
    "YES_NO": ["yes", "no", "y/n", "yes/no", "agree", "consent", "confirm", "accept"],
    "DEMOGRAPHIC": ["gender", "ethnicity", "race", "veteran", "disability", "orientation", 
                   "demographic", "diversity", "identity", "transgender", "lgbtqia"],
    "AUTHORIZATION": ["authorized", "authorization", "eligible", "eligibility", 
                     "sponsorship", "visa", "citizenship", "legally", "green card"],
    "EXPERIENCE": ["experience", "year", "skill", "expertise", "proficiency"],
    "LOCATION": ["where", "location", "city", "state", "country", "address", "remote", "onsite"],
}

# Patterns for extracting numeric values with context
NUMERIC_PATTERNS = [
    (r'\b(\d+)\s*(?:year|yr)[s]?(?:\s+of\s+(?:experience|work))?\b', '{} years'),
    (r'\b(\d+)\s*\+\s*(?:year|yr)[s]?(?:\s+of\s+(?:experience|work))?\b', '{}+ years'),
    (r'\b(\d+)(?:\s*-\s*\d+)?\s*(?:year|yr)[s]?\b', '{} years'),
    (r'\b(\d+)(?:\s*to\s*\d+)?\s*(?:year|yr)[s]?\b', '{} years'),
    (r'\b(\d+)(?:\s*\+)?\s*(?:month|mo)[s]?\b', '{} months'),
    (r'\b(?:salary|compensation|pay)(?:.{0,30})?(\d[\d,]+(?:\.\d+)?)', '${} salary'),
    (r'\b(\d[\d,]+(?:\.\d+)?)(?:.{0,15})?(?:salary|compensation|pay)\b', '${} salary'),
]

# Semantic matching thresholds for option matching
OPTION_MATCH_THRESHOLDS = {
    "EXACT_MATCH": 1.0,           # Threshold for exact matches
    "SEMANTIC_MATCH": 0.4,        # Threshold for semantic similarity
    "FUZZY_MATCH": 0.5,           # Threshold for fuzzy string matching
}

# Weights for semantic similarity components
SEMANTIC_SIMILARITY_WEIGHTS = {
    "STEMMED_OVERLAP": 0.5,       # Weight for stemmed word overlap
    "CONCEPT_OVERLAP": 0.3,       # Weight for key concept matching
    "SEQUENCE_SIMILARITY": 0.2,   # Weight for token sequence similarity
}

# Key concept patterns for semantic matching
KEY_CONCEPT_PATTERNS = {
    "AFFIRMATIVE": ["yes", "agree", "true", "confirm", "accept", "approved", "acknowledged"],
    "NEGATIVE": ["no", "disagree", "false", "reject", "decline", "denied", "not approved"],
    "PRIVACY": ["prefer not", "decline to", "not specify", "private", "confidential", 
               "not disclose", "withhold", "rather not say"],
    "LOCATION": ["onsite", "on-site", "remote", "hybrid", "in-office", "work from home", "wfh"],
    "CURRENT": ["already", "currently", "presently", "now", "at the moment", "existing"]
}