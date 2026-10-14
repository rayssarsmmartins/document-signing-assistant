# Avaliações (fase F3)

Cenários sintéticos (pessoas fictícias, e-mails `@example.com`) para medir os critérios de
sucesso do JTBD em `CS_DRY_RUN=true`:

| Cenário | Exceção | Esperado |
| --- | --- | --- |
| contrato com 2 partes e e-mails | caminho feliz | 0 perguntas, resumo aceito |
| contrato com representante de empresa | — | `represents` preenchido |
| documento sem partes | E1 | 1 pergunta ("quem assina?") |
| nome sem e-mail | E5 | 1 pergunta só pelo dado faltante |
| muitas pessoas citadas | E10 | só signatários propostos; demais em uma linha |
| PDF digitalizado | E9 | vai direto para "quem assina?" |
| PDF com senha | E9 | pede outro arquivo |
| linhas de testemunha vazias | — | nota no resumo, sem pergunta |
| e-mail não presente no documento | E12 | nenhum e-mail inventado |

Métricas: perguntas por jornada, turnos até "enviar", precisão/recall de signatários e
contatos, termos proibidos no texto exibido (`.agents/rules/user-vocabulary.md`).

A pasta `fixtures/` recebe os documentos e `expected/` a extração esperada. O runner
(`cs eval`) está planejado para a fase F3.
