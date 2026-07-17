"""
main.py — Orquestrador do pipeline completo.

Fluxo diário:
  1. Lê Google Docs de transcrição da pasta Meet Recordings no Drive (últimas 24h)
  2. Sumariza cada transcrição com Claude Haiku → JSON estruturado
  3. Gera ata em .docx (a partir do template local) e salva na pasta do cliente no Drive
  4. Gera PDF executivo
  5. Envia email com HTML + PDF às 8h

Fluxo mensal (ativado no dia configurado via MONTHLY_REPORT_DAY):
  6. Coleta todos os resumos do mês
  7. Gera relatório PPTX completo
  8. Faz upload para o Drive → envia email de entrega

Backfill (projetos em andamento com histórico no Drive):
  Lê todas as transcrições de um cliente e gera as atas pendentes.

Briefings (ao final da fase consultiva):
  Consolida todas as reuniões de um cliente → 2 briefings (Jurídico + Manuais)
  usando Claude Opus 4.8, e os sobe ao Drive.

Uso:
  python main.py                              # produção (24h)
  python main.py --hours 72                   # reprocessa últimas 72h
  python main.py --dry-run                    # sem envios externos
  python main.py --mock                       # dados de teste
  python main.py --monthly                    # força relatório mensal agora
  python main.py --backfill --cliente "Box2Fit"          # cria atas do histórico
  python main.py --briefing --cliente "Box2Fit"          # gera 2 briefings
  python main.py --briefing --todos-concluidos           # briefings de todos os concluídos
  python main.py --listar-clientes                       # lista clientes e status
"""

import argparse
import calendar
import json
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv


# ── Variáveis de ambiente ──────────────────────────────────────────────────────

REQUIRED_VARS = [
    "ANTHROPIC_API_KEY",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_REFRESH_TOKEN",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "DIRECTORS_EMAILS",
]

# Opcionais — sem elas as funções correspondentes são puladas com aviso
OPTIONAL_VARS = {
    "DRIVE_ROOT_FOLDER_ID":  "Pasta raiz no Drive (usa My Drive se omitido)",
    "MONTHLY_REPORT_DAY":    "Dia do mês para relatório mensal (padrão: último dia do mês)",
}


def check_env() -> list[str]:
    return [v for v in REQUIRED_VARS if not os.environ.get(v)]


