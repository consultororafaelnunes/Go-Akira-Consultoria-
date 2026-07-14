#!/usr/bin/env node
/**
 * generate_monthly_report.js
 *
 * Gera o relatório mensal em PPTX a partir dos resumos JSON do mês.
 * Chamado pelo Python via subprocess:
 *   node generate_monthly_report.js <summaries_json_path> <output_path> <mes_ano>
 *
 * Estrutura do deck:
 *   Slide 1  — Capa (título, mês, total de reuniões)
 *   Slide 2  — Visão geral (métricas agregadas + gráfico de sentimento)
 *   Slide 3  — Mapa de calor por cliente (frequência × sentimento)
 *   Slides N — 4 slides por cliente, um por semana do mês (dias 1–7, 8–14,
 *              15–21, 22+), sempre 4 mesmo em semanas sem reunião — mantém
 *              visível o ritmo de acompanhamento ao longo do mês
 *   Penúltimo — Alertas críticos do mês
 *   Último   — Próximos passos consolidados
 */

const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

// ── Paleta "Midnight Executive" adaptada ─────────────────────────────────────
const C = {
  navyDark:   "1A1F3C",
  navy:       "1E2761",
  navyMid:    "2D3A7A",
  iceBlue:    "CADCFC",
  icePale:    "EEF3FF",
  white:      "FFFFFF",
  offWhite:   "F7F9FF",
  teal:       "0D9488",
  tealLight:  "CCFBF1",
  amber:      "D97706",
  amberLight: "FEF3C7",
  coral:      "DC2626",
  coralLight: "FEE2E2",
  gray:       "64748B",
  grayLight:  "F1F5F9",
  grayMid:    "CBD5E1",
};

