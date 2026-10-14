# Plano — Workspace agêntico "Envio Pontual" (Clicksign)

> **Objetivo:** um workspace onde o agente (Claude Code, pi ou Codex) resolve o job da
> persona Pontual descrito em `JTBD_Persona_Pontual.md`: *"formalizar um documento o mais
> rápido possível, para retornar à atividade principal sem gerar retrabalho"*. A conversa é
> a interface, e o MCP da Clicksign é o braço que executa.
>

---

## 1. Leitura do problema

O JTBD descreve um fluxo de 6 nós com 15 exceções. As restrições abaixo moldam o desenho:

| Restrição do JTBD | Consequência para o workspace |
| --- | --- |
| Caminho feliz = **anexar, aceitar a lista, enviar** | O agente não pergunta nada no caminho feliz. Pergunta só em 3B/E5, e no máximo uma vez. |
| "Zero aprendizado": a persona não conhece envelope, requisito, `role`, `auth` | Nenhum termo técnico do MCP aparece para o usuário (o próprio MCP já exige isso nos guias). |
| Sem chips nem botões de intenção na landing | A entrada é conversacional: soltar o arquivo **é** o gatilho. O slash command existe só para dev e debug. |
| Editar nunca cria jornada paralela | O estado é uma **máquina de nós**: editar volta ao nó certo e reconverge no resumo. |
| Permissão de leitura resolvida no onboarding | Existe um fluxo de **onboarding** separado, executado uma vez, e um pré-check silencioso no início de cada sessão. |
| Confirmação clara com prazo | Depois do envio, o agente lê o envelope criado e confirma status e prazo. |

---

## 2. O que aproveitar do executive-assistant (e o que não)

### Aproveitar

| Padrão do EA | Como entra aqui |
| --- | --- |
| `CLAUDE.md` + `AGENTS.md` + `.agents/* -> .claude/*` (symlinks) | O mesmo conteúdo serve Claude Code, Codex **e pi** (o pi lê `AGENTS.md`/`CLAUDE.md` e `.agents/skills/`). |
| `.claude/rules/` como fonte única de convenções | `language`, `naming`, `skill-command-boundary`, `orchestration` e duas regras novas: `user-vocabulary` e `dispatch-safety`. |
| Skill = **o quê**, command = **como** | Cada nó da jornada vira uma skill. A orquestração da jornada fica em um command. |
| Nome de skill com prefixo de categoria | Categorias novas: `sign` (jornada de envio), `track` (pós-envio), `write` (mensagem ao signatário), `ops` (onboarding/infra). |
| JSON Schema para cada artefato entre etapas | `extraction.json`, `journey-state.json`, `dispatch-payload.json`, validados antes do envio. |
| Pré-check de conectividade de MCP antes de começar | `ops-onboarding` faz o check completo e cada jornada faz um check leve (conta selecionada, MCP respondendo). |
| Degradação explícita (`host-requires`) | Ex.: sem OCR, um scan vira E9 com mensagem clara, nunca um chute. |
| `.env.example` + segredos fora do git + `settings.local.json.example` com allowlist | Allowlist de `mcp__clicksign__*` e das ferramentas locais. |
| `doctor` read-only com exit code estável (0/1/2) | `bin/cs doctor`: MCP autenticado, conta definida, backend de upload ok, extratores de texto presentes. |
| `knowledge/` carregado sob demanda | Glossário de papéis PT→EN, políticas de autenticação, tom de voz da mensagem Click.AI. |

### Deixar de fora (overkill para este escopo)

- Binário Go `ea` com dezenas de domínios, Multica, painel de review adversarial multi-engine, hooks de sessão, worktrees obrigatórios.
- Subagentes por padrão: aqui a latência da conversa importa mais que paralelismo. Fica **um** subagente opcional para ler documentos longos sem poluir o contexto da conversa.

---

## 3. Achados do spike no MCP da Clicksign (com impacto direto no plano)

Inspecionei as 20 ferramentas e os guias do servidor `https://mcp.clicksign.com/mcp/oauth2`:

