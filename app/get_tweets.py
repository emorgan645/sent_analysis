import json
import re
import string
import sys
from datetime import datetime
from string import punctuation

import joblib
import mysql.connector
import pandas as pd
import tweepy
from dateutil import parser
from flask import flash
from mysql.connector import Error
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.tag import pos_tag
from nltk.tokenize import word_tokenize

from app.forms import InputForm

pd.set_option('display.max_colwidth', 1000)

model_NB = joblib.load("twttr_sntmnt.pkl")

# api key
api_key = 'keNzWN4DQt2sHQ7LJmYZQJ9rV'
# api secret key
api_secret_key = 'jmUlnbV35AGLLCPqfrzmEL88NNCCfdoY2WnNew4gGDGVwwxbuc'
# access token
access_token = '1263111922276237313-TlfkpB7NgMFxV0P4Riz99kFubsRbhM'
# access token secret
access_token_secret = 'DKedCMrsuuLwhKHcBpdidqWl0Jemsdbkvpk9TodeQ656m'

# access twitter api
auth = tweepy.OAuthHandler(api_key, api_secret_key)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth, wait_on_rate_limit=True)


# def get_related_tweets(text_query):
#     # list to store tweets
#     tweets_list = []
#     # no of tweets
#     count = 50
#     try:
#         # Pulling individual tweets from query
#         for tweet in api.search(q=text_query, count=count):
#             print(tweet.text)
#             # Adding to list that contains all tweets
#             tweets_list.append({'created_at': tweet.created_at,
#                                 'tweet_id': tweet.id,
#                                 'tweet_text': tweet.text})
#         return pd.DataFrame.from_dict(tweets_list)

#     except BaseException as e:
#         print('failed on_status,', str(e))
#         time.sleep(3)

def streaming():
    # create instance of Streamlistener
    # tweet mode 'extended' allows for full text tweets to be streamed
    listener = Streamlistener(api=api)

    stream = tweepy.Stream(auth, listener=listener, tweet_mode='extended')

    track = InputForm.keywords

    # choose what we want to filter by
    stream.filter(track=track, languages=['en'])


def remove_noise(tweet_tokens, stop_words=()):
    """
    Takes in a string of text, then performs the following:
    1. Remove all punctuation
    2. Remove all stopwords
    3. Returns a list of the cleaned tokens
    """

    cleaned_tokens = []

    for token, tag in pos_tag(tweet_tokens):
        token = re.sub('’', '', token)
        token = re.sub("http", '', token)
        # Remove HTML special entities (e.g. &amp;)
        token = re.sub(r'&\w*;', '', token)
        # Convert @username to AT_USER
        token = re.sub('@[^\s]+', '', token)
        # Remove tickers
        token = re.sub(r'\$\w*', '', token)
        # To lowercase
        token = token.lower()
        # Remove hyperlinks
        token = re.sub(r'https?:\/\/.*\/\w*', '', token)
        # Remove hashtags
        token = re.sub(r'#\w*', '', token)
        # Remove Punctuation and split 's, 't, 've with a space for filter
        token = re.sub(r'[' + punctuation.replace('@', '') + ']+', ' ', token)
        # Remove words with 2 or fewer letters
        token = re.sub(r'\b\w{1,2}\b', '', token)
        # Remove whitespace (including new line characters)
        token = re.sub(r'\s\s+', ' ', token)
        # Remove single space remaining at the front of the tweet.
        token = token.lstrip(' ')
        # Remove characters beyond Basic Multilingual Plane (BMP) of Unicode:
        token = ''.join(c for c in token if c <= '\uFFFF')

        if tag.startswith("NN"):
            pos = 'n'
        elif tag.startswith('VB'):
            pos = 'v'
        else:
            pos = 'a'

        lemmatizer = WordNetLemmatizer()
        token = lemmatizer.lemmatize(token, pos)

        if len(token) > 0 and token not in string.punctuation and token.lower() not in stop_words:
            cleaned_tokens.append(token.lower())
    return cleaned_tokens


# get a word count per sentence column
def word_count(sentence):
    return len(sentence.split())


# formatting helper
def sentiment_str(x):
    if x == 'negative':
        classification = 'negative'
    elif x == 'positive':
        classification = 'positive'
    else:
        classification = 'neutral'
    return classification


