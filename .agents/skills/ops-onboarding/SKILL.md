---
name: ops-onboarding
description: Prepares the signature assistant for first use — Clicksign MCP authentication, which Clicksign account to use, the upload bucket (signed URLs) and consent to read documents. Use when `bin/cs doctor` reports an error, the MCP asks for login or account selection, or the user asks to configure or reconfigure the assistant.
metadata:
  category: ops
---

# Onboarding

The JTBD locks one decision: **permission to read the document is resolved before the flow,
never during it**. Everything here happens once, so the journey can run without configuration
questions.

## What must be true at the end

| Item | Check | Fix |
| --- | --- | --- |
| Python deps | `bin/cs doctor` → `python-deps` ok | `uv sync` |
| Clicksign MCP authenticated | `clicksign_select_account` answers without an auth error | user logs in (pi: `/mcp` → `clicksign` → login) |
| Account defined | `.env` has `CLICKSIGN_ACCOUNT_KEY` (+ `CLICKSIGN_ACCOUNT_NAME`) | list accounts (call `clicksign_select_account` without a key; the error lists `account_key (nome)`), ask which one, write `.env` |
| Upload bridge | `bin/cs doctor` → `upload-bridge` ok, and `bin/cs upload selftest <any pdf>` returns `content_matches: true` | default `UPLOAD_BACKEND=tunnel` needs only the `cloudflared` binary (`~/.local/bin/cloudflared`). Optional: an S3-compatible or GCS bucket (see `.env.example`) |
| Consent | user acknowledged that the document is read to suggest signers, and that its text is deleted after sending | one short explanation |

## Domain rules

- The OAuth session can see **several accounts**. Sending from the wrong account is a wrong
  send, so the account is fixed in `.env` and re-selected at the start of every session.
- The Clicksign MCP **only accepts public HTTPS URLs** for files. The default bridge is a
  Cloudflare **quick tunnel** (no account): a random 128-bit path, a single file, a 10-minute
  TTL, at most 3 downloads, closed right after the send. **Never** use Telegram's own file URL
  (`api.telegram.org/file/bot<TOKEN>/…`): it embeds the bot token, and handing it to a third
  party gives them control of the bot.
- Some corporate networks' DNS don't resolve `*.trycloudflare.com`. `cs` verifies the link
  through public DNS (DoH 1.1.1.1), which is what Clicksign uses, so this doesn't block.
- Quick tunnels come with no uptime guarantee and suit a prototype. For production, use a
  bucket (`s3`/`gcs`) or a Clicksign MCP tool that takes the file's content.
- GCS signed URLs need service-account credentials (user ADC can't sign), and
  `uv sync --extra gcs`.
- Never create buckets, keys or cloud credentials on your own, and never write secrets
  anywhere except `.env` (gitignored, mode 600).
- `CS_DRY_RUN=true` lets the whole journey run up to the summary, with a simulated send. Use it
  for demos and tests without notifying anyone.

## Quality bar

- The user sees at most one configuration topic per message, in plain pt-BR.
- Exit with `bin/cs doctor` returning 0 (or 1 with only the dry-run warning, when that is
  intended).