| # | Achado | Impacto | Ação |
| --- | --- | --- | --- |
| A1 | **Não há upload de arquivo local para envelope.** `create_envelope_with_file_url` exige URL **HTTPS pública**. Base64 só é aceito em `create_template` (.doc/.docx). | Bloqueia o nó 1 ("solta o arquivo") sem uma ponte. | Ponte de upload: bucket com **URL assinada de TTL curto (≤15 min)**, apagada após o envio. Em paralelo, pedir ao time do MCP uma tool `create_envelope_with_file_content` (o guia cita `content_base64`/INT-575 já no backend, então o gap está só na tool). |
| A2 | **Criar = enviar.** `create_envelope_with_file_url` cria e dispara na mesma chamada, sem rascunho revisável no Clicksign. | O resumo (nó 5) existe só no agente. É a única barreira antes de uma ação **irreversível** (e-mail chega no cliente da persona). | Regra `dispatch-safety`: só chama a tool depois de um "Enviar" explícito, no turno seguinte ao resumo, com hash do payload igual ao resumido. |
| A3 | **A ordem de assinatura (`group`) não aparece no shape da tool**, embora o guia de signatários documente o campo. | Nó 3A promete "ordem reconhecida". | Spike: testar se `group` passa no payload. Se não passar, pedir a feature ao MCP e, até lá, avisar no resumo que todos assinam em paralelo. |
| A4 | **Prazo (`deadline_at`) não é parametrizável** na tool. `remind_interval` tem default 3. | Nó 6 promete "início da contagem de prazo". | Ler o prazo com `get_envelope_details` depois do envio e mostrá-lo na confirmação. Alterar o prazo fica fora do MVP (anotar como E6 parcial). |
| A5 | Métodos de autenticação aceitos: `email`, `sms`, `whatsapp`, `selfie`, `official_document`, `liveness`, `address_proof`, `icp_brasil`, `pix` (`presential` é rejeitado). | Responde parcialmente o ponto em aberto "lista real de métodos do nó 4". | Mapear na skill `sign-auth-policy`. Validar com produto quais expor. |
| A6 | **Múltiplas contas por sessão OAuth.** Toda sessão nova exige `select_account`. | Fricção escondida que a persona não pode ver. | O onboarding grava `CLICKSIGN_ACCOUNT_KEY` e o pré-check de cada jornada chama `select_account` em silêncio. |
| A7 | `list_envelopes` devolve `name: ""` e a conta de teste tem **111 rascunhos sem nome**. | Não dá para deduplicar envios consultando a Clicksign por nome. Rascunhos órfãos sugerem falhas parciais em criações anteriores. | Idempotência pelo **estado local** (id do envelope gravado). Em erro ambíguo, conferir antes de repetir (E13). Investigar a origem dos rascunhos no spike. |
| A8 | `quick_send_envelope` aceita só nome do documento + 1 e-mail. | Não serve à jornada (sem arquivo, sem papel, sem autenticação). | Não usar. |
| A9 | Os guias do MCP já trazem o glossário PT→EN de papéis e a regra "nunca mostrar JSON ao usuário". | Bate com o "zero aprendizado". | Reaproveitar o glossário em `knowledge/` e reforçar com a regra `user-vocabulary`. |
| A10 | `list_envelope_signers` deriva o status de cada signatário a partir de eventos, e há tools de lembrete. | Habilita um pós-envio barato. | Skill `track-envelope-status` (fase 4). |

---

## 4. Estrutura proposta

