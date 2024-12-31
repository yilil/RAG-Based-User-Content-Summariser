import logging
from search.models import RedditContent, StackOverflowContent
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from .utils import get_embeddings
from django.conf import settings

# Initialize logger
logger = logging.getLogger(__name__)

class IndexService:
    def __init__(self):
        # Initialize the embedding model
        self.embedding_model = get_embeddings()

    def index_reddit_content(self):
        """
        Index Reddit content with embeddings.
        """
        logger.info("Indexing Reddit content...")

        try:
            reddit_content_objects = RedditContent.objects.all()

            for content in reddit_content_objects:
                # Generate the embedding for the content
                embedding = self.embedding_model.embed_query(content.content)

                # Save the embedding and relevant data in a search index or custom table
                self._index_content(content, embedding, 'reddit')
            
            logger.info(f"Indexed {len(reddit_content_objects)} Reddit content objects.")
        except Exception as e:
            logger.error(f"Error indexing Reddit content: {str(e)}")
            raise

    def index_stackoverflow_content(self):
        """
        Index StackOverflow content with embeddings.
        """
        logger.info("Indexing StackOverflow content...")

        try:
            stackoverflow_content_objects = StackOverflowContent.objects.all()

            for content in stackoverflow_content_objects:
                # Generate the embedding for the content
                embedding = self.embedding_model.embed_query(content.content)

                # Save the embedding and relevant data in a search index or custom table
                self._index_content(content, embedding, 'stackoverflow')

            logger.info(f"Indexed {len(stackoverflow_content_objects)} StackOverflow content objects.")
        except Exception as e:
            logger.error(f"Error indexing StackOverflow content: {str(e)}")
            raise

    def _index_content(self, content, embedding, source):
        """
        Internal method to index content and store the embedding.
        """

        try:
            from search.models import ContentIndex  # Sample: define a ContentIndex model to store embeddings
            content_index = ContentIndex(
                source=source,
                thread_id=content.thread_id,
                content_type=content.content_type,
                author_name=content.author_name,
                content=content.content,
                created_at=content.created_at,
                updated_at=content.updated_at,
                embedding=embedding  # store the embedding as a JSON or Array
            )
            content_index.save()
            logger.info(f"Indexed content {content.id} from {source}.")
        except Exception as e:
            logger.error(f"Error indexing content {content.id}: {str(e)}")
            raise

    def search_content(self, query):
        """
        Search indexed content using embeddings.
        """
        logger.info(f"Searching for query: {query}")
        
        try:
            # use embeddings to match the query with the indexed content.
            query_embedding = self.embedding_model.embed_query(query)
            
            # Perform semantic search by comparing the query embedding with stored embeddings
            # For demonstration, we will fetch all content, but you could use a more sophisticated retrieval approach.
            from search.models import ContentIndex
            content_objects = ContentIndex.objects.all()  # This would be replaced with a vector search in production
            
            results = []
            for content in content_objects:
                # Simple cosine similarity or other distance metric to compare query embedding with stored embedding
                # (Could integrate this with FAISS or another vector search method in production)
                similarity = self.calculate_similarity(query_embedding, content.embedding)
                if similarity > 0.8:  # Adjust the threshold as needed
                    results.append(content)
            
            logger.info(f"Found {len(results)} matching results for query: {query}")
            return results
        
        except Exception as e:
            logger.error(f"Error searching content: {str(e)}")
            raise

    def calculate_similarity(self, query_embedding, content_embedding):
        """
        Calculate similarity between query and stored content embedding.
        This can be based on cosine similarity or another metric.
        """
        # A placeholder for similarity calculation. You can replace this with a proper similarity measure (e.g., cosine similarity).
        from sklearn.metrics.pairwise import cosine_similarity
        similarity_score = cosine_similarity([query_embedding], [content_embedding])
        return similarity_score[0][0]  # Return the cosine similarity score

