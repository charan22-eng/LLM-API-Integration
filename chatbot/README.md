# Sage — College Study-Buddy Chatbot

A lightweight LLM chatbot with multi-turn memory built using FastAPI, Google Gemini (`google-genai` SDK), and a vanilla HTML/CSS/JavaScript frontend. Sage acts as a friendly, supportive study-buddy tutor who explains academic topics step by step and checks understanding with follow-up questions.

---

## Setup & Running

### 1. Navigate to the project directory
```bash
cd chatbot
```

### 2. Create and activate a virtual environment
- **Linux/macOS:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
- **Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **Windows (Command Prompt):**
  ```cmd
  python -m venv venv
  .\venv\Scripts\activate.bat
  ```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Copy `.env.example` to `.env` and add your Google Gemini API key:
```bash
cp .env.example .env
```
Edit `.env`:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

### 5. Start the server
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## Proper Context Window Management

The chatbot implements a multi-layer context window management pipeline in `chatbot/app.py`:

1. **Sliding Truncation Window (`MAX_MESSAGES = 10`):**
   - The conversational turn history is sliced to the last 10 messages before submission to the Gemini API (`client.models.generate_content`).
2. **Leading Model Turn Dropping:**
   - If the first message in the 10-message slice has role `"model"`, it is discarded. This guarantees the context window always begins with a `"user"` message.
3. **Strict Role Alternation Normalization:**
   - The Gemini API strictly enforces alternating `user` and `model` turns. If consecutive messages of the same role occur, their contents are safely concatenated with newlines to ensure API compliance.
4. **Token & Character Budget Guard (`MAX_CONTEXT_CHARS = 16000`):**
   - To prevent blowing past model token limits, if the combined characters exceed the budget, the oldest turns are pruned in pairs while keeping the newest context intact.
5. **In-Memory Store Bounding (`MAX_STORED_HISTORY = 100`):**
   - In-memory conversation arrays are capped at 100 entries per conversation to prevent memory leaks during long-running sessions.
6. **On-Demand Context Reset (`POST /reset` & UI "New Chat"):**
   - Users can reset their context window and generate a clean session ID anytime via the "New Chat" button in the UI.
   - An active context pill badge in the header displays current context usage (e.g., `Context: 4 / 10 msgs` or `Context: 10 / 10 (Sliding Window)`).

---

## Error Handling Behaviour

- **Request Validation:** Messages that are empty, whitespace-only, or exceed 2000 characters are rejected with HTTP 400.
- **Service Timeouts:** API requests exceeding the 30-second deadline return HTTP 504 (*"The AI took too long to respond. Please try again."*).
- **Rate Limits & Quota:** Rate limit or quota exhaustion errors return HTTP 429 (*"Rate limit reached. Please wait a moment and try again."*).
- **Authentication & Configuration:** Missing or invalid API keys return HTTP 500 (*"Server configuration error with the AI service."*).
- **Fallback & Network Errors:** Empty model responses or upstream failures return HTTP 502 (*"Something went wrong talking to the AI. Please try again."*).
- **History Rollback:** On any failure, the user's message is immediately popped from the in-memory history so conversation turns remain consistent.
- **Client Security & Resilience:** Raw exceptions are logged on the server console and never exposed to the client. The frontend displays user-friendly, red-tinted error bubbles and immediately re-enables text input so the chat session remains interactive and uninterrupted.
