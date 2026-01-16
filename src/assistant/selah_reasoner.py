import pandas as pd
from datetime import datetime
from collections import Counter
from textblob import TextBlob

LOG_FILE = "data/daily_logs.txt"

# ----------------------------
# Load logs
# ----------------------------
def load_logs():
    data = []
    with open(LOG_FILE, "r", encoding="utf-8") as file:
        for line in file:
            if "|" in line:
                ts, text = line.strip().split("|", 1)
                data.append({
                    "timestamp": pd.to_datetime(ts.strip()),
                    "text": text.strip()
                })
    return pd.DataFrame(data)

# ----------------------------
# Sentiment helper
# ----------------------------
def sentiment(text):
    p = TextBlob(text).sentiment.polarity
    if p > 0.1:
        return "Positive"
    elif p < -0.1:
        return "Negative"
    return "Neutral"

# ----------------------------
# Reasoning: compare periods
# ----------------------------
def compare_years(year1, year2):
    df = load_logs()

    def year_summary(year):
        subset = df[df["timestamp"].dt.year == year]
        sentiments = subset["text"].apply(sentiment)
        dominant = sentiments.value_counts().idxmax()

        words = []
        for t in subset["text"]:
            words += [w for w in t.lower().split() if len(w) > 4]

        themes = [w for w, _ in Counter(words).most_common(3)]
        return dominant, themes

    s1, t1 = year_summary(year1)
    s2, t2 = year_summary(year2)

    explanation = (
        f"In {year1}, your mood was mostly {s1.lower()}, "
        f"while in {year2} it was mostly {s2.lower()}. "
    )

    if s1 != s2:
        explanation += "This suggests a change in emotional intensity. "
    else:
        explanation += "Emotionally, both years were similar. "

    explanation += (
        f"Key themes in {year1} were {', '.join(t1)}, "
        f"while in {year2} they were {', '.join(t2)}."
    )

    return explanation

# ----------------------------
# Life summary
# ----------------------------
def summarize_life():
    df = load_logs()
    sentiments = df["text"].apply(sentiment)
    dominant = sentiments.value_counts().idxmax()

    return (
        f"Overall, your journey shows resilience. "
        f"Despite long periods of {dominant.lower()} emotion, "
        f"you continued progressing and rebuilding yourself."
    )
