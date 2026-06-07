import os
from PIL import ImageGrab
from assistant.selah_brain import call_gemini

def capture_and_analyze_screen(persona="os", api_key=None, model_preference=None):
    """
    Takes a screenshot of the main screen and queries Gemini
    multimodally to analyze active apps, work context, and suggested actions.
    """
    try:
        # Grab active screen
        screenshot = ImageGrab.grab()
    except Exception as e:
        return f"Error: Screen capture interface unavailable: {str(e)}"

    # Use client override API key if provided
    active_api_key = api_key
    if not active_api_key:
        active_api_key = os.getenv("GEMINI_API_KEY")

    if not active_api_key:
        try:
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("GEMINI_API_KEY="):
                            active_api_key = line.split("=", 1)[1].strip()
                            break
        except Exception:
            pass

    if not active_api_key:
        return "Error: I need a GEMINI_API_KEY to perform multimodal screen vision analysis."

    try:
        import google.generativeai as genai
        genai.configure(api_key=active_api_key)
        
        # Dynamically discover the first available model that supports content generation
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        model_name = "gemini-1.5-flash"  # standard multimodal fallback
        
        if available_models:
            pref = str(model_preference).lower() if model_preference else ""
            if "pro" in pref:
                # Find a pro model
                pro_models = [m for m in available_models if "pro" in m.lower()]
                if pro_models:
                    model_name = pro_models[0]
                else:
                    model_name = available_models[0]
            elif "normal" in pref or "flash" in pref:
                # Find a flash model
                flash_models = [m for m in available_models if "flash" in m.lower()]
                if flash_models:
                    model_name = flash_models[0]
                else:
                    model_name = available_models[0]
            else:
                model_name = available_models[0]
        else:
            pref = str(model_preference).lower() if model_preference else ""
            if "pro" in pref:
                model_name = "gemini-1.5-pro"
            else:
                model_name = "gemini-1.5-flash"
            
        model = genai.GenerativeModel(model_name)

        # Customize persona system instructions inside the visual scan prompt
        persona_style = ""
        if persona == "coach":
            persona_style = "Respond with exceptional empathy, focus on validating study fatigue or physical strain."
        elif persona == "sage":
            persona_style = "Respond philosophically, guiding the user to focus their mind and connect screen work to deep long-term growth."
        else:
            persona_style = "Respond as an advanced OS, structured, cybernetic, precise, and analytical."

        prompt = (
            f"You are the SELAH Multimodal Screen Awareness Vision Companion.\n"
            f"Persona Instruction: {persona_style}\n\n"
            "Tasks:\n"
            "1. Analyze this screenshot of the user's active monitor.\n"
            "2. Identify the primary active application(s) open (e.g. VS Code, Chrome, Zoom, WhatsApp).\n"
            "3. Describe the content and work context in detail (e.g., debugging a React app, in a video meeting, reviewing faith articles, reading exam schedules).\n"
            "4. Provide exactly 3 highly contextual suggested actions based on the screenshot content. Format them clearly with action-themed titles, for example:\n"
            "   - `[Action Card] Suggest Mail Reply: ...`\n"
            "   - `[Action Card] Summarize Meeting: ...`\n"
            "   - `[Action Card] Autocomplete Form: ...`\n"
            "   - `[Action Card] Explain Selected Code: ...`\n"
            "   - `[Action Card] System Wellness Nudge: ...`\n\n"
            "Structure your output using professional, beautifully formatted HUD telemetry Markdown."
        )

        response = model.generate_content([screenshot, prompt])
        return response.text.strip()
    except Exception as e:
        return f"SELAH Visual Core error during scan: {str(e)}"