def connect(tweetid, username, created_at, tweet, location, place, classification):
    con = mysql.connector.connect(host="localhost", user="root",
                                  passwd="", database="emorgan", use_unicode=True, charset='utf8')
    cursor = con.cursor()
    try:
        if con.is_connected():

            query = "INSERT INTO tweetdb (tweetid, username, created_at, tweet, location, place, classification) " \
                    "VALUES (%s, %s, %s, %s, %s, %s, %s) "
            cursor.execute(query, (tweetid, username, created_at, tweet, location, place, classification))
            if classification == 'negative':
                query_neg = "INSERT INTO neg_tweet (tweetid, username, created_at, tweet, place, location) " \
                            "VALUES (%s, %s, %s, %s, %s, %s)"
                cursor.execute(query_neg, (tweetid, username, created_at, tweet, location, place))
            con.commit()

            # sql_select_query = "select * from tweetdb"
            # cursor.execute(sql_select_query)
            # rows = cursor.fetchall()
            #
            # csvfile = open('tweet_data/tweetdb.csv', 'w', newline='', encoding='utf-8')
            # csvwriter = csv.writer(csvfile)
            #
            # csvwriter.writerows(rows)

    except Error as e:
        print(e)

    cursor.close()
    con.close()
    return


# Tweepy class to access Twitter API
class Streamlistener(tweepy.StreamListener):

    def __init__(self, api=None):
        super().__init__()
        self.counter = 0
        self.limit = 10

    def on_connect(self):
        # Called initially to connect to the Streaming API
        flash("You are now connected to the streaming API.")

    def on_status(self, status):
        try:
            flash(status.extended_tweet['full_text'])
        except Exception as e:
            raise e
        else:
            flash(status.text)
        return True

    def on_error(self, status_code):
        # On error - if an error occurs, display the error / status code
        flash('An Error has occurred: ' + repr(status_code))
        if status_code == 420:
            return False
        return False

    """
    This method reads in tweet data as Json
    and extracts the data needed.
    """

    def on_data(self, data):

        try:

            raw_data = json.loads(data)

            username = raw_data['user']['screen_name']

            item = api.get_user(username)

            account_created_date = item.created_at

            delta = datetime.utcnow() - account_created_date
            account_age_days = delta.days

            pos = 0
            neg = 0
            neut = 0

            if account_age_days > 60:

                if 'extended_tweet' in raw_data:
                    tweet = raw_data['extended_tweet']['full_text']
                    if not raw_data['retweeted'] and 'RT @' and '@' not in raw_data['extended_tweet']['full_text']:
                        return tweet
                    else:
                        tweet = None
                else:
                    tweet = raw_data['text']
                    if not raw_data['retweeted'] and 'RT @' and '@' not in raw_data['text']:
                        return tweet
                    else:
                        tweet = None

                tweetid = raw_data['id']
                created_at = parser.parse(raw_data['created_at'])

                location = raw_data['user']['location']

                if raw_data['place'] is not None:
                    place = raw_data['place']
                else:
                    place = None

                if tweet is not None:
                    custom_tweet = tweet

                    custom_tokens = remove_noise(word_tokenize(custom_tweet))
                    p = model_NB.predict(custom_tokens)
                    classification = sentiment_str(p[0])

                    # insert data just collected into MySQL database
                    connect(tweetid, username, created_at, tweet, location, place, classification)
                    collected = "Tweet collected at: {} ".format(str(created_at))
                    acc_age = "Account age (in days): " + str(account_age_days)
                    tweet_info = custom_tweet, collected, acc_age, classification
                    print(tweet_info)

                    if classification == 'positive':
                        pos += 1
                    elif classification == 'negative':
                        neg += 1
                    else:
                        neut += 1

                    self.counter += 1

                    if self.counter < self.limit:
                        return True
                    else:
                        predictions = 'Model predictions: Positives - {}, Negatives - {}, Neutrals - {}'.format(pos,
                                                                                                                neg,
                                                                                                                neut)
                        sys.exit('Limit of ' + str(self.limit) + ' tweets reached.')
                        return predictions

        except Error as e:
            print(e)
