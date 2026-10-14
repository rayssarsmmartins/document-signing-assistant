---
name: track-envelope-status
description: Answers questions about documents already sent — "já assinaram?", status of a specific document, the list of everything pending in the account — and sends reminders to pending signers on request. Use when the user asks about a sent document or about pending signatures, wants to nudge someone, or comes back after a send.
metadata:
  category: track
---

# After the send

Every turn here calls Clicksign, so **Ack** first ("Vou conferir na Clicksign."), then call
the tools (`.agents/rules/conversation.md`).

## Finding the document

1. Sent by this assistant: `bin/cs run list` → journeys with `dispatch: sent` (each has
   `envelope_id` in `bin/cs run get RUN`). Match by document name or people.
2. Otherwise (sent outside the assistant, or the journey was pruned): `clicksign_list_envelopes`
   with `status: "running"` (or no status filter), `sort: "-created"`, and `page_size: 20`.
   Match by name. **Clicksign may append " (1)", " (5)"… to duplicate names**, so match by
   prefix.
3. More than one candidate → ask which one in one line ("O contrato da ACME ou o NDA da
   Lima?"). Distinguish the candidates by recipient and date, not by ids.

## Status of one document

`clicksign_list_envelope_signers` returns `signed` (with `signed_at`) / `pending` / `refused`
for each person, plus a `summary`. Answer in one or two lines:

- "A Maria já assinou (hoje, 10h44). Falta o João."
- "Todos assinaram ✅ — o documento está concluído." (envelope `closed`)
- "O João recusou a assinatura." Then offer the next step in plain words.
- `status_available=false` → "não consegui ver quem já assinou agora".

Times are in the user's timezone (America/Sao_Paulo); `signed_at` already carries the offset.
The deadline is not available from the MCP, so don't promise a date. When the journey state is
stale, update it with `bin/cs dispatch record RUN --envelope-id ID --status <status>`.

## Pending list (whole account)

"Quais documentos estão pendentes?" → `clicksign_list_envelopes` with `status: "running"`,
`sort: "-created"`, `page_size: 20`, then `clicksign_list_envelope_signers` for each one
(in parallel). Reply with a **numbered list**, newest first, one line per document:

`N. <nome> — falta <quem> (<contexto curto: enviado hoje / lembrete enviado hoje / e-mail parece fictício>)`

- Mark internal tests honestly ("teste interno, ninguém para assinar").
- Envelope still `running` but every signer `signed`: say "todas as assinaturas feitas, mas o
  documento ainda não aparece como concluído na Clicksign". Don't guess why.
- More than 20 → show 20 and say how many remain.
- End by offering the next step ("Quer que eu mande lembrete para algum deles?"). Remember the
  numbering in this conversation, because "item 4" refers to it.

## Reminder

Only when the user asks ("cobra o João", "lembrete do item 4", "manda um lembrete").

- One person: `clicksign_send_signer_reminder` with `envelope_id`, `signer_id` **and**
  `signer_email`, both taken from `clicksign_list_envelope_signers`.
- Everyone pending: `clicksign_send_envelope_reminders`.
- Facts to respect (MCP docs + tests):
  - Reminders go **by email only**, even if the original request went by WhatsApp/SMS.
  - Rate limit: 1 per minute per document/person. The response's `next_send_available_at` is in
    UTC, so convert it to local time before telling the user.
  - `notified: true` means Clicksign accepted the reminder, not that it was delivered. Say "a
    Clicksign vai mandar por e-mail para…".
  - The envelope must be `running`. The MCP returns an error for closed ones; translate it ("esse
    documento já foi concluído").
- Confirm in one line, naming the document, the person and the email. Don't send reminders
  proactively.
- From a voice note: a reminder sends an email to someone, so when the transcription is unclear,
  confirm in text first (`.agents/rules/conversation.md` § Voice).
