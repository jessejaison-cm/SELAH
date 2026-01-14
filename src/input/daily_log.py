from datetime import datetime
def collect_daily_log():
  print("SELAH - Daily Log")
  print("------------------")

  log_text = input("How was your day? Write Freely:\n")

  log_entry= {
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "text": log_text
  }

  with open("data/daily_logs.txt", "a", encoding= "utf-8") as file:
            file.write(f"{log_entry['timestamp']} | {log_entry['text']}\n")

  print("\nLog saved. SELAH is listening.")

if __name__ == "__main__":
    collect_daily_log()