// Cores de sentimento
const SENTIMENT = {
  positivo:    { dot: C.teal,  bg: C.tealLight,  label: "Positivo"    },
  neutro:      { dot: C.amber, bg: C.amberLight, label: "Neutro"      },
  preocupante: { dot: C.coral, bg: C.coralLight, label: "Preocupante" },
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function truncate(str, max) {
  if (!str) return "—";
  return str.length > max ? str.slice(0, max - 1) + "…" : str;
}

// ── Estimativa de quebra de linha (evita depender do "encolher fonte" do
// PowerPoint, que o LibreOffice/Slides não recalculam da mesma forma) ──────────

function estimateLines(text, widthIn, fontSizePt, indentIn = 0) {
  const usableWidth = Math.max(0.5, widthIn - indentIn);
  const charsPerInch = 16 * (10 / fontSizePt); // calibrado a partir do render real (Calibri)
  const perLine = Math.max(8, Math.floor(usableWidth * charsPerInch));
  return Math.max(1, Math.ceil((text || "").length / perLine));
}

function lineHeightIn(fontSizePt, safety = 1.15) {
  return (fontSizePt * 1.2) / 72 * safety;
}

// Corta uma lista de itens (bullets) para o que cabe na altura disponível,
// sem nunca cortar no meio de uma frase — o que não cabe fica de fora,
// com um aviso "+N mais" opcional.
function fitItemsToHeight(items, availableHeightIn, widthIn, fontSizePt, indentIn = 0.25) {
  const lh = lineHeightIn(fontSizePt);
  const maxLines = Math.max(1, Math.floor(availableHeightIn / lh));
  let usedLines = 0;
  let count = 0;
  for (const item of items) {
    const lines = estimateLines(item, widthIn, fontSizePt, indentIn);
    if (count > 0 && usedLines + lines > maxLines) break;
    usedLines += lines;
    count++;
  }
  return Math.min(count, items.length);
}

// Corta um texto corrido (não itemizado) no limite de caracteres que cabe na
// caixa, sempre em fim de palavra — nunca no meio de uma frase.
function fitTextToBox(text, widthIn, heightIn, fontSizePt) {
  if (!text) return "—";
  const charsPerInch = 16 * (10 / fontSizePt);
  const perLine = Math.floor(widthIn * charsPerInch);
  const lines = Math.floor(heightIn / lineHeightIn(fontSizePt));
  const maxChars = Math.max(80, perLine * lines);
  if (text.length <= maxChars) return text;
  const cut = text.slice(0, maxChars);
  const lastSpace = cut.lastIndexOf(" ");
  return (lastSpace > maxChars * 0.7 ? cut.slice(0, lastSpace) : cut) + "…";
}

function groupByClient(summaries) {
  const map = {};
  for (const s of summaries) {
    const c = s.cliente || "Não identificado";
    if (!map[c]) map[c] = [];
    map[c].push(s);
  }
  return map;
}

// Faixas de dia-do-mês usadas para dividir as reuniões de um cliente em
// 4 "semanas" — não são semanas de calendário (seg-dom), mas quartos fixos
// do mês, para que todo cliente sempre gere exatamente 4 slides.
const WEEK_RANGES = [
  { label: "Semana 1 (dias 1–7)",   min: 1,  max: 7   },
  { label: "Semana 2 (dias 8–14)",  min: 8,  max: 14  },
  { label: "Semana 3 (dias 15–21)", min: 15, max: 21  },
  { label: "Semana 4 (dias 22+)",   min: 22, max: 99  },
];

function dayOfMonth(dataReuniao) {
  const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec((dataReuniao || "").trim());
  return m ? parseInt(m[1], 10) : null;
}

// Agrupa as reuniões de um cliente em 4 baldes fixos (uma semana cada),
// preservando a ordem cronológica dentro de cada balde.
function groupByWeek(meetings) {
  const buckets = WEEK_RANGES.map(() => []);
  for (const m of meetings) {
    const day = dayOfMonth(m.data_reuniao);
    const idx = day == null
      ? 3 // sem data interpretável — cai na última semana em vez de sumir
      : WEEK_RANGES.findIndex(r => day >= r.min && day <= r.max);
    buckets[idx === -1 ? 3 : idx].push(m);
  }
  return buckets;
}

function countSentiments(summaries) {
  const counts = { positivo: 0, neutro: 0, preocupante: 0 };
  for (const s of summaries) {
    const key = s.sentimento || "neutro";
    if (key in counts) counts[key]++;
  }
  return counts;
}

// ── Slide 1: Capa ─────────────────────────────────────────────────────────────

function addCoverSlide(pres, summaries, mesAno) {
  const slide = pres.addSlide();
  slide.background = { color: C.navyDark };

  const total     = summaries.length;
  const clientes  = Object.keys(groupByClient(summaries)).length;
  const sentCounts = countSentiments(summaries);
  const alerts    = summaries.filter(s => s.alertas && s.alertas.length > 0).length;

  // Título principal
  slide.addText("Relatório Mensal", {
    x: 0.7, y: 1.1, w: 8.6, h: 0.9,
    fontSize: 44, bold: true, color: C.white,
    fontFace: "Cambria", align: "left",
  });

  // Subtítulo — mês/ano
  slide.addText(mesAno.toUpperCase(), {
    x: 0.7, y: 2.05, w: 8.6, h: 0.5,
    fontSize: 18, bold: false, color: C.iceBlue,
    fontFace: "Calibri", align: "left", charSpacing: 4,
  });

  // Linha divisória
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 2.65, w: 8.6, h: 0.025,
    fill: { color: C.navyMid }, line: { color: C.navyMid },
  });

  // Métricas rápidas — 4 cards na base
  const metrics = [
    { label: "Reuniões",     value: String(total) },
    { label: "Clientes",     value: String(clientes) },
    { label: "Alertas",      value: String(alerts) },
    { label: "Positivas",    value: String(sentCounts.positivo) },
  ];

  metrics.forEach((m, i) => {
    const x = 0.7 + i * 2.2;
    // Card escuro
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 3.1, w: 2.0, h: 1.7,
      fill: { color: C.navyMid }, line: { color: C.navyMid },
      rectRadius: 0.1,
    });
    // Número grande
    slide.addText(m.value, {
      x, y: 3.2, w: 2.0, h: 0.85,
      fontSize: 42, bold: true, color: C.iceBlue,
      fontFace: "Cambria", align: "center", margin: 0,
    });
    // Label
    slide.addText(m.label, {
      x, y: 4.1, w: 2.0, h: 0.45,
      fontSize: 12, color: C.gray,
      fontFace: "Calibri", align: "center",
    });
  });

  // Rodapé
  slide.addText("Gerado automaticamente · Agente de Resumo de Reuniões", {
    x: 0.7, y: 5.25, w: 8.6, h: 0.25,
    fontSize: 9, color: C.gray, fontFace: "Calibri", align: "left",
  });
}

