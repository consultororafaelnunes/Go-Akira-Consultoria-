"""
monitor_agente.py — Monitora a execução do agente diário.

Roda 30 minutos após o agente (9h30). Lê as últimas linhas do agente.log,
detecta falhas reais e envia alerta para o Rafael. Se tudo correu bem, não envia nada.
"""

from dotenv import load_dotenv
load_dotenv()

import os
import smtplib
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

LOG_FILE        = Path(__file__).parent / "agente.log"
ALERTA_EMAIL    = os.environ.get("SMTP_USER", "c10@goakira.com.br")
LINHAS_RECENTES = 200

# Erros reais — condições que indicam falha crítica não tratada
ERROS_KEYWORDS = [
    "❌",
    "traceback (most recent",
    "error:",
    "exception:",
    "unauthorized",
    "crashed",
    "exit code 1",
]

# Padrões de aviso tratado — NÃO disparam alerta (são fallbacks esperados)
AVISOS_TRATADOS = [
    "aviso:",
    "⚠️  template não",
    "⚠️  falha — pulando",
    "⚠️  json inválido",
    "⚠️  rate limit",
    "pasta criada:",
    "pasta business plan nao encontrada",
    "usando pasta fallback",
    "consultor de bp não mapeado",
    "falha ao enviar notificação",
]

# Marcadores de sucesso do pipeline
SUCESSO_KEYWORDS = [
    "pipeline diário concluído",
    "email diário enviado",
    "ata(s) criada(s) com sucesso",
    "✅ pipeline",
]


def _ler_log_recente() -> str:
    if not LOG_FILE.exists():
        return ""
    linhas = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(linhas[-LINHAS_RECENTES:])


def _e_erro_real(linha: str) -> bool:
    """Retorna True apenas se a linha indicar erro crítico não tratado."""
    linha_lower = linha.lower()
    if not any(k in linha_lower for k in ERROS_KEYWORDS):
        return False
    # Exclui avisos tratados que contenham palavras de erro por acidente
    return not any(p in linha_lower for p in AVISOS_TRATADOS)


def _analisar(log: str) -> dict:
    log_lower = log.lower()
    erros = [linha for linha in log.splitlines() if _e_erro_real(linha)]
    sucesso = any(k in log_lower for k in SUCESSO_KEYWORDS)
    return {"erros": erros, "sucesso": sucesso}


def _enviar_alerta(erros: list[str], log_trecho: str) -> None:
    hoje  = date.today().strftime("%d/%m/%Y")
    lista = "".join(
        f"<li style='margin-bottom:4px;color:#DC2626'>{e}</li>"
        for e in erros[:20]
    )

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto;padding:24px">
      <div style="background:#DC2626;padding:20px 28px;border-radius:10px 10px 0 0">
        <h2 style="color:#fff;margin:0;font-size:18px">Agente GoAkira — Falha Critica</h2>
        <p style="color:#FFD5D5;margin:6px 0 0;font-size:13px">{hoje}</p>
      </div>
      <div style="background:#FFF7F7;padding:20px 28px;border:1px solid #FCA5A5;border-top:none;border-radius:0 0 10px 10px">
        <p style="color:#374151;margin-bottom:12px">
          O pipeline diario encontrou os seguintes erros criticos:
        </p>
        <ul style="padding-left:20px;font-size:13px">{lista}</ul>
        <hr style="border:none;border-top:1px solid #FCA5A5;margin:16px 0">
        <p style="font-weight:bold;color:#374151;margin-bottom:6px;font-size:12px">Trecho do log:</p>
        <pre style="background:#fff;border:1px solid #e5e7eb;border-radius:6px;padding:12px;
                    font-size:11px;color:#374151;overflow-x:auto;white-space:pre-wrap">{log_trecho[-2000:]}</pre>
        <p style="font-size:11px;color:#94A3B8;margin-top:16px;text-align:center">
          Monitor do Agente de Reunioes GoAkira
        </p>
      </div>
    </body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[GoAkira · ALERTA] Falha critica no agente — {hoje}"
    msg["From"]    = f"Monitor GoAkira <{os.environ['SMTP_USER']}>"
    msg["To"]      = ALERTA_EMAIL
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL(os.environ.get("SMTP_HOST", "smtp.gmail.com"), 465) as s:
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        s.sendmail(os.environ["SMTP_USER"], [ALERTA_EMAIL], msg.as_string())

    print(f"[{datetime.now():%H:%M}] Alerta enviado para {ALERTA_EMAIL}")


def main():
    agora = datetime.now()
    print(f"[{agora:%H:%M}] Monitor iniciado — verificando log...")

    log = _ler_log_recente()
    if not log:
        print("Log nao encontrado ou vazio — agente pode nao ter rodado hoje.")
        # Sem log = sem saida do pipeline = falha silenciosa
        _enviar_alerta(
            ["agente.log nao encontrado — o pipeline pode nao ter iniciado"],
            "Nenhum log disponivel.",
        )
        return

    resultado = _analisar(log)

    if resultado["erros"] and not resultado["sucesso"]:
        n = len(resultado["erros"])
        print(f"   {n} erro(s) critico(s) — pipeline nao concluiu — enviando alerta")
        _enviar_alerta(resultado["erros"], log)
    elif resultado["erros"] and resultado["sucesso"]:
        print(f"   Pipeline concluido com {len(resultado['erros'])} aviso(s) — sem alerta")
    else:
        print("   Pipeline concluido sem erros criticos — nenhuma acao necessaria")


if __name__ == "__main__":
    main()
