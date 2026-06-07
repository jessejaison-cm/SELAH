import sys
import os

sys.path.append("c:\\Repo\\SELAH\\src")
from web.web_sources import search_web

query = "Croatia Vs Belgium starting lineup June 2 2026"
results = search_web(query)
print("RESULTS FOR:", query)
for idx, r in enumerate(results):
    title = r['title'].encode('ascii', errors='replace').decode('ascii')
    snippet = r['snippet'].encode('ascii', errors='replace').decode('ascii')
    print(f"\n[{idx+1}] Title: {title}")
    print(f"    Snippet: {snippet}")
    print(f"    Link: {r['link']}")