// ── Slide 2: Visão Geral ──────────────────────────────────────────────────────

function addOverviewSlide(pres, summaries) {
  const slide = pres.addSlide();
  slide.background = { color: C.offWhite };

  slide.addText("Visão Geral do Mês", {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28, bold: true, color: C.navy,
    fontFace: "Cambria", align: "left",
  });

  const sentCounts = countSentiments(summaries);
  const total = summaries.length || 1;
  const highPrio = summaries.filter(s => s.prioridade === "alta").length;
  const byClient = groupByClient(summaries);
  const clientCount = Object.keys(byClient).length;

  // Gráfico de sentimento (pizza nativa)
  slide.addChart(pres.charts.PIE, [{
    name: "Sentimento",
    labels: ["Positivo", "Neutro", "Preocupante"],
    values: [sentCounts.positivo, sentCounts.neutro, sentCounts.preocupante],
  }], {
    x: 0.5, y: 1.0, w: 4.5, h: 3.5,
    chartColors: [C.teal, C.amber, C.coral],
    showPercent: true,
    dataLabelColor: C.white,
    dataLabelFontSize: 13,
    chartArea: { fill: { color: C.offWhite } },
    showLegend: true, legendPos: "b",
    legendFontSize: 11, legendColor: C.gray,
    showTitle: true, title: "Distribuição de Sentimento",
    titleFontSize: 13, titleColor: C.navy,
  });

  // Cards de métricas à direita
  const stats = [
    { label: "Total de reuniões",          value: String(total)        },
    { label: "Clientes atendidos",          value: String(clientCount)  },
    { label: "Prioridade alta",             value: String(highPrio)     },
    { label: "Taxa positiva",               value: `${Math.round(sentCounts.positivo / total * 100)}%` },
  ];

  stats.forEach((st, i) => {
    const y = 1.0 + i * 0.85;
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 5.4, y, w: 4.0, h: 0.72,
      fill: { color: C.white },
      line: { color: C.grayMid, pt: 0.5 },
      rectRadius: 0.08,
      shadow: { type: "outer", color: "000000", blur: 4, offset: 1, angle: 45, opacity: 0.08 },
    });
    slide.addText(st.value, {
      x: 5.5, y: y + 0.04, w: 1.2, h: 0.62,
      fontSize: 28, bold: true, color: C.navy,
      fontFace: "Cambria", align: "center", margin: 0,
    });
    slide.addText(st.label, {
      x: 6.8, y: y + 0.18, w: 2.5, h: 0.36,
      fontSize: 13, color: C.gray,
      fontFace: "Calibri", align: "left",
    });
  });
}

// ── Slide 3: Mapa de clientes ─────────────────────────────────────────────────

