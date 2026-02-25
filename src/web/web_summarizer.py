def summarize_results(results):
    if not results:
        return "I couldn't find reliable results."

    main_point = results[0]["snippet"]
    return f"Here’s what I found: {main_point}"