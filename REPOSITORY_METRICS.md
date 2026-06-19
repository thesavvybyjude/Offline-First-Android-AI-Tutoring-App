# Repository Metrics

These metrics represent the exact counts derived from the source code during the audit phase, excluding virtual environments and Git tracking directories.

| Metric | Count |
| ------ | ----- |
| Number of files | 42 |
| Number of Python files | 26 |
| Number of classes | 73 |
| Number of functions | 338 |
| Number of API routes | 4 |
| Number of database tables | 5 |
| Number of screens | 5 |
| Number of test cases | 37 |

---

### Route Breakdown
1. `GET /health`
2. `POST /query`
3. `POST /api/v1/sync/push`
4. `GET /api/v1/sync/pull`

### Table Breakdown
1. `students`
2. `knowledge_items`
3. `repetition_records` (Edge)
4. `sync_log`
5. `repetition_records` (Cloud Server)

### Screen Breakdown
1. `login_screen.py`
2. `dashboard_screen.py`
3. `review_screen.py`
4. `tutor_chat_screen.py`
5. `settings_screen.py`
