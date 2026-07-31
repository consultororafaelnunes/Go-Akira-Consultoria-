# Mapeamento GTM Stack → Agente Comercial GoAkira

**Data:** 30/07/2026
**Fonte de referência:** *AI GTM Prompt Stack — 50 Workflows Claude-Native* (Brian Bittencourt / WOBA) — [Notion público](https://wobabr.notion.site/AI-GTM-Prompt-Stack-50-Workflows-Claude-Native-para-Go-To-Market-3826bf909fc98142b945c50b5ebe74e5)
**Objetivo:** traduzir o funil GTM (afinado para SaaS B2B) para o modelo de negócio da GoAkira e escopar o MVP do Agente Comercial (dono: Rafael + Daniel; janela ago–out/2026).

---

## Frame correto do modelo de negócio

A GoAkira **não vende franquia**. Ela vende **consultoria de modelagem de negócio e formatação do modelo de franquia** para o **franqueador** — que, depois de formatado, é quem vende as franquias.

Consequências para o mapeamento:

- **Produto vendido** = contrato de consultoria (não uma franquia, não um SaaS).
- **ICP** = empresa candidata a se tornar franqueadora.
- **Pós-venda** = o próprio pipeline consultivo BP → Jurídico → Manuais que a GoAkira já executa (e que o Agente de Relatórios já acompanha).

---

## Tradução dos 7 estágios

| Estágio (original SaaS) | Tradução GoAkira (venda de consultoria) | Veredito |
|---|---|---|
| **1. ICP & Research** | ICP = empresa franqueável: operação própria validada, marca, margem que suporta royalties, processos padronizáveis, replicabilidade. Anti-ICP = negócio imaturo / não replicável. Personas = sócio-fundador / diretor de expansão. Battlecard = outras consultorias de franchising. | Reaproveita (reescreve firmografia + fonte de dados) |
| **2. Prospecting & Lead Gen** | Leads de empresas em expansão: abriu 2ª/3ª unidade, recebeu "quero abrir igual à sua", saturação geográfica, busca de capital para expansão. Enriquecimento e listas. | Reaproveita (reescreve integrações) |
| **3. Qualification & Scoring** | Scoring = **diagnóstico de franqueabilidade** (a empresa está pronta para virar franqueadora?). Dupla função: qualifica o lead **e** já é um entregável consultivo. | ⭐ Maior aderência |
| **4. Outreach & Engagement** | Sequências / cold e-mail / follow-up para prospects franqueadores. | Reaproveita (**envio** por SMTP próprio; **rascunho** pode usar Gmail MCP) |
| **5. Nurture & Content** | Nutrir empresa que ainda não está pronta (precisa amadurecer a operação antes). Conteúdo educativo "como franquear seu negócio"; cases de franqueadores formatados pela GoAkira. | Reaproveita (ciclo longo é a norma) |
| **6. Close & Negotiation** | Proposta de consultoria personalizada; ROI = payback da estruturação da franquia para o cliente; negociação; forecast de fechamento de contratos. | Reaproveita (reframe métricas SaaS → contrato consultivo) |
| **7. Expansion & Retention** | Pós-venda = pipeline BP → Jurídico → Manuais já existente. Upsell de fases; saúde do projeto; churn = cliente que trava na formatação; QBR = revisão com o cliente. | Reaproveita — **conecta ao Agente de Relatórios atual** |

---

## Três insights do cruzamento

1. **Estágio 3 é o coração.** "Scoring de qualificação" e "diagnóstico de franqueabilidade" são a mesma coisa neste modelo. Um prompt que avalia se a empresa está pronta para franquear serve ao comercial (qualificar lead) e ao consultivo (primeiro entregável). Duplo valor → ponto de partida do MVP.

2. **As transcrições já existem.** O stack de referência assume **Granola** para transcrever calls — ferramenta que a GoAkira **não usa**. A fonte equivalente aqui é o **Drive (Meet Recordings)**, onde as reuniões já são gravadas e transcritas. Ou seja: onde o stack diz "Granola", leia "Drive/Meet". A etapa "leia a transcrição da call" mapeia direto para um ativo existente — não é ferramenta nova.

3. **O Estágio 7 fecha o loop com o que já roda.** Retention/Expansion, aqui, É o acompanhamento das fases que o Agente de Relatórios já produz. O Agente Comercial não reconstrói isso — ele entrega o cliente fechado ao pipeline existente. Arquitetura circular, igual à do próprio stack.

---

## O que reescrever / descartar

- **Fonte de dados** (em todo prompt): `HubSpot → CRM da GoAkira` (validar: RD Station?); `Granola → Drive/Meet Recordings`; `Notion → Google Drive`; `Slack → e-mail/SMTP`.
- **Métricas SaaS** (ARR, ACV, pipeline coverage) → termos de contrato consultivo (valor do contrato, ciclo de venda consultiva, taxa de conversão diagnóstico → contrato).
- **Descartar / baixar prioridade:** automação de LinkedIn outreach (menos aderente à venda consultiva B2B de ticket alto e relacionamento).

---

## Estágio 2 — opções de ferramenta de prospecção

Dois materiais gratuitos avaliados (30/07/2026) como possíveis feeders do Estágio 2. Ambos são ferramentas de prospecção; nenhum é "adotar como está".

### 1. Agente de Prospecção Ativa — NexusMind
[Notion](https://app.notion.com/p/Agente-de-Prospec-o-Ativa-com-IA-3350b3d271e280089380d9bcc46a1b7d) · material gratuito, com JSON do workflow para download.

- **Stack:** N8N + Apify (raspa Google Maps/LinkedIn) → OpenAI (enriquece) → Perplexity (acha o decisor) → Tavily (perfil LinkedIn) → AnyMail Finder (e-mail) → Google Sheets.
- **Saída:** planilha com empresa + decisor + LinkedIn + e-mail profissional, pronta para abordagem.
- **Custo:** ~US$ 60–100/mês (5 APIs pagas). Usa **OpenAI, não Claude**, e roda em **N8N** (plataforma que a GoAkira não opera).
- **Veredito:** o *mecanismo* é bom (raspa → acha decisor → e-mail), mas o stack não encaixa. **Reconstruir Claude-native** (Claude + Drive + scheduled tasks que já temos, somando só Apify para scraping + uma API de e-mail) em vez de importar o N8N.

### 2. Máquina de Prospecção no Instagram — Autta.IA
[Notion](https://app.notion.com/p/A-M-quina-de-Prospec-o-no-Instagram-3a4d6130aae3805396c6e38c4f0a726e) · material gratuito, entregue como **Claude Skill** (`instagram-likes-scraper.skill`) + Apify.

- **O que faz:** raspa quem interagiu/curtiu um post → lista de leads qualificados + mensagem de abordagem já escrita.
- **Fit de arquitetura:** skill Claude nativa → atrito baixíssimo, encaixa direto no stack.
- **Veredito:** sinal "curtiu um post" é **fraco** para venda consultiva B2B de ticket alto. Só faz sentido **se** entrar a frente de inbound por conteúdo (postar "como franquear seu negócio" e colher quem engaja — auto-seleção por interesse). Baixa prioridade; guardar como opção.

### Ressalvas transversais aos dois

- **Qualidade do sinal:** nenhum raspa por *franqueabilidade*. Google Maps dá empresas por categoria; Instagram dá engajadores. O ICP refinado (operação validada, 2–3 unidades, pronta para franquear) não é capturado — eles geram **volume de topo de funil**; a qualificação real continua sendo o **Estágio 3** (diagnóstico de franqueabilidade).
- **⚠️ LGPD / jurídico:** ambos raspam **dados pessoais** (e-mails, LinkedIn, interações) para abordagem fria. Para uma consultoria que vende rigor jurídico e de formatação, isso exige **aval do Marco (jurídico)** e base legal definida **antes** de virar agente de produção. Não combina com o posicionamento se feito sem base.

**Conclusão do Estágio 2 (atualizada com MCPs — ver seção abaixo):** reaproveitar o *padrão* do NexusMind, mas reconstruído Claude-native usando **MCPs nativos em vez de N8N + OpenAI**. Fluxo recomendado:

```
Apify (raspa por segmento) → KipFlow (enriquece CNPJ: porte, sócios, faturamento, decisor)
   → filtra sinal de franqueabilidade → planilha/Drive → Estágio 3
```

O **KipFlow** (enriquecimento de CNPJ brasileiro) resolve o "sinal fraco" apontado acima: substitui Perplexity/AnyMail e já traz porte/faturamento/decisor, aproximando o feeder do ICP real. Tudo condicionado a green-light de LGPD. Instagram só se houver estratégia de inbound por conteúdo.

---

## MCPs avaliados para os agentes GoAkira

Avaliação (30/07/2026) do guia [18 MCPs para Empresas de Serviços — Playbook Lab](https://playbooklab.notion.site/18-MCPs-para-Empresas-de-Servi-os-o-guia-de-instala-o-3a5f8d62b79a81268860e5e6e9a6f802), cruzada com os nossos agentes (Relatórios atual + Comercial planejado + pipeline consultivo). MCP = conector nativo do Claude (Anthropic), instalado por 1 clique / URL / config local.

### 🟢 Tier 1 — alto valor, encaixe claro

| MCP | Por que serve aos nossos agentes |
|---|---|
| **KipFlow** ⭐ | Enriquece **CNPJ brasileiro** (sócios, faturamento, decisores, contato). Resolve o sinal fraco da prospecção: filtra porte/faturamento = sinais de franqueabilidade. Núcleo do Estágio 2/3 do Agente Comercial. `platform.kipflow.io → Integrações/MCP` |
| **Apify** | Motor de scraping nativo (Google Maps/LinkedIn/Instagram). Forma Claude-native de fazer a prospecção que os materiais faziam via N8N. Combina com KipFlow. *Ressalva LGPD.* Nativo ou `https://mcp.apify.com` |
| **Firecrawl** | Extrai o site do prospect em texto limpo → agente lê a operação (unidades, presença) para o diagnóstico de franqueabilidade; também análise de concorrentes (Estágio 1). `https://mcp.firecrawl.dev/v2/mcp` |
| **Google Agenda** | Nativo. Agendamento de follow-ups, QBRs, reuniões — Comercial + acompanhamento de fases |
| **GitHub** | Nossos agentes são um repositório git. Gerir issues/versões do código pelo Claude = ganho de dev/ops. Nativo |

### 🟡 Tier 2 — situacional (depende de decisão nossa)

| MCP | Condição |
|---|---|
| **Pipedrive** | Só se for o CRM oficial. **Pendência aberta:** qual é o CRM da GoAkira? (confirmar antes — ver "A definir" no MVP) |
| **tl;dv** | Transcreve reuniões com destaques. **Duplica** as transcrições do Meet via Drive que já usamos — só trocar se for comprovadamente melhor |
| **Gmail** | Rascunha e-mails (não envia). Hoje enviamos por SMTP próprio → ganho marginal |
| **Supabase** | Hoje JSON + Drive. Faz sentido no futuro, se a migração VPS levar o estado para um banco |
| **Browserbase / n8n** | Só se entrarmos em automação de portais (Browserbase) ou adotarmos N8N (n8n — recomendado **evitar**) |

### 🔴 Tier 3 — baixo encaixe hoje

**Notion, ClickUp, Tally, Slack, Brevo, WhatsApp, Excalidraw** — duplicam ferramenta já usada (Tally↔Google Forms, Notion↔Drive), pressupõem stack que não rodamos (Slack, ClickUp), ou trazem peso de LGPD/infra sem retorno claro agora (WhatsApp, Brevo).

### Stack mínimo sugerido para começar

**KipFlow + Apify + Firecrawl + Google Agenda** — destravam o Agente Comercial sem infra nova (só conectores). GitHub à parte, para dev/ops.

---

## Recomendação de MVP do Agente Comercial

Só o Estágio 1 do stack de referência está publicado hoje (os demais são liberados semanalmente). Isso não bloqueia a GoAkira — o valor está na estrutura, e escrevemos os prompts adaptados internamente.

**MVP enxuto de maior alavancagem (ago–out/2026):**

```
Estágio 1 (ICP de empresa franqueável)
        ↓
Estágio 3 (diagnóstico de franqueabilidade)   ← núcleo, duplo valor
        ↓
Estágio 6 (proposta de consultoria)
        ↓
Estágio 7 = handoff para o pipeline de relatórios já existente
```

- **Fonte:** transcrições comerciais no Drive + CRM.
- **Entrega:** cliente fechado passa ao pipeline BP → Jurídico → Manuais (sem reconstruir acompanhamento).
- **A definir internamente:** qual é o CRM oficial (RD Station?) e o formato do output do diagnóstico (doc no Drive, no padrão dos briefings atuais).

---

## Primeiro artefato concreto — Prompt do Estágio 3 (adaptado)

Diagnóstico de franqueabilidade, Claude-native, fonte = transcrições do Drive + dados do cliente. Substituir variáveis `[ ]` antes de rodar.

### Variáveis

- `[EMPRESA]` = nome da empresa candidata (ex: "Rede X de alimentação saudável")
- `[SEGMENTO]` = setor de atuação (ex: "food service — açaí")
- `[N_UNIDADES]` = nº de unidades próprias hoje (ex: "3 próprias")
- `[TEMPO_OPERACAO]` = há quanto tempo opera (ex: "6 anos")
- `[TICKET_TITULO]` = ticket médio / faturamento por unidade, se conhecido

### Prompt Claude-Native

```
Aja como consultor sênior de franchising, especialista em avaliar a
FRANQUEABILIDADE de um negócio — ou seja, se a empresa está pronta para
ser formatada como franqueadora.

PRIMEIRO: Leia o material disponível para fundamentar a análise em evidência.
- Leia as transcrições das reuniões comerciais desta empresa no Drive
  (pasta Meet Recordings; filtro pelo nome do cliente [EMPRESA]).
- Extraia falas do cliente sobre: operação, padronização, margem, marca,
  motivação para expandir, expectativa de prazo e investimento.

Contexto da empresa:
- Empresa: [EMPRESA]
- Segmento: [SEGMENTO]
- Unidades próprias hoje: [N_UNIDADES]
- Tempo de operação: [TEMPO_OPERACAO]
- Ticket/faturamento por unidade: [TICKET_TITULO]

Com base nas transcrições + contexto, produza um DIAGNÓSTICO DE FRANQUEABILIDADE
avaliando cada dimensão de 0 a 10, com justificativa apoiada em evidência:

1. **Operação validada e lucrativa** — a unidade própria já dá resultado
   consistente? Há margem que sustente royalties + taxa de franquia?
2. **Padronização e replicabilidade** — processos documentados? A operação
   depende do fundador ou roda sozinha? Dá para ensinar a um franqueado?
3. **Força de marca** — a marca tem reconhecimento/apelo que justifique
   alguém pagar para operá-la?
4. **Maturidade de gestão** — a empresa tem gente e sistemas para dar suporte
   a uma rede (treinamento, supervisão de campo)?
5. **Demanda por expansão** — há sinais reais de interesse de terceiros em
   abrir unidades? (pedidos espontâneos, saturação do modelo próprio)
6. **Saúde financeira para o projeto** — a empresa tem fôlego para o
   investimento de formatação (BP, jurídico, manuais)?

DEPOIS, entregue:
- **Score geral de franqueabilidade** (média ponderada) e classificação:
  Pronta / Pronta com ajustes / Ainda não (nutrir).
- **Pontos fortes** que aceleram a formatação.
- **Lacunas críticas** que precisam ser resolvidas ANTES ou DURANTE a
  consultoria — com o que a GoAkira pode fazer em cada uma.
- **Recomendação comercial**: seguir para proposta agora, ou nutrir e
  reavaliar em X meses.

REGRA ANTI-INVENÇÃO: use apenas o que está nas transcrições e no contexto.
Onde faltar informação para avaliar uma dimensão, marque explicitamente
[A CONFIRMAR COM O CLIENTE] em vez de assumir. Indique sempre o que vem de
evidência (transcrição) vs. inferência.

Formato: relatório estruturado por dimensão + quadro-resumo com os scores.
```

**Output esperado:** diagnóstico de franqueabilidade fundamentado nas reuniões, com score, lacunas e recomendação comercial (seguir para proposta ou nutrir) — no mesmo padrão anti-invenção dos briefings atuais.

**Automação:** rodar quando uma reunião comercial de um novo prospect for transcrita (gatilho por evento, análogo ao pipeline de atas). Output salvo no Drive no padrão dos briefings.
