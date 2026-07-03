"""
teste_mensal_junho_patricia.py
Gera e envia o consolidado de Junho/2026 para Patricia calibrar o template.
Executado uma única vez amanhã às 10h via Task Scheduler.
"""

from dotenv import load_dotenv
load_dotenv()

import json
import os
import sys
from datetime import datetime
from pathlib import Path

DESTINATARIA   = "patricia.cotti@goakira.com.br"
MES_ANO        = "Junho 2026"
SINCE          = datetime(2026, 6, 1, 0, 0)
UNTIL          = datetime(2026, 6, 30, 23, 59)
SUMMARIES_FILE = Path("summaries_junho_2026_teste.json")

print("=" * 60)
print(f"TESTE MENSAL — {MES_ANO}")
print(f"Destinatária: {DESTINATARIA}")
print("=" * 60)

# ── 1. Buscar transcrições de junho ───────────────────────────────────────────
from fetch_transcripts import fetch_drive_transcripts
print("\n[1/5] Buscando transcrições de junho no Drive...")
transcripts = fetch_drive_transcripts(hours_back=None, since_date=SINCE, until_date=UNTIL)

if not transcripts:
    print("Nenhuma transcrição encontrada em junho.")
    sys.exit(0)

print(f"   {len(transcripts)} transcrição(ões) encontrada(s)")

# ── 2. Sumarizar com Claude Haiku ─────────────────────────────────────────────
from summarize import summarize_all
print("\n[2/5] Sumarizando com Claude Haiku...")
summaries = summarize_all(transcripts)

if not summaries:
    print("Nenhum resumo gerado.")
    sys.exit(0)

# Persiste JSON (fonte para o PPTX)
SUMMARIES_FILE.write_text(json.dumps(summaries, ensure_ascii=False, indent=2))
print(f"   {len(summaries)} resumo(s) | salvo em {SUMMARIES_FILE}")

# ── 3. Gerar PPTX via Node.js ─────────────────────────────────────────────────
import subprocess
pptx_path = "relatorio_mensal_junho_2026_teste.pptx"
script_dir = Path(__file__).parent
js_script  = script_dir / "generate_monthly_report.js"

