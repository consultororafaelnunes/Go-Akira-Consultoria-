"""
meet_api_collector.py — Coletor de gravações/transcrições do Google Meet via
Meet REST API + Domain-Wide Delegation (DWD), no lugar de varrer pastas do Drive.

Contexto: desde jul/2026 o Google move as gravações para uma pasta "Google Meet"
no Drive do ORGANIZADOR, que muda de estrutura sem aviso. O pipeline antigo
(fetch_transcripts.py) depende de cada consultor compartilhar essa pasta com
c10@goakira.com.br — o que já causou dois furos de cobertura (consultores cuja
pasta nunca foi compartilhada ficam invisíveis por meses). Este coletor lê
direto da Meet API, por usuário, sem depender de path/ID de pasta nenhuma.

Setup já feito (ver docs/DWD_MEET_API_SETUP.md e meet_collector_setup_rafael.md):
  - Projeto GCP: backup-vps-504817
  - Service account: meet-collector@backup-vps-504817.iam.gserviceaccount.com
  - Client ID (DWD): 109382709593139755988
  - DWD autorizada no Admin Console com os escopos (somente leitura):
      meetings.space.readonly, drive.readonly, admin.directory.user.readonly
  - c10@goakira.com.br tem o papel "Criador de token da conta de serviço"
    (roles/iam.serviceAccountTokenCreator) direto na service account.

SEM chave de arquivo: a impersonação (DWD) é feita assinando um JWT com
`sub=<usuário a impersonar>` via IAM Service Account Credentials API
(signJwt), usando a identidade local de quem roda o script. Isso exige:
  1. Rodar `gcloud auth application-default login` uma vez nesta máquina,
     com a conta que tem o papel Criador de token da conta de serviço
     (c10@goakira.com.br).
  2. A API "IAM Service Account Credentials API" ativa no projeto
     backup-vps-504817.

IMPORTANTE — o escopo drive.readonly, quando impersonado via DWD, lê o Drive
inteiro do usuário impersonado (não só gravações do Meet). Nunca repassar as
credenciais ADC nem o resultado bruto para os agentes de IA — só este módulo
deve chamar a API; os agentes consultam o índice já filtrado que ele produz.
"""

import json
import os
import time
from datetime import datetime

import google.auth
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SERVICE_ACCOUNT_EMAIL = os.environ.get(
    "MEET_COLLECTOR_SA_EMAIL",
    "meet-collector@backup-vps-504817.iam.gserviceaccount.com",
)

MEET_SCOPE = "https://www.googleapis.com/auth/meetings.space.readonly"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
DIRECTORY_SCOPE = "https://www.googleapis.com/auth/admin.directory.user.readonly"

GDOC_MIME = "application/vnd.google-apps.document"

_SIGN_JWT_URL = (
    f"https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/"
    f"{SERVICE_ACCOUNT_EMAIL}:signJwt"
)


def _adc_token() -> str:
    """
    Token da conta local autenticada via `gcloud auth application-default
    login`, usado só para chamar signJwt em nome da service account. Requer
    que essa conta tenha o papel "Criador de token da conta de serviço" na
    service account meet-collector@ (c10@goakira.com.br já tem).
    """
    try:
        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    except Exception as e:
        raise RuntimeError(
            "Nenhuma credencial ADC encontrada. Rodar `gcloud auth "
            "application-default login` com a conta c10@goakira.com.br "
            "antes de usar este coletor — ver docs/DWD_MEET_API_SETUP.md."
        ) from e
    creds.refresh(Request())
    return creds.token


