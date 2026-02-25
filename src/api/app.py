from flask import Flask, request, jsonify
from flask_cors import CORS
from assistant.selah_brain import handle_command

app = Flask(__name__)
CORS(app)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_input = data.get("message")

    if not user_input:
        return jsonify({"error": "No message provided"}), 400

    response = handle_command(user_input, speak_out=False)

    return jsonify({
        "user": user_input,
        "response": response
    })

if __name__ == "__main__":
    app.run(debug=True)