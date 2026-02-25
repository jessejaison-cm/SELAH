import pandas as pd
import os
from preprocessing.sentiment_analysis import analyze_sentiment
from assistant.selah_brain import LOG_FILE

def load_logs():
    print("READING FROM:", os.path.abspath(LOG_FILE))
    print("FILE EXISTS:", os.path.exists(LOG_FILE))
    if not os.path.exists(LOG_FILE):
        return pd.DataFrame()

    data = []

    with open(LOG_FILE, "r", encoding="utf-8") as file:
        for line in file:
            if "|" in line:
                timestamp, text = line.strip().split("|", 1)

                try:
                    parsed_date = pd.to_datetime(timestamp.strip(), format="%Y-%m-%d %H:%M:%S")
                except:
                    continue

                data.append({
                    "date": parsed_date,
                    "text": text.strip()
                })

    df = pd.DataFrame(data)

    if df.empty:
        return df

    # Generate polarity column
    df["polarity"] = df["text"].apply(analyze_sentiment)

    return df

print("READING FILE:", os.path.abspath(LOG_FILE))