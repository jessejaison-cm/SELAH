import pandas as pd
from textblob import TextBlob
from datetime import datetime, timedelta
import pyttsx3
from collections import Counter
import json
import os
import re
import dateparser
from selah_reasoner import compare_years, summarize_life

# =========================
# FILE PATHS
# =========================
LOG_FILE = "data/daily_logs.txt"
GOALS_FILE = "data/goals.json"
HABITS_FILE = "data/habits.json"
REMINDERS_FILE = "data/reminders.json"
CONTEXT_FILE = "data/context.json"

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12
}

# =========================
# VOICE ENGINE
# =========================
engine = pyttsx3.init()
engine.setProperty("rate", 170)

def speak(text):
    engine.say(text)
    engine.runAndWait()

# =========================
# JSON HELPERS
# =========================
def load_json(file_path):
    if not os.path.exists(file_path) or os.stat(file_path).st_size == 0:
        with open(file_path, "w") as f:
            json.dump({}, f)
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# =========================
# CONTEXT MEMORY
# =========================
def load_context():
    return load_json(CONTEXT_FILE)

def save_context(context):
    save_json(CONTEXT_FILE, context)

# =========================
# GOALS
# =========================
def add_goal(goal_text):
    goals = load_json(GOALS_FILE)
    goal_id = str(len(goals) + 1)
    goals[goal_id] = {
        "goal": goal_text,
        "completed": False,
        "date_added": datetime.now().strftime("%Y-%m-%d")
    }
    save_json(GOALS_FILE, goals)
    return f"Goal added: {goal_text}"

def list_goals():
    goals = load_json(GOALS_FILE)
    if not goals:
        return "No goals found."
    return "\n".join(
        f"{gid}. {g['goal']} [{'✅' if g['completed'] else '❌'}]"
        for gid, g in goals.items()
    )

def complete_goal(goal_id):
    goals = load_json(GOALS_FILE)
    if goal_id in goals:
        goals[goal_id]["completed"] = True
        save_json(GOALS_FILE, goals)
        return f"Goal {goal_id} marked as completed."
    return "Goal not found."

def pending_goals():
    goals = load_json(GOALS_FILE)
    pending = [g["goal"] for g in goals.values() if not g["completed"]]
    return pending if pending else []

# =========================
# HABITS
# =========================
def add_habit(habit_text):
    habits = load_json(HABITS_FILE)
    today = datetime.now().strftime("%Y-%m-%d")
    habits.setdefault(today, []).append(habit_text)
    save_json(HABITS_FILE, habits)
    return f"Habit added: {habit_text}"

def list_habits():
    habits = load_json(HABITS_FILE)
    if not habits:
        return "No habits found."
    return "\n".join(f"{d}: {', '.join(h)}" for d, h in habits.items())

def habit_streaks():
    habits = load_json(HABITS_FILE)
    if not habits:
        return "No habit data available."

    dates = sorted(habits.keys())
    streak = 1
    max_streak = 1

    for i in range(1, len(dates)):
        prev = datetime.fromisoformat(dates[i - 1])
        curr = datetime.fromisoformat(dates[i])
        if curr - prev == timedelta(days=1):
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 1

    return f"Your longest habit streak is {max_streak} days."

# =========================
# REMINDERS
# =========================
def add_reminder(text, dt_str):
    reminders = load_json(REMINDERS_FILE)
    rid = str(len(reminders) + 1)
    reminders[rid] = {"text": text, "datetime": dt_str, "done": False}
    save_json(REMINDERS_FILE, reminders)
    return f"Reminder added: {text} at {dt_str}"

def list_reminders(date=None, only_pending=False):
    reminders = load_json(REMINDERS_FILE)
    out = []

    for rid, r in reminders.items():
        if only_pending and r["done"]:
            continue
        if date is None or r["datetime"].startswith(date):
            status = "✅" if r["done"] else "❌"
            out.append(f"{rid}. {r['text']} at {r['datetime']} [{status}]")

    return "\n".join(out) if out else "No reminders found."

def complete_reminder(reminder_id):
    reminders = load_json(REMINDERS_FILE)
    if reminder_id in reminders:
        reminders[reminder_id]["done"] = True
        save_json(REMINDERS_FILE, reminders)
        return f"Reminder {reminder_id} marked as completed."
    return "Reminder not found."

def parse_reminder_command(text):
    m = re.search(r"remind me to (.+)", text, re.I)
    if not m:
        return None, None

    remainder = m.group(1)
    dt = dateparser.parse(remainder, settings={"PREFER_DATES_FROM": "future"})
    if not dt:
        return None, None

    return remainder, dt.strftime("%Y-%m-%d %H:%M:%S")

# =========================
# LOGS + MOOD INTELLIGENCE
# =========================
def load_logs():
    rows = []
    if not os.path.exists(LOG_FILE):
        return pd.DataFrame(rows)
    with open(LOG_FILE) as f:
        for line in f:
            if "|" in line:
                ts, txt = line.split("|", 1)
                rows.append({
                    "timestamp": pd.to_datetime(ts.strip()),
                    "text": txt.strip()
                })
    return pd.DataFrame(rows)

