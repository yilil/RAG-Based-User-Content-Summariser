from typing import List
from langchain.docstore.document import Document
import json

class PromptBuilder:
    @staticmethod
    def build_extraction_prompt(documents: List[Document], query: str) -> str:
        """
        [DEMO SECTION 1] Build extraction prompt for LLM
        
        This method creates the prompt used to extract recommendation items from retrieved documents.
        It formats the documents and provides clear instructions for the LLM to extract structured data.
        
        Args:
            documents: List of documents, each containing content and metadata
            query: User query
            
        Returns:
            str: Formatted prompt for LLM extraction
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
        """
        Return mock data for testing
        
        This method provides fallback mock data when LLM extraction fails,
        ensuring the demo can continue even if there are API issues.
        """
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