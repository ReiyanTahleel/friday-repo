import asyncio
import json
import os
import tempfile
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import ollama
import edge_tts
from actions import (
    open_application, play_music, search_web, calculate_math, get_time, open_google_search
)

app = FastAPI()
TEMP_AUDIO_FILE = os.path.join(tempfile.gettempdir(), "friday_response.mp3")

# Force strict brevity to make TTS generation almost instant
SYSTEM_PROMPT = """You are FRIDAY, a highly efficient, intelligent, and loyal AI assistant.
1. Keep spoken responses UNDER 2 sentences unless specifically asked for details.
2. If asked to do math, ALWAYS use the 'calculate_math' tool.
3. If asked to open an app, use 'open_application'.
4. If asked to play ANY music, video, song, or episode on YouTube or Spotify, ALWAYS use the 'play_music' tool. You DO have the capability to play media via this tool, so NEVER decline a request to play something.
5. If asked a factual question, use 'search_web'.
6. If asked to 'google' something, use 'open_google_search'.
7. You MUST ONLY speak English. If asked to speak another language, politely decline.
8. If asked to do something you truly cannot do (and there is no tool for it), simply say you are not capable of that. But if you have a tool, ALWAYS use it.
9. DO NOT output raw JSON or brackets to the user."""

FUNCTION_MAP = {
    "open_application": open_application,
    "play_music": play_music,
    "search_web": search_web,
    "open_google_search": open_google_search,
    "calculate_math": calculate_math,
    "get_time": get_time
}

@app.get("/")
async def get():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

async def text_to_speech_file(text: str, filename=TEMP_AUDIO_FILE):
    """Generates TTS audio file fast using Edge TTS"""
    # Pad the text with a short pause so the first word isn't clipped by the browser's audio initialization
    padded_text = f", {text}"
    voice = "en-US-JennyNeural" 
    communicate = edge_tts.Communicate(padded_text, voice)
    await communicate.save(filename)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    history = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    try:
        # 1. Automatic Greeting upon connecting!
        greeting = "Systems online. Welcome back, boss."
        await text_to_speech_file(greeting)
        
        with open(TEMP_AUDIO_FILE, "rb") as audio:
            await websocket.send_bytes(audio.read())
        await websocket.send_json({"text": greeting})

        while True:
            # 2. Receive pure text from the browser (0 latency!)
            data = await websocket.receive_text()
            print(f"User: {data}")
            
            try:
                history.append({"role": "user", "content": data})
                await websocket.send_json({"status": "processing"})

                # Define tools for Llama
                tools = [
                    {"type": "function", "function": {"name": "open_application", "description": "Opens desktop apps (Notepad, VS Code, Store)", "parameters": {"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]}}},
                    {"type": "function", "function": {"name": "play_music", "description": "Auto-plays a song, video, movie, or episode on YouTube or Spotify", "parameters": {"type": "object", "properties": {"song_name": {"type": "string", "description": "The name of the song or video to play"}}, "required": ["song_name"]}}},
                    {"type": "function", "function": {"name": "search_web", "description": "Searches the internet for general knowledge or facts", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
                    {"type": "function", "function": {"name": "open_google_search", "description": "Opens the user's web browser and visually searches Google for a query", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
                    {"type": "function", "function": {"name": "calculate_math", "description": "Calculates math equations EXACTLY", "parameters": {"type": "object", "properties": {"expression": {"type": "string", "description": "Math formula e.g., '59 / 87'"}}, "required": ["expression"]}}},
                    {"type": "function", "function": {"name": "get_time", "description": "Gets the current time", "parameters": {"type": "object", "properties": {}}}}
                ]

                response = ollama.chat(model='llama3.2:3b', messages=history, tools=tools)
                assistant_msg = response.get('message', {})
                
                # Handle Tool Calls
                if assistant_msg.get('tool_calls'):
                    history.append(assistant_msg)
                    for tool in assistant_msg['tool_calls']:
                        func_name = tool['function']['name']
                        args = tool['function']['arguments']
                        
                        if func_name in FUNCTION_MAP:
                            tool_result = FUNCTION_MAP[func_name](**args)
                            history.append({"role": "tool", "name": func_name, "content": tool_result})
                    
                    # Ask Llama to summarize what it just did
                    response = ollama.chat(model='llama3.2:3b', messages=history)
                    final_text = response['message']['content']
                else:
                    final_text = assistant_msg.get('content', '')

                # Fix the "JSON Leak" and empty string bug strictly
                if not final_text or not final_text.strip():
                    final_text = "I'm sorry boss, I didn't quite catch that."
                elif final_text.startswith('{') or "tool_calls" in final_text:
                    final_text = "I have handled that for you, boss."

                print(f"FRIDAY: {final_text}")
                history.append({"role": "assistant", "content": final_text})
                
                # Speak Response
                await text_to_speech_file(final_text)
                await websocket.send_json({"text": final_text, "status": "idle"})
                
                with open(TEMP_AUDIO_FILE, "rb") as audio:
                    await websocket.send_bytes(audio.read())

            except Exception as e:
                print(f"Error processing command: {e}")
                err_msg = "I'm sorry boss, I ran into an error processing that."
                await text_to_speech_file(err_msg)
                await websocket.send_json({"text": err_msg, "status": "idle"})
                with open(TEMP_AUDIO_FILE, "rb") as audio:
                    await websocket.send_bytes(audio.read())

    except WebSocketDisconnect:
        print("Client disconnected")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)