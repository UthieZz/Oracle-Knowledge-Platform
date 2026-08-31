# Exact next step for the operator

## What “on main” means

When I say code is **on main**, it is already **committed and pushed** to GitHub at
`UthieZz/Oracle-Knowledge-Platform` branch `main`.

You do **not** re-upload it. You only **pull** it to your machine / deploy target:

```bash
cd /path/to/Oracle-Knowledge-Platform
git pull origin main
```

If Studio is a separate checkout or Vercel deploy, pull/redeploy that path too so
`studio/src/services/ModelRegistry.ts` and Settings changes load.

## What just landed (multi-model)

- Removed hard-coded `gemini-2.0-flash` (shutdown / replaced family).
- Default: `gemini-flash-latest`.
- Settings: provider + model picker + per-provider API keys.
- Providers: Gemini, Groq, OpenRouter, DeepSeek, xAI, OpenAI (optional paid).
- Catalog includes Nano Banana / Omni / TTS entries for **later** media wiring;
  grounded Ask is text-first today.

## Verify

```bash
git pull origin main
git log -8 --oneline
# rebuild Studio if needed
cd studio && npm install && npm run build
```

In Studio → Settings:

1. Pick **Gemini Flash (latest)** or **2.5 / 3.x Flash** + your Gemini key → Ask once.
2. Optionally add a **Groq** key and switch model → Ask once.

Reply: model that worked + any error text.

Do not start Stage 4 attachments until this pull is live on your Studio build.
