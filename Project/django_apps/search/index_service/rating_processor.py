from typing import Dict
import logging

logger = logging.getLogger(__name__)

class RatingProcessor:
    """Handles mapping of qualitative sentiment labels to numeric ratings."""

    def __init__(self):
        # Static mapping of sentiment labels to numeric ratings
        self.mapping: Dict[str, int] = {
            "very positive": 5,
            "positive": 4,
            "neutral": 3,
            "negative": 2,
            "very negative": 1,
        }
        # Reverse mapping for text representation
        self.rating_to_sentiment_text: Dict[int, str] = {
            5: "Very Positive",
            4: "Positive",
            3: "Neutral",
            2: "Negative",
            1: "Very Negative"
        }

    def get_numeric_rating(self, sentiment: str) -> int:
        """Get numeric rating for a sentiment label."""
        # Default to neutral (3) if label not found
        return self.mapping.get(sentiment.lower(), 3)

    def get_sentiment_text(self, rating: int) -> str:
        """Convert a numeric rating (1–5) into sentiment text."""
        return self.rating_to_sentiment_text.get(rating, "Unknown")