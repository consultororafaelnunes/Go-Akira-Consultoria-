# Processo de Planejamento de Novos Agentes GoAkira — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar os três artefatos de texto que operacionalizam o processo de planejamento de novos agentes de IA da GoAkira, definido em `docs/superpowers/specs/2026-07-08-planejamento-agentes-goakira-design.md`: o rulebook de riscos, o roteiro do Google Form de briefing, e o template do Documento de Visibilidade.

**Architecture:** Não há código de produção — são três arquivos markdown independentes, cada um servindo uma etapa do fluxo (Form → rulebook → documento de saída). Cada tarefa cria um arquivo completo e o commita isoladamente, sem dependência de execução entre eles.

**Tech Stack:** Markdown puro. Nenhuma dependência de runtime, biblioteca ou infraestrutura.

---

### Task 1: Rulebook de riscos

**Files:**
- Create: `docs/planejamento-agentes/rulebook.md`

- [ ] **Step 1: Criar o arquivo com as 9 categorias completas**

Conteúdo completo do arquivo:

```markdown
# Rulebook de Riscos — Planejamento de Novos Agentes GoAkira

Este documento é usado junto com as respostas do Google Form de briefing (ver
`docs/planejamento-agentes/roteiro-google-form.md`) numa conversa com o Claude
para gerar o Documento de Visibilidade de um novo agente proposto.

Cada categoria segue o formato: **gatilho** (o que nas respostas do Form ativa
essa categoria) → **regra** (o que concluir/exigir) → **recomendação padrão**.

O Documento de Visibilidade final não lista as 9 categorias sempre — apenas as
que tiverem gatilho ativado pelas respostas do Form daquele agente específico.

---

## 1. Dependência de infraestrutura

- **Gatilho:** resposta "pode rodar 100% na nuvem?" = não, ou "depende de
  computador/pessoa específica" = sim
- **Regra:** marcar risco ALTO de confiabilidade de agendamento
- **Recomendação:** hospedar em nuvem (Managed Agents ou VPS) em vez de
  notebook/computador local desde o início do projeto
- **Lição-origem:** falha dos Task Scheduler do Agente de Relatórios por
  configuração de bateria/sleep — o agendamento simplesmente não disparava
  quando o notebook estava na bateria

## 2. Deduplicação de dados

- **Gatilho:** o agente processa itens que podem reaparecer em execuções
  consecutivas (ex: janelas de tempo sobrepostas, reprocessamento de fontes)
- **Regra:** exigir estratégia de deduplicação por identificador persistente,
  válida entre execuções — não apenas dentro de uma única execução
- **Recomendação:** manter um registro histórico de IDs já processados
  (arquivo, tabela ou similar) consultado antes de processar qualquer item novo
- **Lição-origem:** duplicação cross-day de reuniões no Agente de Relatórios —
  a mesma transcrição era resumida duas vezes quando a janela de busca de 24h
  se sobrepunha entre execuções

## 3. Atribuição de responsável

- **Gatilho:** mais de uma pessoa/área pode ser dona do mesmo item processado,
  ou a responsabilidade muda conforme a fase/etapa do processo
- **Regra:** exigir modelagem de responsável como algo dinâmico, nunca uma
  tabela estática fixa por cliente/item
- **Recomendação:** usar o sinal real de origem do dado (quem de fato gerou/
  processou aquele item) como fonte de verdade, com fallback para uma tabela
  estática apenas quando não houver sinal direto
- **Lição-origem:** erros recorrentes de atribuição BP/Jurídico/Manuais no
  Agente de Relatórios — a tabela estática de consultores não sabia refletir
  mudança de fase nem projetos com responsabilidade conjunta

## 4. Filtragem por data/período

- **Gatilho:** o agente gera relatórios agregados por período (diário,
  semanal, mensal)
- **Regra:** o filtro de período deve sempre usar a data real do evento
  reportado, nunca a data em que o arquivo/registro foi processado pelo
  pipeline
- **Recomendação:** extrair e armazenar a data real do evento em campo
  próprio, e filtrar por esse campo — nunca pelo nome do arquivo/lote de
  processamento
- **Lição-origem:** vazamento de reuniões de semanas anteriores no relatório
  semanal do Agente de Relatórios, causado por filtrar pela data do arquivo
  `summaries_*.json` em vez da data real da reunião

## 5. Credenciais e dados sensíveis

- **Gatilho:** resposta "dados incluem informação sensível" = sim
- **Regra:** exigir definição explícita de onde e como as credenciais serão
  armazenadas antes de aprovar o início da construção — nunca em texto puro
  dentro do repositório de código
- **Recomendação:** usar variáveis de ambiente / cofre de segredos, com
  `.gitignore` cobrindo qualquer arquivo de credencial local
- **Lição-origem:** migração do Agente de Relatórios para nuvem foi
  explicitamente pausada até haver decisão clara sobre gestão de credenciais

## 6. Confiabilidade de entrega

- **Gatilho:** a saída do agente é enviada automaticamente, sem revisão
  humana antes do envio
- **Regra:** exigir um modo de execução manual de fallback, e teste do
  caminho de envio fora do contexto de execução agendada automática
- **Recomendação:** validar o envio (ex: SMTP, webhook, API de terceiros)
  rodando manualmente antes de confiar apenas na execução agendada
- **Lição-origem:** hang do envio de email por SMTP quando o Agente de
  Relatórios rodava sob o Task Scheduler em contexto de logon S4U — o mesmo
  código funcionava normalmente quando executado manualmente

## 7. Risco financeiro

- **Gatilho:** não existe orçamento aprovado para o agente, ou o custo
  depende de volume variável (ex: cobrança por token, por execução, por
  chamada de API)
- **Regra:** exigir estimativa de custo em dois cenários — volume atual e 3x
  o volume atual — antes de aprovar a construção
- **Recomendação:** identificar um dono orçamentário explícito responsável
  por aprovar aumento de custo se o volume crescer além do estimado
- **Lição-origem:** comparação de custo entre Anthropic Managed Agents
  (~US$0,08/hora de sessão ativa) e uma VPS de custo fixo, feita antes de
  propor a migração do Agente de Relatórios para a diretoria

## 8. Risco jurídico/contratual (inclui Propriedade Intelectual)

- **Gatilho:** os dados envolvem clientes finais ou terceiros da GoAkira, ou
  o agente gera conteúdo/análise a partir de dados de cliente final, ou toma
  decisões que afetam terceiros
- **Regra:** marcar risco ALTO — exigir checagem prévia se o contrato com o
  cliente final permite uso de IA sobre os dados dele; verificar quem detém a
  propriedade intelectual do output gerado (GoAkira, cliente, ou ambíguo no
  contrato vigente)
- **Recomendação:** sinalizar necessidade de disclaimer explícito quando a
  saída do agente influenciar diretamente uma decisão de negócio do cliente;
  não iniciar construção sem essa checagem contratual feita
- **Lição-origem:** categoria nova — o Agente de Relatórios já toca dados de
  clientes indiretamente (conteúdo de reuniões), mas o risco de propriedade
  intelectual e cobertura contratual nunca foi formalmente endereçado

## 9. Segurança da informação

- **Gatilho:** "dados incluem informação sensível" = sim E/OU "dados enviados
  a serviço externo de IA/nuvem" = sim
- **Regra:** exigir resposta clara para todos os itens a seguir antes de
  aprovar a construção: (a) onde credenciais/segredos ficam armazenados;
  (b) se há LGPD aplicável aos dados em questão; (c) se os dados são
  retidos/logados por algum serviço externo, e por quanto tempo
- **Recomendação:** marcar risco ALTO se qualquer um dos três itens acima não
  tiver resposta definida no momento da avaliação
- **Lição-origem:** generalização do cuidado com `.gitignore`/segredos do
  Agente de Relatórios para qualquer dado sensível processado por um agente,
  não apenas as credenciais do próprio agente
```