print("\n[3/5] Gerando PPTX...")
pptx_ok = False
try:
    result = subprocess.run(
        ["node", str(js_script), str(SUMMARIES_FILE), pptx_path, MES_ANO],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode == 0:
        print(f"   PPTX gerado: {pptx_path}")
        pptx_ok = True
    else:
        print(f"   Aviso: PPTX falhou — {result.stderr[:200]}")
except Exception as e:
    print(f"   Aviso: Node.js indisponível — {e}")

# ── 4. Gerar PDF (sempre como backup e anexo complementar) ────────────────────
from generate_pdf import generate_pdf
print("\n[4/5] Gerando PDF...")
pdf_bytes = generate_pdf(summaries)
print(f"   PDF gerado ({len(pdf_bytes)//1024}KB)")

# ── 5. Enviar e-mail para Patricia ────────────────────────────────────────────
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from monthly_report import _get_consultor_monthly
from datetime import date

print(f"\n[5/5] Enviando para {DESTINATARIA}...")

clientes    = len(set(s.get("cliente", "") for s in summaries))
n_positivos = sum(1 for s in summaries if s.get("sentimento") == "positivo")
n_alertas   = sum(1 for s in summaries if s.get("alertas"))

# Tabela de reuniões
rows = "".join(
    f"<tr>"
    f"<td style='padding:7px 12px;border-bottom:1px solid #e0e4f0'>"
    f"<b>{s.get('cliente','—')}</b><br>"
    f"<span style='font-size:10px;color:#64748B'>{_get_consultor_monthly(s.get('cliente',''))}</span></td>"
    f"<td style='padding:7px 12px;border-bottom:1px solid #e0e4f0'>{s.get('titulo_reuniao','—')}</td>"
    f"<td style='padding:7px 12px;border-bottom:1px solid #e0e4f0'>{s.get('data_reuniao','—')}</td>"
    f"<td style='padding:7px 12px;border-bottom:1px solid #e0e4f0;"
    f"color:{ {'positivo':'#0D9488','neutro':'#D97706','preocupante':'#DC2626'}.get(s.get('sentimento','neutro'),'#D97706') }"
    f";font-weight:bold'>{s.get('sentimento','—').capitalize()}</td>"
    f"</tr>"
    for s in summaries
)

alerta_banner = (
    f"<p style='background:#FEE2E2;border-radius:6px;padding:10px 14px;"
    f"color:#DC2626;font-size:13px;margin-bottom:16px'>"
    f"<b>⚠️ {n_alertas} reunião(ões) com alertas críticos</b></p>"
    if n_alertas else ""
)

html = f"""
<html><body style="font-family:Arial,sans-serif;max-width:680px;margin:0 auto;padding:24px">
  <div style="background:#1E2761;padding:28px;border-radius:10px 10px 0 0">
    <h2 style="color:#CADCFC;margin:0;font-size:24px">Consolidado Mensal — {MES_ANO}</h2>
    <p style="color:#8899CC;margin:8px 0 0;font-size:13px">
      Compilação completa do mês · <b style="color:#CADCFC">[TESTE — Para calibração do template]</b>
    </p>
  </div>
  <div style="background:#F7F9FF;padding:20px 28px;border:1px solid #e0e4f0;border-top:none;border-radius:0 0 10px 10px">
    <div style="display:flex;gap:12px;margin-bottom:20px">
      <div style="flex:1;background:#fff;border-radius:8px;padding:14px;text-align:center;border:1px solid #e0e4f0">
        <div style="font-size:28px;font-weight:700;color:#1E2761">{len(summaries)}</div>
        <div style="font-size:11px;color:#64748B">Reuniões</div>
      </div>
      <div style="flex:1;background:#fff;border-radius:8px;padding:14px;text-align:center;border:1px solid #e0e4f0">
        <div style="font-size:28px;font-weight:700;color:#1E2761">{clientes}</div>
        <div style="font-size:11px;color:#64748B">Clientes</div>
      </div>
      <div style="flex:1;background:#fff;border-radius:8px;padding:14px;text-align:center;border:1px solid #e0e4f0">
        <div style="font-size:28px;font-weight:700;color:#0D9488">{n_positivos}</div>
        <div style="font-size:11px;color:#64748B">Positivas</div>
      </div>
      <div style="flex:1;background:#fff;border-radius:8px;padding:14px;text-align:center;border:1px solid #e0e4f0">
        <div style="font-size:28px;font-weight:700;color:#DC2626">{n_alertas}</div>
        <div style="font-size:11px;color:#64748B">Com alertas</div>
      </div>
    </div>
    {alerta_banner}
    <p style="font-weight:bold;color:#1E2761;margin-bottom:8px">Todas as reuniões do mês</p>
    <table style="width:100%;border-collapse:collapse;font-size:12px">
      <thead>
        <tr style="background:#1E2761;color:#CADCFC">
          <th style="padding:8px 12px;text-align:left">Cliente · Consultor</th>
          <th style="padding:8px 12px;text-align:left">Reunião</th>
          <th style="padding:8px 12px;text-align:left">Data</th>
          <th style="padding:8px 12px;text-align:left">Sentimento</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    <hr style="border:none;border-top:1px solid #e0e4f0;margin:20px 0">
    <p style="font-size:11px;color:#94A3B8;text-align:center">
      Gerado automaticamente · Agente de Reuniões GoAkira · Claude Haiku 4.5
    </p>
  </div>
</body></html>"""

msg = MIMEMultipart("mixed")
msg["Subject"] = f"[GoAkira · TESTE] Consolidado Mensal — {MES_ANO} ({len(summaries)} reuniões · {clientes} clientes)"
msg["From"]    = f"Agente de Reuniões GoAkira <{os.environ['SMTP_USER']}>"
msg["To"]      = DESTINATARIA
msg.attach(MIMEText(html, "html", "utf-8"))

# Anexa PPTX se gerado, PDF sempre
if pptx_ok and Path(pptx_path).exists():
    with open(pptx_path, "rb") as f:
        att = MIMEBase("application", "vnd.openxmlformats-officedocument.presentationml.presentation")
        att.set_payload(f.read())
        encoders.encode_base64(att)
        att.add_header("Content-Disposition", "attachment", filename=Path(pptx_path).name)
        msg.attach(att)

att_pdf = MIMEBase("application", "pdf")
att_pdf.set_payload(pdf_bytes)
encoders.encode_base64(att_pdf)
att_pdf.add_header("Content-Disposition", "attachment",
                   filename=f"consolidado_junho_2026.pdf")
msg.attach(att_pdf)

with smtplib.SMTP_SSL(os.environ.get("SMTP_HOST", "smtp.gmail.com"), 465) as s:
    s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
    s.sendmail(os.environ["SMTP_USER"], [DESTINATARIA], msg.as_string())

print(f"\nConsolidado enviado para {DESTINATARIA}")
if pptx_ok:
    print("Anexos: PPTX + PDF")
else:
    print("Anexo: PDF (PPTX indisponível)")

# Limpa arquivos temporários
SUMMARIES_FILE.unlink(missing_ok=True)
print("=" * 60)
