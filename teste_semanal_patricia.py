"""
teste_semanal_patricia.py
Envia para a Patricia um resumo de todas as reuniões desta semana.
Executado uma única vez amanhã às 8h via Task Scheduler.
"""

from dotenv import load_dotenv
load_dotenv()

import os
import sys
from datetime import datetime

# Semana atual: desde segunda-feira 23/06/2026
DESDE = datetime(2026, 6, 23, 0, 0)
DESTINATARIO_TESTE = "patricia.cotti@goakira.com.br"

print("=" * 60)
print("TESTE SEMANAL — Patricia Cotti")
print(f"Período: {DESDE.strftime('%d/%m/%Y')} até hoje")
print("=" * 60)

# 1. Buscar transcrições da semana
from fetch_transcripts import fetch_drive_transcripts
transcripts = fetch_drive_transcripts(hours_back=None, since_date=DESDE)

if not transcripts:
    print("\nNenhuma transcrição encontrada esta semana.")
    sys.exit(0)

print(f"\n{len(transcripts)} transcrição(ões) encontrada(s)")

# 2. Sumarizar com Claude Haiku
from summarize import summarize_all
summaries = summarize_all(transcripts)

if not summaries:
    print("Nenhum resumo gerado.")
    sys.exit(0)

# 3. Criar atas no Drive
from create_minutes import create_all_minutes
create_all_minutes(summaries)

# 4. Gerar PDF
from generate_pdf import generate_pdf
pdf_bytes = generate_pdf(summaries)

# 5. Enviar só para Patricia (override do destinatário)
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from send_email import _build_html
from datetime import date

today = date.today().strftime("%d/%m/%Y")
clientes = len(set(s.get("cliente", "") for s in summaries))

msg = MIMEMultipart("mixed")
msg["Subject"] = (
    f"[GoAkira · TESTE] Resumo Semanal — {today} "
    f"({len(summaries)} reunião(ões) · {clientes} cliente(s))"
)
msg["From"] = f"Agente de Reuniões GoAkira <{os.environ['SMTP_USER']}>"
msg["To"]   = DESTINATARIO_TESTE
msg.attach(MIMEText(_build_html(summaries), "html", "utf-8"))

att = MIMEBase("application", "pdf")
att.set_payload(pdf_bytes)
encoders.encode_base64(att)
att.add_header("Content-Disposition", "attachment",
               filename=f"resumo_semanal_{date.today().isoformat()}.pdf")
msg.attach(att)

with smtplib.SMTP_SSL(os.environ.get("SMTP_HOST", "smtp.gmail.com"), 465) as s:
    s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
    s.sendmail(os.environ["SMTP_USER"], [DESTINATARIO_TESTE], msg.as_string())

print(f"\nTeste enviado para {DESTINATARIO_TESTE}")
print("=" * 60)
