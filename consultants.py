"""
consultants.py — Registro de consultores e mapeamento cliente → consultor por fase.

Fases:
  BP  — Business Plan (atas geradas pelo agente)
  IJ  — Instrumentos Jurídicos (recebe Briefing Jurídico)
  MN  — Manuais Operacionais (recebe Briefing de Manuais)

Regras fixas:
  - Briefing Jurídico  → sempre Marco Paixão
  - Briefing de Manuais → Kelly ou Thais; se não mapeado, o agente pergunta no terminal
"""

# ── Registro de consultores ────────────────────────────────────────────────────

CONSULTANTS: dict[str, dict] = {
    "Rafael": {
        "email": "c10@goakira.com.br",
    },
    "Ivan Oréfice": {
        "email": "ivan.orefice@goakira.com.br",
    },
    "Thais Andrade": {
        "email": "c3@goakira.com.br",
    },
    "Kelly Almeida": {
        "email": "c8@goakira.com.br",
    },
    "Marco Paixão": {
        "email": "marco.paixao@goakira.com.br",
    },
}

# Consultor fixo para Briefing Jurídico (sempre Marco)
JURIDICO_CONSULTANT = "Marco Paixão"

# Consultoras de Manuais elegíveis para o prompt interativo
MANUAIS_CONSULTANTS = ["Kelly Almeida", "Thais Andrade"]


# ── Mapeamento por cliente ─────────────────────────────────────────────────────

# "mn": None → não definido ainda; get_manuais_consultant() perguntará no terminal.
# Atualizar conforme a planilha de andamento for atribuindo responsáveis.

