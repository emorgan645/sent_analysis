import re

# open csv and read as a text string
with open('tweet_data/dataset/combined_tweets_updated.csv', 'r', encoding='utf-8') as f:
    my_csv_text = f.read()

find_str = 'get'
replace_str = ''

# substitute
new_csv_str = re.sub(find_str, replace_str, my_csv_text)

# open new file and save
new_csv_path = 'tweet_data/dataset/combined_tweets_updated.csv'
with open(new_csv_path, 'w', encoding='utf-8') as f:
    f.write(new_csv_str)
    f.write("\n")
