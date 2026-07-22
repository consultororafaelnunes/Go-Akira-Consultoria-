"""
calendar_sync.py — Detecta cancelamentos e reagendamentos reais na agenda
dos consultores, via Google Calendar API.

Diferente de inferir "reunião esperada e não apareceu no Drive" (ambíguo —
pode ser cancelamento real ou falha de sincronização, como aconteceu com a
Thais), este módulo lê os metadados que o próprio Google Calendar já marca:
  - status == "cancelled"                → instância cancelada
  - originalStartTime != start           → instância movida (reagendada)

Critério exato usado por _detect_changes():
  - Só conta o que o Calendar do consultor já marcou como cancelado/movido —
    não há inferência própria. Se o consultor não excluiu/moveu o evento na
    agenda dele, nada é reportado aqui, mesmo que a reunião não tenha
    acontecido de fato (isso continua sendo um ponto cego, ver Thais acima).
  - Instâncias canceladas de série recorrente não trazem 'summary' — o título
    é buscado no evento-mestre via _lookup_series_title() (com cache).
  - get_calendar_changes() só reporta o que casa com um cliente conhecido
    (find_client_in_text no título) — filtra fora compromissos pessoais e
    reuniões internas da GoAkira, que também aparecem na mesma varredura.
  - A mesma reunião de cliente pode aparecer na agenda de mais de um
    consultor (BP conjunto) — get_calendar_changes() deduplica por
    (tipo, cliente, título, data original, data nova), juntando os nomes.

Todos os consultores já enxergam a agenda uns dos outros (compartilhamento
existente), então a mesma credencial OAuth usada para Drive/Gmail (c10@) lê
os calendários de todos — basta o escopo calendar.readonly.
"""

from datetime import date, datetime, timedelta

from googleapiclient.discovery import build

from client_aliases import find_client_in_text
from consultants import CONSULTANTS
from fetch_transcripts import get_credentials

_series_title_cache: dict[str, str] = {}


