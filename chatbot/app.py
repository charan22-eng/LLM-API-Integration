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
from pydantic import BaseModel

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


class ChatRequest(BaseModel):
    conversation_id: str
    message: str


app = FastAPI(title="Sage - Study Buddy Chatbot")


@app.post("/chat")
async def chat(request: ChatRequest):
    conv_id = request.conversation_id.strip() if request.conversation_id else ""
    if not conv_id:
        return JSONResponse(
            status_code=400,
            content={"error": "conversation_id is required."}
        )

    raw_message = request.message or ""
    trimmed_message = raw_message.strip()

    # Reject empty or whitespace-only messages
    if not trimmed_message:
        return JSONResponse(
            status_code=400,
            content={"error": "Message cannot be empty or whitespace only."}
        )

    # Cap message length at 2000 characters
    if len(raw_message) > 2000:
        return JSONResponse(
            status_code=400,
            content={"error": "Message exceeds the maximum limit of 2000 characters."}
        )

    if conv_id not in conversations:
        conversations[conv_id] = []

    # Append user message to conversation history
    conversations[conv_id].append({"role": "user", "text": raw_message})

    try:
        # Build contents from truncated context window
        context_slice = get_context_window(conversations[conv_id])
        contents = [
            types.Content(
                role=msg["role"],
                parts=[types.Part(text=msg["text"])]
            )
            for msg in context_slice
        ]

        model_name = os.getenv("GEMINI_MODEL", GEMINI_MODEL)
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT
                )
            )
        except Exception as model_exc:
            if ("404" in str(model_exc) or "NOT_FOUND" in str(model_exc)) and model_name != "gemini-3.5-flash":
                logger.warning("Model %s returned 404, falling back to gemini-3.5-flash", model_name)
                response = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT
                    )
                )
            else:
                raise model_exc

        reply_text = getattr(response, "text", None)
        if not reply_text or not reply_text.strip():
            # Treat empty/None response as invalid response: roll back user message
            if conversations[conv_id] and conversations[conv_id][-1]["role"] == "user":
                conversations[conv_id].pop()
            return JSONResponse(
                status_code=502,
                content={"error": "Something went wrong talking to the AI. Please try again."}
            )

        # On success, append model reply to history
        conversations[conv_id].append({"role": "model", "text": reply_text})

        # Bound total in-memory history to prevent memory leaks
        if len(conversations[conv_id]) > MAX_STORED_HISTORY:
            conversations[conv_id] = conversations[conv_id][-MAX_STORED_HISTORY:]

        return {
            "reply": reply_text,
            "context_count": len(get_context_window(conversations[conv_id]))
        }

    except Exception as exc:
        # Log real exception to console without exposing API key or sensitive data
        logger.error("Error during Gemini API call: %s", exc, exc_info=True)

        # Remove the user message that was just appended to maintain history consistency
        if conv_id in conversations and conversations[conv_id] and conversations[conv_id][-1]["role"] == "user":
            conversations[conv_id].pop()

        exc_str = str(exc)
        exc_type = type(exc).__name__.lower()
        status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)

        # 1. Timeout -> HTTP 504
        if (
            "timeout" in exc_type
            or "timeout" in exc_str.lower()
            or "timed out" in exc_str.lower()
            or "deadline" in exc_str.lower()
            or status_code in (504, 408)
        ):
            return JSONResponse(
                status_code=504,
                content={"error": "The AI took too long to respond. Please try again."}
            )

        # 2. Rate limit / quota -> HTTP 429
        if (
            status_code == 429
            or "429" in exc_str
            or "RESOURCE_EXHAUSTED" in exc_str
            or "quota" in exc_str.lower()
            or "rate limit" in exc_str.lower()
        ):
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit reached. Please wait a moment and try again."}
            )

        # 3. Invalid API key / auth error -> HTTP 500
        if (
            status_code in (401, 403)
            or "API_KEY_INVALID" in exc_str
            or "PERMISSION_DENIED" in exc_str
            or "UNAUTHENTICATED" in exc_str
            or "invalid api key" in exc_str.lower()
            or "unauthorized" in exc_str.lower()
            or "forbidden" in exc_str.lower()
        ):
            return JSONResponse(
                status_code=500,
                content={"error": "Server configuration error with the AI service."}
            )

        # 4. Any other exception -> HTTP 502
        return JSONResponse(
            status_code=502,
            content={"error": "Something went wrong talking to the AI. Please try again."}
        )
