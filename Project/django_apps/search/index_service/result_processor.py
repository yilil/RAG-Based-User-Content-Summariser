# Responsible for grouping, merging, and sorting retrieval results, returning final Document collections

from langchain.docstore.document import Document
from typing import List, Dict
import re
from collections import Counter
import json
import logging
from django.conf import settings
from .rating_processor import RatingProcessor
from .result_formatter import ResultFormatter
from .score_calculator import ScoreCalculator
from .prompt_templates import PromptBuilder
from search_process.prompt_sender.sender import send_prompt_to_gemini

logger = logging.getLogger(__name__)

class ResultProcessor:
    def __init__(self):
        self.rating_processor = RatingProcessor()
        self.result_formatter = ResultFormatter()
        self.score_calculator = ScoreCalculator()
        self.prompt_builder = PromptBuilder()

    def process_recommendations(self, documents: List[Document], query: str, top_k: int) -> str:
        """
        [DEMO SECTION - Recommendation Processor Logic] 
        Process recommendation queries, directly return formatted HTML content
        
        This method implements the specialized recommendation processing logic mentioned in the demo:
        - Extraction Process: Uses LLM to extract recommendation items from retrieved documents
        - Scoring Algorithm: Calculates comprehensive scores combining sentiment, upvotes, mentions
        - Final Output: Returns ranked recommendations with detailed explanations
        """
        try:
            # [DEMO SECTION 1] Step 1: Extract items + qualitative sentiment labels from LLM
            prompt = self.prompt_builder.build_extraction_prompt(documents, query)
            response = self._call_llm_for_extraction(prompt)
            extracted_items = json.loads(response)
            
            # [DEMO SECTION 2+3] Step 2+3: Local aggregation and sentiment analysis
            recommendations = []
            for item_idx, item in enumerate(extracted_items, 1):
                if 'name' not in item or 'posts' not in item:
                    logger.warning(f"Skipping invalid item: {item}")
                    continue

                posts = item['posts']
                total_upvotes = 0  # Initialize total upvotes

                print(f"\n=== Debug 2: Processing Item {item_idx} ===")
                print(f"Item name: {item['name']}")
                
                # Process upvotes/votes for different platforms
                for post_idx, p in enumerate(posts, 1):
                    # Get platform information
                    platform = p.get('platform', '').lower()
                    
                    # Get corresponding upvotes/votes based on different platforms
                    if platform == 'reddit':
                        upvotes = p.get('upvotes', 0)
                    elif platform == 'stackoverflow':
                        upvotes = p.get('vote_score', 0)
                    elif platform == 'rednote':
                        upvotes = p.get('likes', 0)
                    else:
                        # Default: try all possible fields
                        upvotes = p.get('upvotes', p.get('vote_score', p.get('likes', 0)))
                    
                    # Use unified upvotes field
                    p['upvotes'] = upvotes
                    total_upvotes += upvotes
                    
                    print(f"\nPost {post_idx}:")
                    print(f"Platform: {platform}")
                    print(f"Content (first 50 chars): {p.get('content', '')[:50]}...")
                    print(f"Upvotes: {upvotes}")
                    print(f"Current total_upvotes: {total_upvotes}")
                print("=== End Debug 2 ===\n")

                # [DEMO SECTION 3] Map qualitative sentiment → numeric once per post
                numeric_ratings = []
                for p in posts:
                    sent = p.get('sentiment', '').lower()
                    num = self.rating_processor.get_numeric_rating(sent)
                    p['numeric_rating'] = num
                    numeric_ratings.append(num)

                avg_rating = sum(numeric_ratings) / len(numeric_ratings) if numeric_ratings else 3.0
                mentions = len(posts)

                # Sentiment counts by qualitative labels
                labels = [p.get('sentiment', 'neutral').lower() for p in posts]
                counter = Counter(labels)
                sentiment_counts = {
                    'positive': counter.get('very positive',0) + counter.get('positive',0),
                    'neutral': counter.get('neutral',0),
                    'negative': counter.get('negative',0) + counter.get('very negative',0)
                }

                print(f"\n=== Debug 3: Final Item {item_idx} Summary ===")
                print(f"Item name: {item['name']}")
                print(f"Total upvotes: {total_upvotes}")
                print(f"Number of posts: {len(posts)}")
                print("Posts with likes:")
                for post_idx, post in enumerate(posts, 1):
                    print(f"Post {post_idx}: {post.get('upvotes', 0)} likes")
                print("=== End Debug 3 ===\n")

                recommendations.append({
                    'name': item['name'],
                    'total_upvotes': total_upvotes,
                    'avg_rating': round(avg_rating, 2),
                    'mentions': mentions,
                    'sentiment_counts': sentiment_counts,
                    'posts': posts,
                    'summary': item.get('summary', 'No summary available')
                })
            
            # [DEMO SECTION 4] Step 4: Score & rank recommendations
            self.score_calculator.calculate_scores(recommendations)
            top_recs = sorted(recommendations, key=lambda r: r['score'], reverse=True)[:top_k]

            # [DEMO SECTION 5] Step 5: Format into HTML using the new ResultFormatter
            return self.result_formatter.format_recommendations(top_recs)
            
        except Exception as e:
            logger.error(f"Error processing recommendations: {e}")
            return "<p>Error occurred while processing recommendations.</p>"
    
    def _call_llm_for_extraction(self, prompt: str) -> str:
        """
        [DEMO SECTION 1] Call LLM for extraction
        
        This method implements the extraction process mentioned in the demo:
        - Uses LLM to extract recommendation items from retrieved documents
        - Each item includes: name, posts with content and engagement metrics, sentiment scores
        - Returns JSON format data for further processing
        """
        try:
            response = send_prompt_to_gemini(prompt, model_name="gemini-2.0-flash")
            response_text = response.text
            
            # 1. First try to extract from json code block
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                if start > 6 and end > start:  # Ensure valid markers found
                    json_str = response_text[start:end].strip()
                    try:
                        # Fix possible invalid escape sequences
                        fixed_json = re.sub(r'\\(?!["\\/bfnrtu]|u[0-9a-fA-F]{4})', r'\\\\', json_str)
                        # Validate JSON
                        recommendations = json.loads(fixed_json)
                        return json.dumps(recommendations, indent=2, ensure_ascii=False)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON from code block: {e}")
            
            # 2. If code block extraction fails, try to extract JSON array directly
            try:
                start = response_text.find("[")
                end = response_text.rfind("]") + 1
                if start >= 0 and end > start:
                    json_str = response_text[start:end].strip()
                    # Fix possible invalid escape sequences
                    fixed_json = re.sub(r'\\(?!["\\/bfnrtu]|u[0-9a-fA-F]{4})', r'\\\\', json_str)
                    recommendations = json.loads(fixed_json)
                    return json.dumps(recommendations, indent=2, ensure_ascii=False)
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to extract JSON array: {e}")
                # Record problem area for debugging
                pos = e.pos if hasattr(e, 'pos') else 0
                error_context = json_str[max(0, pos-30):min(len(json_str), pos+30)] if pos > 0 else "unknown position"
                logger.error(f"Error context: '{error_context}'")
            
            # 3. If all extraction methods fail, log error and return mock data
            logger.error("Failed to extract valid JSON from response")
            logger.debug(f"Raw response: {response_text}")
            
            if settings.DEBUG:
                logger.warning("Using mock data for testing")
                return self.prompt_builder.get_mock_response()
            raise ValueError("Failed to extract valid recommendations from model response")
                
        except Exception as e:
            logger.error(f"Gemini API call failed: {str(e)}")
            if settings.DEBUG:
                logger.warning("Using mock data for testing")
                return self.prompt_builder.get_mock_response()
            raise