CLIENT_CONSULTANTS: dict[str, dict] = {
    # ── Rafael ────────────────────────────────────────────────────────────────
    "Açaí Island":        {"bp": "Rafael",        "ij": None,           "mn": None},
    "Carrano":            {"bp": "Rafael",        "ij": None,           "mn": None},
    "Indústria da Coxinha":{"bp": "Rafael",       "ij": None,           "mn": None},
    "Softli":             {"bp": "Rafael",        "ij": None,           "mn": None},
    "Softli - Franqueado":{"bp": "Rafael",        "ij": None,           "mn": None},
    "Box2Fit":            {"bp": "Rafael",        "ij": "Marco Paixão", "mn": None},
    "BW9":                {"bp": "Rafael",        "ij": None,           "mn": None},
    "CWB Runner":         {"bp": "Rafael",        "ij": "Marco Paixão", "mn": None},
    "Far Consultoria":    {"bp": "Rafael",        "ij": "Marco Paixão", "mn": None},
    "Idayo Sorvetes":     {"bp": "Rafael",        "ij": None,           "mn": "Kelly Almeida"},
    "Que Tutti de Minas": {"bp": "Rafael",        "ij": "Marco Paixão", "mn": None},
    "We Flores":          {"bp": "Rafael",        "ij": "Marco Paixão", "mn": None},

    # ── Ivan Oréfice ──────────────────────────────────────────────────────────
    "Colégio Bal":        {"bp": "Ivan Oréfice",  "ij": None,           "mn": None},
    "IBF":                {"bp": "Ivan Oréfice",  "ij": None,           "mn": None},
    "Laftech":            {"bp": "Ivan Oréfice",  "ij": None,           "mn": None},
    "Gradisa":            {"bp": "Ivan Oréfice",  "ij": "Marco Paixão", "mn": None},
    "Pura Mania":         {"bp": "Ivan Oréfice",  "ij": None,           "mn": None},
    "Canteiro Fácil":     {"bp": "Ivan Oréfice",  "ij": None,           "mn": None},
    "SPIB":               {"bp": "Ivan Oréfice",  "ij": None,           "mn": None},
    "Vizzela":            {"bp": "Ivan Oréfice",  "ij": None,           "mn": None},

    # ── Thais Andrade ─────────────────────────────────────────────────────────
    "Plaucius":           {"bp": "Thais Andrade", "ij": None,           "mn": None},
    "Grupo Amo":          {"bp": "Thais Andrade", "ij": None,           "mn": "Kelly Almeida"},
    "Migak":              {"bp": "Thais Andrade", "ij": None,           "mn": None},
    "Meraki Gyros":       {"bp": "Thais Andrade", "ij": "Marco Paixão", "mn": "Kelly Almeida"},
    "Sorvetes Capricho":  {"bp": "Thais Andrade", "ij": "Marco Paixão", "mn": "Kelly Almeida"},
    "Farragoni Café":     {"bp": "Thais Andrade", "ij": None,           "mn": "Thais Andrade"},
    "App Launch":         {"bp": "Thais Andrade", "ij": None,           "mn": None},
    "Citroni Brokers":    {"bp": "Thais Andrade", "ij": None,           "mn": None},
    "WG10":               {"bp": "Thais Andrade", "ij": None,           "mn": None},
    "Loja do Queijo":     {"bp": "Thais Andrade", "ij": "Marco Paixão", "mn": None},
    "LR Imóveis":         {"bp": "Thais Andrade", "ij": "Marco Paixão", "mn": "Kelly Almeida"},
    "Maçã Verde Sorvetes":{"bp": "Thais Andrade", "ij": "Marco Paixão", "mn": "Kelly Almeida"},

    # ── Kelly Almeida (MN sem BP GoAkira) ────────────────────────────────────
    "Sai de Moto":        {"bp": None,            "ij": None,           "mn": "Kelly Almeida"},
    "CTA":                {"bp": None,            "ij": None,           "mn": "Kelly Almeida"},
    "MedSempre":          {"bp": None,            "ij": None,           "mn": "Kelly Almeida"},
    "People Telecom":     {"bp": None,            "ij": None,           "mn": "Kelly Almeida"},
    "Tubarão do Açaí":    {"bp": None,            "ij": None,           "mn": "Kelly Almeida"},
    "Ipanema Papéis":     {"bp": None,            "ij": None,           "mn": "Kelly Almeida"},
    "Keystone":           {"bp": None,            "ij": None,           "mn": "Kelly Almeida"},
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_consultant_email(nome: str) -> str | None:
    """Retorna o e-mail de um consultor pelo nome canônico."""
    c = CONSULTANTS.get(nome)
    return c["email"] if c else None


def get_bp_consultant(cliente: str) -> str | None:
    """Retorna o nome do consultor responsável pelo BP do cliente."""
    c = CLIENT_CONSULTANTS.get(cliente, {})
    return c.get("bp")


def get_juridico_email() -> str:
    """E-mail do responsável por Instrumentos Jurídicos (sempre Marco)."""
    return CONSULTANTS[JURIDICO_CONSULTANT]["email"]


def get_manuais_consultant(cliente: str) -> str | None:
    """
    Retorna o nome do consultor de Manuais do cliente.
    Se não estiver mapeado, pergunta interativamente no terminal.
    Retorna None se o usuário pular (input vazio).
    """
    c = CLIENT_CONSULTANTS.get(cliente, {})
    nome = c.get("mn")
    if nome:
        return nome

    # Não mapeado — pergunta no terminal
    print(f"\n   Consultor de Manuais para '{cliente}' não definido.")
    for i, n in enumerate(MANUAIS_CONSULTANTS, 1):
        email = CONSULTANTS[n]["email"]
        print(f"   [{i}] {n} <{email}>")
    print(f"   [0] Pular (não enviar e-mail de Manuais)")

    while True:
        try:
            resp = input("   Escolha: ").strip()
            if resp == "0" or resp == "":
                return None
            idx = int(resp) - 1
            if 0 <= idx < len(MANUAIS_CONSULTANTS):
                escolha = MANUAIS_CONSULTANTS[idx]
                # Salva em memória para a sessão atual (não persiste)
                c["mn"] = escolha
                return escolha
        except (ValueError, KeyboardInterrupt):
            pass
        print("   Opção inválida. Tente novamente.")


def get_manuais_email(cliente: str) -> str | None:
    """Retorna o e-mail do consultor de Manuais, perguntando se necessário."""
    nome = get_manuais_consultant(cliente)
    return get_consultant_email(nome) if nome else None