```text
/home/code/rayssa/clicksign/
├── AGENTS.md                         # instruções canônicas (Codex/pi): papel, loop conversacional, regras
├── CLAUDE.md                         # → aponta para AGENTS.md + específicos do Claude Code
├── README.md                         # setup humano: OAuth MCP, conta, bucket, doctor
├── JTBD_Persona_Pontual.md           # fonte de produto (já existe)
├── .env.example                      # CLICKSIGN_ACCOUNT_KEY, UPLOAD_BUCKET, UPLOAD_TTL_SECONDS, DRY_RUN
├── .mcp.json                         # clicksign (Claude Code)
├── .pi/mcp.json                      # clicksign (pi, se usar o MCP nativo do pi)
├── .agents/{skills,commands,rules,knowledge} -> ../.claude/*
├── bin/cs                            # CLI local (ver §6)
├── .claude/
│   ├── settings.json                 # allowlist mcp__clicksign__*, Bash(bin/cs *)
│   ├── settings.local.json.example
│   ├── rules/
│   │   ├── language.md               # instruções em EN, conversa em pt-BR
│   │   ├── naming.md                 # categorias sign|track|write|ops
│   │   ├── skill-command-boundary.md
│   │   ├── user-vocabulary.md        # termos proibidos na conversa (envelope, requirement, auth, role, JSON…)
│   │   ├── dispatch-safety.md        # regras do envio irreversível (§7)
│   │   └── privacy.md                # PII: CPF, e-mails, texto do documento
│   ├── commands/
│   │   ├── send-for-signature.md     # ORQUESTRADOR da jornada (nós 1→6, exceções, estado)
│   │   └── setup.md                  # onboarding (uma vez)
│   ├── skills/
│   │   ├── ops-onboarding/           # OAuth, select_account, ponte de upload, consentimento de leitura
│   │   ├── sign-document-intake/     # nó 1: valida o arquivo, extrai texto, detecta ilegível (E9) e troca (E8)
│   │   ├── sign-party-extraction/    # nó 2→3A/3B: partes, e-mails, papéis, ordem, evidência por campo
│   │   │   └── schemas/extraction.schema.json
│   │   ├── sign-auth-policy/         # nó 4: padrão e-mail, regras de ajuste pelo documento (E3)
│   │   ├── sign-review-summary/      # nó 5: formato do resumo único, edição por linguagem natural (E4/E6/E7)
│   │   ├── sign-dispatch/            # nó 6: upload → create → verificação → confirmação (E13)
│   │   │   └── schemas/dispatch-payload.schema.json
│   │   ├── write-signer-message/     # mensagem "Click.AI" ao signatário
│   │   └── track-envelope-status/    # pós-envio: quem assinou, lembrete (fase 4)
│   ├── agents/
│   │   └── send-for-signature-reader.md  # opcional: lê documento longo e devolve só extraction.json
│   ├── knowledge/
│   │   ├── roles-glossary.md         # papel PT→EN (derivado do guia do MCP)
│   │   ├── auth-methods.md           # métodos aceitos + quando sugerir cada um
│   │   └── voice-click-ai.md         # tom da mensagem ao signatário e das respostas
│   └── references/send-for-signature/
│       └── journey-state.schema.json
├── evals/
│   ├── fixtures/                     # documentos sintéticos (nomes e e-mails @example.com)
│   └── expected/                     # extração esperada + nº de perguntas esperado
└── runs/                             # gitignored: estado de cada jornada (permite retomar, E14)
```

**Por que o estado fica em `runs/` e não em `/tmp`, como no EA:** a E14 ("abandona no meio") pede retomada. `runs/<run_id>/` guarda `journey-state.json` + `extraction.json` e é limpo depois do envio, com retenção curta por privacidade.

---

## 5. A jornada como máquina de estados

O command `send-for-signature` é o orquestrador. O `AGENTS.md` instrui que **qualquer mensagem com arquivo anexado ou com intenção de "mandar para assinar" inicia essa jornada**, sem o usuário digitar comando (princípio "sem chips na landing").

```
          ┌──────────────────────── E3 editar autenticação ───────────────────────┐
[1 INTAKE] → [2 READ] ─┬→ [3A SIGNERS_PROPOSED] → [4 AUTH_APPLIED] → [5 REVIEW] ─→ [6 DISPATCHED]
     ↑  E8 troca doc   │        ↑ E2/E7 edita             ↑            │ E4/E6 edita   │
     │                 └→ [3B ASK_SIGNERS] ───────────────┘            └→ volta ao nó   └→ [TRACK]
     └── E9 ilegível         (E1/E5: 1 pergunta)
```

| Nó | Skill | Fala com o usuário? | Ferramentas | Saída no estado |
| --- | --- | --- | --- | --- |
| 1 Intake | `sign-document-intake` | Não, salvo E9 | `cs doc text`, `cs doc hash` | `document.{path,hash,filename,pages,text_ref}` |
| 2 Read | `sign-party-extraction` | Não | (LLM) | `extraction.json` com `confidence` e **trecho de evidência** por signatário |
| 3A/3B | `sign-party-extraction` | Só se faltar parte ou e-mail (1 pergunta) | — | `signers[]` + `order` |
| 4 Auth | `sign-auth-policy` | Não (vira uma linha no resumo) | — | `signers[].auth` |
| 5 Review | `sign-review-summary` + `write-signer-message` | **Sim**: resumo único + "posso enviar?" | — | `summary_hash` |
| 6 Dispatch | `sign-dispatch` | Confirmação final | `cs upload` → `clicksign_create_envelope_with_file_url` → `clicksign_get_envelope_details` / `clicksign_list_envelope_signers` → `cs upload --delete` | `envelope_id`, `deadline`, `status` |

