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

## 10. Como calcular o veredito geral

As categorias 1-9 produzem vereditos individuais (baixo/médio/alto). Esta
seção define como agregá-los no "Nível de risco geral" e na recomendação do
Resumo Executivo (Seção 1 do Documento de Visibilidade).

**Risco geral:**

- **ALTO** — se qualquer categoria individual for ALTO **e** não houver
  mitigação viável identificada na conversa (ex: risco jurídico/PI sem
  contrato revisável, ou segurança da informação sem resposta clara sobre
  LGPD/retenção de dados)
- **MÉDIO** — se houver 1 ou mais categorias ALTO com mitigação clara
  identificada, ou 2 ou mais categorias MÉDIO
- **BAIXO** — nos demais casos

**Recomendação (veredito da Seção 1):**

- Risco geral **ALTO** → "precisa mais discovery" — nunca gerar
  automaticamente "não recomendado"; essa conclusão fica sempre a critério
  humano, não do processo
- Risco geral **MÉDIO** → "recomendado construir, com plano de mitigação"
- Risco geral **BAIXO** → "recomendado construir"
