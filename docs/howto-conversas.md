# Como conversar com o assistente de assinaturas

Guia prático do que você pode pedir ao assistente pelo Telegram (ou pelo terminal) e do que
esperar em cada caso. Cada seção é uma tarefa: o que mandar, o que o assistente faz e os
cuidados.

> **Legenda:** ✅ disponível · 🧪 disponível em teste (pode falhar) · 🔜 planejado (o assistente
> ainda não faz; a Clicksign já permite) · ⛔ não dá hoje (limitação da Clicksign/MCP)

**Resumo rápido**

| Você quer… | Diga algo como | Status |
| --- | --- | --- |
| Mandar um documento para assinatura | (anexe o arquivo) | ✅ |
| Dizer quem assina | "manda para a Ana, ana@empresa.com" | ✅ |
| Corrigir algo antes de enviar | "troca o e-mail do João", "tira a testemunha" | ✅ |
| Trocar a forma de confirmar identidade | "usa WhatsApp para a Ana" | ✅ |
| Mudar a mensagem ou o título | "muda a mensagem para…" | ✅ |
| Trocar o arquivo | (anexe a versão nova) "essa é a versão final" | ✅ |
| Desistir antes de enviar | "cancela", "deixa pra lá" | ✅ |
| Saber se já assinaram | "o contrato da ACME já foi assinado?" | ✅ |
| Ver o que está pendente | "quais documentos estão pendentes?" | ✅ |
| Cobrar uma assinatura | "manda um lembrete para a Rayssa" | ✅ |
| Falar por áudio | (mande um áudio) | 🧪 |
| Receber o documento assinado | "me manda o termo assinado" | 🔜 |
| Enviar a partir de um modelo da conta | "manda o contrato de aluguel de equipamentos para…" | 🔜 |
| Cancelar um envio já feito | — | ⛔ |
| Definir prazo ou ordem de assinatura | — | ⛔ |

---

## Mandar um documento para assinatura ✅

**Mande o arquivo como arquivo** (📎 → Arquivo), não como foto. Pode ser PDF, Word (.docx/.doc),
imagem ou texto, até 20 MB. Se quiser, escreva junto quem assina.

**O que acontece:**

