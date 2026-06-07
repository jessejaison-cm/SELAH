from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os

# Ensure the parent /src directory is in the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from assistant.selah_brain import (
    handle_command,
    load_json,
    GOALS_FILE,
    self_concept_stability,
    burnout_prediction,
    detect_triggers,
    identity_anchor_map
)
from assistant.os_agent import dispatch_os_command
from assistant.vision_agent import capture_and_analyze_screen

try:
    from dotenv import load_dotenv
    # Load from the root of the project
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))
except ImportError:
    pass

app = Flask(__name__)
CORS(app)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    user_input = data.get("message")
    persona = data.get("persona", "os")

    # Read client specific overrides from headers or payload JSON
    api_key = request.headers.get("X-Gemini-API-Key") or data.get("api_key")
    model_preference = request.headers.get("X-Gemini-Model-Preference") or data.get("model_preference")

    if not user_input:
        return jsonify({"error": "No message provided"}), 400

    response = handle_command(
        user_input, 
        speak_out=False, 
        persona=persona, 
        api_key=api_key, 
        model_preference=model_preference
    )

    return jsonify({
        "user": user_input,
        "response": response
    })

@app.route("/agent/execute", methods=["POST"])
def execute_agent():
    data = request.get_json() or {}
    command = data.get("message")

    if not command:
        return jsonify({"error": "No OS control command provided"}), 400

    result = dispatch_os_command(command)
    return jsonify({
        "command": command,
        "response": result
    })

@app.route("/screen/analyze", methods=["POST"])
def screen_analyze():
    data = request.get_json() or {}
    persona = data.get("persona", "os")

    # Read client specific overrides from headers or payload JSON
    api_key = request.headers.get("X-Gemini-API-Key") or data.get("api_key")
    model_preference = request.headers.get("X-Gemini-Model-Preference") or data.get("model_preference")

    result = capture_and_analyze_screen(
        persona, 
        api_key=api_key, 
        model_preference=model_preference
    )
    return jsonify({
        "analysis": result
    })

@app.route("/telemetry", methods=["GET"])
def telemetry():
    try:
        # Calculate goal status
        goals = load_json(GOALS_FILE)
        active_goals = sum(1 for g in goals.values() if g.get("state") == "active" and not g.get("completed"))
        completed_goals = sum(1 for g in goals.values() if g.get("completed") or g.get("state") == "completed")
        deferred_goals = sum(1 for g in goals.values() if g.get("state") == "deferred" and not g.get("completed"))

        # Stability
        stability = self_concept_stability()

        # Burnout Prediction
        burnout = burnout_prediction()

        # Triggers
        triggers = detect_triggers()

        # Anchors (parse list from identity anchor map text)
        anchor_text = identity_anchor_map()
        anchors = []
        for line in anchor_text.split("\n"):
            if line.strip().startswith("-"):
                anchors.append(line.strip()[1:].strip())

        return jsonify({
            "stability": stability,
            "burnout": burnout,
            "triggers": triggers,
            "anchors": anchors,
            "active_goals": active_goals,
            "completed_goals": completed_goals,
            "deferred_goals": deferred_goals
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, host="0.0.0.0")
