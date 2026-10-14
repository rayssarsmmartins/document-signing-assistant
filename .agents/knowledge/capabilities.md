# Capabilities map — what the user can ask, and how to serve it

Agent-facing source of truth for "what can this assistant do?". The user-facing version is
`docs/howto-conversas.md`. Keep both in sync: when a status changes here, change it there.

Status: **ready** (skills + tools in place) · **experimental** (works, with known rough edges) ·
**planned** (MCP supports it, the workspace doesn't yet: say so, don't improvise) · **blocked**
(the MCP can't do it).

| Intent (user words) | Status | How to serve it |
| --- | --- | --- |
| Send a document for signature (attaches a file) | ready | `.agents/commands/send-for-signature.md` |
| Say who signs / answer the missing-data question | ready | `sign-party-extraction` (`source: "user"`) |
| Edit before sending (email, person, message, title) | ready | `sign-review-summary` |
| Change the identity confirmation (email/SMS/WhatsApp) | ready | `sign-auth-policy` |
| Replace the file | ready | `bin/cs run replace-doc` (`sign-document-intake` E8) |
| Give up before sending | ready | `bin/cs run abandon` |
| Resume an unfinished send | ready | pre-check, `bin/cs run list --open` |
| "Já assinaram?" / status of a specific document | ready | `track-envelope-status` |
| List what is pending (whole account) | ready | `track-envelope-status` § Pending list |
| Reminder to one person / to everyone pending | ready | `track-envelope-status` § Reminder |
| Voice message (`voice-*.ogg`) | experimental | transcribe (§ Voice below), then route the text like any message. Rules in `.agents/rules/conversation.md` § Voice notes |
| "O que você consegue fazer?" | ready | answer from the quick-summary table of `docs/howto-conversas.md`, in chat format (short list, no table) |
| Get the signed PDF back in the chat | planned | MCP: `clicksign_list_envelope_documents` → `links.files.signed` (S3 URL valid ~5 min). Not wired yet (needs a download plus `telegram_attach`). Tell the user it's coming, and that the signed file is on the Clicksign platform or was emailed to signers |
| Send from an account template ("modelo") | planned | MCP: `clicksign_list_templates`, `clicksign_get_template_fields`, `clicksign_create_envelope_with_template` (.docx only). Not wired: no skill, no summary/hash lock. **Do not** call the template create tool ad hoc; it bypasses `dispatch-safety` |
| Cancel / edit a sent envelope | blocked | no MCP tool. Point the user to the Clicksign platform |
| Set a deadline / read the deadline | blocked | not exposed by the MCP (F0) |
| Signing order | blocked | `group` is accepted but ignored (F0) |
| Several files in one envelope | blocked (by design) | one document per send (JTBD) |
| Observer (CC) | blocked | out of scope for this persona |
| Switch Clicksign account | blocked (by design) | fixed in `.env`. Only via `/setup` by the operator |

## Voice (experimental)

The Telegram bridge saves voice notes as `~/.pi/agent/tmp/telegram/<ts>-voice-<n>.ogg`.
Transcribe locally (no audio leaves the machine):

```bash
uv run --quiet --with faster-whisper python - "$FILE" <<'EOF'
import sys
from faster_whisper import WhisperModel
m = WhisperModel("small", device="cpu", compute_type="int8")
segs, info = m.transcribe(sys.argv[1], language="pt", vad_filter=True, beam_size=5)
print(" ".join(s.text.strip() for s in segs))
EOF
```

The first run downloads the model (~500 MB); afterwards a few seconds per note. Known issues
from the 2026-10-09 tests:
- Very short notes (< 3 s) or noisy ones produce garbage: "Gostaria? Vata!", "e vai para cima".
- Brand names get mangled ("BYD" → "BioID"). Match them against known document names before
  answering.

To be promoted to `cs voice transcribe` (planned). Delete the `.ogg` after transcribing
(privacy).
