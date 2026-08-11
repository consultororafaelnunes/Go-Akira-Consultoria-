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

# Pasta "Meet Recordings" de cada consultor (ESTRUTURA ANTIGA — pasta plana:
# os Google Docs de transcrição ficam soltos no primeiro nível da pasta).
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

# Pasta "Google Meet" de cada consultor (ESTRUTURA NOVA — desde ~24/07/2026).
# O Google passou a guardar as gravações/transcrições em UMA SUBPASTA POR
# REUNIÃO (ou por série recorrente) dentro de uma pasta "Google Meet" na raiz
# do Drive do consultor. Cada subpasta contém o Doc de transcrição
# ("... - Anotações do Gemini") e o vídeo ("... - Recording"), que podem ser
# arquivos reais OU atalhos (google-apps.shortcut) para os originais.
#
# COEXISTE com a estrutura antiga: a migração é gradual e por consultor — a
# mesma conta pode ter reuniões novas aqui e antigas em MEET_RECORDINGS_FOLDERS
# ao mesmo tempo. Por isso o pipeline varre AS DUAS.
#
# Preenchida conforme cada consultor compartilhar a pasta "Google Meet" com
# c10@goakira.com.br (mesmo passo da antiga).
MEET_RECORDINGS_SUBFOLDER_ROOTS: dict[str, str] = {
    "Rafael": "1bkqSDR8WHA7gX0_MeTgLPrwvnezkzwzR",  # c10 — raiz do Drive de c10@goakira.com.br
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
    # Adicionados em 24/07/2026 — resolvendo os avisos de "pasta fallback"
    # encontrados na auditoria semanal (clientes existem no Drive, só não
    # estavam cadastrados aqui ainda).
    "Gradisa":              "1qZtpNuw39tBGUQLp4UoWVPYHyhPH6IeJ",
    "Citroni Brokers":      "1JlRP_HLw4eb7A0EJApYtp2CUPRZKfC0E",
    "Sorvetes Capricho":    "1L3u4xxVR2gXMOHqsh6ScHtE829H6AkAN",
    "Convicção Editora":    "1W8EdJ26vsvptKPmrvNR4oY0okyH_AVNu",
    "Urla Sorvetes":        "1QMWorRzyuUNFCw78nAtBi18FtIffGkKK",
    "Duran Esquadrias":     "1doR4rfBkdTscg28aqnS61ftYyHkTO1j6",
    "Maçã Verde Sorvetes":  "1CfflGAr4IBwPwh2bx-i3knNetM40CDmM",
    "Grupo Amo":            "1w22I1N2xnVNt2E70Y6q5A6ruPhrrxQ6M",
    "Migak":                "1kCLSCbG36an7Xl-ITTf6774ZN21fDLIa",
    # Bonus: encontrado durante a mesma varredura, também faltava
    "App Launch":           "1lrEf80NLNPW_kfbkVuonGg6YBByb557N",
    # Adicionado em 11/08/2026 — cliente novo (Rafael). A pasta já existia no
    # Drive, mas não estava mapeada aqui: a ata do Kickoff (03/08) caiu no
    # fallback da raiz de Clientes por isso.
    "Viavolt":              "1Qr_5KFdYFuARWF6Y0RW4I6YSEKHyIADp",
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
