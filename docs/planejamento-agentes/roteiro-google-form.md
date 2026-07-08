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
