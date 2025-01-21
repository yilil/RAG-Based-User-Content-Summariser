import praw
import json
from prawcore.exceptions import NotFound, Forbidden, PrawcoreException

def create_reddit_instance():
    """
    Creates and returns a Reddit instance for API access.
    """
    # Replace with your own credentials
    client_id='xtOQ5wieF2ZhlKNdjFRVJQ'
    client_secret='5ws7ZS6mU7waQYWjKfP5HZRrNFweTA'
    user_agent = 'python:nextgen-ai:v1.0.0 (by u/your_reddit_username)'

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent
    )

    return reddit

def fetch_subreddit_posts(reddit, subreddit_name, limit=5):
    """
    Fetches top posts from a given subreddit.

    Args:
        reddit (praw.Reddit): Authenticated Reddit instance.
        subreddit_name (str): Name of the subreddit to fetch posts from.
        limit (int): Number of posts to retrieve.

    Returns:
        list: A list of dictionaries containing post data.
    """
    try:
        subreddit = reddit.subreddit(subreddit_name)

        posts_data = []
        # Let's fetch the top 'limit' posts from the 'hot' category
        for post in subreddit.hot(limit=limit):
            post_info = {
                "title": post.title,
                "score": post.score,
                "id": post.id,
                "url": post.url,
                "num_comments": post.num_comments,
                "created_utc": post.created_utc,
                "author": str(post.author)
            }
            posts_data.append(post_info)

        return posts_data
    
    except NotFound:
        print(f"Error: The subreddit '{subreddit_name}' does not exist.")
    except Forbidden:
        print(f"Error: You do not have permission to view the subreddit '{subreddit_name}'.")
    except PrawcoreException as e:
        print(f"An error occurred while accessing Reddit: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
    return []

def fetch_comments_for_post(reddit, post_id):
    """
    Fetches comments for a given post ID.

    Args:
        reddit (praw.Reddit): Authenticated Reddit instance.
        post_id (str): Reddit post ID to fetch comments for.

    Returns:
        list: A list of dictionaries containing comment data.
    """
    submission = reddit.submission(id=post_id)
    comments_data = []

    # Ensure that the submission has comments loaded
    submission.comments.replace_more(limit=0)  # Replace 'MoreComments' objects

    for comment in submission.comments.list():
        comment_info = {
            "comment_id": comment.id,
            "comment_body": comment.body,
            "comment_author": str(comment.author),
            "comment_score": comment.score,
            "comment_created_utc": comment.created_utc
        }
        comments_data.append(comment_info)

    return comments_data

import json

def search_subreddit(reddit, subreddit_name, query, limit=5, sort="relevance"):
    """
    Search for keywords or questions within a specified subreddit.

    Args:
        reddit (praw.Reddit): An authenticated Reddit instance.
        subreddit_name (str): The name of the subreddit (e.g., 'Python').
        query (str): The search keyword or question (e.g., 'Is INFO1110 good?').
        limit (int): The maximum number of search results to return.
        sort (str): The sorting method; options include 'relevance', 'hot', 'top', 'new', 'comments', etc.
    
    Returns:
        list: A list of dictionaries, each containing information about a found post.
    """
    subreddit = reddit.subreddit(subreddit_name)
    results_data = []

    # Perform the search
    # Note: search() defaults to sorting by relevance. You can specify additional parameters 
    # such as time_filter="all" or use sort='new', sort='hot', etc., for different sorting needs.
    search_results = subreddit.search(query, limit=limit, sort=sort)

    # Extract information from the search results
    for post in search_results:
        post_info = {
            "title": post.title,
            "score": post.score,
            "id": post.id,
            "url": post.url,
            "num_comments": post.num_comments,
            "created_utc": post.created_utc,
            "author": str(post.author)
        }
        results_data.append(post_info)
    
    return results_data



def save_data_to_json(data, filename="data.json"):
    """
    Saves the given data to a JSON file.

    Args:
        data (list or dict): Data to be saved in JSON format.
        filename (str): Name of the output JSON file.
    """
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"Data successfully saved to {filename}")
    except IOError as e:
        print(f"Error saving data to {filename}: {e}")
        
        
def display_posts(posts):
    for idx, post in enumerate(posts, start=1):
        print(f"{idx}. Title: {post['title']} | Score: {post['score']}")


if __name__ == "__main__":
    reddit_instance = create_reddit_instance()

    # Example: Fetch posts from the "Python" subreddit
    subreddit_name = "Python"
    print(f"Fetching top posts from r/{subreddit_name}...")
    posts = fetch_subreddit_posts(reddit_instance, subreddit_name, limit=3)

    for idx, post in enumerate(posts, start=1):
        print(f"Post #{idx}: {post['title']} (Score: {post['score']})")

        # Fetch comments for each post (optional)
        post_comments = fetch_comments_for_post(reddit_instance, post['id'])
        print(f"Retrieved {len(post_comments)} comments for this post.\n")
        
    # Displaying posts on the console
    display_posts(posts)

    # Saving posts to a JSON file
    save_data_to_json(posts, "python_subreddit_posts.json")
