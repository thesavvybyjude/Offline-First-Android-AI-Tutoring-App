# Comprehensive Codebase Audit and Testing Plan

The goal of this task is to review the entire Offline-First Android AI Tutoring App codebase, ensure that all modules (frontend and backend) are integrated correctly, run all tests, fix any existing issues or bugs, and guarantee that the app is working correctly from end-to-end.

## User Review Required

> [!NOTE]
> The dependencies for the project are currently being installed in the background. Once they are installed, I will execute the tests as the first step of this plan.

> [!WARNING]
> Please review this plan and let me know if there are any specific features or flows (like specific UI screens or specific ML models) you want me to prioritize testing, or if you have any constraints on the testing process.

## Open Questions

- Should I download the ~2.1GB Phi-3 model using the `setup_env.py` script to do a true end-to-end integration test with the local LLM, or is mocking the inference engine (as currently done in some tests) sufficient for now? 
- Would you like me to attempt building an Android APK using Buildozer to ensure the Kivy app packages correctly?

## Proposed Approach

### 1. Wait for Dependency Installation
Before proceeding, I will wait for the `.venv` virtual environment to finish installing the requirements (Kivy, Flask, sentence-transformers, FAISS, llama-cpp-python, etc.). 

### 2. Run Existing Test Suite
Once dependencies are ready, I will execute the existing automated tests (`pytest tests/test_all.py`). I will:
- Identify any failing tests across the RAG Pipeline, SM2 Scheduler, and Semantic Chunker.
- Fix backend logic and tests until the test suite passes 100%.

### 3. Static Code Analysis and Review
I will review the codebase for common issues, missing imports, and logical gaps. I'll focus on:
- **Frontend-Backend Integration**: Checking how `frontend/main.py` interfaces with `backend/server.py` and the offline SQLite databases.
- **UI Screens**: Checking `login_screen.py`, `dashboard_screen.py`, `tutor_chat_screen.py`, etc., for missing dependencies, unhandled exceptions, and correct Kivy widget usage.

### 4. End-to-End Verification
I will manually start the backend server and frontend Kivy app in a local testing environment to verify:
- Navigation between screens works smoothly.
- The sync layer and database creation function correctly without crashing.

## Verification Plan

### Automated Tests
- `.\.venv\Scripts\pytest tests/ -v`

### Manual Verification
- `.\.venv\Scripts\python frontend\main.py` to ensure the UI boots successfully and the local server subprocess spawns correctly.