- [ ] **Step 2: Revisar o arquivo criado**

Abra `docs/planejamento-agentes/rulebook.md` e confirme visualmente que as 9
seções numeradas estão presentes e que nenhuma ficou incompleta.

- [ ] **Step 3: Commit**

```bash
git add docs/planejamento-agentes/rulebook.md
git commit -m "docs: adiciona rulebook de riscos para planejamento de novos agentes"
```

---

### Task 2: Roteiro do Google Form de briefing

**Files:**
- Create: `docs/planejamento-agentes/roteiro-google-form.md`

- [ ] **Step 1: Criar o arquivo com o texto pronto para colar no Google Forms**

Conteúdo completo do arquivo:

```markdown
# Roteiro do Google Form — Briefing de Novo Agente de IA

Este texto está pronto para ser colado diretamente na criação do formulário em
forms.google.com. Cada `##` é uma seção do Form; cada item de lista é uma
pergunta. Sugestão de tipo de campo ao lado de cada pergunta.

## Seção 1 — Contexto e Objetivo

- Qual área está propondo o agente? (resposta curta)
- Que problema/dor esse agente resolveria? (parágrafo)
- Como esse processo é feito hoje (manual, planilha, outro sistema)? (parágrafo)
- Quem seria o "dono" do agente depois de pronto, responsável por acompanhar
  e manter? (resposta curta)

