"""
contract_reader.py — Lê o CONTRATO DE SERVIÇO (PDF) na pasta do cliente no Drive
e extrai, via Claude, o que foi efetivamente contratado.

É a base do "de-para" da levantada de mão: separa o que já é ESCOPO CONTRATADO
(o projeto em andamento) do que é uma oportunidade de CROSS-SELL para outras
empresas do ecossistema GoAkira (Potencializee, GDesign, etc.).

Também extrai o prazo em DIAS ÚTEIS descrito no contrato — usado por
project_timeline.py para calcular a etapa/prazo do projeto a partir da data do
Kick Off.

Convenção assumida (confirmada com o time em 05/08/2026):
  - O contrato é um PDF na RAIZ da pasta do cliente (não em subpasta).
  - O nome do arquivo contém "contrato" ou "proposta".

O resultado é cacheado em disco por cliente (contract_cache/{slug}.json),
invalidado quando o arquivo do contrato muda (id + modifiedTime), para não
baixar o PDF nem chamar o Claude a cada execução.
"""

import json
import os
import re
import unicodedata
from io import BytesIO
from pathlib import Path

# Reaproveita o mapeamento de pastas já existente
from drive_folders import get_client_folder_id

MODEL = "claude-haiku-4-5-20251001"
MAX_CONTRACT_CHARS = 30000  # corte de segurança para o prompt
CACHE_DIR = Path(__file__).parent / "contract_cache"
# Versão do schema de extração — muda quando o prompt/pós-processamento muda,
# para invalidar caches antigos (senão um contrato inalterado no Drive manteria
# o resultado no formato velho).
EXTRACTION_VERSION = "v2"

# ── Singletons compartilhados (Drive + Anthropic) ───────────────────────────────

_drive_service = None
_anthropic_client = None
# Cache em memória por execução: cliente -> dict de dados do contrato
_mem_cache: dict[str, dict] = {}


def set_drive_service(service) -> None:
    """Permite reaproveitar um service do Drive já autenticado (evita re-login)."""
    global _drive_service
    _drive_service = service


def _get_drive():
    global _drive_service
    if _drive_service is None:
        from googleapiclient.discovery import build
        from create_minutes import get_credentials
        _drive_service = build("drive", "v3", credentials=get_credentials())
    return _drive_service


def _get_anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        _anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _anthropic_client


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _slug(cliente: str) -> str:
    s = unicodedata.normalize("NFKD", cliente).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return s or "cliente"


def _parse_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    return json.loads(text)


