#!/usr/bin/env node
/**
 * generate_visibilidade_pptx.js
 *
 * Gera o Resumo PPTX executivo de um Documento de Visibilidade, expandindo a
 * estrutura original de 4 slides definida em
 * docs/superpowers/specs/2026-07-08-planejamento-agentes-goakira-design.md
 * com 2 slides extras para deixar custo e discovery mais explícitos:
 *   1. Capa — nome do agente, área solicitante, data
 *   2. Veredito — cards com risco geral, custo (resumo), prazo, recomendação
 *   3. Riscos principais — 2-3 riscos de maior severidade, com justificativa + mitigação
 *   4. Detalhamento de custos — item a item, com observações
 *   5. O que pesquisar no discovery — agrupado por categoria (jurídico, segurança, técnico, financeiro)
 *   6. Próximos passos — sequência recomendada
 *
 * Uso:
 *   node generate_visibilidade_pptx.js <avaliacao.json> <output.pptx>
 *
 * Formato do JSON de entrada: ver docs/planejamento-agentes/avaliacoes/*.json
 */

const pptxgen = require("pptxgenjs");
const fs = require("fs");

// ── Paleta "Midnight Executive" (mesma do relatório mensal) ──────────────────
const C = {
  navyDark:   "1A1F3C",
  navy:       "1E2761",
  navyMid:    "2D3A7A",
  iceBlue:    "CADCFC",
  offWhite:   "F7F9FF",
  white:      "FFFFFF",
  teal:       "0D9488",
  tealLight:  "CCFBF1",
  amber:      "D97706",
  amberLight: "FEF3C7",
  coral:      "DC2626",
  coralLight: "FEE2E2",
  gray:       "64748B",
  grayMid:    "CBD5E1",
};

const RISK_COLOR = { baixo: C.teal, médio: C.amber, medio: C.amber, alto: C.coral };

function riskColor(nivel) {
  return RISK_COLOR[(nivel || "").toLowerCase()] || C.gray;
}

// ── Slide 1: Capa ─────────────────────────────────────────────────────────────

function addCoverSlide(pres, d) {
  const slide = pres.addSlide();
  slide.background = { color: C.navyDark };

  slide.addText("Documento de Visibilidade", {
    x: 0.7, y: 1.5, w: 8.6, h: 0.5,
    fontSize: 16, color: C.iceBlue, fontFace: "Calibri", charSpacing: 3,
  });
  slide.addText(d.agente, {
    x: 0.7, y: 2.0, w: 8.6, h: 1.3,
    fontSize: 38, bold: true, color: C.white, fontFace: "Cambria",
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 3.35, w: 8.6, h: 0.025,
    fill: { color: C.navyMid }, line: { color: C.navyMid },
  });
  slide.addText(`Área solicitante: ${d.area}`, {
    x: 0.7, y: 3.55, w: 8.6, h: 0.35,
    fontSize: 14, color: C.iceBlue, fontFace: "Calibri",
  });
  slide.addText(`Avaliado em: ${d.data}`, {
    x: 0.7, y: 3.9, w: 8.6, h: 0.35,
    fontSize: 14, color: C.gray, fontFace: "Calibri",
  });
  slide.addText("Gerado automaticamente · Processo de Planejamento de Agentes GoAkira", {
    x: 0.7, y: 5.25, w: 8.6, h: 0.25,
    fontSize: 9, color: C.gray, fontFace: "Calibri",
  });
}

// ── Slide 2: Veredito ─────────────────────────────────────────────────────────

function addVerdictSlide(pres, d) {
  const slide = pres.addSlide();
  slide.background = { color: C.offWhite };

  slide.addText("Veredito e Estimativas", {
    x: 0.5, y: 0.35, w: 9, h: 0.6,
    fontSize: 28, bold: true, color: C.navy, fontFace: "Cambria",
  });

  const risk = riskColor(d.risco_geral);
  const cards = [
    { label: "RISCO GERAL",   value: (d.risco_geral || "—").toUpperCase(), color: risk },
    { label: "CUSTO ESTIMADO",value: "Ver detalhamento →", color: C.navy, small: true },
    { label: "PRAZO ESTIMADO",value: d.prazo_estimado, color: C.navy, small: true },
  ];

  cards.forEach((card, i) => {
    const x = 0.5 + i * 3.05;
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 1.15, w: 2.85, h: 1.9,
      fill: { color: C.white }, line: { color: C.grayMid, pt: 0.5 },
      rectRadius: 0.1,
      shadow: { type: "outer", color: "000000", blur: 5, offset: 2, angle: 45, opacity: 0.08 },
    });
    slide.addText(card.label, {
      x: x + 0.15, y: 1.3, w: 2.55, h: 0.3,
      fontSize: 10, bold: true, color: C.gray, fontFace: "Calibri", charSpacing: 1,
    });
    slide.addText(card.value, {
      x: x + 0.15, y: 1.65, w: 2.55, h: 1.3,
      fontSize: card.small ? 13 : 30, bold: true, color: card.color,
      fontFace: card.small ? "Calibri" : "Cambria",
      valign: "top",
    });
  });

  // Card de recomendação, largura total
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 3.25, w: 9.0, h: 1.8,
    fill: { color: C.navy }, line: { color: C.navy },
    rectRadius: 0.1,
  });
  slide.addText("RECOMENDAÇÃO", {
    x: 0.75, y: 3.45, w: 8.5, h: 0.3,
    fontSize: 11, bold: true, color: C.iceBlue, fontFace: "Calibri", charSpacing: 2,
  });
  slide.addText(d.veredito, {
    x: 0.75, y: 3.8, w: 8.5, h: 1.1,
    fontSize: 22, bold: true, color: C.white, fontFace: "Cambria", valign: "top",
  });
}

