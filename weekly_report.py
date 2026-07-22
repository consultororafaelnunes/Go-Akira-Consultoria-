"""
weekly_report.py — Relatório semanal de reuniões por consultor.

Roda toda segunda-feira às 09:30, cobrindo a semana anterior (seg–sex).
Agrupa as reuniões por consultor e envia email consolidado para os diretores.
"""

import json
import os
import smtplib
from collections import defaultdict
from datetime import date, datetime, timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from generate_pdf import generate_weekly_pdf


def _previous_week_range() -> tuple[date, date]:
    """Retorna (segunda, sexta) da semana anterior."""
    today = date.today()
    # Volta até a segunda-feira da semana atual, depois subtrai 7 dias
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_friday = last_monday + timedelta(days=4)
    return last_monday, last_friday


def _meeting_in_range(s: dict, start: date, end: date) -> bool:
    """
    Confirma que a reunião de fato ocorreu na semana, usando a data real da
    reunião (data_reuniao) quando interpretável — o arquivo summaries_*.json em
    que o resumo foi salvo reflete quando o pipeline processou a transcrição,
    não quando a reunião de fato aconteceu (uma transcrição antiga pode ser
    capturada tardiamente se o documento no Drive for modificado depois).
    """
    raw = s.get("data_reuniao", "")
    try:
        d = datetime.strptime(raw.strip(), "%d/%m/%Y").date()
    except (ValueError, AttributeError):
        return True  # data não interpretável — mantém, já está na janela do arquivo
    return start <= d <= end


