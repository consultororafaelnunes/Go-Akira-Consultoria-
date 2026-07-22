"""
get_refresh_token.py — Gera o GOOGLE_REFRESH_TOKEN via login no navegador.

Pré-requisitos:
  - No Google Cloud Console, crie uma credencial OAuth do tipo "App de computador"
    (Desktop app) e tenha em mãos o Client ID e o Client Secret.
  - As APIs "Google Drive API" e "Gmail API" precisam estar ativadas no projeto.

Uso:
  # Opção A — informe client id/secret direto:
  python get_refresh_token.py --client-id XXX --client-secret YYY

  # Opção B — use um client_secret.json baixado do Console:
  python get_refresh_token.py --client-file client_secret.json

  # Opção C — leia de variáveis de ambiente já definidas (GOOGLE_CLIENT_ID/SECRET):
  python get_refresh_token.py

Ao final, copie o refresh token impresso para o seu arquivo .env.
"""

import argparse
import os
import sys

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()

# Escopos cobrindo todo o pipeline (Gmail leitura + Drive + Calendar leitura)
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/calendar.readonly",
]


def build_client_config(client_id: str, client_secret: str) -> dict:
    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-id")
    parser.add_argument("--client-secret")
    parser.add_argument("--client-file", help="Caminho do client_secret.json do Console")
    args = parser.parse_args()

    if args.client_file:
        flow = InstalledAppFlow.from_client_secrets_file(args.client_file, SCOPES)
    else:
        client_id     = args.client_id     or os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = args.client_secret or os.environ.get("GOOGLE_CLIENT_SECRET")
        if not client_id or not client_secret:
            print("❌ Faltam credenciais. Passe --client-id/--client-secret, "
                  "--client-file, ou defina GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET.")
            sys.exit(1)
        flow = InstalledAppFlow.from_client_config(
            build_client_config(client_id, client_secret), SCOPES
        )

    print("\n🌐 Abrindo o navegador para você autorizar o acesso...")
    print("   (faça login com a conta Google que tem o Gmail e o Drive do agente)\n")

    # access_type=offline + prompt=consent garante o refresh_token
    creds = flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent",
    )

    print("\n" + "=" * 64)
    print("✅ Autorização concluída! Copie a linha abaixo para o seu .env:\n")
    print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")
    print("=" * 64)


if __name__ == "__main__":
    main()
