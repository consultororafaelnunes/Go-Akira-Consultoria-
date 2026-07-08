# Processo de Planejamento para Novos Agentes de IA — GoAkira

Data: 2026-07-08
Status: aprovado para implementação (via `writing-plans`)

## Contexto

O Agente de Relatórios (pipeline de reuniões/atas construído nesta mesma base de código) revelou, ao longo de sua operação, uma série de riscos estruturais que só ficaram visíveis depois de causarem problemas reais: dependência de hardware local para agendamento, deduplicação de dados entre execuções, atribuição incorreta de responsáveis, filtragem de relatórios por data errada, e necessidade de decisão explícita sobre onde guardar credenciais antes de migrar para nuvem.

Este documento define um processo repetível para que **outras áreas da GoAkira** possam propor novos agentes de IA com visibilidade antecipada desses mesmos riscos — em vez de descobri-los em produção, como aconteceu aqui.

## Objetivo

Dar a qualquer área da GoAkira um caminho estruturado para: (1) descrever a ideia de um agente de IA em linguagem não-técnica, e (2) receber de volta um documento de visibilidade que aponte arquitetura sugerida, riscos mapeados por categoria, custo/prazo estimados e um checklist de decisões pendentes — antes de qualquer linha de código ser escrita.

## Fora de escopo (por ora)

- Automação completa (Form → documento sem intervenção humana). O motor é você + Claude numa conversa, guiados pelo rulebook — não um script.
- Interface web própria (tipo wizard PM3). O briefing usa Google Forms.
- Validação/aprovação formal em fluxo de workflow (ex: sistema de aprovação com múltiplas etapas). A decisão go/no-go continua sendo humana, fora da ferramenta.

## Fluxo geral

```
[Área tem ideia de agente]
        │
        ▼
[Área preenche Google Form de briefing]
        │
        ▼
[Respostas caem numa planilha Google Sheets]
        │
        ▼
[Você revisa as respostas, identifica lacunas/ambiguidades]
        │
        ▼
[Você leva as respostas + o rulebook.md para uma conversa com o Claude]
        │
        ▼
[Claude aplica as regras do rulebook + julgamento próprio,
 gera: Documento de Visibilidade (detalhado) + Resumo PPTX (executivo)]
        │
        ▼
[Você revisa, ajusta, e leva para decisão go/no-go
 com a área solicitante e/ou diretoria]
```

Pontos-chave:
- **Sem automação ponta a ponta.** O rulebook é o único artefato que precisa manutenção contínua — cada nova lição aprendida na operação vira uma entrada nova nele, não uma mudança de processo.
- **O Google Form é a única interface que a área-solicitante toca.** Tudo depois disso é interno (você + Claude).

## Estrutura do Google Form (briefing)

**1. Contexto e Objetivo**
- Qual área está propondo o agente?
- Que problema/dor esse agente resolveria? (texto livre)
- Como esse processo é feito hoje (manual, planilha, outro sistema)?
- Quem seria o "dono" do agente depois de pronto (responsável por acompanhar/manter)?

**2. Dados e Fontes**
- Que dados o agente precisa ler? (ex: emails, planilhas, documentos, sistema X)
- Onde esses dados vivem hoje (Drive, Gmail, sistema interno, papel)?
- Esses dados incluem informação sensível (financeira, contratual, pessoal de terceiros)?
- Esses dados envolvem informações de clientes finais da GoAkira ou terceiros (não apenas dados internos)?
- Esses dados seriam enviados a serviços externos de IA/nuvem (ex: Anthropic, Google)? Já existe cláusula contratual com o cliente que autorize isso?
- O contrato com o cliente final trata da propriedade dos materiais/análises gerados a partir dos dados dele (inclusive por IA)?

**3. Frequência e Volume**
- Com que frequência o agente precisa rodar (diário, semanal, sob demanda)?
- Volume esperado (quantos itens/reuniões/documentos por execução)?
- Existe um horário/prazo crítico para a execução (ex: "precisa estar pronto até 9h")?

**4. Saída Esperada**
- Quem recebe o resultado (pessoas, cargos)?
- Em que formato (email, documento, dashboard, planilha)?
- Precisa de aprovação humana antes de sair, ou pode ser automático?

**5. Integrações e Dependências**
- Precisa se conectar a algum sistema externo (Google Workspace, WhatsApp, ERP, etc.)?
- Depende de algum computador/pessoa específica estar ligado/disponível, ou pode rodar 100% na nuvem?

**6. Orçamento**
- Existe orçamento aprovado para custos recorrentes (API, hospedagem)?
- Quem aprova aumento de custo se o volume crescer?

**7. Nível de Confiança Esperado**
- O que acontece se o agente errar ou perder uma informação uma vez — é grave ou tolerável?
- Precisa de rastreabilidade (histórico de tudo que foi processado)?

## Estrutura do Rulebook (`docs/planejamento-agentes/rulebook.md`)

Documento markdown organizado por categoria de risco. Cada categoria segue o formato: **pergunta-gatilho do Form → regra de decisão → recomendação padrão**. É levado junto com as respostas do briefing para a conversa com o Claude que gera o Documento de Visibilidade.

**1. Dependência de infraestrutura**
- Gatilho: "pode rodar 100% na nuvem?" = não, ou "depende de computador específico" = sim
- Regra: risco ALTO de confiabilidade de agendamento; recomendar hospedagem em nuvem (Managed Agents/VPS) em vez de notebook local
- Lição-origem: falha dos Task Scheduler por bateria/sleep no Agente de Relatórios

