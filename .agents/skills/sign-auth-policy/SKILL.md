---
name: sign-auth-policy
description: Chooses how each signer confirms their identity (node 4) — email code by default, silently, deviating only when the document or the user gives a reason; handles the user asking to change it (E3) and qualification data present in the document (E11). Use when building or editing the signer list.
metadata:
  category: sign
---

# Identity confirmation (authentication)

The persona "accepts the default authentication without deciding anything". It shows up as
**one line in the summary**, never as a question.

## Default

`auth: "email"` (email token) for every signer. Requires `email`.

## Silent deviations (no question)

| Situation | `auth` |
| --- | --- |
| Signer has a phone but no email (document or user) | `whatsapp` (if the user said SMS, `sms`) |
| User asked: "por WhatsApp / por SMS" | `whatsapp` / `sms` for the signers they named (all, if unspecified) |

## Methods available in this MVP

Controlled by `CS_ALLOWED_AUTHS` (default `email,sms,whatsapp`). Clicksign also supports
`selfie`, `official_document`, `liveness`, `address_proof`, `icp_brasil` and `pix` (see
`.agents/knowledge/auth-methods.md`). If the user asks for one of these and it isn't enabled,
say it isn't available in this assistant yet and keep the current one. Never fail silently.
`presential` doesn't exist in the API.

## E3 — user wants to change it

"Quero que confirmem por WhatsApp" → set `auth`, ask for phones if missing (one question),
then show the summary again. The options offered, in plain words: "código por e-mail, SMS ou
WhatsApp".

## E11 — qualification data in the document

CPF, RG and address commonly appear in the parties block. In this MVP they are **not** sent
as signer data and **not** shown in the summary. The signer sees the document itself. Mention
them only if the user asks for stronger verification (and then see "available methods").
