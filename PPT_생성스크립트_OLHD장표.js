const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";           // 13.333 x 7.5
pres.author = "학습조직";
pres.title  = "형상 생성부터 설계최적화까지";

const NAVY   = "16305B";
const NAVY2  = "2C4E82";
const ACCENT = "00A3C4";
const ICE    = "CFE0F2";
const BG     = "F3F5F8";
const CARD   = "FFFFFF";
const TXT    = "1C2733";
const MUTED  = "6B7A8F";
const LINE   = "DDE3EB";

const F = "Malgun Gothic";
const M = 0.55;                         // 좌우 여백
const CW = 5.95;                        // 2분할 카드 폭
const CX2 = 6.93;                       // 우측 카드 x

const sh = () => ({ type: "outer", color: "9AA8BC", blur: 8, offset: 1, angle: 90, opacity: 0.18 });

function card(s, x, y, w, h) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, fill: { color: CARD }, rectRadius: 0.06,
    line: { color: LINE, width: 0.75 }, shadow: sh()
  });
}

function cardTitle(s, x, y, t) {
  s.addShape(pres.ShapeType.rect, { x: x + 0.28, y: y + 0.30, w: 0.09, h: 0.20, fill: { color: ACCENT }, line: { color: ACCENT } });
  s.addText(t, { x: x + 0.46, y: y + 0.20, w: 4.9, h: 0.4, fontSize: 13, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0 });
}

function header(s, no, section, title) {
  s.addShape(pres.ShapeType.rect, { x: M, y: 0.42, w: 0.52, h: 0.52, fill: { color: NAVY }, line: { color: NAVY } });
  s.addText(no, { x: M, y: 0.42, w: 0.52, h: 0.52, fontSize: 16, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  s.addText(section, { x: M + 0.68, y: 0.40, w: 8.0, h: 0.26, fontSize: 10.5, bold: true, color: ACCENT, fontFace: F, isTextBox: true, margin: 0, charSpacing: 1 });
  s.addText(title, { x: M + 0.68, y: 0.60, w: 11.6, h: 0.42, fontSize: 22, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0 });
}

function body(s, x, y, w, h, text, opt = {}) {
  s.addText(text, Object.assign({
    x, y, w, h, fontSize: 10.5, color: TXT, fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25
  }, opt));
}

function tbl(s, x, y, w, rows, colW, opt = {}) {
  s.addTable(rows, Object.assign({
    x, y, w, colW, fontSize: 9.5, fontFace: F, color: TXT,
    border: [{ type: "none" }, { type: "none" }, { pt: 0.5, color: LINE }, { type: "none" }],
    rowH: 0.26, valign: "middle", margin: [2, 4, 2, 4]
  }, opt));
}

const hdr = (t) => ({ text: t, options: { bold: true, color: NAVY, fill: { color: "EEF2F7" } } });

// 코드 블록 — 간단한 구문 강조 (주석 / 문자열 / 키워드)
const CODE_BG = "1E2430", C_TXT = "D6DEEB", C_CMT = "7F9C7A", C_STR = "E6A26B", C_KW = "C792EA";
const MONO = "Consolas";
function codeRuns(line) {
  const runs = [];
  let code = line, cmt = "";
  const h = line.indexOf("#");
  if (h >= 0) { code = line.slice(0, h); cmt = line.slice(h); }
  const re = /(f?"[^"]*"|f?'[^']*'|\b(?:for|in|import|from|return|def|lambda|if)\b)/g;
  let last = 0, m;
  while ((m = re.exec(code)) !== null) {
    if (m.index > last) runs.push([code.slice(last, m.index), C_TXT]);
    const tok = m[0];
    runs.push([tok, /^(for|in|import|from|return|def|lambda|if)$/.test(tok) ? C_KW : C_STR]);
    last = m.index + tok.length;
  }
  if (last < code.length) runs.push([code.slice(last), C_TXT]);
  if (cmt) runs.push([cmt, C_CMT]);
  if (!runs.length) runs.push([" ", C_TXT]);
  return runs;
}
function codeBlock(s, x, y, w, h, fname, lines, fs = 8.5) {
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.06, fill: { color: CODE_BG }, line: { color: CODE_BG } });
  ["FF5F57", "FEBC2E", "28C840"].forEach((c, i) => s.addShape(pres.ShapeType.ellipse, { x: x + 0.18 + i * 0.17, y: y + 0.14, w: 0.1, h: 0.1, fill: { color: c }, line: { color: c } }));
  s.addText(fname, { x: x + 0.72, y: y + 0.07, w: w - 0.9, h: 0.24, fontSize: 8.5, color: "8A94A6", fontFace: MONO, isTextBox: true, margin: 0, valign: "middle" });
  s.addShape(pres.ShapeType.line, { x: x, y: y + 0.38, w: w, h: 0, line: { color: "2E3645", width: 0.75 } });
  const runs = [];
  lines.forEach((ln, i) => {
    const r = codeRuns(ln);
    r.forEach(([t, c], j) => runs.push({ text: t, options: { color: c, breakLine: (j === r.length - 1 && i < lines.length - 1) } }));
  });
  s.addText(runs, { x: x + 0.2, y: y + 0.5, w: w - 0.32, h: h - 0.62, fontSize: fs, fontFace: MONO, isTextBox: true, margin: 0, valign: "top", lineSpacingMultiple: 1.08 });
}

