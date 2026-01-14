import pandas as pd
from textblob import TextBlob

LOG_FILE = "data/daily_logs.txt"

# Load logs
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

# Analyze sentiment
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

def generate_recommendations(df):
    df = df.sort_values('timestamp')
    df['day'] = df['timestamp'].dt.day_name()

    recommendations = []

    # 1️⃣ Most positive day of the week
    positive_day = df[df['sentiment'] == "Positive"]['day'].mode()
    if not positive_day.empty:
        recommendations.append(f"You tend to be most positive on {positive_day[0]}s. Plan important tasks then!")

    # 2️⃣ Most negative day of the week
    negative_day = df[df['sentiment'] == "Negative"]['day'].mode()
    if not negative_day.empty:
        recommendations.append(f"Your mood tends to dip on {negative_day[0]}s. Consider taking breaks or relaxing activities.")

    # 3️⃣ Productivity advice based on text length
    df['word_count'] = df['text'].apply(lambda x: len(x.split()))
    avg_words = df['word_count'].mean()
    if avg_words < 5:
        recommendations.append("Your logs are very short. Adding more details might help SELAH understand your mood better.")
    elif avg_words > 20:
        recommendations.append("You are providing detailed logs — great for tracking mood and productivity!")

    # 4️⃣ Daily streak advice
    positive_streak = (df['sentiment'] == "Positive").sum()
    if positive_streak >= 5:
        recommendations.append("You are maintaining a positive streak! Keep it up!")

    return recommendations

if __name__ == "__main__":
    df = load_logs()
    df = analyze_sentiment(df)
    recommendations = generate_recommendations(df)

    print("\n--- SELAH'S RECOMMENDATIONS ---")
    for rec in recommendations:
        print("-", rec)
