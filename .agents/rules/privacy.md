# Privacy

Documents carry personal data (names, CPF, addresses, prices, terms of the deal).

- Document text lives only in `runs/<run_id>/document.txt` (gitignored). Never copy it into
  other files, commit messages, memories or logs. Quote only the minimal snippet needed as
  `evidence`.
- Don't show CPF, RG, birth date or address in the summary or the conversation unless the user
  asks for them. They stay in the document (E11).
- After a confirmed send: `bin/cs run scrub RUN` removes the extracted text and the local copy.
  The state file stays, holding only the data needed to track the send. `bin/cs run prune` cleans
  up old journeys.
- Upload bridge (default `tunnel`): the file is served from this machine only through a random
  link, for ≤ 10 min and ≤ 3 downloads. `dispatch record`/`fail` close it. The link never goes
  to the user or into any file other than `runs/<id>/dispatch-args.json` (deleted by `scrub`).
- Never pass Telegram file URLs (`api.telegram.org/file/bot…`) anywhere: they contain the bot
  token.
- Telegram: the bridge's temp copy (`~/.pi/agent/tmp/telegram/`) is deleted by `scrub`. Bot
  chats are not end-to-end encrypted, so the document also lives on Telegram's servers.
  That's acceptable for the prototype and an open item for production.
- Test fixtures use synthetic people and `@example.com` addresses only.