## Seção 2 — Dados e Fontes

- Que dados o agente precisa ler? Ex: emails, planilhas, documentos, sistema
  X. (parágrafo)
- Onde esses dados vivem hoje? Ex: Drive, Gmail, sistema interno, papel.
  (resposta curta)
- Esses dados incluem informação sensível (financeira, contratual, pessoal
  de terceiros)? (sim/não + campo de detalhe)
- Esses dados envolvem informações de clientes finais da GoAkira ou
  terceiros, e não apenas dados internos? (sim/não + campo de detalhe)
- Esses dados seriam enviados a serviços externos de IA/nuvem (ex:
  Anthropic, Google)? Já existe cláusula contratual com o cliente que
  autorize isso? (parágrafo)
- O contrato com o cliente final trata da propriedade dos materiais/análises
  gerados a partir dos dados dele, inclusive por IA? (sim/não/não sei +
  campo de detalhe)

## Seção 3 — Frequência e Volume

- Com que frequência o agente precisa rodar? (múltipla escolha: diário /
  semanal / mensal / sob demanda / outro)
- Volume esperado — quantos itens/reuniões/documentos por execução?
  (resposta curta)
- Existe um horário ou prazo crítico para a execução? Ex: "precisa estar
  pronto até 9h". (resposta curta)

## Seção 4 — Saída Esperada

- Quem recebe o resultado? Cite pessoas e/ou cargos. (parágrafo)
- Em que formato? (múltipla escolha: email / documento / dashboard /
  planilha / outro)
- Precisa de aprovação humana antes de sair, ou pode ser automático?
  (múltipla escolha: sempre precisa de aprovação / pode ser automático /
  depende do caso)

## Seção 5 — Integrações e Dependências

- Precisa se conectar a algum sistema externo? Ex: Google Workspace,
  WhatsApp, ERP. (parágrafo)
- Depende de algum computador ou pessoa específica estar ligado/disponível,
  ou pode rodar 100% na nuvem? (múltipla escolha: pode rodar 100% na nuvem /
  depende de computador ou pessoa específica / não sei)

## Seção 6 — Orçamento

- Existe orçamento aprovado para custos recorrentes, como API e
  hospedagem? (sim/não/não sei)
- Quem aprova aumento de custo se o volume crescer? (resposta curta)

## Seção 7 — Nível de Confiança Esperado

- O que acontece se o agente errar ou perder uma informação uma vez — é
  grave ou tolerável? (parágrafo)
- Precisa de rastreabilidade, ou seja, um histórico de tudo que foi
  processado? (sim/não)
