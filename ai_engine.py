"""
AI Engine module for Zyren Personal Assistant.
Supports Free APIs (Google Gemini, Groq, Ollama) and Anthropic Claude.
Manages streaming generation, multi-turn history, persistent memory injection,
web search tool execution, and voice transcription.
"""

import os
import re
import io
import json
from typing import List, Dict, Any, Generator, Optional
from dotenv import load_dotenv

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

from config import SYSTEM_PROMPT, BASE_DIR, PROVIDERS_CONFIG

def reload_env():
    """Reload .env dynamically in case user updated keys while app is running."""
    load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)

def perform_web_search(query: str, max_results: int = 4) -> str:
    """
    Perform a fast real-time web search using DuckDuckGo.
    Returns formatted markdown snippets with sources.
    """
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                title = r.get("title", "No Title")
                href = r.get("href", "")
                snippet = r.get("body", "")
                results.append(f"**[{title}]({href})**\n{snippet}")
        
        if not results:
            return "No real-time search results found for this query."
        return "\n\n---\n\n".join(results)
    except Exception as e:
        return f"Web search could not retrieve results: {str(e)}"

def detect_memory_command(text: str) -> Optional[str]:
    """
    Detects if the user prompt is an explicit instruction to remember something.
    Examples:
      - "Remember that my favorite language is Python"
      - "Please remember: I am working on a Streamlit project"
      - "Don't forget that I prefer concise explanations"
    """
    patterns = [
        r"^(?:please\s+)?remember\s+that\s+(.*)",
        r"^(?:please\s+)?remember\s*:\s*(.*)",
        r"^(?:please\s+)?remember\s+(.*)",
        r"^(?:please\s+)?don'?t\s+forget\s+that\s+(.*)",
        r"^(?:please\s+)?keep\s+in\s+mind\s+that\s+(.*)"
    ]
    cleaned = text.strip()
    for pat in patterns:
        match = re.match(pat, cleaned, re.IGNORECASE)
        if match:
            fact = match.group(1).strip()
            if fact.endswith("."):
                fact = fact[:-1].strip()
            if len(fact) > 3:
                return fact
    return None

# --- Provider Streaming Implementations ---

def _stream_gemini(
    messages: List[Dict[str, str]],
    user_prompt: str,
    system_text: str,
    model: str,
    api_key: Optional[str]
) -> Generator[str, None, None]:
    """Stream from Google Gemini API (Free Tier from Google AI Studio)."""
    reload_env()
    key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()
    if not key or key == "your_gemini_api_key_here":
        yield (
            "⚠️ **Google Gemini API Key is missing!**\n\n"
            "Google offers a **100% Free API** with generous limits (no credit card required):\n"
            "1. Visit **[Google AI Studio](https://aistudio.google.com/apikey)**\n"
            "2. Click **Create API Key** (takes ~15 seconds)\n"
            "3. Paste your key in the sidebar under **Assistant Settings** or add `GEMINI_API_KEY=...` to your `.env` file.\n"
        )
        return

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key)

        # Build conversation contents
        contents = []
        for msg in messages:
            role = "model" if msg["role"] == "assistant" else "user"
            contents.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["content"])]
            ))
        # Append current user prompt
        contents.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_prompt)]
        ))

        config = types.GenerateContentConfig(
            system_instruction=system_text,
            temperature=0.7
        )

        response = client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=config
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text

    except Exception as e:
        yield f"❌ **Google Gemini Error:** {str(e)}"

