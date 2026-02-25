import pandas as pd
from textblob import TextBlob
import matplotlib.pyplot as plt

LOG_FILE = "data/daily_logs.txt"

def load_logs():
    data = []
    with open(LOG_FILE, "r", encoding="utf-8") as file:
        for line in file:
            if "|" in line:
                timestamp, text = line.strip().split("|", 1)
                data.append({
                    "timestamp": pd.to_datetime(timestamp.strip()),
                    "text": text.strip()
                })
    df = pd.DataFrame(data)
    return df


def analyze_sentiment(df):
    sentiments = []

    for text in df['text']:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity

        if polarity > 0.1:
            sentiments.append("Positive")
        elif polarity < -0.1:
            sentiments.append("Negative")
        else:
            sentiments.append("Neutral")

    df['sentiment'] = sentiments
    df['word_count'] = df['text'].apply(lambda x: len(x.split()))
    df["polarity"] = df["text"].apply(
        lambda x: TextBlob(str(x)).sentiment.polarity
    )

    return df


def generate_mood_trend_graph(df):
    df = df.sort_values("timestamp")

    plt.figure()
    plt.plot(df["timestamp"], df["polarity"])
    plt.xlabel("Date")
    plt.ylabel("Polarity")
    plt.title("Emotional Trend Over Time")
    plt.xticks(rotation=45)
    plt.axhline(0)  # zero reference line
    plt.tight_layout()
    plt.show()

def generate_sentiment_distribution(df):
    sentiment_counts = df["sentiment"].value_counts()

    plt.figure()
    plt.pie(sentiment_counts, labels=sentiment_counts.index, autopct='%1.1f%%')
    plt.title("Sentiment Distribution")
    plt.show()

if __name__ == "__main__":
    df = load_logs()
    df = analyze_sentiment(df)

    print(df)

    # Generate graph
    generate_mood_trend_graph(df)
    generate_sentiment_distribution(df)