// gerar_apresentacao.js — Apresentação do Agente de Reuniões GoAkira (4 slides)
// Roda: node gerar_apresentacao.js

const pptxgen = require("pptxgenjs");

let pres = new pptxgen();
pres.layout  = "LAYOUT_16x9";
pres.author  = "GoAkira";
pres.title   = "Agente de Reuniões GoAkira";
pres.subject = "Pipeline de automação de reuniões";

// ── Paleta ─────────────────────────────────────────────────────
const NAVY      = "1E2761";
const ICE       = "CADCFC";
const CORAL     = "DC2626";
const WHITE     = "FFFFFF";
const GRAY      = "64748B";
const DARK_TEXT = "1E293B";
const LIGHT_BG  = "F8FAFC";
const GREEN     = "10B981";
const PURPLE    = "8B5CF6";
const BLUE      = "3B82F6";

// ─────────────────────────────────────────────────────────────────
// SLIDE 1 — CAPA
// ─────────────────────────────────────────────────────────────────
const s1 = pres.addSlide();
s1.background = { color: NAVY };

// Badge "GOAKIRA" vermelho
s1.addShape(pres.shapes.ROUNDED_RECTANGLE, {
  x: 0.5, y: 0.42, w: 1.9, h: 0.34,
  fill: { color: CORAL }, rectRadius: 0.05,
});
s1.addText("GOAKIRA", {
  x: 0.5, y: 0.42, w: 1.9, h: 0.34,
  fontSize: 10, bold: true, charSpacing: 3,
  color: WHITE, align: "center", valign: "middle", margin: 0,
  fontFace: "Calibri",
});

// Título principal
s1.addText("Agente de Reuniões", {
  x: 0.5, y: 1.1, w: 9.0, h: 1.0,
  fontSize: 50, bold: true, color: WHITE, fontFace: "Calibri",
});
s1.addText("GoAkira", {
  x: 0.5, y: 2.0, w: 9.0, h: 0.9,
  fontSize: 50, bold: true, color: ICE, fontFace: "Calibri",
});

// Linha divisória
s1.addShape(pres.shapes.RECTANGLE, {
  x: 0.5, y: 3.05, w: 3.5, h: 0.04,
  fill: { color: CORAL },
});

// Subtítulo
s1.addText(
  "Automação inteligente de transcrições, atas e relatórios — de ponta a ponta.",
  {
    x: 0.5, y: 3.25, w: 7.5, h: 0.65,
    fontSize: 14, color: "A5B4FC", fontFace: "Calibri",
  }
);

// Rodapé
s1.addText("Junho 2026  ·  Pipeline diário automatizado", {
  x: 0.5, y: 5.1, w: 9.0, h: 0.35,
  fontSize: 10, color: "4B5563", fontFace: "Calibri",
});

// ─────────────────────────────────────────────────────────────────
// SLIDE 2 — COMO FUNCIONA (pipeline em 4 etapas)
// ─────────────────────────────────────────────────────────────────
const s2 = pres.addSlide();
s2.background = { color: LIGHT_BG };

s2.addText("Como Funciona", {
  x: 0.5, y: 0.3, w: 9.0, h: 0.6,
  fontSize: 30, bold: true, color: NAVY, fontFace: "Calibri",
});

const steps = [
  {
    num: "1", title: "Busca", color: BLUE,
    lines: ["Google Drive", "Meet Recordings", "transcrições do dia"],
  },
  {
    num: "2", title: "Sumariza", color: PURPLE,
    lines: ["Claude Haiku 4.5", "extrai tópicos,", "acionáveis e riscos"],
  },
  {
    num: "3", title: "Cria Atas", color: GREEN,
    lines: ["Gera .docx e sobe", "ao Drive como", "Google Doc editável"],
  },
  {
    num: "4", title: "Notifica", color: CORAL,
    lines: ["PDF por email para", "os diretores da", "GoAkira"],
  },
];

const CARD_W = 2.1, CARD_GAP = 0.25, START_X = 0.4, CARD_Y = 1.15, CARD_H = 3.6;

