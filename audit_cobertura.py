"""
audit_cobertura.py — Auditoria de cobertura de atas.

Compara as reuniões (Google Docs nas pastas Meet Recordings) de uma data ou
intervalo contra os _message_id já processados (registrados em summaries_*.json)
e aponta:
  - reuniões de cliente COM ata gerada
  - reuniões de cliente SEM ata (furos de cobertura)
  - nomes de arquivo não reconhecidos pelo parser na janela (reuniões internas
    ou possíveis furos que precisam de revisão manual)

Nasce da auditoria manual pedida pela Patrícia em 14/07/2026 (338 reuniões
varridas, 86 nunca processadas) — agora reutilizável e parametrizável.

Somente leitura do Drive — nunca gera nem apaga atas.

Uso:
  python audit_cobertura.py                      # ontem (padrão)
  python audit_cobertura.py --data 27/07/2026    # um dia específico
  python audit_cobertura.py --data 2026-07-27    # ISO também aceito
  python audit_cobertura.py --de 20/07/2026 --ate 27/07/2026   # intervalo
"""

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from googleapiclient.discovery import build

from drive_folders import MEET_RECORDINGS_FOLDERS
from fetch_transcripts import GDOC_MIME, _list_folder, _parse_filename, get_credentials

# Console do Windows às vezes usa cp1252 e quebra em acentos/símbolos — força UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _parse_data(texto: str) -> date:
    """Aceita DD/MM/YYYY ou YYYY-MM-DD."""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(f"Data inválida: {texto!r} (use DD/MM/YYYY ou YYYY-MM-DD)")


def _ids_processados() -> set[str]:
    """IDs (_message_id) de todas as transcrições já sumarizadas (têm ata)."""
    ids: set[str] = set()
    for path in Path(".").glob("summaries_*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for item in data:
            mid = item.get("_message_id")
            if mid:
                ids.add(mid)
    return ids


def auditar(inicio: date, fim: date) -> dict:
    """Varre todas as pastas Meet Recordings e classifica as reuniões da janela."""
    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    processados = _ids_processados()
    print(f"IDs já processados (summaries_*.json): {len(processados)}")

    # Strings de data (no formato do nome do arquivo) que caem na janela
    datas_janela = set()
    d = inicio
    while d <= fim:
        datas_janela.add(d.strftime("%Y/%m/%d"))
        d += timedelta(days=1)

    rows: list[dict] = []
    unparsed: list[tuple[str, str]] = []
    seen: set[str] = set()

    for consultor, folder_id in MEET_RECORDINGS_FOLDERS.items():
        if not folder_id or str(folder_id).startswith("COLE_"):
            print(f"  (pasta de {consultor} não configurada — pulando)")
            continue
        files = _list_folder(service, folder_id, None)
        docs = [f for f in files if f.get("mimeType") == GDOC_MIME]
        for f in docs:
            if f["id"] in seen:
                continue
            seen.add(f["id"])
            parsed = _parse_filename(f["name"])
            if not parsed:
                if any(ds in f["name"] for ds in datas_janela):
                    unparsed.append((consultor, f["name"]))
                continue
            if not (inicio <= parsed["data_dt"].date() <= fim):
                continue
            rows.append({
                "consultor": consultor,
                "cliente": parsed["cliente"],
                "fase": parsed["fase"],
                "assunto": parsed["assunto"],
                "data": parsed["data_dt"].date(),
                "id": f["id"],
                "name": f["name"],
                "processed": f["id"] in processados,
            })

    return {"rows": rows, "unparsed": unparsed}


def imprimir_relatorio(inicio: date, fim: date, resultado: dict) -> bool:
    """Imprime o relatório e retorna True se a cobertura de clientes está 100%."""
    rows = resultado["rows"]
    unparsed = resultado["unparsed"]
    com_ata = [r for r in rows if r["processed"]]
    sem_ata = [r for r in rows if not r["processed"]]

    if inicio == fim:
        titulo = f"reuniões de {inicio.strftime('%d/%m/%Y')}"
    else:
        titulo = f"reuniões de {inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}"

    print("\n" + "=" * 70)
    print(f"AUDITORIA DE COBERTURA — {titulo}")
    print("=" * 70)
    print(f"Reuniões de cliente reconhecidas: {len(rows)}")
    print(f"  ✅ Com ata gerada:  {len(com_ata)}")
    print(f"  ❌ SEM ata gerada:  {len(sem_ata)}")
    print(f"  ⚠️  Nomes não reconhecidos na janela: {len(unparsed)}")

    if com_ata:
        print("\n--- COM ATA ---")
        for r in sorted(com_ata, key=lambda x: (x["data"], x["consultor"], x["cliente"])):
            fase = f" · {r['fase']}" if r["fase"] else ""
            print(f"  {r['data'].strftime('%d/%m')} [{r['consultor']}] {r['cliente']}{fase} · {r['assunto'][:50]}")

    if sem_ata:
        print("\n--- ❌ SEM ATA (revisar / rodar backfill) ---")
        for r in sorted(sem_ata, key=lambda x: (x["data"], x["consultor"], x["cliente"])):
            print(f"  {r['data'].strftime('%d/%m')} [{r['consultor']}] {r['cliente']} · {r['assunto'][:50]}")
            print(f"       arquivo: {r['name'][:80]}")

    if unparsed:
        print("\n--- ⚠️ NOMES NÃO RECONHECIDOS (reuniões internas OU possíveis furos) ---")
        for consultor, name in unparsed:
            print(f"  [{consultor}] {name[:90]}")

    print("\n" + "=" * 70)
    ok = not sem_ata
    if ok and not unparsed:
        print("RESULTADO: cobertura 100% — todas as reuniões de cliente têm ata.")
    elif ok:
        print("RESULTADO: 100% das reuniões de cliente têm ata (revisar os nomes não reconhecidos acima).")
    else:
        print("RESULTADO: HÁ FUROS de cobertura — reuniões de cliente sem ata (ver acima).")
    print("=" * 70)
    return ok


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Auditoria de cobertura de atas GoAkira")
    parser.add_argument("--data", type=_parse_data, help="Dia único (DD/MM/YYYY ou YYYY-MM-DD)")
    parser.add_argument("--de", type=_parse_data, help="Início do intervalo")
    parser.add_argument("--ate", type=_parse_data, help="Fim do intervalo")
    args = parser.parse_args()

    if args.de or args.ate:
        if not (args.de and args.ate):
            parser.error("use --de e --ate juntos para um intervalo")
        inicio, fim = args.de, args.ate
    elif args.data:
        inicio = fim = args.data
    else:
        inicio = fim = date.today() - timedelta(days=1)  # ontem

    if inicio > fim:
        parser.error("--de não pode ser depois de --ate")

    resultado = auditar(inicio, fim)
    ok = imprimir_relatorio(inicio, fim, resultado)
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