function addClientMapSlide(pres, summaries) {
  const slide = pres.addSlide();
  slide.background = { color: C.offWhite };

  slide.addText("Resumo por Cliente", {
    x: 0.5, y: 0.28, w: 9, h: 0.55,
    fontSize: 26, bold: true, color: C.navy,
    fontFace: "Cambria",
  });

  const byClient = groupByClient(summaries);
  const entries = Object.entries(byClient);

  // Cabeçalho da tabela
  const headerRow = [
    { text: "Cliente",           options: { bold: true, color: C.white, fill: { color: C.navy }, fontSize: 11 } },
    { text: "Reuniões",          options: { bold: true, color: C.white, fill: { color: C.navy }, fontSize: 11 } },
    { text: "Último sentimento", options: { bold: true, color: C.white, fill: { color: C.navy }, fontSize: 11 } },
    { text: "Alertas",           options: { bold: true, color: C.white, fill: { color: C.navy }, fontSize: 11 } },
    { text: "Prioridade",        options: { bold: true, color: C.white, fill: { color: C.navy }, fontSize: 11 } },
  ];

  const rows = [headerRow];

  entries.slice(0, 12).forEach(([cliente, meetings]) => {
    const last   = meetings[meetings.length - 1];
    const sent   = last.sentimento || "neutro";
    const alerts = meetings.reduce((acc, m) => acc + (m.alertas || []).length, 0);
    const prio   = last.prioridade || "media";

    const sentColor = sent === "positivo" ? C.teal : sent === "preocupante" ? C.coral : C.amber;
    const prioColor = prio === "alta" ? C.coral : prio === "media" ? C.amber : C.teal;

    rows.push([
      { text: truncate(cliente, 28),   options: { fontSize: 10, color: C.navyDark } },
      { text: String(meetings.length), options: { fontSize: 10, color: C.navyDark, align: "center" } },
      { text: sent.charAt(0).toUpperCase() + sent.slice(1), options: { fontSize: 10, color: sentColor, bold: true, align: "center" } },
      { text: alerts > 0 ? `⚠️ ${alerts}` : "—", options: { fontSize: 10, color: alerts > 0 ? C.coral : C.gray, align: "center" } },
      { text: prio.charAt(0).toUpperCase() + prio.slice(1), options: { fontSize: 10, color: prioColor, bold: prio === "alta", align: "center" } },
    ]);
  });

  slide.addTable(rows, {
    x: 0.5, y: 0.95, w: 9.0,
    colW: [3.2, 1.2, 2.0, 1.3, 1.3],
    border: { pt: 0.5, color: C.grayMid },
    rowH: 0.36,
    autoPage: false,
  });
}

// ── Slides por cliente ────────────────────────────────────────────────────────

