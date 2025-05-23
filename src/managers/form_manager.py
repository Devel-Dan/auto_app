import os
import json
import difflib
import logging
import time
from google import genai
from google.genai import types
import pathlib

from src.config.config import (
    FORM_RESPONSES_PATH, DEFAULT_RESUME_PATH, GEMINI_API_KEY, FILE_PATHS, 
    PROMPTS
)

# Setup logger
logger = logging.getLogger(__name__)

# Use values from config
resume_path = DEFAULT_RESUME_PATH
pdf_file = pathlib.Path(resume_path)

class FormResponseManager:
    def __init__(self, json_path=None, headless=False):
        """Simple key-value response manager"""
        self.logger = logger
        self.logger.info("Initializing FormResponseManager")
        self.logger.debug(f"Headless mode: {headless}")
        
        if not headless:
            # Initialize paths and load responses
            self.json_path = self._get_json_path(json_path)
            self.responses = self._load_responses()
        else:
            self.logger.info("Running in headless mode, skipping form responses loading")
            self.responses = {}
            
        self.current_job_description = None
        self.logger.info("FormResponseManager initialization complete")
    
    def _get_json_path(self, json_path):
        """Get the path to the JSON file"""
        potential_paths = FILE_PATHS["FORM_RESPONSES"]
        
        if json_path:
            potential_paths.insert(0, json_path)
            
        env_path = os.getenv('FORM_RESPONSES_PATH')
        if env_path:
            potential_paths.insert(0, env_path)
            
        default_path = FORM_RESPONSES_PATH
        if default_path:
            potential_paths.insert(0, default_path)
        
        # Log potential paths
        self.logger.debug("Potential paths to search:")
        for path in potential_paths:
            self.logger.debug(f"  - {path}")
        
        # Find first existing path or use first potential path
        for path in potential_paths:
            if os.path.exists(path):
                self.logger.info(f"Found existing form responses file: {path}")
                return path
                
        # Use first path and ensure directory exists
        selected_path = potential_paths[0]
        self.logger.warning(f"No existing form responses file found. Will create at: {selected_path}")
        
        # Ensure directory exists
        dir_path = os.path.dirname(selected_path)
        os.makedirs(dir_path, exist_ok=True)
        self.logger.info(f"Created directory for form responses: {dir_path}")
        
        return selected_path
    
    def _load_responses(self):
        """Load responses from JSON file"""
        try:
            with open(self.json_path, 'r') as f:
                responses = json.load(f)
                self.logger.info(f"Loaded {len(responses)} responses from {self.json_path}")
                return responses
        except FileNotFoundError:
            self.logger.warning(f"Response file {self.json_path} not found!")
            # Create an empty file if it doesn't exist
            try:
                with open(self.json_path, 'w') as f:
                    json.dump({}, f)
                self.logger.info(f"Created empty form responses file at {self.json_path}")
                return {}
            except Exception as create_error:
                self.logger.error(f"Error creating response file: {create_error}")
                return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Error decoding JSON in {self.json_path}: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Unexpected error loading responses: {e}")
            return {}
    
    def _save_responses(self):
        """Save responses to JSON file"""
        try:
            with open(self.json_path, 'w') as f:
                json.dump(self.responses, f, indent=2)
            self.logger.info(f"Saved {len(self.responses)} responses to {self.json_path}")
        except Exception as e:
            self.logger.error(f"Error saving responses: {e}")
    
    def clean_question_text(self, question_text):
        """Remove duplicate text and clean up question text"""
        if not question_text:
            return ""
            
        # Check if text is duplicated with a newline
        lines = question_text.split('\n')
        if len(lines) == 2 and lines[0] == lines[1]:
            return lines[0]
            
        # Remove duplicate lines while preserving order
        unique_lines = []
        for line in lines:
            if line and line not in unique_lines:
                unique_lines.append(line)
                
        return '\n'.join(unique_lines)
    
    def normalize_key(self, text):
        """Normalize text to create a consistent key"""
        if not text:
            return ""
        # Convert to lowercase and strip whitespace
        normalized = text.lower().strip()
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        return normalized
    
    def find_best_match(self, question_text, options=None, error=None):
        """
        Simple key-value lookup with Gemini fallback
        
        Args:
            question_text (str): The question to find a match for
            options (list, optional): Available options for the answer
            error (str, optional): Error context if any
            
        Returns:
            Best matching answer or None
        """
        self.logger.info(f"\nLooking for match for question: {question_text}")
        if options:
            self.logger.info(f"Available options: {options}")
        
        # If an error is provided, skip cached responses and go straight to Gemini
        if error:
            self.logger.info(f"Error context provided: '{error}'. Going directly to Gemini.")
            return None
        
        # Clean and normalize the question
        cleaned_question = self.clean_question_text(question_text)
        key = self.normalize_key(cleaned_question)
        
        # Direct lookup
        if key in self.responses:
            answer = self.responses[key]["answer"]
            self.logger.info(f"Found exact match! Answer: {answer}")
            
            # If options provided, find closest match
            if options:
                matched_option = self._find_closest_option(answer, options)
                if matched_option:
                    self.logger.info(f"Matched to option: {matched_option}")
                    return matched_option
                else:
                    # If we can't match to an option, it's likely outdated
                    self.logger.info("Could not match cached answer to current options, will get new response")
                    return None
            return answer
        
        self.logger.info("No match found in database")
        return None
    
    def _find_closest_option(self, answer, options):
        """
        Find the closest matching option using simple string matching
        """
        if not options:
            return answer
            
        answer_lower = str(answer).lower().strip()
        
        # 1. Exact match
        for option in options:
            if str(option).lower().strip() == answer_lower:
                self.logger.debug(f"Exact match found: {option}")
                return option
        
        # 2. Containment match (one contains the other)
        for option in options:
            option_lower = str(option).lower().strip()
            if answer_lower in option_lower or option_lower in answer_lower:
                self.logger.debug(f"Containment match found: {option}")
                return option
        
        # 3. Check for numeric answers matching numeric options
        # This handles cases like "5" matching "5 years" or "$100,000" matching "100000"
        answer_numbers = ''.join(filter(str.isdigit, answer_lower))
        if answer_numbers:
            for option in options:
                option_numbers = ''.join(filter(str.isdigit, str(option).lower()))
                if answer_numbers == option_numbers:
                    self.logger.debug(f"Numeric match found: {option}")
                    return option
        
        # 4. Simple fuzzy match with high threshold
        best_ratio = 0
        best_option = None
        
        for option in options:
            ratio = difflib.SequenceMatcher(None, answer_lower, str(option).lower()).ratio()
            if ratio > best_ratio and ratio > 0.8:  # High threshold for accuracy
                best_ratio = ratio
                best_option = option
        
        if best_option:
            self.logger.info(f"Fuzzy matched '{answer}' to '{best_option}' (score: {best_ratio:.2f})")
            return best_option
            
        self.logger.info(f"Could not match '{answer}' to any option")
        return None
    
    def add_response(self, question_text, answer, options=None, source="manual"):
        """Add or update a response in the database"""
        self.logger.info("\nAdding new response:")
        self.logger.info(f"Question: {question_text}")
        self.logger.info(f"Answer: {answer}")
        if options:
            self.logger.info(f"Options: {options}")
        self.logger.info(f"Source: {source}")
        
        # Clean and normalize the question
        cleaned_question = self.clean_question_text(question_text)
        key = self.normalize_key(cleaned_question)
        
        # Store the response
        self.responses[key] = {
            "answer": answer,
            "options": options,
            "source": source,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "original_question": question_text  # Keep original for debugging
        }
        
        self._save_responses()
    
    def get_gemini_response(self, question_text, options=None, error=None, saves=True):
        """Get response from Gemini and optionally save it"""
        self.logger.info(f"\nGetting Gemini response for question: {question_text}")
        error_text = f"IMPORTANT: {error}!!!" if error else ""
        if options:
            self.logger.info(f"Available options: {options}")
            options_text = f"Available options: {', '.join(str(opt) for opt in options)}"
        else:
            options_text = ""

        try:
            # Format the prompt
            prompt = PROMPTS["FORM_RESPONSE"].format(
                question_text=question_text,
                options_text=options_text,
                job_description=self.current_job_description if self.current_job_description else "no job description given",
                error_text=error_text
            )

            self.logger.info("Sending request to Gemini...")
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=[
                    types.Part.from_bytes(
                        data=pdf_file.read_bytes(),
                        mime_type='application/pdf',
                    ),
                    prompt
                ]
            )
            answer = response.text.strip()
            self.logger.info(f"Gemini's response: {answer}")

            # Save the response for future use
            if saves:
                self.add_response(question_text, answer, options, source="gemini")

            # If options provided, find closest match
            if options:
                matched_option = self._find_closest_option(answer, options)
                if matched_option:
                    self.logger.info(f"Matched to option: {matched_option}")
                    return matched_option
                else:
                    # If Gemini's answer doesn't match any option, log warning
                    self.logger.warning(f"Gemini response '{answer}' doesn't match any available options")
                    # Return the first option as a fallback
                    if options:
                        self.logger.info(f"Using first option as fallback: {options[0]}")
                        return options[0]
                    
            return answer

        except Exception as e:
            self.logger.error(f"Error getting Gemini response: {e}")
            # Return a sensible default if we have options
            if options:
                self.logger.info(f"Returning first option as fallback: {options[0]}")
                return options[0]
            return None
    
    def get_response(self, question_text, options=None, error=None):
        """
        Main entry point for getting responses
        This method provides a simple interface that other code can use
        """
        # Try cache first
        answer = self.find_best_match(question_text, options, error)
        
        if answer:
            return answer
        
        # Not in cache or error provided, get from Gemini
        return self.get_gemini_response(question_text, options, error, saves=True)