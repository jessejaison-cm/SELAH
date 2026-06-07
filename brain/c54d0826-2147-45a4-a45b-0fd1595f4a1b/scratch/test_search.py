import os
import google.generativeai as genai

api_key = None
env_path = "c:\\Repo\\SELAH\\.env"
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("GEMINI_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
                break
print("API KEY:", api_key[:10] if api_key else "None")

genai.configure(api_key=api_key)
try:
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        tools="google_search"
    )
    response = model.generate_content("What is the starting lineup for Croatia Vs Belgium today June 2 2026?")
    print("RESPONSE:")
    print(response.text)
except Exception as e:
    print("ERROR:", e)
