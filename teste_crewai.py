"""
teste_crewai.py — Exploração técnica do CrewAI com Claude.

Dois agentes colaboram para analisar o log do pipeline GoAkira e
produzir um relatório de status executivo.

Roda: python teste_crewai.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from crewai import Agent, Crew, LLM, Task

# ── LLM: Claude via Anthropic (sem precisar de chave OpenAI) ─────────────────

llm = LLM(
    model="anthropic/claude-haiku-4-5-20251001",
    api_key=os.environ["ANTHROPIC_API_KEY"],
    max_tokens=2048,
)

# ── Fonte de dados: log real ou exemplo embutido ──────────────────────────────

LOG_PATH = Path(__file__).parent / "agente.log"

if LOG_PATH.exists():
    log_content = LOG_PATH.read_text(encoding="utf-8", errors="replace")[-4000:]
    print(f"[LOG] Lendo {LOG_PATH.name} ({len(log_content)} chars)")
else:
    print("[LOG] agente.log nao encontrado — usando exemplo embutido")
    log_content = """\
=== 26/06/2026 09:00 AGENTE INICIADO ===
Pipeline diario — iniciando
Buscando em Meet Recordings de Rafael...
   3 arquivo(s) encontrado(s)
   OK: [Carrano] Definicao dos Shoppings SP (24/06/2026)
   OK: [Acai Island] Analise do Mix de Produtos (24/06/2026)
   OK: [Que Tutti de Minas] Apresentacao Modelo de Franquia (24/06/2026)
Total: 3 transcricao(oes) carregada(s)

Sumarizando 3 transcricao(oes) com Claude...
   [1/3] [Carrano] BP. Definicao dos Shoppings...
   JSON invalido (tentativa 1/3) — retentando...
   JSON invalido (tentativa 2/3) — retentando...
   Carrano — Definicao dos Shoppings SP - FlagShip
   [2/3] [Acai Island] BP. Analise do Mix...
   Acai Island — Analise do Mix de Produtos
   [3/3] [Que Tutti] BP. Apresentacao...
   Que Tutti de Minas — Apresentacao Modelo de Franquia

3/3 resumo(s) gerado(s)

Criando 3 ata(s) de reuniao...
   Criando ata para: Carrano
   Ata gerada: Ata - Carrano - 24-06-2026 - Definicao dos Shoppings SP
   Salva no Drive: https://docs.google.com/document/d/abc123
   Notificacao enviada para c10@goakira.com.br
   Criando ata para: Acai Island
   Ata gerada: Ata - Acai Island - 24-06-2026 - Analise do Mix de Produtos
   Salva no Drive: https://docs.google.com/document/d/def456
   Notificacao enviada para c10@goakira.com.br
   Criando ata para: Que Tutti de Minas
   Aviso: falha ao enviar notificacao para marco.paixao@goakira.com.br: Connection timeout
   Ata gerada e salva no Drive.
3 ata(s) criada(s) com sucesso

Gerando PDF...
PDF salvo: resumo_2026-06-26.pdf

Email diario enviado para: jose.fugice@goakira.com.br, patricia.cotti@goakira.com.br
Pipeline diario concluido!
=== 26/06/2026 09:04 AGENTE FINALIZADO ===
"""

# ── Agente 1: Analista Técnico ────────────────────────────────────────────────

analista = Agent(
    role="Analista de Pipeline",
    goal="Analisar logs de execucao e extrair metricas, erros e status com precisao",
    backstory=(
        "Especialista em monitoramento de pipelines de dados corporativos. "
        "Le logs tecnicos e distingue erros criticos de avisos normais. "
        "Conhece o pipeline GoAkira: busca transcricoes no Drive, sumariza com Claude, "
        "cria atas e envia emails para diretores."
    ),
    llm=llm,
    verbose=True,
)

# ── Agente 2: Redator Executivo ───────────────────────────────────────────────

redator = Agent(
    role="Redator de Status Executivo",
    goal="Transformar analise tecnica em comunicacao clara e acionavel para gestores",
    backstory=(
        "Especialista em comunicacao executiva. Converte informacoes tecnicas em "
        "mensagens diretas, sem jargao, que um CEO ou diretora possa ler em 10 segundos. "
        "Usa emoji para sinalizar status e destaca apenas o que requer atencao."
    ),
    llm=llm,
    verbose=True,
)

# ── Tarefa 1: Analisar o log ──────────────────────────────────────────────────

tarefa_analise = Task(
    description=f"""
Analise o log de execucao do pipeline GoAkira abaixo e responda as seguintes perguntas:

1. O pipeline concluiu com sucesso?
2. Quantas transcricoes foram encontradas e quantas foram processadas com sucesso?
3. Quantas atas foram criadas e salvas no Drive?
4. Houve erros? Liste cada um e classifique: CRITICO (pipeline falhou) ou AVISO (contornado).
5. Os emails foram enviados? Para quem?
6. Qual foi o tempo total de execucao?

LOG DE EXECUCAO:
---
{log_content}
---

Seja preciso — use apenas o que esta no log, nao invente informacoes.
""",
    expected_output=(
        "Relatorio de analise estruturado com: status geral, metricas numericas, "
        "lista de erros classificados por gravidade e confirmacao dos envios."
    ),
    agent=analista,
)

# ── Tarefa 2: Escrever mensagem executiva ─────────────────────────────────────

tarefa_relatorio = Task(
    description="""
Com base na analise do pipeline, redija uma mensagem de status executivo em portugues.

Formato:
- Maximo 6 linhas
- Primeira linha: emoji de status + resultado geral
- Segunda linha: metricas principais (reunioes, atas, clientes)
- Se houver avisos ou erros: descreva em 1-2 linhas o que precisa de atencao
- Ultima linha: proxima execucao agendada

Tom: direto, profissional, sem jargao tecnico.
Adequado para envio por WhatsApp ou email rapido aos diretores da GoAkira.
""",
    expected_output="Mensagem executiva de status do pipeline, pronta para envio.",
    agent=redator,
    context=[tarefa_analise],
)

# ── Crew ──────────────────────────────────────────────────────────────────────

crew = Crew(
    agents=[analista, redator],
    tasks=[tarefa_analise, tarefa_relatorio],
    verbose=True,
    tracing=True,   # envia execução para app.crewai.com
)

# ── Execucao ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TESTE CrewAI — Monitoramento GoAkira")
    print("Agentes: Analista de Pipeline + Redator Executivo")
    print("LLM: Claude Haiku 4.5 (Anthropic)")
    print("=" * 60 + "\n")

    resultado = crew.kickoff()

    print("\n" + "=" * 60)
    print("MENSAGEM FINAL (pronta para envio):")
    print("=" * 60)
    print(resultado.raw)
