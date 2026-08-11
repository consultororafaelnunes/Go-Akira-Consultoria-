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

# Catálogo de serviços do ecossistema GoAkira — usado pelo Claude para
# reconhecer oportunidades comerciais ("levantada de mão") durante a
# sumarização de reuniões: quando o cliente menciona uma dor/necessidade
# que se encaixa em um desses serviços, fora do escopo do projeto atual.
#
# IMPORTANTE (revisado em 22/07/2026, a partir do material de kick-off
# "Convicção Editora - Consultoria - Kick Off.pptx.pdf"): o projeto de
# Formatação de Franquias tem 8 etapas fixas (Kick Off, BP Franqueado,
# Viabilidade Franqueado, BP Franqueador, Viabilidade Franqueador, Estudo e
# Plano de Expansão, Instrumentos Jurídicos, Processos e Manualização) que já
# entregam, DENTRO do mesmo contrato: geomarketing, consultoria jurídica,
# manualização, consultoria financeira, funil comercial, pesquisa de mercado
# e treinamentos — nenhum desses é oportunidade nova para quem já contratou
# o pacote completo (ver get_escopo_contratado()). Por isso a lista abaixo
# contém só serviços de OUTROS pilares do ecossistema — coisas que um
# cliente de Formatação de Franquias normalmente NÃO tem incluído.
#
# Atualizado em 22/07/2026 com os itens específicos das duas empresas irmãs
# do ecossistema (materiais institucionais "POTENCIALIZEE.pdf" e
# "GDESIGN.pdf"), no lugar de rótulos genéricos como "Branding" isolado:
#   - Potencializee = marketing/performance (pilar "Campanhas de Expansão,
#     Branding & Performance Digital&Física")
#   - GDesign = arquitetura comercial/PDV (pilar "Design de Loja, Experiência
#     do Cliente & Padrão Visual")
SERVICOS_GOAKIRA: list[str] = [
    # Potencializee (marketing)
    "Construção de Marca — Naming, Identidade Verbal e Visual",
    "Reposicionamento e Arquitetura Estratégica de Marca",
    "Social Media Estratégico (Gestão de Redes Sociais)",
    "Performance e Mídia Paga (Tráfego Pago)",
    "Marketing para E-commerce",
    "Geração de Leads (Inbound) para Venda de Franquias",
    "Geração de Leads B2B",
    # GDesign (arquitetura comercial / PDV)
    "Desenvolvimento de Conceito e Projeto Piloto de Loja/PDV",
    "Visual Merchandising",
    "Comunicação Visual do Ponto de Venda",
    "Projeto Arquitetônico de Rollout e Guia de Padronização",
    # Outros pilares do ecossistema
    "Integração de Canais e Estratégia Omnichannel",
    "Business Valuation",
    "Registro de Marcas",
    "Associação ABF",
    "Licenciamento de Marcas",
    "Criação de Dashboard/BI",
    "Expansão Terceirizada / Broker de Ponto Comercial",
    "Captação de Investidores (Portal Goakira Invest)",
    "Curso/Palestra sobre Investir em Franquias",
    "Participação em Eventos do Setor (NRF, SXSW, Retail Tours)",
]

