from pydoc import text
import pandas as pd
# pyrefly: ignore [missing-import]
from textblob import TextBlob
from datetime import datetime, timedelta
# pyrefly: ignore [missing-import]
import pyttsx3
import json
import math
import os
import re
import dateparser
from collections import Counter
from web.web_intent_router import needs_web_search
from web.web_query import handle_web_query
from assistant.text_tools import summarize_text, generate_thoughts, generate_topic_content

# =========================
# FILE PATHS
# =========================
# Get absolute path to /src directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Data folder inside src
DATA_DIR = os.path.join(BASE_DIR, "data")

# File paths (same variable names, so no other code breaks)
LOG_FILE = os.path.join(BASE_DIR, "data", "daily_logs.txt")
GOALS_FILE = os.path.join(BASE_DIR, "data", "goals.json")
HABITS_FILE = os.path.join(BASE_DIR, "data", "habits.json")
REMINDERS_FILE = os.path.join(BASE_DIR, "data", "reminders.json")
CONTEXT_FILE = os.path.join(BASE_DIR, "data", "context.json")
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
# JSON STORAGE
# =========================
def save_json(path, data):
    # Make sure the folder exists
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Save the dictionary to JSON
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def load_json(path):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump({}, f)

    with open(path, "r") as f:
        return json.load(f)

# =========================
# CONTEXT MEMORY
# =========================
def load_context():
    return load_json(CONTEXT_FILE)

def save_context(ctx):
    save_json(CONTEXT_FILE, ctx)

def remember_fact(text):
    ctx = load_context()
    ctx.setdefault("facts", []).append({
        "text": text,
        "timestamp": datetime.now().isoformat()
    })
    save_context(ctx)
    return "Got it. I’ll remember that."

def recall_memory():
    facts = load_context().get("facts", [])
    return "\n".join(f"- {f['text']}" for f in facts) if facts else "I don't remember anything yet."

def load_week31_state():
    ctx = load_context()
    ctx.setdefault("risk_history", [])
    ctx.setdefault("burnout_trend", "stable")
    ctx.setdefault("recovery_window", {
        "active": False,
        "days_remaining": 0
    })
    save_context(ctx)
    return ctx


# =========================
# DAILY LOGS & MOOD ANALYSIS
# =========================

def load_logs():
    print("READING FROM:", os.path.abspath(LOG_FILE))
    if not os.path.exists(LOG_FILE):
        return pd.DataFrame(columns=["date", "text", "polarity"])

    rows = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if "|" not in line:
                continue

            date_part, text = line.split("|", 1)

            dt = pd.to_datetime(date_part.strip(), errors="coerce")
            if pd.isna(dt):
                continue

            polarity = TextBlob(text.strip()).sentiment.polarity

            rows.append({
                "date": dt,
                "text": text.strip(),
                "polarity": polarity
            })

    return pd.DataFrame(rows)

def monthly_mood_summary(year, month):
    logs = load_logs()

    if logs.empty:
        return "I don't have any daily logs yet."

    logs["year"] = logs["date"].dt.year
    logs["month"] = logs["date"].dt.month

    data = logs[(logs["year"] == year) & (logs["month"] == month)]

    if data.empty:
        return "No logs found for that month."

    avg = data["polarity"].mean()

    if math.isnan(avg):
        return "I couldn't analyze your mood for that month."

    if avg > 0.2:
        mood = "mostly positive"
    elif avg < -0.2:
        mood = "mostly negative"
    else:
        mood = "mostly neutral"

    ctx = load_context()
    ctx["last_mood_query"] = {"year": year, "month": month}
    save_context(ctx)

    return (
        f"In {datetime(year, month, 1).strftime('%B %Y')}, "
        f"your mood was {mood}."
    )


def previous_month_mood():
    today = datetime.now()
    
    # Go to first day of this month
    first_day_this_month = today.replace(day=1)
    
    # Go one day back → lands in previous month
    last_day_previous_month = first_day_this_month - timedelta(days=1)
    
    year = last_day_previous_month.year
    month = last_day_previous_month.month
    
    return monthly_mood_summary(year, month)

def parse_month_query(text):
    text = text.lower()

    if "last month" in text or "previous month" in text:
        return "PREVIOUS"

    for name, num in MONTHS.items():
        if name in text:
            year = re.findall(r"\d{4}", text)
            return int(year[0]) if year else datetime.now().year, num

    return None

# =========================
# GOAL SYSTEM
# =========================
def add_goal(text):
    goals = load_json(GOALS_FILE)
    gid = str(len(goals) + 1)
    goals[gid] = {"goal": text, "completed": False}
    save_json(GOALS_FILE, goals)
    return f"Goal added: {text}"

def list_goals():
    goals = load_json(GOALS_FILE)
    return "\n".join(
        f"{gid}. {g['goal']} [{'✅' if g['completed'] else '❌'}]"
        for gid, g in goals.items()
    ) if goals else "No goals found."

def complete_goal(gid):
    goals = load_json(GOALS_FILE)
    if gid in goals:
        goals[gid]["completed"] = True
        save_json(GOALS_FILE, goals)
        return f"Goal {gid} completed."
    return "Goal not found."

def pending_goals():
    return [g["goal"] for g in load_json(GOALS_FILE).values() if not g["completed"]]

def goal_insights():
    goals = load_json(GOALS_FILE)
    total = len(goals)
    completed = sum(1 for g in goals.values() if g["completed"])
    return f"Goals: {completed}/{total} completed." if total else "No goals yet."

# =========================
# HABIT SYSTEM
# =========================
def add_habit(text):
    habits = load_json(HABITS_FILE)
    today = datetime.now().strftime("%Y-%m-%d")
    habits.setdefault(today, []).append(text)
    save_json(HABITS_FILE, habits)
    return f"Habit added: {text}"

def list_habits():
    habits = load_json(HABITS_FILE)
    return "\n".join(f"{d}: {', '.join(h)}" for d, h in habits.items()) if habits else "No habits found."

def habit_streaks():
    habits = load_json(HABITS_FILE)
    dates = sorted(habits.keys())
    streak = max_streak = 1
    for i in range(1, len(dates)):
        if datetime.fromisoformat(dates[i]) - datetime.fromisoformat(dates[i-1]) == timedelta(days=1):
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 1
    return f"Longest habit streak: {max_streak} days." if dates else "No habit data."

def most_common_habit():
    counter = Counter()
    for h in load_json(HABITS_FILE).values():
        counter.update(h)
    return f"Most common habit: {counter.most_common(1)[0][0]}" if counter else "No habit data."

# =========================
# REMINDER SYSTEM
# =========================
def add_reminder(text, dt):
    reminders = load_json(REMINDERS_FILE)
    rid = str(len(reminders) + 1)
    reminders[rid] = {"text": text, "datetime": dt, "done": False}
    save_json(REMINDERS_FILE, reminders)
    return f"Reminder added: {text}"

