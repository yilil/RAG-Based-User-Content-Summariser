from stackapi import StackAPI
import os

api_key = os.getenv('STACKAPI_KEY')

SITE = StackAPI('stackoverflow', key=api_key)

questions = SITE.fetch('questions', tagged='rag;python', pagesize=5, sort='votes')

if 'items' in questions and questions['items']:
    for question in questions['items']:
        print(f"Title: {question['title']}")
        print(f"Link: {question['link']}")
        print(f"Score: {question['score']}")
        print("-" * 50)
else:
    print("No questions found for the given keywords.")
