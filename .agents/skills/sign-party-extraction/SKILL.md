---
name: sign-party-extraction
description: Identifies who must sign a document (nodes 2→3A/3B) — names, emails/phones, how each person participates (contratante, locatário, testemunha…) and signing order, each backed by a quoted evidence snippet; asks a single question when parties or contact data are missing. Use after a document is read, when the user answers who signs, or when they edit the signer list.
metadata:
  category: sign
---

# Who signs

Goal: a signer list the persona can **accept without editing** — and that is never confidently
wrong (E12).

## Output contract

Each item of `signers` (schema `src/cs/schemas/journey-state.schema.json`, `$defs.signer`):

| Field | Rule |
| --- | --- |
| `name` | Full name as written in the document (first and last name, no digits). For a company party, the **natural person who signs for it** (representative, partner, director). If only the company is named, the signer is unknown: treat it as missing data |
| `email` | Only if it appears **in the document** (`email_evidence` = the snippet) or the **user said it** (`source: "user"`). **Never infer** (`maria@acme.com.br` from "Maria, ACME" is forbidden) |
| `phone` | Digits only, with area code (10–11). Same evidence rule |
| `role` | Canonical role: `bin/cs glossary role "<termo>"` maps pt-BR → API. Unknown or ambiguous ("parte") → `sign` |
| `auth` | Leave it to `sign-auth-policy` (default `email`) |
| `group` | Signing order: 1 = first. Same number = in parallel. Only when the document or the user states an order |
| `source` | `extracted` (from the document) or `user` |
| `confidence` | `high` (name + role explicit in the qualification block or signature block), `medium` (inferred from context), `low` (guess; the summary will flag "⚠ confira") |
| `evidence` | Short snippet (≤ 120 chars) that shows this person signs. Never more than needed (privacy) |
| `represents` | The company (or person) this signer signs for, if any ("ACME Comércio Ltda"). Shown in the summary as "— contratante, pela ACME Comércio Ltda" |

Also fill in `mentioned_non_signers` (E10) and `envelope_name`: a short title in the persona's
words ("Contrato de prestação de serviços — ACME"), never the raw filename when a better title
is evident.

## How to find signers

1. **Parties block** (qualificação, usually the preamble): "CONTRATANTE: …", "LOCADOR(A): …",
   "de um lado … de outro lado …".
2. **Signature block** at the end: lines with names under "_____", "Testemunhas: 1. … 2. …".
3. Contact details: e-mails/phones near the qualification or in a "Notificações"/"Comunicações"
   clause.
4. The persona themself often is a party (e.g. the consultant who is "CONTRATADA"). Include
   them: they also sign.

## Who is *not* a signer (E10)

People and companies merely cited (a previous owner, a referenced third party, a lawyer cited
for notifications) go to `mentioned_non_signers` with a short `reason`, and the summary lists them
in one line. A company that **is** a party and has a named representative is not "mentioned":
it goes in that signer's `represents`. Witnesses **are** signers (role
`witness`) when the signature block has witness lines with names. Empty witness lines →
add a `summary_notes` line ("O documento tem espaço para 2 testemunhas — se quiser incluir
alguém, é só me dizer."). That's information in the summary, not a question, and it doesn't
block the send. `summary_notes` holds at most 3 short lines and is reserved for things the
persona would regret not knowing.

## Signing order

Set `group` only on explicit evidence: "assinará após", "a ser assinado primeiro por…", or a
user instruction ("a Maria assina depois"). Otherwise everyone gets `group: 1`. The tool tells
you (as a summary warning) when order can't be honored yet.

## When something is missing — one question (3B / E1 / E5)

- **Nobody identifiable** (E1, or an unreadable document): "Quem precisa assinar? Pode me
  mandar nome e e-mail de cada pessoa."
- **Names found, contact missing** (E5): ask **only** for the missing data, grouped together:
  "Faltou o e-mail do João Pedro Lima e da Ana Rocha — pode me passar?". Don't re-list the
  people who are already complete.
- **Company without a person**: "Quem assina pela ACME Ltda? Nome e e-mail."
- Parse the answer generously ("joão: joao@x.com, a ana é ana@y.com.br"). Anything the user
  provides gets `source: "user"`. If the answer is still incomplete, ask only for what remains.
- If the answer arrives and everything is complete → continue to the summary in the same turn.

## Edits (E2 / E7)

Apply natural-language edits directly: "tira a testemunha", "troca o e-mail da Maria para…",
"o João assina por último", "inclui o Pedro, pedro@x.com, como testemunha". Then show the
summary again in the same turn (orchestrator). Never ask "tem certeza?" for an edit. The
summary is the confirmation.

## Quality bar

- An email or phone with no `email_evidence`/user source never exists. `bin/cs` blocks it
  anyway.
- Two parties on opposite sides of a contract are never merged. Homonyms keep both entries.
- `low` confidence is used honestly. A misread with high confidence is the worst failure mode
  of this persona (blind acceptance).