# ── Responsáveis comerciais por pilar (gatilho semântico da "levantada de mão") ─
#
# Calibragem: uma oportunidade só é uma "levantada de mão" QUALIFICADA quando a
# conversa liga a necessidade do cliente a um handoff/oferta envolvendo o
# responsável comercial daquele pilar (ex.: "posso marcar uma agenda com a
# Bianca para você entender o que a GDesign faz?"). Se o serviço aparece só
# como tema do projeto, sem esse vínculo comercial, é MENÇÃO de contexto — não
# uma oportunidade a acionar. Cada entrada: pilar → (responsáveis, serviços).
RESPONSAVEIS_COMERCIAIS: dict[str, dict] = {
    "GDesign (arquitetura comercial / design de loja e PDV)": {
        "responsaveis": ["Bianca"],
        "servicos": [
            "Desenvolvimento de Conceito e Projeto Piloto de Loja/PDV",
            "Visual Merchandising",
            "Comunicação Visual do Ponto de Venda",
            "Projeto Arquitetônico de Rollout e Guia de Padronização",
        ],
    },
    "Potencializee (marketing, branding e performance)": {
        "responsaveis": ["Fabiana", "Naka"],
        "servicos": [
            "Construção de Marca — Naming, Identidade Verbal e Visual",
            "Reposicionamento e Arquitetura Estratégica de Marca",
            "Social Media Estratégico (Gestão de Redes Sociais)",
            "Performance e Mídia Paga (Tráfego Pago)",
            "Marketing para E-commerce",
            "Geração de Leads (Inbound) para Venda de Franquias",
            "Geração de Leads B2B",
        ],
    },
    # Fabiana e Naka também respondem pela Consultoria (demais serviços do
    # ecossistema fora de GDesign/Potencializee).
    "Consultoria (demais serviços do ecossistema GoAkira)": {
        "responsaveis": ["Fabiana", "Naka"],
        "servicos": [
            "Integração de Canais e Estratégia Omnichannel",
            "Business Valuation",
            "Registro de Marcas",
            "Associação ABF",
            "Licenciamento de Marcas",
            "Criação de Dashboard/BI",
            "Expansão Terceirizada / Broker de Ponto Comercial",
            "Captação de Investidores (Portal Goakira Invest)",
            "Curso/Palestra sobre Investir em Franquias",
            "Participação em Eventos do Setor (NRF, SXSW, Retail Tours)",
        ],
    },
}


def render_responsaveis_comerciais() -> str:
    """Texto pronto para injetar no prompt de sumarização (gatilho de qualificação)."""
    linhas = []
    for pilar, dados in RESPONSAVEIS_COMERCIAIS.items():
        nomes = " ou ".join(dados["responsaveis"])
        linhas.append(f"  - {pilar} → responsável comercial: {nomes}")
    return "\n".join(linhas)


# Consultoras de Manuais elegíveis para o prompt interativo
MANUAIS_CONSULTANTS = ["Kelly Almeida", "Thais Andrade"]


# ── Mapeamento por cliente ─────────────────────────────────────────────────────

# "mn": None → não definido ainda; get_manuais_consultant() perguntará no terminal.
# Atualizar conforme a planilha de andamento for atribuindo responsáveis.

