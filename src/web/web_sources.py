import requests
import os

def search_web(query):
    api_key = os.getenv("SERPAPI_KEY")
    
    params = {
        "q": query,
        "api_key": api_key,
        "engine": "google"
    }
    
    response = requests.get("https://serpapi.com/search", params=params)
    data = response.json()
    
    results = []
    for r in data.get("organic_results", [])[:3]:
        results.append({
            "title": r.get("title"),
            "snippet": r.get("snippet"),
            "link": r.get("link")
        })
    
    return results

def summarize_results(results, query=None):
    if not results:
        return "I couldn't find reliable results."

    # Load api key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        try:
            env_path = "c:\\Repo\\SELAH\\.env"
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("GEMINI_API_KEY="):
                            api_key = line.split("=", 1)[1].strip()
                            break
        except Exception:
            pass

    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            
            context = "\n".join(
                f"Source Title: {r['title']}\nSnippet: {r['snippet']}\nLink: {r['link']}"
                for r in results
            )
            
            prompt = (
                f"You are a helpful assistant. The user is asking the following query: \"{query or 'Search Results Summary'}\".\n\n"
                f"Here are the web search results for the query:\n"
                f"{context}\n\n"
                f"Based on the search results and your own knowledge, please provide a clear, accurate, and comprehensive response.\n"
                f"TOKEN COMPRESSION MODE: Practice extreme token compression. Keep your response extremely concise, direct, and focused ONLY on the exact details/names requested. Avoid verbose introductions, explanations, summaries, and conversational filler.\n"
                f"If the user is asking for the lineup of a football/soccer match or a team, you MUST provide ONLY the starting lineups (11 players for each team, clearly grouped by team name). Do not output any other details.\n"
                f"CRITICAL: If official starting lineups are not fully finalized or available, you MUST instead provide the PREDICTED/EXPECTED starting lineups (11 players for each team, totaling 22 players) based on the latest previews and team news. Under no circumstances should you refuse to provide the 11 + 11 player lists or output a warning about data limitations or missing telemetry. Just provide the list of 22 players."
            )
            
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            pass

    main_snippets = " ".join(
        r["snippet"] for r in results if r.get("snippet")
    )

    return main_snippets[:500] + "..."