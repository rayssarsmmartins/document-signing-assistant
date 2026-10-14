# setup — onboarding (run once, or when the pre-check fails)

Load `.agents/skills/ops-onboarding/SKILL.md` and run its checklist in order. This is the only
moment you may talk about configuration with the user. Keep it short, in pt-BR, one step at
a time.

1. `bin/cs doctor` — show only the failing items, translated into plain language.
2. Python dependencies missing → `uv sync`.
3. Clicksign MCP: call `clicksign_select_account` with the account from `.env`.
   - OAuth error → guide the user through the login (`/mcp` in pi → `clicksign` → login), and
     try again.
   - No account in `.env` → call it without a key to list the available accounts, ask which
     one to use, and write `CLICKSIGN_ACCOUNT_KEY`/`CLICKSIGN_ACCOUNT_NAME` to `.env`.
4. Upload bridge: if `UPLOAD_BACKEND`/`UPLOAD_BUCKET` are missing, explain that a bucket with
   signed URLs is needed (S3, R2, MinIO or GCS) and collect the parameters. Never create cloud
   resources or credentials on your own. Then run `bin/cs doctor` again.
5. Consent to read documents (a locked product decision: it is resolved here, never mid-journey).
   Explain once that the assistant reads the attached document to suggest who signs, and that
   the text is deleted after the send.
6. Finish with `bin/cs doctor`; the exit code must be 0, or 1 with only the `mode` warning in
   dry run.