def _load_week_summaries(start: date, end: date, summaries_dir: str = ".") -> list[dict]:
    """
    Carrega os resumos da semana filtrando pela data REAL da reunião
    (data_reuniao), não pelo nome do arquivo em que foram salvos — uma
    reunião de sexta processada tardiamente na segunda seguinte (ex: falha
    de agendamento, backfill) fica salva num arquivo fora da janela da
    semana, mas ainda precisa aparecer no relatório daquela semana.
    """
    summaries = []
    seen_ids = set()
    for path in sorted(Path(summaries_dir).glob("summaries_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"   Aviso: erro ao ler {path.name} — {e}")
            continue
        for s in data:
            mid = s.get("_message_id")
            if mid and mid in seen_ids:
                continue
            if mid:
                seen_ids.add(mid)
            summaries.append(s)
    return [s for s in summaries if _meeting_in_range(s, start, end)]


def _group_by_consultant(summaries: list[dict]) -> dict[str, list[dict]]:
    """
    Agrupa resumos por consultor responsável.
    Prioriza o consultor que de fato gravou a reunião (campo "consultor",
    pasta de origem no Drive) sobre a tabela estática de BP — clientes com
    fases diferentes (ex: BP com um consultor, Manuais com outro) ficam mal
    atribuídos se só olharmos o BP fixo do cliente. Clientes com mais de um
    BP cadastrado (projeto conjunto) sempre creditam todos os BPs, independente
    de quem gravou aquela reunião específica.
    """
    try:
        from consultants import get_bp_consultants
    except ImportError:
        get_bp_consultants = lambda c: ["Rafael"]

    grouped = defaultdict(list)
    for s in summaries:
        bp_list = get_bp_consultants(s.get("cliente", ""))
        if len(bp_list) > 1:
            consultores = bp_list
        elif s.get("consultor"):
            consultores = [s["consultor"]]
        else:
            consultores = bp_list or ["Não identificado"]
        for consultor in consultores:
            grouped[consultor].append(s)
    return dict(grouped)


def _sentiment_badge(sent: str) -> str:
    styles = {
        "positivo":    "background:#CCFBF1;color:#0D9488",
        "neutro":      "background:#FEF3C7;color:#92400E",
        "preocupante": "background:#FEE2E2;color:#DC2626",
    }
    style = styles.get(sent, "background:#F1F5F9;color:#64748B")
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:20px;'
        f'font-size:11px;font-weight:700;{style}">{sent.capitalize()}</span>'
    )


def _build_html(grouped: dict[str, list[dict]], start: date, end: date,
                 calendar_changes: list[dict] | None = None) -> str:
    total = sum(len(v) for v in grouped.values())
    n_clientes = len({s.get("cliente", "") for v in grouped.values() for s in v})
    n_alertas = sum(1 for v in grouped.values() for s in v if s.get("alertas"))

    from calendar_sync import render_changes_html
    changes_section = render_changes_html(calendar_changes or [])

    alert_banner = ""
    if n_alertas:
        alert_banner = f"""
        <p style="background:#FEE2E2;border-radius:6px;padding:10px 14px;
                  color:#DC2626;font-size:13px;margin-bottom:20px">
          <b>⚠️ {n_alertas} reunião(ões) com alertas</b> — revise as atas com atenção.
        </p>"""

    consultant_sections = ""
    for consultor, meetings in sorted(grouped.items()):
        n_pos  = sum(1 for s in meetings if s.get("sentimento") == "positivo")
        n_preo = sum(1 for s in meetings if s.get("sentimento") == "preocupante")

        rows = ""
        for s in meetings:
            ata   = s.get("ata_link", "")
            ata_btn = (
                f'<a href="{ata}" style="font-size:11px;color:#1E2761;'
                f'text-decoration:underline;white-space:nowrap">Ver ata →</a>'
                if ata else "—"
            )
            data_str = s.get("data_reuniao", s.get("_date", "—"))
            fase     = s.get("fase", "BP")
            duracao  = s.get("duracao_estimada", "—")
            rows += f"""
            <tr>
              <td style="padding:9px 12px;border-bottom:1px solid #e0e4f0;
                         font-size:12px;color:#64748B;white-space:nowrap">{data_str}</td>
              <td style="padding:9px 12px;border-bottom:1px solid #e0e4f0;
                         font-size:13px;color:#1E293B;font-weight:600">{s.get("cliente","—")}</td>
              <td style="padding:9px 12px;border-bottom:1px solid #e0e4f0;
                         font-size:12px;color:#374151">{s.get("titulo_reuniao","—")}</td>
              <td style="padding:9px 12px;border-bottom:1px solid #e0e4f0;
                         font-size:12px;color:#374151">{fase}</td>
              <td style="padding:9px 12px;border-bottom:1px solid #e0e4f0;
                         font-size:12px;color:#64748B;white-space:nowrap">{duracao}</td>
              <td style="padding:9px 12px;border-bottom:1px solid #e0e4f0">{_sentiment_badge(s.get("sentimento","neutro"))}</td>
              <td style="padding:9px 12px;border-bottom:1px solid #e0e4f0">{ata_btn}</td>
            </tr>"""

        stat_color = "#DC2626" if n_preo else ("#0D9488" if n_pos == len(meetings) else "#D97706")
        consultant_sections += f"""
        <div style="margin-bottom:24px">
          <div style="display:flex;align-items:center;justify-content:space-between;
                      margin-bottom:8px">
            <h3 style="margin:0;font-size:15px;color:#1E2761">{consultor}</h3>
            <span style="font-size:11px;color:{stat_color};font-weight:700">
              {len(meetings)} reunião(ões)
              {f' · {n_preo} alerta(s)' if n_preo else ''}
            </span>
          </div>
          <table style="width:100%;border-collapse:collapse;font-size:13px">
            <thead>
              <tr style="background:#1E2761">
                <th style="padding:8px 12px;text-align:left;color:#CADCFC;font-size:11px">Data</th>
                <th style="padding:8px 12px;text-align:left;color:#CADCFC;font-size:11px">Cliente</th>
                <th style="padding:8px 12px;text-align:left;color:#CADCFC;font-size:11px">Reunião</th>
                <th style="padding:8px 12px;text-align:left;color:#CADCFC;font-size:11px">Fase</th>
                <th style="padding:8px 12px;text-align:left;color:#CADCFC;font-size:11px">Duração</th>
                <th style="padding:8px 12px;text-align:left;color:#CADCFC;font-size:11px">Sentimento</th>
                <th style="padding:8px 12px;text-align:left;color:#CADCFC;font-size:11px">Ata</th>
              </tr>
            </thead>
            <tbody>{rows}</tbody>
          </table>
        </div>"""

    sem_inicio = start.strftime("%d/%m")
    sem_fim    = end.strftime("%d/%m/%Y")

    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:720px;margin:0 auto;padding:24px">
      <div style="background:#1E2761;padding:28px;border-radius:10px 10px 0 0">
        <h2 style="color:#CADCFC;margin:0;font-size:22px">
          Resumo Semanal de Reuniões — {sem_inicio} a {sem_fim}
        </h2>
        <p style="color:#8899CC;margin:8px 0 0;font-size:13px">
          {total} reunião(ões) · {n_clientes} cliente(s) · {len(grouped)} consultor(es)
        </p>
      </div>
      <div style="background:#F7F9FF;padding:24px 28px;border:1px solid #e0e4f0;
                  border-top:none;border-radius:0 0 10px 10px">
        {alert_banner}
        {changes_section}
        {consultant_sections}
        <p style="font-size:11px;color:#94A3B8;text-align:center;margin-top:8px">
          Gerado automaticamente · Agente de Reuniões GoAkira · Claude Haiku 4.5
        </p>
      </div>
    </body></html>"""


def send_weekly_report(summaries_dir: str = ".") -> None:
    start, end = _previous_week_range()
    print(f"Relatório semanal: {start.strftime('%d/%m')} a {end.strftime('%d/%m/%Y')}")

    summaries = _load_week_summaries(start, end, summaries_dir)
    if not summaries:
        print(f"   Nenhuma reunião encontrada na semana de {start} a {end}.")
        return

    grouped = _group_by_consultant(summaries)
    print(f"   {len(summaries)} reunião(ões) · {len(grouped)} consultor(es)")

    try:
        from calendar_sync import get_calendar_changes
        calendar_changes = get_calendar_changes(start, end)
        if calendar_changes:
            print(f"   📅 {len(calendar_changes)} alteração(ões) de agenda detectada(s)")
    except Exception as e:
        print(f"   Aviso: falha ao verificar alterações de agenda — {e}")
        calendar_changes = []

    html = _build_html(grouped, start, end, calendar_changes)
    pdf_bytes = generate_weekly_pdf(grouped, start, end)

    raw = os.environ.get("DIRECTORS_EMAILS", os.environ.get("RECIPIENT_EMAIL", ""))
    recipients = [e.strip() for e in raw.split(",") if e.strip()]
    if not recipients:
        print("   Aviso: nenhum destinatário configurado em DIRECTORS_EMAILS")
        return

    sem_inicio = start.strftime("%d/%m")
    sem_fim    = end.strftime("%d/%m/%Y")

    msg = MIMEMultipart("mixed")
    msg["Subject"] = (
        f"[GoAkira] Resumo Semanal — {sem_inicio} a {sem_fim} "
        f"({len(summaries)} reunião(ões) · {len(grouped)} consultor(es))"
    )
    msg["From"] = (
        f"{os.environ.get('SENDER_NAME', 'Agente de Reuniões GoAkira')} "
        f"<{os.environ['SMTP_USER']}>"
    )
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html, "html", "utf-8"))

    att = MIMEBase("application", "pdf")
    att.set_payload(pdf_bytes)
    encoders.encode_base64(att)
    att.add_header(
        "Content-Disposition", "attachment",
        filename=f"resumo_semanal_{start.isoformat()}.pdf",
    )
    msg.attach(att)

    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    with smtplib.SMTP_SSL(host, 465) as s:
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        s.sendmail(os.environ["SMTP_USER"], recipients, msg.as_string())

    print(f"   Relatório semanal enviado para: {', '.join(recipients)}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    send_weekly_report()
