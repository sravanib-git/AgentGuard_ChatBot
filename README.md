# AgentGuard documentation support

The application finds original AgentGuard documentation sections and displays their source links. It uses local BM25 keyword search. It has no LLM, RAG generation, API key, model prompt, vector database or external search service.

## Start on Windows

1. Double-click setup.cmd once on a new checkout. It creates .venv using Python 3.12 or uv. No third-party Python packages are installed. If Python is unavailable, install Python 3.12 or uv first; uv can download Python during setup.
2. Double-click start.cmd. Keep its terminal open.
3. The browser opens at http://127.0.0.1:3101. Ctrl+C stops the server.

The default port is 3101. An optional .env file may contain PORT=3102 to select another port. No .env file or credentials are required by default. An existing server belonging to this project is reused; another application on the configured port produces a clear error.

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
| lib/search.py | BM25 keyword/question ranking, full-text fallback, SDK filtering and follow-up hints |
| lib/keywords.py | Extracts important keywords from section text |
| generate_keywords.py | Regenerates section-keyword metadata |
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
| data/section-keywords.json | Keywords for each page, section and SDK variant |
| test/ | Python service/HTTP/startup/clarification tests and JavaScript input/memory tests |
| docs/architecture.md | Data flow, boundaries and limitations |
| setup.cmd, start.cmd, start.ps1 | Windows setup/start/test commands |
| .env.example | Optional port-setting example |
| .gitignore | Excludes environment files, bytecode and logs |
| package.json | Optional browser-memory test command; no npm dependencies |
| .venv/ | Local Python runtime required by the startup scripts; do not commit |

## Documentation updates

Each of the 72 sections has its own keywords in `data/section-keywords.json`, keyed by page, section anchor, and SDK language. Keywords are extracted from section headings, important AgentGuard concepts present in the text, technical option names, and distinctive words. You can review and edit these lists. Search first ranks keyword and hypothetical-question matches together with BM25, then uses full-text-only matches to fill remaining result slots. Existing SDK filters, related-section inclusion, and result limits still apply. Keywords and hypothetical questions are search metadata; displayed excerpts remain original documentation.

After changing the documentation snapshot, regenerate keywords with `.\.venv\Scripts\python.exe -B generate_keywords.py`, review the JSON, and restart the server. Regeneration replaces manual edits. Missing keyword coverage is reported at startup.

Replace data/knowledge.json with an updated documentation export when guides change. The app uses the individual sections; a combined page-text copy is unnecessary. Review hypothetical-question mappings against updated section anchors. Run the tests after regenerating keywords; update the snapshot-count test if the number of sections intentionally changes.

Do not edit documentation statements to conceal contradictions. Some guardrail-execution descriptions differ across source sections; search preserves both perspectives when relevant.

## Verification and deployment

The suite contains 29 Python tests and three JavaScript tests covering search metadata and fallback priority, original excerpts, SDK context, clarification, input limits, secret filtering, URLs, HTTP limits, startup, and chat reset behavior. Actual console browser lifecycle behavior still needs review.

The standard-library server is a loopback-only standalone prototype. It is not the AgentGuard console integration or a production server. Console authentication, hosting and actual Support-panel component integration remain separate tasks. Secret-pattern checks are limited heuristics and can miss unfamiliar formats or block harmless text.
