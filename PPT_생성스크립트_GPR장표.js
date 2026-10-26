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

const fs = require("fs");
const DATA = JSON.parse(fs.readFileSync(__dirname + "/2개월차_데이터.json", "utf-8"));
const EQ = __dirname + "/식/";
const eq = (s, name, x, y, k = 0.7) => {
  const sz = { eq1: [1821, 120], eq2: [2099, 285], eq3a: [941, 136], eq3b: [1497, 136], eq4: [2120, 125], eqA: [793, 252] }[name];
  const w = sz[0] / 300 * k, h = sz[1] / 300 * k;
  s.addImage({ path: EQ + name + ".png", x, y, w, h });
  return h;
};
const lbl = (s, t, x, y, w) => s.addText(t, { x, y, w, h: 0.26, fontSize: 10.5, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0 });
const cap = (s, t, x, y, w, h = 0.26) => s.addText(t, { x, y, w, h, fontSize: 8.8, color: MUTED, fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.15 });
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "04", "머신러닝 대리모델 구축", "대리모델  —  가우시안 프로세스 회귀 (GPR)");
  const y0 = 1.30, ch = 5.55, X = M + 0.34, W = 5.3, RX = CX2 + 0.34;

  // 좌 — 개념 그림 + 예측 식
  card(s, M, y0, CW, ch);
  cardTitle(s, M, y0, "개념  —  예측값과 불확실성을 함께 제공");
  const g = DATA.gp1d;
  const PX = M + 0.55, PY = y0 + 0.66, PW = 4.9, PH = 1.75;
  const ups = g.m.map((m, i) => m + 2 * g.sd[i]), los = g.m.map((m, i) => m - 2 * g.sd[i]);
  const yMin = Math.min(...los) - 0.1, yMax = Math.max(...ups) + 0.1;
  const tx = (x) => x * PW, ty = (y) => (yMax - y) / (yMax - yMin) * PH;
  s.addShape(pres.ShapeType.rect, { x: PX, y: PY, w: PW, h: PH, fill: { color: "FAFBFD" }, line: { color: LINE, width: 0.75 } });
  const band = g.x.map((x, i) => ({ x: tx(x), y: ty(ups[i]) })).concat(g.x.slice().reverse().map((x, j) => { const i = g.x.length - 1 - j; return { x: tx(x), y: ty(los[i]) }; }));
  band.push({ close: true });
  s.addShape(pres.ShapeType.custGeom, { x: PX, y: PY, w: PW, h: PH, points: band, fill: { color: ACCENT, transparency: 72 }, line: { color: ACCENT, transparency: 100 } });
  s.addShape(pres.ShapeType.custGeom, { x: PX, y: PY, w: PW, h: PH, points: g.x.map((x, i) => ({ x: tx(x), y: ty(g.m[i]) })), line: { color: NAVY, width: 2 } });
  g.xt.forEach((x, i) => s.addShape(pres.ShapeType.ellipse, { x: PX + tx(x) - 0.06, y: PY + ty(g.yt[i]) - 0.06, w: 0.12, h: 0.12, fill: { color: "FFFFFF" }, line: { color: NAVY, width: 1.5 } }));
  const ly = PY + PH + 0.06;
  s.addShape(pres.ShapeType.ellipse, { x: PX, y: ly + 0.05, w: 0.12, h: 0.12, fill: { color: "FFFFFF" }, line: { color: NAVY, width: 1.5 } });
  s.addText("해석 결과 y", { x: PX + 0.18, y: ly, w: 1.2, h: 0.22, fontSize: 8.5, color: TXT, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  s.addShape(pres.ShapeType.line, { x: PX + 1.35, y: ly + 0.11, w: 0.3, h: 0, line: { color: NAVY, width: 2 } });
  s.addText("예측 평균 μ", { x: PX + 1.7, y: ly, w: 1.0, h: 0.22, fontSize: 8.5, color: TXT, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  s.addShape(pres.ShapeType.rect, { x: PX + 2.8, y: ly + 0.03, w: 0.3, h: 0.16, fill: { color: ACCENT, transparency: 72 }, line: { color: ACCENT, transparency: 100 } });
  s.addText("불확실성 ±2σ", { x: PX + 3.15, y: ly, w: 1.3, h: 0.22, fontSize: 8.5, color: TXT, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

  lbl(s, "예측 평균", X, y0 + 2.82, W);
  const ha = eq(s, "eq3a", X + 0.1, y0 + 3.1, 0.62);
  cap(s, "새 설계 x*의 예측 = 해석 결과 y의 가중합. 가중치는 x*가 각 해석점과 얼마나 비슷한지(k*)로 정해짐", X, y0 + 3.1 + ha + 0.03, W, 0.4);
  lbl(s, "예측 분산 (불확실성)", X, y0 + 4.0, W);
  const hb = eq(s, "eq3b", X + 0.1, y0 + 4.28, 0.62);
  cap(s, "처음 불확실성 k(x*,x*)에서 근처 해석점이 알려준 만큼 빼줌 → 해석점이 가까울수록 작아짐", X, y0 + 4.28 + hb + 0.03, W, 0.4);
  cap(s, "K : 해석점 80개끼리의 유사도 표 (80 × 80)   ·   k* : 새 설계와 해석점 80개 사이 유사도", X, y0 + 5.12, W);

  // 우 — 왜 GPR + 모델 식
  card(s, CX2, y0, CW, ch);
  cardTitle(s, CX2, y0, "왜 GPR인가  —  본 과제에 적합한 이유");
  [["해석 비용이 큼", "1회 약 17분 → 대리모델이 해석 대신 수 초 만에 예측"],
   ["소규모 데이터로 학습", "80점만으로 응답 7개 모델 (교차검증 R² 0.89 ~ 1.00)"],
   ["불확실성 제공", "예측 신뢰도를 함께 제공 → 추가 해석 위치 선정"]].forEach(([h, d], i) => {
    const yy = y0 + 0.62 + i * 0.34;
    s.addText([{ text: h, options: { bold: true, color: NAVY } }, { text: "   " + d, options: { color: TXT } }],
      { x: RX, y: yy, w: W, h: 0.3, fontSize: 9, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });
  s.addShape(pres.ShapeType.line, { x: RX, y: y0 + 1.7, w: W, h: 0, line: { color: LINE, width: 0.75 } });

  lbl(s, "모델 가정", RX, y0 + 1.78, W);
  const h1 = eq(s, "eq1", RX + 0.1, y0 + 2.06, 0.62);
  cap(s, "y: 해석 결과  ·  f: 설계에 따라 매끄럽게 변하는 성능  ·  ε: 작은 수치 오차 (크기 σ_n²)", RX, y0 + 2.06 + h1 + 0.03, W);
  lbl(s, "커널  —  Matern 5/2 + ARD", RX, y0 + 2.7, W);
  const h2 = eq(s, "eq2", RX + 0.1, y0 + 2.98, 0.62);
  cap(s, "k: 두 설계가 얼마나 비슷한지 (가까우면 큼)  ·  r: 변수별 눈금 ℓ_d로 잰 거리  ·  ℓ_d가 작으면 그 변수에 민감", RX, y0 + 2.98 + h2 + 0.03, W, 0.4);
  lbl(s, "학습  —  하이퍼파라미터 결정", RX, y0 + 4.1, W);
  const h4 = eq(s, "eq4", RX + 0.1, y0 + 4.38, 0.6);
  cap(s, "앞 항: 데이터에 잘 맞는지  ·  가운데 항: 너무 복잡하지 않은지 → σ_f, ℓ₁~ℓ₈, σ_n을 이 값이 최대가 되도록 결정", RX, y0 + 4.38 + h4 + 0.03, W, 0.4);

  s.addNotes("가우시안 프로세스 회귀는 해석 결과를 매끄러운 함수와 작은 수치 오차의 합으로 봅니다. 두 설계가 얼마나 비슷한지는 Matern 커널로 계산하는데, 변수마다 길이척도를 따로 두어 민감한 변수는 짧게, 둔감한 변수는 길게 학습합니다. 이 하이퍼파라미터들은 확보한 해석 데이터가 나올 가능성, 즉 우도가 최대가 되도록 자동으로 정합니다. 예측값은 해석한 80점 결과의 가중평균이고 가까운 점일수록 가중치가 크며, 불확실성은 해석점에서 멀어질수록 커집니다.");
}
pres.writeFile({ fileName: __dirname + "/GPR_장표.pptx" }).then(f => console.log("생성 완료:", f));