def _delegated_credentials(subject: str, scope: str) -> Credentials:
    """
    Credenciais da service account impersonando `subject` via Domain-Wide
    Delegation, sem arquivo de chave: assina um JWT (claim `sub=subject`)
    via IAM Service Account Credentials API e troca por um access token
    OAuth de curta duração (1h).
    """
    now = int(time.time())
    payload = {
        "iss": SERVICE_ACCOUNT_EMAIL,
        "sub": subject,
        "scope": scope,
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
    }
    sign_resp = requests.post(
        _SIGN_JWT_URL,
        headers={"Authorization": f"Bearer {_adc_token()}"},
        json={"payload": json.dumps(payload)},
        timeout=30,
    )
    sign_resp.raise_for_status()
    signed_jwt = sign_resp.json()["signedJwt"]

    token_resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": signed_jwt,
        },
        timeout=30,
    )
    token_resp.raise_for_status()
    return Credentials(token_resp.json()["access_token"])


def list_domain_users(admin_subject: str | None = None) -> list[dict]:
    """
    Lista usuários ativos (não suspensos) do domínio via Admin SDK Directory API.

    admin_subject: e-mail a impersonar para essa chamada (precisa de
    privilégio de leitura de usuários no Workspace). Default:
    GOOGLE_WORKSPACE_ADMIN_EMAIL do .env, ou c10@goakira.com.br.
    """
    subject = admin_subject or os.environ.get("GOOGLE_WORKSPACE_ADMIN_EMAIL", "c10@goakira.com.br")
    creds = _delegated_credentials(subject, DIRECTORY_SCOPE)
    service = build("admin", "directory_v1", credentials=creds)

    users, token = [], None
    while True:
        resp = service.users().list(
            customer="my_customer",
            maxResults=200,
            orderBy="email",
            pageToken=token,
        ).execute()
        users.extend(resp.get("users", []))
        token = resp.get("nextPageToken")
        if not token:
            break
    return [u for u in users if not u.get("suspended")]


def _meet_service(subject: str):
    creds = _delegated_credentials(subject, MEET_SCOPE)
    return build("meet", "v2", credentials=creds)


def fetch_conference_records(subject: str, since: datetime | None = None) -> list[dict]:
    """
    Busca conferenceRecords de um usuário (como organizador ou participante),
    já com recordings e transcripts resolvidos (IDs no Drive, não conteúdo).

    Cada gravação vem de recordings[].driveDestination.file (ID do MP4) e
    cada transcrição de transcripts[].docsDestination.document (ID do Doc) —
    isso independe de em qual pasta o Google decidiu guardar o arquivo.
    """
    service = _meet_service(subject)
    filtro = f'startTime >= "{since.strftime("%Y-%m-%dT%H:%M:%SZ")}"' if since else None

    records, token = [], None
    while True:
        resp = service.conferenceRecords().list(filter=filtro, pageToken=token).execute()
        records.extend(resp.get("conferenceRecords", []))
        token = resp.get("nextPageToken")
        if not token:
            break

    out = []
    for rec in records:
        name = rec["name"]  # ex: "conferenceRecords/abc123"
        recordings = (
            service.conferenceRecords().recordings().list(parent=name).execute().get("recordings", [])
        )
        transcripts = (
            service.conferenceRecords().transcripts().list(parent=name).execute().get("transcripts", [])
        )
        out.append({
            "conference_record": name,
            "start_time": rec.get("startTime"),
            "end_time": rec.get("endTime"),
            "space": rec.get("space"),  # nome do recurso, ex: "spaces/abc123" — não um objeto
            "recordings": [
                {
                    "name": r["name"],
                    "drive_file_id": (r.get("driveDestination") or {}).get("file"),
                    "state": r.get("state"),
                }
                for r in recordings
            ],
            "transcripts": [
                {
                    "name": t["name"],
                    "doc_id": (t.get("docsDestination") or {}).get("document"),
                    "state": t.get("state"),
                }
                for t in transcripts
            ],
        })
    return out


def _consultant_emails() -> list[str]:
    """Fallback de subjects: e-mails já cadastrados em consultants.py."""
    from consultants import CONSULTANTS
    return [c["email"] for c in CONSULTANTS.values()]