def list_reminders(date=None):
    reminders = load_json(REMINDERS_FILE)
    out = []
    for rid, r in reminders.items():
        if date and not r["datetime"].startswith(date):
            continue
        out.append(f"{rid}. {r['text']} [{ '✅' if r['done'] else '❌' }]")
    return "\n".join(out) if out else "No reminders."

def parse_reminder_command(text):
    m = re.search(r"remind me to (.+)", text, re.I)
    if not m:
        return None, None
    dt = dateparser.parse(m.group(1), settings={"PREFER_DATES_FROM": "future"})
    return m.group(1), dt.strftime("%Y-%m-%d %H:%M:%S") if dt else (None, None)

# =========================
# DAILY PLANNING
# =========================
def plan_my_day():
    today = datetime.now().strftime("%Y-%m-%d")
    return "\n".join([
        "Today's Plan:",
        f"Goals: {pending_goals()[0] if pending_goals() else 'None'}",
        f"Habits: {', '.join(load_json(HABITS_FILE).get(today, []))}",
        f"Reminders:\n{list_reminders(today)}"
    ])

# =========================
# REFLECTION & INSIGHTS
# =========================
def reflect():
    return "Reflection:\n- What helped you today?\n- What drained you?"

def extract_insights():
    insights = []
    if len(load_json(HABITS_FILE)) < 3:
        insights.append("Habit consistency is low.")
    if len(pending_goals()) >= 3:
        insights.append("You may be overloading goals.")
    ctx = load_context()
    ctx.setdefault("insights", []).extend(
        {"text": i, "timestamp": datetime.now().isoformat()} for i in insights
    )
    save_context(ctx)
    return insights or ["No strong insights yet."]

def list_insights():
    return "\n".join(i["text"] for i in load_context().get("insights", [])) or "No insights yet."

# =========================
# VALUES & DECISION INTELLIGENCE
# =========================
def add_value(value):
    ctx = load_context()
    ctx.setdefault("values", []).append(value)
    save_context(ctx)
    return f"Value added: {value}"

def list_values():
    values = load_context().get("values", [])
    return "\n".join(f"- {v}" for v in values) if values else "No values defined."

def evaluate_decision(text):
    values = load_context().get("values", [])
    goals = pending_goals()
    return (
        f"Decision: {text}\n"
        f"Values: {', '.join(values) if values else 'None'}\n"
        f"Consider alignment with long-term consistency."
    )

# =========================
# EMOTIONAL TREND ANALYSIS
# =========================

def emotional_trend(days=14):
    logs = load_logs()
    if logs.empty:
        return "I don’t have enough data yet."

    cutoff = datetime.now() - timedelta(days=days)
    recent = logs[logs["date"] >= cutoff]

    if len(recent) < 5:
        return "Not enough recent data to detect a trend."

    avg = recent["polarity"].mean()

    if avg > 0.15:
        trend = "improving"
    elif avg < -0.15:
        trend = "declining"
    else:
        trend = "stable"

    ctx = load_context()
    ctx["emotional_trend"] = {
        "trend": trend,
        "days": days,
        "timestamp": datetime.now().isoformat()
    }
    save_context(ctx)

    return f"Over the last {days} days, your emotional trend looks **{trend}**."

def update_risk_history(risk_label):
    ctx = load_week31_state()
    ctx["risk_history"].append({
        "risk": risk_label,
        "timestamp": datetime.now().isoformat()
    })
    ctx["risk_history"] = ctx["risk_history"][-14:]  # keep last 14 entries
    save_context(ctx)



# =========================
# BURNOUT DETECTION
# =========================

def detect_burnout():
    logs = load_logs()
    if logs.empty:
        return "I don’t have enough emotional data yet."

    recent = logs[logs["date"] >= datetime.now() - timedelta(days=10)]

    if len(recent) < 5:
        return "Not enough data to assess burnout."

    negative_days = recent[recent["polarity"] < -0.2]

    if len(negative_days) >= 5:
        insight = "You may be experiencing early burnout signs."
    else:
        insight = "No strong burnout signals detected."

    ctx = load_context()
    ctx.setdefault("burnout_checks", []).append({
        "result": insight,
        "timestamp": datetime.now().isoformat()
    })
    save_context(ctx)

    return insight

def burnout_prediction():
    ctx = load_week31_state()
    risks = [r["risk"] for r in ctx["risk_history"]]

    high_risk = risks.count("high")
    mild_risk = risks.count("mild")

    if high_risk >= 3:
        ctx["burnout_trend"] = "high"
        save_context(ctx)
        return "🔴 Burnout likely within 7–10 days if patterns continue."

    if mild_risk >= 4:
        ctx["burnout_trend"] = "rising"
        save_context(ctx)
        return "🟡 Burnout probability rising. Consider slowing down."

    ctx["burnout_trend"] = "stable"
    save_context(ctx)
    return "🟢 Burnout risk currently stable."

def predict_burnout_window():
    ctx = load_context()
    risk_history = ctx.get("risk_history", [])[-10:]

    if len(risk_history) < 3:
        return "Burnout prediction: Insufficient data."

    levels = [r["level"] for r in risk_history]
    high_count = levels.count("high")
    mild_count = levels.count("mild")

    goals = load_json(GOALS_FILE)
    pending_goals = [g for g in goals.values() if not g["completed"]]

    habit_days = sorted(load_json(HABITS_FILE).keys())
    continuous_habits = 0
    for i in range(1, len(habit_days)):
        if datetime.fromisoformat(habit_days[i]) - datetime.fromisoformat(habit_days[i-1]) == timedelta(days=1):
            continuous_habits += 1
        else:
            continuous_habits = 0

    signals = 0
    if high_count >= 2:
        signals += 1
    if mild_count >= 3:
        signals += 1
    if len(pending_goals) >= 4:
        signals += 1
    if continuous_habits >= 5:
        signals += 1

    if signals >= 2:
        return (
            "⚠️ Burnout Risk Forecast:\n"
            "- Pattern indicates rising fatigue\n"
            "- Burnout likely in ~3–5 days if load continues\n"
            "- Recommendation: initiate recovery mode early"
        )

    return "🟢 Burnout forecast: No immediate risk detected."


# =========================
# EMOTIONAL FORECASTING
# =========================

def emotional_forecast(days_back=14, forecast_days=3):
    logs = load_logs()
    if logs.empty:
        return "I don’t have enough data to forecast your mood yet."

    recent = logs[logs["date"] >= datetime.now() - timedelta(days=days_back)]

    if len(recent) < 6:
        return "Not enough recent emotional data to generate a forecast."

    avg = recent["polarity"].mean()
    slope = recent["polarity"].diff().mean()

    if avg < -0.2 and slope < 0:
        outlook = "likely to worsen"
    elif avg > 0.2 and slope > 0:
        outlook = "likely to improve"
    else:
        outlook = "likely to remain stable"

    forecast = (
        f"Over the next {forecast_days} days, your emotional state is "
        f"**{outlook}** based on recent patterns."
    )

    ctx = load_context()
    ctx.setdefault("forecasts", []).append({
        "outlook": outlook,
        "avg_polarity": avg,
        "trend": slope,
        "timestamp": datetime.now().isoformat()
    })
    save_context(ctx)

    return forecast

