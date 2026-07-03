"""
drive_folders.py — Mapeamento estático de clientes → IDs de pastas no Drive GoAkira.

Estrutura:
  Consultoria (Shared Drive)
    └─ Clientes
         └─ 1.Formatação e Outros   ← PASTA_RAIZ_CLIENTES
               ├─ Box2Fit/
               ├─ Softli/
               └─ ...

Convenção de subpastas dentro de cada cliente:
  Business Plan  →  "1. Business Plan" | "1.Business Plan" | "Business Plan" | "BP"
  Atas           →  subpasta que contenha "Atas" — criada como "6. Atas e Formalizações" se ausente
  Briefings      →  "Briefings" — criada se ausente
"""

from googleapiclient.discovery import build

PASTA_RAIZ_CLIENTES = "1XYNQf0Il4JQ85GeupTGC71-Mc7jSLa_K"

# Pasta "Meet Recordings" de cada consultor.
# Preenchida conforme cada consultor compartilhar a pasta com c10@goakira.com.br.
# Passo: Drive → Meet Recordings → Compartilhar → c10@goakira.com.br (Leitor)
# Depois enviar o link da pasta para incluir o ID aqui.
MEET_RECORDINGS_FOLDERS: dict[str, str] = {
    "Rafael":        "1tY6yBpKj4UjSD4lwG_iLg0hCn2vRik0P",  # c10 — já configurado
    "Ivan Oréfice":  "1Av-5g6t-WNU9Hg6VuX8t_niE-qK6sNxt",
    "Thais Andrade": "1Iz5fLfye0WqpvEeVWKiKyZsvIGPSvDep",
    "Kelly Almeida": "1LEpPNcEbdBqYE55w8btlBsA3EQEaeCPe",
    "Marco Paixão":  "1wmyQPZJaEdrCr33FzvNt7EYO-Is-KXmJ",
}

# Nome canônico (client_aliases.py) → ID da pasta no Drive
# Todos esses IDs são do Shared Drive GoAkira — Clientes / 1.Formatação e Outros
CLIENT_FOLDERS: dict[str, str] = {
    "Açaí Island":          "1nRaVI9TSP0gHukpgCNSl6mz9VQ9cjcj_",
    "Box2Fit":              "1cwUda0WHZHqYxhnr-hxuJSWI2MATLqyK",
    "BW9":                  "1sokcOCUb9DJJ7iOFWcsocK8zFSKq9hWs",
    "Carrano":              "1mV-BgVqZRiFiLXQ8W7qCIaShdnhqoGaZ",
    "CWB Runner":           "1aml48l04DPu9q-OwL1J-0uMtzUn_n_-q",
    "Far Consultoria":      "15m_NDgdm0OZ3hgrmA8GSh6S2w8iPizd8",
    "Idayo Sorvetes":       "1lT3j8c8prM5DTDbDP_gOtngbPSM2mI6y",
    "Indústria da Coxinha": "1QJ8SYmjyCouU8btiNYsc3vKu1pPCFOif",
    "Que Tutti de Minas":   "1o6mDW579TMW63mgOUViQqa6pFJt22kxN",
    "Softli":               "1LP8lxIgzi5giWApA6xk5r45818DzLDYX",
    "We Flores":            "14OZ3KxgdBzJd7STOSeldGw-0XXCXR1E-",
}


# Cache in-memory por execução — evita chamadas repetidas ao Drive para a mesma pasta
_FOLDER_CACHE: dict[str, list[dict]] = {}


