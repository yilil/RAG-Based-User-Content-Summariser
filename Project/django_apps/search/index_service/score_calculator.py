from typing import List, Dict

class ScoreCalculator:
    def __init__(self, weights: Dict[str, float] = None):
        """Initialize the score calculator with optional custom weights"""
        self.default_weights = {
            'rating': 0.4,      # 情感评分权重
            'upvotes': 0.35, 
            'mentions': 0.25    
        }
        self.weights = weights if weights is not None else self.default_weights

    def calculate_scores(self, recs: List[Dict]) -> None:
        """Calculate scores for each recommendation item
        
        Args:
            recs: List of recommendation items to score. Each item should have:
                - avg_rating: float
                - total_upvotes: int
                - mentions: int
                
        The method will add/modify these fields in each item:
            - score: float (the final score)
            - score_components: Dict[str, float] (individual component scores)
        """
        # 找出最大值用于归一化
        max_upvotes = max((r['total_upvotes'] for r in recs), default=0)
        # 防止除以 0
        if max_upvotes == 0:
            max_upvotes = 1
        max_mentions = max((r['mentions'] for r in recs), default=0)
        # 防止除以 0
        if max_mentions == 0:
            max_mentions = 1
        max_rating = 5.0
        
        # 计算每个推荐项的分数
        for rec in recs:
            # 归一化各个组件
            rating_component = self.weights['rating'] * (rec['avg_rating'] / max_rating)
            upvote_component = self.weights['upvotes'] * (rec['total_upvotes'] / max_upvotes)
            mention_component = self.weights['mentions'] * (rec['mentions'] / max_mentions)
            # 计算总分
            score = rating_component + upvote_component + mention_component    
            # 更新推荐项
            rec['score'] = round(score, 3)
            rec['score_components'] = {
                'rating': round(rating_component, 3),
                'upvotes': round(upvote_component, 3),
                'mentions': round(mention_component, 3)
            } 