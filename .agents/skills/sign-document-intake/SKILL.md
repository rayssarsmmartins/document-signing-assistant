---
name: sign-document-intake
description: Receives the document the persona wants signed (node 1) — validates format, size, password protection and readability, and decides whether to read it, ask who signs, or ask for another file. Use whenever the user attaches or points to a file, or replaces the file of an ongoing send.
metadata:
  category: sign
---

# Document intake

## Input

Exactly one document per journey. Accepted by Clicksign: PDF, Word (.docx/.doc), JPG/PNG
images, TXT, up to 20 MB. The file arrives as a local path (in the terminal, a pasted path or a
dragged file; via Telegram, the temp path the bridge provides). Free text in the same message
counts as instructions.

`bin/cs run new <file>` copies the file into the journey, hashes it, extracts the text and
classifies it:

| `status` | Meaning | Next node | What the user hears |
| --- | --- | --- | --- |
| `ok` | readable | `read` | only the acknowledgement ("Recebi o contrato…"), then the summary or the question |
| `no_text` | scan or image, no selectable text | `ask_signers` | nothing about the scan. Just the who-signs question (it can still be sent) |
| `unreadable_format` | old `.doc` | `ask_signers` | same as above |
| `encrypted` | password-protected PDF | `ask_new_file` | "Esse PDF está protegido por senha. Consegue me mandar uma versão sem senha?" |
| `corrupt` | won't open | `ask_new_file` | "Não consegui abrir esse arquivo. Pode mandar de novo?" |
| `unsupported_format` | e.g. .xlsx, .zip | `ask_new_file` | "Esse formato não dá para enviar para assinatura. Consegue mandar em PDF ou Word?" |
| `too_large` | > 20 MB | `ask_new_file` | "O arquivo passou de 20 MB. Consegue mandar uma versão menor (ex.: PDF comprimido)?" |

**E9 decision rule:** if Clicksign can send it, we never block the persona. An unreadable but
sendable file goes to "who signs?" (3B). Only an unsendable file asks for another file.

## Arriving via Telegram

- `origin: "telegram"`: the bridge already downloaded the file, and the timestamp prefix in the
  name was removed. After the send, `bin/cs run scrub` also deletes the bridge's temp copy.
- `compressed_photo: true`: the user sent the document **as a photo**, which Telegram
  compresses. If it looks like a page of a contract (it usually does), say in one sentence:
  "Chegou como foto, que o Telegram comprime. Se tiver o PDF, me manda como arquivo (📎 →
  Arquivo). Se a foto é o documento mesmo, sigo com ela." Count it as the turn's one question.
  If the user confirms the photo, or sends nothing better, continue with it (it's sendable).
- Telegram bots can download files up to 20 MB, the same as Clicksign's limit. A larger file
  never reaches us, so the bridge reports the error.

## Replacing the document (E8)

- "mandei errado / segue a versão final / atualizei o contrato" with an open journey →
  `bin/cs run replace-doc RUN <file>`. Signers already confirmed or edited by the user are
  **preserved** (current hypothesis, to be validated). Re-read the new text and only **add**
  signers that appear now, or flag in the summary one that disappeared from the document.
- Use `--reset-signers` only when the user says it's a different document or deal.
- A replacement after the send is impossible: say it was already sent and offer a new send.

## Multiple files in one message

One document per send (JTBD). Say so in one sentence and ask which one goes first. Never merge
files.
