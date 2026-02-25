from .web_sources import search_web, summarize_results


def handle_web_query(query):
    results = search_web(query)
    summary = summarize_results(results)

    formatted_sources = "\n".join(
        [f"- {r['title']}: {r['link']}" for r in results]
    )

    return f"{summary}\n\nSources:\n{formatted_sources}"