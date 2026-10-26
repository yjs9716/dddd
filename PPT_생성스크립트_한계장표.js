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
  header(s, "04", "머신러닝 대리모델 구축", "한계 및 차월 계획  —  데이터 보강 필요성");
  const y0 = 1.30, ch = 4.55, X = M + 0.34, W = 5.3;
  card(s, M, y0, CW, ch);
  cardTitle(s, M, y0, "80점으로는 부족한 근거");
  tbl(s, X, y0 + 0.68, W, [
    [hdr("근거"), hdr("2차 균일도"), hdr("다른 응답")],
    ["① 예측 정확도 (교차검증 R²)", { text: "0.893", options: { bold: true, color: "0088A6" } }, "0.956 ~ 1.000"],
    ["② 예측 불확실성 (2σ ÷ 응답 변동폭)", { text: "43%", options: { bold: true, color: "0088A6" } }, "10 ~ 30%"],
    ["③ 불확실성 큰 영역 비율", { text: "설계공간 17%", options: { bold: true, color: "0088A6" } }, "0 ~ 2%"],
    ["④ 교호작용 비율", { text: "19%", options: { bold: true, color: "0088A6" } }, "3 ~ 13%"]
  ], [2.6, 1.3, 1.4], { rowH: 0.42, fontSize: 9 });
  s.addShape(pres.ShapeType.roundRect, { x: X, y: y0 + 2.95, w: W, h: 1.4, rectRadius: 0.06, fill: { color: "EEF2F7" }, line: { color: "EEF2F7" } });
  s.addText([
    { text: "⑤ 8차원 공간에 80점 — 데이터가 성김", options: { bold: true, color: NAVY, breakLine: true } },
    { text: "새 설계에서 가장 가까운 해석점까지 거리가 보통 각 변수 범위의 약 절반", options: { color: TXT, breakLine: true } },
    { text: "→ 변수끼리 얽혀 복잡하게 변하는 응답(2차 균일도)일수록 점이 더 필요", options: { color: TXT } }
  ], { x: X + 0.16, y: y0 + 2.95, w: W - 0.3, h: 1.4, fontSize: 9.3, valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.3 });

  card(s, CX2, y0, CW, ch);
  cardTitle(s, CX2, y0, "차월 계획  —  적응 샘플링");
  const RX = CX2 + 0.34;
  [["균일하게 더 뽑으면", "이미 정확한 영역까지 해석 → 해석 시간 낭비", "B9C7D8", MUTED],
   ["적응 샘플링", "GPR 불확실성(σ)이 가장 큰 지점만 골라 해석 추가 → 모델 갱신 → 반복", ACCENT, NAVY]].forEach(([h, d, c, tc], i) => {
    const yy = y0 + 0.7 + i * 0.95;
    s.addShape(pres.ShapeType.roundRect, { x: RX, y: yy, w: W, h: 0.82, rectRadius: 0.06, fill: { color: i ? "E8F6FA" : "F7F9FC" }, line: { color: c, width: 0.75 } });
    s.addText([{ text: h, options: { bold: true, color: tc, breakLine: true } }, { text: d, options: { color: TXT } }],
      { x: RX + 0.16, y: yy, w: W - 0.3, h: 0.82, fontSize: 9.5, valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });
  });
  s.addText("이후", { x: RX, y: y0 + 2.75, w: W, h: 0.26, fontSize: 10.5, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0 });
  s.addText([
    { text: "다목적 최적화 — 보강된 대리모델 위에서 파레토 최적해 탐색", options: { bullet: true, breakLine: true } },
    { text: "최적안 재해석으로 예측 검증", options: { bullet: true, breakLine: true } },
    { text: "실제 사업 AI 열해석 자동화 적용 가능성 검토", options: { bullet: true } }
  ], { x: RX, y: y0 + 3.05, w: W, h: 1.2, fontSize: 9.5, color: TXT, fontFace: F, isTextBox: true, margin: 0, paraSpaceAfter: 4, lineSpacingMultiple: 1.2 });

  bottomStrip(s, [
    ["2차 균일도가 가장 부족", "정확도 최저 · 불확실성 최대 · 교호작용 최대"],
    ["원인은 데이터 밀도", "8차원에 80점 → 복잡한 응답을 다 담지 못함"],
    ["필요한 곳만 보강", "불확실성 큰 지점에 해석 추가 (적응 샘플링)"]
  ]);
  s.addNotes("80점으로 만든 모델은 대부분 응답에서 정확하지만, 2차 균일도는 교차검증 R²가 0.893으로 가장 낮고, 예측 불확실성도 응답 변동폭의 43%로 가장 큽니다. 설계공간의 17%는 불확실성이 변동폭의 절반을 넘습니다. 2차 균일도는 변수끼리 얽힌 효과가 19%로 가장 커서 복잡하게 변하는데, 8차원 공간에 80점이면 새 설계에서 가장 가까운 해석점이 보통 범위의 절반쯤 떨어져 있어 이런 변화를 다 담지 못합니다. 그래서 차월에는 균일하게 점을 더 뽑는 대신, GPR 불확실성이 큰 지점만 골라 해석을 추가하는 적응 샘플링으로 모델을 보강합니다.");
}
pres.writeFile({ fileName: __dirname + "/한계_차월_장표.pptx" }).then(f => console.log("ok"));
