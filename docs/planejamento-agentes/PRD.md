# PRD — Processo de Planejamento de Novos Agentes de IA da GoAkira

**Versão:** 1.0
**Data:** 2026-07-08
**Responsável:** Rafael Nunes
**Status:** Aprovado internamente — pronto para primeiro uso real

---

## 1. Visão Geral

Um processo estruturado, em três documentos, que permite a qualquer área da
GoAkira propor um novo agente de IA e receber — antes de qualquer linha de
código ser escrita — visibilidade completa sobre arquitetura sugerida,
riscos mapeados, custo estimado e prazo. O processo nasce diretamente das
lições reais aprendidas na construção e operação do Agente de Relatórios
(pipeline de reuniões/atas da GoAkira).

## 2. Problema

Hoje, quando uma área quer um agente de IA, não existe um caminho estruturado
para avaliar viabilidade antes de começar a construir. O Agente de Relatórios
foi construído sem esse processo, e isso custou caro em produção: falhas de
agendamento por dependência de hardware local, duplicação de dados entre
execuções, atribuição incorreta de responsáveis, relatórios vazando dados de
períodos errados, e uma decisão de migração para nuvem pausada por falta de
definição prévia sobre gestão de credenciais. Todos esses problemas eram
previsíveis — só não foram previstos porque não havia um checklist que os
capturasse antes da construção.

Sem esse processo, cada novo agente da GoAkira corre o risco de repetir os
mesmos erros, descobrindo os riscos em produção em vez de no planejamento.

## 3. Objetivo

Dar a qualquer área da GoAkira um caminho estruturado para: (1) descrever a
ideia de um agente de IA em linguagem não-técnica, e (2) receber de volta um
documento de visibilidade — com arquitetura sugerida, riscos mapeados por
categoria, veredito geral de risco, custo/prazo estimados e um checklist de
decisões pendentes — antes de qualquer decisão de investimento ou construção.

## 4. Fora de escopo (v1)

- Automação de ponta a ponta (Form → documento sem intervenção humana). O
  motor é você + Claude numa conversa, guiados pelo rulebook — não um script.
- Interface web própria (tipo wizard). O briefing usa Google Forms.
- Fluxo formal de aprovação com múltiplas etapas/alçadas. A decisão go/no-go
  continua sendo humana, fora da ferramenta.
- Cálculo automático de custo/prazo por fórmula fixa — a estimativa é
  qualitativa, feita na conversa, ancorada nas categorias de risco ativadas.

## 5. Usuários

| Papel | Quem | O que faz |
|---|---|---|
| Solicitante | Líder de uma área da GoAkira (ex: RH, financeiro, comercial) | Preenche o Google Form descrevendo a ideia do agente |
| Avaliador | Rafael (ou quem herdar essa função) | Revisa as respostas, conduz a conversa com o Claude, produz e valida o Documento de Visibilidade |
| Decisor | Diretoria (Patricia/José) ou a própria área solicitante | Usa o Documento de Visibilidade + resumo PPTX para decidir go/no-go |

## 6. Como funciona (fluxo)

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
[Avaliador revisa as respostas, identifica lacunas/ambiguidades]
        │
        ▼
[Avaliador leva as respostas + o rulebook.md para uma conversa com o Claude]
        │
        ▼
[Claude aplica as regras do rulebook + julgamento próprio,
 gera: Documento de Visibilidade (detalhado) + Resumo PPTX (executivo)]
        │
        ▼
[Avaliador revisa, ajusta, e leva para decisão go/no-go
 com a área solicitante e/ou diretoria]
