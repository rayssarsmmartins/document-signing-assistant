# Dispatch safety

`clicksign_create_envelope_with_file_url` **creates and sends in one call**: Clicksign has no
reviewable draft, and an email reaches the persona's client immediately. The summary you show is
the only gate, so these rules have no exceptions.

1. **Explicit confirmation of the exact summary.** Call the send tool only after:
   `bin/cs review show RUN` printed a summary with `hash=H` → the user's **next** message
   clearly approves it ("pode enviar", "manda", "ok, envia", "sim") → `bin/cs dispatch prepare
   RUN --hash H` succeeded. Any edit invalidates the confirmation, so show the summary again.
   An approval followed by a change request ("pode enviar, mas troca o e-mail") is an edit, not
   an approval.
2. **Send exactly the args `prepare` printed**, unchanged. Never build the payload by hand.
3. **One send per journey.** Right after the MCP call, record the outcome:
   - success → `bin/cs dispatch record RUN --envelope-id ID`;
   - validation error (4xx, the MCP rejected the payload, nothing was created) →
     `bin/cs dispatch fail RUN --error "..."`, fix it, show the summary again;
   - timeout, 5xx, dropped connection, or any doubt → `bin/cs dispatch fail RUN --error "..."
     --ambiguous`.
4. **Never retry blindly.** With `ambiguous` (or `ready` left over from a crashed session), first
   check in Clicksign whether the document was created (§E13 in
   `.agents/skills/sign-dispatch/SKILL.md`). Then `record` it if it was created, or
   `resolve --not-created` if it wasn't. Only then may you prepare again.
5. **Right account.** Every journey runs after `clicksign_select_account` with
   `CLICKSIGN_ACCOUNT_KEY` from `.env`. If that fails, stop; never send from whichever account
   the session happens to be in.
6. **Silent test mode.** With `CS_SILENT_SEND=true`, the envelope is real but nobody is
   notified. Say so explicitly in the confirmation.
7. **Dry run.** With `CS_DRY_RUN=true`, `prepare` says so. In that case **do not call the MCP**:
   record with `--envelope-id dry-run` and tell the user it was a simulation.
8. Never use `clicksign_quick_send_envelope`.