// ── Slide 3: Riscos principais ────────────────────────────────────────────────

function addRisksSlide(pres, d) {
  const slide = pres.addSlide();
  slide.background = { color: C.offWhite };

  slide.addText("Riscos Principais", {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28, bold: true, color: C.navy, fontFace: "Cambria",
  });

  const riscos = (d.riscos_principais || []).slice(0, 3);
  const cardH = 1.62;
  const gap = 0.1;

  riscos.forEach((r, i) => {
    const y = 1.0 + i * (cardH + gap);
    const color = riskColor(r.veredito);

    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 0.5, y, w: 9.0, h: cardH,
      fill: { color: C.white }, line: { color: color, pt: 1 },
      rectRadius: 0.08,
      shadow: { type: "outer", color: "000000", blur: 5, offset: 2, angle: 45, opacity: 0.08 },
    });
    // Faixa lateral colorida
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 0.12, h: cardH,
      fill: { color }, line: { color },
    });
    slide.addText(r.nome, {
      x: 0.8, y: y + 0.08, w: 6.0, h: 0.3,
      fontSize: 14, bold: true, color: C.navy, fontFace: "Cambria",
    });
    slide.addText((r.veredito || "—").toUpperCase(), {
      x: 7.0, y: y + 0.08, w: 2.3, h: 0.3,
      fontSize: 11, bold: true, color, fontFace: "Calibri", align: "right",
    });
    slide.addText([
      { text: "Por quê: ", options: { bold: true, color: C.navy } },
      { text: (r.justificativa || "—") + "\n", options: { color: C.gray } },
      { text: "Mitigação: ", options: { bold: true, color: C.navy } },
      { text: r.mitigacao || "—", options: { color: C.gray } },
    ], {
      x: 0.8, y: y + 0.4, w: 8.5, h: cardH - 0.48,
      fontSize: 9.5, fontFace: "Calibri", valign: "top", lineSpacingMultiple: 1.05,
    });
  });

  if (!riscos.length) {
    slide.addText("Nenhum risco de severidade alta/média identificado.", {
      x: 0.5, y: 2.5, w: 9, h: 0.5,
      fontSize: 14, italic: true, color: C.gray, fontFace: "Calibri", align: "center",
    });
  }
}

// ── Slide 4: Detalhamento de Custos ───────────────────────────────────────────

function addCostsSlide(pres, d) {
  const slide = pres.addSlide();
  slide.background = { color: C.offWhite };

  slide.addText("Detalhamento de Custos", {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 28, bold: true, color: C.navy, fontFace: "Cambria",
  });

  const custos = d.custos || [];
  const headerRow = [
    { text: "Item",       options: { bold: true, color: C.white, fill: { color: C.navy }, fontSize: 11 } },
    { text: "Valor",      options: { bold: true, color: C.white, fill: { color: C.navy }, fontSize: 11 } },
    { text: "Observação", options: { bold: true, color: C.white, fill: { color: C.navy }, fontSize: 11 } },
  ];
  const rows = [headerRow, ...custos.map(c => ([
    { text: c.item,  options: { fontSize: 11, color: C.navyDark || C.navy, bold: true, valign: "top" } },
    { text: c.valor, options: { fontSize: 11, color: C.navy, valign: "top" } },
    { text: c.obs,   options: { fontSize: 10, color: C.gray, valign: "top" } },
  ]))];

  slide.addTable(rows, {
    x: 0.5, y: 1.05, w: 9.0,
    colW: [2.4, 1.8, 4.8],
    border: { pt: 0.5, color: C.grayMid },
    autoPage: false,
    valign: "top",
  });

  slide.addText("Estimativas — a confirmar após discovery técnico/jurídico (ver checklist).", {
    x: 0.5, y: 5.15, w: 9, h: 0.3,
    fontSize: 9, italic: true, color: C.gray, fontFace: "Calibri",
  });
}

