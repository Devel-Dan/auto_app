import os
import json
import difflib
import logging
import time
from google import genai
from google.genai import types
import pathlib
import re
from collections import Counter
import string

# Import Porter Stemmer for stemming
try:
    from nltk.stem import PorterStemmer
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

from src.config.config import (
    FORM_RESPONSES_PATH, DEFAULT_RESUME_PATH, GEMINI_API_KEY, FILE_PATHS, 
    PROMPTS, FORM_STOP_WORDS, FORM_IMPORTANT_KEYWORDS_FLAT, FORM_COMPOUND_PATTERNS,
    MATCH_THRESHOLDS, MATCH_WEIGHTS, NLP_SETTINGS, QUESTION_TYPES, NUMERIC_PATTERNS,
    FORM_IMPORTANT_KEYWORDS, OPTION_MATCH_THRESHOLDS, SEMANTIC_SIMILARITY_WEIGHTS, KEY_CONCEPT_PATTERNS 
)

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
        
        self.logger = logger
        
        # Initialize stemmer if NLTK is available
        self.stemmer = None
        self.stem_cache = {}
        if NLTK_AVAILABLE and NLP_SETTINGS["USE_STEMMING"]:
            self.stemmer = PorterStemmer()
            logger.info("NLTK stemmer initialized")
        
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
        Find best matching response using enhanced semantic matching.
        
        Args:
            question_text (str): The question to find a match for
            options (list, optional): Available options for the answer
            error (str, optional): Error context if any
            
        Returns:
            Best matching answer or None
        """
        logger.info(f"\nLooking for match for question: {question_text}")
        if options:
            logger.info(f"Available options: {options}")
        
        # If an error is provided, skip using cached responses
        if error:
            logger.info(f"Error context provided: '{error}'. Skipping cached responses.")
            return None
            
        # Clean and normalize the question text
        question_text = self.clean_question_text(question_text.lower().strip())
        
        # Determine question type for specialized handling
        question_type = self._determine_question_type(question_text)
        logger.info(f"Detected question type: {question_type}")
        
        # Direct match
        if question_text in self.responses:
            answer = self.responses[question_text]["answer"]
            logger.info(f"Found exact match! Answer: {answer}")
            
            # If options provided, find closest match
            if options:
                matched_option = self._find_closest_option(answer, options, question_type)
                logger.info(f"Matched to option: {matched_option}")
                return matched_option
            return answer
        
        # Extract keywords with enhanced method
        question_keywords = self._extract_keywords(question_text)
        logger.debug(f"Keywords from question: {question_keywords}")
        
        # Find potential matches based on keywords
        potential_matches = []
        
        for saved_question in self.responses:
            saved_keywords = self._extract_keywords(saved_question.lower())
            
            # Skip if no keywords are available
            if not saved_keywords or not question_keywords:
                continue
                
            # Calculate similarity with improved methods
            keyword_similarity = self._calculate_keyword_similarity(question_keywords, saved_keywords)
            string_similarity = difflib.SequenceMatcher(None, question_text, saved_question.lower()).ratio()
            
            # Calculate weighted combined score
            combined_score = (
                keyword_similarity * MATCH_WEIGHTS["KEYWORD_WEIGHT"] + 
                string_similarity * MATCH_WEIGHTS["STRING_WEIGHT"]
            )
            
            # Apply context-based adjustments
            combined_score = self._apply_context_adjustments(
                combined_score, question_text, saved_question, question_type
            )
            
            # Add to potential matches if score is above threshold
            if combined_score > MATCH_THRESHOLDS["KEYWORD_MATCH_THRESHOLD"]:
                potential_matches.append((saved_question, combined_score))
        
        # Sort potential matches by score
        potential_matches.sort(key=lambda x: x[1], reverse=True)
        
        # Log the top matches for debugging
        if potential_matches:
            logger.debug("Top potential matches:")
            for i, (match, score) in enumerate(potential_matches[:3], 1):
                logger.debug(f"  {i}. '{match}' (score: {score:.2f})")
        
        # If we have potential matches
        if potential_matches:
            best_match, score = potential_matches[0]
            
            # Accept match if the score is good enough
            if score > MATCH_THRESHOLDS["COMBINED_SCORE_THRESHOLD"]:
                answer = self.responses[best_match]["answer"]
                logger.info(f"Found semantic match '{best_match}' with score {score:.2f}")
                logger.info(f"Answer: {answer}")
                
                if options:
                    matched_option = self._find_closest_option(answer, options, question_type)
                    logger.info(f"Matched to option: {matched_option}")
                    return matched_option
                return answer
        
        # Fall back to traditional fuzzy matching with improved threshold
        logger.info("Semantic matching below threshold, trying traditional fuzzy matching...")
        best_ratio = 0
        best_match = None
        
        for saved_question in self.responses:
            ratio = difflib.SequenceMatcher(None, question_text, saved_question.lower()).ratio()
            logger.debug(f"Comparing with '{saved_question}' - similarity: {ratio:.2f}")
            
            if ratio > MATCH_THRESHOLDS["FUZZY_MATCH_THRESHOLD"] and ratio > best_ratio:
                best_ratio = ratio
                best_match = saved_question
                
        if best_match:
            answer = self.responses[best_match]["answer"]
            logger.info(f"Found fuzzy match '{best_match}' with similarity {best_ratio:.2f}")
            logger.info(f"Answer: {answer}")
            
            if options:
                matched_option = self._find_closest_option(answer, options, question_type)
                logger.info(f"Matched to option: {matched_option}")
                return matched_option
            return answer
        
        logger.info("No suitable match found in database")
        return None

    def _extract_keywords(self, text):
        """
        Extract important keywords from a question with enhanced semantic understanding.
        
        Args:
            text (str): Text to extract keywords from
            
        Returns:
            List of extracted keywords
        """
        # Handle None or empty text
        if not text:
            return []

        # Ensure text is a string
        text = str(text).lower()

        # Remove punctuation and split into words
        words = re.findall(r'\b\w+\b', text)

        # Apply stemming if available
        if self.stemmer:
            stemmed_words = []
            for word in words:
                # Use cache to avoid re-stemming
                if word in self.stem_cache:
                    stemmed_word = self.stem_cache[word]
                else:
                    stemmed_word = self.stemmer.stem(word)
                    # Cache the result with size limit
                    if len(self.stem_cache) < NLP_SETTINGS["STEM_CACHE_SIZE"]:
                        self.stem_cache[word] = stemmed_word
                stemmed_words.append(stemmed_word)
            words = stemmed_words

        # Remove common stop words
        keywords = [word for word in words if word not in FORM_STOP_WORDS and len(word) > 1]

        # Check for important keywords that might have been filtered out
        for term in FORM_IMPORTANT_KEYWORDS_FLAT:
            if term in text and term not in keywords:
                keywords.append(term)

        # Add compound terms as single concepts
        for pattern in FORM_COMPOUND_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                # Get the full match (not just capture groups)
                full_matches = re.finditer(pattern, text)
                for match in full_matches:
                    full_term = match.group(0)
                    if full_term not in keywords:
                        keywords.append(full_term)

        # Add numeric values with context (e.g., "5 years")
        # This helps with experience/year questions
        for pattern, format_str in NUMERIC_PATTERNS:
            num_matches = re.finditer(pattern, text)
            for match in num_matches:
                number = match.group(1)
                # Clean up the number (remove commas, etc.)
                number = number.replace(',', '')
                full_match = match.group(0)
                formatted_term = format_str.format(number)
                if formatted_term not in keywords:
                    keywords.append(formatted_term)

        # Add question type markers based on content analysis
        for q_type, indicators in QUESTION_TYPES.items():
            if any(indicator in text for indicator in indicators):
                keywords.append(f"{q_type.lower()}_question")

        # Add 'required' tag if the question indicates it's required
        if any(term in text for term in ['required', 'must', 'necessary', 'mandatory']):
            keywords.append('required_field')

        # Add category-based keywords
        for category, category_keywords in FORM_IMPORTANT_KEYWORDS.items():
            if any(kw in text for kw in category_keywords):
                keywords.append(f"category_{category.lower()}")

        # Log the extracted keywords for debugging
        logger.debug(f"Extracted keywords from '{text[:50]}...': {keywords}")

        return keywords
    
    def _calculate_keyword_similarity(self, keywords1, keywords2):
        """
        Calculate semantic similarity between keyword sets using weighted approach.
        
        Args:
            keywords1 (list): First set of keywords
            keywords2 (list): Second set of keywords
            
        Returns:
            Similarity score (0-1)
        """
        if not keywords1 or not keywords2:
            return 0
        
        # Count keywords and their frequencies for TF-IDF like approach
        counter1 = Counter(keywords1)
        counter2 = Counter(keywords2)
        
        # Calculate weight for each keyword based on importance
        weighted_matches = 0
        total_weight = 0
        
        # First, identify common keywords
        common_keywords = set(keywords1) & set(keywords2)
        
        # For each common keyword, calculate its contribution
        for keyword in common_keywords:
            # Base weight is 1.0
            weight = 1.0
            
            # Skip if keyword is not a string (could be a boolean or other type)
            if not isinstance(keyword, str):
                continue
                
            # Give more weight to important keywords
            if any(keyword.startswith(f"category_") for category in FORM_IMPORTANT_KEYWORDS.keys()):
                weight = 2.0
            
            # Give more weight to question type indicators
            if any(keyword.endswith("_question") for q_type in QUESTION_TYPES.keys()):
                weight = 2.5
            
            # Give more weight to numeric patterns (especially years of experience)
            if keyword.endswith("years") or keyword.endswith("months"):
                weight = 3.0
                
            # Calculate contribution based on frequency and weight
            contribution = weight * min(counter1[keyword], counter2[keyword])
            weighted_matches += contribution
            
        # Calculate total possible weight (from unique keywords in both sets)
        all_keywords = set(keywords1) | set(keywords2)
        for keyword in all_keywords:
            # Skip if keyword is not a string
            if not isinstance(keyword, str):
                continue
                
            # Use same weighting as above
            weight = 1.0
            
            if isinstance(keyword, str):
                if any(keyword.startswith(f"category_") for category in FORM_IMPORTANT_KEYWORDS.keys()):
                    weight = 2.0
                if any(keyword.endswith("_question") for q_type in QUESTION_TYPES.keys()):
                    weight = 2.5
                if keyword.endswith("years") or keyword.endswith("months"):
                    weight = 3.0
                    
            # Add max frequency from either set
            total_weight += weight * max(counter1.get(keyword, 0), counter2.get(keyword, 0))
        
        # Calculate similarity
        if total_weight > 0:
            return weighted_matches / total_weight
        return 0
        
    def _apply_context_adjustments(self, score, question_text, saved_question, question_type):
        """
        Apply context-based adjustments to the similarity score.
        
        Args:
            score (float): Base similarity score
            question_text (str): Current question
            saved_question (str): Saved question from database
            question_type (str): Determined question type
            
        Returns:
            Adjusted similarity score
        """
        # Start with the base score
        adjusted_score = score
        
        # Give bonus for matching question types
        saved_question_type = self._determine_question_type(saved_question)
        if question_type == saved_question_type and question_type != "UNKNOWN":
            adjusted_score += 0.1
            logger.debug(f"Applied +0.1 bonus for matching question type: {question_type}")
        
        # Give bonus for questions with similar length
        length_ratio = min(len(question_text), len(saved_question)) / max(len(question_text), len(saved_question))
        if length_ratio > 0.8:
            adjusted_score += 0.05
            logger.debug(f"Applied +0.05 bonus for similar question length")
        
        # Apply job context bonus if job description is available
        if self.current_job_description:
            # Extract relevant keywords from job description
            job_keywords = self._extract_job_context_keywords()
            
            # Check if both questions share keywords with job context
            q1_job_matches = self._count_job_keyword_matches(question_text, job_keywords)
            q2_job_matches = self._count_job_keyword_matches(saved_question, job_keywords)
            
            # If both questions match job context similarly, give bonus
            if q1_job_matches > 0 and q2_job_matches > 0:
                job_context_similarity = min(q1_job_matches, q2_job_matches) / max(q1_job_matches, q2_job_matches)
                if job_context_similarity > 0.7:
                    adjusted_score += 0.1
                    logger.debug(f"Applied +0.1 bonus for matching job context")
        
        # Special handling for specific question types
        if question_type == "EXPERIENCE":
            # Extract years from both questions
            years_current = self._extract_years(question_text)
            years_saved = self._extract_years(saved_question)
            
            # If both have numeric years and they're close, give bonus
            if years_current and years_saved:
                years_diff = abs(years_current - years_saved)
                if years_diff <= 1:
                    adjusted_score += 0.15
                    logger.debug(f"Applied +0.15 bonus for similar experience years")
                elif years_diff <= 3:
                    adjusted_score += 0.05
                    logger.debug(f"Applied +0.05 bonus for close experience years")
        
        # Cap the score at 1.0
        return min(adjusted_score, 1.0)
    
    def _determine_question_type(self, question_text):
        """
        Determine the type of question for specialized handling.
        
        Args:
            question_text (str): Question to analyze
            
        Returns:
            String indicating question type
        """
        question_text = question_text.lower()
        
        # Check each question type based on indicators
        for q_type, indicators in QUESTION_TYPES.items():
            if any(indicator in question_text for indicator in indicators):
                return q_type
        
        # Default to unknown
        return "UNKNOWN"
    
    def _extract_years(self, text):
        """
        Extract years of experience from text if present.
        
        Args:
            text (str): Text to analyze
            
        Returns:
            Numeric value of years or None
        """
        # Patterns to match various forms of years of experience
        patterns = [
            r'(\d+)\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|work)',
            r'(\d+)\s*\+\s*(?:years?|yrs?)',
            r'(\d+)\s*(?:years?|yrs?)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    pass
        
        return None
    
    def _extract_job_context_keywords(self):
        """
        Extract relevant keywords from job description for context.
        
        Returns:
            List of job context keywords
        """
        if not self.current_job_description:
            return []
        
        # Use the same keyword extraction for job description
        return self._extract_keywords(self.current_job_description)
    
    def _count_job_keyword_matches(self, text, job_keywords):
        """
        Count number of job context keywords that appear in a text.
        
        Args:
            text (str): Text to check against job keywords
            job_keywords (list): Keywords from job description
            
        Returns:
            Count of matching keywords
        """
        text = text.lower()
        matches = 0
        
        for keyword in job_keywords:
            if keyword in text:
                matches += 1
        
        return matches

    def _find_closest_option(self, answer, options, question_type="UNKNOWN"):
        """
        Find the closest matching option primarily using NLP capabilities.
        """
        logger.info(f"\nFinding closest option to answer: {answer}")
        logger.info(f"Available options: {options}")
        logger.debug(f"Question type: {question_type}")
        
        if not options:
            return answer
        
        answer_lower = str(answer).lower().strip()
        
        # 1. Exact match check first (fastest)
        for option in options:
            option_lower = str(option).lower().strip()
            if answer_lower == option_lower:
                logger.info(f"Exact match found! Answer '{answer}' matches option '{option}'")
                return option
        
        # 2. NLP-based semantic matching
        if self.stemmer:
            # Process answer for semantic comparison
            answer_tokens = self._process_text_for_semantic_matching(answer_lower)
            
            best_match = None
            best_score = 0
            
            for option in options:
                option_lower = str(option).lower().strip()
                option_tokens = self._process_text_for_semantic_matching(option_lower)
                
                # Calculate composite semantic similarity score
                similarity = self._calculate_semantic_similarity(answer_tokens, option_tokens)
                
                logger.debug(f"Semantic similarity between '{answer}' and '{option}': {similarity:.2f}")
                
                if similarity > best_score:
                    best_score = similarity
                    best_match = option
            
            # Use threshold from config
            if best_score > OPTION_MATCH_THRESHOLDS["SEMANTIC_MATCH"]:
                logger.info(f"Semantic match found! Answer '{answer}' matched to option '{best_match}' with score {best_score:.2f}")
                return best_match
        
        # 3. Fuzzy string matching as fallback
        best_option = None
        best_ratio = 0
        
        for option in options:
            ratio = difflib.SequenceMatcher(None, answer_lower, str(option).lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_option = option
        
        if best_ratio > OPTION_MATCH_THRESHOLDS["FUZZY_MATCH"]:
            logger.info(f"String similarity match! Answer '{answer}' matched to option '{best_option}' with score {best_ratio:.2f}")
            return best_option
        
        # 4. Containment matching as last resort
        for option in options:
            option_lower = str(option).lower().strip()
            if answer_lower in option_lower or option_lower in answer_lower:
                logger.info(f"Containment match! Answer '{answer}' related to option '{option}'")
                return option
        
        logger.info("No option matched above threshold")
        return None

    def _process_text_for_semantic_matching(self, text):
        """
        Process text for semantic matching using NLP techniques.
        
        Returns:
            dict: Contains processed text information including:
                - stemmed_words: List of stemmed content words
                - tokens: Original tokens 
                - key_concepts: Identified key concepts
        """
        # Split into tokens
        tokens = re.findall(r'\b\w+\b', text)
        
        # Remove stop words
        content_words = [w for w in tokens if w not in FORM_STOP_WORDS]
        
        # Apply stemming
        stemmed_words = []
        if self.stemmer:
            for word in content_words:
                if word in self.stem_cache:
                    stemmed_word = self.stem_cache[word]
                else:
                    stemmed_word = self.stemmer.stem(word)
                    if len(self.stem_cache) < NLP_SETTINGS["STEM_CACHE_SIZE"]:
                        self.stem_cache[word] = stemmed_word
                stemmed_words.append(stemmed_word)
        else:
            stemmed_words = content_words
        
        # Identify key concepts using patterns from config
        key_concepts = set()
        
        # Check for concept patterns
        for concept, patterns in KEY_CONCEPT_PATTERNS.items():
            if any(pattern in text for pattern in patterns):
                key_concepts.add(concept.lower())
        
        # Add numeric values
        numbers = re.findall(r'\b\d+\b', text)
        for num in numbers:
            key_concepts.add(f"numeric_{num}")
        
        return {
            "stemmed_words": stemmed_words,
            "tokens": tokens,
            "key_concepts": key_concepts
        }

    def _calculate_semantic_similarity(self, text1_data, text2_data):
        """
        Calculate semantic similarity between two processed texts.
        
        Args:
            text1_data (dict): Processed data for first text
            text2_data (dict): Processed data for second text
            
        Returns:
            float: Similarity score between 0 and 1
        """
        # Component 1: Stemmed word overlap (Jaccard similarity)
        stemmed1 = text1_data["stemmed_words"]
        stemmed2 = text2_data["stemmed_words"]
        
        stemmed_overlap = 0
        if stemmed1 and stemmed2:
            common_stems = set(stemmed1) & set(stemmed2)
            all_stems = set(stemmed1) | set(stemmed2)
            if all_stems:
                stemmed_overlap = len(common_stems) / len(all_stems)
        
        # Component 2: Key concept matching
        concepts1 = text1_data["key_concepts"]
        concepts2 = text2_data["key_concepts"]
        
        concept_overlap = 0
        if concepts1 and concepts2:
            common_concepts = concepts1 & concepts2
            all_concepts = concepts1 | concepts2
            if all_concepts:
                concept_overlap = len(common_concepts) / len(all_concepts)
        
        # Component 3: Token sequence similarity
        sequence_similarity = difflib.SequenceMatcher(
            None, 
            " ".join(text1_data["tokens"]), 
            " ".join(text2_data["tokens"])
        ).ratio()
        
        # Weighted combination of components using weights from config
        combined_score = (
            (stemmed_overlap * SEMANTIC_SIMILARITY_WEIGHTS["STEMMED_OVERLAP"]) + 
            (concept_overlap * SEMANTIC_SIMILARITY_WEIGHTS["CONCEPT_OVERLAP"]) + 
            (sequence_similarity * SEMANTIC_SIMILARITY_WEIGHTS["SEQUENCE_SIMILARITY"])
        )
        
        return combined_score

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
                matched_option = self._find_closest_option(answer, options, self._determine_question_type(question_text))
                logger.info(f"Matched to option: {matched_option}")
                return matched_option
            return answer

        except Exception as e:
            logger.error(f"Error getting gemini response: {e}")
            return None