**Formato do resumo (nó 5), em linguagem de persona:**

```
📄 Contrato de Prestação de Serviços — ACME.pdf (4 páginas)

Quem vai assinar:
  1. Maria Souza (maria@acme.com.br) — contratante
  2. João Lima (joao@lima.dev) — contratado

Confirmação de identidade: código por e-mail
Mensagem: "Olá! Segue o contrato de prestação de serviços para sua assinatura…"

Posso enviar? (ou me diga o que mudar)
```

Edição em linguagem natural ("troca o e-mail do João", "a Maria assina depois") volta ao nó correspondente, atualiza o estado e **reapresenta o resumo no mesmo turno** (E7: edição e reconfirmação em um único turno).

---

## 6. Ferramentas locais (`bin/cs`)

Seguindo o princípio do EA ("lógica nova vira subcomando de um CLI, não script solto"), em versão enxuta:

| Comando | Função |
| --- | --- |
| `cs doctor` | Read-only, exit 0/1/2: MCP autenticado, `CLICKSIGN_ACCOUNT_KEY` definido, bucket gravável, extratores (`pdftotext`, `pandoc`/`python-docx`, OCR opcional) presentes |
| `cs doc text <file>` | Extrai texto (PDF, DOCX, TXT, imagem via OCR). Detecta PDF protegido, scan sem texto e formato não suportado (E9) |
| `cs doc hash <file>` | sha256, para detectar troca de documento (E8) e para a idempotência |
| `cs upload <file>` / `cs upload --delete <ref>` | Sobe o arquivo para o bucket e devolve URL assinada HTTPS com TTL curto. Apaga depois do envio |
| `cs state new/get/set/validate` | Lê e grava `runs/<id>/journey-state.json` e valida contra o schema |
| `cs eval` | Roda os fixtures em `DRY_RUN` e mede as métricas do §9 |

**Linguagem:** recomendo **Python + uv**, porque o ecossistema de extração de documentos (pypdf, python-docx, OCR) é bem mais maduro que em Go. O EA usa Go, mas para outro tipo de problema. Decisão em aberto (§11).

Hoje esta máquina não tem `pdftotext` nem `pandoc` instalados, então o `cs doctor` precisa cobrir isso.

---

## 7. Regras invioláveis (`rules/dispatch-safety.md` e `rules/user-vocabulary.md`)

1. **Nada é enviado sem "Enviar" explícito** no turno imediatamente após um resumo, e o payload enviado tem que ter o mesmo `summary_hash` do resumo mostrado. Qualquer edição invalida a confirmação anterior.
2. **Um envio por jornada.** `envelope_id` é gravado no estado. Em erro ambíguo (timeout, 5xx), o agente **confere antes de repetir** (detalhes e signatários de envelopes recentes) e nunca reenvia às cegas (E13, A7).
3. **Nunca inventar contato.** Sem e-mail ou telefone extraído com evidência, pergunta (E5). Nunca completa "maria@empresa.com" por padrão.
4. **Vocabulário da persona:** proibido mostrar "envelope", "requirement", "role", "auth", "provide_evidence", "signer", JSON ou IDs técnicos, salvo pedido explícito. Dizer "documento", "quem assina", "como a pessoa confirma a identidade".
5. **No máximo uma pergunta por turno** e zero no caminho feliz.
6. **Privacidade:** o texto do documento não vai para o git nem para o log. CPF e dados de qualificação não aparecem no resumo sem necessidade. O arquivo no bucket é apagado após o envio e `runs/` tem retenção curta.
7. **Conta errada é envio errado:** o pré-check confirma a conta selecionada e, se houver mais de uma e nenhuma configurada, isso vira onboarding, não pergunta no meio da jornada (A6, E15).

---

## 8. Exceções → tratamento

