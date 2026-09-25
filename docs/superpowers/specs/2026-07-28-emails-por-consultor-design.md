# Design — Relatório Semanal Segmentado por Consultor

**Data:** 2026-07-28
**Responsável:** Rafael Nunes
**Status:** Design aprovado — pronto para plano de implementação

---

## 1. Contexto e problema

Hoje o Agente de Consultoria envia (ver `send_email.py` / `weekly_report.py`):

- **Notificação de ata** → ao consultor responsável pela fase da reunião (por ata).
- **Relatório diário** → à diretoria (consolidado, todos os clientes).
- **Relatório semanal** → à diretoria (consolidado, já agrupado por consultor internamente).
- **Alerta de oportunidade** → consultor + diretoria.

O consultor recebe um *ping* por ata, mas **não recebe um resumo consolidado só das reuniões dele**. Só a diretoria enxerga a visão semanal agrupada. Cada consultor precisa hoje garimpar as próprias atas para saber o que tem em aberto na semana.

## 2. Objetivo

Enviar, junto do envio semanal atual, **um relatório semanal individual para cada consultor**, contendo apenas as reuniões pelas quais ele é responsável e um apanhado dos próximos passos e pendências dele na semana — sem alterar o relatório consolidado que a diretoria já recebe.

Esta feature também serve de **modelo de referência** para a distribuição segmentada dos próximos agentes (Potencialize, Arquitetura), que replicam a mesma arquitetura.

## 3. Decisões de escopo (travadas com o Rafael)

| Decisão | Escolha |
|---|---|
| Quais relatórios segmentar | **Só o semanal** (diário permanece só para a diretoria) |
| Diretoria continua com o consolidado | **Sim, em paralelo** — nada muda para a diretoria |
| O que o consultor vê | **Só as fases dele** (via `get_responsible_consultants(cliente, fase)`) |
| Conteúdo do e-mail | **Lista de reuniões** + **campo de próximos passos e pendências** |
| Mecanismo de envio | **SMTP atual** (`smtplib`), reusando a infra existente |

## 4. Arquitetura

Toda a mudança fica em `weekly_report.py` + um helper novo em `send_email.py`. **Nenhum módulo novo.**

Fluxo, após o envio do consolidado atual (que permanece intacto):

1. **Reagrupar por responsável.** Para cada reunião da semana, determinar a fase (`get_fase_reuniao`) e o(s) consultor(es) responsável(eis) (`get_responsible_consultants(cliente, fase)`). Uma reunião de Manuais conta para a consultora de Manuais, não para o BP.
2. **Montar o recorte por consultor.** Para cada consultor com ≥1 reunião na semana, montar o conteúdo (ver seção 5).
3. **Enviar individualmente.** Novo helper `send_weekly_consultant_report(consultor_nome, consultor_email, reunioes, periodo)` em `send_email.py`, reusando `smtplib.SMTP_SSL` e o template visual navy/ice já usado nos outros e-mails.

## 5. Conteúdo do e-mail do consultor

Mesmo template visual dos demais relatórios (navy/ice), com duas seções:

1. **Lista de reuniões da semana** — agrupada por fase (BP / Jurídico / Manuais); cada item: cliente, data, título da reunião e duração.
2. **Próximos passos e pendências** — agregação, sobre as reuniões dele, dos campos já existentes nos resumos (`summaries_*.json`):
   - `proximos_passos` e `acionaveis` → "Próximos passos"
   - `alertas` → "Pendências / atenção" (destaque visual quando houver)

Assunto: `[GoAkira] Seu resumo semanal — {nome} — {DD/MM} a {DD/MM}`.

## 6. Casos de borda

- **Consultor sem reunião na semana** → não envia e-mail (nada de mensagem vazia).
- **Reunião cujo responsável não está mapeado / sem e-mail** → entra apenas no consolidado da diretoria; registra aviso no log; não interrompe o envio dos demais consultores.
- **Consultor com papéis em fases diferentes na semana** → recebe **um único e-mail**, com as reuniões agrupadas por fase.
- **Falha de envio para um consultor** → logar e seguir para o próximo (um erro não derruba os demais nem o consolidado).

## 7. Fora de escopo (v1)

- Segmentar também o relatório **diário** (decidido: só semanal por ora).
- Migrar o mecanismo de envio para **Gmail API / OAuth** — resolve a fragilidade da senha de app (erro `535` de 13/07), mas é transversal a todos os e-mails e pertence à **gestão de credenciais da migração VPS (M1)**, não a esta feature.
- Preferências por consultor (opt-out, horário, formato) — não há demanda.

## 8. Abordagens consideradas

- **A — Reusar SMTP atual (escolhida).** Menor superfície, zero infra nova. Herda o risco da senha de app, mas esse risco é transversal e será tratado na migração VPS.
- **B — Gmail API / Apps Script (descartada para esta feature).** Mais robusta para credenciais, porém é uma mudança de infra que afeta todos os envios; acoplar atrasaria a feature. Fica registrada como trilha separada da migração.

## 9. Testes

- `weekly_report.py --dry-run` deve imprimir, por consultor, quantas reuniões e para qual e-mail o relatório iria — **sem enviar**.
- Teste com uma semana real conhecida (padrão de `teste_semanal_patricia.py`), conferindo que o recorte de cada consultor bate com o mapeamento de `consultants.py`.
- Verificar que o **consolidado da diretoria permanece idêntico** ao atual (nenhuma regressão).

## 10. Métricas de sucesso

- Cada consultor com reunião na semana recebe exatamente **um** e-mail, só com o que é dele.
- Zero regressão no consolidado da diretoria.
- Nenhum e-mail vazio; nenhuma falha individual derruba o lote.

## 11. Próximos passos

1. Revisão desta spec pelo Rafael.
2. Plano de implementação (skill `writing-plans`).
3. Implementação + `--dry-run` de validação.
4. Rodar em paralelo por uma semana antes de considerar concluído.