CLIENT_CONSULTANTS: dict[str, dict] = {
    # ── Rafael ────────────────────────────────────────────────────────────────
    "Açaí Island":        {"bp": "Rafael",        "ij": None,           "mn": None},
    "Carrano":            {"bp": ["Rafael", "Ivan Oréfice"], "ij": None, "mn": None},
    "Convicção Editora":  {"bp": ["Rafael", "Ivan Oréfice"], "ij": None, "mn": None},
    "Urla Sorvetes":      {"bp": "Rafael",        "ij": None,           "mn": None},
    "Viavolt":            {"bp": "Rafael",        "ij": None,           "mn": None},
    "Indústria da Coxinha":{"bp": "Rafael",       "ij": None,           "mn": None},
    "Softli":             {"bp": "Rafael",        "ij": None,           "mn": None},
    "Softli - Franqueado":{"bp": "Rafael",        "ij": None,           "mn": None},
    "Box2Fit":            {"bp": "Rafael",        "ij": "Marco Paixão", "mn": None},
    "BW9":                {"bp": "Rafael",        "ij": None,           "mn": None},
    "CWB Runner":         {"bp": "Rafael",        "ij": "Marco Paixão", "mn": "Kelly Almeida"},
    "Far Consultoria":    {"bp": "Rafael",        "ij": "Marco Paixão", "mn": "Kelly Almeida"},
    "Idayo Sorvetes":     {"bp": "Rafael",        "ij": None,           "mn": "Kelly Almeida"},
    "Que Tutti de Minas": {"bp": "Rafael",        "ij": "Marco Paixão", "mn": "Kelly Almeida"},
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
    "Santa Edwiges":      {"bp": "Ivan Oréfice",  "ij": None,           "mn": None},

    # ── Thais Andrade ─────────────────────────────────────────────────────────
    "Plaucius":           {"bp": "Thais Andrade", "ij": None,           "mn": None},
    "Grupo Amo":          {"bp": "Thais Andrade", "ij": None,           "mn": "Kelly Almeida"},
    "Migak":              {"bp": "Thais Andrade", "ij": "Marco Paixão", "mn": None},
    "Meraki Gyros":       {"bp": "Thais Andrade", "ij": "Marco Paixão", "mn": "Kelly Almeida"},
    "Sorvetes Capricho":  {"bp": "Thais Andrade", "ij": "Marco Paixão", "mn": "Kelly Almeida"},
    "Farragoni Café":     {"bp": "Thais Andrade", "ij": None,           "mn": "Thais Andrade"},
    "App Launch":         {"bp": "Thais Andrade", "ij": None,           "mn": None},
    "Citroni Brokers":    {"bp": "Thais Andrade", "ij": None,           "mn": None},
    "WG10":               {"bp": "Thais Andrade", "ij": None,           "mn": None},
    "Loja do Queijo":     {"bp": "Thais Andrade", "ij": "Marco Paixão", "mn": None},
    "LR Imóveis":         {"bp": "Thais Andrade", "ij": "Marco Paixão", "mn": "Kelly Almeida"},
    "Maçã Verde Sorvetes":{"bp": "Thais Andrade", "ij": "Marco Paixão", "mn": "Kelly Almeida"},
    "Duran Esquadrias":   {"bp": "Thais Andrade", "ij": "Marco Paixão", "mn": "Kelly Almeida"},

    # ── Kelly Almeida (MN sem BP GoAkira) ────────────────────────────────────
    "Sai de Moto":        {"bp": None,            "ij": None,           "mn": "Kelly Almeida"},
    "CTA":                {"bp": None,            "ij": None,           "mn": "Kelly Almeida"},
    "MedSempre":          {"bp": None,            "ij": None,           "mn": "Kelly Almeida"},
    "People Telecom":     {"bp": None,            "ij": None,           "mn": "Kelly Almeida"},
    "Tubarão do Açaí":    {"bp": None,            "ij": None,           "mn": "Kelly Almeida"},
    "Ipanema Papéis":     {"bp": None,            "ij": None,           "mn": "Kelly Almeida"},
    "Keystone":           {"bp": None,            "ij": None,           "mn": "Kelly Almeida"},
}


# ── Escopo já contratado (contexto p/ detecção de oportunidade comercial) ──────