| ID | Tratamento | Skill |
| --- | --- | --- |
| E1 | Uma pergunta: "Quem precisa assinar? Pode mandar nome e e-mail." | party-extraction |
| E2/E7 | Edição por linguagem natural + resumo reapresentado no mesmo turno | review-summary |
| E3 | "Quer outra forma de confirmar identidade? Pode ser SMS, WhatsApp, selfie…" Sem bifurcar a jornada | auth-policy |
| E4/E6 | Edição a partir do resumo volta ao nó dono do campo e reconverge no resumo | orquestrador |
| E5 | Pede **só** o dado que falta ("Qual o e-mail do João Lima?"), sem refazer a lista | party-extraction |
| E8 | Hash diferente ⇒ relê o documento. **Proposta:** preserva os signatários editados à mão e mostra a diferença | document-intake |
| E9 | PDF com senha ou formato não suportado → pede outro arquivo. Scan → OCR se disponível; senão pede outro arquivo **ou** segue para 3B | document-intake |
| E10 | Separa "partes que assinam" de "pessoas citadas" (procurador, testemunha, terceiros). Propõe só as primeiras e menciona as outras em uma linha | party-extraction |
| E11 | Qualificação (CPF/endereço) fica no documento e não no resumo. Sinaliza só se a autenticação exigir | auth-policy |
| E12 | Cada signatário guarda o trecho de evidência. Se a confiança for baixa, o resumo marca a linha com "⚠ confira". O e-mail nunca vem de inferência | party-extraction |
| E13 | Retry seguro (regra 2) + mensagem clara + estado preservado | dispatch |
| E14 | `runs/<id>` persiste. Na próxima mensagem: "Você tinha um envio do *Contrato X* pela metade. Continuo?" | orquestrador |
| E15 | Pré-check falhou ⇒ direciona para `/setup` antes de ler qualquer documento | ops-onboarding |

---

## 9. Avaliação (critérios de sucesso do JTBD → métricas)

- **Fixtures sintéticos** (≥12), um por cenário: partes claras (2 e 3 assinantes, com ordem), sem partes (E1), nome sem e-mail (E5), muitas partes citadas (E10), scan (E9), PDF com senha, DOCX, contrato com testemunhas, documento com qualificação/CPF (E11), e-mail ambíguo (E12).
- **`cs eval` em DRY_RUN:** roda a jornada com respostas roteirizadas do "usuário" e compara a extração com `expected/`. Valida o payload contra o schema **sem** chamar a tool de envio.
- **Métricas:**
  - nº de perguntas por jornada (meta: 0 no caminho feliz, 1 em 3B)
  - nº de turnos até "Enviar"
  - precisão e recall de signatários e e-mails
  - % de resumos aceitos sem edição
  - incidência de termos proibidos na conversa (lint automático sobre a transcrição)
- **Teste end-to-end real:** em conta de teste, com signatários de e-mail próprios (o envio é real e notifica pessoas).

---

## 10. Fases de entrega

| Fase | Entrega | Critério de pronto |
| --- | --- | --- |
| **F0 — Spike MCP** (1–2 dias) | Validar A1 (URL assinada aceita?), A3 (`group`), A4 (prazo lido em `get_envelope_details`), A5 (métodos de autenticação), A7 (origem dos rascunhos sem nome) | Relatório curto + lista de pedidos ao time do MCP |
| **F1 — Esqueleto** | `AGENTS.md`/`CLAUDE.md`, rules, symlinks `.agents`, `.mcp.json`/`.pi/mcp.json`, `.env.example`, `.gitignore`, `cs doctor`, `/setup` | `cs doctor` retorna 0 em máquina configurada |
| **F2 — Caminho feliz** | Nós 1–6, `cs doc`, `cs upload`, `cs state`, schemas, resumo, mensagem Click.AI | Contrato limpo: anexar → aceitar → enviar, com 0 perguntas e confirmação mostrando prazo |
| **F3 — Exceções da árvore** | E1–E7 | Fixtures correspondentes verdes em `cs eval` |
| **F4 — Robustez** | E8–E15, retomada, retry seguro, `track-envelope-status` (status + lembrete) | Todos os fixtures verdes, lint de vocabulário zerado |
| **F5 — Omnichannel** (opcional) | Mesmo fluxo via Telegram (a ponte pi↔Telegram já está ativa nesta máquina): PDF enviado pelo celular → resumo → "enviar" | Jornada completa pelo celular |

---

## 11. Decisões

