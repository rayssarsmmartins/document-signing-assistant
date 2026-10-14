# JTBD — Persona Pontual (Operador 2.0)

> **Fontes:** proto-persona Pontual (Nova Visão VS Operador H2/2026, slide 5), árvore de decisão "Jornada Pontual" (Miro), post-its de premissas (primeiro uso / configurar vs. pode querer alterar) e decisões já travadas do projeto.
> **Convenção:** itens marcados com **[Hipótese]** são proposta minha para validar, não vêm direto das fontes. Tudo sem marcação vem da árvore, do deck ou dos post-its.

---

## 1. Quem é

| | |
| --- | --- |
| **Perfil** | Empreendedor, consultor, profissional de marketing |
| **Frequência** | Esporádico: 1 a 4 documentos por mês |
| **Modo de envio** | Um documento por vez, tudo no padrão |
| **Dor crítica** | Fricção desnecessária para envios simples e pontuais |
| **Foco para Produto & Tech** | Interface minimalista, jornadas omnichannel, melhor responsivo/mobile, onboarding guiado por uso/pacote |
| **Estado da evidência** | Estudo preliminar (dez/25), ~19 entrevistas sintetizadas em 3 arquétipos. A validar. |

Contexto de uso: assinar é uma tarefa **no meio do caminho**, não a atividade principal. Como usa pouco, a persona tem pouca memória muscular da plataforma e tende a chegar com o documento pronto e pouca paciência para configuração.

---

## 2. Job-to-be-done

### Job principal (do deck)
> **Formalizar um documento o mais rápido possível, para retornar à atividade principal sem gerar retrabalho.**

### Job statement (formato "Quando… quero… para…")
> **Quando** preciso colher a assinatura de alguém em um documento que já tenho em mãos, **quero** soltar o arquivo e confirmar poucas coisas, **para** que o envio saia certo sem eu aprender ou revisar uma configuração inteira, e eu voltar ao que estava fazendo.

### Dimensões do job

| Dimensão | O que a persona quer |
| --- | --- |
| **Funcional** | Enviar um documento para assinatura com o mínimo de decisões; ter os signatários identificados sem digitar tudo; não errar destinatário ou autenticação |
| **Emocional** | Sentir que "não preciso entender a ferramenta"; segurança de que o envio foi disparado corretamente; não ter medo de errar por ser usuário esporádico |
| **Social** | Parecer profissional e ágil para quem vai assinar (cliente, parceiro, fornecedor) |

### O que ela espera fazer (tarefas)
1. Anexar o documento (arquivo solto ou texto livre).
2. Ter os signatários e a ordem de assinatura reconhecidos a partir do documento.
3. Corrigir ou completar só o que a IA não resolveu.
4. Aceitar a autenticação padrão sem decidir nada.
5. Revisar um resumo único.
6. Disparar o envio.

### O que ela espera alcançar (resultados desejados)
- **Rapidez:** do anexo ao envio com o menor número de passos possível. Benchmark de referência do projeto: envio simples em 4 cliques (Docusign 6, ZapSign 7).
- **Zero retrabalho:** nada para refazer depois do envio.
- **Zero aprendizado:** a jornada não exige conhecer conceitos como envelope, documento, ordem ou autenticação.
- **Controle sob demanda:** consegue alterar qualquer coisa, mas nada é imposto.
- **Confirmação clara** de que o envio foi disparado e de que o prazo começou a contar.

### Critérios de sucesso **[Hipótese]**
- Tempo do anexo ao "Enviar" (comparar com a mediana atual de setup).
- Nº de perguntas feitas pelo agente por jornada (meta: 0 no caminho feliz, 1 nas exceções 3B).
- Taxa de aceitação do resumo sem edição.
- Taxa de retorno aos nós de edição após o resumo.

---

## 3. Artefatos

### Inputs (o que a persona insere)

| Artefato | Quando | Observação |
| --- | --- | --- |
| **Documento (arquivo)** | Nó 1 | Único input obrigatório. Um documento por vez. |
| **Texto livre / instrução no campo de anexo** | Nó 1 | Só o campo de anexo/texto livre fica exposto. |
| **Resposta conversacional com quem assina** | Nó 3B | Só quando a IA não achou partes no documento. Nome + e-mail. |
| **Edições pontuais** | Nós 3A, 4 e 5 | Signatário, ordem, autenticação, configurações, documento. |
| **Confirmação ("Enviar")** | Nó 5 | Ação final, um botão. |

Pré-condição: permissão de leitura do documento pela IA **já resolvida no onboarding**, nunca pedida no meio do fluxo (decisão travada).

### Outputs (o que a persona quer receber)

| Output | Nó | Descrição |
| --- | --- | --- |
| **Signatários sugeridos** | 3A | Lista editável com ordem de assinatura, "editar" por linha |
| **Autenticação aplicada** | 4 | Token por e-mail, visível só como uma linha no resumo |
| **Resumo revisável** | 5 | Tela única: documento + signatários + autenticação, com um botão "Enviar" |
| **Confirmação de envio** | 6 | Mensagem de sucesso, com início da contagem de prazo |
| **Mensagem aos signatários** | 6 | Texto gerado pelo Click.AI (post-it: "MSG feita pela Click.AI") |

### Configurações assumidas pela IA (post-it "podemos configurar")
- Autenticação, aprendida por lógica de identificação e sugestão a partir do documento (qualificação costuma estar no documento).
- Mensagem ao signatário.
- Configurações padrão, **a não ser que a IA identifique alguma informação no documento**.
- Observador: fica para o futuro (ou próximas personas).

### O que a persona **pode querer alterar** (post-it)
Signatário, autenticação, configurações, documento. Todas as edições são sob demanda e não bifurcam a jornada.

---

## 4. Princípios que governam a jornada

