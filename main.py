
# Update imports at the top of the file
from dotenv import load_dotenv

# Load environment variables from .env file
print(load_dotenv())
import os
import logging
import argparse
import json
from datetime import datetime
from src.core.application_app import ApplicationApp
from src.core.logger import setup_logger, setup_root_logger

# Import from config
from src.config.config import (
    SEARCH_QUERIES, TIME_FILTER_MAPPING, WORK_TYPE_MAPPING, 
    LOG_LEVEL, APPLICATION_MAPPING, FILE_PATHS
)

# Create session timestamp
session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Get log level from config
log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

# Setup root logger first to capture any uncaught logs
root_logger = setup_root_logger(
    log_level=log_level,
    log_file=FILE_PATHS["ROOT_LOG"],
    add_timestamp=True
)

# Setup main logger
logger = setup_logger(
    "main", 
    log_level=log_level,
    log_file=FILE_PATHS["MAIN_LOG"],
    add_timestamp=True
)

# Log session start
logger.info(f"==================================================")
logger.info(f"=== New Application Session: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
logger.info(f"==================================================")


def validate_time_filter(value):
    """
    Validates and converts time filter input:
    - String values ('day', 'week', 'month', 'any') are returned as is
    - Numeric values are interpreted as minutes and returned with 'r' prefix
    """
    # Use keys from TIME_FILTER_MAPPING instead of hardcoding values
    if value in TIME_FILTER_MAPPING.keys():
        return value
        
    # Try to convert to integer for custom durations (in minutes)
    try:
        minutes = int(value)
        if minutes < 1:
            raise argparse.ArgumentTypeError("Time filter minutes must be a positive number")
        # Return directly with 'r' prefix
        return f"r{minutes}"
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Time filter must be one of {tuple(TIME_FILTER_MAPPING.keys())} or a positive number of minutes"
        )
    

def build_complex_query(query_name):
    """Build a complex LinkedIn search query from predefined components"""
    logger.debug(f"Building complex query for: {query_name}")
    
    if query_name not in SEARCH_QUERIES:
        logger.error(f"Query name not found: {query_name}")
        return None
        
    query_data = SEARCH_QUERIES[query_name]
    
    # Build titles to include
    titles_include = " OR ".join([f'intitle:"*{title.replace(" ", "*")}*"' for title in query_data["titles_include"]])
    logger.debug(f"Titles to include section: {len(query_data['titles_include'])} items")
    
    # Build titles to exclude
    titles_exclude = " OR ".join([f'intitle:"*{title.replace(" ", "*")}*"' for title in query_data["titles_exclude"]])
    logger.debug(f"Titles to exclude section: {len(query_data['titles_exclude'])} items")
    
    # Build skills
    skills = " OR ".join([f'"{skill}"' if " " in skill else skill for skill in query_data["skills_required"]])
    logger.debug(f"Skills section: {len(query_data['skills_required'])} items")
    
    # Build functions
    functions = " OR ".join([f'"{func}"' if " " in func else func for func in query_data["functions_required"]])
    logger.debug(f"Functions section: {len(query_data['functions_required'])} items")
    
    # Combine all parts
    query = f"({titles_include}) AND NOT ({titles_exclude}) AND ({skills}) AND ({functions})"
    
    logger.debug(f"Built complex query with length: {len(query)}")
    return query

