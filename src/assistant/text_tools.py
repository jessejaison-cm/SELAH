import re
from collections import defaultdict
import random

def summarize_text(text, num_sentences=2):
    """
    Extractive summarization using word frequency scoring.
    """
    sentences = re.split(r'(?<=[.!?]) +', text)
    if len(sentences) <= num_sentences:
        return text
        
    word_freq = defaultdict(int)
    words = re.findall(r'\w+', text.lower())
    for word in words:
        if len(word) > 3: # Ignore basic stop words
            word_freq[word] += 1
            
    sentence_scores = {}
    for i, sentence in enumerate(sentences):
        for word in re.findall(r'\w+', sentence.lower()):
            if word in word_freq:
                sentence_scores[i] = sentence_scores.get(i, 0) + word_freq[word]
                
    # Rank sentences and keep the top N
    ranked = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)
    top_indices = sorted([idx for idx, score in ranked[:num_sentences]])
    
    summary = " ".join([sentences[i] for i in top_indices])
    return summary

def generate_thoughts(log_file_path):
    """
    A pure Python Generative AI (Markov Chain) trained on the user's own journal logs.
    It writes text that mimics the user's voice and thoughts!
    """
    try:
        with open(log_file_path, "r", encoding="utf-8") as f:
            text = ""
            for line in f:
                if "|" in line:
                    text += line.split("|", 1)[1].strip() + " "
    except FileNotFoundError:
        return "I need more journal logs before I can generate your thoughts!"
        
    words = text.split()
    if len(words) < 20:
        return "Not enough data in your daily logs to generate thoughts yet. Write more!"
        
    # Build Markov Chain dictionary
    chain = defaultdict(list)
    for i in range(len(words) - 1):
        chain[words[i]].append(words[i+1])
        
    # Generate text
    # Pick a random starting word that is capitalized (likely a sentence starter)
    start_words = [w for w in words if w.istitle()]
    current_word = random.choice(start_words) if start_words else random.choice(words)
    generated = [current_word]
    
    for _ in range(30): # Generate ~30 words
        if current_word in chain:
            next_word = random.choice(chain[current_word])
            generated.append(next_word)
            current_word = next_word
        else:
            break
            
    return " ".join(generated) + "..."

import os

def generate_topic_content(topic):
    """
    Generates content on any arbitrary topic using the Google Gemini LLM API.
    """
    try:
        import google.generativeai as genai
    except ImportError:
        return "To generate content on any topic, you need to install the Gemini API library. Run: pip install google-generativeai"
        
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        try:
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
            with open(env_path, "r") as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        break
        except Exception:
            pass
            
    if not api_key:
        return "I need a GEMINI_API_KEY environment variable to generate content. You can get one for free at aistudio.google.com!"
        
    try:
        genai.configure(api_key=api_key)
        
        # Dynamically find the first model that supports generateContent
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if not available_models:
            return "Error: No text generation models are available for this API key."
            
        model = genai.GenerativeModel(available_models[0])
        
        prompt = f"Write a creative, engaging, and highly informative short response about the following topic: {topic}"
        response = model.generate_content(prompt)
        
        return response.text.strip()
    except Exception as e:
        return f"Sorry, I ran into an error while generating the content: {str(e)}"
