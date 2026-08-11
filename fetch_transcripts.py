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

from client_aliases import (
    normalize_client,
    find_client_in_text,
    is_internal_meeting,
    TODOS_PROJETOS,
)
from drive_folders import MEET_RECORDINGS_FOLDERS, MEET_RECORDINGS_SUBFOLDER_ROOTS


SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]

GDOC_MIME = "application/vnd.google-apps.document"
SHORTCUT_MIME = "application/vnd.google-apps.shortcut"
FOLDER_MIME = "application/vnd.google-apps.folder"

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

    # Reunião interna com prefixo entre colchetes ("[INTERNO]", "[Treinamento]")
    # — o formato bate com o parser, mas não é reunião de cliente: descarta.
    if is_internal_meeting(cliente_raw):
        return None

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


# ── Estrutura NOVA: pasta "Google Meet" com uma subpasta por reunião ────────────

def _list_child_folders(service, parent_id: str) -> list[dict]:
    """Lista todas as subpastas diretas de uma pasta (com paginação, Shared Drive safe)."""
    folders, token = [], None
    while True:
        params = dict(
            q=(
                f"'{parent_id}' in parents"
                f" and mimeType = '{FOLDER_MIME}'"
                " and trashed = false"
            ),
            fields="nextPageToken, files(id, name, modifiedTime)",
            pageSize=200,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        if token:
            params["pageToken"] = token
        result = service.files().list(**params).execute()
        folders.extend(result.get("files", []))
        token = result.get("nextPageToken")
        if not token:
            break
    return folders


def _list_subfolder_items(service, folder_id: str, hours_back: int | None) -> list[dict]:
    """
    Lista os itens de uma subpasta de reunião: Google Docs (transcrição), vídeos
    (gravação) e ATALHOS (shortcuts) para qualquer um deles. Filtro opcional por
    data de modificação. Inclui shortcutDetails para resolver o alvo dos atalhos.
    """
    query_parts = [
        f"'{folder_id}' in parents",
        f"(mimeType = '{GDOC_MIME}' or mimeType = 'video/mp4'"
        f" or mimeType = 'video/webm' or mimeType = '{SHORTCUT_MIME}')",
        "trashed = false",
    ]
    if hours_back is not None:
        since = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        query_parts.append(f"modifiedTime >= '{since.strftime('%Y-%m-%dT%H:%M:%SZ')}'")

    query = " and ".join(query_parts)
    files, token = [], None
    while True:
        params = dict(
            q=query,
            fields=(
                "nextPageToken, files(id, name, modifiedTime, mimeType, "
                "videoMediaMetadata, shortcutDetails)"
            ),
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


def _resolve_shortcut(item: dict) -> dict | None:
    """
    Normaliza um atalho para um item {id, name, mimeType} apontando ao alvo real.
    Retorna None se o atalho não aponta para Doc/vídeo. O nome exibido é o do
    PRÓPRIO atalho (que carrega "[Cliente] ... - data - Anotações do Gemini").
    """
    sd = item.get("shortcutDetails") or {}
    target_id = sd.get("targetId")
    target_mime = sd.get("targetMimeType")
    if not target_id or not target_mime:
        return None
    if target_mime == GDOC_MIME or target_mime.startswith("video/"):
        return {"id": target_id, "name": item["name"], "mimeType": target_mime}
    return None


def _entries_from_new_structure(
    service, roots: dict[str, str], hours_back: int | None
) -> list[dict]:
    """
    Percorre as pastas "Google Meet" (estrutura nova), recursando 1 nível nas
    subpastas por reunião, e devolve entradas normalizadas de transcrição.
    Cada entrada: {consultor, id (Doc real), name (p/ parse), duracao_real}.
    Resolve atalhos (shortcuts) para Docs/vídeos reais.
    """
    entries: list[dict] = []
    for nome_consultor, root_id in roots.items():
        if not root_id or str(root_id).startswith("COLE_"):
            print(f"   Pasta 'Google Meet' de {nome_consultor} ainda não configurada — pulando")
            continue

        subfolders = _list_child_folders(service, root_id)
        print(f"   Buscando em 'Google Meet' de {nome_consultor} ({len(subfolders)} subpasta(s))...")

        for sf in subfolders:
            items = _list_subfolder_items(service, sf["id"], hours_back)
            docs, videos = [], []
            for it in items:
                if it.get("mimeType") == SHORTCUT_MIME:
                    resolved = _resolve_shortcut(it)
                    if not resolved:
                        continue
                    if resolved["mimeType"] == GDOC_MIME:
                        docs.append({"id": resolved["id"], "name": resolved["name"]})
                    # vídeo via atalho: sem videoMediaMetadata no atalho, então
                    # não dá para extrair duração barata — ignorado (não crítico).
                elif it.get("mimeType") == GDOC_MIME:
                    docs.append({"id": it["id"], "name": it["name"]})
                elif (it.get("mimeType") or "").startswith("video/"):
                    videos.append(it)

            duration_by_base = _video_duration_by_base_name(videos)
            for d in docs:
                entries.append({
                    "consultor": nome_consultor,
                    "id": d["id"],
                    "name": d["name"],
                    "duracao_real": duration_by_base.get(_base_name(d["name"], _DOC_SUFFIX)),
                })
    return entries


def _entries_from_old_structure(
    service, pastas: dict[str, str], hours_back: int | None
) -> list[dict]:
    """
    Percorre as pastas planas "Meet Recordings" (estrutura antiga) e devolve
    entradas normalizadas de transcrição — mesmo formato de _entries_from_new_structure.
    """
    entries: list[dict] = []
    for nome_consultor, folder_id in pastas.items():
        if not folder_id or str(folder_id).startswith("COLE_"):
            print(f"   Pasta de {nome_consultor} ainda não configurada — pulando")
            continue

        print(f"   Buscando em Meet Recordings de {nome_consultor}...")
        files = _list_folder(service, folder_id, hours_back)
        docs = [f for f in files if f.get("mimeType") == GDOC_MIME]
        duration_by_base = _video_duration_by_base_name(files)
        print(f"      {len(docs)} arquivo(s) encontrado(s)")
        for f in docs:
            entries.append({
                "consultor": nome_consultor,
                "id": f["id"],
                "name": f["name"],
                "duracao_real": duration_by_base.get(_base_name(f["name"], _DOC_SUFFIX)),
            })
    return entries


def _select_por_consultor(mapping: dict[str, str], consultor: str | None) -> dict[str, str]:
    """Filtra um mapa consultor→pasta para um consultor específico (ou todos)."""
    if consultor is None:
        return mapping
    return {consultor: mapping[consultor]} if consultor in mapping else {}


def enumerate_meeting_docs(
    service, hours_back: int | None, consultor: str | None = None
) -> list[dict]:
    """
    Enumera TODAS as transcrições (Google Docs) visíveis, das DUAS estruturas de
    Drive — antiga (pastas planas Meet Recordings) e nova (pastas "Google Meet"
    com uma subpasta por reunião, com Docs/vídeos reais OU atalhos).

    Somente leitura — nunca exporta conteúdo, cria ou apaga nada. É a fonte de
    verdade compartilhada por fetch_drive_transcripts() (pipeline/ata) e por
    audit_cobertura.auditar() (auditoria), garantindo que a auditoria enxergue
    exatamente as mesmas reuniões que o pipeline.

    Cada entrada: {consultor, id (Doc real), name (p/ _parse_filename), duracao_real}.
    """
    entries = _entries_from_old_structure(
        service, _select_por_consultor(MEET_RECORDINGS_FOLDERS, consultor), hours_back
    )
    entries += _entries_from_new_structure(
        service, _select_por_consultor(MEET_RECORDINGS_SUBFOLDER_ROOTS, consultor), hours_back
    )
    return entries


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

    # Enumera as reuniões das DUAS estruturas (antiga plana + nova "Google Meet")
    entries = enumerate_meeting_docs(service, hours_back, consultor=consultor)

    seen_ids    = set()   # dedup pelo id do Doc real (atalho já resolvido no enumerador)
    transcripts = []

    for e in entries:
        if e["id"] in seen_ids:
            continue
        seen_ids.add(e["id"])

        parsed = _parse_filename(e["name"])
        if not parsed:
            print(f"      Pulando (nome não reconhecido): {e['name'][:100]}")
            continue

        if cliente_norm and parsed["cliente"] != cliente_norm:
            continue

        dt = parsed["data_dt"]
        if since_date and dt < since_date:
            continue
        if until_date and dt > until_date:
            continue

        text = _read_doc_text(service, e["id"])
        if not text or len(text.strip()) < 50:
            print(f"      Pulando (sem conteúdo): {e['name'][:60]}")
            continue

        print(f"      OK: [{parsed['cliente']}] {parsed['assunto']} ({parsed['data_reuniao']})")
        transcripts.append({
            "message_id":  e["id"],
            "subject":     e["name"],
            "date":        parsed["data_reuniao"],
            "cliente":     parsed["cliente"],
            "fase":        parsed["fase"],
            "assunto":     parsed["assunto"],
            "consultor":   e["consultor"],
            "data_dt":     parsed["data_dt"],
            "transcript":  text.strip(),
            "duracao_real": e["duracao_real"],
        })

    transcripts.sort(key=lambda t: t["data_dt"])
    print(f"   Total: {len(transcripts)} transcrição(ões) carregada(s)")
    return transcripts


# Alias esperado por main.py (pipeline diário)
def get_all_transcripts(hours_back: int = 24) -> list[dict]:
    return fetch_drive_transcripts(hours_back=hours_back)
