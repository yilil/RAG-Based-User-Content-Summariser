from typing import List
from langchain.docstore.document import Document
import json

class PromptBuilder:
    @staticmethod
    def build_extraction_prompt(documents: List[Document], query: str) -> str:
        """构建大模型提取信息的提示词
        
        Args:
            documents: 文档列表，每个文档包含内容和元数据
            query: 用户查询
            
        Returns:
            str: 格式化后的提示词
        """
        posts_text = ""
        for doc in documents:
            content = doc.page_content.strip()
            likes = doc.metadata.get('likes', 0) 
            posts_text += (
                f"Post (Likes: {likes}):\n"
                f"{content}\n\n"
            )

        return f"""Please analyze these posts for query "{query}" and extract recommendation items.

Input Posts:
{posts_text}

For each item, output:
- name
- posts: list of {{content, platform, likes, sentiment}}
- summary (2-3 sentences)

Output Format:
[
    {{
        "name": "item name",
        "posts": [
            {{
                "content": "the exact post text",
                "platform": "reddit/stackoverflow/rednote", 
                "upvotes": number_of_upvotes, 
                "sentiment": "very positive/positive/neutral/negative/very negative"
            }}
        ],
        "summary": "Brief summary of all reviews for this item"
    }}
]

Return ONLY a JSON array of items."""

    @staticmethod
    def get_mock_response() -> str:
        """返回用于测试的模拟数据"""
        mock_data = [
            {
                "name": "a",
                "posts": [
                    {"content": "a", "upvotes": 1, "sentiment": "positive"},
                    {"content": "b", "upvotes": 2, "sentiment": "positive"},
                    {"content": "c", "upvotes": 3, "sentiment": "positive"},
                ],
                "summary": "a, b, c"
            },
        ]
        return json.dumps(mock_data, indent=2, ensure_ascii=False) 