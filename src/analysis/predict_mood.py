# predict_mood.py

import pandas as pd
from textblob import TextBlob
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder

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
# Prepare features for ML
# ----------------------------
def prepare_features(df):
    df = df.sort_values('timestamp')
    df['day'] = df['timestamp'].dt.day_name()

    # Encode day of week (optional, not used in this simple model)
    day_le = LabelEncoder()
    df['day_num'] = day_le.fit_transform(df['day'])

    # Previous sentiment as feature
    df['prev_sentiment'] = df['sentiment'].shift(1)
    df = df.dropna()

    # Encode sentiment for model
    sentiment_le = LabelEncoder()
    df['sentiment_num'] = sentiment_le.fit_transform(df['sentiment'])

    # Features
    features = df[['day_num', 'prev_sentiment']].copy()
    features['prev_sentiment'] = sentiment_le.transform(features['prev_sentiment'])

    target = df['sentiment_num']
    return features, target, day_le, sentiment_le

# ----------------------------
# Train simple predictive model
# ----------------------------
def train_predictive_model(features, target):
    model = LogisticRegression(max_iter=200)
    model.fit(features, target)
    return model

# ----------------------------
# Predict next-day sentiment
# ----------------------------
def predict_next_day_mood(df, model, sentiment_le):
    last_day = df.iloc[-1]

    prev_sentiment = last_day['sentiment']
    prev_sentiment_num = sentiment_le.transform([prev_sentiment])[0]

    # day_num can be dummy (0) in this simple model
    X_next = pd.DataFrame({'day_num':[0], 'prev_sentiment':[prev_sentiment_num]})
    pred_num = model.predict(X_next)[0]

    predicted_sentiment = sentiment_le.inverse_transform([pred_num])[0]
    return predicted_sentiment

# ----------------------------
# Main execution
# ----------------------------
if __name__ == "__main__":
    df = load_logs()
    df = analyze_sentiment(df)
    features, target, day_le, sentiment_le = prepare_features(df)
    model = train_predictive_model(features, target)
    next_day_sentiment = predict_next_day_mood(df, model, sentiment_le)
    print(f"\n--- SELAH PREDICTION ---")
    print(f"Predicted sentiment for the next day: {next_day_sentiment}")