def fetch_all(since: datetime | None = None, subjects: list[str] | None = None) -> dict[str, list[dict]]:
    """
    Roda fetch_conference_records para vários usuários e devolve
    {email: [conference_records...]}.

    subjects: lista explícita de e-mails. None = tenta listar todos os
    usuários ativos do domínio via Directory API (list_domain_users) — cobre
    consultor novo sem precisar cadastrar nada; se isso falhar (a Directory
    API exige que o subject impersonado seja admin do Workspace — testado em
    24/09/2026 e c10@ não tem esse privilégio), cai para os e-mails já
    cadastrados em consultants.CONSULTANTS.

    Dedup: a mesma reunião aparece para organizador e cada participante que
    também é usuário do domínio — quem consumir este dict deve deduplicar
    por "conference_record".
    """
    if subjects:
        emails = subjects
    else:
        try:
            emails = [u["primaryEmail"] for u in list_domain_users()]
        except Exception as e:
            print(f"   Aviso: Directory API falhou ({e}); usando lista de consultants.py")
            emails = _consultant_emails()

    result = {}
    for email in emails:
        try:
            result[email] = fetch_conference_records(email, since=since)
        except Exception as e:
            print(f"   Aviso: falha ao buscar conferenceRecords de {email}: {e}")
            result[email] = []
    return result


def export_doc_text(doc_id: str, owner_subject: str) -> str:
    """
    Exporta o texto de um Google Doc (transcrição) impersonando o dono do
    arquivo via DWD (drive.readonly). owner_subject normalmente é o mesmo
    e-mail usado para achar o conference_record (organizador).
    """
    creds = _delegated_credentials(owner_subject, DRIVE_SCOPE)
    service = build("drive", "v3", credentials=creds)
    content = service.files().export(fileId=doc_id, mimeType="text/plain").execute()
    if isinstance(content, bytes):
        return content.decode("utf-8", errors="replace")
    return str(content)


def fetch_legacy_recordings_by_mimetype(subject: str) -> list[dict]:
    """
    Fallback para histórico: lista todo MP4 do Drive de `subject` sem filtrar
    por pasta (cobre o que ficou em "Legacy Meet Recordings" ou qualquer
    outra pasta). Deduplicar por shortcutDetails.targetId — atalhos de
    reuniões recorrentes aparecem repetidos.
    """
    creds = _delegated_credentials(subject, DRIVE_SCOPE)
    service = build("drive", "v3", credentials=creds)

    files, token = [], None
    query = "mimeType = 'video/mp4' and trashed = false"
    while True:
        resp = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, modifiedTime, mimeType, shortcutDetails)",
            pageSize=200,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            pageToken=token,
        ).execute()
        files.extend(resp.get("files", []))
        token = resp.get("nextPageToken")
        if not token:
            break

    seen_targets = set()
    deduped = []
    for f in files:
        target = (f.get("shortcutDetails") or {}).get("targetId")
        key = target or f["id"]
        if key in seen_targets:
            continue
        seen_targets.add(key)
        deduped.append(f)
    return deduped


if __name__ == "__main__":
    # Smoke test manual — roda depois de `gcloud auth application-default
    # login`, antes de plugar isso no pipeline. Não escreve nada, só imprime.
    print("Testando DWD: listando usuários do domínio (Directory API)...")
    try:
        users = list_domain_users()
        emails = [u["primaryEmail"] for u in users]
        print(f"   {len(users)} usuário(s) ativo(s) encontrado(s).")
    except Exception as e:
        print(f"   Directory API falhou ({e}) — usando consultants.py como fallback.")
        emails = _consultant_emails()

    for email in emails[:5]:
        print(f"   - {email}")

    if emails:
        alvo = emails[0]
        print(f"\nTestando Meet API impersonando {alvo}...")
        registros = fetch_conference_records(alvo)
        com_arquivo = sum(1 for r in registros for rec in r["recordings"] if rec["drive_file_id"])
        print(f"   {len(registros)} conferenceRecord(s) encontrado(s) para {alvo} ({com_arquivo} com arquivo pronto no Drive).")