// ── Slide 5: O que pesquisar no discovery ─────────────────────────────────────

function addDiscoverySlide(pres, d) {
  const slide = pres.addSlide();
  slide.background = { color: C.navy };

  slide.addText("O Que Pesquisar no Discovery", {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 26, bold: true, color: C.white, fontFace: "Cambria",
  });

  const grupos = d.discovery || [];
  const colW = 4.4;
  const gapX = 0.2;

  grupos.slice(0, 4).forEach((g, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.5 + col * (colW + gapX);
    const y = 1.0 + row * 2.15;

    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y, w: colW, h: 2.0,
      fill: { color: C.navyMid }, line: { color: C.navyMid },
      rectRadius: 0.08,
    });
    slide.addText(g.categoria.toUpperCase(), {
      x: x + 0.2, y: y + 0.12, w: colW - 0.4, h: 0.3,
      fontSize: 11, bold: true, color: C.iceBlue, fontFace: "Calibri", charSpacing: 1,
    });
    const itens = (g.itens || []).map((item, ii) => ({
      text: item,
      options: { bullet: { code: "2022" }, breakLine: ii < g.itens.length - 1, fontSize: 10, color: C.white },
    }));
    slide.addText(itens, {
      x: x + 0.2, y: y + 0.48, w: colW - 0.4, h: 1.42,
      fontFace: "Calibri", valign: "top", lineSpacingMultiple: 1.15,
    });
  });

  slide.addText("Gerado automaticamente · Processo de Planejamento de Agentes GoAkira", {
    x: 0.5, y: 5.3, w: 9, h: 0.2,
    fontSize: 9, color: C.gray, fontFace: "Calibri", align: "center",
  });
}

// ── Slide 6: Próximos passos ───────────────────────────────────────────────────

function addNextStepsSlide(pres, d) {
  const slide = pres.addSlide();
  slide.background = { color: C.navy };

  slide.addText("Decisões Pendentes e Próximos Passos", {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 26, bold: true, color: C.white, fontFace: "Cambria",
  });

  // Sequência recomendada (numerados) — decisões pendentes já ficaram
  // detalhadas por categoria no slide de discovery anterior.
  slide.addText("SEQUÊNCIA RECOMENDADA", {
    x: 0.5, y: 1.1, w: 9.0, h: 0.3,
    fontSize: 12, bold: true, color: C.iceBlue, fontFace: "Calibri", charSpacing: 1,
  });
  const passos = (d.proximos_passos || []).map((item, i) => ({
    text: `${i + 1}. ${item}`,
    options: { breakLine: true, fontSize: 15, color: C.white },
  }));
  slide.addText(passos.length ? passos : [{ text: "—", options: { color: C.gray } }], {
    x: 0.5, y: 1.55, w: 9.0, h: 3.8,
    fontFace: "Calibri", valign: "top", lineSpacingMultiple: 1.6,
  });

  slide.addText("Gerado automaticamente · Processo de Planejamento de Agentes GoAkira", {
    x: 0.5, y: 5.3, w: 9, h: 0.2,
    fontSize: 9, color: C.gray, fontFace: "Calibri", align: "center",
  });
}

// ── Main ──────────────────────────────────────────────────────────────────────

async function main() {
  const [,, jsonPath, outputPath] = process.argv;

  if (!jsonPath || !outputPath) {
    console.error("Uso: node generate_visibilidade_pptx.js <avaliacao.json> <output.pptx>");
    process.exit(1);
  }

  const d = JSON.parse(fs.readFileSync(jsonPath, "utf-8"));

  console.log(`📊 Gerando resumo executivo: ${d.agente}`);

  const pres   = new pptxgen();
  pres.layout  = "LAYOUT_16x9";
  pres.title   = `Documento de Visibilidade — ${d.agente}`;
  pres.author  = "Processo de Planejamento de Agentes GoAkira";
  pres.subject = "Resumo Executivo";

  addCoverSlide(pres, d);
  addVerdictSlide(pres, d);
  addRisksSlide(pres, d);
  addCostsSlide(pres, d);
  addDiscoverySlide(pres, d);
  addNextStepsSlide(pres, d);

  await pres.writeFile({ fileName: outputPath });
  console.log(`✅ PPTX salvo em: ${outputPath}`);
}

main().catch(err => {
  console.error("Erro ao gerar PPTX:", err);
  process.exit(1);
});
