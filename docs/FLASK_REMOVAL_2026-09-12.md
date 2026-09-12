# Flask removal — 2026-09-12

## Decision

Removed Flask as a Studio backend.

## Why nothing critical broke

- `studio/` reads Firestore via `FirestoreService` and calls model APIs from the browser (`ChatService`).
- Import page already instructs local `python run.py` + Firestore publish; it does not POST to `/api/import`.
- No production code path in `studio/src` called `/api/*`.

## Removed

- `src/studio/api_server.py`
- `tests/test_beta_api.py` (required a live `:5000` Flask process)
- `api_server.log`
- `flask`, `flask-cors`, `werkzeug`, `gunicorn` from `requirements.txt`

## Adjusted

- `Dockerfile` no longer serves gunicorn/Flask; compiler-oriented image only.

## Still intentional

- Compiler CLI (`run.py`, export services) remains the write path.
- Studio remains the read/chat path over Firestore.

## xAI in ChatService

Already supported before this change:

- Provider `xai` → `https://api.x.ai/v1`
- Key storage `okp_xai_api_key` via Settings
- Non-Gemini providers use OpenAI-compatible chat completions

Expanded selectable models: Grok 4.3, 4.5, 4.6, Build 0.1, plus legacy fast alias.