**2. Deduplicação de dados**
- Gatilho: agente processa itens que podem aparecer mais de uma vez em execuções consecutivas (ex: janelas de tempo sobrepostas)
- Regra: exigir estratégia de dedup por ID persistente (não só "dentro da mesma execução")
- Lição-origem: duplicação cross-day de reuniões

**3. Atribuição de responsável**
- Gatilho: existe mais de uma pessoa/área que pode ser dona do mesmo item processado, ou a responsabilidade muda por fase/etapa
- Regra: exigir modelagem de responsável como algo dinâmico (não tabela estática fixa) — usar sinal real da origem do dado sempre que possível
- Lição-origem: erros de atribuição BP/Jurídico/Manuais

**4. Filtragem por data/período**
- Gatilho: agente gera relatórios por período (diário/semanal/mensal)
- Regra: filtro de período deve usar a data real do evento, não a data de processamento do arquivo
- Lição-origem: vazamento de reuniões fora da semana no relatório semanal

**5. Credenciais e dados sensíveis**
- Gatilho: "dados incluem informação sensível" = sim
- Regra: exigir definição explícita de onde/como credenciais são guardadas (nunca em texto no repositório) antes de aprovar construção
- Lição-origem: pausa da migração para nuvem até decisão de credenciais

**6. Confiabilidade de entrega**
- Gatilho: saída é enviada automaticamente sem revisão humana
- Regra: recomendar modo de execução manual de fallback, e teste do envio fora do contexto de tarefa agendada
- Lição-origem: hang do SMTP sob Task Scheduler (contexto S4U)

**7. Risco financeiro**
- Gatilho: não existe orçamento aprovado, ou custo depende de volume variável (ex: cobrança por token/execução)
- Regra: exigir estimativa de custo em 2 cenários (volume atual e 3x o volume) antes de aprovar; risco ALTO se não houver dono orçamentário definido
- Lição-origem: comparação de custo Managed Agents ($0,08/h) vs VPS feita antes de propor a migração para Patricia

**8. Risco jurídico/contratual (inclui Propriedade Intelectual)**
- Gatilho: dados envolvem clientes finais/terceiros, ou o agente gera conteúdo/análise a partir de dados de cliente final, ou toma decisões que afetam terceiros
- Regra: risco ALTO — exigir checagem prévia se o contrato com o cliente final permite uso de IA sobre os dados dele; verificar quem detém a propriedade intelectual do output gerado (GoAkira, cliente, ou ambíguo); sinalizar necessidade de disclaimer se a saída influencia decisão de negócio do cliente
- Lição-origem: nova categoria — o Agente de Relatórios já toca dados de clientes indiretamente (conteúdo das reuniões), mas o risco de PI/contrato nunca foi formalmente endereçado

**9. Segurança da informação**
- Gatilho: dados sensíveis = sim E/OU dados enviados a serviço externo = sim
- Regra: exigir definição explícita de onde credenciais/segredos ficam armazenados, se há LGPD aplicável, se dados são retidos/logados em algum serviço externo e por quanto tempo; risco ALTO se qualquer um desses não tiver resposta clara
- Lição-origem: generalização do `.gitignore` de segredos e da pausa da migração, para qualquer dado sensível (não só credenciais do próprio agente)

O Documento de Visibilidade não lista as 9 categorias sempre — apenas as que tiveram gatilho ativado pelas respostas do Form.

## Estrutura do Documento de Visibilidade (saída detalhada)

1. **Resumo Executivo** — veredito (recomendado construir / precisa mais discovery / não recomendado agora), custo estimado (cenário atual e 3x volume), prazo estimado, nível de risco geral
2. **Contexto do Pedido** — problema, área solicitante, processo atual, dono do agente
3. **Arquitetura Sugerida** — componentes necessários (fontes de dados, motor de IA, saída, agendamento), reaproveitando padrões já validados no Agente de Relatórios quando aplicável
4. **Riscos Mapeados** — uma subseção por categoria do rulebook com gatilho ativo, cada uma com veredito + mitigação recomendada
5. **Checklist de Decisões Pendentes** — lista objetiva do que precisa ser decidido antes de começar a construir
6. **Próximos Passos** — sequência recomendada de implementação

## Estrutura do Resumo PPTX (executivo)

Reaproveita o padrão visual já validado nesta sessão (paleta navy/ice, cards com sombra, `pptxgenjs`). 4 slides, extraídos do Documento de Visibilidade, gerados na mesma conversa:

1. Slide título — nome do agente proposto, área solicitante, data
2. Slide veredito — cards com risco geral, custo estimado, prazo estimado, recomendação
3. Slide riscos principais — só os 2-3 riscos de maior severidade, com mitigação
4. Slide próximos passos — checklist de decisões pendentes + sequência recomendada

## Manutenção do processo

- `rulebook.md` é um documento vivo: toda nova lição real (de qualquer agente, incluindo o de Relatórios) vira uma categoria nova ou um ajuste de regra existente.
- O Google Form pode evoluir sem quebrar nada, pois só alimenta uma conversa — não um script rígido.
- Não há testes automatizados neste processo (não há código de produção). A validação é a sua revisão do Documento de Visibilidade antes de levar à decisão go/no-go.

## Entregáveis desta implementação

1. `docs/planejamento-agentes/rulebook.md` — as 9 categorias acima, em formato pronto para uso em conversas futuras.
2. Estrutura/roteiro do Google Form (texto pronto para você colar na criação do Form no Google Forms — a criação do Form em si é uma ação manual sua, fora do escopo de código).
3. Um template de Documento de Visibilidade (ex: `docs/planejamento-agentes/template-documento-visibilidade.md`) com as 6 seções acima já esqueletadas, para reduzir trabalho repetitivo a cada novo agente avaliado.