def main():
    logger.info("Starting LinkedIn Job Application Automation")
    
    # Parse command line arguments
    logger.debug("Parsing command line arguments")
    parser = argparse.ArgumentParser(description='LinkedIn Job Application Automation')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--search', action='store_true', help='Use search instead of top picks')
    parser.add_argument('--keywords', type=str, default='software engineer', help='Job search keywords or predefined query name')
    parser.add_argument('--location', type=str, default='United States', help='Job search location')
    
    # Work type options
    work_type_group = parser.add_mutually_exclusive_group()
    work_type_group.add_argument('--remote-only', action='store_true', help='Filter for remote jobs only (default)')
    work_type_group.add_argument('--onsite-only', action='store_true', help='Filter for on-site jobs only')
    work_type_group.add_argument('--hybrid-only', action='store_true', help='Filter for hybrid jobs only')
    work_type_group.add_argument('--all-work-types', action='store_true', help='Include all work types (remote, onsite, and hybrid)')
    work_type_group.add_argument('--work-types', type=str, nargs='+', choices=list(WORK_TYPE_MAPPING.keys()), 
                               help='Specify one or more work types')
    
    parser.add_argument('--time-filter', type=validate_time_filter, default='day',
                        help=f'Time filter for jobs: {", ".join(["\"" + k + "\"" for k in TIME_FILTER_MAPPING.keys()])} or a custom number of minutes (e.g. 3600 for last hour)')
    parser.add_argument('--query-file', type=str, help='Path to JSON file with custom search query')
    parser.add_argument('--predefined-query', type=str, choices=list(SEARCH_QUERIES.keys()), 
                        help='Use a predefined complex query')
    args = parser.parse_args()
    
    logger.info(f"Command line arguments: {vars(args)}")

    remote_only = False  # Default to remote jobs
    work_types = None

    if args.remote_only:
        remote_only = True
        work_types = ['remote']
        logger.info("Filtering for remote jobs only")
    elif args.onsite_only:
        work_types = ['onsite']
        logger.info("Filtering for on-site jobs only")
    elif args.hybrid_only:
        work_types = ['hybrid']
        logger.info("Filtering for hybrid jobs only")
    elif args.all_work_types:
        work_types = list(WORK_TYPE_MAPPING.keys())
        logger.info(f"Including all work types: {', '.join(work_types)}")
    elif args.work_types:
        work_types = args.work_types
        logger.info(f"Using specified work types: {work_types}")
    else:
        # Default to all work types if nothing else specified
        work_types = list(WORK_TYPE_MAPPING.keys())
        logger.info(f"Using default: all job types")

    try:
        # Check for required environment variables
        # Use keys from the LinkedIn configuration instead of hardcoding
        linkedin_config = APPLICATION_MAPPING.get("linkedin", {})
        required_env_vars = []
        
        # Dynamically determine required env vars from config
        if linkedin_config.get("username") is None:
            required_env_vars.append('USERNAME')
        if linkedin_config.get("password") is None:
            required_env_vars.append('PASSWORD')
        
        # Always require browser data
        if not os.getenv('BROWSER_DATA'):
            required_env_vars.append('BROWSER_DATA')
        
        if required_env_vars:
            logger.error(f"Missing required environment variables: {', '.join(required_env_vars)}")
            return 1
        
        # Process query if provided
        search_keywords = args.keywords
        logger.debug(f"Initial search keywords: {search_keywords}")
        
        # Check for predefined query
        if args.predefined_query:
            logger.info(f"Using predefined query: {args.predefined_query}")
            complex_query = build_complex_query(args.predefined_query)
            if complex_query:
                logger.info(f"Built complex query with approximate length: {len(complex_query)}")
                search_keywords = complex_query
            else:
                logger.error(f"Failed to build complex query for: {args.predefined_query}")
                return 1
                
        # Check for query file
        if args.query_file:
            logger.info(f"Loading query from file: {args.query_file}")
            try:
                with open(args.query_file, 'r') as f:
                    query_data = json.load(f)
                    if "query" in query_data:
                        search_keywords = query_data["query"]
                        logger.info(f"Loaded query from file with approximate length: {len(search_keywords)}")
                    else:
                        logger.error(f"Query file does not contain 'query' key: {args.query_file}")
            except Exception as e:
                logger.error(f"Error loading query file: {e}")
                return 1
        
        # Initialize the application
        logger.info("Initializing ApplicationApp")
        with ApplicationApp(application_type="linkedin", headless=args.headless, time_filter=args.time_filter) as app:
            logger.info(f"ApplicationApp initialized with time_filter={args.time_filter}, headless={args.headless}")
            logger.info(f"Work types: {work_types}")
            
            # Either search for jobs or use top picks
            if args.search or args.predefined_query or args.query_file:
                # If a query is provided, we should use search even if --search isn't explicitly specified
                formatted_work_types = '/'.join(work_types) if work_types else 'any'
                logger.info(f"Searching for jobs matching criteria in {args.location} with work types: {formatted_work_types}")
                app.search_jobs(search_keywords, args.location, remote_only, work_types)
            else:
                logger.info(f"Finding top job picks with Easy Apply (work types: {work_types})")
                app.find_top_picks_and_easy_apply_jobs(remote_only, work_types)
                
            # Start applying to jobs
            logger.info("Starting application process")
            app.apply()
            
            logger.info("Job application process completed successfully")
            return 0
            
    except Exception as e:
        logger.error(f"Application failed with error", exc_info=True)
        return 1
    finally:
        # Log session end
        logger.info(f"==================================================")
        logger.info(f"=== Application Session Ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
        logger.info(f"==================================================")

if __name__ == "__main__":
    exit_code = main()
    logger.info(f"Exiting with code: {exit_code}")
    exit(exit_code)