steps.forEach((step, i) => {
  const cx = START_X + i * (CARD_W + CARD_GAP);

  // Card
  s2.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: cx, y: CARD_Y, w: CARD_W, h: CARD_H,
    fill: { color: WHITE },
    shadow: { type: "outer", color: "000000", blur: 8, offset: 2, angle: 45, opacity: 0.10 },
    rectRadius: 0.12,
  });

  // Número círculo
  s2.addShape(pres.shapes.OVAL, {
    x: cx + 0.725, y: CARD_Y + 0.22, w: 0.65, h: 0.65,
    fill: { color: step.color },
  });
  s2.addText(step.num, {
    x: cx + 0.725, y: CARD_Y + 0.22, w: 0.65, h: 0.65,
    fontSize: 18, bold: true, color: WHITE,
    align: "center", valign: "middle", margin: 0, fontFace: "Calibri",
  });

  // Título da etapa
  s2.addText(step.title, {
    x: cx + 0.1, y: CARD_Y + 1.08, w: CARD_W - 0.2, h: 0.4,
    fontSize: 14, bold: true, color: DARK_TEXT,
    align: "center", fontFace: "Calibri",
  });

  // Descrição (multi-linha via array)
  const descItems = step.lines.map((line, li) =>
    li < step.lines.length - 1
      ? { text: line, options: { breakLine: true } }
      : { text: line }
  );
  s2.addText(descItems, {
    x: cx + 0.1, y: CARD_Y + 1.58, w: CARD_W - 0.2, h: 1.4,
    fontSize: 11, color: GRAY, align: "center", fontFace: "Calibri",
  });

  // Seta (exceto após o último)
  if (i < steps.length - 1) {
    s2.addText("→", {
      x: cx + CARD_W, y: CARD_Y + 1.5, w: CARD_GAP, h: 0.5,
      fontSize: 18, color: "CBD5E1", align: "center", valign: "middle",
    });
  }
});

// Nota de agendamento
s2.addShape(pres.shapes.ROUNDED_RECTANGLE, {
  x: 0.4, y: 5.0, w: 9.2, h: 0.38,
  fill: { color: "FEF3C7" }, rectRadius: 0.06,
});
s2.addText(
  "Executa automaticamente às 9h (seg–sex)  ·  Monitor verifica às 9h30 e alerta por email em caso de falha",
  {
    x: 0.5, y: 5.0, w: 9.0, h: 0.38,
    fontSize: 10, color: "92400E", fontFace: "Calibri",
    align: "center", valign: "middle",
  }
);

// ─────────────────────────────────────────────────────────────────
// SLIDE 3 — RESULTADOS
// ─────────────────────────────────────────────────────────────────
const s3 = pres.addSlide();
s3.background = { color: WHITE };

s3.addText("O que o Agente entrega", {
  x: 0.5, y: 0.3, w: 9.0, h: 0.6,
  fontSize: 30, bold: true, color: NAVY, fontFace: "Calibri",
});

// 3 cards de métricas
const metrics = [
  {
    num: "100%", label: "Transcrições\nprocessadas",
    sub: "Todas as reuniões do dia", color: GREEN, bg: "F0FDF4",
  },
  {
    num: "1 ata", label: "por reunião\nno Drive",
    sub: "Google Doc editável por cliente", color: NAVY, bg: "EEF2FF",
  },
  {
    num: "PDF", label: "resumo diário\npara diretores",
    sub: "Email automático às 9h04", color: CORAL, bg: "FEF2F2",
  },
];

const MET_W = 2.8, MET_H = 2.2, MET_Y = 1.1, MET_GAP = 0.38;

metrics.forEach((m, i) => {
  const mx = 0.5 + i * (MET_W + MET_GAP);

  s3.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: mx, y: MET_Y, w: MET_W, h: MET_H,
    fill: { color: m.bg },
    shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 45, opacity: 0.07 },
    rectRadius: 0.12,
  });

  s3.addText(m.num, {
    x: mx, y: MET_Y + 0.2, w: MET_W, h: 0.75,
    fontSize: 40, bold: true, color: m.color,
    fontFace: "Calibri", align: "center",
  });

  const labelItems = m.label.split("\n").map((line, li, arr) =>
    li < arr.length - 1
      ? { text: line, options: { breakLine: true } }
      : { text: line }
  );
  s3.addText(labelItems, {
    x: mx, y: MET_Y + 1.0, w: MET_W, h: 0.65,
    fontSize: 12, bold: true, color: DARK_TEXT,
    fontFace: "Calibri", align: "center",
  });

  s3.addText(m.sub, {
    x: mx, y: MET_Y + 1.72, w: MET_W, h: 0.32,
    fontSize: 10, color: GRAY, fontFace: "Calibri", align: "center",
  });
});

