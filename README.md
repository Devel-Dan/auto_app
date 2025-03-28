# LinkedIn Job Application Automation

An automated tool that helps you apply to LinkedIn "Easy Apply" jobs based on your custom criteria and resume.

## Overview

This tool automates the process of applying to LinkedIn jobs that use the "Easy Apply" feature. It can:

- Search for jobs based on custom keywords, location, and work type preferences
- Filter jobs based on customizable criteria
- Generate custom resumes tailored to each job description using Gemini AI
- Automatically fill out application forms
- Apply to multiple jobs in a single session

## Features

- **Intelligent Form Filling**: Automatically fills application forms with appropriate responses
- **Custom Resume Generation**: Creates tailored resumes for each job using AI
- **Flexible Job Search**: Search by keywords or use complex predefined queries
- **Work Type Filtering**: Filter for remote, on-site, hybrid, or any combination
- **Time-Based Filtering**: Focus on recently posted jobs (past 24 hours, week, or month)
- **Headless Operation**: Run in the background without a visible browser (optional)
- **Comprehensive Logging**: Detailed logs of all operations for debugging and tracking

## Installation

### Prerequisites

- Python 3.8 or higher
- A LinkedIn account
- Google Gemini API key for resume customization

### Setup

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/linkedin-job-automation.git
   cd linkedin-job-automation
   ```

2. Install the package and dependencies:
   ```
   pip install -e .
   ```
   
   Or install dependencies directly:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with your credentials:
   ```
   USERNAME=your_linkedin_email
   PASSWORD=your_linkedin_password
   BROWSER_DATA=/path/to/browser/user/data/directory
   GEMINI_API_KEY=your_gemini_api_key
   DEFAULT_RESUME_PATH=/path/to/your/default/resume.pdf
   ```

## Usage

### Basic Usage

Run with default settings (searches "software engineer" jobs posted in the last 24 hours):

```
python main.py
```

### Custom Search

Search for specific job titles in a specific location:

```
python main.py --search --keywords "python developer" --location "San Francisco"
```

### Work Type Filtering

Filter for specific work arrangements:

```
python main.py --remote-only
python main.py --onsite-only
python main.py --hybrid-only
python main.py --all-work-types
python main.py --work-types remote hybrid
```

### Time Filtering

Specify how recent the job postings should be:

```
python main.py --time-filter day    # Last 24 hours (default)
python main.py --time-filter week   # Last week
python main.py --time-filter month  # Last month
python main.py --time-filter any    # Any time 
python main.py --time-filter 3600   # Last hour (3600 minutes)
```

### Using Predefined Complex Queries

Use built-in complex search queries:

```
python main.py --predefined-query default
```

### Headless Mode

Run without displaying the browser:

```
python main.py --headless
```

## Project Structure

```
linkedin-job-automation/
├── src/
│   ├── core/
│   │   ├── application_app.py    # Main application class
│   │   └── logger.py             # Logging configuration
│   ├── handlers/
│   │   ├── form_handler.py       # Form field processing
│   │   └── custom_resume.py      # Resume customization
│   ├── managers/
│   │   ├── application_manager.py    # Job application workflow
│   │   ├── authentication_manager.py # LinkedIn authentication
│   │   ├── browser_manager.py        # Browser control
│   │   ├── form_manager.py           # Form responses
│   │   └── job_search_manager.py     # Job searching and filtering
├── main.py                       # Entry point script
├── logs/                         # Application logs (auto-generated)
├── custom_resumes/               # Generated custom resumes (auto-generated)
├── setup.py                      # Package installation configuration
├── requirements.txt              # Project dependencies
└── README.md                     # This file
```

## Customization

### Form Responses

To customize default answers for application questions, edit the `form_responses.json` file. The tool will automatically create this file if it doesn't exist.

### Job Filters

Edit the `job_filters` list in `application_app.py` to modify which job titles are automatically filtered out.

### Predefined Queries

Modify the `SEARCH_QUERIES` dictionary in `main.py` to create your own predefined complex queries.

## Notes

- This tool is for educational and personal use only
- Using automation tools may violate LinkedIn's Terms of Service
- Be responsible with your usage and respect rate limits
- Only your customized information will be submitted in job applications

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.