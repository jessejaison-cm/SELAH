def needs_web_search(user_text):
    keywords = [
        "what is",
        "who is",
        "latest",
        "news",
        "price",
        "define",
        "current",
        "today"
    ]

    user_text = user_text.lower()

    return any(keyword in user_text for keyword in keywords)