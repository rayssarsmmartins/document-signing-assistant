# Envio Pontual — workspace agêntico sobre o MCP da Clicksign

Assistente conversacional para a persona **Pontual**: a pessoa
solta o documento, confere um resumo e diz "pode enviar". O agente (pi + `claude-opus-5-5`)
conversa e opera o **MCP da Clicksign**. O CLI local `bin/cs` (Python + uv) cuida do que precisa
ser determinístico: leitura do arquivo, estado da jornada, resumo, payload, upload e as travas
de envio.

Plano e decisões: `PLANO_WORKSPACE.md`. Instruções do agente: `AGENTS.md`.
**O que o usuário pode pedir (how-to):** `docs/howto-conversas.md`.

## Requisitos

- [pi](https://github.com/earendil-works/pi) com a extensão `pi-mcp-adapter`
- [uv](https://docs.astral.sh/uv/) (Python ≥ 3.11 é gerenciado por ele)
- Login OAuth no MCP da Clicksign (`https://mcp.clicksign.com/mcp/oauth2`)
- [`cloudflared`](https://github.com/cloudflare/cloudflared) no PATH ou em `~/.local/bin`: é a ponte de upload padrão, um quick tunnel sem conta. Um bucket S3/GCS é opcional
- A ponte pi ↔ Telegram (`pi-telegram`) configurada, já que o Telegram é o canal principal

## Setup

```bash
uv sync                      # dependências
cp .env.example .env         # depois preencha conta e bucket
chmod 600 .env
bin/cs doctor                # 0 = ok · 1 = avisos · 2 = erro
pi                           # dentro do workspace; depois /setup para o onboarding guiado
```

Para validar a ponte de upload sem enviar nada: `bin/cs upload selftest <algum.pdf>`.
`CS_DRY_RUN=true` roda a jornada inteira com o envio simulado (bom para demos).

## Ponte de upload: por que um túnel

O MCP da Clicksign só aceita uma **URL HTTPS pública** do arquivo. O link do próprio Telegram
(`api.telegram.org/file/bot<TOKEN>/…`) não pode ser usado, porque contém o token do bot. No
envio, o `cs` abre um quick tunnel do Cloudflare que serve **só aquele arquivo**, num caminho
aleatório, por no máximo 10 minutos e 3 downloads, e o fecha assim que o envio é registrado.
Redes cujo DNS não resolve `trycloudflare.com` não atrapalham, porque a verificação usa DNS
público (DoH), como a Clicksign.

## Uso

**Pelo Telegram (canal principal):** mande o documento **como arquivo** (📎 → Arquivo), com ou
sem uma frase. O assistente responde com o resumo, e "pode enviar" dispara o envio.

**Pelo terminal:** cole o caminho do arquivo, se quiser com uma instrução:

```
~/Downloads/contrato-acme.pdf
```

```
manda esse NDA pra assinatura: ~/Downloads/nda.pdf — a Ana assina pela Lima, ana@lima.dev
```

Também existem `/send-for-signature [arquivo]` para retomar ou depurar e `/setup` para o
onboarding. Depois do envio, dá para perguntar "já assinaram?" ou "cobra o João".

## Estrutura

| Caminho | Papel |
| --- | --- |
| `AGENTS.md` | contexto do agente: comportamento padrão, regras, mapa |
| `.agents/rules/` | regras invioláveis: envio seguro, vocabulário, privacidade, conversa |
| `.agents/skills/` | uma skill por nó da jornada (`sign-*`), pós-envio (`track-*`), mensagem (`write-*`), setup (`ops-*`) |
| `.agents/commands/` | orquestração: `send-for-signature`, `setup` |
| `.agents/knowledge/` | glossário de papéis, métodos de autenticação, voz |
| `.pi/` | modelo padrão e slash commands do pi |
| `src/cs/`, `bin/cs` | CLI local; schemas em `src/cs/schemas/` |
| `tests/` | `uv run pytest -q` |
| `runs/` | estado das jornadas (gitignored, contém dados pessoais) |

## CLI `cs`

```
cs doctor                         diagnóstico read-only
cs run new|get|patch|list|abandon|replace-doc|scrub|prune|metric
cs review show|check RUN          resumo único + hash de confirmação
cs dispatch prepare RUN --hash H  trava: hash, upload, payload validado
cs dispatch record|fail|resolve   registra o resultado do envio (retry seguro)
cs upload put|delete|selftest     ponte de upload (túnel ou bucket)
cs glossary role "<termo>"        papel pt-BR → API
```
