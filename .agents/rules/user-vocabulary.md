# User vocabulary ("zero learning")

The persona must not need to learn Clicksign concepts. In everything the user reads:

| Never say | Say instead |
| --- | --- |
| envelope | "documento", "envio" |
| signer / signatário (as a technical term) | "quem assina", or the person's name |
| requirement, qualificação, `agree`, `role` | "como a pessoa participa" / the role label (contratante, testemunha…) |
| auth, autenticação, `provide_evidence`, token | "confirmação de identidade", or "código por e-mail" |
| group, ordem de grupo | "assina primeiro / depois" |
| run, run_id, hash, payload, JSON, envelope_id, account_key | (don't mention them) |
| draft, status `running`/`closed` | "aguardando assinatura", "assinado por todos" |

- Never paste MCP JSON, tool names, error stacks or field names. Translate errors into what the
  user can do ("o e-mail da Maria parece ter um erro de digitação — confere?").
- Technical detail only when the user explicitly asks for it.
- Role labels come from `bin/cs` / `.agents/knowledge/roles-glossary.md`; don't invent new ones.
