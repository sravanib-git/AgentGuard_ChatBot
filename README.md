# AgentGuard documentation support - fresh implementation

This project was written from scratch in AG_ChatBot_Final. Only the documentation snapshot and reviewed search-question metadata were reused from the earlier project. The existing AG_ChatBot folder is unchanged.

The application finds original AgentGuard documentation sections and displays their source links. It uses local BM25 keyword search. It has no LLM, RAG generation, API key, model prompt, vector database or external search service.

## Start on Windows

1. Double-click setup.cmd once on a new checkout. It creates .venv using Python 3.12 or uv. No third-party Python packages are installed. If Python is unavailable, install Python 3.12 or uv first; uv can download Python during setup.
2. Double-click start.cmd. Keep its terminal open.
3. The browser opens at http://127.0.0.1:3101. Ctrl+C stops the server.

Port 3101 lets this project coexist with the earlier prototype on 3100. An optional .env file may contain PORT=3102 to select another port. No .env file or credentials are required by default. An existing server belonging to this project is reused; another application on the configured port produces a clear error.

Direct commands:

```powershell
.\.venv\Scripts\python.exe -B run.py
.\.venv\Scripts\python.exe -B run.py --no-browser
.\.venv\Scripts\python.exe -B -m unittest discover -s test -v
.\start.ps1 -Test
```

UI-input and browser-memory tests use Node 22+ with `npm run test:browser`. package.json defines only module handling and that test command. There are no npm dependencies, and Node is not needed to run the app.

## What happens on a question

The server validates the request and bounded history. The service checks common secret patterns and handles greetings locally. Blank/whitespace input is disabled in the UI and rejected by the API. Meaningful fragments such as "Python SDK setup" search normally; vague actions and pronouns without a user-established topic receive a clarification question before search. Filler-only input asks for a feature or topic. A short reply can complete an earlier missing-topic question, and an explicit new subject replaces the previous SDK context. These are lexical rules, not semantic understanding. BM25 ranks eligible documentation sections using the question, relevant earlier user topics, SDK hints and reviewed hypothetical questions. The browser displays the original matched sections; it never generates a new explanation.

Results include at most five complete sections within 30,000 characters. Long sections are skipped rather than truncated. When no section matches, the response says it could not find a relevant section rather than claiming that the answer is absent. Search can still miss details or return loosely related results. Ranking scores are not confidence in factual correctness. Questions such as 'explain it more simply' can refine the search topic but cannot produce a rewritten explanation.

The browser stores history only in memory. Close chat, New chat, navigation and reload clear it. Late responses after reset are ignored. The backend receives at most three complete exchanges, capped at 18,000 characters, and never stores transcripts. Search itself makes no outbound network calls. Opening source links visits the existing documentation site.

## Folder map

| Path | Purpose |
|---|---|
| run.py | Entry point, port settings, duplicate-start detection and browser opening |
| lib/documentation.py | Validates local documents and source links; creates numbered immutable sections |
| lib/search.py | Fresh pure-Python BM25 implementation, SDK filtering and follow-up hints |
| lib/security.py | Request/history limits and common-secret checks |
| lib/service.py | Coordinates fixed replies and original documentation results |
| lib/server.py | Standard-library HTTP server, static-file allowlist, headers and rate/body limits |
| lib/__init__.py | Package marker |
| public/index.html | Browser page and controls |
| public/style.css | Responsive UI styling |
| public/memory.js | Temporary history, bounded exchanges and stale-response protection |
| public/app.js | UI events, local API requests and safe text rendering |
| data/knowledge.json | Reused documentation snapshot: nine guides, 72 sections |
| data/hypothetical-questions.json | Reused reviewed search phrasing; never displayed as source text |
| test/ | Python service/HTTP/startup/clarification tests and JavaScript input/memory tests |
| docs/architecture.md | Data flow, boundaries and limitations |
| setup.cmd, start.cmd, start.ps1 | Windows setup/start/test commands |
| .env.example | Optional port-setting example |
| .gitignore | Excludes environment files, bytecode and logs |
| package.json | Optional browser-memory test command; no npm dependencies |
| .venv/ | Newly created local Python environment; do not commit |

## Documentation updates

This version consumes a validated JSON snapshot. It does not include the old TSX importer or its parser dependencies. When docs change, produce an updated export with the existing importer in the earlier project and replace data/knowledge.json here. Review hypothetical-question mappings against the updated section anchors. Restart after replacing data and run the tests; the current snapshot-count test must be updated if the number of sections intentionally changes.

Do not edit documentation statements to conceal contradictions. Some guardrail-execution descriptions differ across source sections; search preserves both perspectives when relevant.

## Verification and deployment

Verification passes 26 Python test methods, including subcases across nine documentation workflows, blank/ambiguous HTTP requests and clarification/topic handling, plus three JavaScript UI-input and browser-memory tests. Tests cover offline/verbatim results, query metadata, SDK context, input limits, secret filtering, URLs, API limits and reset/stale-answer logic. Actual console browser lifecycle behavior still needs review.

The standard-library server is a loopback-only standalone prototype. It is not the AgentGuard console integration or a production server. Console authentication, hosting and actual Support-panel component integration remain separate tasks. Secret-pattern checks are limited heuristics and can miss unfamiliar formats or block harmless text.
