import csv
import json
from dateutil import parser
import mysql
import tweepy
from mysql.connector import Error

consumer_key = ''
consumer_secret = ''
access_token = ''
access_token_secret = ''


def connect(tweetid, username, created_at, tweet, place, location):
    try:
        con = mysql.connector.connect(host="localhost", user="root",
                                      passwd="", database="", use_unicode=True, charset='utf8')

        if con.is_connected():
            cursor = con.cursor()
            query = 'INSERT INTO TABLE (tweetid, username, created_at, tweet, location, place) VALUES (' \
                    '%s, %s, %s, %s, %s, %s) '
            cursor.execute(query, (tweetid, username, created_at, tweet, location, place))
            con.commit()

    except Error as e:
        print(e)

    cursor.close()
    con.close()

    return


# Tweepy class to access Twitter API
class Streamlistener(tweepy.StreamListener):

    def on_connect(self):
        # Called initially to connect to the Streaming API
        print("You are now connected to the streaming API.")

    def on_status(self, status):
        try:
            print(status.extended_tweet['full_text'])
        except Exception as e:
            raise
        else:
            print(status.text)
        return True

    def on_error(self, status_code):
        # On error - if an error occurs, display the error / status code
        print('An Error has occurred: ' + repr(status_code))
        if status_code == 420:
            return False
        return False

    """
    This method reads in tweet data as Json
    and extracts the data we want.
    """

    def on_data(self, data):

        try:
            raw_data = json.loads(data)

            if 'extended_tweet' in raw_data:

                tweetid = raw_data['id']
                username = raw_data['user']['screen_name']
                created_at = parser.parse(raw_data['created_at'])
                location = raw_data['user']['location']

                if raw_data['place'] is not None:
                    place = raw_data['place']['country']
                else:
                    place = None

                if not raw_data['retweeted'] and 'RT @' and '@' not in raw_data['extended_tweet']['full_text']:
                    tweet = raw_data['extended_tweet']['full_text']
                    print(tweet)

                else:
                    tweet = None

                # tweet data will only be stored in db if above criteria is met
                if tweet is not None:
                    connect(tweetid, username, created_at, tweet, location, place)
                    print("Tweet collected at: {} ".format(str(created_at)))

        except Error as e:
            print(e)


if __name__ == '__main__':
    # access twitter
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth, wait_on_rate_limit=True)

    # create instance of Streamlistener
    # tweet mode 'extended' allows for full text tweets to be streamed
    listener = Streamlistener(api=api)
    stream = tweepy.Stream(auth, listener=listener, tweet_mode='extended')

    track = ['']

    # choose what to filter by
    stream.filter(track=track, languages=['en'])