# =========================
# SELF-INTERVENTION ENGINE
# =========================

def suggest_intervention():
    logs = load_logs()
    habits = load_json(HABITS_FILE)
    goals = load_json(GOALS_FILE)

    suggestions = []

    if not logs.empty:
        recent = logs[logs["date"] >= datetime.now() - timedelta(days=5)]
        if recent["polarity"].mean() < -0.2:
            suggestions.append("Reduce cognitive load — do one small, easy task today.")

    if len(pending_goals()) >= 3:
        suggestions.append("Pause goal expansion. Focus on completion, not ambition.")

    if not habits:
        suggestions.append("Anchor one grounding habit (walk, breath, journaling).")

    if not suggestions:
        suggestions.append("Maintain current rhythm. You’re stable right now.")

    ctx = load_context()
    ctx.setdefault("interventions", []).append({
        "suggestions": suggestions,
        "timestamp": datetime.now().isoformat()
    })
    save_context(ctx)

    return "Suggested Interventions:\n" + "\n".join(f"- {s}" for s in suggestions)

# =========================
# IDENTITY PATTERN ENGINE
# =========================

def extract_identity_patterns():
    logs = load_logs()
    if logs.empty or len(logs) < 10:
        return ["Not enough data to extract identity patterns yet."]

    patterns = []
    logs = logs.sort_values("date")

    for i in range(1, len(logs)):
        prev = logs.iloc[i - 1]
        curr = logs.iloc[i]

        if prev["polarity"] < -0.3 and curr["polarity"] < -0.3:
            patterns.append("When emotionally low → tendency to stay low")

        if prev["polarity"] < -0.2 and curr["polarity"] > 0.2:
            patterns.append("Emotional recovery after reflection or rest")

    counter = Counter(patterns)
    dominant = [p for p, c in counter.items() if c >= 2]

    ctx = load_context()
    ctx["identity_patterns"] = dominant
    save_context(ctx)

    return dominant if dominant else ["No dominant identity patterns detected yet."]

# =========================
# EMOTIONAL TRIGGERS
# =========================

def detect_triggers():
    logs = load_logs()
    if logs.empty:
        return ["No data available to detect triggers."]

    trigger_words = []
    for text in logs["text"]:
        if re.search(r"(tired|exhausted|overwhelmed|stressed)", text, re.I):
            trigger_words.append("Fatigue / overload")

        if re.search(r"(alone|ignored|unseen)", text, re.I):
            trigger_words.append("Social disconnection")

        if re.search(r"(fail|behind|not enough)", text, re.I):
            trigger_words.append("Self-judgment")

    counter = Counter(trigger_words)
    triggers = [t for t, c in counter.items() if c >= 2]

    ctx = load_context()
    ctx["triggers"] = triggers
    save_context(ctx)

    return triggers if triggers else ["No strong emotional triggers detected yet."]

def emotional_risk_monitor(days=14):
    if not os.path.exists(LOG_FILE):
        return "No logs available."

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        raw = f.read()

    entries = re.split(r"\n(?=\d{4}-\d{2}-\d{2})", raw)
    recent = entries[-days:]

    sentiments = []
    pressure_words = ["behind", "should", "must", "need to", "have to"]

    pressure_count = 0
    for entry in recent:
        blob = TextBlob(entry)
        sentiments.append(blob.sentiment.polarity)
        for w in pressure_words:
            pressure_count += entry.lower().count(w)

    if len(sentiments) < 5:
        return "Not enough recent data for risk analysis."

    trend = sum(sentiments[-7:]) / 7 - sum(sentiments[:7]) / 7

    if trend < -0.15 and pressure_count >= 5:
        return (
            "⚠️ Emotional Risk Detected:\n"
            "Sustained effort with declining emotional tone.\n"
            "Consider reducing load or adding recovery time."
        )

    if trend < -0.08:
        return "🟡 Mild fatigue trend detected. Stay aware."

    return "🟢 Emotional state stable."


# =========================
# EARLY WARNING SYSTEM
# =========================

def early_warning():
    ctx = load_context()
    patterns = ctx.get("identity_patterns", [])
    triggers = ctx.get("triggers", [])

    warnings = []

    if "Fatigue / overload" in triggers:
        warnings.append("⚠️ When tired, you are more likely to spiral emotionally.")

    if "When emotionally low → tendency to stay low" in patterns:
        warnings.append("⚠️ Emotional inertia detected. Early interruption is critical.")

    if not warnings:
        warnings.append("No immediate emotional risk detected.")

    ctx.setdefault("warnings", []).append({
        "warnings": warnings,
        "timestamp": datetime.now().isoformat()
    })
    save_context(ctx)

    return "Early Warning Report:\n" + "\n".join(warnings)

def early_warning_nudge():
    ctx = load_week31_state()
    risks = [r["risk"] for r in ctx["risk_history"]]

    if risks.count("mild") >= 3:
        return "⚠️ Early warning: Emotional load increasing. Plan a lighter day."

    if ctx["burnout_trend"] == "rising":
        return "⚠️ You’re trending toward burnout. Slow goal velocity."

    return None


# =========================
# RECOVERY RECOMMENDATION SYSTEM
# =========================
def recovery_recommendation():
    # Call emotional risk monitor safely (no arguments)
    risk = emotional_risk_monitor()

    goals = load_json(GOALS_FILE)
    pending = [g for g in goals.values() if not g["completed"]]

    habit_days = load_json(HABITS_FILE)
    recent_habits = list(habit_days.keys())[-5:]

    recommendation = []

    if "⚠️ Emotional Risk Detected" in risk:
        recommendation.append(
            "🔴 High Load Detected:\n"
            "- Pause outcome-based goals for 72 hours\n"
            "- Maintain only identity habits (sleep, movement)\n"
            "- Do not add new goals"
        )

    elif "🟡 Mild fatigue" in risk:
        recommendation.append(
            "🟡 Mild Fatigue Response:\n"
            "- Reduce goal intensity by ~20%\n"
            "- Keep habits lightweight\n"
            "- Schedule one low-effort recovery activity"
        )

    else:
        recommendation.append(
            "🟢 System Stable:\n"
            "- Maintain current goals\n"
            "- No recovery adjustment needed"
        )

    if len(pending) >= 4:
        recommendation.append("⚠️ You may be carrying too many active goals.")

    if len(recent_habits) >= 5 and len(set(recent_habits)) == 5:
        recommendation.append("⚠️ No habit rest days detected.")

    if "⚠️ Emotional Risk Detected" in risk:
        update_risk_history("high")
        adaptive_recovery_adjustment("high")

    elif "🟡 Mild fatigue" in risk:
        update_risk_history("mild")
        adaptive_recovery_adjustment("mild")

    else:
        update_risk_history("stable")
        adaptive_recovery_adjustment("stable")

    recommendation.append(resume_deferred_goal())
    return "\n".join(recommendation)




