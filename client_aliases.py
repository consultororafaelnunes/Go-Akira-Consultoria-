"""
client_aliases.py — Normaliza nomes de clientes da GoAkira.

Os arquivos do Meet Recordings usam variantes e erros de digitação
nos nomes de cliente. Este módulo mapeia todos para o nome canônico.
"""

import re

# Mapa: variante (lower, strip) → nome canônico
_ALIASES: dict[str, str] = {
    # Box2Fit
    "box2fit":   "Box2Fit",
    "box 2 fit": "Box2Fit",
    "box2 fit":  "Box2Fit",

    # Softli
    "softli":              "Softli",
    "softili":             "Softli",
    "softli - franqueado": "Softli - Franqueado",

    # CWB Runner
    "cwb runner":  "CWB Runner",
    "cwb running": "CWB Runner",
    "cwb run":     "CWB Runner",
    "cwb":         "CWB Runner",

    # Que Tutti de Minas
    "que tutti de minas":  "Que Tutti de Minas",
    "que tutti":           "Que Tutti de Minas",
    "que tuttti de minas": "Que Tutti de Minas",
    "que tuttti":          "Que Tutti de Minas",

    # Indústria da Coxinha
    "idc":                  "Indústria da Coxinha",
    "ind coxinha":          "Indústria da Coxinha",
    "ind. coxinha":         "Indústria da Coxinha",
    "industria da coxinha": "Indústria da Coxinha",
    "indústria da coxinha": "Indústria da Coxinha",

    # Far Consultoria
    "far consultoria": "Far Consultoria",
    "far consulting":  "Far Consultoria",
    "far":             "Far Consultoria",

    # Idayo Sorvetes
    "idayo sorvetes": "Idayo Sorvetes",
    "idayo":          "Idayo Sorvetes",

    # Açaí Island
    "açaí island": "Açaí Island",
    "acai island": "Açaí Island",
    "açai island": "Açaí Island",

    # We Flores
    "we flores": "We Flores",
    "weflores":  "We Flores",

    # Carrano
    "carrano":          "Carrano",
    "carrano calçados": "Carrano",
    "carrano calcados": "Carrano",

    # BW9
    "bw9":  "BW9",
    "bw 9": "BW9",

    # Colégio Bal
    "colégio bal": "Colégio Bal",
    "colegio bal": "Colégio Bal",
    "col. bal":    "Colégio Bal",

    # Laftech
    "laftech":             "Laftech",
    "laf tech":            "Laftech",
    "laf tech (distribuidora)": "Laftech",
    "laf":                 "Laftech",

    # Gradisa
    "gradisa": "Gradisa",

    # Meraki Gyros
    "meraki gyros": "Meraki Gyros",
    "meraki":       "Meraki Gyros",

    # Sorvetes Capricho
    "sorvetes capricho": "Sorvetes Capricho",
    "capricho":          "Sorvetes Capricho",

    # Farragoni Café
    "farragoni café": "Farragoni Café",
    "farragoni cafe": "Farragoni Café",
    "farragoni":      "Farragoni Café",

    # Plaucius / MFS Assessoria Esportiva
    "plaucius":                    "Plaucius",
    "mfs assessoria esportiva":    "Plaucius",
    "plaucius (mfs assessoria esportiva)": "Plaucius",

    # LR Imóveis
    "lr imóveis": "LR Imóveis",
    "lr imoveis": "LR Imóveis",

    # Maçã Verde Sorvetes
    "maçã verde sorvetes": "Maçã Verde Sorvetes",
    "maca verde sorvetes": "Maçã Verde Sorvetes",
    "maçã verde":          "Maçã Verde Sorvetes",

    # Loja do Queijo
    "loja do queijo": "Loja do Queijo",

    # WG10 / Essência di Fiori
    "wg10":                      "WG10",
    "essência di fiori":         "WG10",
    "essencia di fiori":         "WG10",
    "wg10 (essência de fiori)":  "WG10",
    "wg10 (essencia de fiori)":  "WG10",

    # App Launch
    "app launch":            "App Launch",
    "app launch & goakira":  "App Launch",  # variante de nome de arquivo usada em algumas reuniões

    # Migak (opera também sob a marca Sijan)
    "migak e sijan":  "Migak",
    "migak & sijan":  "Migak",

    # Citroni Brokers
    "citroni brokers": "Citroni Brokers",
    "citroni":         "Citroni Brokers",
    "critroni":        "Citroni Brokers",  # erro de digitação usado nos títulos reais do calendário

    # Grupo Amo
    "grupo amo": "Grupo Amo",

    # Migak
    "migak": "Migak",
    "migak & goakira": "Migak",

    # IBF
    "ibf": "IBF",

    # Canteiro Fácil
    "canteiro fácil": "Canteiro Fácil",
    "canteiro facil": "Canteiro Fácil",

    # Pura Mania
    "pura mania": "Pura Mania",
    "puramania":  "Pura Mania",

    # SPIB
    "spib": "SPIB",

    # Sai de Moto
    "sai de moto": "Sai de Moto",

    # Idayo (sem sorvetes)
    "idayo sorvetes": "Idayo Sorvetes",
    "idayo":          "Idayo Sorvetes",

    # Vizzela
    "vizzela": "Vizzela",
    "vizela":  "Vizzela",

    # Santa Edwiges
    "santa edwiges":    "Santa Edwiges",
    "santa de edwiges": "Santa Edwiges",

    # CTA
    "cta":            "CTA",
    "cta tricologia": "CTA",

    # MedSempre
    "medsempre":  "MedSempre",
    "medsempre-": "MedSempre",

    # People Telecom
    "people telecom": "People Telecom",

    # Tubarão do Açaí
    "tubarão do açai": "Tubarão do Açaí",
    "tubarao do acai": "Tubarão do Açaí",

    # Ipanema Papéis
    "ipanema papéis": "Ipanema Papéis",
    "ipanema papeis": "Ipanema Papéis",

    # Keystone
    "keystone": "Keystone",
}

