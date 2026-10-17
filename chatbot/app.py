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

app = FastAPI(title="Sage - Study Buddy Chatbot")
