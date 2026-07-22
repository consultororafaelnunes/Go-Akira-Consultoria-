"""
fetch_transcripts.py — Busca transcrições do Google Meet via Google Drive.

Cada consultor tem sua própria pasta "Meet Recordings" na conta pessoal do Google.
Para que o agente leia todas, cada consultor compartilha a pasta com c10@goakira.com.br.
As pastas compartilhadas ficam registradas em drive_folders.MEET_RECORDINGS_FOLDERS.

Convenção de nome dos arquivos:
  [Cliente] Fase. Assunto - YYYY/MM/DD HH:MM - Anotações do Gemini

Retorna lista de dicts:
  {
    "message_id":  str,       # file_id do Drive (dedup)
    "subject":     str,       # nome completo do arquivo
    "date":        str,       # data no formato DD/MM/YYYY
    "cliente":     str,       # nome canônico do cliente
    "fase":        str,       # fase do projeto (ex: "BP")
    "assunto":     str,       # assunto/título da reunião
    "consultor":   str,       # consultor dono da gravação
    "data_dt":     datetime,
    "transcript":  str,       # texto completo exportado do Google Doc
  }
"""

import os
import re
from datetime import datetime, timedelta, timezone

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from client_aliases import normalize_client, find_client_in_text, TODOS_PROJETOS
from drive_folders import MEET_RECORDINGS_FOLDERS


SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]

GDOC_MIME = "application/vnd.google-apps.document"

# Sufixos que o Google Meet/Gemini usa para nomear os dois arquivos de uma
# mesma reunião — a transcrição (Google Doc) e a gravação (vídeo). Usados
# para casar os dois pelo nome-base e extrair a duração real do vídeo.
_DOC_SUFFIX = " - Anotações do Gemini"
_VIDEO_SUFFIX = " - Recording"


def _base_name(name: str, suffix: str) -> str:
    if name.endswith(suffix):
        return name[: -len(suffix)].rstrip()
    return name.rstrip()


def _format_duration(duration_millis: int) -> str:
    total_min = round(duration_millis / 60000)
    h, m = divmod(total_min, 60)
    if h and m:
        return f"{h}h {m}min"
    if h:
        return f"{h}h"
    return f"{m}min"

# [Cliente] [Fase. ]Desc - YYYY/MM/DD HH:MM [GMT±HH:MM] [- Anotações do Gemini]
# A parte "Fase." é opcional; a timezone GMT é ignorada pelo grupo data.
_FILENAME_RE = re.compile(
    r"^\s*\[(?P<cliente>[^\]]+)\]\s*"
    r"(?P<desc>.+?)\s*-\s*"
    r"(?P<data>\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})"
)

# Formato antigo sem colchetes: "Goakira & Cliente [- Desc] - YYYY/MM/DD HH:MM ..."
# Só é aceito se o cliente extraído já for conhecido (TODOS_PROJETOS) — evita
# classificar reuniões internas (ex. "Goakira & Alinhamento ISO 9001...") como de cliente.
_FILENAME_RE_FALLBACK = re.compile(
    r"^\s*Goakira\s*&\s*(?P<cliente>[^-]+?)\s*-\s*"
    r"(?:(?P<desc>.+?)\s*-\s*)??"
    r"(?P<data>\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})",
    re.IGNORECASE,
)

_DATE_RE = re.compile(r"(?P<data>\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})")