def _list_subfolders(service, parent_id: str) -> list[dict]:
    """Lista todas as subpastas diretas de uma pasta (Shared Drive safe). Usa cache por run."""
    if parent_id in _FOLDER_CACHE:
        return _FOLDER_CACHE[parent_id]
    result = service.files().list(
        q=(
            f"'{parent_id}' in parents"
            " and mimeType='application/vnd.google-apps.folder'"
            " and trashed=false"
        ),
        fields="files(id, name)",
        pageSize=50,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    _FOLDER_CACHE[parent_id] = result.get("files", [])
    return _FOLDER_CACHE[parent_id]


def _create_folder(service, name: str, parent_id: str) -> str:
    """Cria uma pasta e retorna o ID."""
    f = service.files().create(
        body={
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        },
        fields="id",
        supportsAllDrives=True,
    ).execute()
    return f["id"]


# Clientes com estrutura fora do padrão — mapeados diretamente à pasta de Atas
# (evita a busca por Business Plan que não existe ou tem nome diferente)
CUSTOM_ATAS_FOLDERS: dict[str, str] = {
    # Softli: subpasta "Reuniões e Formalizações" no lugar do BP
    "Softli": "1DImRYHWLXyiPhYFY2BWen2Y1IzgAj73w",
    # BW9: projeto recente sem subpastas — pasta criada após esse mapeamento
    # Será atualizado quando a pasta Business Plan for criada
}


def get_client_folder_id(cliente: str) -> str | None:
    """Retorna o ID da pasta do cliente, ou None se não mapeado."""
    return CLIENT_FOLDERS.get(cliente)


def find_bp_folder(service, client_folder_id: str) -> str | None:
    """
    Localiza a subpasta de Business Plan dentro da pasta do cliente.
    Aceita variações: "1. Business Plan", "1.Business Plan", "Business Plan", "BP".
    Retorna None se não encontrar.
    """
    subs = _list_subfolders(service, client_folder_id)
    for f in subs:
        name_lower = f["name"].lower()
        if "business plan" in name_lower or name_lower.strip() in ("bp", "1.bp", "1. bp"):
            return f["id"]
    return None


def find_or_create_atas_folder(service, bp_folder_id: str) -> str:
    """
    Localiza a subpasta de Atas dentro do Business Plan.
    Cria '6. Atas e Formalizações' se não existir.
    """
    subs = _list_subfolders(service, bp_folder_id)
    for f in subs:
        if "atas" in f["name"].lower():
            return f["id"]
    # Não encontrou — cria
    folder_id = _create_folder(service, "6. Atas e Formalizações", bp_folder_id)
    print(f"   Pasta criada: '6. Atas e Formalizações'")
    return folder_id


def find_or_create_briefings_folder(service, client_folder_id: str) -> str:
    """
    Localiza a pasta Briefings dentro da pasta do cliente.
    Cria 'Briefings' se não existir.
    """
    subs = _list_subfolders(service, client_folder_id)
    for f in subs:
        if "briefing" in f["name"].lower():
            return f["id"]
    folder_id = _create_folder(service, "Briefings", client_folder_id)
    print(f"   Pasta criada: 'Briefings'")
    return folder_id


def resolve_atas_folder(service, cliente: str) -> str | None:
    """
    Resolve o ID da pasta de Atas para um cliente.

    Ordem de resolução:
      1. CUSTOM_ATAS_FOLDERS — clientes com estrutura fora do padrão
      2. Caminho padrão: pasta do cliente → Business Plan → Atas e Formalizações
      3. Fallback: se o cliente está mapeado mas sem BP, cria "6. Atas e Formalizações"
         diretamente na raiz do cliente (ex: BW9 que ainda não tem subpastas)

    Retorna None apenas se o cliente não estiver mapeado em CLIENT_FOLDERS.
    """
    # 1. Exceção direta (Softli e futuros casos especiais)
    if cliente in CUSTOM_ATAS_FOLDERS:
        return CUSTOM_ATAS_FOLDERS[cliente]

    client_folder_id = get_client_folder_id(cliente)
    if not client_folder_id:
        return None

    # 2. Caminho padrão: Business Plan → Atas
    bp_folder_id = find_bp_folder(service, client_folder_id)
    if bp_folder_id:
        return find_or_create_atas_folder(service, bp_folder_id)

    # 3. Fallback: sem BP — cria Atas direto na raiz do cliente
    print(f"   Aviso: pasta Business Plan nao encontrada para '{cliente}' — criando Atas na raiz")
    return find_or_create_atas_folder(service, client_folder_id)
