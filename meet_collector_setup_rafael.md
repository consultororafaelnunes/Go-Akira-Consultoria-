# Meet Collector – acesso via DWD (sem chave)

## O que já está pronto
- Projeto GCP: `backup-vps-504817`
- Service account: `meet-collector@backup-vps-504817.iam.gserviceaccount.com`
- Client ID (DWD): `109382709593139755988`
- Você (`c10@goakira.com.br`) tem o papel **Criador de token da conta de serviço** direto na service account
- DWD autorizada no Admin Console com os escopos (somente leitura):
  - `https://www.googleapis.com/auth/meetings.space.readonly`
  - `https://www.googleapis.com/auth/drive.readonly`
  - `https://www.googleapis.com/auth/admin.directory.user.readonly`

## O que você precisa fazer
1. No projeto `backup-vps-504817`, confirmar que estas APIs estão ativas:
   - Google Meet REST API
   - Google Drive API
   - Admin SDK API
   - **IAM Service Account Credentials API**
2. Autenticar localmente com sua conta:
   ```
   gcloud auth application-default login
   ```
3. Usar o código abaixo. Não existe arquivo de chave; o JWT com `sub` é assinado via `signJwt`.

## Código base (Python)
```python
import time, json, google.auth, requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SA = "meet-collector@backup-vps-504817.iam.gserviceaccount.com"
SCOPES = ("https://www.googleapis.com/auth/meetings.space.readonly "
          "https://www.googleapis.com/auth/drive.readonly "
          "https://www.googleapis.com/auth/admin.directory.user.readonly")

def creds_for(user_email):
    src, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    src.refresh(Request())
    now = int(time.time())
    payload = {"iss": SA, "sub": user_email, "scope": SCOPES,
               "aud": "https://oauth2.googleapis.com/token",
               "iat": now, "exp": now + 3600}
    r = requests.post(
        f"https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/{SA}:signJwt",
        headers={"Authorization": f"Bearer {src.token}"},
        json={"payload": json.dumps(payload)})
    r.raise_for_status()
    tok = requests.post("https://oauth2.googleapis.com/token", data={
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": r.json()["signedJwt"]}).json()
    return Credentials(tok["access_token"])
```

Teste rápido:
```python
from googleapiclient.discovery import build
meet = build("meet", "v2", credentials=creds_for("usuario@goakira.com.br"))
print(meet.conferenceRecords().list().execute())
```

## Diretrizes da integração
- **Não rastrear por pasta/caminho.** Desde jul/2026 o Meet salva em `Google Meet/<reunião>/` e a antiga
  `Meet Recordings` virou `Google Meet/Legacy Meet Recordings`. Usar a Meet API
  (`conferenceRecords` → `recordings` / `transcripts`) e guardar o **file ID** do Drive, que não muda ao mover.
- **Ignorar atalhos** (`application/vnd.google-apps.shortcut`) ou deduplicar por `shortcutDetails.targetId`.
- **Histórico:** `files.list` por usuário com `mimeType='video/mp4'`, sem filtro de pasta.
- **Tempo real (opcional):** Google Workspace Events API para eventos de gravação/transcrição gerada.
- **Segurança:** o acesso vale para o Drive de todo o domínio. Manter somente leitura, não repassar
  credenciais para agentes de IA; os agentes devem consultar só o índice gerado pelo coletor.
