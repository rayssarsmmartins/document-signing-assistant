# Spike F0 — validação do MCP da Clicksign (2026-10-08)

Conta: Rayssa Raphaely Souza de Medeiros Martins (`2b738bd7-…`), conta de teste com uso
autorizado. Envelope de teste: `9b42a7f7-b6f4-4a91-aed1-06594c3c63f3` ("Spike F0 — teste
integração (ignorar)"), com 2 signatários `@example.com` e `communicate_events.signature_request
= none`, ou seja, ninguém foi notificado. O envelope ficou em `running` na conta, porque não há
tool para cancelar.

| Pergunta | Resultado | Consequência no workspace |
| --- | --- | --- |
| O MCP baixa o arquivo pelo túnel `trycloudflare.com`? | ✅ Sim, com **1 GET** (log do túnel). O envelope foi criado e confirmado em 4 s | Ponte `tunnel` validada de ponta a ponta. Limite de 3 downloads é suficiente |
| O formato da resposta do create | `{success, confirmed, envelope_id, envelope.attributes.status, job_id, elapsed_seconds}`. Criação assíncrona, com confirmação aguardada pelo MCP | `record` usa `envelope_id` e o status da própria resposta. `confirmed:false` vira ambíguo |
| A ordem de assinatura (`group`) é suportada? | ⚠️ O campo foi **aceito e ignorado**: os 2 signatários ficaram no grupo 1 | `CLICKSIGN_SEND_GROUP=false`, e o resumo avisa que todos recebem ao mesmo tempo. **Pedido ao time do MCP** |
| O prazo aparece em `get_envelope_details`? | ❌ Só vêm `name` e `status` | A confirmação diz que o prazo começou a contar, sem data. **Pedido ao time do MCP** |
| Dá para localizar um envelope recém-criado (E13)? | ✅ `list_envelopes` com `name` exato, `created_from` e `created_to` (obrigatoriamente juntos) e `sort` traz exatamente o envelope | Procedimento de E13 atualizado em `sign-dispatch` |
| De onde vêm os rascunhos sem nome? | O total foi de 111 para 112 com o teste, sem rascunho extra. Só os envelopes `running` têm nome, e há 69 `draft` sem nome. **Não vêm deste fluxo**; provavelmente são rascunhos abandonados na interface web ou de testes antigos | Nenhuma ação. A verificação de E13 continua usando o filtro por nome |
| `communicate_events.signature_request=none` é aceito? | ✅ Aceito sem erro | Virou o modo de teste `CS_SILENT_SEND=true` |
| DNS da rede local | ❌ O DNS desta rede (`10.116.15.254`) não resolve `*.trycloudflare.com`. Pelo DNS público resolve | A verificação do túnel usa DoH (1.1.1.1) |

## Pedidos ao time do MCP da Clicksign
1. Uma tool de criação com **conteúdo do arquivo** (base64/upload), para eliminar a ponte de upload.
2. Repassar **`group`** e o modo sequencial do envelope (ordem de assinatura).
3. Expor **`deadline_at`** (e permitir defini-lo) em `get_envelope_details` e no create.
4. Uma tool para **cancelar envelope**, útil em testes e para desfazer um envio errado.
