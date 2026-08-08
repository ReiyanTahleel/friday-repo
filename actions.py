import os
import math
import datetime
import pywhatkit
from duckduckgo_search import DDGS

def calculate_math(expression: str) -> str:
    """Evaluates a mathematical expression safely and returns the exact answer."""
    try:
        # Use python's eval securely for math
        allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return f"The answer is {result}"
    except Exception as e:
        return f"Sorry, I couldn't calculate that. Error: {str(e)}"

def search_web(query: str) -> str:
    """Searches the internet for real-time knowledge and news."""
    try:
        results = DDGS().text(query, max_results=2)
        if not results:
            return "No web results found."
        
        info = ""
        for r in results:
            info += f"{r['title']}: {r['body']}\n"
        return info
    except Exception as e:
        return "The web search failed."

def open_application(app_name: str) -> str:
    """Opens a system application based on the user's request."""
    app_name = app_name.lower().strip()
    
    # Map common app names to Windows executable commands
    app_map = {
        "notepad": "notepad",
        "calculator": "calc",
        "chrome": "start chrome",
        "edge": "start msedge",
        "vs code": "code",
        "code": "code",
        "spotify": "start spotify",
        "microsoft store": "start ms-windows-store:",
        "word": "start winword",
        "excel": "start excel",
        "youtube": "start https://www.youtube.com",
        "settings": "start ms-settings:"
    }
    
    cmd = app_map.get(app_name, f"start {app_name}")
    os.system(cmd)
    return f"I have opened {app_name}."

def play_music(song_name: str) -> str:
    """Instantly opens browser and auto-plays the requested song on YouTube."""
    try:
        pywhatkit.playonyt(song_name)
        return f"Playing {song_name} for you now."
    except Exception as e:
        return "I encountered an error trying to play the song."

def open_google_search(query: str) -> str:
    """Opens a web browser and visually searches Google for the given query."""
    try:
        pywhatkit.search(query)
        return f"I have opened a Google search for {query}."
    except Exception as e:
        return "I encountered an error trying to open Google search."

def get_time() -> str:
    """Gets the current time."""
    now = datetime.datetime.now()
    return f"The current time is {now.strftime('%I:%M %p')}."