// Detalhes do conteúdo entregue
s3.addText("O que chega para os diretores:", {
  x: 0.5, y: 3.55, w: 9.0, h: 0.38,
  fontSize: 13, bold: true, color: NAVY, fontFace: "Calibri",
});

const items = [
  "Resumo executivo em PDF: tópicos discutidos, acionáveis e próximos passos de cada reunião",
  "Links para as atas individuais no Google Drive — editáveis e prontas para formalização",
  "Notificação ao consultor BP do cliente via email, com link direto para a ata no Drive",
];

items.forEach((item, i) => {
  s3.addText(
    [
      { text: "✓  ", options: { bold: true, color: GREEN } },
      { text: item, options: { color: DARK_TEXT } },
    ],
    {
      x: 0.5, y: 4.0 + i * 0.38, w: 9.0, h: 0.34,
      fontSize: 11, fontFace: "Calibri",
    }
  );
});

// ─────────────────────────────────────────────────────────────────
// SLIDE 4 — TECNOLOGIAS & MONITORAMENTO
// ─────────────────────────────────────────────────────────────────
const s4 = pres.addSlide();
s4.background = { color: NAVY };

s4.addText("Tecnologias & Monitoramento", {
  x: 0.5, y: 0.28, w: 9.0, h: 0.6,
  fontSize: 30, bold: true, color: WHITE, fontFace: "Calibri",
});

const techs = [
  { name: "Python 3.12",    desc: ["Pipeline principal", "e orquestração"], icon: "🐍", color: BLUE },
  { name: "Claude Haiku",   desc: ["Sumarização com IA", "(Anthropic)"],     icon: "🤖", color: PURPLE },
  { name: "Google Drive",   desc: ["Busca transcrições", "e salva as atas"], icon: "📁", color: GREEN },
  { name: "Gmail SMTP",     desc: ["Envio de relatórios", "aos diretores"],   icon: "📧", color: "F59E0B" },
  { name: "CrewAI",         desc: ["Observabilidade e", "rastreio em tempo real"], icon: "👥", color: CORAL },
  { name: "Task Scheduler", desc: ["Execução automática", "diária às 9h"],   icon: "⏰", color: "6B7280" },
];

const TW = 2.95, TH = 1.6, TX0 = 0.4, TY0 = 1.18, TGAPX = 0.18, TGAPY = 0.22;

techs.forEach((tech, i) => {
  const col = i % 3;
  const row = Math.floor(i / 3);
  const tx = TX0 + col * (TW + TGAPX);
  const ty = TY0 + row * (TH + TGAPY);

  // Card
  s4.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: tx, y: ty, w: TW, h: TH,
    fill: { color: WHITE, transparency: 88 },
    rectRadius: 0.1,
  });

  // Ícone + nome
  s4.addText([
    { text: tech.icon + "  ", options: {} },
    { text: tech.name, options: { bold: true } },
  ], {
    x: tx + 0.15, y: ty + 0.18, w: TW - 0.3, h: 0.4,
    fontSize: 12, color: WHITE, fontFace: "Calibri",
  });

  // Descrição
  const descItems = tech.desc.map((line, li, arr) =>
    li < arr.length - 1
      ? { text: line, options: { breakLine: true } }
      : { text: line }
  );
  s4.addText(descItems, {
    x: tx + 0.15, y: ty + 0.65, w: TW - 0.3, h: 0.75,
    fontSize: 11, color: ICE, fontFace: "Calibri",
  });
});

// Nota final
s4.addText(
  "Rastreio de execução em tempo real via  app.crewai.com  ·  Logs persistidos em agente.log",
  {
    x: 0.5, y: 5.2, w: 9.0, h: 0.28,
    fontSize: 10, color: "4B5563", fontFace: "Calibri", align: "center",
  }
);

// ─────────────────────────────────────────────────────────────────
// SLIDE 5 — CONFIGURAÇÃO INICIAL
// ─────────────────────────────────────────────────────────────────
const s5 = pres.addSlide();
s5.background = { color: LIGHT_BG };

s5.addText("Configuração Inicial", {
  x: 0.5, y: 0.2, w: 6.5, h: 0.52,
  fontSize: 28, bold: true, color: NAVY, fontFace: "Calibri",
});