| # | Decisão | Status |
| --- | --- | --- |
| 1 | Ponte de upload | ✅ **Opção A — quick tunnel do Cloudflare** (sem bucket), escolhida quando o canal passou a ser o Telegram. O link do Telegram foi descartado porque carrega o token do bot. S3/GCS continuam no `cs` como alternativa de produção, e o pedido ao MCP de uma tool de upload por conteúdo segue como solução definitiva |
| 1b | Canal | ✅ **Telegram** (ponte pi ↔ Telegram) como principal. O terminal continua funcionando |
| 2 | Conta | ✅ `2b738bd7-c875-4396-a29d-f3896c7ebb91` (Rayssa Raphaely Souza de Medeiros Martins), gravada no `.env` |
| 3 | Harness | ✅ **pi** com `anthropic/claude-opus-5-5` (`.pi/settings.json`). Por isso a estrutura é nativa do pi: `.agents/` é a fonte canônica (sem `.claude/` nem `CLAUDE.md`), os comandos ficam em `.pi/prompts/` e o MCP em `.mcp.json` (lido pelo pi-mcp-adapter) |
| 4 | Linguagem do `cs` | ✅ **Python + uv** |
| 5 | E8 (troca de documento) | Implementado como hipótese: preserva signatários (`--reset-signers` para descartar) |
| 6 | E10 (muitas partes) | Implementado como hipótese: propõe só quem assina e cita os demais em uma linha |
| 7 | Autenticação no MVP | Implementado como hipótese: e-mail, SMS e WhatsApp (`CS_ALLOWED_AUTHS`) |

## 12. Status

- **F1 (esqueleto): feita.** `AGENTS.md`, 5 regras, 8 skills, 2 commands, knowledge, `.pi/`, `.mcp.json`, `.env(.example)`, `.gitignore` e `cs doctor`.
- **F2 (caminho feliz): pronta em dry run.** `cs run/review/dispatch/upload` com schemas e 29 testes. O roteiro de ponta a ponta pelo CLI passou: resumo → hash → prepare → record → scrub.
- **Ponte de upload (túnel):** implementada e validada de verdade. `cs upload selftest` sobe o arquivo em cerca de 7 s, o conteúdo baixado é idêntico (`application/pdf`) e a URL deixa de funcionar ao fechar. O teste integrado (`prepare` com túnel real, depois `fail`) fecha o túnel e apaga a cópia temporária do Telegram. São 36 testes no total.
- **Telegram:** o prefixo de timestamp da ponte é removido do nome do arquivo, foto comprimida é detectada (`compressed_photo`), a cópia temporária é apagada no `scrub` e as respostas saem em texto simples.
- **F0 (spike MCP): feita** (`docs/spike-f0.md`). O MCP baixa o arquivo pelo túnel (1 GET) e cria e confirma o envelope em 4 s. O `group` é aceito mas ignorado, e o prazo não é exposto, então os dois viraram pedidos ao time do MCP. A busca por nome + período funciona para E13. Os rascunhos sem nome não vêm deste fluxo. Também foi criado o modo de teste `CS_SILENT_SEND`.
- **Envio real habilitado** (`CS_DRY_RUN=false`) na conta de teste da Rayssa, com uso autorizado de todos os recursos. Os e-mails de quem assina vêm do documento ou da conversa (`source: "user"`).

- **Documentação de uso (how-to):** `docs/howto-conversas.md`, voltada ao usuário, mostra o que ele pode pedir, com exemplos, cuidados e status (✅/🧪/🔜/⛔). Para o agente, a mesma informação está em `.agents/knowledge/capabilities.md`, e um teste garante que as duas versões não divergem.

### Backlog que saiu dos testes com usuário (2026-10-09)
1. `cs voice transcribe`: promover a transcrição de áudio (hoje improvisada com faster-whisper) para um comando do CLI, com teste e limpeza do `.ogg`.
2. Documento assinado de volta no chat: `list_envelope_documents` → `links.files.signed` → download → `telegram_attach`.
3. Envio a partir de modelo da conta: skill nova com a mesma trava de resumo/hash do envio por arquivo.
4. Nome do arquivo enviado gerado a partir do título (a ponte do Telegram troca acentos por `_`).
5. E-mail que não é de contato (ex.: chave PIX) vira pergunta, não "⚠ confira".
6. Normalizar o texto extraído do PDF (hoje vem uma palavra por linha).
