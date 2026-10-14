# send-for-signature — journey orchestration

The conversational journey for the Pontual persona, nodes 1→6 of `JTBD_Persona_Pontual.md`.
This file owns **order, state transitions and failure handling**. The rules for each node live
in the skills it points to: read a skill in full the first time its node comes up in the
session.

**Every user turn that needs tools starts with an acknowledgement**, one short line written
before the first tool call (`.agents/rules/conversation.md`). The "Ack" markers below show
where. After the acknowledgement, the rest of the turn produces exactly one more message: the
result (summary, question or confirmation).

All `bin/cs` calls run from the repo root. The journey state (`runs/<run_id>/journey-state.json`)
is the memory: when in doubt about where you are, run `bin/cs run get RUN`.

## 0. Silent pre-check (once per session, before the first journey action)

1. `bin/cs doctor --json`. An `error` in `clicksign-account` or `python-deps` means the setup
   is incomplete: switch to `/setup` (`.agents/commands/setup.md`) instead of reading any
   document (E15). An `upload-bucket` error **without** dry run means sending is impossible:
   tell the user in one sentence and offer to continue up to the summary.
2. Call MCP `clicksign_select_account` with `CLICKSIGN_ACCOUNT_KEY` from `.env`. On an auth
   error, ask the user to reauthenticate the Clicksign MCP (in pi: `/mcp` → login `clicksign`)
   and stop.
3. `bin/cs run list --open --max-age-days 7`. If there is an unfinished journey **and** the user
   didn't just attach a new file, offer to resume it (E14): "Você tinha um envio do *<nome>* pela
   metade. Quer continuar?". If they attached a new file, start a new journey and leave the old
   one alone. If a journey is in dispatch status `ready`/`ambiguous`, resolve it first
   (dispatch-safety rule 4) before any new send.

Don't tell the user about the pre-check when it passes.

## 1. Intake (skill `sign-document-intake`)

**Ack:** "Recebi o <tipo/nome do documento> 👍 Já estou vendo quem precisa assinar." (Derive
the type from the filename. Don't wait to read it.) Then the session pre-check, if it hasn't
run yet, and `bin/cs run new <file>` → keep `run_id`. Branch on `node`:

| `node` | Next |
| --- | --- |
| `read` | → 2 |
| `ask_signers` | file can be sent but not read (scan/image/.doc) → 3B |
| `ask_new_file` | cannot be sent (password, corrupt, format, >20 MB) → tell why and ask for another file (E9) |

If the user's message also carries instructions ("manda pra Maria, maria@x.com", "é um NDA com
a ACME"), treat them as **input with priority over extraction**: they fill or override what the
document says (`source: "user"`).

A new file sent during an open journey for the *same* deal ("ops, mandei a versão errada")
→ `bin/cs run replace-doc RUN <file>` (E8; signers are preserved). An unrelated new file → a
new journey.

## 2 → 3A/3B. Who signs (skill `sign-party-extraction`)

Read the text (`bin/cs run get RUN --text`, or the read tool on `document.text_path`). Long
document (> ~60k chars) → read the parts and preamble first, then search for signature blocks
and witness lines. Build the `signers` array per the skill and save it:
`bin/cs run patch RUN '{"signers":[...], "mentioned_non_signers":[...], "envelope_name":"...", "node":"signers"}'`.

- All signers complete → **don't stop here**: go straight to 4 → 5 in the same turn (3A is
  shown *as* the summary).
- Nobody identifiable (E1) or data missing (E5) → `node: "ask_signers"`, and ask **one**
  question (see the skill), then `bin/cs run metric RUN question`. When the answer arrives,
  patch the signers with `source: "user"` and continue to 4.

## 4. Authentication (skill `sign-auth-policy`)

Set `auth` for each signer (default `email`) inside the same patch. No question to the user.

When the user answers a question (who signs / a missing email), **Ack** briefly ("Anotado!
Já atualizo o resumo.") before patching, unless the reply is instant.

## 5. Summary (skills `write-signer-message` + `sign-review-summary`)

1. Write the signer message per `write-signer-message` and patch `message`.
2. `bin/cs review show RUN` → copy the summary text **verbatim** into your reply and keep
   `hash=H` to yourself.
   - Exit 1 (`bloqueios>0`): the summary lists what's missing. Ask for it in **one** question;
     that's a 3B/E5 case.
3. User reply:
   - Approval ("pode enviar", "manda", "ok", "sim, envia", 👍) → 6.
   - Change ("troca o e-mail da Maria", "o João assina depois", "usa WhatsApp para a Ana",
     "muda a mensagem", "o título é Contrato ACME") → patch, then `bin/cs review show RUN` again
     **in the same turn** (E2/E4/E6/E7). The patch automatically invalidates the previous
     confirmation.
   - Question or doubt → answer it, then repeat "Posso enviar?".
   - Give up ("deixa pra lá", "cancela") → `bin/cs run abandon RUN`, and confirm in one
     sentence that nothing was sent.

## 6. Send (skill `sign-dispatch`)

**Ack:** "Enviando agora…" (or "Combinado, enviando para a Rayssa…"). Then:

1. `bin/cs dispatch prepare RUN --hash H`. If it refuses, follow its message (stale summary
   → show it again; pending attempt → E13).
2. If `dry_run: true` → don't call the MCP: `bin/cs dispatch record RUN --envelope-id dry-run`,
   and tell the user it was a simulation.
3. Otherwise call MCP `clicksign_create_envelope_with_file_url` with **exactly** `args`.
4. Record the outcome per `dispatch-safety.md` rule 3.
5. Verify and complete: `clicksign_get_envelope_details` (status, deadline) →
   `bin/cs dispatch record RUN --envelope-id ID --status S --deadline D`.
6. Confirm to the user (format in the skill), then `bin/cs run scrub RUN`.

## Failure handling

| Failure | Action |
| --- | --- |
| `bin/cs` exits 2 | Read the stderr message (pt-BR), fix the call, and don't show it raw to the user |
| MCP auth error | Ask the user to reauthenticate the Clicksign MCP; the state is preserved |
| MCP validation error on create | `dispatch fail` (not ambiguous), translate it into a correction, show the summary again |
| Timeout/5xx on create | `dispatch fail --ambiguous` → E13 check → record or resolve |
| Create returns `status: "queued"` / `confirmed: false` | progress message to the user ("A Clicksign está levando um pouco mais que o normal, já confiro."), `dispatch fail --ambiguous`, then the E13 check from `sign-dispatch` (wait, then search) |
| Upload fails | Nothing was sent; say it in one sentence and offer to try again |

## Idempotency

The `run_id` + dispatch status make retries safe: `prepare` refuses while a previous attempt is
unresolved, and patches are refused after `sent`. Re-running any step before 6 just overwrites
state.
