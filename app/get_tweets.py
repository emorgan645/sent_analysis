import json
import re
import string
import sys
import datetime
import time
from string import punctuation
from collections import Counter
import sys

import joblib

import sqlite3

import pandas as pd
import tweepy
from dateutil import parser
from flask import flash

from nltk.stem.wordnet import WordNetLemmatizer
from nltk.tag import pos_tag
from nltk.tokenize import word_tokenize

from textblob import TextBlob

from app.forms import InputForm
from app import db

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
# we can avoid hitting the rate limit by invoking wait_on_rate_limit=True
api = tweepy.API(auth, wait_on_rate_limit=True)

database = r"C:\Users\emorg\webapp\app.db"


# formatting helper
def sentiment_str(x):
    if x == 'negative':
        classification = 'negative'
    elif x == 'positive':
        classification = 'positive'
    else:
        classification = 'neutral'
    return classification


def get_tweets_classification(user_id, text_query, limit):
    try:

        # list to store tweets
        tweets_list = []
        # no of tweets
        count = limit

        # Pulling individual tweets from query based on user input
        results = api.search(q=[text_query], count=count, tweet_mode='extended',
                                           include_rts=False, result_type="recent",
                                           include_entities=True,
                                           lang="en")
        for tweet in results:

            tweet_msg = tweet.full_text

            location = tweet.user.location
            username = tweet.user.screen_name

            # will work out how old the acc is in days
            item = api.get_user(username)

            account_created_date = item.created_at

            delta = datetime.datetime.utcnow() - account_created_date
            account_age_days = delta.days

            if account_age_days > 60:

                if tweet_msg is not None:
                    # custom_tokens = remove_noise(word_tokenize(tweet_msg))
                    # print(custom_tokens)

                    # Adding to list that contains all tweets
                    tweets_list.append(
                        {'tweetid': tweet.id, 'username': username, 'created_at': (str(tweet.created_at)),
                         'tweet': tweet_msg, 'location': location, 'place': tweet.place})

                    tweet_msg = [tweet_msg]

                    classification = model_NB.predict(tweet_msg)
                    classification = sentiment_str(classification[0])

                    tweets_list.append({'classification': classification})

                    tweet_msg = "".join(tweet_msg)

                    # insert data just collected into SQLite database
                    connect(user_id, tweet.id, username, (str(tweet.created_at)), str(tweet_msg), location,
                            classification)
        return pd.DataFrame.from_dict(tweets_list)

    except BaseException as e:
        print('failed on_status,', str(e))
        time.sleep(3)


def get_user_classification(user_id, text_query):

    users = connect_sql_users()

    account_list = []
    tweet_count = 0

    for user in users[0:]:
        try:
            if users is not None:

                search = api.user_timeline(screen_name=user, count=20, tweet_mode='extended', include_rts=False)

                num = 0
                tb_total = 0

                for status in search:

                    num += 1
                    tb_score = 0
                    analysis = TextBlob(status.full_text)
                    
                    if analysis.sentiment.polarity == 0:  # neutral
                        tb_score = 2
                    elif 0 < analysis.sentiment.polarity <= 0.2:  # weak positive
                        tb_score = 3
                    elif 0.2 < analysis.sentiment.polarity <= 0.4:  # positive
                        tb_score = 4
                    elif 0.4 < analysis.sentiment.polarity <= 1:  # strong positive
                        tb_score = 5
                    elif -0.2 < analysis.sentiment.polarity <= 0:  # weak negative
                        tb_score = 1
                    elif -0.7 < analysis.sentiment.polarity <= -0.2:  # negative
                        tb_score = 0
                    elif -1 < analysis.sentiment.polarity <= -0.7:  # strong negative
                        tb_score = -1

                    tb_total += tb_score
                    total = num * 5
                    avg = tb_total / total * 100
                    avg = round(avg, 2)

                    account_list.append(user)
                
            else:
                sys.exit(0)
        except tweepy.TweepError as ex:
            if ex.reason == "Not authorized.":
                continue

        if len(account_list) > 0:

            
            item = api.get_user(user)
            t_user_id = item.id
            name = item.name
            description = item.description
            status_count = str(item.statuses_count)
            friend_count = str(item.friends_count)
            followers_count = str(item.followers_count)

            tweets = item.statuses_count
            account_created_date = item.created_at
            delta = datetime.datetime.utcnow() - account_created_date
            account_age_days = delta.days
            acc_age = str(account_age_days)
            if account_age_days > 0:
                avg_tweets = (float(tweets) / float(account_age_days))
                avg_tweets = round(avg_tweets, 2)
                end_date = datetime.datetime.utcnow() - datetime.timedelta(days=30)
                for status in tweepy.Cursor(api.user_timeline, id=user).items():
                    tweet_count += 1
                    if status.created_at < end_date:
                        break

            connect_sql_update(text_query, t_user_id, user_id, user, avg, name, description, status_count, friend_count, followers_count, avg_tweets, acc_age)

        else:
            print("no info")
            break
    return users

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


def connect_sql_users():
    con = sqlite3.connect(database)
    cursor = con.cursor()

    username = []

    try:

        search_query = """SELECT search_id 
        from search 
        ORDER BY `search_id` 
        DESC LIMIT 1"""
        cursor.execute(search_query)
        search_id = cursor.fetchall()

        query = """SELECT username, classification 
        FROM user_results 
        WHERE search_id = ? AND classification = 'negative'"""
        cursor.execute(query, (int(search_id[0][0]),))
        usersall = cursor.fetchall()
        for row in usersall:
            username.append(row[0])
        return username
    except sqlite3.Error as e:
        print(e)

    cursor.close()
    con.close()


def connect(user_id, tweetid, username, created_at, tweet, place, classification):
    con = sqlite3.connect(database)
    cursor = con.cursor()

    try:

        search_query = """SELECT search_id from search ORDER BY `search_id` DESC LIMIT 1"""
        cursor.execute(search_query)
        search_id = cursor.fetchall()

        query = "INSERT INTO user_results(user_id, search_id, tweetid, username, created_at, tweet, place, " \
                "classification) VALUES(?, ?, ?, ?, ?, ?, ?, ?) "

        """when using fetchall above, search_id is returned as a tuple, this is corrected below where it is cast as 
        an int """
        cursor.execute(query,
                       (user_id, int(search_id[0][0]), tweetid, username, created_at, tweet, place, classification))
        con.commit()

    except sqlite3.Error as error:
        print("Failed to insert data into sqlite table", error)

    cursor.close()
    con.close()
    return


def connect_sql_update(search_id, t_user_id, user_id, user, tb_avg, name, description, status_count, friend_count, followers_count, tweets, acc_age):
    con = sqlite3.connect(database)
    cursor = con.cursor()

    try:


        twit_query = """INSERT INTO twitter_details (search_id, twitter_user_id, name, desc, status_count, friend_count, follower_count, tweet_avg, acc_age, username, user_id, tb_score) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""" 
        cursor.execute(twit_query, (search_id, t_user_id, name, description, status_count,
                                    friend_count, followers_count, tweets, acc_age, user, user_id, tb_avg))

        con.commit()
    except sqlite3.Error as e:
        print(e)

    cursor.close()
    con.close()