def get_sentiment(text):
    p = TextBlob(text).sentiment.polarity
    return "Positive" if p > 0.1 else "Negative" if p < -0.1 else "Neutral"

def summarize_mood_by_period(df, year, month=None):
    df = df[df["timestamp"].dt.year == year]
    if month:
        df = df[df["timestamp"].dt.month == month]
    if df.empty:
        return "I do not have enough data for that time period."
    mood = df["text"].apply(get_sentiment).value_counts().idxmax()
    return f"Your mood during that time was mostly {mood.lower()}."

def weekly_mood_summary(df):
    last_week = datetime.now() - timedelta(days=7)
    df = df[df["timestamp"] >= last_week]
    if df.empty:
        return "No logs for the past week."
    mood = df["text"].apply(get_sentiment).value_counts().idxmax()
    return f"Your mood over the last week was mostly {mood.lower()}."

def stress_check(df):
    last_week = datetime.now() - timedelta(days=7)
    df = df[df["timestamp"] >= last_week]
    if df.empty:
        return "I don't have enough recent data."
    sentiments = df["text"].apply(TextBlob).apply(lambda t: t.sentiment.polarity)
    avg = sentiments.mean()
    if avg < -0.2:
        return "You seem more stressed or negative lately."
    return "You seem emotionally stable lately."

# =========================
# DATE PARSING + TEMPORAL
# =========================
def parse_month_year(text):
    text = text.lower()
    year = None
    month = None
    for m, num in MONTHS.items():
        if m in text:
            month = num
    y = re.search(r"(20\d{2})", text)
    if y:
        year = int(y.group(1))
    return year, month

def shift_period(year, month, direction):
    if not year:
        return None, None
    if not month:
        month = 1
    if direction == "previous":
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    elif direction == "next":
        month += 1
        if month == 13:
            month = 1
            year += 1
    return year, month

# =========================
# DAILY SUMMARY FOR WEEK 20
# =========================
def daily_summary():
    today = datetime.now().strftime("%Y-%m-%d")
    logs = load_logs()
    df_today = logs[logs["timestamp"].dt.date == datetime.now().date()]
    mood = df_today["text"].apply(get_sentiment).value_counts().idxmax() if not df_today.empty else "Neutral"

    habits = load_json(HABITS_FILE).get(today, [])
    goals = [g["goal"] for g in load_json(GOALS_FILE).values() if not g["completed"]]

    reminders = list_reminders(date=today)
    return f"Daily Summary:\nMood: {mood}\nHabits: {', '.join(habits) if habits else 'None'}\nPending Goals: {', '.join(goals) if goals else 'None'}\nReminders:\n{reminders if reminders else 'None'}"

# =========================
# COMMAND HANDLER — WEEK 20
# =========================
def handle_command(command, speak_out=True):
    text = command.lower()
    context = load_context()

    # -------- MOOD + TEMPORAL
    if "how was i" in text or "what about" in text or "my mood" in text:
        df = load_logs()
        year, month = parse_month_year(text)
        last = context.get("last_period")
        if "previous" in text or "last month" in text:
            if last:
                year, month = shift_period(last["year"], last.get("month"), "previous")
        elif "next" in text:
            if last:
                year, month = shift_period(last["year"], last.get("month"), "next")
        elif not year and last:
            year, month = last["year"], last.get("month")
        response = summarize_mood_by_period(df, year, month)
        context["last_period"] = {"year": year, "month": month}
        save_context(context)

    # -------- WEEKLY / STRESS / HABITS / REMINDERS / LIFE / COMPARE
    elif "last week" in text or "my week" in text:
        df = load_logs()
        response = weekly_mood_summary(df)
        context["last_summary"] = "weekly"
        save_context(context)

    elif "stressed" in text or "how am i lately" in text:
        df = load_logs()
        response = stress_check(df)

    elif "habit streak" in text or "consistent" in text:
        response = habit_streaks()

    elif "pending reminders" in text:
        response = list_reminders(only_pending=True)

    elif "summarize my life" in text:
        response = summarize_life()

    elif "compare" in text:
        years = re.findall(r"(20\d{2})", text)
        response = compare_years(int(years[0]), int(years[1])) if len(years) == 2 else "Specify two years."

    elif "daily summary" in text:
        response = daily_summary()

    # -------- REMINDERS
    elif "remind me to" in text:
        r, dt = parse_reminder_command(command)
        response = add_reminder(r, dt) if r else "Could not parse reminder."

    # -------- GOALS
    elif text.startswith("add goal"):
        response = add_goal(command.split(":", 1)[1].strip())
    elif text.startswith("complete goal"):
        goal_id = text.split()[-1]
        response = complete_goal(goal_id)
    elif "show my goals" in text or "list goals" in text:
        response = list_goals()

    # -------- HABITS
    elif text.startswith("add habit"):
        response = add_habit(command.split(":", 1)[1].strip())
    elif "show my habits" in text:
        response = list_habits()

    # -------- REMINDER LIST
    elif "show my reminders" in text:
        response = list_reminders()

    else:
        response = "I am still learning to reason about that."

    if speak_out:
        speak(response)

    print("🤖 SELAH:", response)
    return response