1. O assistente confirma na hora que recebeu ("Recebi o contrato 👍 Já estou vendo quem
   precisa assinar.").
2. Ele lê o documento e descobre quem assina, o e-mail de cada um e como cada pessoa participa
   (vendedor, compradora, testemunha…).
3. Você recebe **um resumo único** terminando em "Posso enviar?".
4. Responda "pode enviar" e ele confirma o envio.

**Exemplo:**

> **Você:** 📎 contrato-prestacao-servicos.pdf
> **Assistente:** Recebi o contrato de prestação de serviços 👍 Já estou vendo quem precisa assinar.
> **Assistente:**
> 📄 Contrato de prestação de serviços (contrato-prestacao-servicos.pdf, 4 páginas)
> Quem vai assinar:
>   1. Maria Souza (maria@acme.com.br) — contratante
>   2. João Lima (joao@lima.dev) — contratado(a)
> Confirmação de identidade: código por e-mail
> Mensagem: "Olá! Segue o contrato de prestação de serviços para sua assinatura…"
> Posso enviar? (ou me diga o que mudar)
> **Você:** pode enviar
> **Assistente:** Enviando agora…
> **Assistente:** ✅ Enviado! Maria Souza e João Lima já receberam o pedido de assinatura por e-mail, e o prazo para assinar começou a contar.

**Cuidados:**
- **Nada é enviado sem o seu "pode enviar"**, sempre depois do resumo. Se você muda algo, o
  resumo aparece de novo e a confirmação anterior deixa de valer.
- O envio é real: as pessoas recebem e-mail da Clicksign na hora.
- Se o PDF tem senha, está corrompido ou passa de 20 MB, o assistente pede outro arquivo.
- Se o arquivo é uma foto ou um scan sem texto, ele não consegue ler os nomes e pergunta quem
  assina. Mesmo assim o envio funciona normalmente.

## Dizer quem assina ✅

Você pode informar quem assina **junto com o arquivo**, **depois que o assistente perguntar** ou
**por cima do que está no documento**:

- "manda para a Rayssa, rayssa.martins@clicksign.com"
- "só o Carlos assina"
- "a Ana assina pela Lima Consultoria, ana@lima.dev"
- "inclui o Pedro como testemunha, pedro@exemplo.com"

**Quando o assistente pergunta:**
- Faltou algum e-mail: ele pede **só** o que falta ("Faltou o e-mail do João e da Ana — me
  passa?").
- O documento não tem nomes, como um modelo com campos em branco: ele pergunta "Quem precisa
  assinar?".
- Uma empresa assina sem o nome do representante: ele pergunta "Quem assina pela Escola
  Horizonte Azul?".

**Cuidados:**
- O assistente **nunca inventa e-mail**. Quando um e-mail no documento não parece ser de
  contato, como uma chave PIX, ele marca "⚠ confira" no resumo.
- O que você diz vale mais do que o que está no documento.

## Corrigir algo antes de enviar ✅

Depois do resumo, peça a mudança com suas palavras. O resumo atualizado volta **na mesma
resposta**.

| Para… | Diga |
| --- | --- |
| Corrigir um e-mail | "o e-mail do João é joao@lima.dev" |
| Tirar alguém | "tira a testemunha" / "só a Maria assina" |
| Incluir alguém | "inclui a Beatriz, beatriz@exemplo.com, como testemunha" |
| Mudar a mensagem | "muda a mensagem para: Oi Maria, segue o contrato que conversamos" |
| Mudar o título | "o título é Contrato ACME — março" |
| Mudar a confirmação de identidade | "usa WhatsApp para a Ana" (ele pede o celular se faltar) |

**Formas de confirmar identidade disponíveis:** código por e-mail (padrão), por SMS ou por
WhatsApp. Selfie, documento oficial, certificado digital e Pix existem na Clicksign, mas ainda
não estão liberados no assistente.

## Trocar o arquivo ✅

Mande a nova versão com algo como "essa é a versão final" ou "mandei o errado". O assistente lê
de novo e **mantém as pessoas que você já confirmou**. Depois do envio não dá para trocar o
arquivo; nesse caso é preciso fazer um envio novo.

## Desistir antes de enviar ✅

"cancela", "deixa pra lá", "não envia". O assistente confirma que **nada foi enviado**. Se você
simplesmente parar no meio, o envio fica guardado por 7 dias. Na próxima mensagem ele pergunta
se você quer continuar.

## Saber se já assinaram ✅

- "o contrato do BYD Dolphin já foi assinado?"
- "a Rayssa já assinou?"
- "já assinaram?" (sobre o último envio)

O assistente responde quem assinou (com data e hora), quem falta e se o documento está
concluído. Se houver mais de um documento parecido, ele pergunta qual é.

## Ver o que está pendente ✅

"quais documentos estão pendentes de assinatura?" traz a lista de **todos** os documentos da
conta que aguardam assinatura, inclusive os que não foram enviados pelo assistente, e quem falta
em cada um. A lista vem numerada, então você pode responder "manda lembrete do item 2".

## Cobrar uma assinatura (lembrete) ✅

- "manda um lembrete para a Rayssa" (uma pessoa)
- "cobra todo mundo do contrato da ACME" / "lembrete do item 4" (todos que faltam)

**Cuidados:**
- O lembrete vai **só por e-mail**, mesmo que o pedido original tenha ido por WhatsApp ou SMS.
- A Clicksign aceita **um lembrete por minuto** para cada documento ou pessoa. O assistente
  avisa quando o próximo pode sair.
- O assistente não manda lembrete por conta própria, só quando você pede.

## Falar por áudio 🧪

Mande um áudio como mandaria uma mensagem: "qual o status do contrato do BYD?", "lista os
pendentes". O assistente transcreve e segue normalmente.

**Cuidados:**
- Áudios muito curtos ou com ruído podem ser mal entendidos. Nesse caso o assistente diz o que
  entendeu e pede para repetir.
- Para **ações que mandam algo para alguém** (enviar, lembrete), o assistente confirma por
  escrito antes de agir se o áudio não estiver claro.
- Nomes e e-mails ditos em áudio costumam vir com erro. Prefira escrevê-los.

## Receber o documento assinado 🔜

A Clicksign já disponibiliza o PDF assinado. O assistente ainda não está preparado para baixá-lo
e mandar no chat. Por enquanto, ele vai por e-mail para quem assinou, ou fica na plataforma
Clicksign.

## Enviar a partir de um modelo da conta 🔜

A conta tem modelos prontos (ex.: "Contrato de aluguel de equipamentos", "Contrato de Licença de
Uso de Imagem e Voz"). A Clicksign permite enviar a partir deles preenchendo os campos, mas o
assistente ainda não faz esse fluxo. Por enquanto, gere o documento e mande o arquivo.

## O que não dá para fazer hoje ⛔

| Pedido | Por quê | Alternativa |
| --- | --- | --- |
| Cancelar ou editar um envio já feito | o MCP da Clicksign não oferece essa ação | cancelar pela plataforma Clicksign |
| Definir prazo para assinar | o MCP não aceita prazo, e o assistente também não consegue consultá-lo | usa o prazo padrão da conta |
| Definir ordem ("a Maria assina depois do João") | o MCP ignora a ordem e todos recebem ao mesmo tempo | mandar em dois envios separados |
| Vários arquivos no mesmo envio | o assistente trabalha com um documento por vez | um envio por arquivo |
| Incluir observador (alguém que só acompanha) | ainda não suportado | — |
| Mudar a conta Clicksign usada | a conta é fixa na configuração | pedir ao administrador do assistente |

## Dicas

- **Mande o PDF como arquivo** (📎 → Arquivo), não como foto: a foto é comprimida e fica mais
  difícil de ler.
- **Escreva e-mails** em vez de ditar.
- Em dúvida, pergunte: "o que você consegue fazer?" traz este resumo.
- `/start` e `/help` no Telegram são comandos da ponte e não do assistente. Para ajuda,
  escreva normalmente.