# Nota livre por cliente sobre serviços já contratados/entregues que NÃO
# aparecem na estrutura BP/Jurídico/Manuais abaixo (ex: projeto pontual já
# fechado, serviço avulso já realizado). Preencher conforme cada falso
# positivo real for identificado nos alertas de "levantada de mão" — não
# precisa (nem faz sentido) preencher para todos os clientes de uma vez.
CLIENT_ESCOPO_EXTRA: dict[str, str] = {
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_consultant_email(nome: str) -> str | None:
    """Retorna o e-mail de um consultor pelo nome canônico."""
    c = CONSULTANTS.get(nome)
    return c["email"] if c else None


def get_bp_consultant(cliente: str) -> str | None:
    """
    Retorna o(s) nome(s) do(s) consultor(es) responsável(eis) pelo BP do cliente.
    Alguns clientes têm mais de um BP (projeto conjunto) — nesse caso retorna
    os nomes unidos por " & " para exibição.
    """
    c = CLIENT_CONSULTANTS.get(cliente, {})
    bp = c.get("bp")
    if isinstance(bp, list):
        return " & ".join(bp) if bp else None
    return bp


def get_bp_consultants(cliente: str) -> list[str]:
    """Retorna a lista de consultores responsáveis pelo BP do cliente (pode ter mais de um)."""
    c = CLIENT_CONSULTANTS.get(cliente, {})
    bp = c.get("bp")
    if isinstance(bp, list):
        return bp
    return [bp] if bp else []


def get_fase_reuniao(cliente: str, consultor: str | None) -> str:
    """
    Retorna a fase do projeto ("BP", "Jurídico" ou "Manuais") a que uma
    reunião pertence, comparando quem de fato a conduziu (consultor, pasta de
    origem no Drive) com os responsáveis de cada fase cadastrados para o
    cliente. Cai em "BP" por padrão quando não há correspondência (ex:
    consultor não informado, ou cliente com BP conjunto).
    """
    c = CLIENT_CONSULTANTS.get(cliente, {})
    if consultor:
        if consultor == c.get("ij"):
            return "Jurídico"
        if consultor == c.get("mn"):
            return "Manuais"
    return "BP"


def get_responsible_consultants(cliente: str, fase: str | None) -> list[str]:
    """
    Retorna o(s) consultor(es) responsável(eis) pela FASE da reunião (não
    sempre o BP) — usado para notificação de ata. Uma reunião de Jurídico
    ou Manuais deve notificar quem de fato conduz aquela fase, com o BP
    como fallback apenas quando a fase não tem consultor mapeado.
    """
    c = CLIENT_CONSULTANTS.get(cliente, {})
    if fase == "Jurídico":
        ij = c.get("ij")
        if ij:
            return [ij]
    elif fase == "Manuais":
        mn = c.get("mn")
        if mn:
            return [mn]
    return get_bp_consultants(cliente)


_ESCOPO_FORMATACAO_FRANQUIAS = (
    "Projeto completo de Formatação de Franquias contratado — inclui as 8 etapas fixas da "
    "metodologia (Kick Off, Business Plan do Franqueado, Viabilidade Econômica do Franqueado, "
    "Business Plan do Franqueador, Viabilidade Econômica do Franqueador, Estudo e Plano de "
    "Expansão — inclui geomarketing —, Instrumentos Jurídicos — COF/contrato —, e Processos e "
    "Manualização). Mesmo que a etapa específica ainda não tenha começado para este cliente, "
    "TODAS essas entregas (geomarketing, consultoria jurídica, manualização, consultoria "
    "financeira, funil comercial, pesquisa de mercado, treinamentos de onboarding/gestão) já "
    "são escopo contratado, não oportunidade nova."
)


def get_escopo_contratado(cliente: str) -> str:
    """
    Resume o que o cliente já tem contratado com a GoAkira, para dar contexto
    ao Claude na hora de detectar "oportunidades comerciais" (levantada de
    mão) — evita sinalizar como nova oportunidade um serviço que já está em
    andamento ou que já faz parte do pacote de Formatação de Franquias.
    Combina o que já sabemos estruturalmente (CLIENT_CONSULTANTS) com notas
    livres cadastradas em CLIENT_ESCOPO_EXTRA. Ver SERVICOS_GOAKIRA para a
    lista do que fica de fora desse pacote padrão (oportunidades genuínas).
    """
    c = CLIENT_CONSULTANTS.get(cliente, {})
    partes = []
    if c.get("bp"):
        partes.append(_ESCOPO_FORMATACAO_FRANQUIAS)
    if c.get("ij") and not c.get("bp"):
        partes.append("Consultoria Jurídica (Instrumentos Jurídicos) já contratada")
    if c.get("mn") and not c.get("bp"):
        partes.append("Manuais Operacionais já contratados")
    extra = CLIENT_ESCOPO_EXTRA.get(cliente)
    if extra:
        partes.append(extra)
    return " ".join(partes) if partes else "sem registro de escopo contratado"


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