// Um slide por semana (sempre 4 por cliente) — quando a semana não teve
// reunião, mostra um estado vazio consistente em vez de omitir o slide,
// para que o ritmo de acompanhamento do mês fique visível de ponta a ponta.
function addClientWeekSlide(pres, cliente, weekLabel, meetings) {
  const slide = pres.addSlide();
  slide.background = { color: C.offWhite };

  const hasMeetings = meetings.length > 0;
  const last        = hasMeetings ? meetings[meetings.length - 1] : null;
  const sent        = hasMeetings ? (last.sentimento || "neutro") : null;
  const sentInfo     = sent ? (SENTIMENT[sent] || SENTIMENT.neutro) : null;
  const allActions  = meetings.flatMap(m => m.acionaveis || []);
  const allAlerts   = meetings.flatMap(m => m.alertas  || []);

  // Resumo consolidado: uma entrada por reunião da semana, com a data à frente
  // quando há mais de uma reunião no mesmo balde.
  const resumoConsolidado = meetings
    .map(m => (meetings.length > 1 ? `[${m.data_reuniao}] ${m.resumo}` : m.resumo))
    .join("\n\n");

  // Cabeçalho com fundo navy
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 1.2,
    fill: { color: C.navy }, line: { color: C.navy },
  });
  slide.addText(truncate(cliente, 42), {
    x: 0.5, y: 0.1, w: 8.0, h: 0.5,
    fontSize: 24, bold: true, color: C.white,
    fontFace: "Cambria", align: "left", margin: 0,
  });
  slide.addText(
    hasMeetings
      ? `${weekLabel}  ·  ${meetings.length} reunião(ões)  ·  Sentimento: ${sentInfo.label}`
      : `${weekLabel}  ·  Sem reunião registrada`,
    {
      x: 0.5, y: 0.72, w: 9.0, h: 0.3,
      fontSize: 12, color: C.iceBlue,
      fontFace: "Calibri", align: "left",
    }
  );

  if (!hasMeetings) {
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 0.4, y: 1.35, w: 9.15, h: 3.9,
      fill: { color: C.white }, line: { color: C.grayMid, pt: 0.5 },
      rectRadius: 0.1,
      shadow: { type: "outer", color: "000000", blur: 5, offset: 2, angle: 45, opacity: 0.08 },
    });
    slide.addText("Sem reunião registrada nesta semana.", {
      x: 0.4, y: 1.35, w: 9.15, h: 3.9,
      fontSize: 13, color: C.gray, italic: true,
      fontFace: "Calibri", align: "center", valign: "middle",
    });
    return;
  }

  // ── Coluna esquerda: Resumo ──
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.4, y: 1.35, w: 4.2, h: 3.9,
    fill: { color: C.white }, line: { color: C.grayMid, pt: 0.5 },
    rectRadius: 0.1,
    shadow: { type: "outer", color: "000000", blur: 5, offset: 2, angle: 45, opacity: 0.08 },
  });
  slide.addText("RESUMO DA SEMANA", {
    x: 0.55, y: 1.5, w: 3.9, h: 0.3,
    fontSize: 10, bold: true, color: C.navy,
    fontFace: "Calibri", charSpacing: 2,
  });
  slide.addText(fitTextToBox(resumoConsolidado, 3.9, 3.3, 11), {
    x: 0.55, y: 1.85, w: 3.9, h: 3.3,
    fontSize: 11, color: C.navyDark,
    fontFace: "Calibri", align: "left", valign: "top",
  });

  // ── Coluna direita: Acionáveis + Alertas ──
  // Card acionáveis
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 4.85, y: 1.35, w: 4.7, h: 2.5,
    fill: { color: C.white }, line: { color: C.grayMid, pt: 0.5 },
    rectRadius: 0.1,
    shadow: { type: "outer", color: "000000", blur: 5, offset: 2, angle: 45, opacity: 0.08 },
  });
  slide.addText("ACIONÁVEIS DA SEMANA", {
    x: 5.0, y: 1.48, w: 4.4, h: 0.3,
    fontSize: 10, bold: true, color: C.navy,
    fontFace: "Calibri", charSpacing: 2,
  });
  const actionFontSize = 10;
  const actionBoxH = 1.75; // deixa 0.15 de folga antes do rodapé do card
  const actionFit = fitItemsToHeight(allActions, actionBoxH, 4.4, actionFontSize);
  const actionsShown = allActions.slice(0, actionFit);
  const actionItems = actionsShown.map((a, i) => ({
    text: a,
    options: { bullet: true, breakLine: i < actionsShown.length - 1, fontSize: actionFontSize, color: C.navyDark },
  }));
  if (actionItems.length === 0) actionItems.push({ text: "Nenhuma ação registrada", options: { fontSize: actionFontSize, color: C.gray } });
  slide.addText(actionItems, {
    x: 5.0, y: 1.85, w: 4.4, h: actionBoxH,
    fontFace: "Calibri", valign: "top",
  });
  if (allActions.length > actionFit) {
    slide.addText(`+ ${allActions.length - actionFit} ação(ões) adicional(is) — ver ata completa`, {
      x: 5.0, y: 1.85 + actionBoxH, w: 4.4, h: 0.2,
      fontSize: 8, italic: true, color: C.gray, fontFace: "Calibri",
    });
  }

  // Card alertas
  const alertBg = allAlerts.length > 0 ? C.coralLight : C.white;
  const alertBorder = allAlerts.length > 0 ? C.coral : C.grayMid;
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 4.85, y: 3.95, w: 4.7, h: 1.3,
    fill: { color: alertBg }, line: { color: alertBorder, pt: 0.5 },
    rectRadius: 0.1,
    shadow: { type: "outer", color: "000000", blur: 5, offset: 2, angle: 45, opacity: 0.08 },
  });
  slide.addText(allAlerts.length > 0 ? "⚠️ ALERTAS E RISCOS" : "ALERTAS E RISCOS", {
    x: 5.0, y: 4.08, w: 4.4, h: 0.3,
    fontSize: 10, bold: true,
    color: allAlerts.length > 0 ? C.coral : C.navy,
    fontFace: "Calibri", charSpacing: 2,
  });
  const alertFontSize = 9;
  const alertBoxH = 0.85;
  const alertFit = fitItemsToHeight(allAlerts, alertBoxH, 4.4, alertFontSize);
  const alertsShown = allAlerts.slice(0, alertFit);
  const alertItems = alertsShown.map((a, i) => ({
    text: a,
    options: { bullet: true, breakLine: i < alertsShown.length - 1, fontSize: alertFontSize, color: C.coral },
  }));
  if (alertItems.length === 0) alertItems.push({ text: "Nenhum alerta registrado na semana", options: { fontSize: alertFontSize, color: C.teal } });
  slide.addText(alertItems, {
    x: 5.0, y: 4.4, w: 4.4, h: alertBoxH,
    fontFace: "Calibri", valign: "top",
  });
  if (allAlerts.length > alertFit) {
    slide.addText(`+ ${allAlerts.length - alertFit} alerta(s) adicional(is) — ver ata completa`, {
      x: 5.0, y: 4.4 + alertBoxH - 0.02, w: 4.4, h: 0.18,
      fontSize: 7, italic: true, color: C.gray, fontFace: "Calibri",
    });
  }
}

