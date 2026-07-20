"""Groq LLM configuration for the Healthify agent."""
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Load env from backend/.env or repo root .env
_root = Path(__file__).resolve().parent.parent
load_dotenv(_root / "backend" / ".env")
load_dotenv(_root / ".env")


def get_llm(temperature: float = 0.2, model: str = "llama-3.3-70b-versatile") -> ChatGroq:
    """Return a configured Groq ChatGroq instance."""
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key or api_key.startswith("gsk_your"):
        raise ValueError(
            "GROQ_API_KEY is not set. Add your Groq API key to backend/.env. "
            "Get a free key at https://console.groq.com"
        )
    return ChatGroq(
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=4096,
    )