def _fmt_dt(obj: dict | None) -> str:
    if not obj:
        return "—"
    raw = obj.get("dateTime") or obj.get("date")
    if not raw:
        return "—"
    try:
        if "T" in raw:
            return datetime.fromisoformat(raw).strftime("%d/%m/%Y %H:%M")
        return datetime.strptime(raw, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return raw


def _lookup_series_title(service, calendar_id: str, recurring_event_id: str) -> str:
    """
    Instâncias canceladas de eventos recorrentes vêm sem 'summary' — só o
    evento-mestre da série tem o título. Cacheado porque a mesma série
    recorrente pode gerar várias instâncias canceladas no período.
    """
    key = f"{calendar_id}:{recurring_event_id}"
    if key in _series_title_cache:
        return _series_title_cache[key]
    try:
        master = service.events().get(calendarId=calendar_id, eventId=recurring_event_id).execute()
        titulo = master.get("summary", "")
    except Exception:
        titulo = ""
    _series_title_cache[key] = titulo
    return titulo


def _fetch_events(service, calendar_id: str, start: date, end: date) -> list[dict]:
    time_min = datetime.combine(start, datetime.min.time()).isoformat() + "Z"
    time_max = datetime.combine(end + timedelta(days=1), datetime.min.time()).isoformat() + "Z"

    events: list[dict] = []
    page_token = None
    while True:
        resp = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            showDeleted=True,
            pageToken=page_token,
        ).execute()
        events.extend(resp.get("items", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return events


def _detect_changes(service, calendar_id: str, events: list[dict]) -> list[dict]:
    changes = []
    for e in events:
        status = e.get("status")
        original_start = e.get("originalStartTime")
        start = e.get("start")

        titulo = e.get("summary")
        if not titulo and e.get("recurringEventId"):
            titulo = _lookup_series_title(service, calendar_id, e["recurringEventId"])
        titulo = titulo or "(título indisponível)"

        if status == "cancelled":
            changes.append({
                "tipo": "cancelada",
                "titulo": titulo,
                "data_original": _fmt_dt(original_start or start),
            })
        elif original_start and start and _fmt_dt(original_start) != _fmt_dt(start):
            changes.append({
                "tipo": "remarcada",
                "titulo": titulo,
                "data_original": _fmt_dt(original_start),
                "data_nova": _fmt_dt(start),
            })
    return changes


def get_calendar_changes(start: date, end: date, consultores: list[str] | None = None) -> list[dict]:
    """
    Retorna cancelamentos e reagendamentos reais no período [start, end],
    em todas as agendas dos consultores (ou só nas passadas em `consultores`).
    Cada item: {tipo, titulo, cliente, consultor, data_original, [data_nova]}.
    """
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    nomes = consultores or list(CONSULTANTS.keys())
    raw_changes = []
    for nome in nomes:
        email = CONSULTANTS[nome]["email"]
        try:
            events = _fetch_events(service, email, start, end)
        except Exception as e:
            print(f"   Aviso: falha ao ler agenda de {nome} ({email}): {e}")
            continue
        for c in _detect_changes(service, email, events):
            c["consultor"] = nome
            c["cliente"] = find_client_in_text(c["titulo"])
            raw_changes.append(c)

    # Só interessa ao relatório o que é reunião de cliente reconhecido — a
    # varredura pega TUDO na agenda do consultor (compromissos pessoais,
    # reuniões internas da GoAkira, blocos de agenda), que é ruído aqui.
    client_changes = [c for c in raw_changes if c["cliente"]]

    # A mesma reunião de cliente aparece na agenda de todos os participantes
    # (ex: BP conjunto Rafael+Ivan) — sem isso, vira alerta duplicado.
    merged: dict[tuple, dict] = {}
    order: list[tuple] = []
    for c in client_changes:
        key = (c["tipo"], c["cliente"], c["titulo"], c["data_original"], c.get("data_nova"))
        if key not in merged:
            merged[key] = {**c, "consultor": [c["consultor"]]}
            order.append(key)
        elif c["consultor"] not in merged[key]["consultor"]:
            merged[key]["consultor"].append(c["consultor"])

    changes = []
    for key in order:
        item = merged[key]
        item["consultor"] = " & ".join(item["consultor"])
        changes.append(item)
    return changes


def render_changes_html(changes: list[dict]) -> str:
    """Fragmento HTML da seção 'Alterações de Agenda', reaproveitado nos
    relatórios diário e semanal. Retorna string vazia se não há alterações.

    Critério de detecção (ver docstring do módulo para detalhes técnicos):
    conta como cancelamento/reagendamento o que está de fato marcado como tal
    no Google Calendar do consultor responsável — não uma inferência por
    ausência de transcrição no Drive. Por isso a nota de rodapé abaixo da
    tabela avisa que reflete a agenda do consultor, não confirmação do
    cliente.
    """
    if not changes:
        return ""

    rows = ""
    for c in changes:
        icon = "🔁" if c["tipo"] == "remarcada" else "❌"
        detalhe = (
            f'{c["data_original"]} → <b>{c["data_nova"]}</b>'
            if c["tipo"] == "remarcada"
            else f'era {c["data_original"]}'
        )
        rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #e0e4f0;font-size:12px;white-space:nowrap">{icon} {c["tipo"].capitalize()}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e0e4f0;font-size:13px;font-weight:600">{c.get("cliente") or "—"}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e0e4f0;font-size:12px;color:#374151">{c["titulo"]}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e0e4f0;font-size:12px;color:#64748B;white-space:nowrap">{c.get("consultor","—")}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e0e4f0;font-size:12px;color:#64748B;white-space:nowrap">{detalhe}</td>
        </tr>"""

    return f"""
    <div style="margin-bottom:24px">
      <h3 style="margin:0 0 8px;font-size:15px;color:#1E2761">📅 Alterações de Agenda</h3>
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <thead>
          <tr style="background:#1E2761">
            <th style="padding:8px 12px;text-align:left;color:#CADCFC;font-size:11px">Tipo</th>
            <th style="padding:8px 12px;text-align:left;color:#CADCFC;font-size:11px">Cliente</th>
            <th style="padding:8px 12px;text-align:left;color:#CADCFC;font-size:11px">Reunião</th>
            <th style="padding:8px 12px;text-align:left;color:#CADCFC;font-size:11px">Consultor</th>
            <th style="padding:8px 12px;text-align:left;color:#CADCFC;font-size:11px">Detalhe</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
      <p style="font-size:11px;color:#94A3B8;margin:6px 2px 0">
        Critério: reunião marcada como cancelada/remarcada diretamente no Google Calendar
        do consultor responsável — reflete a agenda dele, não uma confirmação do cliente.
      </p>
    </div>"""