def find_contract_pdf(service, cliente: str) -> dict | None:
    """
    Localiza o PDF do contrato na RAIZ da pasta do cliente.
    Prioriza nomes com 'contrato', depois 'proposta'. Entre candidatos do mesmo
    grupo, escolhe o modificado mais recentemente. Retorna dict do arquivo
    (id, name, modifiedTime, webViewLink) ou None.
    """
    folder_id = get_client_folder_id(cliente)
    if not folder_id:
        return None
    try:
        res = service.files().list(
            q=(
                f"'{folder_id}' in parents "
                "and mimeType='application/pdf' and trashed=false"
            ),
            fields="files(id,name,modifiedTime,webViewLink)",
            pageSize=100,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
    except Exception as e:
        print(f"   Aviso: falha ao listar PDFs de '{cliente}' — {e}")
        return None

    pdfs = res.get("files", [])
    if not pdfs:
        return None

    contratos = [f for f in pdfs if "contrato" in f["name"].lower()]
    propostas = [f for f in pdfs if "proposta" in f["name"].lower()]
    grupo = contratos or propostas
    if not grupo:
        return None
    grupo.sort(key=lambda f: f.get("modifiedTime", ""), reverse=True)
    return grupo[0]


def _download_pdf_text(service, file_id: str) -> str:
    """Baixa o PDF do Drive e extrai o texto com pypdf."""
    from pypdf import PdfReader

    data = service.files().get_media(
        fileId=file_id, supportsAllDrives=True
    ).execute()
    if not isinstance(data, bytes):
        data = bytes(data)

    reader = PdfReader(BytesIO(data))
    partes = []
    for page in reader.pages:
        try:
            partes.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(partes).strip()


_EXTRACTION_SYSTEM = """Você lê CONTRATOS DE PRESTAÇÃO DE SERVIÇOS da GoAkira (consultoria de \
formatação/expansão de franquias) e extrai dados estruturados. Retorne APENAS um JSON válido, \
sem markdown, sem texto adicional.

Campos:
{
  "escopo_contratado":    "Resumo objetivo (máx. ~500 caracteres) dos serviços EFETIVAMENTE contratados neste contrato — o projeto em andamento",
  "servicos_contratados": ["Lista curta dos serviços/entregáveis explicitamente contratados"],
  "dias_uteis_total":     número inteiro de dias úteis de prazo TOTAL do projeto, APENAS se o contrato der um único número total explícito — senão null,
  "etapas":               [{"nome": "Nome da etapa/fase", "dias_uteis": número inteiro de dias úteis daquela etapa, "a_partir_de": "marco a partir do qual a etapa é contada (ex: Kick Off, Business Plan, Instrumentos Jurídicos, assinatura)"}],
  "prazo_texto":          "Trecho literal do contrato que menciona os prazos em dias úteis"
}

Regras:
- NÃO invente. Extraia apenas o que está escrito no contrato.
- Muitos contratos da GoAkira NÃO dão um total único: dão o prazo de cada ETAPA em dias úteis, uma começando quando a anterior termina. Nesse caso, preencha "etapas" com o prazo de cada uma e deixe "dias_uteis_total": null — o total será somado depois.
- Se o contrato der um único prazo total explícito, preencha "dias_uteis_total" e pode deixar "etapas": [].
- Se o contrato não menciona nenhum prazo em dias úteis, use "dias_uteis_total": null e "etapas": [].
- "servicos_contratados" deve refletir o escopo real do contrato, não o catálogo geral da GoAkira.
- Responda SOMENTE com o JSON."""


def _extract_with_claude(texto: str) -> dict:
    client = _get_anthropic()
    if len(texto) > MAX_CONTRACT_CHARS:
        texto = texto[:MAX_CONTRACT_CHARS] + "\n[CONTRATO TRUNCADO]"
    msg = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=_EXTRACTION_SYSTEM,
        messages=[{"role": "user", "content":
                   f"--- CONTRATO ---\n{texto}\n--- FIM ---\n\nRetorne o JSON."}],
    )
    return _parse_json(msg.content[0].text)


def _empty_result(cliente: str, motivo: str) -> dict:
    return {
        "cliente": cliente,
        "encontrado": False,
        "motivo": motivo,
        "escopo_contratado": "",
        "servicos_contratados": [],
        "dias_uteis": None,
        "dias_uteis_fonte": "",
        "etapas": [],
        "prazo_texto": "",
        "contrato_link": "",
        "contrato_nome": "",
    }


def _normalizar_etapas(raw) -> list[dict]:
    """Sanitiza a lista de etapas extraída (nome + dias_uteis inteiros)."""
    etapas = []
    if not isinstance(raw, list):
        return etapas
    for e in raw:
        if not isinstance(e, dict):
            continue
        try:
            dias = int(e.get("dias_uteis")) if e.get("dias_uteis") is not None else None
        except (TypeError, ValueError):
            dias = None
        etapas.append({
            "nome": (e.get("nome") or "").strip() or "—",
            "dias_uteis": dias,
            "a_partir_de": (e.get("a_partir_de") or "").strip(),
        })
    return etapas


def _resolver_dias_uteis(total_explicito, etapas: list[dict]) -> tuple[int | None, str]:
    """
    Define o total de dias úteis do projeto e a fonte:
      - total explícito no contrato, se houver;
      - senão, soma das etapas (elas correm em sequência, uma começando quando a
        anterior finaliza — é o prazo nominal total a partir do Kick Off);
      - senão None.
    """
    try:
        total = int(total_explicito) if total_explicito is not None else None
    except (TypeError, ValueError):
        total = None
    if total is not None:
        return total, "total explícito no contrato"
    dias_etapas = [e["dias_uteis"] for e in etapas if e.get("dias_uteis")]
    if dias_etapas:
        return sum(dias_etapas), "soma das etapas do contrato"
    return None, ""


