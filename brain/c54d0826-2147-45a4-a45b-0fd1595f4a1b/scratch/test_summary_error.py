import os
import sys

sys.path.append("c:\\Repo\\SELAH\\src")
from web.web_sources import search_web, summarize_results

query = "Croatia Vs Belgium starting lineup June 2 2026"
results = search_web(query)

try:
    # Let's run the actual summarizer and print the error if it fails
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        env_path = os.path.join(base_dir, ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        break

    print("Using API KEY:", api_key[:10] if api_key else "None")
    genai.configure(api_key=api_key)
    
    context = "\n".join(
        f"Source Title: {r['title']}\nSnippet: {r['snippet']}\nLink: {r['link']}"
        for r in results
    )
    
    prompt = (
        f"You are a helpful assistant. The user is asking the following query: \"{query}\".\n\n"
        f"Here are the web search results for the query:\n"
        f"{context}\n\n"
        f"Based on the search results and your own knowledge, please provide a clear, accurate, and comprehensive response. "
        f"If the user is asking for the lineup of a football/soccer match or a team, you MUST provide the complete starting lineup "
        f"(11 starting players for each team, i.e., 11 + 11 names, clearly grouped by team with their positions if possible).\n"
        f"Format the output beautifully using clean markdown lists."
    )
    
    model = genai.GenerativeModel("gemini-1.5-flash")
    print("Generating content...")
    response = model.generate_content(prompt)
    print("SUCCESS! RESPONSE:")
    print(response.text)

except Exception as e:
    print("CAUGHT ERROR:", e)
    import traceback
    traceback.print_exc()
