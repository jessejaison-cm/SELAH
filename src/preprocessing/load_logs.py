import pandas as pd

LOG_FILE = "data/daily_logs.txt"

def load_logs():
    data = []

    with open(LOG_FILE, "r", encoding="utf-8") as file:
        for line in file:
            if "|" in line:
                timestamp, text = line.strip().split("|", 1)
                data.append({
                    "timestamp": timestamp.strip(),
                    "text": text.strip()
                })

    df = pd.DataFrame(data)
    return df


if __name__ == "__main__":
    df = load_logs()
    print(df.head())
