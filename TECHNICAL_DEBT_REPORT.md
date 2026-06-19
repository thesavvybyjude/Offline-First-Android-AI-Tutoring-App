# Technical Debt & Repository Gap Analysis

This report identifies missing documentation, uncompleted features, and architectural vulnerabilities discovered during the repository audit.

---

## 1. Missing Features & Incomplete Modules

| Location | Problem | Impact | Suggested Fix |
| -------- | ------- | ------ | ------------- |
| `frontend/widgets/` | Empty directory. No reusable custom Kivy components found. | UI code is duplicated across `screens/`. Codebase lacks a unified design system. | Create custom classes for standard Buttons, Cards, and Inputs inside this directory and import them into screens. |
| `backend/server.py` | Missing API Authentication. Endpoints like `/api/v1/sync/push` accept data without verifying the client. | Severe security vulnerability. Any malicious user could push fake progress data if they know a `student_id`. | Implement JWT (JSON Web Tokens) or OAuth2 headers for all `/api/v1/sync` routes. |
| `frontend/main.py` | Connectivity checking relies on a blocking HTTP request before allowing sync. | If the network is extremely slow, the main Kivy UI thread might freeze during initialization. | Move the `ConnectivityChecker` into a dedicated non-blocking thread or asyncio loop within Kivy's `Clock`. |
| `backend/database.py` | Exists in directory structure but core DB initialization actually happens inside `sm2_scheduler.py`. | Separation of concerns is violated. Code logic is tangled. | Refactor `sm2_scheduler.py` to inherit or depend on a unified DB connection manager from `database.py`. |
| Kivy UI Architecture | Kivy UI elements are declared purely in Python rather than utilizing Kivy language (`.kv` files). | UI code is verbose and harder to maintain or theme. | Migrate UI component layouts to `tutorapp.kv` to separate styling logic from business logic. |

---

## 2. Missing Documentation

* **Deployment Guide**: No instructions exist for deploying `backend/server.py` to a production environment (e.g., Gunicorn/Nginx setup, Dockerfiles).
* **Model Sourcing**: The documentation mentions "Phi-3-mini-4k-instruct-q4.gguf" but does not explicitly detail the exact HuggingFace source URL or the prompting format (ChatML vs Llama format) required by the model.
* **Corpus Processing**: `corpus_processor.py` is present but undocumented. There is no guide on how educators can upload new PDFs to expand the RAG knowledge base.

---

## 3. Recommended Refactoring

* **Hardcoded Paths**: Several paths in `rag_pipeline.py` assume specific working directory structures (`data_dir / "curriculum.index"`). These should be configurable via environment variables (`.env`).
* **Test Coverage**: While `test_all.py` covers happy paths, it lacks stress-testing for the `ConflictResolver` in edge cases (e.g., simultaneous bidirectional sync conflicts with identical timestamps).