```

## 7. Requisitos funcionais

### RF1 — Briefing estruturado (Google Form)
O formulário deve cobrir 7 seções: Contexto e Objetivo, Dados e Fontes,
Frequência e Volume, Saída Esperada, Integrações e Dependências, Orçamento,
Nível de Confiança Esperado. Texto pronto em
[`roteiro-google-form.md`](./roteiro-google-form.md).

### RF2 — Rulebook de riscos determinístico
9 categorias de risco, cada uma com gatilho (o que nas respostas do Form a
ativa), regra de decisão e recomendação padrão, todas rastreáveis a uma
lição real do Agente de Relatórios:
infraestrutura, deduplicação de dados, atribuição de responsável, filtragem
por data, credenciais e dados sensíveis, confiabilidade de entrega,
financeiro, jurídico/contratual (inclui propriedade intelectual), segurança
da informação. Documento em [`rulebook.md`](./rulebook.md).

### RF3 — Regra de agregação de veredito geral
O rulebook deve definir como os vereditos individuais (baixo/médio/alto) por
categoria se combinam num risco geral e numa recomendação (construir / construir
com mitigação / precisar de mais discovery), sem nunca gerar automaticamente
um veredito de "não recomendado" — essa conclusão é sempre humana. Ver
Categoria 10 em [`rulebook.md`](./rulebook.md).

### RF4 — Documento de Visibilidade
Template com 6 seções fixas: Resumo Executivo, Contexto do Pedido,
Arquitetura Sugerida, Riscos Mapeados (apenas categorias com gatilho ativo),
Checklist de Decisões Pendentes, Próximos Passos. Template em
[`template-documento-visibilidade.md`](./template-documento-visibilidade.md).

### RF5 — Resumo executivo em PPTX
A partir do Documento de Visibilidade, gerar um resumo de até 4 slides
(título, veredito, riscos principais, próximos passos), reaproveitando o
padrão visual já validado nos decks da GoAkira (paleta navy/ice,
`pptxgenjs`). Gerado ad-hoc na mesma conversa — não é um artefato de
template fixo, pois o conteúdo varia por agente avaliado.

## 8. Requisitos não-funcionais

- **Sem dependência de código de produção.** Todo o processo funciona com
  Google Forms + documentos markdown + uma conversa com o Claude — nenhuma
  infraestrutura nova precisa ser mantida.
- **Manutenibilidade do rulebook.** Qualquer lição nova aprendida na operação
  de um agente (incluindo o próprio Agente de Relatórios) deve poder virar
  uma categoria nova ou ajuste de regra existente, sem exigir reestruturação
  do processo.
- **Rastreabilidade.** Cada regra do rulebook deve citar a lição-origem que a
  motivou, para que decisões futuras possam ser auditadas.

## 9. Métricas de sucesso

Como este é um processo de baixo volume (não um sistema com tráfego
mensurável automaticamente), o sucesso é avaliado qualitativamente a cada
uso:

- O Documento de Visibilidade gerado antecipou pelo menos um risco real que
  só teria aparecido depois, em produção (comparável aos problemas do Agente
  de Relatórios)?
- A decisão go/no-go foi tomada com base no documento, sem precisar de uma
  rodada extra de descoberta não prevista nele?
- O tempo entre "ideia proposta" e "documento de visibilidade pronto" ficou
  abaixo de alguns dias úteis (não meses)?

## 10. Riscos e premissas do próprio processo

- **Premissa:** o volume de pedidos de novos agentes é baixo o suficiente
  para que o processo manual (Form + conversa) não vire gargalo. Se o volume
  crescer, migrar partes do rulebook para regras automatizadas (script) passa
  a valer a pena — ver Abordagem B descartada no
  [spec de design](../superpowers/specs/2026-07-08-planejamento-agentes-goakira-design.md).
- **Risco:** o rulebook fica desatualizado se novas lições não forem
  incorporadas a ele. Mitigação: tratar a atualização do rulebook como parte
  do encerramento de qualquer incidente de produção em qualquer agente da
  GoAkira.
- **Risco:** áreas não-técnicas podem preencher o Form de forma incompleta ou
  ambígua. Mitigação: o avaliador sempre revê as respostas antes de gerar o
  documento, e pode voltar à área solicitante para esclarecer antes de seguir.

## 11. Rollout

1. Criar o Google Form real a partir do roteiro (`roteiro-google-form.md`) —
   ação manual, fora do repositório de código.
2. Divulgar o link do Form para as áreas da GoAkira como canal oficial de
   proposta de novos agentes de IA.
3. Rodar o processo end-to-end na primeira proposta real recebida, usando-a
   como validação do rulebook e do template.
4. Revisar o rulebook após esse primeiro uso real, incorporando qualquer
   lacuna encontrada.

## 12. Documentos relacionados

- [Spec de design](../superpowers/specs/2026-07-08-planejamento-agentes-goakira-design.md)
- [Plano de implementação](../superpowers/plans/2026-07-08-planejamento-agentes-goakira.md)
- [Rulebook de riscos](./rulebook.md)
- [Roteiro do Google Form](./roteiro-google-form.md)
- [Template do Documento de Visibilidade](./template-documento-visibilidade.md)