- A superfície exposta é o mínimo necessário em cada nó. O que a IA resolve silenciosamente não aparece.
- Permissão de leitura é pedida antes do fluxo, não durante.
- Editar nunca cria uma jornada paralela: o usuário volta ao nó específico e segue.
- Ponto de partida: usuário de primeiro uso "pode ter a magia da IA"; usuário recorrente se beneficia do aprendizado de dados. O sistema que recebe o input e chama o fluxo não é necessariamente IA.
- Sem chips ou botões de intenção fixos na landing.

---

## 5. Jornada feliz

Documento com partes claras, autenticação padrão aceita, resumo confirmado.

| # | Nó | O que a persona faz | O que o agente faz | O que a persona vê |
| --- | --- | --- | --- | --- |
| 1 | Documento anexado | Solta o arquivo | Nada ainda | Só o campo de anexo/texto livre |
| 2 | IA lê o documento | Nada | Extrai nomes, e-mails e papéis | Nada (processamento silencioso) |
| 3A | Signatários sugeridos | Confere a lista; aceita | Monta signatários + ordem | Lista editável, "editar" por linha |
| 4 | Autenticação padrão | Nada | Aplica token por e-mail | Uma linha no resumo, sem pergunta |
| 5 | Resumo revisável | Confirma | Compila tudo | Tela única com botão "Enviar" |
| 6 | Envio disparado | Nada | Dispara e inicia contagem de prazo | Confirmação de sucesso |

**Interações mínimas do caminho feliz:** anexar, aceitar a lista, enviar.

```
Anexo → IA lê → achou partes → lista aceita → auth padrão → resumo → Enviar → sucesso
```

---

## 6. Jornadas de exceção

### 6.1 Exceções previstas na árvore de decisão

| ID | Exceção | Gatilho | Comportamento | Retorno |
| --- | --- | --- | --- | --- |
| **E1** | **IA não achou partes / documento incompleto** (nó 3B) | Ausência de partes identificáveis | Agente reconhece que precisa de input humano e faz **uma pergunta conversacional** ("quem assina?") | Resposta recebida → converge para o nó 4 |
| **E2** | **Quer editar signatários** (3A) | Clica "editar" na linha, ou pede alteração | Permanece no mesmo nó, edita nome, e-mail, ordem | Volta à lista e segue |
| **E3** | **Quer editar autenticação** (4) | Clica "editar" na linha de autenticação | Abre opções de autenticação **sem bifurcar** a jornada | Volta ao resumo |
| **E4** | **Quer editar a partir do resumo** (5) | Pede mudança na tela de revisão | Retorna ao **nó específico** (3A/3B ou 4) | Volta ao resumo depois da edição |

### 6.2 Exceções já especificadas no projeto

| ID | Exceção | Comportamento |
| --- | --- | --- |
| **E5** | **Dado de signatário incompleto** (nome achado, e-mail ausente) | Tratado como exceção nos três canais; o agente pede apenas o dado faltante, sem refazer a lista |
| **E6** | **Alterar configurações** durante a revisão | Acionada por mensagem (não por timeout); a persona pede e a IA ajusta, sem abrir uma tela nova |
| **E7** | **Editar signatários em chat** | Edição e reconfirmação ocorrem em **um único turno conversacional**. Nomenclatura do nó ainda pendente de confirmação. |

### 6.3 Exceções que o mapa ainda não cobre **[Hipótese]**

Candidatas para entrar na árvore. Nenhuma foi validada.

| ID | Cenário | Pergunta de design em aberto |
| --- | --- | --- |
| **E8** | **Alterar o documento** (post-it "alterar doc") | Troca de arquivo após a leitura: a IA relê tudo e descarta signatários já editados, ou preserva? |
| **E9** | **Arquivo ilegível** (scan ruim, protegido por senha, formato não suportado) | Pede outro arquivo ou segue para 3B? |
| **E10** | **Documento com vários possíveis signatários** (muitas partes citadas, só algumas assinam) | A IA sugere todas, e a persona remove, ou pergunta antes? |
| **E11** | **Qualificação do signatário exigida no documento, mas não visível para ele** (post-it "qualificação… pro signatário não é visível") | Como tratar quando o dado essencial ao fluxo está no documento e o signatário não o vê? |
| **E12** | **IA extrai errado com confiança alta** | Como a persona percebe o erro se a lista aparece "pronta"? Risco de aceitação cega. |
| **E13** | **Falha de entrega / erro no disparo** | Mensagem de erro, retry e preservação do estado |
| **E14** | **Persona abandona no meio** | Estado fica salvo? Retoma de onde parou? |
| **E15** | **Persona sem permissão de leitura concedida** | Hoje a decisão é resolver no onboarding; falta definir o que acontece se ela foi pulada |

---

## 7. Mapa das jornadas

```
                         ┌─────────────── E3 editar auth ───────────────┐
                         │                                               │
[1 Anexo] → [2 IA lê] ─┬→ [3A Signatários] ──→ [4 Auth padrão] ──→ [5 Resumo] ──→ [6 Envio]
                       │        ↑ E2 edita          ↑                  │
                       │                            │                  │ E4 quer editar
                       └→ [3B Pergunta quem assina] ┘                  └→ volta ao nó 3A/3B/4
                              (E1)
```

---

## 8. Pontos em aberto

- Lista real de métodos de autenticação disponíveis para o nó 4 (depende de confirmação de produto).
- Nome do módulo de IA (IA, Contract Intelligence ou Click Intelligence): decisão de Marcelo e Mariana.
- A árvore travada no Miro ainda precisa refletir a fusão dos nós 3A-EDIT e 4-EDIT em um único turno.
- Persona e números vêm de estudo preliminar (dez/25), com necessidade de aprofundamento antes de tratar como validado.
