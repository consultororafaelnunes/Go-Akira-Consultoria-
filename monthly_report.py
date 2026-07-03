"""
monthly_report.py — Orquestra o relatório mensal:
  1. Coleta todos os JSON de resumos do mês de um bucket/Drive ou pasta local
  2. Chama generate_monthly_report.js via subprocess para gerar o PPTX
  3. Faz upload do PPTX para a pasta 'Relatórios Mensais' no Google Drive
  4. Envia email de entrega com link + arquivo em anexo
"""

import json
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


# ── Helpers Google ────────────────────────────────────────────────────────────

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def get_credentials() -> Credentials:
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def find_or_create_folder(drive_service, name: str, parent_id: str | None = None) -> str:
    """Encontra ou cria uma pasta no Drive. Retorna o folder_id."""
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    res = drive_service.files().list(q=query, fields="files(id)", pageSize=1).execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]

    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        meta["parents"] = [parent_id]
    folder = drive_service.files().create(body=meta, fields="id").execute()
    return folder["id"]


def upload_pptx_to_drive(pptx_path: str, filename: str, folder_id: str) -> str:
    """Faz upload do PPTX para o Drive. Retorna o webViewLink."""
    creds = get_credentials()
    drive_service = build("drive", "v3", credentials=creds)

    media = MediaFileUpload(
        pptx_path,
        mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        resumable=False,
    )
    meta = {
        "name": filename,
        "parents": [folder_id],
        "mimeType": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
    file = drive_service.files().create(
        body=meta, media_body=media, fields="id,webViewLink"
    ).execute()

    link = file.get("webViewLink", "")
    print(f"   ☁️  Uploaded para o Drive: {link}")
    return link


# ── Coleta de resumos do mês ──────────────────────────────────────────────────

def collect_monthly_summaries(year: int, month: int, summaries_dir: str = ".") -> list[dict]:
    """
    Lê todos os arquivos summaries_YYYY-MM-DD.json do mês indicado
    no diretório local (gerados pelo pipeline diário).
    Retorna lista consolidada de resumos.
    """
    prefix = f"summaries_{year}-{month:02d}-"
    all_summaries = []

    for p in sorted(Path(summaries_dir).glob(f"{prefix}*.json")):
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                all_summaries.extend(data)
            elif isinstance(data, dict):
                all_summaries.append(data)

    print(f"   📂 {len(all_summaries)} resumo(s) carregado(s) de {summaries_dir}")
    return all_summaries


# ── Geração do PPTX ───────────────────────────────────────────────────────────

def generate_pptx(summaries: list[dict], output_path: str, mes_ano: str) -> str:
    """
    Salva os resumos em JSON temporário e chama o script Node.js para gerar o PPTX.
    Retorna o caminho do arquivo gerado.
    """
    # Salva JSON temporário para o script JS ler
    tmp_json = output_path.replace(".pptx", "_tmp.json")
    with open(tmp_json, "w", encoding="utf-8") as f:
        json.dump(summaries, f, ensure_ascii=False, indent=2)

    # Caminho do script JS
    script_dir = Path(__file__).parent
    js_script = script_dir / "generate_monthly_report.js"

    print(f"\n📊 Gerando PPTX via Node.js...")
    result = subprocess.run(
        ["node", str(js_script), tmp_json, output_path, mes_ano],
        capture_output=True, text=True,
    )

    if result.stdout:
        print(result.stdout)
    if result.returncode != 0:
        print(f"❌ Erro no Node.js:\n{result.stderr}")
        raise RuntimeError(f"Falha ao gerar PPTX: {result.stderr[:500]}")

    # Limpa JSON temporário
    Path(tmp_json).unlink(missing_ok=True)
    return output_path


# ── Email de entrega ──────────────────────────────────────────────────────────

def _get_consultor_monthly(cliente: str) -> str:
    try:
        from consultants import get_bp_consultant
        return get_bp_consultant(cliente) or "—"
    except Exception:
        return "—"


def send_monthly_email(pptx_path: str, drive_link: str, summaries: list[dict], mes_ano: str) -> None:
    """Envia o email de entrega do relatório mensal com o PPTX em anexo."""
    import smtplib
    from email import encoders
    from email.mime.base import MIMEBase
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    from collections import Counter
    sent_counts = Counter(s.get("sentimento", "neutro") for s in summaries)
    n_alerts    = sum(1 for s in summaries if s.get("alertas"))
    clientes    = len(set(s.get("cliente", "") for s in summaries))

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:650px;margin:0 auto;padding:24px">
      <div style="background:#1E2761;padding:28px 28px 20px;border-radius:10px 10px 0 0">
        <h2 style="color:#CADCFC;margin:0;font-size:24px">📊 Relatório Mensal — {mes_ano}</h2>
        <p style="color:#8899CC;margin:8px 0 0;font-size:13px">Compilação completa do mês · arquivo PowerPoint em anexo</p>
      </div>
      <div style="background:#F7F9FF;padding:20px 28px;border:1px solid #e0e4f0;border-top:none;border-radius:0 0 10px 10px">
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:12px;margin-bottom:20px">
          <div style="background:#fff;border-radius:8px;padding:14px;text-align:center;border:1px solid #e0e4f0">
            <div style="font-size:28px;font-weight:700;color:#1E2761">{len(summaries)}</div>
            <div style="font-size:11px;color:#64748B">Reuniões</div>
          </div>
          <div style="background:#fff;border-radius:8px;padding:14px;text-align:center;border:1px solid #e0e4f0">
            <div style="font-size:28px;font-weight:700;color:#1E2761">{clientes}</div>
            <div style="font-size:11px;color:#64748B">Clientes</div>
          </div>
          <div style="background:#fff;border-radius:8px;padding:14px;text-align:center;border:1px solid #e0e4f0">
            <div style="font-size:28px;font-weight:700;color:#0D9488">{sent_counts["positivo"]}</div>
            <div style="font-size:11px;color:#64748B">Positivas</div>
          </div>
          <div style="background:#fff;border-radius:8px;padding:14px;text-align:center;border:1px solid #e0e4f0">
            <div style="font-size:28px;font-weight:700;color:#DC2626">{n_alerts}</div>
            <div style="font-size:11px;color:#64748B">Com alertas</div>
          </div>
        </div>
        {"<p style='background:#FEE2E2;border-radius:6px;padding:10px 14px;color:#DC2626;font-size:13px;margin-bottom:16px'><b>⚠️ " + str(n_alerts) + " reunião(ões) com alertas críticos</b> — veja detalhes no relatório.</p>" if n_alerts else ""}
        <p style="font-size:14px;color:#334155;margin-bottom:12px">O relatório completo está em anexo. Você também pode abrir diretamente no Google Drive:</p>
        <a href="{drive_link}" style="display:inline-block;background:#1E2761;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;font-size:13px">Abrir no Google Drive →</a>

        <hr style="border:none;border-top:1px solid #e0e4f0;margin:20px 0">

        <p style="font-weight:bold;color:#1E2761;margin-bottom:8px">Reuniões do mês</p>
        <table style="width:100%;border-collapse:collapse;font-size:12px">
          <thead>
            <tr style="background:#1E2761;color:#CADCFC">
              <th style="padding:8px 12px;text-align:left">Cliente · Consultor</th>
              <th style="padding:8px 12px;text-align:left">Reunião</th>
              <th style="padding:8px 12px;text-align:left">Data</th>
              <th style="padding:8px 12px;text-align:left">Sentimento</th>
            </tr>
          </thead>
          <tbody>
            {"".join(
                f"<tr>"
                f"<td style='padding:7px 12px;border-bottom:1px solid #e0e4f0'>"
                f"<b>{s.get('cliente','—')}</b><br>"
                f"<span style='font-size:10px;color:#64748B'>{_get_consultor_monthly(s.get('cliente',''))}</span></td>"
                f"<td style='padding:7px 12px;border-bottom:1px solid #e0e4f0'>{s.get('titulo_reuniao','—')}</td>"
                f"<td style='padding:7px 12px;border-bottom:1px solid #e0e4f0'>{s.get('data_reuniao','—')}</td>"
                f"<td style='padding:7px 12px;border-bottom:1px solid #e0e4f0;"
                f"color:{['#0D9488','#D97706','#DC2626'][['positivo','neutro','preocupante'].index(s.get('sentimento','neutro')) if s.get('sentimento','neutro') in ['positivo','neutro','preocupante'] else 1]}"
                f";font-weight:bold'>{s.get('sentimento','neutro').capitalize()}</td>"
                f"</tr>"
                for s in summaries
            )}
          </tbody>
        </table>

        <hr style="border:none;border-top:1px solid #e0e4f0;margin:20px 0">
        <p style="font-size:11px;color:#94A3B8;text-align:center">Gerado automaticamente · Agente de Reuniões GoAkira · Claude Haiku 4.5</p>
      </div>
    </body></html>"""

    raw_emails = os.environ.get("MONTHLY_RECIPIENTS", os.environ.get("RECIPIENT_EMAIL", ""))
    recipients = [e.strip() for e in raw_emails.split(",") if e.strip()]

    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"[GoAkira] Relatório Mensal — {mes_ano} ({len(summaries)} reunião(ões) · {clientes} cliente(s))"
    msg["From"]    = f"{os.environ.get('SENDER_NAME','Agente de Reuniões GoAkira')} <{os.environ['SMTP_USER']}>"
    msg["To"]      = ", ".join(recipients)
    msg.attach(MIMEText(html, "html", "utf-8"))

    with open(pptx_path, "rb") as f:
        att = MIMEBase("application", "vnd.openxmlformats-officedocument.presentationml.presentation")
        att.set_payload(f.read())
        encoders.encode_base64(att)
        att.add_header("Content-Disposition", "attachment",
                       filename=Path(pptx_path).name)
        msg.attach(att)

    with smtplib.SMTP_SSL(os.environ.get("SMTP_HOST","smtp.gmail.com"), 465) as s:
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        s.sendmail(os.environ["SMTP_USER"], recipients, msg.as_string())

    print(f"   Email mensal enviado para: {', '.join(recipients)}")


# ── Função principal ───────────────────────────────────────────────────────────

def run_monthly_report(
    year: int | None  = None,
    month: int | None = None,
    summaries_dir: str = ".",
    root_folder_id: str | None = None,
    dry_run: bool = False,
    mock: bool = False,
) -> None:
    """
    Gera e entrega o relatório mensal completo.
    
    Args:
        year, month:      Mês de referência (padrão: mês atual)
        summaries_dir:    Pasta com os arquivos summaries_YYYY-MM-DD.json
        root_folder_id:   Pasta raiz no Drive para salvar (ou DRIVE_ROOT_FOLDER_ID)
        dry_run:          Gera o PPTX mas não envia email nem faz upload
        mock:             Usa dados de exemplo
    """
    today = date.today()
    year  = year  or today.year
    month = month or today.month

    MONTH_PT = {
        1:"Janeiro",2:"Fevereiro",3:"Março",4:"Abril",5:"Maio",6:"Junho",
        7:"Julho",8:"Agosto",9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro",
    }
    mes_ano = f"{MONTH_PT[month]} {year}"

    print("\n" + "=" * 60)
    print(f"📅 Relatório Mensal — {mes_ano}")
    print("=" * 60)

    if mock:
        # Dados de demonstração
        summaries = _mock_monthly_data()
    else:
        summaries = collect_monthly_summaries(year, month, summaries_dir)

    if not summaries:
        print(f"ℹ️  Nenhum resumo encontrado para {mes_ano}. Encerrando.")
        return

    print(f"   → {len(summaries)} reunião(ões) | {len(set(s.get('cliente','') for s in summaries))} cliente(s)")

    # Gerar PPTX
    filename  = f"relatorio_mensal_{year}_{month:02d}.pptx"
    pptx_path = str(Path(summaries_dir) / filename)
    generate_pptx(summaries, pptx_path, mes_ano)

    if dry_run:
        print(f"\n🔍 Dry-run — PPTX salvo em: {pptx_path}\nUpload e email não realizados.")
        return

    # Upload para o Drive
    print("\n☁️  Fazendo upload para o Google Drive...")
    creds = get_credentials()
    drive_service = build("drive", "v3", credentials=creds)

    root_id = root_folder_id or os.environ.get("DRIVE_ROOT_FOLDER_ID")
    reports_folder_id = find_or_create_folder(drive_service, "Relatórios Mensais", root_id)
    year_folder_id    = find_or_create_folder(drive_service, str(year), reports_folder_id)

    drive_link = upload_pptx_to_drive(pptx_path, filename, year_folder_id)

    # Enviar email
    send_monthly_email(pptx_path, drive_link, summaries, mes_ano)

    print(f"\n✅ Relatório mensal concluído: {mes_ano}")


# ── Mock data ─────────────────────────────────────────────────────────────────

def _mock_monthly_data() -> list[dict]:
    """Gera dados de exemplo para testar sem o pipeline real."""
    import random
    clientes   = ["Acme Corp", "Beta Indústria", "Gamma Tecnologia", "Delta Serviços"]
    sentimentos = ["positivo", "positivo", "neutro", "preocupante"]
    prioridades = ["baixa",    "alta",      "media",  "alta"]
    summaries = []

    for i, (c, s, p) in enumerate(zip(clientes, sentimentos, prioridades)):
        for j in range(random.randint(2, 4)):
            summaries.append({
                "cliente":          c,
                "titulo_reuniao":   f"Reunião {j+1} — {c}",
                "data_reuniao":     f"{random.randint(1,28):02d}/05/2025",
                "duracao_estimada": f"{random.randint(30,90)}min",
                "participantes":    ["Ana Silva", "Carlos Mendes"],
                "resumo":           f"Reunião produtiva com {c}. Foram discutidos pontos de melhoria e alinhamento de expectativas para o próximo trimestre.",
                "acionaveis":       [f"Enviar proposta até dia {random.randint(5,20)}", "Agendar follow-up"],
                "proximos_passos":  [f"Demo agendada para semana de {random.randint(10,25)}/06"],
                "alertas":          ["Contrato em risco de cancelamento"] if s == "preocupante" and j == 0 else [],
                "sentimento":       s,
                "prioridade":       p,
            })

    return summaries


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    from dotenv import load_dotenv
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--year",  type=int)
    parser.add_argument("--month", type=int)
    parser.add_argument("--dir",   default=".", help="Pasta com os JSON de resumos")
    parser.add_argument("--dry-run",  action="store_true")
    parser.add_argument("--mock",     action="store_true")
    args = parser.parse_args()

    run_monthly_report(
        year=args.year, month=args.month,
        summaries_dir=args.dir,
        dry_run=args.dry_run, mock=args.mock,
    )
