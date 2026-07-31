"""
weekly_levantadas.py — Relatório semanal das "Levantadas de Mão".

Consolida, na janela da semana, todas as oportunidades comerciais detectadas
nas reuniões (campo `oportunidades_comerciais` dos summaries_*.json) e envia
um e-mail-resumo no padrão visual GoAkira (navy/ice).

Diferente do alerta imediato de "Levantada de Mão" (send_email.py), que dispara
por reunião, este é o consolidado da semana: o que os clientes pediram/abriram,
por serviço, cliente, consultor e fase.

Uso:
    python weekly_levantadas.py --dry-run                # imprime, não envia
    python weekly_levantadas.py --to "a@x.com,b@y.com"   # envia p/ destinatários
    python weekly_levantadas.py --de 2026-07-27 --ate 2026-07-31 --to ...
"""

import os
import smtplib
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from weekly_report import _load_week_summaries

# navy/ice GoAkira
NAVY = "#1E2761"
ICE = "#CADCFC"
TEAL = "#0D9488"
AMBER = "#D97706"
SLATE = "#64748B"

# Cache de links de ata por (cliente, data) para evitar buscas repetidas no Drive
_ata_link_cache: dict[tuple[str, str], str] = {}
_drive_service = None


def _get_drive():
    global _drive_service
    if _drive_service is None:
        from googleapiclient.discovery import build
        from create_minutes import get_credentials
        _drive_service = build("drive", "v3", credentials=get_credentials())
    return _drive_service


def get_ata_link(cliente: str, data: str) -> str:
    """
    Busca no Drive a ata (Google Doc) do cliente naquela data e retorna o
    webViewLink. Nome do arquivo segue o padrão de create_minutes:
    'Ata — {cliente} — {data-com-hifens} — {assunto}'. Retorna '' se não achar.
    """
    key = (cliente, data)
    if key in _ata_link_cache:
        return _ata_link_cache[key]

    link = ""
    try:
        data_fn = (data or "").replace("/", "-")
        svc = _get_drive()
        # escapa aspas simples para a query do Drive
        cli_q = cliente.replace("'", "\\'")
        q = (
            f"name contains 'Ata — {cli_q}' and "
            f"mimeType='application/vnd.google-apps.document' and trashed=false"
        )
        res = svc.files().list(
            q=q, fields="files(id,name,webViewLink)", pageSize=25,
            includeItemsFromAllDrives=True, supportsAllDrives=True,
        ).execute()
        files = res.get("files", [])
        # prioriza o arquivo cujo nome contém a data exata da reunião
        match = next((f for f in files if data_fn and data_fn in f.get("name", "")), None)
        if not match and files:
            match = files[0]
        if match:
            link = match.get("webViewLink", "")
    except Exception as e:
        print(f"   Aviso: falha ao buscar ata de {cliente} ({data}) — {e}")

    _ata_link_cache[key] = link
    return link


