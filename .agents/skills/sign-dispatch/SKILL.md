---
name: sign-dispatch
description: Sends the document for signature through the Clicksign MCP (node 6) — upload to the private bucket, create-and-send call with the exact prepared payload, verification of status and deadline, success confirmation in pt-BR, and safe recovery from errors or uncertain outcomes (E13). Use only after the user approved the current summary.
metadata:
  category: sign
---

# Send

Sending is irreversible. `.agents/rules/dispatch-safety.md` applies in full.

## Sequence

1. `bin/cs dispatch prepare RUN --hash H` → JSON with `tool`, `args`, `dry_run`,
   `url_expires_at`. With the default `tunnel` bridge, this opens a temporary public link to the
   file (about 10 s), verified before returning. It stays open for 10 min and 3 downloads at
   most. Call the MCP **right away**: no message to the user in between, and no other tool
   call.
2. `dry_run: true` → no MCP call. `bin/cs dispatch record RUN --envelope-id dry-run`, then tell
   the user: "Simulação concluída — nada foi enviado de verdade (modo de teste)."
3. `clicksign_create_envelope_with_file_url` with `args` exactly as printed.
4. Read the response (format validated in F0): `{success, confirmed, envelope_id,
   envelope: {attributes: {status}}, elapsed_seconds, job_id}`. Creation is async (a job),
   and the MCP waits for confirmation, which took ~4 s in F0.
   - `success: true` + `confirmed: true` + `envelope_id` →
     `bin/cs dispatch record RUN --envelope-id <envelope_id> --status <status>` (status
     `running` = waiting for signatures).
   - `success: true` with `confirmed: false` / `status: "queued"` (observed on 2026-10-09: the
     job went into a Sidekiq retry, no `envelope_id`, and a `retry_hint` with a
     `list_envelopes` filter) → treat it as **ambiguous** (`fail --ambiguous`). **Tell the user
     right away** that it's taking longer ("A Clicksign está levando um pouco mais que o normal,
     já confiro e te aviso."), then run E13. **Never call create again.** The job is still
     queued and will run; a second create sends a duplicate.
   - error → per the Errors table.
5. Optional sanity check: `clicksign_list_envelope_signers` returns the same people, all
   `pending`.
6. `bin/cs run scrub RUN`.

**Deadline:** the MCP doesn't expose the envelope's deadline (`get_envelope_details` returns
only name and status, as of F0). Don't promise a date. Say the deadline started counting,
without one, and don't call `get_envelope_details` just for this.

**Signing order:** the MCP accepts `group` but **ignores it** (F0: everyone ended up in group 1).
`CLICKSIGN_SEND_GROUP` stays `false`, and the summary already warns that everyone receives it
at the same time.

## Confirmation to the user (node 6)

```
✅ Enviado! Maria Souza Andrade e Joao Pedro Lima já receberam o pedido de assinatura por e-mail,
e o prazo para assinar começou a contar. Quando quiser saber se já assinaram, é só me perguntar.
```

- Name the people (or "as 3 pessoas" when there are more than 3) and say how they were notified
  (e-mail/WhatsApp/SMS). Give a deadline date only if a reliable source exists (today, none
  does).
- `CS_SILENT_SEND=true` (test mode): say "Envio de teste criado — os signatários **não** foram
  notificados." instead.
- No ids, links to the API, or JSON.

## Errors

| Error | Meaning | Action |
| --- | --- | --- |
| validation (name, email, phone, role, auth, filename) | nothing created | `fail` (not ambiguous). Translate it into a fix, ask or correct, show the summary again |
| `SSRF bloqueado`, `scheme nao e permitido`, download failure, link expired | bridge problem, nothing created | `fail` (it closes the tunnel). Run `bin/cs doctor`, then tell the user it's a temporary problem on our side. A new `prepare` opens a fresh link |
| `prepare` fails with "túnel não ficou pronto" / "URL pública não respondeu" | Cloudflare quick tunnel unavailable, nothing created | retry `prepare` once. If it still fails, say "não consegui preparar o envio agora, tento de novo em instantes?" |
| auth/OAuth | not executed | `fail`. Ask the user to reauthenticate, keep the state, and offer to retry after |
| timeout, 5xx, connection dropped, any doubt | **maybe created** | `fail --ambiguous` → E13 |

## E13 — checking whether it was created

1. `clicksign_list_envelopes` with `created_from` = `dispatch.prepared_at` minus 2 min,
   `created_to` = now plus 5 min (UTC, ISO 8601; **both are required together**), and
   `sort: "-created"`. **Don't filter by `name`.** Clicksign renames duplicates (observed on
   2026-10-09: "Contrato … BYD Dolphin" was created as "Contrato … BYD Dolphin (1)"), so an
   exact-name filter, including the MCP's own `retry_hint`, misses it. Candidates are envelopes
   whose name **starts with** `envelope_name`. Confirm each with
   `clicksign_list_envelope_signers` that the emails match the journey's signers.
   - Queued case: if nothing shows up, wait about 60 s (the retry slot) and search once more,
     then about 2 min more for a last search. On a real send, the envelope showed up about 30 s
     after `enqueued_at`.
2. Found → `bin/cs dispatch record RUN --envelope-id ID`, then confirm normally. If the
   name got a suffix "(1)", mention it in one line ("na Clicksign ele aparece como '… (1)'
   porque já havia um envio com o mesmo nome").
3. Still not found after the last search → `bin/cs dispatch resolve RUN --not-created`, show the summary again and ask
   "Posso tentar enviar de novo?". The persona's earlier approval doesn't carry over to a new
   attempt.
4. Tell the user only what matters: "Tive uma instabilidade ao enviar. Já conferi: [foi enviado
   / não foi enviado]."
