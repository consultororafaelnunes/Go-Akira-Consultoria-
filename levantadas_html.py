"""
levantadas_html.py — Renderização HTML compartilhada dos blocos de "levantada
de mão": timeline (etapa + prazo em dias úteis) e de-para (escopo contratado).

Usado tanto pelo push diário (send_email._opportunity_context_html) quanto pelo
relatório semanal (weekly_levantadas), para que os dois blocos permaneçam
visualmente coerentes e — importante — apliquem o mesmo escaping de HTML. Os
valores de contrato/timeline vêm de extração em texto livre de PDFs, então
qualquer '&', '<', '>' ou aspas precisa ser escapado antes de entrar no HTML.

Todos os renderizadores são tolerantes a dict incompleto (usam .get), de forma
que uma timeline/contrato de fallback nunca quebra o envio.
"""

# Paleta GoAkira
NAVY = "#1E2761"
ICE = "#CADCFC"
TEAL = "#0D9488"
AMBER = "#D97706"
SLATE = "#64748B"
GREEN = "#059669"
RED = "#DC2626"


def esc(t) -> str:
    """Escapa texto para conteúdo HTML (&, <, >)."""
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def esc_attr(t) -> str:
    """Escapa um valor para uso dentro de um atributo HTML entre aspas simples."""
    return esc(t).replace("'", "&#39;").replace('"', "&quot;")


def fmt_date(d) -> str:
    return d.strftime("%d/%m/%Y") if d else "—"


def render_timeline(tl: dict, *, margin: str = "10px 0 0", show_progress: bool = True) -> str:
    """
    Bloco visual da etapa + prazo do projeto (dias úteis contratados/decorridos/
    restantes). `margin` controla a margem externa do card; `show_progress` liga
    a barra de progresso (usada no relatório semanal, omitida no push diário).
    """
    etapa = esc(tl.get("etapa") or "—")

    barra = ""
    if show_progress:
        pct = tl.get("progresso_pct")
        if pct is not None:
            cor = RED if tl.get("atrasado") else TEAL
            barra = (
                f"<div style='margin-top:8px;background:#E2E8F0;border-radius:6px;height:8px;overflow:hidden'>"
                f"<div style='width:{min(100, pct)}%;background:{cor};height:8px'></div></div>"
            )

    if tl.get("tem_prazo") and tl.get("tem_kickoff"):
        if tl.get("atrasado"):
            prazo_txt = (f"<b style='color:{RED}'>prazo estourado</b> — previsão era "
                         f"{fmt_date(tl.get('previsao_fim'))}")
        else:
            prazo_txt = (f"<b style='color:{NAVY}'>{tl.get('dias_uteis_restantes')} dia(s) útil(eis) "
                         f"restante(s)</b> · previsão de término {fmt_date(tl.get('previsao_fim'))}")
        fonte = tl.get("dias_uteis_fonte") or ""
        fonte_hint = (f" <span style='color:{SLATE}'>({esc(fonte)})</span>"
                      if "soma" in fonte.lower() else "")
        detalhe = (
            f"Kick Off {fmt_date(tl.get('kickoff'))} · "
            f"{tl.get('dias_uteis_total')} dias úteis contratados{fonte_hint} · "
            f"{tl.get('dias_uteis_decorridos')} decorridos<br>{prazo_txt}"
        )
    else:
        obs = esc(tl.get("obs") or "prazo/kick off não localizados")
        detalhe = f"<span style='color:{AMBER}'>⚠️ {obs}</span>"

    return (
        f"<div style='margin:{margin};background:#F8FAFC;border:1px solid #E2E8F0;"
        f"border-radius:6px;padding:10px 12px'>"
        f"<div style='font-size:11px;color:{SLATE};text-transform:uppercase;letter-spacing:.4px'>Etapa do projeto</div>"
        f"<div style='font-size:14px;font-weight:700;color:{NAVY};margin:2px 0'>{etapa}</div>"
        f"<div style='font-size:12px;color:#475569;line-height:1.5'>{detalhe}</div>"
        f"{barra}</div>"
    )


def render_escopo(contrato: dict, *, margin: str = "10px 0 0", fallback_suffix: str = "") -> str:
    """
    Lado 'escopo contratado' do de-para. `fallback_suffix` é um texto opcional
    (já escapado/estático) acrescentado à mensagem de contrato não localizado.
    """
    if not contrato.get("encontrado"):
        motivo = esc(contrato.get("motivo") or "contrato não localizado")
        return (
            f"<div style='margin:{margin};font-size:12px;color:{SLATE}'>"
            f"<b style='color:{NAVY}'>Escopo contratado:</b> "
            f"<span style='color:{AMBER}'>⚠️ {motivo}</span>{fallback_suffix}</div>"
        )

    servicos = contrato.get("servicos_contratados") or []
    if servicos:
        chips = "".join(
            f"<span style='display:inline-block;background:#ECFDF5;color:{GREEN};"
            f"font-size:11px;font-weight:600;padding:2px 9px;border-radius:12px;margin:3px 4px 0 0'>"
            f"✅ {esc(s)}</span>"
            for s in servicos
        )
        corpo = f"<div style='margin-top:4px'>{chips}</div>"
    else:
        corpo = (f"<p style='margin:4px 0 0;font-size:12px;color:#475569;line-height:1.45'>"
                 f"{esc(contrato.get('escopo_contratado') or '—')}</p>")

    link = contrato.get("contrato_link") or ""
    link_html = (f" <a href='{esc_attr(link)}' style='font-size:11px;color:{TEAL};text-decoration:none;"
                 f"font-weight:700'>📄 contrato →</a>" if link else "")
    return (
        f"<div style='margin:{margin}'>"
        f"<span style='font-size:12px;font-weight:700;color:{NAVY}'>Escopo contratado</span>{link_html}"
        f"{corpo}</div>"
    )
