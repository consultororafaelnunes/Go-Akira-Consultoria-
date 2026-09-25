"""
project_timeline.py — Calcula a etapa e o prazo do projeto de um cliente.

Combina duas fontes:
  1. A DATA DO KICK OFF — lida da ata do Kick Off do cliente no Drive (Google Doc
     "Ata — {cliente} — DD-MM-YYYY — ... Kick Off ...") ou, como fallback, dos
     summaries_*.json já processados.
  2. O PRAZO EM DIAS ÚTEIS — extraído do contrato de serviço (contract_reader).

A partir disso, calcula: dias úteis decorridos, dias úteis restantes, data
prevista de término e um percentual de progresso.

Observação sobre dias úteis: contamos segunda a sexta (feriados nacionais NÃO
são descontados — o contrato define o prazo em dias úteis corridos de semana).
"""

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import contract_reader

# Cache em memória por execução: cliente -> date | None do kick off
_kickoff_cache: dict[str, date | None] = {}

# "Ata — {cliente} — 12-05-2026 — Kick Off ..."  → captura a data no nome
_ATA_DATE_RE = re.compile(r"(\d{2})-(\d{2})-(\d{4})")
_KICKOFF_TERMS = ("kick off", "kickoff", "kick-off")


# ── Matemática de dias úteis (seg–sex) ──────────────────────────────────────────

def is_business_day(d: date) -> bool:
    return d.weekday() < 5  # 0=segunda ... 4=sexta


def business_days_between(start: date, end: date) -> int:
    """Dias úteis em (start, end] — exclui o dia inicial, inclui o final. 0 se end<=start."""
    if end <= start:
        return 0
    dias = 0
    d = start + timedelta(days=1)
    while d <= end:
        if is_business_day(d):
            dias += 1
        d += timedelta(days=1)
    return dias


def add_business_days(start: date, n: int) -> date:
    """Retorna a data após somar n dias úteis a partir de start (exclusivo)."""
    d = start
    restantes = n
    while restantes > 0:
        d += timedelta(days=1)
        if is_business_day(d):
            restantes -= 1
    return d


# ── Data do Kick Off ─────────────────────────────────────────────────────────────

def _kickoff_from_drive(service, cliente: str) -> date | None:
    """Procura a ata cujo nome contém 'Kick Off' e extrai a data do nome."""
    cli_q = cliente.replace("'", "\\'")
    try:
        res = service.files().list(
            q=(
                f"name contains 'Ata — {cli_q}' and "
                f"mimeType='application/vnd.google-apps.document' and trashed=false"
            ),
            fields="files(id,name)",
            pageSize=50,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
        ).execute()
    except Exception as e:
        print(f"   Aviso: falha ao buscar ata de Kick Off de '{cliente}' — {e}")
        return None

    datas = []
    for f in res.get("files", []):
        nome = f.get("name", "")
        if not any(t in nome.lower() for t in _KICKOFF_TERMS):
            continue
        m = _ATA_DATE_RE.search(nome)
        if m:
            try:
                datas.append(date(int(m.group(3)), int(m.group(2)), int(m.group(1))))
            except ValueError:
                continue
    return min(datas) if datas else None


def _kickoff_from_summaries(cliente: str, summaries_dir: str = ".") -> date | None:
    """Fallback: procura nos summaries_*.json uma reunião de Kick Off do cliente."""
    datas = []
    for path in Path(summaries_dir).glob("summaries_*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for s in data:
            if s.get("cliente") != cliente:
                continue
            texto = f"{s.get('titulo_reuniao','')} {s.get('assunto','')} {s.get('fase','')}".lower()
            if not any(t in texto for t in _KICKOFF_TERMS):
                continue
            try:
                datas.append(datetime.strptime(s.get("data_reuniao", "").strip(), "%d/%m/%Y").date())
            except (ValueError, AttributeError):
                continue
    return min(datas) if datas else None


def get_kickoff_date(cliente: str, service=None, summaries_dir: str = ".") -> date | None:
    """Data do Kick Off do cliente (Drive primeiro, summaries como fallback). None se não achar."""
    if cliente in _kickoff_cache:
        return _kickoff_cache[cliente]

    resultado = None
    try:
        svc = service or contract_reader._get_drive()
        resultado = _kickoff_from_drive(svc, cliente)
    except Exception as e:
        print(f"   Aviso: sem acesso ao Drive para Kick Off de '{cliente}' — {e}")

    if resultado is None:
        resultado = _kickoff_from_summaries(cliente, summaries_dir)

    _kickoff_cache[cliente] = resultado
    return resultado


# ── Timeline consolidada ─────────────────────────────────────────────────────────

def get_project_timeline(cliente: str, etapa_atual: str | None = None,
                         service=None, hoje: date | None = None,
                         summaries_dir: str = ".") -> dict:
    """
    Consolida etapa + prazo do projeto de um cliente.

    Args:
        etapa_atual: fase corrente já conhecida (ex: "BP"/"Jurídico"/"Manuais"),
                     tipicamente a fase da reunião mais recente do cliente.

    Retorna dict com:
      {cliente, etapa, kickoff, dias_uteis_total, dias_uteis_decorridos,
       dias_uteis_restantes, previsao_fim, progresso_pct, atrasado,
       tem_prazo, tem_kickoff, contrato_link, obs}
    onde datas são objetos date (ou None) — a formatação fica com o relatório.
    """
    hoje = hoje or date.today()
    contrato = contract_reader.get_contract_data(cliente, service=service)
    dias_total = contrato.get("dias_uteis")
    kickoff = get_kickoff_date(cliente, service=service, summaries_dir=summaries_dir)

    out = {
        "cliente": cliente,
        "etapa": etapa_atual or "—",
        "kickoff": kickoff,
        "dias_uteis_total": dias_total,
        "dias_uteis_fonte": contrato.get("dias_uteis_fonte", ""),
        "etapas_contrato": contrato.get("etapas", []),
        "dias_uteis_decorridos": None,
        "dias_uteis_restantes": None,
        "previsao_fim": None,
        "progresso_pct": None,
        "atrasado": False,
        "tem_prazo": dias_total is not None,
        "tem_kickoff": kickoff is not None,
        "contrato_link": contrato.get("contrato_link", ""),
        "obs": "",
    }

    if kickoff is None and dias_total is None:
        out["obs"] = "kick off e prazo do contrato não localizados"
    elif kickoff is None:
        out["obs"] = "data de kick off não localizada"
    elif dias_total is None:
        out["obs"] = "prazo em dias úteis não localizado no contrato"
        out["dias_uteis_decorridos"] = business_days_between(kickoff, hoje)

    if kickoff is not None and dias_total is not None:
        decorridos = business_days_between(kickoff, hoje)
        previsao_fim = add_business_days(kickoff, dias_total)
        restantes = business_days_between(hoje, previsao_fim)
        out["dias_uteis_decorridos"] = decorridos
        out["previsao_fim"] = previsao_fim
        out["dias_uteis_restantes"] = restantes
        out["progresso_pct"] = min(100, round(100 * decorridos / dias_total)) if dias_total else None
        out["atrasado"] = hoje > previsao_fim

    return out
