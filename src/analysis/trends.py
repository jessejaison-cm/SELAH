# trends.py

import pandas as pd
from textblob import TextBlob
import matplotlib.pyplot as plt

LOG_FILE = "data/daily_logs.txt"

# ----------------------------
# Load logs from daily_logs.txt
# ----------------------------
def load_logs():
    data = []
    with open(LOG_FILE, "r", encoding="utf-8") as file:
        for line in file:
            if "|" in line:
                timestamp, text = line.strip().split("|", 1)
                data.append({"timestamp": timestamp.strip(), "text": text.strip()})
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

# ----------------------------
# Analyze sentiment using TextBlob
# ----------------------------
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
    return df

# ----------------------------
# Detect trends and patterns
# ----------------------------
def detect_trends(df):
    # Sort by timestamp
    df = df.sort_values('timestamp')

    # Add day of the week
    df['day'] = df['timestamp'].dt.day_name()

    # Overall sentiment counts
    sentiment_counts = df['sentiment'].value_counts()
    print("\nOverall Sentiment Counts:")
    print(sentiment_counts)

    # Sentiment per day of week
    day_sentiment = df.groupby('day')['sentiment'].value_counts()
    print("\nSentiment per Day of Week:")
    print(day_sentiment)

    # ----------------------------
    # Plot weekly mood trends
    # ----------------------------
    plt.figure(figsize=(10,6))
    df.groupby('day')['sentiment'].value_counts().unstack().reindex(
        ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    ).plot(kind='bar', stacked=True, ax=plt.gca())
    plt.title("Weekly Mood Trends")
    plt.ylabel("Number of Logs")
    plt.xlabel("Day of Week")
    plt.xticks(rotation=45)
    plt.legend(title="Sentiment")
    plt.tight_layout()
    plt.show()

    return df

# ----------------------------
# Main Execution
# ----------------------------
if __name__ == "__main__":
    df = load_logs()
    df = analyze_sentiment(df)
    df = detect_trends(df)
