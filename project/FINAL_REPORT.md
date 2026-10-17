# Final Report: Proper Context Window Management

## 1. Executive Summary
We upgraded and hardened the context window management architecture in the Sage study-buddy chatbot across backend logic, server resource safety, API protocol compliance, and UI feedback.

---

## 2. Implemented Architecture

### Backend (`chatbot/app.py`)
1. **Sliding Truncation Window (`MAX_MESSAGES = 10`):**
   - Keeps the context sent to Gemini capped at the most recent 10 messages.
2. **Guaranteed Leading User Turn:**
   - Evaluates the start of the window and drops leading model messages (`while window and window[0]['role'] == 'model': window = window[1:]`), preventing orphaned assistant turns.
3. **Strict Role Alternation Normalization:**
   - Fulfills the Gemini API contract by ensuring turns alternate strictly (`user` -> `model` -> `user` ...). Any consecutive same-role messages are cleanly merged with `\n\n`.
4. **Token/Character Budget Guard (`MAX_CONTEXT_CHARS = 16000`):**
   - Guards against payload overflow by pruning oldest turn pairs if messages exceed character budget.
5. **In-Memory Store Bounding (`MAX_STORED_HISTORY = 100`):**
   - Caps conversational arrays stored in memory at 100 turns per session, eliminating server memory leaks.
6. **On-Demand Context Reset (`POST /reset`):**
   - Wipes in-memory conversation history for the specified session ID.
7. **Port Collision Resilience:**
   - Detects if port 8000 is occupied (e.g., by Docker Desktop or system services) and auto-selects port 8001.

### Frontend (`chatbot/static/index.html`)
1. **Dynamic Context Badge:**
   - Real-time pill badge in the header displaying active turns (e.g., `Context: 2 / 10 msgs` or `Context: 10 / 10 (Sliding Window)`).
2. **"New Chat" Button:**
   - Allows users to reset conversation history with one click, issuing a fresh UUID and clearing the screen to an initial greeting.

---

## 3. Verification & QA
- **Unit Test**: Verified sliding window truncation, leading model drops, and role alternation normalization.
- **Integration Test**: Verified `POST /chat` and `POST /reset` endpoints live on `http://127.0.0.1:8001`.
- **UI Test**: Verified header action controls and responsive rendering.

---

## 4. How to Run
```bash
cd chatbot
python app.py
```
Open in browser:
**http://127.0.0.1:8001** (or http://127.0.0.1:8000 if port 8000 is free).
