import requests
import os

client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
username = os.getenv('USERNAME')
password = os.getenv('PASSWORD')

url = 'https://www.reddit.com/api/v1/access_token'
headers = {'User-Agent': 'NextGen_AI'}

data = {
    'grant_type': 'client_credentials',
    'username': username,
    'password': password,
}

auth = (client_id, client_secret)

response = requests.post(url, data=data, headers=headers, auth=auth)

if response.status_code == 200:
    token = response.json()['access_token']
else:
    print(f"Failed to get access token: {response.status_code}, {response.text}")
    exit()

headers = {
    'Authorization': f'bearer {token}',
    'User-Agent': 'NextGen_AI',
}

subreddits = ['USYD']
question = "Is INFO1110 good?"

for subreddit in subreddits:
    url = f'https://oauth.reddit.com/r/{subreddit}/search.json?q={question}&sort=relevance&t=all'

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        print(f"Results for subreddit: {subreddit}")
        for post in data['data']['children']:
            title = post['data']['title']
            relative_url = post['data']['url']
            print(f"Title: {title}\nURL: {relative_url}\n")
    else:
        print(f"Failed to fetch data for subreddit {subreddit}: {response.status_code}")