```

- [ ] **Step 2: Revisar o arquivo criado**

Confirme que as 7 seções do spec estão todas presentes e que cada pergunta
tem uma sugestão de tipo de campo.

- [ ] **Step 3: Commit**

```bash
git add docs/planejamento-agentes/roteiro-google-form.md
git commit -m "docs: adiciona roteiro do Google Form de briefing de novos agentes"
```

---

### Task 3: Template do Documento de Visibilidade

**Files:**
- Create: `docs/planejamento-agentes/template-documento-visibilidade.md`

- [ ] **Step 1: Criar o arquivo com as 6 seções esqueletadas**

Este arquivo é um template reutilizável — os campos entre colchetes
(`[assim]`) são intencionalmente placeholders a serem preenchidos a cada novo
agente avaliado, não pendências deste plano.

Conteúdo completo do arquivo:

```markdown
# Documento de Visibilidade — [Nome do Agente Proposto]

Área solicitante: [nome da área]
Data da avaliação: [DD/MM/AAAA]
Avaliado por: [nome]

## 1. Resumo Executivo

- **Veredito:** [recomendado construir / precisa mais discovery / não
  recomendado agora]
- **Custo estimado:** [valor no volume atual] · [valor em 3x o volume atual]
- **Prazo estimado:** [ex: 2-3 semanas de construção]
- **Nível de risco geral:** [baixo / médio / alto]

## 2. Contexto do Pedido

- **Problema/dor:** [descrição]
- **Área solicitante:** [nome]
- **Processo atual:** [como é feito hoje]
- **Dono do agente:** [nome/cargo responsável por acompanhar e manter]

## 3. Arquitetura Sugerida

- **Fontes de dados:** [lista]
- **Motor de IA:** [modelo/abordagem sugerida]
- **Saída:** [formato e canal de entrega]
- **Agendamento/execução:** [nuvem / local / sob demanda, e por quê]

## 4. Riscos Mapeados

> Preencher apenas as categorias do rulebook (`docs/planejamento-agentes/rulebook.md`)
> cujo gatilho foi ativado pelas respostas do Form deste agente.

### [Nome da categoria de risco]

- **Veredito:** [baixo / médio / alto]
- **Justificativa:** [por que esse risco se aplica aqui]
- **Mitigação recomendada:** [ação concreta]

## 5. Checklist de Decisões Pendentes

- [ ] [Decisão pendente 1, ex: definir onde credenciais ficam armazenadas]
- [ ] [Decisão pendente 2, ex: confirmar cláusula contratual de PI com o
      cliente X]

## 6. Próximos Passos

1. [Passo recomendado 1]
2. [Passo recomendado 2]
3. [Passo recomendado 3]
```

- [ ] **Step 2: Revisar o arquivo criado**

Confirme que as 6 seções do spec estão presentes e que a nota sobre a Seção
4 (usar apenas categorias com gatilho ativo) está clara.

- [ ] **Step 3: Commit**

```bash
git add docs/planejamento-agentes/template-documento-visibilidade.md
git commit -m "docs: adiciona template do Documento de Visibilidade para novos agentes"
```

---

## Self-Review

**1. Cobertura do spec:**
- Fluxo geral → documentado no spec, não requer artefato próprio (Task N/A)
- Rulebook (9 categorias) → Task 1, todas as 9 presentes
- Roteiro do Google Form (7 seções) → Task 2, todas as 7 presentes
- Template do Documento de Visibilidade (6 seções) → Task 3, todas as 6
  presentes
- Estrutura do resumo PPTX → não gera artefato fixo, pois o spec define que é
  montado ad-hoc na conversa a partir do Documento de Visibilidade; não requer
  task própria
- Manutenção do processo → é uma prática operacional (editar o rulebook
  quando surgir lição nova), não um artefato a ser criado agora

**2. Placeholder scan:** os únicos colchetes `[assim]` estão dentro do
template da Task 3, que é intencionalmente reutilizável — cada instância do
Documento de Visibilidade real preenche esses campos. Nenhum step das tarefas
ficou com "TBD" ou instrução vaga.

**3. Consistência:** os nomes de arquivo referenciados entre tarefas
(`rulebook.md`, `roteiro-google-form.md`, `template-documento-visibilidade.md`)
são idênticos aos caminhos declarados em cada `Files:` e aos citados no spec
aprovado.
