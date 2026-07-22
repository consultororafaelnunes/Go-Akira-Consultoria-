# Documento de Visibilidade — Agente de Atas e Briefings de Marketing

Área solicitante: Marketing
Data da avaliação: 21/07/2026
Avaliado por: Rafael Nunes (com apoio do Claude)
Fonte: resposta do Google Form de briefing, preenchida por Bárbara Savazzoni (20/07/2026)

## 1. Resumo Executivo

- **Veredito:** precisa mais discovery — risco jurídico/contratual e de segurança da informação ainda sem resposta definida (ver Seção 4). Não é "não recomendado": a dor é real e o processo atual (ata manual → ClickUp manual) já existe e funciona parcialmente, só precisa da checagem contratual antes de avançar.
- **Custo estimado:** baixo — volume de 1 a 3 reuniões/semana é bem menor que o do Agente de Relatórios (que roda diariamente). Estimativa por analogia: processamento via Claude (sumarização) na faixa de poucos dólares/mês mesmo em 3x o volume (até ~12 reuniões/semana). Custo de hospedagem adicional deve ser marginal se reaproveitar a mesma infraestrutura do Agente de Relatórios.
- **Prazo estimado:** depende do resultado da checagem jurídica (Seção 5). Sem essa pendência, um MVP que só gera a ata automática (Gmail/Drive, reaproveitando o pipeline existente) é da ordem de 1-2 semanas; a integração com ClickUp para organizar briefings/próximos passos automaticamente é um componente novo, não construído antes, e adiciona mais 1-2 semanas.
- **Nível de risco geral:** ALTO (por causa da Seção 8 e 9 — sem mitigação identificada ainda para nenhuma das duas)

## 2. Contexto do Pedido

- **Problema/dor:** perda de informações das reuniões, retrabalho, falta de automação na geração de atas, briefings e próximos passos — quer garantir alinhamento e eficiência do time de Marketing.
- **Área solicitante:** Marketing
- **Processo atual:** híbrido e manual. Ata gerada pelo Gemini (Google Meet) e enviada por e-mail ao time após a reunião com o cliente. Próximos passos, demandas e briefings são depois organizados manualmente no ClickUp.
- **Dono do agente:** Bárbara Savazzoni (Gerente de Marketing) e Daniel Braga (Sócio) — responsabilidade conjunta.

## 3. Arquitetura Sugerida

- **Fontes de dados:** Gmail (atas/transcrições já geradas pelo Gemini), Google Drive (documentos, apresentações, propostas comerciais, cronogramas), ClickUp (gestão de tarefas e briefings).
- **Motor de IA:** Claude, reaproveitando o mesmo padrão de sumarização estruturada já validado no Agente de Relatórios (Haiku para o resumo/estruturação; possivelmente Opus só na etapa de geração de briefing consolidado, se a qualidade do Haiku não for suficiente para esse output mais elaborado).
- **Saída:** e-mail para Bárbara e Daniel, sempre com aprovação humana antes de qualquer ação subsequente (ela não pediu envio automático).
- **Agendamento/execução:** sob demanda (não precisa de agendamento fixo tipo diário/semanal), 100% na nuvem — sem dependência de computador ou pessoa específica ligados. Isso evita de saída o Risco #1 do rulebook (dependência de infraestrutura local), que foi a causa mais recorrente de falha no Agente de Relatórios.
- **Componente novo (ainda não existe no ecossistema GoAkira):** integração de leitura/escrita com o ClickUp. Todo o resto (Gmail, Drive, Claude) já tem padrão pronto e testado.

## 4. Riscos Mapeados

> Apenas as categorias do rulebook cujo gatilho foi ativado pelas respostas do Form.

### Risco jurídico/contratual (inclui Propriedade Intelectual)

- **Veredito:** ALTO
- **Justificativa:** os dados envolvem diretamente clientes finais e terceiros da GoAkira (atas de reuniões, briefings, demandas, cronogramas, contatos de responsáveis) — gatilho confirmado pela própria respondente. Ela também confirma que os dados **seriam enviados a um serviço externo de IA** (Claude/Anthropic) e que **não existe hoje cláusula contratual com os clientes autorizando isso**. Além disso, o contrato vigente não trata da propriedade dos materiais/análises gerados por IA a partir dos dados do cliente.
- **Mitigação recomendada:** não iniciar a construção da parte do agente que toca dados de cliente final antes de uma checagem jurídica confirmando (a) se o contrato permite processar os dados da reunião via IA externa, e (b) a quem pertence o output gerado. Bárbara já sinalizou isso sozinha na resposta — é só formalizar a checagem com jurídico/Patrícia antes de programar.

### Segurança da informação

- **Veredito:** ALTO
- **Justificativa:** o gatilho combinado ("dados sensíveis" OU "enviado a serviço externo") está ativo pela via do envio a serviço externo de IA. Nenhum dos três itens exigidos pela regra tem resposta definida ainda: (a) onde ficariam armazenadas as credenciais de acesso ao ClickUp/Gmail/Drive deste novo agente; (b) se há LGPD aplicável (há dado pessoal de contatos/responsáveis de clientes envolvido — provavelmente sim); (c) por quanto tempo a Anthropic retém os dados enviados para sumarização.
- **Mitigação recomendada:** responder os três itens antes de aprovar construção. Os itens (a) e (c) são rápidos de resolver (o padrão de variáveis de ambiente do Agente de Relatórios já cobre (a); (c) é só confirmar a política de retenção da Anthropic para a conta usada). O item (b) exige uma decisão de negócio/jurídica, não só técnica.

### Risco financeiro

- **Veredito:** MÉDIO
- **Justificativa:** não existe orçamento aprovado definido ("Não sei", na resposta). Ao mesmo tempo, o volume é baixo e previsível (1-3 reuniões/semana), o que limita o tamanho do risco na prática — daí médio, não alto.
- **Mitigação recomendada:** confirmar com José Fugice (indicado como aprovador de aumento de custo) um teto de gasto mensal antes de ativar em produção, mesmo sendo um valor baixo esperado.

## 5. Checklist de Decisões Pendentes

- [ ] Confirmar com jurídico/Patrícia se os contratos atuais dos clientes de Marketing permitem processar atas/reuniões via IA externa (Claude/Anthropic)
- [ ] Definir a quem pertence o output gerado por IA a partir de dados do cliente (GoAkira, cliente, ou split) — se necessário, ajustar contrato-modelo para novos clientes
- [ ] Confirmar se há dado pessoal (LGPD) nos contatos/responsáveis processados e qual base legal se aplica
- [ ] Confirmar política de retenção de dados da Anthropic para a conta usada
- [ ] Definir onde ficam as credenciais do ClickUp (e do restante) — variáveis de ambiente, nunca em texto no repositório
- [ ] Confirmar com José Fugice um teto de orçamento mensal para custos de API, mesmo estimado como baixo

## 6. Próximos Passos

1. Levar a checagem jurídica (contrato + PI) para Patrícia antes de qualquer linha de código — é o único item que pode inviabilizar ou mudar o escopo do projeto.
2. Em paralelo, prototipar só a parte de geração automática de ata a partir do e-mail do Gemini (reaproveita 90% do Agente de Relatórios já existente) — sem tocar ClickUp ainda, para validar o valor com Bárbara rapidamente.
3. Só depois de (1) resolvido, desenhar e construir a integração com ClickUp para organizar briefings/próximos passos automaticamente.
4. Confirmar teto de orçamento com José Fugice antes de ativar em produção.
