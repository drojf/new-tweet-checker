import collections
import json
import os
import typing
import re
import shelve
from urllib import request
from urllib import parse

regex_data_tweet_id = re.compile(r'data-tweet-id="(\d+)"', flags=re.IGNORECASE)
DB_KEY_TWEET_IDS = 'tweet_ids'
TWITTER_SEARCH_URL = r'https://twitter.com/i/search/timeline?f=tweets&q='
debug = False


class TwitterQuery:
    def __init__(self, search_string='', username=''):
        self.search_string = search_string
        self.username = username

    def __repr__(self):
        user_part = '(Any User)'
        if self.username != '':
            user_part = self.username

        search_part = '(No Search String)'
        if self.search_string != '':
            search_part = self.search_string

        return f'User: {user_part} Search String: {search_part}'


def get_new_tweet_ids(url):
    r = request.Request(url)
    r.add_header('User-Agent', 'My User Agent 1.0')

    tweets_json = json.loads(request.urlopen(r).read())

    if 'items_html' not in tweets_json:
        print("Error: items html missing on returned json")
        exit(-1)

    tweets_html = tweets_json['items_html']

    return regex_data_tweet_id.findall(tweets_html)


def generate_twitter_query_url(query: TwitterQuery):
    query_parts = []
    if query.username != '':
        query_parts.append(f'(from:{query.username})')
    query_parts.append(query.search_string)

    query_as_string = ''.join(query_parts)
    quoted_query = parse.quote(query_as_string)

    if debug:
        print(f"Query: {query_as_string}")
        print(f"Quoted Query: {quoted_query}")

    return fr'{TWITTER_SEARCH_URL}{quoted_query}', '-'.join([query.username, query.search_string])


def scan_url(db, query: TwitterQuery):
    url_to_scan, unique_key = generate_twitter_query_url(query)
    tweet_ids_set = set(get_new_tweet_ids(url_to_scan))

    old_tweet_set = db[unique_key]
    difference = tweet_ids_set.difference(old_tweet_set)

    num_new_tweets = len(difference)

    if num_new_tweets > 0:
        db[unique_key] = tweet_ids_set

    return num_new_tweets


def scan_result_as_string(query, num_new_tweets) -> str:
    if query.username != '':
        prefix = f'- {query.username}: '
    else:
        prefix = f'- {query.search_string}: '

    if num_new_tweets == 0:
        return f"{prefix}No new tweets found"
    else:
        if query.username != '':
            return f"{prefix}Found {num_new_tweets} new tweets! - https://twitter.com/{query.username}"
        else:
            return f"{prefix}Found {num_new_tweets} new tweets! - ({query})"


def json_queries_to_python_queries(json_queries):
    twitter_queries = []
    for query in json_queries:
        username = ''
        search_string = ''
        if 'username' in query:
            username = query['username']
        if 'search_string' in query:
            search_string = query['search_string']
        twitter_queries.append(TwitterQuery(search_string, username))

    return twitter_queries


class TweetScanner:
    def __init__(self):
        with open('settings.json', 'rb') as json_settings:
            settings = json.load(json_settings)
            self.queries = json_queries_to_python_queries(settings['queries'])

        db_folder = 'tweet_checker_db'
        os.makedirs(db_folder, exist_ok=True)
        self.shelf = shelve.open(f'{db_folder}/tweet_ids')

        # Initialize the db on the shelf if it doesn't already exist
        if DB_KEY_TWEET_IDS not in self.shelf:
            db = collections.defaultdict(TweetScanner.default_dict_factory)
            self.shelf[DB_KEY_TWEET_IDS] = db

        # Load the database
        self.db = self.shelf[DB_KEY_TWEET_IDS]

        if debug:
            print(f"Base url: {TWITTER_SEARCH_URL}")

    def scan_for_tweets(self):
        print("Checking for new tweets...")

        # Scan each user in the list
        string_result = []
        for query in self.queries:
            num_new_tweets = scan_url(self.db, query)
            if num_new_tweets > 0:
                string_result.append(scan_result_as_string(query, num_new_tweets))

        # Save the database
        # Python docs suggest sync() only needed when writeback option is used, but I found it wouldn't save immediately
        # unless I called it myself
        self.shelf[DB_KEY_TWEET_IDS] = self.db
        self.shelf.sync()

        if string_result:
            return '\n'.join(string_result)
        else:
            return None

    def close(self):
        self.shelf.close()

    @staticmethod
    def default_dict_factory():
        return set()


if __name__ == '__main__':
    scanner = TweetScanner()
    print(scanner.scan_for_tweets())
    scanner.close()