// Gera os 4 slides semanais de um cliente.
function addClientSlides(pres, cliente, meetings) {
  const weeks = groupByWeek(meetings);
  weeks.forEach((weekMeetings, i) => {
    addClientWeekSlide(pres, cliente, WEEK_RANGES[i].label, weekMeetings);
  });
}

// ── Slide de Alertas Críticos ─────────────────────────────────────────────────

function addCriticalAlertsSlide(pres, summaries) {
  const critical = summaries.filter(s => s.prioridade === "alta" && s.alertas && s.alertas.length > 0);
  if (critical.length === 0) return;

  const slide = pres.addSlide();
  slide.background = { color: C.navyDark };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 1.15,
    fill: { color: C.coral }, line: { color: C.coral },
  });
  slide.addText("⚠️  Alertas Críticos do Mês", {
    x: 0.5, y: 0.2, w: 9, h: 0.7,
    fontSize: 28, bold: true, color: C.white,
    fontFace: "Cambria",
  });

  // Cards de alerta
  const maxPerRow = 2;
  const cardW = 4.4;
  const cardH = 1.6;

  critical.slice(0, 6).forEach((s, i) => {
    const col = i % maxPerRow;
    const row = Math.floor(i / maxPerRow);
    const x = 0.45 + col * (cardW + 0.35);
    const y = 1.35 + row * (cardH + 0.2);

    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y, w: cardW, h: cardH,
      fill: { color: "2A0A0A" }, line: { color: C.coral, pt: 1 },
      rectRadius: 0.1,
    });
    slide.addText(truncate(s.cliente, 32), {
      x: x + 0.15, y: y + 0.1, w: cardW - 0.3, h: 0.35,
      fontSize: 13, bold: true, color: C.iceBlue,
      fontFace: "Cambria",
    });
    const alertText = (s.alertas || []).slice(0, 2).map((a, ai) => ({
      text: truncate(a, 55),
      options: { bullet: true, breakLine: ai === 0 && s.alertas.length > 1, fontSize: 10, color: C.coralLight },
    }));
    slide.addText(alertText, {
      x: x + 0.15, y: y + 0.5, w: cardW - 0.3, h: 0.95,
      fontFace: "Calibri", valign: "top",
    });
  });
}

// ── Slide de Próximos Passos ──────────────────────────────────────────────────