def _parse_filename_lenient(name: str) -> dict | None:
    """
    Último recurso: extrai qualquer trecho do nome (antes da data) que,
    depois de normalizado, bata com um cliente já conhecido (TODOS_PROJETOS).
    Cobre variações como "Manuais - Cliente & Goakira - data",
    "Cliente - Reunião de Conclusão... - data", "R6. Goakira & Cliente (alias) - data".
    Só aceita se algum trecho normalizar para um cliente conhecido — nunca cria cliente novo.
    """
    m_data = _DATE_RE.search(name)
    if not m_data:
        return None

    before = name[: m_data.start()].strip().rstrip("-").strip()
    if not before:
        return None

    candidatos = set()
    for parte in re.split(r"[&|]", before):
        parte = parte.strip()
        if parte:
            candidatos.add(parte)
        for trecho in parte.split(" - "):
            trecho = re.sub(r"^\s*Goakira\s*", "", trecho, flags=re.IGNORECASE).strip()
            trecho = re.sub(r"\s*Goakira\s*$", "", trecho, flags=re.IGNORECASE).strip()
            trecho = re.sub(r"\s*\([^)]*\)\s*$", "", trecho).strip()  # remove "(alias)" no final
            if trecho:
                candidatos.add(trecho)

    for candidato in candidatos:
        norm = normalize_client(candidato)
        if norm in TODOS_PROJETOS:
            return {"cliente": norm, "data": m_data.group("data"), "desc": before}

    # Último recurso: procura algum alias conhecido como palavra isolada em "before"
    # (cobre casos como "MedSempre- Reunião..." ou "Reunião_ CTA Manuais").
    achado = find_client_in_text(before)
    if achado:
        return {"cliente": achado, "data": m_data.group("data"), "desc": before}

    return None


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


def _parse_filename(name: str) -> dict | None:
    """Extrai cliente, fase, assunto e data do nome do arquivo."""
    m = _FILENAME_RE.match(name)
    if m:
        cliente_raw = m.group("cliente").strip()
        desc = (m.group("desc") or "").strip()
        data_str = m.group("data")
    else:
        m = _FILENAME_RE_FALLBACK.match(name)
        if m and normalize_client(m.group("cliente")) in TODOS_PROJETOS:
            cliente_raw = m.group("cliente").strip()
            desc = (m.group("desc") or "").strip()
            data_str = m.group("data")
        else:
            lenient = _parse_filename_lenient(name)
            if not lenient:
                return None
            cliente_raw = lenient["cliente"]
            desc = lenient["desc"]
            data_str = lenient["data"]

    try:
        dt = datetime.strptime(data_str, "%Y/%m/%d %H:%M")
    except ValueError:
        return None

    # "BP. Assunto detalhado" → fase="BP", assunto="Assunto detalhado"
    # Sem ponto: fase vazia, assunto = desc inteiro
    if ". " in desc:
        fase, assunto = desc.split(". ", 1)
    else:
        fase, assunto = "", desc

    return {
        "cliente_raw":  cliente_raw,
        "cliente":      normalize_client(cliente_raw),
        "fase":         fase.strip(),
        "assunto":      assunto.strip(),
        "data_dt":      dt,
        "data_reuniao": dt.strftime("%d/%m/%Y"),
    }


def _read_doc_text(service, file_id: str) -> str:
    """Exporta Google Doc como texto plano."""
    try:
        content = service.files().export(
            fileId=file_id,
            mimeType="text/plain",
        ).execute()
        if isinstance(content, bytes):
            return content.decode("utf-8", errors="replace")
        return str(content)
    except Exception as e:
        print(f"      Aviso: erro ao exportar {file_id}: {e}")
        return ""


