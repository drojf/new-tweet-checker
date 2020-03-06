import collections
import json
import os
import typing
import re
import shelve
from urllib import request

regex_data_tweet_id = re.compile(r'data-tweet-id="(\d+)"', flags=re.IGNORECASE)
DB_KEY_TWEET_IDS = 'tweet_ids'


def default_dict_factory():
    return set()


def get_new_tweet_ids(url):
    r = request.Request(url)
    r.add_header('User-Agent', 'My User Agent 1.0')

    tweets_json = json.loads(request.urlopen(r).read())

    if 'items_html' not in tweets_json:
        print("Error: items html missing on returned json")
        exit(-1)

    tweets_html = tweets_json['items_html']

    return regex_data_tweet_id.findall(tweets_html)


def generate_twitter_query_url(query_to_scan='', username=''):
    url = fr'https://twitter.com/i/search/timeline?f=tweets&q=(from:{username}){query_to_scan}'
    return url, '-'.join([username, query_to_scan])


def scan_url(db, username):
    url_to_scan, unique_key = generate_twitter_query_url(username=username)
    tweet_ids_set = set(get_new_tweet_ids(url_to_scan))

    num_new_tweets = len(tweet_ids_set.difference(db[unique_key]))

    if num_new_tweets > 0:
        db[unique_key] = tweet_ids_set

    return num_new_tweets


def scan_and_update_db(usernames: typing.List[str]):
    db_folder = 'tweet_checker_db'
    os.makedirs(db_folder, exist_ok=True)

    with shelve.open(f'{db_folder}/tweet_ids') as shelf:
        # Initialize the db on the shelf if it doesn't already exist
        if DB_KEY_TWEET_IDS not in shelf:
            db = collections.defaultdict(default_dict_factory)
            shelf[DB_KEY_TWEET_IDS] = db

        # Load the database
        db = shelf[DB_KEY_TWEET_IDS]

        # Scan each user in the list
        for username in usernames:
            num_new_tweets = scan_url(db, username)

            print(f'{username}: ', end='')
            if num_new_tweets == 0:
                print("No new tweets found")
            else:
                print(f"Found {num_new_tweets} new tweets! - https://twitter.com/{username}")

        # Save the database
        shelf[DB_KEY_TWEET_IDS] = db


if __name__ == '__main__':
    with open('settings.json', 'rb') as json_settings:
        settings = json.load(json_settings)
        usernames = settings['usernames']

    print("Checking for new tweets...")
    scan_and_update_db(usernames)
