# Sage — LLM Study-Buddy Chatbot with Multi-Turn Memory

An intelligent, lightweight study-buddy tutor built with **FastAPI**, **Google Gemini** (`google-genai` SDK), and a vanilla HTML/CSS/JavaScript frontend. Sage explains academic concepts step-by-step, asks follow-up questions to test understanding, politely redirects off-topic inquiries, and manages multi-turn conversational context seamlessly.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-green)
![Gemini](https://img.shields.io/badge/Google%20GenAI-Gemini%20API-orange)
![License](https://img.shields.io/badge/License-MIT-purple)

---

## Key Features

- **Multi-Turn Conversational Memory:** Preserves multi-turn state across interactions with proper sliding window truncation.
- **Robust Context Window Management:**
  - 10-message rolling window truncation (`MAX_MESSAGES = 10`).
  - Leading model turn drop (guarantees context always begins with a user turn).
  - Strict turn alternation normalization (`user` ➔ `model` ➔ `user`...) to prevent API errors.
  - Token and character budget overflow guard (`MAX_CONTEXT_CHARS = 16000`).
  - Server memory leak bounding (`MAX_STORED_HISTORY = 100`).
- **Dynamic Context Badge & Reset:** Header displays real-time context utilization and includes a "New Chat" reset button.
- **Resilient Error Handling:** Graceful user-friendly error bubbles for rate limits (429), timeouts (504), service spikes (503/502), and auth issues (500).
- **Port Collision Fallback:** Automatically selects port 8001 if port 8000 is occupied (e.g. by Docker).
- **No Build Step:** Clean vanilla JS and CSS frontend without complex tooling.

---

## Repository Structure

```
├── .gitignore               # Root git ignore protecting secrets
├── README.md                # Repository overview and quickstart
├── chatbot/                 # Main application source
│   ├── app.py               # FastAPI server and Gemini integration
│   ├── static/
│   │   └── index.html       # Single-page chat interface
│   ├── requirements.txt     # Python dependencies
│   ├── .env.example         # Environment template
│   ├── .gitignore           # Chatbot local git ignore
│   └── README.md            # Chatbot component documentation
└── project/                 # Engineering delivery artifacts
    ├── STATUS.md            # Multi-agent delivery tracker
    └── FINAL_REPORT.md      # Architecture and QA report
```

---

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>/chatbot
```

### 2. Set up virtual environment
- **Windows:**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **macOS / Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
cp .env.example .env
```
Edit `.env` and add your Google Gemini API key:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash
```

### 5. Run the application
```bash
python app.py
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** (or **[http://127.0.0.1:8001](http://127.0.0.1:8001)** if 8000 is in use).

---

## License
MIT License. Free for educational and personal use.