def adaptive_recovery_adjustment(risk_label):
    ctx = load_week31_state()
    recovery = ctx["recovery_window"]

    if risk_label == "high":
        recovery["active"] = True
        recovery["days_remaining"] = max(recovery["days_remaining"], 3)

    elif risk_label == "mild":
        recovery["active"] = True
        recovery["days_remaining"] = max(recovery["days_remaining"], 1)

    else:
        if recovery["days_remaining"] > 0:
            recovery["days_remaining"] -= 1
        if recovery["days_remaining"] <= 0:
            recovery["active"] = False

    ctx["recovery_window"] = recovery
    save_context(ctx)

# -----------------------------
# Goal State Normalization & Rebalancing (Week 33)
# -----------------------------

def normalize_goal_states():
    goals = load_json(GOALS_FILE)
    updated = False

    for g in goals.values():
        if "state" not in g:
            g["state"] = "completed" if g.get("completed") else "active"
            updated = True

    if updated:
        save_json(GOALS_FILE, goals)

def auto_rebalance_goals():
    normalize_goal_states()
    forecast = predict_burnout_window()

    if "Burnout Risk Forecast" not in forecast:
        return "🟢 Goals stable. No rebalancing needed."

    goals = load_json(GOALS_FILE)
    deferred = []

    for gid, g in goals.items():
        if g["state"] == "active" and not g.get("completed"):
            g["state"] = "deferred"
            deferred.append(g["goal"])
            break  

    save_json(GOALS_FILE, goals)

    if not deferred:
        return "⚠️ Burnout risk detected, but no active goals to defer."

    return (
        "⚖️ Goal Rebalanced Automatically:\n"
        f"- Deferred: {deferred[0]}\n"
        "- Reason: rising burnout risk\n"
        "- This goal will resume after recovery"
    )

# -----------------------------
# Goal Resumption Intelligence (Week 34)
# -----------------------------

def is_system_stable_recently(days=3):
    """
    Checks if emotional system has been stable for the last N checks
    """
    ctx = load_context()
    history = ctx.get("risk_history", [])

    if len(history) < days:
        return False

    recent = history[-days:]
    return all(r["level"] == "stable" for r in recent)


def resume_deferred_goal():
    """
    Resumes one deferred goal if recovery is sustained
    """
    if not is_system_stable_recently():
        return "⏳ Recovery still in progress. Goals remain deferred."

    goals = load_json(GOALS_FILE)

    for g in goals.values():
        if g.get("state") == "deferred":
            g["state"] = "active"
            save_json(GOALS_FILE, goals)

            return (
                "🟢 Goal Resumed Automatically:\n"
                f"- {g['goal']}\n"
                "- Reason: emotional stability maintained"
            )

    return "🟢 No deferred goals to resume."

# =========================
# PERSONALITY EVOLUTION ENGINE
# =========================

def emotional_stability_index(month=None, year=None):
    df = load_logs()
    if df.empty:
        return "No log data available."

    # Ensure datetime column exists
    if "timestamp" not in df.columns:
        if "date" in df.columns:
            df["timestamp"] = pd.to_datetime(df["date"])
        else:
            return "Log format error: No timestamp column found."

    df["polarity"] = df["text"].apply(lambda x: TextBlob(x).sentiment.polarity)

    if month and year:
        df = df[
            (df["timestamp"].dt.month == month) &
            (df["timestamp"].dt.year == year)
        ]

    if df.empty:
        return "No logs for that period."

    variance = df["polarity"].var()

    if variance is None:
        return "Not enough data."

    if variance < 0.02:
        level = "Highly Stable"
    elif variance < 0.08:
        level = "Moderately Stable"
    else:
        level = "Emotionally Volatile"

    return f"Emotional Stability: {level} (Variance: {round(variance,3)})"

def growth_direction_analysis():
    df = load_logs()
    if df.empty:
        return "No log data available."

    if "timestamp" not in df.columns:
        if "date" in df.columns:
            df["timestamp"] = pd.to_datetime(df["date"])
        else:
            return "Log format error: No timestamp column found."

    df["polarity"] = df["text"].apply(lambda x: TextBlob(x).sentiment.polarity)
    df = df.sort_values("timestamp")

    midpoint = len(df) // 2
    if midpoint == 0:
        return "Not enough data."

    first_half = df.iloc[:midpoint]["polarity"].mean()
    second_half = df.iloc[midpoint:]["polarity"].mean()

    if second_half > first_half + 0.05:
        return "📈 Emotional trajectory improving over time."
    elif second_half < first_half - 0.05:
        return "📉 Emotional trajectory declining recently."
    else:
        return "➖ Emotional trajectory relatively stable."

def identity_shift_analysis():
    df = load_logs()
    if df.empty:
        return "No log data available."

    if "timestamp" not in df.columns:
        if "date" in df.columns:
            df["timestamp"] = pd.to_datetime(df["date"])
        else:
            return "Log format error: No timestamp column found."

    df = df.sort_values("timestamp")

    midpoint = len(df) // 2
    if midpoint == 0:
        return "Not enough data."

    early_logs = " ".join(df.iloc[:midpoint]["text"]).lower()
    recent_logs = " ".join(df.iloc[midpoint:]["text"]).lower()

    early_positive = early_logs.count("hope") + early_logs.count("excited")
    recent_discipline = (
        recent_logs.count("discipline") +
        recent_logs.count("training") +
        recent_logs.count("control")
    )

    if recent_discipline > early_positive:
        return "Identity shift detected: Moving toward structured discipline."
    else:
        return "No major identity shift detected."

def transformation_summary():
    stability = emotional_stability_index()
    growth = growth_direction_analysis()
    identity = identity_shift_analysis()

    return (
        "Long-Term Transformation Analysis:\n"
        f"- {stability}\n"
        f"- {growth}\n"
        f"- {identity}"
    )

# =========================
# COGNITIVE DISTORTION DETECTOR
# =========================

def detect_cognitive_distortions():
    df = load_logs()
    if df.empty:
        return "No logs available."

    distortions = {
        "all_or_nothing": ["always", "never", "completely", "totally"],
        "catastrophizing": ["ruined", "disaster", "unbearable", "worst"],
        "mind_reading": ["they think", "they must think", "everyone thinks"],
        "self_blame": ["my fault", "i ruined", "i messed up", "foolish"]
    }

    detected = []

    for text in df["text"]:
        t = text.lower()
        for label, keywords in distortions.items():
            if any(word in t for word in keywords):
                detected.append(label)

    if not detected:
        return "No strong cognitive distortions detected."

    summary = Counter(detected)
    return "Cognitive Patterns Detected:\n" + "\n".join(
        f"- {k.replace('_',' ').title()} ({v} times)"
        for k, v in summary.items()
    )