# Projetos ainda em andamento (fase consultiva ativa)
PROJETOS_ATIVOS: set[str] = {
    # Rafael
    "Açaí Island", "Carrano", "Convicção Editora", "Indústria da Coxinha",
    "Softli - Franqueado", "Urla Sorvetes",
    # Ivan
    "Colégio Bal", "IBF", "Laftech", "Gradisa", "Santa Edwiges",
    # Thais
    "Plaucius", "Grupo Amo", "Migak", "Meraki Gyros", "Sorvetes Capricho",
    "Farragoni Café", "App Launch", "Citroni Brokers", "Duran Esquadrias",
    # Kelly (MN ativo)
    "Maçã Verde Sorvetes", "LR Imóveis", "People Telecom",
    # Ivan
    "Vizzela",
}

# Projetos que concluíram a fase consultiva
PROJETOS_CONCLUIDOS: set[str] = {
    "Box2Fit", "Softli", "CWB Runner", "Que Tutti de Minas",
    "Idayo Sorvetes", "We Flores", "Far Consultoria", "BW9",
    "Loja do Queijo", "WG10", "Pura Mania", "Canteiro Fácil", "SPIB",
    "Sai de Moto",
    # Kelly (MN concluído)
    "CTA", "MedSempre", "Tubarão do Açaí", "Ipanema Papéis", "Keystone",
}

# Todos os clientes canônicos
TODOS_PROJETOS: set[str] = PROJETOS_ATIVOS | PROJETOS_CONCLUIDOS


def normalize_client(raw: str) -> str:
    """
    Retorna o nome canônico do cliente.
    Se não encontrar no mapa, devolve o nome original (limpo).
    """
    return _ALIASES.get(raw.strip().lower(), raw.strip())


# Chaves de alias ordenadas da mais longa para a mais curta, para que
# "cta tricologia" seja testado antes de "cta" em find_client_in_text.
_ALIAS_KEYS_BY_LEN = sorted(_ALIASES.keys(), key=len, reverse=True)


def find_client_in_text(text: str) -> str | None:
    """
    Procura, dentro de um texto livre (ex: nome de arquivo), algum alias de
    cliente conhecido como palavra/expressão isolada, e retorna o nome canônico.
    Usado como último recurso para reconhecer nomes de arquivo fora do padrão.
    Retorna None se nenhum alias conhecido aparecer no texto.
    """
    lowered = text.lower()
    for key in _ALIAS_KEYS_BY_LEN:
        if re.search(r"\b" + re.escape(key) + r"\b", lowered):
            return _ALIASES[key]
    return None


def list_clients(apenas_concluidos: bool = False) -> list[str]:
    """Retorna lista de clientes canônicos ordenada alfabeticamente."""
    base = PROJETOS_CONCLUIDOS if apenas_concluidos else TODOS_PROJETOS
    return sorted(base)


def is_active(cliente: str) -> bool:
    """True se o projeto ainda está na fase consultiva ativa."""
    return normalize_client(cliente) in PROJETOS_ATIVOS
