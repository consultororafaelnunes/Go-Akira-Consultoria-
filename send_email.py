"""
send_email.py — Envia o resumo diário por email (HTML + PDF em anexo).
"""

import os
import smtplib
from collections import Counter
from datetime import date
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _get_consultor(cliente: str) -> str:
    """Retorna o nome curto do consultor BP do cliente, ou '—' se não mapeado."""
    try:
        from consultants import get_bp_consultant
        nome = get_bp_consultant(cliente)
        return nome.split()[0] if nome else "—"   # só o primeiro nome
    except Exception:
        return "—"


def _build_html(summaries: list[dict], calendar_changes: list[dict] | None = None) -> str:
    sent_counts = Counter(s.get("sentimento", "neutro") for s in summaries)
    n_alerts    = sum(1 for s in summaries if s.get("alertas"))
    clientes    = len(set(s.get("cliente", "") for s in summaries))
    today       = date.today().strftime("%d/%m/%Y")

    from calendar_sync import render_changes_html
    changes_section = render_changes_html(calendar_changes or [])

    rows = ""
    for s in summaries:
        sent      = s.get("sentimento", "neutro")
        color     = {"positivo": "#0D9488", "preocupante": "#DC2626"}.get(sent, "#D97706")
        ata       = s.get("ata_link", "")
        ata_btn   = (
            f'<a href="{ata}" style="font-size:11px;color:#1E2761;text-decoration:underline">Ver ata →</a>'
            if ata else ""
        )
        cliente   = s.get("cliente", "—")
        consultor = _get_consultor(cliente)
        fase      = s.get("fase", "BP")
        duracao   = s.get("duracao_estimada", "—")
        rows += f"""
        <tr>
          <td style="padding:10px 14px;border-bottom:1px solid #e0e4f0">
            <b>{cliente}</b><br>
            <span style="font-size:11px;color:#64748B">{consultor}</span>
          </td>
          <td style="padding:10px 14px;border-bottom:1px solid #e0e4f0">{s.get("titulo_reuniao","—")}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #e0e4f0">{fase}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #e0e4f0">{duracao}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #e0e4f0;color:{color};font-weight:bold">{sent.capitalize()}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #e0e4f0">{ata_btn}</td>
        </tr>"""

    alert_banner = ""
    if n_alerts:
        alert_banner = f"""
        <p style="background:#FEE2E2;border-radius:6px;padding:10px 14px;color:#DC2626;font-size:13px;margin-bottom:16px">
          <b>⚠️ {n_alerts} reunião(ões) com alertas</b> — revise as atas com atenção.
        </p>"""

    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:680px;margin:0 auto;padding:24px">
      <div style="background:#1E2761;padding:28px;border-radius:10px 10px 0 0">
        <h2 style="color:#CADCFC;margin:0;font-size:22px">Resumo de Reuniões — {today}</h2>
        <p style="color:#8899CC;margin:8px 0 0;font-size:13px">{len(summaries)} reunião(ões) · {clientes} cliente(s)</p>
      </div>
      <div style="background:#F7F9FF;padding:20px 28px;border:1px solid #e0e4f0;border-top:none;border-radius:0 0 10px 10px">
        {alert_banner}
        {changes_section}
        <table style="width:100%;border-collapse:collapse;font-size:13px">
          <thead>
            <tr style="background:#1E2761;color:#CADCFC">
              <th style="padding:10px 14px;text-align:left">Cliente · Consultor</th>
              <th style="padding:10px 14px;text-align:left">Reunião</th>
              <th style="padding:10px 14px;text-align:left">Fase</th>
              <th style="padding:10px 14px;text-align:left">Duração</th>
              <th style="padding:10px 14px;text-align:left">Sentimento</th>
              <th style="padding:10px 14px;text-align:left">Ata</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
        <p style="font-size:11px;color:#94A3B8;text-align:center;margin-top:20px">
          Gerado automaticamente · Agente de Reuniões GoAkira · Claude Haiku 4.5
        </p>
      </div>
    </body></html>"""


def send_ata_notification(summary: dict, ata_link: str, destinatario_email: str) -> None:
    """
    Envia notificação ao consultor responsável quando uma ata é criada.

    Args:
        summary:             Dict com os dados do resumo da reunião.
        ata_link:            Link do Google Doc gerado no Drive.
        destinatario_email:  E-mail do consultor responsável pelo cliente.
    """
    cliente      = summary.get("cliente", "Cliente")
    titulo       = summary.get("titulo_reuniao", "Reunião")
    data         = summary.get("data_reuniao", date.today().strftime("%d/%m/%Y"))
    resumo       = summary.get("resumo", "—")
    acionaveis   = summary.get("acionaveis", [])
    proximos     = summary.get("proximos_passos", [])
    sentimento   = summary.get("sentimento", "neutro").capitalize()
    sent_color   = {"Positivo": "#0D9488", "Preocupante": "#DC2626"}.get(sentimento, "#D97706")

    def _bullets(items):
        if not items:
            return "<li style='color:#94A3B8'>—</li>"
        return "".join(f"<li style='margin-bottom:4px'>{i}</li>" for i in items)

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto;padding:24px">
      <div style="background:#1E2761;padding:24px 28px;border-radius:10px 10px 0 0">
        <h2 style="color:#CADCFC;margin:0;font-size:20px">Nova Ata de Reunião</h2>
        <p style="color:#8899CC;margin:6px 0 0;font-size:13px">{cliente} · {data}</p>
      </div>
      <div style="background:#F7F9FF;padding:20px 28px;border:1px solid #e0e4f0;border-top:none;border-radius:0 0 10px 10px">
        <p style="margin:0 0 4px"><b style="color:#1E2761">Reunião:</b> {titulo}</p>
        <p style="margin:0 0 16px">
          <b style="color:#1E2761">Sentimento:</b>
          <span style="color:{sent_color};font-weight:bold">{sentimento}</span>
        </p>

        <p style="margin:0 0 6px;font-weight:bold;color:#1E2761">Resumo Executivo</p>
        <p style="margin:0 0 16px;font-size:13px;color:#374151">{resumo}</p>

        <p style="margin:0 0 6px;font-weight:bold;color:#1E2761">Principais Acionáveis</p>
        <ul style="margin:0 0 16px;padding-left:20px;font-size:13px;color:#374151">
          {_bullets(acionaveis)}
        </ul>

        <p style="margin:0 0 6px;font-weight:bold;color:#1E2761">Próximos Passos</p>
        <ul style="margin:0 0 20px;padding-left:20px;font-size:13px;color:#374151">
          {_bullets(proximos)}
        </ul>

        <a href="{ata_link}"
           style="display:inline-block;background:#1E2761;color:#fff;padding:10px 20px;
                  border-radius:6px;text-decoration:none;font-size:13px;font-weight:bold">
          Ver Ata Completa no Drive →
        </a>

        <p style="font-size:11px;color:#94A3B8;margin-top:20px;text-align:center">
          Gerado automaticamente · Agente de Reuniões GoAkira
        </p>
      </div>
    </body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[GoAkira] Nova ata — {cliente} — {data}"
    msg["From"] = (
        f"{os.environ.get('SENDER_NAME', 'Agente GoAkira')} "
        f"<{os.environ['SMTP_USER']}>"
    )
    msg["To"] = destinatario_email
    msg.attach(MIMEText(html, "html", "utf-8"))

    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    with smtplib.SMTP_SSL(host, 465) as s:
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        s.send_message(msg)

    print(f"   Notificação enviada para {destinatario_email}")


def send_opportunity_alert(summary: dict, consultor_email: str | None) -> None:
    """
    Envia a "levantada de mão" comercial — alerta imediato quando o Claude
    identifica, durante a sumarização, uma oportunidade de outro serviço do
    ecossistema GoAkira mencionada pelo cliente. Vai para o consultor
    responsável (se houver email mapeado) + diretoria, na hora, sem esperar
    o relatório diário.
    """
    oportunidades = summary.get("oportunidades_comerciais") or []
    if not oportunidades:
        return

    cliente    = summary.get("cliente", "Cliente")
    titulo     = summary.get("titulo_reuniao", "Reunião")
    data       = summary.get("data_reuniao", date.today().strftime("%d/%m/%Y"))
    consultor  = summary.get("consultor", "—")

    itens_html = "".join(
        f"<li style='margin-bottom:8px'><b>{o.get('servico','—')}</b><br>"
        f"<span style='color:#374151'>{o.get('justificativa','—')}</span></li>"
        for o in oportunidades
    )

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto;padding:24px">
      <div style="background:#1E2761;padding:24px 28px;border-radius:10px 10px 0 0">
        <h2 style="color:#CADCFC;margin:0;font-size:20px">🖐️ Levantada de Mão — Oportunidade Comercial</h2>
        <p style="color:#8899CC;margin:6px 0 0;font-size:13px">{cliente} · {data} · {consultor}</p>
      </div>
      <div style="background:#F7F9FF;padding:20px 28px;border:1px solid #e0e4f0;border-top:none;border-radius:0 0 10px 10px">
        <p style="margin:0 0 4px"><b style="color:#1E2761">Reunião:</b> {titulo}</p>
        <p style="margin:16px 0 6px;font-weight:bold;color:#1E2761">Serviço(s) identificado(s)</p>
        <ul style="margin:0 0 16px;padding-left:20px;font-size:13px">
          {itens_html}
        </ul>
        <p style="font-size:12px;color:#64748B">
          Sinalizado automaticamente pelo Agente de Reuniões a partir da transcrição — vale
          confirmar com o cliente antes de qualquer abordagem comercial.
        </p>
        <p style="font-size:11px;color:#94A3B8;margin-top:20px;text-align:center">
          Gerado automaticamente · Agente de Reuniões GoAkira
        </p>
      </div>
    </body></html>"""

    raw_extra = os.environ.get("OPPORTUNITY_EXTRA_RECIPIENTS", "")
    recipients = list(dict.fromkeys(  # dedup preservando ordem
        ([consultor_email] if consultor_email else []) + _get_directors_emails()
        + [e.strip() for e in raw_extra.split(",") if e.strip()]
    ))
    if not recipients:
        print("   Aviso: nenhum destinatário para o alerta de oportunidade comercial")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[GoAkira] 🖐️ Oportunidade comercial — {cliente} — {data}"
    msg["From"] = (
        f"{os.environ.get('SENDER_NAME', 'Agente GoAkira')} "
        f"<{os.environ['SMTP_USER']}>"
    )
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html, "html", "utf-8"))

    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    with smtplib.SMTP_SSL(host, 465) as s:
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        s.sendmail(os.environ["SMTP_USER"], recipients, msg.as_string())

    print(f"   Alerta de oportunidade comercial enviado para: {', '.join(recipients)}")


