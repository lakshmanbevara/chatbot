"""
Configuration module for Zyren Personal Assistant.
Supports Free APIs (Google Gemini, Groq, local Ollama) as well as Anthropic Claude.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env file
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Provider Registry with Sleek Zyren Models
PROVIDERS_CONFIG = {
    "gemini": {
        "name": "Zyren Cloud Core",
        "badge": "Zyren",
        "env_key": "GEMINI_API_KEY",
        "portal_url": "https://aistudio.google.com/apikey",
        "portal_name": "AI Studio",
        "default_model": "gemini-3.5-flash",
        "models": [
            {"id": "gemini-3.5-flash", "name": "Zyren 3.5 Flash (Recommended)", "desc": "High intelligence, ultra-fast streaming responses"},
            {"id": "gemini-3.5-flash-lite", "name": "Zyren 3.5 Lite (Instant)", "desc": "Lowest latency responses for quick inquiries"},
            {"id": "gemini-3.8-flash", "name": "Zyren 3.8 Ultra (Deep Reasoning)", "desc": "Advanced reasoning, complex coding, and math"},
        ]
    },
    "groq": {
        "name": "Zyren Turbo Engine",
        "badge": "Turbo",
        "env_key": "GROQ_API_KEY",
        "portal_url": "https://console.groq.com/keys",
        "portal_name": "Groq Console",
        "default_model": "llama-3.3-70b-versatile",
        "models": [
            {"id": "llama-3.3-70b-versatile", "name": "Zyren 70B Versatile", "desc": "500 tokens/sec flagship open intelligence"},
            {"id": "llama-3.1-8b-instant", "name": "Zyren 8B Instant", "desc": "Instantaneous responses for quick queries"},
            {"id": "deepseek-r1-distill-llama-70b", "name": "Zyren R1 Reasoning", "desc": "Step-by-step reasoning and problem solving"},
        ]
    },
    "ollama": {
        "name": "Zyren Offline / Local",
        "badge": "Offline",
        "env_key": None,
        "portal_url": "https://ollama.com",
        "portal_name": "Ollama Website",
        "default_model": "llama3.2",
        "models": [
            {"id": "llama3.2", "name": "Zyren Local 3B", "desc": "Lightweight local model"},
            {"id": "llama3.1", "name": "Zyren Local 8B", "desc": "High performance local open weights"},
            {"id": "deepseek-r1:8b", "name": "Zyren Local R1", "desc": "Local reasoning model"},
            {"id": "mistral", "name": "Zyren Mistral", "desc": "General local assistant"},
        ]
    },
    "anthropic": {
        "name": "Zyren Claude Engine",
        "badge": "Claude",
        "env_key": "ANTHROPIC_API_KEY",
        "portal_url": "https://console.anthropic.com/",
        "portal_name": "Anthropic Console",
        "default_model": "claude-3-5-sonnet-20241022",
        "models": [
            {"id": "claude-3-5-sonnet-20241022", "name": "Zyren Sonnet", "desc": "Exceptional nuance and coding"},
            {"id": "claude-3-5-haiku-20241022", "name": "Zyren Haiku", "desc": "Fast and responsive"},
            {"id": "claude-sonnet-5-5", "name": "Zyren Sonnet 5.5", "desc": "Advanced next-gen endpoint"},
        ]
    }
}

# Default provider from .env or fallback to Gemini
DEFAULT_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()
if DEFAULT_PROVIDER not in PROVIDERS_CONFIG:
    DEFAULT_PROVIDER = "gemini"

# Database Path
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "zyren.db"))

# Application Metadata
APP_NAME = "Zyren"
APP_SUBTITLE = "Next-Generation AI Assistant"
APP_VERSION = "2.5.0"

# Default System Prompt
SYSTEM_PROMPT = """You are Zyren, a friendly study and coding assistant. Be warm, patient, and direct. Lead with the answer. Explain complex topics simply with examples. Give complete, working code in fenced blocks with short comments, and explain how to run it. When debugging, find the root cause and explain the fix. Be honest: say when you are unsure and never invent facts, libraries, or links. Use Markdown, keep simple answers short, and reply in the user's language. Decline harmful requests kindly and offer a safe alternative."""
