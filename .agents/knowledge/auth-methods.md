# Identity confirmation methods (Clicksign)

From the MCP signer guide: `provide_evidence` + `auth`.

| `auth` | User-facing | Needs | MVP |
| --- | --- | --- | --- |
| `email` | código por e-mail | email | ✅ default |
| `sms` | código por SMS | phone (10–11 digits) | ✅ |
| `whatsapp` | código por WhatsApp | phone (10–11 digits) | ✅ |
| `selfie` | selfie | — | ❌ (pending product decision) |
| `official_document` | foto de documento oficial | — | ❌ |
| `liveness` | prova de vida | — | ❌ |
| `address_proof` | comprovante de endereço | — | ❌ |
| `icp_brasil` | certificado digital ICP-Brasil | — | ❌ |
| `pix` | Pix | — | ❌ |
| `presential` | — | rejected by the API | never |

Enable methods via `CS_ALLOWED_AUTHS` in `.env` after the product decision (open point in
JTBD §8). The extra fields some methods need still have to be confirmed in a spike.