def _current_week_range() -> tuple[date, date]:
    """Segunda a sexta da semana corrente (cadência seg-sex do pipeline)."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    return monday, friday


def _collect_levantadas(summaries: list[dict]) -> list[dict]:
    """
    Achata as oportunidades da semana em registros individuais, um por
    (reunião × serviço levantado).
    """
    itens = []
    for s in summaries:
        oc = s.get("oportunidades_comerciais") or []
        if not isinstance(oc, list):
            continue
        for op in oc:
            if not isinstance(op, dict):
                continue
            servico = (op.get("servico") or "").strip()
            if not servico:
                continue
            itens.append({
                "cliente": s.get("cliente", "—"),
                "consultor": s.get("consultor") or "—",
                "fase": s.get("fase") or "—",
                "data": s.get("data_reuniao", "—"),
                "titulo": s.get("titulo_reuniao", "—"),
                "servico": servico,
                "grau": (op.get("grau") or "").strip().lower(),          # qualificada | mencao | "" (histórico)
                "responsavel_citado": (op.get("responsavel_citado") or "").strip(),
                "justificativa": (op.get("justificativa") or "").strip(),
            })
    return itens


def _esc(t: str) -> str:
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _is_qualificada(r: dict) -> bool:
    return (r.get("grau") or "").lower() == "qualificada"


def _grau_badge(r: dict) -> str:
    """Selo de qualificação. Tudo que não é 'qualificada' é menção (topo do funil)."""
    if _is_qualificada(r):
        resp = r.get("responsavel_citado") or ""
        extra = f" · {_esc(resp)}" if resp else ""
        return (f"<span style='margin-left:6px;display:inline-block;background:{TEAL};color:#fff;"
                f"font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px'>🎯 Qualificada{extra}</span>")
    return (f"<span style='margin-left:6px;display:inline-block;background:#EEF2F7;color:{SLATE};"
            f"font-size:10px;font-weight:600;padding:2px 8px;border-radius:10px'>menção de contexto</span>")


def build_html(itens: list[dict], start: date, end: date) -> str:
    sem = f"{start.strftime('%d/%m')} a {end.strftime('%d/%m/%Y')}"
    n_itens = len(itens)
    n_qual = sum(1 for i in itens if _is_qualificada(i))
    n_mencao = n_itens - n_qual
    clientes = sorted(set(i["cliente"] for i in itens))
    servico_counts = Counter(i["servico"] for i in itens)
    reunioes = len(set((i["cliente"], i["data"], i["titulo"]) for i in itens))

    # Ranking de serviços mais pedidos
    ranking_rows = "".join(
        f"<tr>"
        f"<td style='padding:6px 12px;border-bottom:1px solid #e0e4f0;font-size:13px'>{_esc(serv)}</td>"
        f"<td style='padding:6px 12px;border-bottom:1px solid #e0e4f0;font-size:13px;text-align:right;"
        f"font-weight:700;color:{NAVY}'>{qtd}</td>"
        f"</tr>"
        for serv, qtd in servico_counts.most_common()
    )

    # Agrupa por cliente → reunião (data, título)
    por_cliente: dict[str, dict[tuple[str, str], list[dict]]] = {}
    for i in itens:
        reunioes_do_cliente = por_cliente.setdefault(i["cliente"], {})
        reunioes_do_cliente.setdefault((i["data"], i["titulo"]), []).append(i)

    cards = ""
    for cliente in clientes:
        reunioes_cli = por_cliente[cliente]
        consultor = next(iter(reunioes_cli.values()))[0]["consultor"]
        fase = next(iter(reunioes_cli.values()))[0]["fase"]
        n_lev = sum(len(v) for v in reunioes_cli.values())

        blocos_reuniao = ""
        for (data, titulo), regs in sorted(reunioes_cli.items()):
            link = get_ata_link(cliente, data)
            ata_html = (
                f"<a href='{link}' style='font-size:11px;color:{TEAL};text-decoration:none;font-weight:700'>"
                f"📄 Ver ata →</a>" if link else
                f"<span style='font-size:11px;color:#94A3B8'>ata não localizada</span>"
            )
            linhas_serv = "".join(
                f"<div style='margin:8px 0 0'>"
                f"<span style='display:inline-block;background:{ICE};color:{NAVY};font-size:12px;"
                f"font-weight:700;padding:3px 10px;border-radius:12px'>{_esc(r['servico'])}</span>"
                f"{_grau_badge(r)}"
                f"<p style='margin:5px 0 0;font-size:13px;color:#334155;line-height:1.45'>{_esc(r['justificativa'])}</p>"
                f"</div>"
                for r in sorted(regs, key=lambda x: 0 if x.get('grau') == 'qualificada' else 1)
            )
            blocos_reuniao += f"""
            <div style="margin-top:12px;padding-top:12px;border-top:1px dashed #e0e4f0">
              <div style="display:flex;justify-content:space-between;align-items:baseline">
                <span style="font-size:12px;color:{SLATE}">{_esc(titulo)} · {_esc(data)}</span>
                {ata_html}
              </div>
              {linhas_serv}
            </div>"""

        cards += f"""
        <div style="background:#fff;border:1px solid #e0e4f0;border-left:4px solid {AMBER};
                    border-radius:8px;padding:16px 18px;margin-bottom:14px">
          <div style="display:flex;justify-content:space-between;align-items:baseline">
            <span style="font-size:16px;font-weight:700;color:{NAVY}">{_esc(cliente)}</span>
            <span style="font-size:11px;color:{SLATE}">{_esc(consultor)} · fase {_esc(fase)}</span>
          </div>
          <div style="font-size:12px;color:{SLATE};margin-top:2px">{n_lev} levantada(s) · {len(reunioes_cli)} reunião(ões)</div>
          {blocos_reuniao}
        </div>"""

    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:680px;margin:0 auto;padding:24px;background:#F7F9FF">
      <div style="background:{NAVY};padding:26px 28px 20px;border-radius:10px 10px 0 0">
        <h2 style="color:{ICE};margin:0;font-size:22px">🖐️ Levantadas de Mão — Semana</h2>
        <p style="color:#8899CC;margin:8px 0 0;font-size:13px">Resumo das oportunidades comerciais abertas nas reuniões · {sem}</p>
      </div>
      <div style="background:#fff;padding:22px 28px;border:1px solid #e0e4f0;border-top:none;border-radius:0 0 10px 10px">

        <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:12px;margin-bottom:22px">
          <div style="background:#F7F9FF;border-radius:8px;padding:14px;text-align:center;border:1px solid #e0e4f0">
            <div style="font-size:28px;font-weight:700;color:{AMBER}">{n_itens}</div>
            <div style="font-size:11px;color:{SLATE}">Levantadas</div>
          </div>
          <div style="background:#F7F9FF;border-radius:8px;padding:14px;text-align:center;border:1px solid #e0e4f0">
            <div style="font-size:28px;font-weight:700;color:{SLATE}">{n_mencao}</div>
            <div style="font-size:11px;color:{SLATE}">Menções (topo)</div>
          </div>
          <div style="background:#F7F9FF;border-radius:8px;padding:14px;text-align:center;border:1px solid #e0e4f0">
            <div style="font-size:28px;font-weight:700;color:{TEAL}">{n_qual}</div>
            <div style="font-size:11px;color:{SLATE}">Qualificadas 🎯</div>
          </div>
          <div style="background:#F7F9FF;border-radius:8px;padding:14px;text-align:center;border:1px solid #e0e4f0">
            <div style="font-size:28px;font-weight:700;color:{NAVY}">{len(clientes)}</div>
            <div style="font-size:11px;color:{SLATE}">Clientes</div>
          </div>
        </div>

        <div style="background:#F0FDFA;border:1px solid #99F6E4;border-radius:8px;padding:12px 16px;margin-bottom:22px;font-size:12px;color:#334155;line-height:1.5">
          <b style="color:{NAVY}">Funil de vendas do ecossistema:</b>
          <span style="display:inline-block;background:#EEF2F7;color:{SLATE};font-size:11px;font-weight:600;padding:1px 8px;border-radius:10px">menção de contexto</span>
          = oportunidade latente identificada dentro do projeto &nbsp;→&nbsp;
          <span style="display:inline-block;background:{TEAL};color:#fff;font-size:11px;font-weight:700;padding:1px 8px;border-radius:10px">🎯 Qualificada</span>
          = o consultor percebeu abertura e citou o responsável comercial (Bianca / Fabiana / Naka) para uma reunião de vendas.
        </div>

        <h3 style="font-size:14px;color:{NAVY};margin:0 0 8px">Serviços mais pedidos na semana</h3>
        <table style="width:100%;border-collapse:collapse;margin-bottom:24px">
          <thead>
            <tr style="background:{NAVY};color:{ICE}">
              <th style="padding:7px 12px;text-align:left;font-size:12px">Serviço</th>
              <th style="padding:7px 12px;text-align:right;font-size:12px">Qtd</th>
            </tr>
          </thead>
          <tbody>{ranking_rows}</tbody>
        </table>

        <h3 style="font-size:14px;color:{NAVY};margin:0 0 12px">Detalhe por cliente</h3>
        {cards}

        <hr style="border:none;border-top:1px solid #e0e4f0;margin:22px 0 12px">
        <p style="font-size:11px;color:#94A3B8;text-align:center">
          Gerado automaticamente · Agente de Reuniões GoAkira · "Levantada de mão" = oportunidade comercial detectada nas reuniões
        </p>
      </div>
    </body></html>"""