// Badge "Faça uma única vez"
s5.addShape(pres.shapes.ROUNDED_RECTANGLE, {
  x: 7.3, y: 0.23, w: 2.35, h: 0.34,
  fill: { color: GREEN }, rectRadius: 0.06,
});
s5.addText("Faça uma única vez", {
  x: 7.3, y: 0.23, w: 2.35, h: 0.34,
  fontSize: 10, bold: true, color: WHITE, align: "center", valign: "middle",
  margin: 0, fontFace: "Calibri",
});

// ── PASSO 1 card (esquerda) ──────────────────────────────────────
s5.addShape(pres.shapes.ROUNDED_RECTANGLE, {
  x: 0.4, y: 0.88, w: 4.42, h: 4.55,
  fill: { color: WHITE },
  shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 45, opacity: 0.08 },
  rectRadius: 0.1,
});

s5.addShape(pres.shapes.OVAL, { x: 0.6, y: 0.98, w: 0.52, h: 0.52, fill: { color: BLUE } });
s5.addText("1", {
  x: 0.6, y: 0.98, w: 0.52, h: 0.52,
  fontSize: 14, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0, fontFace: "Calibri",
});
s5.addText("Compartilhe sua pasta \"Meet Recordings\"", {
  x: 1.22, y: 0.98, w: 3.45, h: 0.52,
  fontSize: 11, bold: true, color: DARK_TEXT, fontFace: "Calibri", valign: "middle",
});

const passo1 = [
  "Abra o Google Drive da sua conta @goakira.com.br",
  "Localize a pasta \"Meet Recordings\" na raiz do Drive",
  "Clique com botão direito → Compartilhar",
  "Adicione c10@goakira.com.br com permissão de Leitor",
  "Clique em Enviar",
  "Copie o link da pasta e envie para c10@goakira.com.br",
];
passo1.forEach((step, i) => {
  s5.addText(
    [
      { text: `${i + 1}.  `, options: { bold: true, color: BLUE } },
      { text: step, options: { color: DARK_TEXT } },
    ],
    { x: 0.55, y: 1.65 + i * 0.42, w: 4.1, h: 0.38, fontSize: 10, fontFace: "Calibri" }
  );
});

s5.addText(
  "Após isso, o agente lê suas gravações automaticamente — você não precisa fazer mais nada nesta etapa.",
  {
    x: 0.55, y: 4.22, w: 4.1, h: 0.65,
    fontSize: 9.5, italic: true, color: GREEN, fontFace: "Calibri",
  }
);

// ── PASSO 2 card (direita) ───────────────────────────────────────
s5.addShape(pres.shapes.ROUNDED_RECTANGLE, {
  x: 5.08, y: 0.88, w: 4.52, h: 4.55,
  fill: { color: WHITE },
  shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 45, opacity: 0.08 },
  rectRadius: 0.1,
});

s5.addShape(pres.shapes.OVAL, { x: 5.28, y: 0.98, w: 0.52, h: 0.52, fill: { color: PURPLE } });
s5.addText("2", {
  x: 5.28, y: 0.98, w: 0.52, h: 0.52,
  fontSize: 14, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0, fontFace: "Calibri",
});
s5.addText("Nomeie a reunião no Google Calendar", {
  x: 5.9, y: 0.98, w: 3.55, h: 0.52,
  fontSize: 11, bold: true, color: DARK_TEXT, fontFace: "Calibri", valign: "middle",
});

s5.addText("Formato:", { x: 5.22, y: 1.65, w: 4.2, h: 0.26, fontSize: 10, bold: true, color: DARK_TEXT, fontFace: "Calibri" });
s5.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.22, y: 1.93, w: 4.2, h: 0.3, fill: { color: "EEF2FF" }, rectRadius: 0.05 });
s5.addText("[Nome do Cliente] Fase - Assunto", {
  x: 5.27, y: 1.93, w: 4.1, h: 0.3,
  fontSize: 10, bold: true, color: NAVY, fontFace: "Calibri", valign: "middle",
});

s5.addText("Exemplos:", { x: 5.22, y: 2.32, w: 4.2, h: 0.25, fontSize: 10, bold: true, color: DARK_TEXT, fontFace: "Calibri" });
const exemplos = [
  "[Meraki Gyros] BP - R3 Validação da Modelagem",
  "[Sorvetes Capricho] MN - Validação Kit 1",
  "[Colégio Bal] BP - Kick Off",
];
exemplos.forEach((ex, i) => {
  s5.addText("• " + ex, {
    x: 5.22, y: 2.58 + i * 0.28, w: 4.2, h: 0.25,
    fontSize: 9.5, color: GRAY, fontFace: "Calibri",
  });
});

