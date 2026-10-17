# Project Status: Proper Context Window Management

## Scale: SMALL
**Target**: Enhance and verify context window management in Sage chatbot.

## Pipeline Progress
- [x] **Setup & Triage**: Problem identified — robust context window truncation, turn alternation guarantee, memory leak bounding, and UI context visibility/reset.
- [x] **Phase 1 · Backend Engineer**: Implemented robust context window manager in `chatbot/app.py`:
  - 10-message rolling truncation (`MAX_MESSAGES = 10`)
  - Guaranteed leading user turn (drops leading model turns)
  - Strict turn alternation normalization (merges consecutive same-role messages)
  - Token/character budget guard (`MAX_CONTEXT_CHARS = 16000`)
  - Server memory leak bounding (`MAX_STORED_HISTORY = 100`)
  - On-demand reset endpoint (`POST /reset`)
  - Port collision resilience (auto-switches to 8001 if Docker occupies 8000)
- [x] **Phase 2 · Frontend Engineer**: Added "New Chat" reset button and dynamic context badge (`Context: X / 10 msgs`) in `chatbot/static/index.html`.
- [x] **Phase 3 · Integration & Review**: Verified end-to-end integration across backend and frontend.
- [x] **Phase 4 · QA Engineer**: Validated single-turn, multi-turn, reset endpoint, and alternation normalization.
- [x] **Close**: Final report generated. Server active on `http://127.0.0.1:8001`.
