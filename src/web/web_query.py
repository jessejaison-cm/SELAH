from .web_sources import search_web, summarize_results


def handle_web_query(query):
    results = search_web(query)
    summary = summarize_results(results, query)

    formatted_sources = ", ".join(
        [f"[{r['title']}]({r['link']})" for r in results if r.get("link")]
    )

    return f"{summary}\n\n**Sources:** {formatted_sources}" if formatted_sources else summary