def _get_directors_emails() -> list[str]:
    """Lê a lista de diretores de DIRECTORS_EMAILS (vírgula-separado) ou cai em RECIPIENT_EMAIL."""
    raw = os.environ.get("DIRECTORS_EMAILS", os.environ.get("RECIPIENT_EMAIL", ""))
    return [e.strip() for e in raw.split(",") if e.strip()]


def send_report(summaries: list[dict], pdf_bytes: bytes, calendar_changes: list[dict] | None = None) -> None:
    """Envia o resumo diário para todos os diretores (HTML + PDF em anexo)."""
    raw_extra = os.environ.get("DAILY_EXTRA_RECIPIENTS", "")
    recipients = list(dict.fromkeys(  # dedup preservando ordem
        _get_directors_emails() + [e.strip() for e in raw_extra.split(",") if e.strip()]
    ))
    if not recipients:
        print("   Aviso: nenhum destinatário configurado em DIRECTORS_EMAILS")
        return

    today    = date.today().strftime("%d/%m/%Y")
    clientes = len(set(s.get("cliente", "") for s in summaries))

    msg = MIMEMultipart("mixed")
    msg["Subject"] = (
        f"[GoAkira] Resumo de Reuniões — {today} "
        f"({len(summaries)} reunião(ões) · {clientes} cliente(s))"
    )
    msg["From"] = (
        f"{os.environ.get('SENDER_NAME', 'Agente de Reuniões GoAkira')} "
        f"<{os.environ['SMTP_USER']}>"
    )
    msg["To"] = ", ".join(recipients)

    msg.attach(MIMEText(_build_html(summaries, calendar_changes), "html", "utf-8"))

    att = MIMEBase("application", "pdf")
    att.set_payload(pdf_bytes)
    encoders.encode_base64(att)
    att.add_header(
        "Content-Disposition", "attachment",
        filename=f"resumo_{date.today().isoformat()}.pdf",
    )
    msg.attach(att)

    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    with smtplib.SMTP_SSL(host, 465) as s:
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        s.sendmail(os.environ["SMTP_USER"], recipients, msg.as_string())

    print(f"   Email diário enviado para: {', '.join(recipients)}")
