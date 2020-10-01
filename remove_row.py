import csv

"""
The following will only check one column's value and so 
should be significantly faster than checking all of 
them in every row of the file. 
"""

file_name = 'tweet_data/dataset/positive_tweets_.csv'
cleaned_file_name = 'tweet_data/dataset/positive_tweets_updated.csv'
ONE_COLUMN = 2
remove_words = ['#MAGA', '#maga', '#OnlyFans', '#Onlyfans', '#onlyfans', 'discount code', '#live', '#Follow', 'shop now', '#ad']

with open(file_name, 'r', newline='', encoding='utf-8') as infile, \
        open(cleaned_file_name, 'w', newline='', encoding='utf-8') as outfile:
    writer = csv.writer(outfile)
    for row in csv.reader(infile, delimiter=','):
        column = row[ONE_COLUMN]
        if not any(remove_word in column for remove_word in remove_words):
            writer.writerow(row)
        else:
            print(row)