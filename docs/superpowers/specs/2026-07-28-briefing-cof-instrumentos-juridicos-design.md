# Design — Briefing de Instrumentos Jurídicos no Formato COF

**Data:** 2026-07-28
**Responsável:** Rafael Nunes
**Status:** Design aprovado — pronto para plano de implementação

---

## 1. Contexto e problema

Ao final da fase de BP, o agente já gera um **Briefing Jurídico** (`generate_briefing.py`, prompt `_JURIDICO_PROMPT`) a partir de todas as reuniões do cliente: Haiku sumariza cada reunião, Opus consolida, o resultado vira `.docx` e sobe ao Drive em `/<cliente>/Briefings/`.

O problema: esse briefing tem **11 seções genéricas** que não batem com o formato real da **Circular de Oferta de Franquia (COF)**. O consultor jurídico (Marco) ainda precisa reorganizar tudo no template de "Informações para COF" (estruturado pelos Incisos da Lei de Franquias 13.966/2019) antes de redigir a COF.

Existe um modelo-padrão desse intake — `REF DOCUMENTOS/Informações para COF - LR IMÓVEIS.docx` — preenchido à mão para o LR Imóveis. Ele é o formato-alvo.

## 2. Objetivo

Fazer o agente entregar, ao fim do BP, um documento **"Informações para COF"** já pré-preenchido na estrutura dos Incisos, a partir das decisões das reuniões — para o jurídico partir de um rascunho quase pronto em vez de reorganizar do zero.

## 3. Decisões de escopo (travadas com o Rafael)

| Decisão | Escolha |
|---|---|
| O template de Incisos é padrão para todos os clientes | **Sim** — encodar como estrutura de saída para qualquer cliente |
| Relação com o Briefing Jurídico atual | **Substituir** a estrutura de 11 seções pela estrutura COF |
| Gatilho | **Manual** — `main.py --briefing --cliente "X"` (como hoje) |
| Citar a fonte (reunião) de cada campo | **Não** — saída limpa, sem fontes |
| Briefing de Manuais | **Inalterado** |

## 4. Arquitetura

Mudança cirúrgica, contida em `generate_briefing.py`:

- Substituir `_JURIDICO_SYSTEM` e `_JURIDICO_PROMPT` por um par novo que produz a **estrutura COF** (seção 5).
- **Nada mais muda:** o fluxo Haiku (sumariza cada reunião) → Opus (consolida) → `_build_docx` → upload em `/<cliente>/Briefings/` permanece igual; o Briefing de Manuais permanece igual; o gatilho (`--briefing` / `--todos-concluidos`) permanece igual.
- O nome do artefato passa de "Briefing Juridico — {cliente}" para **"Informações para COF — {cliente}"**.
- O destinatário continua sendo o responsável jurídico (`get_juridico_email()` → Marco).

## 5. Estrutura de saída (formato COF)

Ordem e campos extraídos do modelo-padrão. O prompt do Opus deve produzir exatamente estas seções:

- **Identificação** — responsável(eis) pelo franchising, site, redes sociais.
- **Inciso I** — histórico do negócio; missão; visão; valores.
- **Inciso II** — empresas ligadas ao franqueador (identidade de sócios).
- **Inciso III** — situação dos balanços da franqueadora.
- **Inciso IV** — pendências judiciais/arbitragens (franqueadora, marcas, sistema).
- **Inciso V** — descrição detalhada da franquia e do negócio; atividades do franqueado.
- **Incisos VI e VII** — perfil e requisitos do franqueado; envolvimento direto na operação; política comercial.
- **Inciso VIII** — planilha de investimento inicial (por plano/formato); condições de pagamento por item; local e mês/ano da pesquisa; o que não está incluso.
- **Inciso IX** — taxas periódicas (por plano); outras remunerações; aluguel/comodato; seguro.
- **Inciso XI** — território (exclusividade × preferência); regras de concorrência territorial; política de vendas na unidade; clientes com tratamento especial.
- **Inciso XII** — mix de produtos e serviços; fornecedores/marcas obrigatórias; centralização de contratos; softwares obrigatórios e finalidade.
- **Inciso XIII** — o que é oferecido ao franqueado; treinamento inicial (público, local, carga horária/dias, conteúdo, se é cobrado).
- **Inciso XIV** — marcas franqueadas (sinalizar verificação no INPI).
- **Inciso XV** — preferência da franqueadora sobre o ponto comercial na saída do franqueado.
- **Inciso XXII** — prazo do contrato de franquia.
- **Informações adicionais** — unidade piloto; endereço/cidade/CEP; divergência em relação ao piloto; obrigações operacionais de destaque; formatos a migrar; homologação de fornecedores por região.
- **Tabela — Perfil do franqueado** — capital; experiência; expectativas; comportamento.

## 6. Regras de preenchimento

- Preencher cada campo a partir das **decisões reais** das reuniões de BP; preservar **valores, percentuais, prazos e datas exatos**.
- Campo sem informação nas reuniões → marcar **`[A COLETAR COM O CLIENTE]`**; ponto jurídico sensível que exige avaliação → **`[Dr. Marco verificar]`**. **Nunca inventar** dado jurídico ou financeiro.
- **Segmento-agnóstico:** o modelo de referência é imobiliário (LR Imóveis), mas a estrutura de Incisos é geral — o prompt não deve assumir segmento nem copiar conteúdo específico do LR.
- **Saída limpa:** sem citar de qual reunião veio cada informação.

## 7. Não-objetivos (v1)

- Não redige a COF final nem o contrato de franquia — entrega apenas o **intake de informações**.
- Não consulta o INPI — apenas sinaliza a verificação de marcas.
- Não altera o Briefing de Manuais nem o gatilho de execução.

## 8. Validação (teste com gabarito)

O **LR Imóveis** tem reuniões reais no Drive **e** o documento humano preenchido (`REF DOCUMENTOS/`). Rodar `main.py --briefing --cliente "LR Imóveis"` e comparar a saída do agente, campo a campo, com o documento do Marco — validação contra ground truth real. Critério: as seções presentes batem, os valores factuais coincidem, e as lacunas do doc humano ("A definir", "Confirmar com o cliente") aparecem como `[A COLETAR COM O CLIENTE]` na saída do agente (não inventadas).

## 9. Métricas de sucesso

- A saída segue a estrutura de Incisos completa (seção 5), sem seções inventadas nem faltando.
- Nenhum dado jurídico/financeiro inventado; lacunas explicitamente marcadas.
- Na comparação com o gabarito do LR, os campos factuais preenchíveis pelas reuniões coincidem.

## 10. Próximos passos

1. Revisão desta spec pelo Rafael.
2. Plano de implementação (skill `writing-plans`).
3. Implementar o novo prompt COF em `generate_briefing.py`.
4. Validar contra o gabarito do LR Imóveis antes de considerar concluído.
