# How someone participates (role) — pt-BR ↔ API

Source of truth in code: `src/cs/glossary.py` (`bin/cs glossary role "<termo>"`). Derived from the
Clicksign MCP signer guide (`clicksign_read_signer_guide`, PT→EN glossary section).

| In the document | `role` | Label shown in the summary |
| --- | --- | --- |
| Contratante | `contractor` | contratante |
| Contratado(a) | `contractee` | contratado(a) |
| Prestador(a) de serviço | `service_provider` | prestador(a) de serviço |
| Locador(a) | `lessor` | locador(a) |
| Locatário(a) | `lessee` | locatário(a) |
| Comprador(a) / Vendedor(a) | `buyer` / `seller` | comprador(a) / vendedor(a) |
| Fiador(a) | `guarantor` | fiador(a) |
| Testemunha | `witness` | testemunha |
| Outorgante / Outorgado(a) | `grantor` / `grantee` | outorgante / outorgado(a) |
| Representante legal | `legal_representative` | representante legal |
| Sócio(a) | `partner` | sócio(a) |
| Aprovador(a) (approves, doesn't sign) | `approve` | aprova |
| Generic / unclear ("parte", "assinante") | `sign` | assina |

Ambiguous on purpose: "parte" (`party` vs `sign`). Use `sign` and don't ask; the persona doesn't
care about this distinction.