function addNextStepsSlide(pres, summaries) {
  const slide = pres.addSlide();
  slide.background = { color: C.navy };

  slide.addText("Próximos Passos Consolidados", {
    x: 0.5, y: 0.3, w: 9, h: 0.7,
    fontSize: 30, bold: true, color: C.white,
    fontFace: "Cambria",
  });

  const allNext = summaries.flatMap(s =>
    (s.proximos_passos || []).slice(0, 2).map(p => ({ cliente: s.cliente, passo: p }))
  );

  // Tabela de próximos passos
  const headerRow = [
    { text: "Cliente",       options: { bold: true, color: C.navy,  fill: { color: C.iceBlue }, fontSize: 11 } },
    { text: "Próximo passo", options: { bold: true, color: C.navy,  fill: { color: C.iceBlue }, fontSize: 11 } },
  ];

  const rows = [headerRow, ...allNext.slice(0, 14).map((item, i) => [
    { text: truncate(item.cliente, 24), options: { fontSize: 10, color: C.iceBlue, valign: "top" } },
    { text: item.passo,                 options: { fontSize: 10, color: C.white, valign: "top" } },
  ])];

  if (rows.length === 1) {
    rows.push([
      { text: "—", options: { fontSize: 10, color: C.gray } },
      { text: "Nenhum próximo passo registrado", options: { fontSize: 10, color: C.gray } },
    ]);
  }

  // Limita a tabela a 8 linhas de dados (texto completo, sem corte, pode quebrar em 2 linhas)
  // para não colidir com o rodapé.
  const visibleRows = [headerRow, ...rows.slice(1, 9)];
  const hasMore = rows.length > 9;

  slide.addTable(visibleRows, {
    x: 0.5, y: 1.15, w: 9.0,
    colW: [2.0, 7.0],
    border: { pt: 0.5, color: C.navyMid },
    rowH: 0.36,
    autoPage: false,
    fill: { color: C.navyMid },
  });

  if (hasMore) {
    slide.addText(`+ ${rows.length - 9} passos adicionais — ver PDF diário para lista completa`, {
      x: 0.5, y: 5.05, w: 9, h: 0.22,
      fontSize: 9, color: C.gray, fontFace: "Calibri", align: "left", italic: true,
    });
  }

  // Rodapé
  slide.addText("Relatório gerado automaticamente · Agente de Resumo de Reuniões", {
    x: 0.5, y: 5.3, w: 9, h: 0.2,
    fontSize: 9, color: C.gray, fontFace: "Calibri", align: "center",
  });
}

// ── Main ──────────────────────────────────────────────────────────────────────

async function main() {
  const [,, jsonPath, outputPath, mesAno] = process.argv;

  if (!jsonPath || !outputPath) {
    console.error("Uso: node generate_monthly_report.js <summaries.json> <output.pptx> <Junho 2025>");
    process.exit(1);
  }

  const raw       = fs.readFileSync(jsonPath, "utf-8");
  const summaries = JSON.parse(raw);
  const label     = mesAno || "Mês";

  console.log(`📊 Gerando relatório mensal: ${label} — ${summaries.length} reunião(ões)`);

  const pres      = new pptxgen();
  pres.layout     = "LAYOUT_16x9";
  pres.title      = `Relatório Mensal — ${label}`;
  pres.author     = "Agente de Resumo de Reuniões";
  pres.subject    = "Relatório Executivo Mensal";

  // Slide 1: Capa
  addCoverSlide(pres, summaries, label);

  // Slide 2: Visão geral
  addOverviewSlide(pres, summaries);

  // Slide 3: Mapa de clientes
  addClientMapSlide(pres, summaries);

  // Slides por cliente (4 por cliente — uma por semana do mês)
  const byClient = groupByClient(summaries);
  for (const [cliente, meetings] of Object.entries(byClient)) {
    addClientSlides(pres, cliente, meetings);
  }

  // Slide de alertas críticos
  addCriticalAlertsSlide(pres, summaries);

  // Slide de próximos passos
  addNextStepsSlide(pres, summaries);

  await pres.writeFile({ fileName: outputPath });
  console.log(`✅ PPTX salvo em: ${outputPath}`);
}

main().catch(err => {
  console.error("Erro ao gerar PPTX:", err);
  process.exit(1);
});
