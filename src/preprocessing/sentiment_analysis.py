import pandas as pd
from textblob import TextBlob

LOG_FILE = "data/daily_logs.txt"

def load_logs():
    data = []
    with open(LOG_FILE, "r", encoding="utf-8") as file:
        for line in file:
            if "|" in line:
                timestamp, text = line.strip().split("|", 1)
                data.append({"timestamp": timestamp.strip(), "text": text.strip()})
    df = pd.DataFrame(data)
    return df

def analyze_sentiment(df):
    sentiments = []
    for text in df['text']:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        # classify as positive, neutral, negative
        if polarity > 0.1:
            sentiments.append("Positive")
        elif polarity < -0.1:
            sentiments.append("Negative")
        else:
            sentiments.append("Neutral")
    df['sentiment'] = sentiments
    df['word_count'] = df['text'].apply(lambda x: len(x.split()))
    return df

if __name__ == "__main__":
    df = load_logs()
    df = analyze_sentiment(df)
    print(df)