def _stream_groq(
    messages: List[Dict[str, str]],
    user_prompt: str,
    system_text: str,
    model: str,
    api_key: Optional[str]
) -> Generator[str, None, None]:
    """Stream from Groq Cloud (Free Tier, ultra-fast Llama 3.3 / DeepSeek)."""
    reload_env()
    key = (api_key or os.getenv("GROQ_API_KEY", "")).strip()
    if not key or key == "your_groq_api_key_here":
        yield (
            "⚠️ **Groq API Key is missing!**\n\n"
            "Groq provides an **ultra-fast, 100% Free API** running Llama 3.3 and DeepSeek R1:\n"
            "1. Visit **[Groq Console](https://console.groq.com/keys)**\n"
            "2. Sign in and create a free API key (takes ~20 seconds, no credit card)\n"
            "3. Paste your key in the sidebar under **Assistant Settings** or add `GROQ_API_KEY=...` to your `.env` file.\n"
        )
        return

    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=key,
            base_url="https://api.groq.com/openai/v1"
        )

        chat_messages = [{"role": "system", "content": system_text}]
        for msg in messages:
            chat_messages.append({"role": msg["role"], "content": msg["content"]})
        chat_messages.append({"role": "user", "content": user_prompt})

        stream = client.chat.completions.create(
            model=model,
            messages=chat_messages,
            stream=True,
            temperature=0.7
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except Exception as e:
        yield f"❌ **Groq Cloud Error:** {str(e)}"

def _stream_ollama(
    messages: List[Dict[str, str]],
    user_prompt: str,
    system_text: str,
    model: str
) -> Generator[str, None, None]:
    """Stream from local Ollama instance (100% Free, Private & Offline)."""
    reload_env()
    base_url = (os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434/v1").rstrip("/")
    if not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"

    try:
        from openai import OpenAI
        client = OpenAI(
            base_url=base_url,
            api_key="ollama"
        )

        chat_messages = [{"role": "system", "content": system_text}]
        for msg in messages:
            chat_messages.append({"role": msg["role"], "content": msg["content"]})
        chat_messages.append({"role": "user", "content": user_prompt})

        stream = client.chat.completions.create(
            model=model,
            messages=chat_messages,
            stream=True
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except Exception as e:
        yield (
            f"⚠️ **Could not connect to local Ollama at `{base_url}`**\n\n"
            "To use local free AI models without an internet connection or API key:\n"
            "1. Download and install **[Ollama](https://ollama.com)**.\n"
            f"2. Open terminal and run: `ollama run {model}` (e.g. `ollama run llama3.2`).\n"
            "3. Return here and start chatting!\n\n"
            f"*Details: {str(e)}*"
        )

def _stream_anthropic(
    messages: List[Dict[str, str]],
    user_prompt: str,
    system_text: str,
    model: str,
    api_key: Optional[str]
) -> Generator[str, None, None]:
    """Stream from Anthropic Claude Messages API."""
    reload_env()
    key = (api_key or os.getenv("ANTHROPIC_API_KEY", "")).strip()
    if not key or key == "your_anthropic_api_key_here":
        yield (
            "⚠️ **Anthropic Claude API Key is missing!**\n\n"
            "To chat with Claude:\n"
            "1. Get your key at **[console.anthropic.com](https://console.anthropic.com/)**.\n"
            "2. Paste it in the sidebar or add `ANTHROPIC_API_KEY=...` to your `.env` file.\n\n"
            "💡 *Tip: Switch to **Google Gemini** or **Groq** in the sidebar for a 100% FREE API key!*"
        )
        return

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)

        formatted: List[Dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "").strip()
            if not content or role not in ("user", "assistant"):
                continue
            if formatted and formatted[-1]["role"] == role:
                formatted[-1]["content"] += f"\n\n{content}"
            else:
                formatted.append({"role": role, "content": content})

        clean_new = user_prompt.strip()
        if formatted and formatted[-1]["role"] == "user":
            formatted[-1]["content"] += f"\n\n{clean_new}"
        else:
            formatted.append({"role": "user", "content": clean_new})

        if formatted and formatted[0]["role"] != "user":
            formatted.pop(0)

        with client.messages.stream(
            model=model,
            max_tokens=4096,
            system=system_text,
            messages=formatted,
            temperature=0.7
        ) as stream:
            for text_chunk in stream.text_stream:
                yield text_chunk

    except Exception as e:
        yield f"❌ **Anthropic Claude Error:** {str(e)}"

# --- Master Streaming Dispatcher ---

def stream_chat_response(
    history: List[Dict[str, str]],
    user_prompt: str,
    provider: str = "gemini",
    model: Optional[str] = None,
    enable_search: bool = False,
    memories: Optional[List[str]] = None,
    api_key: Optional[str] = None
) -> Generator[str, None, None]:
    """
    Main dispatcher for streaming responses from the chosen AI provider.
    Injects persistent long-term memories and real-time web search.
    """
    provider = provider.lower()
    provider_info = PROVIDERS_CONFIG.get(provider, PROVIDERS_CONFIG["gemini"])
    target_model = model or provider_info["default_model"]

    # Build system prompt with persistent long-term memories
    system_text = SYSTEM_PROMPT
    if memories and len(memories) > 0:
        mem_bullets = "\n".join([f"- {m}" for m in memories])
        system_text += f"\n\n[Persistent Long-Term Memories about the User]:\n{mem_bullets}\nUse these memories naturally whenever relevant to personalize responses."

    # Web search integration
    if enable_search:
        search_triggers = ["who is", "what is", "news", "weather", "latest", "price", "today", "current", "released", "2024", "2025", "2026", "search", "browse"]
        prompt_lower = user_prompt.lower()
        should_search = any(trigger in prompt_lower for trigger in search_triggers) or len(user_prompt.split()) > 4
        
        if should_search:
            yield "🔍 *Searching the web for latest information...*\n\n"
            search_context = perform_web_search(user_prompt)
            if search_context:
                system_text += (
                    f"\n\n[Live Web Search Results for User Prompt]:\n{search_context}\n"
                    "Incorporate these current facts into your response. Cite references when appropriate."
                )

    if provider == "gemini":
        yield from _stream_gemini(history, user_prompt, system_text, target_model, api_key)
    elif provider == "groq":
        yield from _stream_groq(history, user_prompt, system_text, target_model, api_key)
    elif provider == "ollama":
        yield from _stream_ollama(history, user_prompt, system_text, target_model)
    elif provider == "anthropic":
        yield from _stream_anthropic(history, user_prompt, system_text, target_model, api_key)
    else:
        yield f"❌ Unsupported provider: {provider}"

def transcribe_audio_input(audio_bytes: bytes) -> Dict[str, Any]:
    """
    Transcribes audio bytes recorded via Streamlit's native st.audio_input.
    Uses Python's SpeechRecognition library with Google's free speech recognition engine.
    """
    try:
        import speech_recognition as sr
        from pydub import AudioSegment

        audio_io = io.BytesIO(audio_bytes)
        try:
            sound = AudioSegment.from_file(audio_io)
        except Exception:
            audio_io.seek(0)
            sound = AudioSegment.from_wav(audio_io)

        wav_io = io.BytesIO()
        sound.set_channels(1).set_frame_rate(16000).export(wav_io, format="wav")
        wav_io.seek(0)

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_io) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.2)
            audio_data = recognizer.record(source)

        text = recognizer.recognize_google(audio_data)
        return {"success": True, "text": text, "error": None}

    except Exception as e:
        return {"success": False, "text": "", "error": f"Audio processing error: {str(e)}"}