s5.addText("Códigos de fase:", { x: 5.22, y: 3.44, w: 4.2, h: 0.25, fontSize: 10, bold: true, color: DARK_TEXT, fontFace: "Calibri" });

s5.addTable(
  [
    [
      { text: "Código", options: { bold: true, color: WHITE, fill: { color: NAVY }, align: "center" } },
      { text: "Fase",   options: { bold: true, color: WHITE, fill: { color: NAVY } } },
    ],
    [{ text: "BP",  options: { align: "center", color: DARK_TEXT } }, { text: "Business Plan",         options: { color: DARK_TEXT } }],
    [{ text: "MN",  options: { align: "center", color: DARK_TEXT } }, { text: "Manuais Operacionais",  options: { color: DARK_TEXT } }],
    [{ text: "IJ",  options: { align: "center", color: DARK_TEXT } }, { text: "Instrumentos Jurídicos",options: { color: DARK_TEXT } }],
    [{ text: "GM",  options: { align: "center", color: DARK_TEXT } }, { text: "GoMentoring",           options: { color: DARK_TEXT } }],
    [{ text: "GEO", options: { align: "center", color: DARK_TEXT } }, { text: "Geomarketing",          options: { color: DARK_TEXT } }],
  ],
  {
    x: 5.22, y: 3.7, w: 4.2, h: 1.55,
    fontSize: 9.5, fontFace: "Calibri",
    border: { pt: 0.5, color: "E2E8F0" },
    fill: { color: "F8FAFC" },
    colW: [0.95, 3.25],
  }
);

// ─────────────────────────────────────────────────────────────────
// SLIDE 6 — O QUE ACONTECE APÓS A REUNIÃO
// ─────────────────────────────────────────────────────────────────
const s6 = pres.addSlide();
s6.background = { color: WHITE };

s6.addText("Após a Reunião", {
  x: 0.5, y: 0.2, w: 9.0, h: 0.52,
  fontSize: 28, bold: true, color: NAVY, fontFace: "Calibri",
});
s6.addText("Tudo acontece automaticamente — você não precisa criar atas nem mover arquivos.", {
  x: 0.5, y: 0.76, w: 9.0, h: 0.3,
  fontSize: 12, color: GRAY, fontFace: "Calibri",
});

// ── Coluna esquerda: O que acontece automaticamente ──────────────
s6.addShape(pres.shapes.ROUNDED_RECTANGLE, {
  x: 0.4, y: 1.18, w: 5.1, h: 4.2,
  fill: { color: LIGHT_BG },
  shadow: { type: "outer", color: "000000", blur: 5, offset: 1, angle: 45, opacity: 0.07 },
  rectRadius: 0.1,
});
s6.addText("O que acontece automaticamente", {
  x: 0.6, y: 1.28, w: 4.7, h: 0.38,
  fontSize: 12, bold: true, color: NAVY, fontFace: "Calibri",
});

const autoSteps = [
  { num: "1", text: "O Gemini gera a transcrição e salva automaticamente em \"Meet Recordings\" no Drive.", color: BLUE },
  { num: "2", text: "Às 9h do dia seguinte, o agente localiza e lê a transcrição da sua reunião.", color: PURPLE },
  { num: "3", text: "Gera a ata e salva na pasta do cliente:\nClientes → [Cliente] → Business Plan → Atas e Formalizações", color: GREEN },
  { num: "4", text: "Você recebe um email com o resumo executivo e o link direto para a ata no Drive.", color: CORAL },
];

autoSteps.forEach((step, i) => {
  const sy = 1.82 + i * 0.84;
  s6.addShape(pres.shapes.OVAL, { x: 0.58, y: sy, w: 0.42, h: 0.42, fill: { color: step.color } });
  s6.addText(step.num, {
    x: 0.58, y: sy, w: 0.42, h: 0.42,
    fontSize: 12, bold: true, color: WHITE, align: "center", valign: "middle", margin: 0, fontFace: "Calibri",
  });
  s6.addText(step.text, {
    x: 1.12, y: sy - 0.04, w: 4.2, h: 0.72,
    fontSize: 10.5, color: DARK_TEXT, fontFace: "Calibri",
  });
});

