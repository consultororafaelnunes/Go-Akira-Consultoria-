"""
generate_pdf.py — Gera PDF executivo com os resumos do dia via ReportLab.
"""

import os
from datetime import date
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

# ── Paleta ────────────────────────────────────────────────────────────────────
NAVY      = colors.HexColor("#1E2761")
ICE_BLUE  = colors.HexColor("#CADCFC")
TEAL      = colors.HexColor("#0D9488")
CORAL     = colors.HexColor("#DC2626")
AMBER     = colors.HexColor("#D97706")
GRAY      = colors.HexColor("#64748B")
OFF_WHITE = colors.HexColor("#F7F9FF")

SENTIMENT_COLOR = {
    "positivo":    TEAL,
    "neutro":      AMBER,
    "preocupante": CORAL,
}


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Heading1"],
            fontSize=22, textColor=NAVY, spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"],
            fontSize=11, textColor=GRAY, spaceAfter=12,
        ),
        "section": ParagraphStyle(
            "section", parent=base["Heading2"],
            fontSize=13, textColor=NAVY, spaceBefore=14, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"],
            fontSize=10, textColor=colors.HexColor("#1E293B"), leading=14,
        ),
        "bullet": ParagraphStyle(
            "bullet", parent=base["Normal"],
            fontSize=10, textColor=colors.HexColor("#1E293B"),
            leftIndent=12, leading=13,
        ),
        "alert": ParagraphStyle(
            "alert", parent=base["Normal"],
            fontSize=10, textColor=CORAL, leftIndent=12, leading=13,
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["Normal"],
            fontSize=8, textColor=GRAY, alignment=1,
        ),
    }


def _get_consultor_pdf(cliente: str) -> str:
    try:
        from consultants import get_bp_consultant
        return get_bp_consultant(cliente) or "—"
    except Exception:
        return "—"


def _meeting_block(summary: dict, styles: dict) -> list:
    """Gera os flowables de um resumo de reunião."""
    s = styles
    elements = []

    cliente   = summary.get("cliente", "Não identificado")
    consultor = _get_consultor_pdf(cliente)
    titulo    = summary.get("titulo_reuniao", "—")
    data      = summary.get("data_reuniao", "—")
    duracao   = summary.get("duracao_estimada", "—")
    sent      = summary.get("sentimento", "neutro")
    prio      = summary.get("prioridade", "media")
    sent_cor  = SENTIMENT_COLOR.get(sent, AMBER)

    # Cabeçalho do card
    header_data = [[
        Paragraph(
            f"<b>{cliente}</b>  <font size='9' color='#CADCFC'>· {consultor}</font>",
            ParagraphStyle("h", fontSize=12, textColor=colors.white),
        ),
        Paragraph(f"{data}  ·  {duracao}", ParagraphStyle("h2", fontSize=9, textColor=ICE_BLUE, alignment=2)),
    ]]
    header_table = Table(header_data, colWidths=[11 * cm, 6 * cm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [4]),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 4))

    elements.append(Paragraph(titulo, s["section"]))

    # Badges sentimento / prioridade
    sent_hex = "#{:02X}{:02X}{:02X}".format(
        int(sent_cor.red * 255), int(sent_cor.green * 255), int(sent_cor.blue * 255)
    )
    badge = (
        f'<font color="{sent_hex}"><b>{sent.capitalize()}</b></font>'
        f'  ·  Prioridade: <b>{prio.capitalize()}</b>'
    )
    elements.append(Paragraph(badge, s["body"]))
    elements.append(Spacer(1, 6))

    # Resumo
    elements.append(Paragraph("<b>Resumo</b>", s["body"]))
    elements.append(Paragraph(summary.get("resumo", "—"), s["body"]))
    elements.append(Spacer(1, 6))

    # Participantes
    participantes = summary.get("participantes", [])
    if participantes:
        elements.append(Paragraph("<b>Participantes:</b> " + ", ".join(participantes), s["body"]))
        elements.append(Spacer(1, 6))

    # Acionáveis
    acionaveis = summary.get("acionaveis", [])
    if acionaveis:
        elements.append(Paragraph("<b>Acionáveis</b>", s["body"]))
        for a in acionaveis:
            elements.append(Paragraph(f"• {a}", s["bullet"]))
        elements.append(Spacer(1, 4))

    # Alertas
    alertas = summary.get("alertas", [])
    if alertas:
        elements.append(Paragraph("<b>⚠ Alertas</b>", ParagraphStyle(
            "alert_title", fontSize=10, textColor=CORAL, spaceBefore=4,
        )))
        for a in alertas:
            elements.append(Paragraph(f"• {a}", s["alert"]))
        elements.append(Spacer(1, 4))

    # Link da ata (se disponível)
    ata_link = summary.get("ata_link")
    if ata_link:
        elements.append(Paragraph(
            f'<a href="{ata_link}" color="#1E2761"><u>Ver ata no Google Docs →</u></a>', s["body"]
        ))

    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceAfter=10))
    return elements


def generate_pdf(summaries: list[dict]) -> bytes:
    """
    Gera o PDF executivo com todos os resumos do dia.
    Retorna os bytes do PDF.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=f"Resumo de Reuniões — {date.today().strftime('%d/%m/%Y')}",
        author="Agente de Resumo de Reuniões",
    )

    s = _styles()
    elements = []

    # Cabeçalho
    elements.append(Paragraph("Resumo de Reuniões", s["title"]))
    elements.append(Paragraph(
        f"{date.today().strftime('%d/%m/%Y')}  ·  {len(summaries)} reunião(ões)", s["subtitle"]
    ))
    elements.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=16))

    if not summaries:
        elements.append(Paragraph("Nenhuma reunião registrada hoje.", s["body"]))
    else:
        for summary in summaries:
            elements.extend(_meeting_block(summary, s))

    # Rodapé
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        "Gerado automaticamente · Agente de Resumo de Reuniões · Claude Haiku 4.5",
        s["footer"],
    ))

    doc.build(elements)
    return buf.getvalue()