function bottomStrip(s, pts) {
  s.addShape(pres.ShapeType.roundRect, { x: M, y: 6.06, w: 12.23, h: 0.92, rectRadius: 0.06, fill: { color: CARD }, line: { color: LINE, width: 0.75 }, shadow: sh() });
  pts.forEach(([h, d], i) => {
    const x = M + 0.36 + i * 4.0;
    s.addShape(pres.ShapeType.rect, { x, y: 6.26, w: 0.07, h: 0.18, fill: { color: ACCENT }, line: { color: ACCENT } });
    s.addText(h, { x: x + 0.16, y: 6.20, w: 3.6, h: 0.28, fontSize: 10.5, bold: true, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(d, { x: x + 0.16, y: 6.50, w: 3.7, h: 0.34, fontSize: 9.5, color: MUTED, fontFace: F, isTextBox: true, margin: 0 });
  });
}

{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "03", "실험계획법 기반 자동해석 및 데이터 확보", "활성 변수 실험계획  —  OLHD (최적라틴방격법)");
  const y0 = 1.30, ch = 5.55, X = M + 0.34, W = 5.3;
  card(s, M, y0, CW, ch);
  cardTitle(s, M, y0, "실험계획 요약");
  [["8", "활성 변수"], ["80", "실험점 (10 × 변수 8)"], ["3", "고정 변수"]].forEach(([v, l], i) => {
    const x = X + i * 1.8;
    s.addShape(pres.ShapeType.roundRect, { x, y: y0 + 0.7, w: 1.62, h: 0.95, rectRadius: 0.07, fill: { color: i === 1 ? NAVY : "EEF2F7" }, line: { color: i === 1 ? NAVY : "EEF2F7" } });
    s.addText(v, { x, y: y0 + 0.74, w: 1.62, h: 0.55, fontSize: 26, bold: true, color: i === 1 ? "FFFFFF" : NAVY, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(l, { x, y: y0 + 1.3, w: 1.62, h: 0.28, fontSize: 9, color: i === 1 ? ICE : MUTED, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });
  s.addText("OLHD란", { x: X, y: y0 + 1.9, w: W, h: 0.28, fontSize: 11, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0 });
  s.addShape(pres.ShapeType.roundRect, { x: X, y: y0 + 2.22, w: W, h: 1.05, rectRadius: 0.06, fill: { color: "EEF2F7" }, line: { color: "EEF2F7" } });
  s.addText([
    { text: "최적라틴방격법 (Optimal Latin Hypercube Design)", options: { bold: true, color: NAVY, breakLine: true } },
    { text: "각 변수 범위를 80구간으로 나눠 구간마다 한 점씩 쓰고, 점 사이 거리를 최대로 벌려 설계공간을 빈틈없이 채우는 실험계획법", options: { color: TXT } }
  ], { x: X + 0.16, y: y0 + 2.22, w: W - 0.3, h: 1.05, fontSize: 9.5, valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });
  s.addText("오른쪽 그래프 읽는 법", { x: X, y: y0 + 3.5, w: W, h: 0.28, fontSize: 11, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0 });
  s.addText([
    { text: "점 하나 = 해석 1회, 칸마다 변수 두 개를 짝지어 본 분포", options: { bullet: true, breakLine: true } },
    { text: "대각선 막대 = 변수 하나만 봤을 때 범위를 고르게 썼는지", options: { bullet: true, breakLine: true } },
    { text: "빨간 칸(핀 개수 × 두께)이 비스듬히 깎이고 핀 두께 막대가 얇은 쪽에 몰린 것은 핀 갭(≥ 2 mm) 제약 때문", options: { bullet: true, bold: true, color: "C0392B" } }
  ], { x: X, y: y0 + 3.84, w: W, h: 1.5, fontSize: 9.5, color: TXT, fontFace: F, isTextBox: true, margin: 0, paraSpaceAfter: 5, lineSpacingMultiple: 1.2, valign: "top" });

  card(s, CX2, y0, CW, ch);
  const IS = 5.35;
  s.addImage({ path: __dirname + "/OLHD_변수쌍산점도.png", x: CX2 + (CW - IS) / 2, y: y0 + (ch - IS) / 2, w: IS, h: IS });
  s.addNotes("선별에서 남은 활성 변수 8개로 최적라틴방격법(OLHD) 80점을 해석했습니다. 오른쪽은 80점을 변수 두 개씩 짝지어 그린 것으로, 점 하나가 해석 한 번입니다. 대부분의 칸에서 점이 고르게 퍼져 있어 설계공간을 빈틈없이 덮었고, 핀 개수와 두께 칸만 핀 갭 제약 때문에 만들 수 있는 영역에만 점이 있습니다.");
}
pres.writeFile({ fileName: __dirname + "/OLHD_장표.pptx" }).then(f => console.log("생성 완료:", f));
