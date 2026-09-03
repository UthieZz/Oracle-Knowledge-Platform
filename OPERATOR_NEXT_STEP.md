# Exact next step for the operator

Stage 3.6 is on branch `stage-3.6-browser-ingest` in `UthieZz/Oracle-Knowledge-Platform`.
Do **not** copy `OKP-Studio` into `studio/`.

```bash
cd /path/to/Oracle-Knowledge-Platform
git fetch origin
git checkout stage-3.6-browser-ingest
git pull origin stage-3.6-browser-ingest
git log -8 --oneline
```

Confirm live Studio identity is unchanged:

```bash
grep -n '"name"' studio/package.json | head -1
# expected: "oracle-studio" — NOT "app-builder-workspace"
test -f studio/src/services/importApi.ts && echo IMPORT_API_OK
test -f docs/studio-infusion.md && echo INFUSION_DOC_OK
```

Run both processes from the repo root:

```bash
# terminal 1 — Flask must own uploads/
python3 -m src.studio.api_server

# terminal 2
cd studio && npm install && npm run dev
```

In Studio Import:

1. Choose a small `.json` export (not a random binary).
2. Status should become `queued`, not an alert about moving files by hand.
3. Confirm the file landed:

```bash
ls -lt uploads | head
```

Then compile the **canonical** way (do not treat `/api/compile` as freeze path yet):

```bash
python run.py
```

Optional Studio build check:

```bash
cd studio && npm run build
```

## Reply with this paste

1. Last 8 `git log --oneline` lines on this branch.
2. The `name` line from `studio/package.json`.
3. Whether Flask was running when you selected a file.
4. Output of `ls -lt uploads | head` after the browser pick.
5. Whether `npm run build` in `studio/` succeeded.

Do **not** subtree-merge `OKP-Studio`.
Do **not** replace `studio/package.json`.
Do **not** start Stage 4 attachments until Stage 3 live Ask is verified.
