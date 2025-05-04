from typing import Dict
import logging
import json
from search_process.prompt_sender.sender import send_prompt_to_gemini

logger = logging.getLogger(__name__)

class RatingProcessor:
    """Handles mapping of qualitative sentiment labels to numeric ratings via a single LLM call."""

    def __init__(self):
        # Local fallback mappings
        self.local_map = {
            "very positive": 5,
            "positive": 4,
            "neutral": 3,
            "negative": 2,
            "very negative": 1
        }
        self.mapping = None
        self.rating_to_sentiment_text = {
            5: "Very Positive",
            4: "Positive",
            3: "Neutral",
            2: "Negative",
            1: "Very Negative"
        }

    def _fetch_numeric_mapping(self) -> Dict[str, int]:
        """Call LLM once to map sentiment labels to numeric ratings."""
        prompt = (
            'Map the following sentiment categories to numeric ratings: '
            'very positive, positive, neutral, negative, very negative. '
            'Return ONLY a JSON object, e.g.: {"very positive":5, ...}.'
        )
        try:
            resp = send_prompt_to_gemini(prompt, model_name="gemini-1.5-flash")
            data = json.loads(resp.text)
            # Validate keys exist
            required = set(self.local_map.keys())
            if required.issubset(data.keys()):
                return data
            else:
                logger.warning("LLM mapping missing keys, using local fallback")
        except Exception as e:
            logger.error(f"Failed to fetch numeric mapping: {e}")
        return self.local_map

    def get_numeric_rating(self, sentiment: str) -> int:
        """Get numeric rating for a sentiment label, fetching mapping once."""
        if self.mapping is None:
            self.mapping = self._fetch_numeric_mapping()
        return self.mapping.get(sentiment.lower(), self.local_map.get(sentiment.lower(), 3))

    def get_sentiment_text(self, rating: int) -> str:
        """Convert a numeric rating (1–5) into sentiment text."""
        return self.rating_to_sentiment_text.get(rating, "Unknown")