def build_empty_html(start: date, end: date) -> str:
    sem = f"{start.strftime('%d/%m')} a {end.strftime('%d/%m/%Y')}"
    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:680px;margin:0 auto;padding:24px;background:#F7F9FF">
      <div style="background:{NAVY};padding:26px 28px 20px;border-radius:10px 10px 0 0">
        <h2 style="color:{ICE};margin:0;font-size:22px">🖐️ Levantadas de Mão — Semana</h2>
        <p style="color:#8899CC;margin:8px 0 0;font-size:13px">Resumo das oportunidades comerciais abertas nas reuniões · {sem}</p>
      </div>
      <div style="background:#fff;padding:28px;border:1px solid #e0e4f0;border-top:none;border-radius:0 0 10px 10px;text-align:center">
        <div style="font-size:40px">✅</div>
        <p style="font-size:15px;color:{NAVY};font-weight:700;margin:8px 0 4px">Nenhuma levantada de mão nesta semana</p>
        <p style="font-size:13px;color:{SLATE};margin:0;line-height:1.5">
          Nenhuma oportunidade de outro serviço do ecossistema foi sinalizada nas reuniões da semana.
          O agente rodou normalmente — este aviso confirma que não houve levantadas a reportar.
        </p>
        <p style="font-size:11px;color:#94A3B8;margin-top:22px">Agente de Reuniões GoAkira</p>
      </div>
    </body></html>"""


def send(html: str, recipients: list[str], start: date, end: date, n_itens: int) -> None:
    sem = f"{start.strftime('%d/%m')} a {end.strftime('%d/%m')}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[GoAkira] Levantadas de Mão — Semana {sem} ({n_itens})"
    msg["From"] = f"{os.environ.get('SENDER_NAME','Agente de Reuniões GoAkira')} <{os.environ['SMTP_USER']}>"
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html, "html", "utf-8"))

    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    with smtplib.SMTP_SSL(host, 465) as s:
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        s.sendmail(os.environ["SMTP_USER"], recipients, msg.as_string())
    print(f"   E-mail enviado para: {', '.join(recipients)}")


def run(de: str | None, ate: str | None, to: str | None, dry_run: bool,
        anterior: bool = False) -> None:
    if de and ate:
        start = datetime.strptime(de, "%Y-%m-%d").date()
        end = datetime.strptime(ate, "%Y-%m-%d").date()
    elif anterior:
        # semana passada (seg-sex) — usado no envio agendado de segunda de manhã
        from weekly_report import _previous_week_range
        start, end = _previous_week_range()
    else:
        start, end = _current_week_range()

    print(f"\n🖐️  Levantadas de Mão — {start:%d/%m} a {end:%d/%m/%Y}")
    summaries = _load_week_summaries(start, end)
    itens = _collect_levantadas(summaries)
    print(f"   {len(itens)} levantada(s) em {len(set(i['cliente'] for i in itens))} cliente(s)")

    vazio = not itens
    html = build_empty_html(start, end) if vazio else build_html(itens, start, end)

    if dry_run:
        out = Path("preview_levantadas.html")
        out.write_text(html, encoding="utf-8")
        estado = "VAZIO" if vazio else f"{len(itens)} levantada(s)"
        print(f"🔍 Dry-run [{estado}] — HTML salvo em {out.resolve()} (nenhum e-mail enviado)")
        return

    raw_to = to or os.environ.get("LEVANTADAS_RECIPIENTS", "")
    recipients = [e.strip() for e in raw_to.split(",") if e.strip()]
    if not recipients:
        print("❌ Nenhum destinatário (--to ou LEVANTADAS_RECIPIENTS). Abortando.")
        sys.exit(1)
    send(html, recipients, start, end, len(itens))
    print("✅ Concluído.")


if __name__ == "__main__":
    import argparse
    from dotenv import load_dotenv

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    load_dotenv()

    p = argparse.ArgumentParser()
    p.add_argument("--de", help="Data inicial YYYY-MM-DD (padrão: segunda da semana atual)")
    p.add_argument("--ate", help="Data final YYYY-MM-DD (padrão: sexta da semana atual)")
    p.add_argument("--anterior", action="store_true",
                   help="Usa a semana passada (seg-sex) — para o envio agendado de segunda de manhã")
    p.add_argument("--to", help="Destinatários (vírgula). Padrão: LEVANTADAS_RECIPIENTS do .env")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    run(args.de, args.ate, args.to, args.dry_run, anterior=args.anterior)