# =========================
# OVERTHINKING LOOP ANALYSIS
# =========================

def detect_mental_loops():
    df = load_logs()
    if df.empty:
        return "No logs available."

    df["polarity"] = df["text"].apply(lambda x: TextBlob(x).sentiment.polarity)
    negative_days = df[df["polarity"] < -0.2]

    if len(negative_days) >= 3:
        return "⚠️ Repeated negative emotional cycle detected."
    elif len(negative_days) == 2:
        return "Mild emotional repetition pattern detected."
    else:
        return "No strong emotional loops detected."

# =========================
# THOUGHT REFRAMING SYSTEM
# =========================

def reframe_thought():
    distortions = detect_cognitive_distortions()

    if "Catastrophizing" in distortions:
        return (
            "Reframe:\n"
            "Ask yourself — Is this truly permanent, or temporary?\n"
            "What is one small controllable action right now?"
        )

    if "All Or Nothing" in distortions:
        return (
            "Reframe:\n"
            "Progress is not binary.\n"
            "What is one small improvement instead of perfection?"
        )

    if "Self Blame" in distortions:
        return (
            "Reframe:\n"
            "Mistakes are data, not identity.\n"
            "What did this situation teach you?"
        )

    return "No strong distortions to reframe right now."

# =========================
# IDENTITY ANCHOR ANALYSIS
# =========================

def identity_anchor_map():
    df = load_logs()
    if df.empty:
        return "No logs available."

    themes = {
        "resilience": ["recovery", "trying", "stay strong", "comeback", "rebuild"],
        "faith": ["bible", "pray", "god", "proverbs", "faith"],
        "family": ["brother", "parents", "family", "home"],
        "discipline": ["training", "practice", "team", "study", "exams"],
        "isolation": ["alone", "boring", "no friends", "not talking"]
    }

    detected = []

    for text in df["text"]:
        t = text.lower()
        for label, words in themes.items():
            if any(word in t for word in words):
                detected.append(label)

    if not detected:
        return "No strong identity anchors detected."

    summary = Counter(detected)

    return "Identity Anchors:\n" + "\n".join(
        f"- {k.title()} ({v} references)"
        for k, v in summary.items()
    )

# =========================
# EMOTIONAL DEPENDENCY ANALYSIS
# =========================

def emotional_dependency_check():
    df = load_logs()
    if df.empty:
        return "No logs available."

    dependency_terms = ["football", "injury", "friend", "team"]

    dependency_count = 0
    total_entries = len(df)

    for text in df["text"]:
        if any(term in text.lower() for term in dependency_terms):
            dependency_count += 1

    if total_entries == 0:
        return "No data."

    ratio = dependency_count / total_entries

    if ratio > 0.4:
        return "⚠️ Strong emotional dependency detected on a single life domain."
    elif ratio > 0.2:
        return "Moderate emotional dependency pattern detected."
    else:
        return "No strong emotional dependency pattern."

# =========================
# SELF CONCEPT STABILITY INDEX
# =========================

def self_concept_stability():
    df = load_logs()
    if df.empty:
        return "No logs available."

    df["polarity"] = df["text"].apply(lambda x: TextBlob(x).sentiment.polarity)

    volatility = df["polarity"].std()

    if volatility > 0.6:
        return "⚠️ High emotional volatility — identity instability risk."
    elif volatility > 0.3:
        return "Moderate emotional variability."
    else:
        return "Stable emotional identity pattern."

# =========================
# LIFE CHAPTER DETECTION
# =========================

def detect_life_chapters():
    df = load_logs()
    if df.empty:
        return "No logs available."

    df = df.sort_values("timestamp")
    df["polarity"] = df["text"].apply(lambda x: TextBlob(x).sentiment.polarity)

    chapters = []
    current_chapter = []
    threshold = 0.4

    for i in range(1, len(df)):
        shift = abs(df.iloc[i]["polarity"] - df.iloc[i-1]["polarity"])
        current_chapter.append(df.iloc[i-1]["text"])

        if shift > threshold:
            chapters.append(current_chapter)
            current_chapter = []

    if current_chapter:
        chapters.append(current_chapter)

    return f"Detected {len(chapters)} emotional life chapters."

# =========================
# PERSONAL MYTH EXTRACTION
# =========================

def personal_myth():
    df = load_logs()
    if df.empty:
        return "No logs available."

    text_blob = " ".join(df["text"].tolist()).lower()

    myth_elements = []

    if "injury" in text_blob:
        myth_elements.append("The Wounded Warrior")

    if "recovery" in text_blob or "comeback" in text_blob:
        myth_elements.append("The Rebuilder")

    if "faith" in text_blob or "bible" in text_blob:
        myth_elements.append("The Faith-Driven Seeker")

    if "team" in text_blob:
        myth_elements.append("The Leader in Formation")

    if not myth_elements:
        return "No dominant myth detected."

    return "Your evolving personal myth:\n- " + "\n- ".join(myth_elements)

# =========================
# COGNITIVE PATTERN ANALYSIS
# =========================

def cognitive_pattern_analysis():
    df = load_logs()
    if df.empty:
        return "No logs available."

    patterns = {
        "catastrophizing": ["always", "never", "ruined", "unbearable"],
        "self-blame": ["my fault", "foolish", "regret"],
        "growth mindset": ["learning", "improving", "trying"],
    }

    detected = Counter()

    for text in df["text"]:
        t = text.lower()
        for label, words in patterns.items():
            if any(w in t for w in words):
                detected[label] += 1

    if not detected:
        return "No strong cognitive distortions detected."

    return "Cognitive tendencies:\n" + "\n".join(
        f"- {k}: {v} instances"
        for k, v in detected.items()
    )

# =========================
# THINKING EVOLUTION TRACKER
# =========================

