import os
import json
import difflib
import logging
import time
from google import genai
from google.genai import types
import pathlib
from src.config.config import FORM_RESPONSES_PATH, DEFAULT_RESUME_PATH, GEMINI_API_KEY, FILE_PATHS, PROMPTS

# Setup logger
logger = logging.getLogger(__name__)

# Use values from config
resume_path = DEFAULT_RESUME_PATH
pdf_file = pathlib.Path(resume_path)

class FormResponseManager:
    def __init__(self, json_path=None, headless=False):
        """
        Initialize FormResponseManager with flexible JSON file path handling.
        
        Args:
            json_path (str, optional): Custom path to form responses JSON file
            headless (bool, optional): Whether running in headless mode
        """
        logger.info("Initializing FormResponseManager")
        logger.debug(f"Headless mode: {headless}")
        
        if not headless:
            # Potential paths to look for the JSON file
            potential_paths = FILE_PATHS["FORM_RESPONSES"]

            
            # Get default path from config
            default_path = FORM_RESPONSES_PATH
            if default_path:
                logger.info(f"Using config FORM_RESPONSES_PATH: {default_path}")
                potential_paths.insert(0, default_path)
            
            # Check environment variable
            env_path = os.getenv('FORM_RESPONSES_PATH')
            if env_path:
                logger.info(f"Found FORM_RESPONSES_PATH environment variable: {env_path}")
                potential_paths.insert(0, env_path)
            
            # If a specific path is passed to the constructor, use it first
            if json_path:
                logger.info(f"Custom json_path provided: {json_path}")
                potential_paths.insert(0, json_path)
            
            # Log potential paths
            logger.debug("Potential paths to search:")
            for path in potential_paths:
                logger.debug(f"  - {path}")
            
            # Find the first existing path
            found_path = None
            for path in potential_paths:
                if os.path.exists(path):
                    found_path = path
                    logger.info(f"Found existing form responses file: {found_path}")
                    break
            
            if found_path:
                self.json_path = found_path
            else:
                # If no existing path is found, use the first potential path and ensure its directory exists
                self.json_path = potential_paths[0]
                logger.warning(f"No existing form responses file found. Will create at: {self.json_path}")
                
                # Ensure directory exists
                dir_path = os.path.dirname(self.json_path)
                os.makedirs(dir_path, exist_ok=True)
                logger.info(f"Created directory for form responses: {dir_path}")
            
            # Log the final chosen path
            logger.info(f"Using form responses path: {self.json_path}")
            
            try:
                # Load responses
                self.responses = self._load_responses()
            except Exception as e:
                logger.error(f"Error loading form responses: {e}")
                # Initialize with an empty dictionary if loading fails
                self.responses = {}
        else:
            logger.info("Running in headless mode, skipping form responses loading")
            self.responses = {}
        
        self.current_job_description = None
        logger.info("FormResponseManager initialization complete")

    def _load_responses(self):
        """Load responses from JSON file."""
        try:
            with open(self.json_path, 'r') as f:
                responses = json.load(f)
                logger.info(f"Loaded {len(responses)} responses from {self.json_path}")
                return responses
        except FileNotFoundError:
            logger.warning(f"Response file {self.json_path} not found!")
            # Create an empty file if it doesn't exist
            try:
                with open(self.json_path, 'w') as f:
                    json.dump({}, f)
                logger.info(f"Created empty form responses file at {self.json_path}")
                return {}
            except Exception as create_error:
                logger.error(f"Error creating response file: {create_error}")
                return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON in {self.json_path}: {e}")
            # Return an empty dictionary if the file is corrupt
            return {}
        except Exception as e:
            logger.error(f"Unexpected error loading responses: {e}")
            return {}

    def _save_responses(self):
        """Save responses to JSON file."""
        try:
            with open(self.json_path, 'w') as f:
                json.dump(self.responses, f, indent=2)
            logger.info(f"Saved {len(self.responses)} responses to {self.json_path}")
        except Exception as e:
            logger.error(f"Error saving responses: {e}")

    def find_best_match(self, question_text, options=None, error=None):
        """
        Find best matching response using keyword matching for better semantic understanding.
        """
        logger.info(f"\nLooking for match for question: {question_text}")
        if options:
            logger.info(f"Available options: {options}")
        
        # If an error is provided, skip using cached responses
        if error:
            logger.info(f"Error context provided: '{error}'. Skipping cached responses.")
            return None
            
        question_text = self.clean_question_text(question_text.lower().strip())
        
        # Direct match
        if question_text in self.responses:
            answer = self.responses[question_text]["answer"]
            logger.info(f"Found exact match! Answer: {answer}")
            
            # If options provided, find closest match
            if options:
                matched_option = self._find_closest_option(answer, options)
                logger.info(f"Matched to option: {matched_option}")
                return matched_option
            return answer
        
        # Extract keywords from the question
        question_keywords = self._extract_keywords(question_text)
        logger.debug(f"Keywords from question: {question_keywords}")
        
        # Find potential matches based on keywords
        potential_matches = []
        
        for saved_question in self.responses:
            saved_keywords = self._extract_keywords(saved_question.lower())
            
            # Calculate keyword match percentage
            if not saved_keywords or not question_keywords:
                continue
                
            # Calculate Jaccard similarity (intersection over union)
            matches = len(set(question_keywords) & set(saved_keywords))
            total = len(set(question_keywords) | set(saved_keywords))
            keyword_similarity = matches / total if total > 0 else 0
            
            # If keywords match well enough, consider this question
            if keyword_similarity > 0.5:
                # Also do a string similarity check as secondary measure
                string_similarity = difflib.SequenceMatcher(None, question_text, saved_question.lower()).ratio()
                
                # Combined score (70% keywords, 30% string)
                combined_score = (keyword_similarity * 0.7) + (string_similarity * 0.3)
                
                potential_matches.append((saved_question, combined_score))
        
        # Sort potential matches by score
        potential_matches.sort(key=lambda x: x[1], reverse=True)
        
        # If we have potential matches
        if potential_matches:
            best_match, score = potential_matches[0]
            
            # Accept match if the score is good enough
            if score > 0.6:
                answer = self.responses[best_match]["answer"]
                logger.info(f"Found keyword match '{best_match}' with score {score:.2f}")
                logger.info(f"Answer: {answer}")
                
                if options:
                    matched_option = self._find_closest_option(answer, options)
                    logger.info(f"Matched to option: {matched_option}")
                    return matched_option
                return answer
        
        # Fall back to traditional fuzzy matching
        logger.info("Keyword matching failed, trying traditional fuzzy matching...")
        best_ratio = 0
        best_match = None
        
        for saved_question in self.responses:
            ratio = difflib.SequenceMatcher(None, question_text, saved_question.lower()).ratio()
            logger.debug(f"Comparing with '{saved_question}' - similarity: {ratio:.2f}")
            
            if ratio > 0.8 and ratio > best_ratio:
                best_ratio = ratio
                best_match = saved_question
                
        if best_match:
            answer = self.responses[best_match]["answer"]
            logger.info(f"Found fuzzy match '{best_match}' with similarity {best_ratio:.2f}")
            logger.info(f"Answer: {answer}")
            
            if options:
                matched_option = self._find_closest_option(answer, options)
                logger.info(f"Matched to option: {matched_option}")
                return matched_option
            return answer
        
        logger.info("No suitable match found in database")
        return None

    def _extract_keywords(self, text):
        """
        Extract important keywords from a question for semantic matching.
        """
        import re
        
        # Remove punctuation and split into words
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Remove common stop words
        stop_words = [
            'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
            'which', 'this', 'that', 'these', 'those', 'then', 'just', 'so', 'than',
            'such', 'both', 'through', 'about', 'into', 'between', 'after', 'since',
            'without', 'within', 'along', 'across', 'behind', 'beyond', 'plus',
            'except', 'but', 'up', 'out', 'around', 'down', 'off', 'above', 'below',
            'to', 'from', 'in', 'on', 'by', 'at', 'for', 'with', 'do', 'does', 'did',
            'have', 'has', 'had', 'am', 'is', 'are', 'was', 'were', 'be', 'been',
            'of', 'you', 'your', 'we', 'our', 'i', 'me', 'my', 'many', 'much'
        ]
        
        keywords = [word for word in words if word not in stop_words and len(word) > 1]
        
        # Special handling for important terms
        important_terms = [
            "python", "java", "javascript", "c++", "c#", "ruby", "php", "experience",
            "programming", "software", "development", "years", "work", "hands-on"
        ]
        
        # Make sure important terms are included
        for term in important_terms:
            if term in text.lower() and term not in keywords:
                keywords.append(term)
        
        return keywords

    def _find_closest_option(self, answer, options):
        """
        Find the closest matching option to the given answer.
        
        Args:
            answer (str): Answer to match
            options (list): Available options
        
        Returns:
            Best matching option or None
        """
        logger.info(f"\nFinding closest option to answer: {answer}")
        logger.info(f"Available options: {options}")
        
        if not options:
            return answer
            
        best_ratio = 0
        best_option = None
        
        for option in options:
            ratio = difflib.SequenceMatcher(None, str(answer).lower(), str(option).lower()).ratio()
            logger.debug(f"Comparing with option '{option}' - similarity: {ratio:.2f}")
            if ratio > best_ratio:
                best_ratio = ratio
                best_option = option
                
        if best_ratio > 0.6:
            logger.info(f"Best matching option: {best_option} (similarity: {best_ratio:.2f})")
            return best_option
        else:
            logger.info("No option matched above threshold")
            return None

    def clean_question_text(self, question_text):
        """
        Remove duplicate text and clean up question text.
        
        Args:
            question_text (str): Text to clean
        
        Returns:
            Cleaned text
        """
        if not question_text:
            return ""

        # Check if text is duplicated with a newline in between
        lines = question_text.split('\n')
        if len(lines) == 2 and lines[0] == lines[1]:
            return lines[0]  # Return just one copy

        # More general solution - split by newlines and remove duplicates
        # while preserving order
        unique_lines = []
        for line in lines:
            if line and line not in unique_lines:  # Skip empty lines
                unique_lines.append(line)

        return '\n'.join(unique_lines)

    def add_response(self, question_text, answer, options=None, source="manual"):
        """
        Add or update a response in the database.
        
        Args:
            question_text (str): Question text
            answer (str): Answer text
            options (list, optional): Available options
            source (str, optional): Source of the response
        """
        logger.info("\nAdding new response:")
        logger.info(f"Question: {question_text}")
        logger.info(f"Answer: {answer}")
        if options:
            logger.info(f"Options: {options}")
        logger.info(f"Source: {source}")
        
        question_text = self.clean_question_text(question_text.lower().strip())
        self.responses[question_text] = {
            "answer": answer,
            "options": options,
            "source": source,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self._save_responses()

    def get_gemini_response(self, question_text, options=None, error=None, saves=True):
        """
        Get response from Gemini and optionally save it.
        """
        logger.info(f"\nGetting gemini response for question: {question_text}")
        error_text = f"IMPORTANT: {error}!!!" if error else ""
        if options:
            logger.info(f"Available options: {options}")
            options_text = f"Available options: {', '.join(options)}"
        else:
            options_text = ""

        try:
            # Format the prompt template from config
            prompt = PROMPTS["FORM_RESPONSE"].format(
                question_text=question_text,
                options_text=options_text,
                job_description=self.current_job_description if self.current_job_description else "no job description given",
                error_text=error_text
            )

            logger.info("Sending request to gemini...")
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
            logger.info(f"Gemini's response: {answer}")

            # Save the response
            if saves:
                self.add_response(question_text, answer, options, source="gemini")

            if options:
                matched_option = self._find_closest_option(answer, options)
                logger.info(f"Matched to option: {matched_option}")
                return matched_option
            return answer

        except Exception as e:
            logger.error(f"Error getting gemini response: {e}")
            return None

# Optional main block for testing
if __name__ == "__main__":
    from generic_application import GenericApplier
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    applier = GenericApplier()
    url = "https://job-boards.greenhouse.io/appliedintuition/jobs/4045057005?gh_jid=4045057005&source=LinkedIn"
    job_description = applier.get_job_description_from_url(url)
    
    test = FormResponseManager(headless=True)
    test.current_job_description = job_description
    
    answer = test.get_gemini_response(
        "What is the most impactful thing you've ever done for a business or organization? 100 words", 
        saves=False
    )