def get_contract_data(cliente: str, service=None, force: bool = False) -> dict:
    """
    Retorna os dados extraídos do contrato do cliente. Usa cache em memória e em
    disco (invalida quando o arquivo muda). NUNCA levanta exceção — em qualquer
    falha retorna um resultado "não encontrado" com o motivo, para não quebrar
    o pipeline de sumarização/relatório.

    Estrutura retornada:
      {cliente, encontrado, motivo, escopo_contratado, servicos_contratados,
       dias_uteis, prazo_texto, contrato_link, contrato_nome}
    """
    if not force and cliente in _mem_cache:
        return _mem_cache[cliente]

    try:
        svc = service or _get_drive()
    except Exception as e:
        return _empty_result(cliente, f"sem acesso ao Drive: {e}")

    meta = find_contract_pdf(svc, cliente)
    if not meta:
        result = _empty_result(cliente, "contrato PDF não localizado na pasta do cliente")
        _mem_cache[cliente] = result
        return result

    cache_path = CACHE_DIR / f"{_slug(cliente)}.json"
    cache_key = f"{EXTRACTION_VERSION}:{meta['id']}:{meta.get('modifiedTime','')}"

    if not force and cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if cached.get("_cache_key") == cache_key:
                _mem_cache[cliente] = cached
                return cached
        except Exception:
            pass  # cache corrompido — regenera

    # Baixa + extrai
    try:
        texto = _download_pdf_text(svc, meta["id"])
    except Exception as e:
        return _empty_result(cliente, f"falha ao baixar/ler o PDF: {e}")

    if not texto or len(texto) < 100:
        result = _empty_result(cliente, "PDF sem texto extraível (possível contrato escaneado)")
        result["contrato_link"] = meta.get("webViewLink", "")
        result["contrato_nome"] = meta.get("name", "")
        _mem_cache[cliente] = result
        return result

    try:
        extracted = _extract_with_claude(texto)
    except Exception as e:
        return _empty_result(cliente, f"falha na extração via Claude: {e}")

    etapas = _normalizar_etapas(extracted.get("etapas"))
    dias, fonte = _resolver_dias_uteis(extracted.get("dias_uteis_total"), etapas)

    result = {
        "cliente": cliente,
        "encontrado": True,
        "motivo": "",
        "escopo_contratado": (extracted.get("escopo_contratado") or "").strip(),
        "servicos_contratados": [s for s in (extracted.get("servicos_contratados") or []) if s],
        "dias_uteis": dias,
        "dias_uteis_fonte": fonte,
        "etapas": etapas,
        "prazo_texto": (extracted.get("prazo_texto") or "").strip(),
        "contrato_link": meta.get("webViewLink", ""),
        "contrato_nome": meta.get("name", ""),
        "_cache_key": cache_key,
    }

    try:
        CACHE_DIR.mkdir(exist_ok=True)
        cache_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"   Aviso: falha ao gravar cache do contrato de '{cliente}' — {e}")

    _mem_cache[cliente] = result
    return result


def get_escopo_contratado_texto(cliente: str, service=None) -> str:
    """
    Texto do escopo contratado para injetar no prompt de sumarização (evita
    sinalizar como oportunidade nova um serviço que já está no contrato).

    Usa o contrato real quando disponível; senão cai no mapeamento estático de
    consultants.get_escopo_contratado() — que já sabe que o pacote de Formatação
    de Franquias entrega geomarketing/jurídico/manuais dentro do mesmo contrato.
    """
    from consultants import get_escopo_contratado as _estatico

    data = get_contract_data(cliente, service=service)
    if data.get("encontrado") and data.get("escopo_contratado"):
        base = data["escopo_contratado"]
        servicos = data.get("servicos_contratados") or []
        if servicos:
            base += " | Serviços contratados: " + "; ".join(servicos)
        # Complementa com o conhecimento estrutural (pacote de franquias),
        # que o contrato pode não detalhar item a item.
        estatico = _estatico(cliente)
        if estatico and estatico != "sem registro de escopo contratado":
            base += f" | Contexto: {estatico}"
        return base

    return _estatico(cliente)