// ── Coluna direita: O que você recebe ───────────────────────────
s6.addShape(pres.shapes.ROUNDED_RECTANGLE, {
  x: 5.7, y: 1.18, w: 3.9, h: 4.2,
  fill: { color: "EEF2FF" },
  shadow: { type: "outer", color: "000000", blur: 5, offset: 1, angle: 45, opacity: 0.07 },
  rectRadius: 0.1,
});
s6.addText("O que você recebe no email", {
  x: 5.9, y: 1.28, w: 3.5, h: 0.38,
  fontSize: 12, bold: true, color: NAVY, fontFace: "Calibri",
});

// Ícone de email
s6.addShape(pres.shapes.ROUNDED_RECTANGLE, {
  x: 5.9, y: 1.74, w: 3.5, h: 0.3,
  fill: { color: NAVY }, rectRadius: 0.04,
});
s6.addText("✉  Email automático após cada reunião processada", {
  x: 5.92, y: 1.74, w: 3.46, h: 0.3,
  fontSize: 9, bold: true, color: WHITE, fontFace: "Calibri", valign: "middle",
});

const emailItems = [
  "Nome do cliente e título da reunião",
  "Resumo executivo da conversa",
  "Principais acionáveis identificados",
  "Próximos passos acordados",
  "Alertas e riscos (se houver)",
  "Botão de acesso direto à ata no Drive",
];
emailItems.forEach((item, i) => {
  s6.addText(
    [
      { text: "✓  ", options: { bold: true, color: GREEN } },
      { text: item, options: { color: DARK_TEXT } },
    ],
    { x: 5.9, y: 2.18 + i * 0.46, w: 3.5, h: 0.38, fontSize: 10.5, fontFace: "Calibri" }
  );
});

// ─────────────────────────────────────────────────────────────────
// SLIDE 7 — FAQ
// ─────────────────────────────────────────────────────────────────
const s7 = pres.addSlide();
s7.background = { color: NAVY };

s7.addText("Dúvidas Frequentes", {
  x: 0.5, y: 0.2, w: 9.0, h: 0.52,
  fontSize: 28, bold: true, color: WHITE, fontFace: "Calibri",
});

const faqs = [
  {
    q: "E se eu esquecer de nomear a reunião no formato correto?",
    a: "Corrija o nome do arquivo na pasta \"Meet Recordings\" do Drive e avise c10@goakira.com.br — faremos o reprocessamento manual.",
  },
  {
    q: "O Gemini precisa estar ativo durante a reunião?",
    a: "Sim. Verifique nas configurações do Google Meet se \"Anotações automáticas\" está habilitado. Sem transcrição, o agente não tem o que processar.",
  },
  {
    q: "Posso editar a ata gerada?",
    a: "Sim. A ata é um Google Doc 100% editável. Use o link do email de notificação para abrir e ajustar livremente.",
  },
  {
    q: "O agente processa reuniões internas da GoAkira?",
    a: "Não. Somente reuniões com [Cliente] no nome do evento são processadas. Reuniões internas sem esse formato são ignoradas.",
  },
];

const FAQ_W = 4.3, FAQ_H = 2.05, FAQ_GAP_X = 0.28, FAQ_GAP_Y = 0.22;
const FAQ_X0 = 0.4, FAQ_Y0 = 0.95;

faqs.forEach((faq, i) => {
  const col = i % 2;
  const row = Math.floor(i / 2);
  const fx = FAQ_X0 + col * (FAQ_W + FAQ_GAP_X);
  const fy = FAQ_Y0 + row * (FAQ_H + FAQ_GAP_Y);

  s7.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: fx, y: fy, w: FAQ_W, h: FAQ_H,
    fill: { color: WHITE, transparency: 88 },
    rectRadius: 0.1,
  });

  s7.addText("P: " + faq.q, {
    x: fx + 0.18, y: fy + 0.14, w: FAQ_W - 0.36, h: 0.68,
    fontSize: 11, bold: true, color: WHITE, fontFace: "Calibri",
  });

  s7.addText("R: " + faq.a, {
    x: fx + 0.18, y: fy + 0.88, w: FAQ_W - 0.36, h: 1.0,
    fontSize: 10, color: ICE, fontFace: "Calibri",
  });
});

// ── Salvar ────────────────────────────────────────────────────────
pres
  .writeFile({ fileName: "Agente_GoAkira.pptx" })
  .then(() => console.log("done"))
  .catch((e) => { console.error(e); process.exit(1); });
