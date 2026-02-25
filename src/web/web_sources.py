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

def summarize_results(results):
    if not results:
        return "I couldn't find reliable results."

    main_snippets = " ".join(
        r["snippet"] for r in results if r.get("snippet")
    )

    return main_snippets[:500] + "..."