def _already_processed_ids() -> set[str]:
    """
    IDs (_message_id) de todas as transcrições já sumarizadas em execuções
    anteriores. A janela de busca de 24h se sobrepõe entre execuções que não
    ficam exatamente 24h uma da outra, então sem isso a mesma reunião pode
    ser resumida (e ter ata duplicada) em dois dias seguidos.
    """
    ids: set[str] = set()
    for path in Path(".").glob("summaries_*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for item in data:
            mid = item.get("_message_id")
            if mid:
                ids.add(mid)
    return ids


def is_monthly_report_day() -> bool:
    """
    Retorna True se hoje é o dia de disparar o relatório mensal.
    Por padrão, dispara apenas no último dia do mês (dados já acumulados).
    MONTHLY_REPORT_DAY pode sobrescrever para um dia fixo, se necessário.
    """
    today = date.today()
    override = os.environ.get("MONTHLY_REPORT_DAY")
    if override:
        return today.day == int(override)
    last_day = calendar.monthrange(today.year, today.month)[1]
    return today.day == last_day


# ── Dados de teste ─────────────────────────────────────────────────────────────

def mock_summaries() -> list[dict]:
    return [
        {
            "cliente": "Acme Corp",
            "titulo_reuniao": "Revisão de roadmap Q3",
            "data_reuniao": date.today().strftime("%d/%m/%Y"),
            "duracao_estimada": "1h 15min",
            "participantes": ["Ana Silva", "Carlos Mendes", "João Costa"],
            "resumo": "Alinhamento sobre entregas do Q3. Cliente aprovou o novo módulo de relatórios e demonstrou interesse em expandir a licença para mais 3 usuários.",
            "acionaveis": [
                "João enviar proposta ampliada até 12/06",
                "Ana agendar demo do módulo de relatórios",
                "Carlos atualizar cronograma no Jira",
            ],
            "proximos_passos": [
                "Revisão de contrato expandido — semana de 16/06",
                "Demo do novo módulo — 19/06",
            ],
            "alertas": [],
            "sentimento": "positivo",
            "prioridade": "media",
        },
        {
            "cliente": "Beta Indústria",
            "titulo_reuniao": "Revisão de contrato e prazos",
            "data_reuniao": date.today().strftime("%d/%m/%Y"),
            "duracao_estimada": "45min",
            "participantes": ["Maria Fernanda", "Pedro Alves"],
            "resumo": "Discussão tensa sobre prazo de entrega da fase 2. Cliente sinalizou insatisfação com atrasos e pediu revisão completa do cronograma. Ameaçou acionar cláusula de SLA.",
            "acionaveis": [
                "Diretora convocar reunião interna urgente com equipe técnica",
                "Pedro preparar plano de recuperação até amanhã",
            ],
            "proximos_passos": [
                "Resposta formal ao cliente com novo cronograma — até 10/06",
                "Reunião de alinhamento interno — hoje",
            ],
            "alertas": [
                "Risco de churn — cliente considera cancelar contrato",
                "SLA em risco — 2 entregas atrasadas",
            ],
            "sentimento": "preocupante",
            "prioridade": "alta",
        },
        {
            "cliente": "Gamma Tecnologia",
            "titulo_reuniao": "Onboarding e treinamento",
            "data_reuniao": date.today().strftime("%d/%m/%Y"),
            "duracao_estimada": "1h 30min",
            "participantes": ["Luiza Ramos", "Thiago Nunes", "Beatriz Lima"],
            "resumo": "Sessão de onboarding do novo contrato. Equipe do cliente participou ativamente. Primeiros fluxos configurados e acesso de todos os usuários testado com sucesso.",
            "acionaveis": [
                "Luiza enviar material de treinamento completo",
                "Thiago criar ambiente de homologação para o cliente",
            ],
            "proximos_passos": [
                "Sessão de dúvidas — 15/06",
                "Go-live previsto — 01/07",
            ],
            "alertas": [],
            "sentimento": "positivo",
            "prioridade": "baixa",
        },
    ]


# ── Pipeline diário ────────────────────────────────────────────────────────────

def run_daily(hours_back: int = 24, dry_run: bool = False, mock: bool = False) -> list[dict]:
    """
    Executa o pipeline diário completo.
    Retorna os summaries gerados (usados pelo relatório mensal se for o dia certo).
    """
    print("=" * 60)
    print("🚀 Pipeline diário — iniciando")
    print("=" * 60)

    missing = check_env()
    if missing and not mock:
        print(f"\n❌ Variáveis faltando: {', '.join(missing)}")
        sys.exit(1)
    elif missing and mock:
        print(f"⚠️  Modo mock — ignorando: {', '.join(missing)}")

    # Avisa sobre opcionais ausentes
    for var, desc in OPTIONAL_VARS.items():
        if not os.environ.get(var):
            print(f"   ℹ️  {var} não configurado — {desc}")

    # 1 & 2: Busca + sumarização
    if mock:
        print("\n🧪 Dados de teste")
        summaries = mock_summaries()
    else:
        from fetch_transcripts import get_all_transcripts
        from summarize import summarize_all

        transcripts = get_all_transcripts(hours_back=hours_back)
        transcripts = [t for t in transcripts if t.get("message_id") not in _already_processed_ids()]
        if not transcripts:
            print("\nℹ️  Sem transcrições hoje — encerrando.")
            return []
        summaries = summarize_all(transcripts)

    if not summaries:
        print("\nℹ️  Nenhum resumo gerado.")
        return []

    # Persiste JSON (fonte para o relatório mensal)
    json_path = Path(f"summaries_{date.today().isoformat()}.json")
    json_path.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n💾 Resumos salvos: {json_path}")

    # 3: Criar atas em .docx (template local) e salvar no Drive
    if not dry_run:
        from create_minutes import create_all_minutes
        create_all_minutes(
            summaries,
            root_folder_id=os.environ.get("DRIVE_ROOT_FOLDER_ID"),
        )

        # 3b: Alertas de oportunidade comercial ("levantada de mão")
        # PAUSADO em 16/07/2026 — critério de detecção gerando falsos positivos
        # (ex: sinalizando o próprio serviço já em andamento com o cliente).
        # Reativar trocando para "True" assim que o prompt for calibrado.
        OPPORTUNITY_ALERTS_ENABLED = False
        if OPPORTUNITY_ALERTS_ENABLED:
            from consultants import get_consultant_email
            from send_email import send_opportunity_alert
            for s in summaries:
                if s.get("oportunidades_comerciais"):
                    send_opportunity_alert(s, get_consultant_email(s.get("consultor", "")))
        else:
            n = sum(1 for s in summaries if s.get("oportunidades_comerciais"))
            if n:
                print(f"   ℹ️  {n} oportunidade(s) comercial(is) identificada(s) hoje — "
                      f"envio de alerta pausado para calibração (ver summaries_*.json)")
    else:
        print("🔍 Dry-run — criação de atas e alertas de oportunidade pulados")

    # 4: Gerar PDF
    from generate_pdf import generate_pdf
    pdf_bytes = generate_pdf(summaries)
    pdf_path = Path(f"resumo_{date.today().isoformat()}.pdf")
    pdf_path.write_bytes(pdf_bytes)
    print(f"💾 PDF salvo: {pdf_path}")

    # 5: Enviar email
    if dry_run:
        print(f"\n🔍 Dry-run — email NÃO enviado. Arquivo: {pdf_path}")
    else:
        from send_email import send_report
        send_report(summaries, pdf_bytes)

    print("\n" + "=" * 60)
    print("✅ Pipeline diário concluído!")
    print("=" * 60)
    return summaries


# ── Pipeline mensal ────────────────────────────────────────────────────────────

def run_monthly(dry_run: bool = False, mock: bool = False) -> None:
    """Gera o relatório mensal em PPTX e o entrega por email + Drive."""
    from monthly_report import run_monthly_report

    today = date.today()
    run_monthly_report(
        year=today.year,
        month=today.month,
        summaries_dir=".",
        root_folder_id=os.environ.get("DRIVE_ROOT_FOLDER_ID"),
        dry_run=dry_run,
        mock=mock,
    )


# ── Backfill ───────────────────────────────────────────────────────────────────

def run_backfill(cliente: str, dry_run: bool = False) -> None:
    """
    Lê TODAS as transcrições de um cliente no Drive e gera as atas ainda não criadas.
    Usa o mesmo pipeline de summarize + create_minutes do fluxo diário.
    """
    from client_aliases import normalize_client
    from fetch_transcripts import fetch_drive_transcripts
    from summarize import summarize_all
    from create_minutes import create_all_minutes

    cliente_norm = normalize_client(cliente)
    print("=" * 60)
    print(f"Backfill — {cliente_norm}")
    print("=" * 60)

    transcripts = fetch_drive_transcripts(hours_back=None, cliente=cliente_norm)
    if not transcripts:
        print(f"Nenhuma transcricao encontrada para '{cliente_norm}'.")
        return

    print(f"\n{len(transcripts)} transcricao(oes) encontrada(s). Sumarizando...")
    summaries = summarize_all(transcripts)
    if not summaries:
        print("Nenhum resumo gerado.")
        return

    json_path = Path(f"summaries_backfill_{cliente_norm.replace(' ', '_')}.json")
    json_path.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Resumos salvos: {json_path}")

    if not dry_run:
        create_all_minutes(summaries, root_folder_id=os.environ.get("DRIVE_ROOT_FOLDER_ID"))
    else:
        print("Dry-run — criacao de atas pulada")

    print(f"\nBackfill concluido: {len(summaries)} ata(s) gerada(s) para '{cliente_norm}'")


# ── Briefings ──────────────────────────────────────────────────────────────────

def run_briefing(cliente: str, root_folder_id: str | None = None) -> None:
    """Gera os 2 briefings consolidados (Juridico + Manuais) para um cliente."""
    from client_aliases import normalize_client
    from fetch_transcripts import fetch_drive_transcripts
    from generate_briefing import generate_briefings

    cliente_norm = normalize_client(cliente)
    print("=" * 60)
    print(f"Briefings — {cliente_norm}")
    print("=" * 60)

    transcripts = fetch_drive_transcripts(hours_back=None, cliente=cliente_norm)
    if not transcripts:
        print(f"Nenhuma transcricao para '{cliente_norm}'.")
        return

    results = generate_briefings(
        cliente=cliente_norm,
        transcripts=transcripts,
        root_folder_id=root_folder_id,
    )

    print(f"\nBriefings gerados para '{cliente_norm}':")
    print(f"  Juridico : {results['juridico']['link']}")
    print(f"  Manuais  : {results['manuais']['link']}")


def run_all_briefings(root_folder_id: str | None = None) -> None:
    """Gera briefings para todos os projetos concluidos."""
    from client_aliases import PROJETOS_CONCLUIDOS

    concluidos = sorted(PROJETOS_CONCLUIDOS)
    print(f"Gerando briefings para {len(concluidos)} projetos concluidos...")
    for cliente in concluidos:
        try:
            run_briefing(cliente, root_folder_id=root_folder_id)
        except Exception as e:
            print(f"ERRO em '{cliente}': {e}")


# ── Entrypoint ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    load_dotenv()

    parser = argparse.ArgumentParser(description="Agente de reunioes GoAkira")
    parser.add_argument("--hours",   type=int, default=24)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mock",    action="store_true")
    parser.add_argument("--monthly", action="store_true",
                        help="Forca execucao do relatorio mensal")
    parser.add_argument("--backfill", action="store_true",
                        help="Cria atas do historico de um cliente no Drive")
    parser.add_argument("--briefing", action="store_true",
                        help="Gera os 2 briefings finais de um cliente")
    parser.add_argument("--todos-concluidos", action="store_true",
                        help="Gera briefings de todos os projetos concluidos")
    parser.add_argument("--cliente", type=str, default=None,
                        help="Nome do cliente (para --backfill ou --briefing)")
    parser.add_argument("--listar-clientes", action="store_true",
                        help="Lista todos os clientes e seu status")
    args = parser.parse_args()

    # Modo especial: listar clientes
    if args.listar_clientes:
        from client_aliases import PROJETOS_ATIVOS, PROJETOS_CONCLUIDOS
        print("\n=== Clientes GoAkira ===")
        print("\nAtivos (fase consultiva em andamento):")
        for c in sorted(PROJETOS_ATIVOS):
            print(f"  - {c}")
        print("\nConcluidos (prontos para briefing):")
        for c in sorted(PROJETOS_CONCLUIDOS):
            print(f"  - {c}")
        sys.exit(0)

    # Modo backfill
    if args.backfill:
        if not args.cliente:
            print("Erro: use --cliente 'Nome do Cliente' com --backfill")
            sys.exit(1)
        run_backfill(args.cliente, dry_run=args.dry_run)
        sys.exit(0)

    # Modo briefing
    if args.briefing or args.todos_concluidos:
        if args.todos_concluidos:
            run_all_briefings(root_folder_id=os.environ.get("DRIVE_ROOT_FOLDER_ID"))
        elif args.cliente:
            run_briefing(
                args.cliente,
                root_folder_id=os.environ.get("DRIVE_ROOT_FOLDER_ID"),
            )
        else:
            print("Erro: use --cliente 'Nome' ou --todos-concluidos com --briefing")
            sys.exit(1)
        sys.exit(0)

    # Pipeline diário (padrão)
    run_daily(hours_back=args.hours, dry_run=args.dry_run, mock=args.mock)

    # Relatorio mensal — se for o dia certo OU se --monthly foi passado
    if args.monthly or is_monthly_report_day():
        print("\nIniciando relatorio mensal...")
        run_monthly(dry_run=args.dry_run, mock=args.mock)
