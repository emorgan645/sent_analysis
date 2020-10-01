import random
import re
import string
from string import punctuation

from nltk.corpus import stopwords
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.tag import pos_tag

from pandas import read_csv
import joblib

from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.naive_bayes import MultinomialNB
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.model_selection import GridSearchCV


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

        # the following function that lemmatizes the dataset
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


def get_all_words(cleaned_tokens_list):
    for tokens in cleaned_tokens_list:
        for token in tokens:
            yield token


def get_tweets_for_model(cleaned_tokens_list):
    for tweet_tokens in cleaned_tokens_list:
        yield dict([token, True] for token in tweet_tokens)


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


if __name__ == "__main__":
    # load train data
    dataset = read_csv('tweet_data/dataset/combined_tweets_updated.csv',
                       error_bad_lines=False)

    # drop duplicates
    dataset = dataset.drop_duplicates('tweet')

    dataset = dataset[dataset['tweet'].notnull()]

    # check the number of positive/negative/neutral tagged sentences
    positives = dataset['classification'][dataset.classification == 'positive']
    negatives = dataset['classification'][dataset.classification == 'negative']
    neutral = dataset['classification'][dataset.classification == 'neutral']
    print('number of positive tagged sentences is:  {}'.format(len(positives)))
    print('number of negative tagged sentences is: {}'.format(len(negatives)))
    print('number of neutral tagged sentences is: {}'.format(len(neutral)))
    print('total length of the data is:            {}'.format(dataset.shape[0]))

    sentence = dataset['tweet']

    stop_words = stopwords.words('english')

    # unnecessary words removed from tweets
    sentence = remove_noise(sentence, stop_words)

    # vectorize
    bow_transformer = CountVectorizer().fit(remove_noise(sentence, stop_words))
    # print total number of vocab words
    print(len(bow_transformer.vocabulary_))

    # transform the entire DataFrame of messages
    messages_bow = bow_transformer.transform(remove_noise(sentence, stop_words))

    # check out the bag-of-words counts for the entire corpus as a large sparse matrix
    print('Shape of Sparse Matrix: ', messages_bow.shape)
    print('Amount of Non-Zero occurrences: ', messages_bow.nnz)

    tfidf_transformer = TfidfTransformer().fit(messages_bow)

    # to transform the entire bag-of-words corpus
    messages_tfidf = tfidf_transformer.transform(messages_bow)
    print(messages_tfidf.shape)

    # creates pipeline
    pipeline = Pipeline([
        ('bow', CountVectorizer(strip_accents='ascii',
                                stop_words='english',
                                lowercase=True)),  # strings to token integer counts
        ('tfidf', TfidfTransformer()),  # integer counts to weighted TF-IDF scores
        ('classifier', MultinomialNB()),  # train on TF-IDF vectors w/ Naive Bayes classifier
    ])
    # define the values for GridSearchCV to iterate over
    parameters = {'bow__ngram_range': [(1, 1), (1, 2)],
                  'tfidf__use_idf': (True, False),
                  'classifier__alpha': (1, 1e-1, 1e-2, 1e-3),
                  }

    X_train, X_test, y_train, y_test = train_test_split(dataset['tweet'], dataset['classification'], test_size=0.2)

    # 10-fold cross validation for each of the 8 possible combinations of the above params
    grid = GridSearchCV(pipeline, cv=10, param_grid=parameters, verbose=1)
    grid.fit(X_train, y_train)

    # summarize results
    print("\nBest Model: %f using %s" % (grid.best_score_, grid.best_params_))
    print('\n')
    means = grid.cv_results_['mean_test_score']
    stds = grid.cv_results_['std_test_score']
    params = grid.cv_results_['params']
    for mean, stdev, param in zip(means, stds, params):
        print("Mean: %f Stdev:(%f) with: %r" % (mean, stdev, param))

    # save best model to current working directory
    joblib.dump(grid, "twttr_sntmnt.pkl")

    # load from file and predict using the best configs found in the CV step
    model_NB = joblib.load("twttr_sntmnt.pkl")

    # get predictions from best model above
    y_preds = model_NB.predict(X_test)

    print('accuracy score: ', accuracy_score(y_test, y_preds))
    print('\n')
    print('confusion matrix: \n', confusion_matrix(y_test, y_preds))
    print('\n')
    print(classification_report(y_test, y_preds))
