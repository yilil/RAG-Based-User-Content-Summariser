from typing import List, Dict

class ScoreCalculator:
    def __init__(self, weights: Dict[str, float] = None):
        """
        Initialize the score calculator with optional custom weights
        [DEMO SECTION 4] - This class handles the scoring algorithm for recommendation items
        """
        self.default_weights = {
            'rating': 0.4,      # Sentiment rating weight
            'upvotes': 0.35,    # Upvotes/likes weight
            'mentions': 0.25    # Mention frequency weight
        }
        self.weights = weights if weights is not None else self.default_weights

    def calculate_scores(self, recs: List[Dict]) -> None:
        """
        [DEMO SECTION 4] Calculate scores for each recommendation item
        
        This method implements the scoring algorithm mentioned in the demo:
        - Combines sentiment analysis results, post upvotes/likes, and mention frequency
        - Normalizes each component to ensure fair comparison
        - Applies weighted fusion to calculate final recommendation scores
        
        Args:
            recs: List of recommendation items to score. Each item should have:
                - avg_rating: float
                - total_upvotes: int
                - mentions: int
                
        The method will add/modify these fields in each item:
            - score: float (the final score)
            - score_components: Dict[str, float] (individual component scores)
        """
        # Find maximum values for normalization
        max_upvotes = max((r['total_upvotes'] for r in recs), default=0)
        # Prevent division by zero
        if max_upvotes == 0:
            max_upvotes = 1
        max_mentions = max((r['mentions'] for r in recs), default=0)
        # Prevent division by zero
        if max_mentions == 0:
            max_mentions = 1
        max_rating = 5.0
        
        # Calculate scores for each recommendation item
        for rec in recs:
            # Normalize each component
            rating_component = self.weights['rating'] * (rec['avg_rating'] / max_rating)
            upvote_component = self.weights['upvotes'] * (rec['total_upvotes'] / max_upvotes)
            mention_component = self.weights['mentions'] * (rec['mentions'] / max_mentions)
            # Calculate total score
            score = rating_component + upvote_component + mention_component    
            # Update recommendation item
            rec['score'] = round(score, 3)
            rec['score_components'] = {
                'rating': round(rating_component, 3),
                'upvotes': round(upvote_component, 3),
                'mentions': round(mention_component, 3)
            } 