def _list_folder(service, folder_id: str, hours_back: int | None) -> list[dict]:
    """
    Lista Google Docs (transcrições) e vídeos (gravações) de uma pasta, com
    filtro opcional de data de modificação. Os vídeos são usados só para
    extrair a duração real da reunião — nunca processados como transcrição.
    """
    query_parts = [
        f"'{folder_id}' in parents",
        f"(mimeType = '{GDOC_MIME}' or mimeType = 'video/mp4' or mimeType = 'video/webm')",
        "trashed = false",
    ]
    if hours_back is not None:
        since = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        query_parts.append(f"modifiedTime >= '{since.strftime('%Y-%m-%dT%H:%M:%SZ')}'")

    query  = " and ".join(query_parts)
    files  = []
    token  = None
    while True:
        params = dict(
            q=query,
            fields="nextPageToken, files(id, name, modifiedTime, mimeType, videoMediaMetadata)",
            pageSize=200,
            orderBy="name",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        if token:
            params["pageToken"] = token
        result = service.files().list(**params).execute()
        files.extend(result.get("files", []))
        token = result.get("nextPageToken")
        if not token:
            break
    return files


def _video_duration_by_base_name(files: list[dict]) -> dict[str, str]:
    """Mapeia nome-base da reunião -> duração formatada, a partir dos vídeos da pasta."""
    result = {}
    for f in files:
        if not f.get("mimeType", "").startswith("video/"):
            continue
        duration_millis = (f.get("videoMediaMetadata") or {}).get("durationMillis")
        if not duration_millis:
            continue
        base = _base_name(f["name"], _VIDEO_SUFFIX)
        result[base] = _format_duration(int(duration_millis))
    return result


def fetch_drive_transcripts(
    hours_back: int | None = 24,
    cliente: str | None = None,
    since_date: datetime | None = None,
    until_date: datetime | None = None,
    consultor: str | None = None,
) -> list[dict]:
    """
    Busca transcrições nas pastas Meet Recordings de todos os consultores configurados.

    Args:
        hours_back:  Arquivos modificados nas últimas N horas. None = sem filtro (backfill).
        cliente:     Filtra por cliente (canônico ou alias). None = todos.
        since_date:  Data mínima da reunião.
        until_date:  Data máxima da reunião.
        consultor:   Filtra pela pasta de um consultor específico. None = todos.
    """
    creds   = get_credentials()
    service = build("drive", "v3", credentials=creds)

    cliente_norm = normalize_client(cliente) if cliente else None

    # Seleciona quais pastas varrer
    pastas = (
        {consultor: MEET_RECORDINGS_FOLDERS[consultor]}
        if consultor and consultor in MEET_RECORDINGS_FOLDERS
        else MEET_RECORDINGS_FOLDERS
    )

    seen_ids    = set()   # dedup entre pastas
    transcripts = []

    for nome_consultor, folder_id in pastas.items():
        if not folder_id or folder_id.startswith("COLE_"):
            print(f"   Pasta de {nome_consultor} ainda não configurada — pulando")
            continue

        print(f"   Buscando em Meet Recordings de {nome_consultor}...")
        files = _list_folder(service, folder_id, hours_back)
        docs = [f for f in files if f.get("mimeType") == GDOC_MIME]
        duration_by_base = _video_duration_by_base_name(files)
        print(f"      {len(docs)} arquivo(s) encontrado(s)")

        for f in docs:
            if f["id"] in seen_ids:
                continue
            seen_ids.add(f["id"])

            parsed = _parse_filename(f["name"])
            if not parsed:
                print(f"      Pulando (nome não reconhecido): {f['name'][:100]}")
                continue

            if cliente_norm and parsed["cliente"] != cliente_norm:
                continue

            dt = parsed["data_dt"]
            if since_date and dt < since_date:
                continue
            if until_date and dt > until_date:
                continue

            text = _read_doc_text(service, f["id"])
            if not text or len(text.strip()) < 50:
                print(f"      Pulando (sem conteúdo): {f['name'][:60]}")
                continue

            duracao_real = duration_by_base.get(_base_name(f["name"], _DOC_SUFFIX))

            print(f"      OK: [{parsed['cliente']}] {parsed['assunto']} ({parsed['data_reuniao']})")
            transcripts.append({
                "message_id":  f["id"],
                "subject":     f["name"],
                "date":        parsed["data_reuniao"],
                "cliente":     parsed["cliente"],
                "fase":        parsed["fase"],
                "assunto":     parsed["assunto"],
                "consultor":   nome_consultor,
                "data_dt":     parsed["data_dt"],
                "transcript":  text.strip(),
                "duracao_real": duracao_real,
            })

    transcripts.sort(key=lambda t: t["data_dt"])
    print(f"   Total: {len(transcripts)} transcrição(ões) carregada(s)")
    return transcripts


# Alias esperado por main.py (pipeline diário)
def get_all_transcripts(hours_back: int = 24) -> list[dict]:
    return fetch_drive_transcripts(hours_back=hours_back)
