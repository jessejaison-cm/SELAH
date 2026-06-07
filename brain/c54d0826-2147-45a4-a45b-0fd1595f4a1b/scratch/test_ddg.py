import requests
import re
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36"
}

query = "Croatia Vs Belgium squad starting lineup June 2 2026"
url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"

try:
    response = requests.get(url, headers=headers)
    print("STATUS CODE:", response.status_code)
    
    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    
    for a in soup.find_all("a", class_="result__snippet")[:4]:
        title_elem = a.find_parent("div", class_="result__body").find("a", class_="result__url")
        results.append({
            "title": title_elem.text.strip() if title_elem else "Search Result",
            "snippet": a.text.strip(),
            "link": title_elem["href"] if title_elem and "href" in title_elem.attrs else ""
        })
        
    print("RESULTS:")
    for r in results:
        print("- Title:", r["title"])
        print("  Snippet:", r["snippet"])
        print("  Link:", r["link"])
        
except Exception as e:
    print("ERROR:", e)
