---
name: sign-review-summary
description: The single reviewable summary before sending (node 5) — document, who signs, identity confirmation and message on one screen ending with "Posso enviar?", plus natural-language edits that return to the right node and reconverge on the summary in the same turn (E2, E4, E6, E7). Use whenever a send is ready for review or the user changes anything during review.
metadata:
  category: sign
---

# Summary and review

## The summary

Always produced by `bin/cs review show RUN`, never hand-written, so its content and the
`hash` that authorizes the send can't drift apart. Shape:

```
📄 Contrato de consultoria — ACME (contrato-consultoria-acme.pdf, 4 páginas)

Quem vai assinar:
  1. Maria Souza Andrade (maria.souza@example.com) — contratante, pela ACME Comercio Ltda
  2. Joao Pedro Lima (joao.lima@example.com) — contratado(a), pela Lima Consultoria ME

Confirmação de identidade: código por e-mail
Mensagem: "Olá! Segue o contrato de consultoria de marketing digital…"

ℹ️ O documento tem espaço para 2 testemunhas — se quiser incluir alguém, é só me dizer.

Posso enviar? (ou me diga o que mudar)
```

- Copy it **verbatim** into the reply. One line before it is fine when something needs context
  ("Achei 2 pessoas no contrato:"). Don't explain each item.
- "⚠ confira" marks a low-confidence line (E12). Don't remove it.
- Exit code 1 means blocked. The summary ends with "Antes de enviar, preciso resolver:"; ask
  for the missing pieces in one question.

## Edits during review (one turn, no new screens)

| User says | Patch | Notes |
| --- | --- | --- |
| "troca/corrige o e-mail do X" | `signers[i].email`, `source: "user"` | E2/E7 |
| "inclui/tira o Y" | `signers` | E2 |
| "o X assina primeiro/depois" | `group` | ordering, E2 |
| "usa WhatsApp/SMS" | `auth` (+ phone) | E3, see `sign-auth-policy` |
| "muda a mensagem para…" | `message` | E6 |
| "o título é…" | `envelope_name` | E6 |
| "mandei o arquivo errado" | `bin/cs run replace-doc` | E8 |
| "muda o prazo / lembrete" | not supported yet | say so in one sentence and keep the summary |

After any patch: `bin/cs review show RUN` again, **in the same reply**. Each patch after a
summary counts as an edit automatically (metric `edits`).

## What counts as approval

Clear consent to send this summary: "pode enviar", "manda", "envia", "ok", "sim", "isso",
"perfeito, pode mandar", 👍. Not approval: questions, "acho que sim, mas…", or approval plus a
change (that's an edit, so show the summary again). When it's ambiguous, ask "Posso enviar?"
once more. Never send on doubt.
