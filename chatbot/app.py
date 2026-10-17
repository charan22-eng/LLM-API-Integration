import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("chatbot")

# Base paths
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
ENV_PATH = BASE_DIR / ".env"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Load environment variables
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

if not GEMINI_API_KEY or not GEMINI_API_KEY.strip():
    raise RuntimeError(
        "GEMINI_API_KEY is missing. Please set your Gemini API key in the .env file or environment."
    )

# Initialize Gemini Client with a 30-second request timeout (30000 ms)
client = genai.Client(
    api_key=GEMINI_API_KEY.strip(),
    http_options=types.HttpOptions(timeout=30000)
)

SYSTEM_PROMPT = (
    "You are Sage, a friendly study-buddy tutor for college students. "
    "Your style is concise, encouraging, and explains concepts step by step. "
    "At the end of each response, ask one short follow-up question to check understanding. "
    "Stay strictly on study and learning topics; if the user asks off-topic or unrelated questions, "
    "politely redirect them back to their studies."
)

MAX_MESSAGES = 10
MAX_STORED_HISTORY = 100
MAX_CONTEXT_CHARS = 16000

# In-memory conversation store: conversation_id -> list[{"role": "user" | "model", "text": str}]
conversations: dict[str, list[dict]] = {}


def get_context_window(history: list[dict]) -> list[dict]:
    """Retrieves a normalized, safely truncated context window.

    Rules enforced:
    1. Truncates to the most recent MAX_MESSAGES entries.
    2. Ensures the window starts with a 'user' turn (drops leading 'model' messages).
    3. Normalizes turns so roles strictly alternate ('user' -> 'model' -> 'user' ...),
       merging consecutive same-role messages with newlines to fulfill Gemini API constraints.
    4. Guards against token budget overflow by capping total context characters.
    """
    if not history:
        return []

    # 1. Truncate to the most recent MAX_MESSAGES
    window = list(history[-MAX_MESSAGES:])

    # 2. Drop any leading model messages so window always begins with a user turn
    while window and window[0].get("role") == "model":
        window = window[1:]

    if not window:
        return []

    # 3. Normalize turn alternation: merge consecutive same-role messages
    normalized: list[dict] = []
    for msg in window:
        role = msg.get("role", "user")
        text = msg.get("text", "")
        if normalized and normalized[-1]["role"] == role:
            normalized[-1]["text"] = f"{normalized[-1]['text']}\n\n{text}"
        else:
            normalized.append({"role": role, "text": text})

    # Ensure leading message remains user
    while normalized and normalized[0]["role"] == "model":
        normalized = normalized[1:]

    # 4. Token/Character budget guard: if total length exceeds limit, prune oldest pairs
    while len(normalized) > 2 and sum(len(m["text"]) for m in normalized) > MAX_CONTEXT_CHARS:
        normalized = normalized[2:]

    return normalized

app = FastAPI(title="Sage - Study Buddy Chatbot")