def thinking_evolution():
    df = load_logs()
    if df.empty:
        return "No logs available."

    df = df.sort_values("timestamp")
    df["polarity"] = df["text"].apply(lambda x: TextBlob(x).sentiment.polarity)

    first_half = df.iloc[:len(df)//2]["polarity"].mean()
    second_half = df.iloc[len(df)//2:]["polarity"].mean()

    if second_half > first_half:
        return "Your thinking pattern shows overall positive evolution."
    else:
        return "Your cognitive tone has become more heavy over time."

# =========================
# FULL SELF SYSTEM REPORT
# =========================

def full_self_system_report():
    report = []

    report.append(identity_anchor_map())
    report.append(emotional_dependency_check())
    report.append(self_concept_stability())
    report.append(cognitive_pattern_analysis())
    report.append(thinking_evolution())

    return "\n\n---\n\n".join(report)

# =========================
# AUTONOMOUS LIFE STATUS
# =========================

def life_system_status():
    risk = emotional_risk_monitor()
    stability = self_concept_stability()

    if "High" in risk:
        return "System under psychological strain."

    if "Stable" in stability:
        return "System operating in stable adaptive mode."

    return "System adapting."


# =========================
# SMART JOURNAL PROCESSING
# =========================
def process_journal(text):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{now} | {text}\n")
    
    t = text.lower()
    
    extracted_habits = []
    habit_keywords = ["ran ", "run ", "walk", "meditate", "read", "gym", "workout", "study", "slept", "water"]
    for kw in habit_keywords:
        if kw in t:
            add_habit(kw.capitalize().strip())
            extracted_habits.append(kw.strip())
    
    extracted_goals = []
    goal_matches = re.findall(r"(?:want to|need to|goal is to|plan to)\s+([a-zA-Z\s]+?)(?:\.|\,|$|and|but)", t)
    for g in goal_matches:
        goal_text = g.strip().capitalize()
        if len(goal_text) > 3:
            add_goal(goal_text)
            extracted_goals.append(goal_text)
            
    mood_score = TextBlob(text).sentiment.polarity
    mood_desc = "Positive" if mood_score > 0.1 else "Negative" if mood_score < -0.1 else "Neutral"
    
    response = [f"📖 Journal logged ({mood_desc} tone)."]
    if extracted_habits:
        response.append(f"✅ Auto-tracked habits: {', '.join(extracted_habits)}")
    if extracted_goals:
        response.append(f"🎯 Auto-added goals: {', '.join(extracted_goals)}")
        
    # 1. Stress / Burnout Detection
    stress_keywords = ["tired", "exhausted", "overwhelmed", "stressed", "burnout", "give up", "struggling"]
    if any(w in t for w in stress_keywords):
        response.append("⚠️ Stress detected in your entry. Consider triggering 'what should i do' for recovery steps.")
        
    # 2. Cognitive Distortion Check
    distortions = []
    if any(w in t for w in ["always", "never", "ruined", "disaster"]):
        distortions.append("All-or-Nothing / Catastrophizing")
    if any(w in t for w in ["my fault", "i messed up", "foolish"]):
        distortions.append("Self-Blame")
    if distortions:
        response.append(f"🧠 Cognitive pattern noticed: {', '.join(distortions)}. (Try saying 'reframe my thoughts'!)")
        
    # 3. Identity Anchor Check
    anchors = []
    if any(w in t for w in ["pray", "god", "faith", "bible"]): anchors.append("Faith")
    if any(w in t for w in ["family", "brother", "parents", "home"]): anchors.append("Family")
    if any(w in t for w in ["training", "practice", "study", "discipline", "workout", "gym"]): anchors.append("Discipline")
    if anchors:
        response.append(f"⚓ Anchors grounded today: {', '.join(anchors)}")
        
    return "\n".join(response)

# ==========================================
# ADVANCED AI SYSTEM & PERSONA SPECIFICATIONS
# ==========================================

CORE_OS_SYSTEM = (
    "You are SELAH_OS, an advanced cybernetic personal assistant operating system. "
    "Your tone is cool, highly structured, technical, and precise. "
    "Incorporate telemetry metadata in your responses (e.g. '[SYS_ALERT]', '[METRIC_SCAN]', '[DECRYPTION_SUCCESS]'). "
    "Keep your answers efficient, clear, and logical. You analyze the user's life telemetry as raw inputs."
)

COACH_SYSTEM = (
    "You are SELAH, playing the role of an Empathetic Coach and mental wellness partner. "
    "Your tone is exceptionally warm, gentle, compassionate, and reassuring. "
    "Validate the user's feelings, emphasize self-care, and encourage physical/emotional recovery. "
    "Always frame struggles (like knee rehab, exam stress, or loneliness) as natural, temporary parts of their growth journey. "
    "Provide comfort and support. Keep answers relatively concise but deeply caring."
)

SAGE_SYSTEM = (
    "You are SELAH, acting as a Socratic Sage and wise philosophical companion. "
    "Your tone is reflective, thoughtful, deep, and intellectually stimulating. "
    "Guide the user to find their own answers by asking gentle, introspective Socratic questions. "
    "Draw upon philosophical concepts, faith patterns, and long-term perspective. "
    "Encourage discipline, wisdom, and inner growth. Speak with calm, structured clarity."
)

def call_gemini(prompt, system_instruction=None, api_key=None, model_preference=None):
    """
    Sends a query to the Google Gemini LLM API, using the API key loaded from .env or supplied by client.
    """
    try:
        import google.generativeai as genai
    except ImportError:
        return "Error: To access advanced AI features, run: pip install google-generativeai"

    # Use client override API key if provided
    active_api_key = api_key
    if not active_api_key:
        active_api_key = os.getenv("GEMINI_API_KEY")
    
    if not active_api_key:
        try:
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("GEMINI_API_KEY="):
                            active_api_key = line.split("=", 1)[1].strip()
                            break
        except Exception:
            pass

    if not active_api_key:
        return "I need a GEMINI_API_KEY environment variable to generate content. Please ensure it is present in your .env file."

    try:
        genai.configure(api_key=active_api_key)
        
        # Dynamically discover active models
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        model_name = "gemini-1.5-flash"  # standard fallback
        
        if available_models:
            pref = str(model_preference).lower() if model_preference else ""
            if "pro" in pref:
                # Find a pro model
                pro_models = [m for m in available_models if "pro" in m.lower()]
                if pro_models:
                    model_name = pro_models[0]
                else:
                    model_name = available_models[0]
            elif "normal" in pref or "flash" in pref:
                # Find a flash model
                flash_models = [m for m in available_models if "flash" in m.lower()]
                if flash_models:
                    model_name = flash_models[0]
                else:
                    model_name = available_models[0]
            else:
                model_name = available_models[0]
        else:
            # Hardcoded fallbacks if list_models fails but key is valid
            pref = str(model_preference).lower() if model_preference else ""
            if "pro" in pref:
                model_name = "gemini-1.5-pro"
            else:
                model_name = "gemini-1.5-flash"
        
        if system_instruction:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_instruction
            )
        else:
            model = genai.GenerativeModel(model_name=model_name)

        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"SELAH AI Core error: {str(e)}"

def ai_reframe_thought(thought, system_instruction, api_key=None, model_preference=None):
    """
    Analyzes negative thoughts and reframes them using Socratic reframing techniques.
    """
    logs_context = ""
    try:
        logs = load_logs()
        if not logs.empty:
            recent_entries = logs.tail(5)["text"].tolist()
            logs_context = "\nRecent Journal History Context:\n" + "\n".join(f"- {e}" for e in recent_entries)
    except Exception:
        pass

    prompt = (
        f"The user has requested cognitive reframing for the following thought:\n"
        f"Thought: \"{thought}\"\n\n"
        f"{logs_context}\n\n"
        f"Task:\n"
        f"1. Identify if any cognitive distortions are present (e.g., Catastrophizing, All-or-Nothing thinking, Self-Blame, Mind Reading).\n"
        f"2. Engage the user in a personalized, Socratic dialogue to dissect the assumptions behind this thought.\n"
        f"3. Provide two actionable reframed perspectives that are grounded, realistic, and positive.\n\n"
        f"Structure your response beautifully with bold headings and markdown."
    )
    return call_gemini(prompt, system_instruction=system_instruction, api_key=api_key, model_preference=model_preference)

def ai_interpret_dream(dream_desc, system_instruction, api_key=None, model_preference=None):
    """
    Provides a psychoanalytic dream interpretation, tying symbol analysis to the user's real-life context.
    """
    logs_context = ""
    try:
        logs = load_logs()
        if not logs.empty:
            recent_entries = logs.tail(10)["text"].tolist()
            logs_context = "\nUser's Recent Life Context (injury recovery, exams study, training, faith, family):\n" + "\n".join(f"- {e}" for e in recent_entries)
    except Exception:
        pass

    prompt = (
        f"The user wants an interpretation of their dream:\n"
        f"Dream: \"{dream_desc}\"\n\n"
        f"{logs_context}\n\n"
        f"Task:\n"
        f"1. Provide a beautiful psychoanalytic interpretation of the symbols and emotional undertones in this dream.\n"
        f"2. Crucially, correlate these dream symbols directly to the user's actual life challenges and anchors "
        f"(e.g., knee surgery rehabilitation, study strain, leadership conflicts, or faith/discipline anchors) "
        f"based on the provided life context.\n"
        f"3. Offer an empowering wellness takeaway.\n\n"
        f"Structure the response beautifully using markdown."
    )
    return call_gemini(prompt, system_instruction=system_instruction, api_key=api_key, model_preference=model_preference)

def ai_weekly_wisdom(system_instruction, api_key=None, model_preference=None):
    """
    Aggregates logs, goals, and habits into a structured weekly wisdom psychological report.
    """
    logs_context = ""
    goals_context = ""
    habits_context = ""
    
    try:
        logs = load_logs()
        if not logs.empty:
            recent_entries = logs.tail(15)
            logs_context = "\nRecent Journal Logs (last 15 entries):\n" + "\n".join(
                f"- {row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else row['date']}: {row['text']}" 
                for _, row in recent_entries.iterrows()
            )
    except Exception:
        pass

    try:
        goals = load_json(GOALS_FILE)
        if goals:
            goals_context = "\nUser's Goals:\n" + "\n".join(
                f"- {g['goal']} (Status: {g.get('state', 'active')}, Completed: {g.get('completed', False)})" 
                for g in goals.values()
            )
    except Exception:
        pass

    try:
        habits = load_json(HABITS_FILE)
        if habits:
            habits_context = "\nTracked Habits:\n" + "\n".join(
                f"- {d}: {', '.join(h)}" 
                for d, h in list(habits.items())[-5:]
            )
    except Exception:
        pass

    prompt = (
        f"Generate a deep, comprehensive 'Weekly Wisdom & Psychological Synthesis' based on the user's data:\n\n"
        f"{logs_context}\n\n"
        f"{goals_context}\n\n"
        f"{habits_context}\n\n"
        f"Task:\n"
        f"1. Analyze the user's emotional trajectory, highlight progress in coping with knee injury recovery, exam stress, or anger management.\n"
        f"2. Synthesize key themes, repeating loops, or subconscious anchors (like faith, study discipline, or family connection).\n"
        f"3. Evaluate goal velocity and balance. Address if they are overloading goals or need recovery.\n"
        f"4. Provide a structured, beautiful, and deeply empowering wellness synthesis with actionable philosophical/coaching guidance.\n\n"
        f"Format the output as a premium report."
    )
    return call_gemini(prompt, system_instruction=system_instruction, api_key=api_key, model_preference=model_preference)

# ==========================================
# COMMAND ROUTER (SINGLE SOURCE OF TRUTH)
# ==========================================
def handle_command(command, speak_out=True, persona="os", api_key=None, model_preference=None):
    text = command.lower()
    print("Web detection result:", needs_web_search(text))

    # Resolve active persona instructions
    p = persona.lower()
    if p == "coach":
        system_instruction = COACH_SYSTEM
    elif p == "sage":
        system_instruction = SAGE_SYSTEM
    else:
        system_instruction = CORE_OS_SYSTEM

    # -----------------------------
    # 1. Advanced Interactive AI Commands
    # -----------------------------
    if text.startswith("reframe:") or "reframe my thought" in text:
        thought_content = command.split(":", 1)[1].strip() if ":" in command else command.replace("reframe my thoughts", "").replace("reframe my thought", "").strip()
        if not thought_content:
            response = "What thought would you like me to reframe? Format as 'reframe: [your thought]'."
        else:
            response = ai_reframe_thought(thought_content, system_instruction, api_key=api_key, model_preference=model_preference)

    elif text.startswith("dream:") or text.startswith("interpret my dream:") or text.startswith("dream interpretation:"):
        dream_content = command.split(":", 1)[1].strip()
        if not dream_content:
            response = "Please share the dream details! Format as 'dream: [dream description]'."
        else:
            response = ai_interpret_dream(dream_content, system_instruction, api_key=api_key, model_preference=model_preference)

    elif "weekly wisdom" in text or "generate synthesis" in text:
        response = ai_weekly_wisdom(system_instruction, api_key=api_key, model_preference=model_preference)

    elif "scan screen" in text or "scan my screen" in text or "screen awareness" in text or "capture my screen" in text or "what is on my screen" in text:
        from assistant.vision_agent import capture_and_analyze_screen
        response = capture_and_analyze_screen(persona, api_key=api_key, model_preference=model_preference)

    elif text.startswith("detect spam:") or text.startswith("check spam:") or text.startswith("spam check:") or text.startswith("is this spam:"):
        from assistant.spam_detector import detect_spam
        content = command.split(":", 1)[1].strip()
        response = detect_spam(content)

    elif text.startswith("os:") or text.startswith("execute:") or any(kw in text for kw in ["clean downloads", "start dev environment", "convert png to jpg", "npm run dev"]):
        from assistant.os_agent import dispatch_os_command
        cmd_content = command.split(":", 1)[1].strip() if ":" in command else command
        response = dispatch_os_command(cmd_content)

    # -----------------------------
    # 2. Existing Structured Commands
    # -----------------------------
    elif text.startswith("journal:") or text.startswith("log:"):
        response = process_journal(command.split(":",1)[1].strip())

    elif text.startswith("summarize:"):
        response = summarize_text(command.split(":", 1)[1].strip())

    elif "generate my thoughts" in text:
        response = generate_thoughts(LOG_FILE)

    elif text.startswith("generate topic:"):
        response = generate_topic_content(command.split(":", 1)[1].strip())

    elif text.startswith("remember that"):
        response = remember_fact(command.replace("remember that", "").strip())

    elif "what do you remember" in text:
        response = recall_memory()

    elif text.startswith("add goal"):
        response = add_goal(command.split(":",1)[1].strip())

    elif "show my goals" in text:
        response = list_goals()

    elif "complete goal" in text:
        response = complete_goal(re.findall(r"\d+", text)[0])

    elif text.startswith("add habit"):
        response = add_habit(command.split(":",1)[1].strip())

    elif "habit streak" in text:
        response = habit_streaks()

    elif "most common habit" in text:
        response = most_common_habit()

    elif "plan my day" in text:
        response = plan_my_day()

    elif "reflect" in text:
        response = reflect()

    elif "analyze me" in text:
        response = "\n".join(extract_insights())

    elif "what insights" in text:
        response = list_insights()

    elif text.startswith("add value"):
        response = add_value(command.split(":",1)[1].strip())

    elif "show my values" in text:
        response = list_values()

    elif text.startswith("should i"):
        response = evaluate_decision(command)

    elif "remind me to" in text:
        r, dt = parse_reminder_command(command)
        response = add_reminder(r, dt) if r else "Couldn't parse reminder."

    elif "show my reminders" in text:
        response = list_reminders()

    elif "how was i last month" in text or "previous month" in text:
        response = previous_month_mood()

    elif re.match(r"^[a-zA-Z]+\s+\d{4}$", text.strip()):
        parsed = parse_month_query(text)
        if parsed:
            year, month = parsed
            response = monthly_mood_summary(year, month)
        else:
            response = "Tell me a valid month and year like 'January 2026'."

    elif "how was i in" in text or "analyze my mood" in text:
        parsed = parse_month_query(text)
        if parsed == "PREVIOUS":
            response = previous_month_mood()
        elif parsed:
            year, month = parsed
            response = monthly_mood_summary(year, month)
        else:
            response = "Tell me a month and year, like 'January 2025'."
    
    elif "how am i trending" in text or "emotional trend" in text:
        response = emotional_trend()
        
    elif "am i burning out" in text or "burnout" in text:
        response = detect_burnout()

    elif "forecast my mood" in text or "how will i feel" in text:
        response = emotional_forecast()

    elif "what should i do right now" in text or "help me stabilize" in text:
        response = suggest_intervention()

    elif "analyze my patterns" in text:
        response = "\n".join(extract_identity_patterns())

    elif "what triggers me" in text:
        response = "\n".join(detect_triggers())

    elif "warn me" in text or "early warning" in text:
        response = early_warning()

    elif "emotional risk" in text or "how am i doing lately" in text:
        response = emotional_risk_monitor()

    elif "what should i do" in text or "recovery" in text:
        response = recovery_recommendation()

    elif "am i close to burnout" in text:
        response = burnout_prediction()

    elif "do i need rest" in text:
        response = early_warning_nudge() or "🟢 No immediate recovery needed."

    elif "how stable am i emotionally" in text:
        response = f"Current emotional stability: {load_week31_state()['burnout_trend']}"

    elif "burnout risk" in text or "predict burnout" in text:
        response = predict_burnout_window()

    elif "rebalance goals" in text:
        response = auto_rebalance_goals()

    elif "goal status" in text:
        normalize_goal_states()
        goals = load_json(GOALS_FILE)
        response = "\n".join(
            f"{i}. {g['goal']} ({g['state']})"
            for i, g in goals.items()
        )

    elif "emotional stability" in text:
        response = emotional_stability_index()

    elif "how have i changed" in text:
        response = transformation_summary()

    elif "growth analysis" in text:
        response = growth_direction_analysis()

    elif "identity shift" in text:
        response = identity_shift_analysis()

    elif "cognitive patterns" in text:
        response = detect_cognitive_distortions()

    elif "am i overthinking" in text:
        response = detect_mental_loops()

    elif "reframe my thoughts" in text:
        response = reframe_thought()

    elif "who am i becoming" in text:
        response = identity_anchor_map()

    elif "am i emotionally dependent" in text:
        response = emotional_dependency_check()

    elif "how stable am i" in text:
        response = self_concept_stability()

    elif "what chapter am i in" in text:
        response = detect_life_chapters()

    elif "what is my story" in text:
        response = personal_myth()

    elif "how do i think" in text:
        response = cognitive_pattern_analysis()

    elif "have i evolved" in text:
        response = thinking_evolution()

    elif "analyze my entire system" in text:
        response = full_self_system_report()

    elif "what is my life status" in text:
        response = life_system_status()

    # -----------------------------
    # 3. Fallback Conversational AI or Web Search
    # -----------------------------
    else:
        facts_context = ""
        try:
            facts_context = recall_memory()
        except Exception:
            pass
        
        chat_history_str = ""
        try:
            ctx = load_context()
            history = ctx.get("chat_history", [])
            if history:
                history_lines = []
                for h in history[-10:]:
                    history_lines.append(f"User: {h.get('user', '')}")
                    history_lines.append(f"Selah: {h.get('response', '')}")
                chat_history_str = "\n".join(history_lines)
        except Exception:
            pass
        
        fallback_prompt = (
            f"Previous Context Facts:\n{facts_context}\n\n"
            f"Recent Chat History:\n{chat_history_str}\n\n"
            f"User Message: \"{command}\"\n\n"
            f"Respond conversationally to the user message. Maintain your persona character exactly and make your response highly engaging and tailored. "
            f"Use the Recent Chat History context to understand references (like 'them', 'who', 'the players', etc.).\n\n"
            f"CRITICAL SYSTEM INSTRUCTION:\n"
            f"If the user asks for a command, how to execute something, or how to fix a system error (e.g. port conflicts, network ports, checking git status, killing a process, showing directories), "
            f"ALWAYS provide the exact raw terminal shell command inside a clean markdown code block formatted as:\n"
            f"```bash\n"
            f"<command>\n"
            f"```\n"
            f"Make sure the command is single-line or chainable (using &&) so it is extremely easy to copy or execute."
        )

        if needs_web_search(text):
            try:
                response = handle_web_query(command)
            except Exception:
                # Fallback gracefully to standard Gemini AI when search fails or lacks API Key
                response = call_gemini(fallback_prompt, system_instruction=system_instruction, api_key=api_key, model_preference=model_preference)
        else:
            response = call_gemini(fallback_prompt, system_instruction=system_instruction, api_key=api_key, model_preference=model_preference)

    if speak_out:
        speak(response)
    
    # Save the turn to rolling chat history
    try:
        ctx = load_context()
        history = ctx.setdefault("chat_history", [])
        history.append({
            "user": command,
            "response": response,
            "timestamp": datetime.now().isoformat()
        })
        ctx["chat_history"] = history[-30:] # keep last 30 turns
        save_context(ctx)
    except Exception as e:
        print(f"Error saving chat history: {e}")

    try:
        print("SELAH:", response)
    except UnicodeEncodeError:
        try:
            print("SELAH:", response.encode('ascii', errors='replace').decode('ascii'))
        except Exception:
            pass
    return response

if __name__ == "__main__":
    print("🧠 SELAH Online. Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ")

        if user_input.lower() == "exit":
            break

        handle_command(user_input)