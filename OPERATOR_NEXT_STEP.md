# Exact next step for the operator

Code is already on `main` at `UthieZz/Oracle-Knowledge-Platform`.
You do **not** re-upload. Pull only.

```bash
cd /path/to/Oracle-Knowledge-Platform
git pull origin main
git log -5 --oneline
```

Confirm these files exist and `studio/` was not replaced:

```bash
test -f docs/studio-infusion.md && echo INFUSION_DOC_OK
test -f studio/package.json && echo STUDIO_PACKAGE_OK
grep -n '"name"' studio/package.json | head -1
# expected: "oracle-studio" — NOT "app-builder-workspace"
```

Optional sanity build (does not deploy):

```bash
cd studio && npm install && npm run build
```

Also confirm the satellite repo is still separate:

```bash
git ls-remote git@github.com:UthieZz/OKP-Studio.git HEAD
```

## Reply with this paste

1. Last 5 `git log --oneline` lines.
2. The `name` line from `studio/package.json`.
3. Whether `npm run build` in `studio/` succeeded.
4. Local path of both checkouts if you have `OKP-Studio` cloned.

Do **not** copy `OKP-Studio` files into `studio/` yourself.
Do **not** start a git subtree until the next agent step after this paste.
Do **not** start Stage 4 attachments until Stage 3 live Ask is verified.
