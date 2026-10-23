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


/* ═════════════════════════ 2개월차 ═════════════════════════ */
const fs = require("fs");
const DATA = JSON.parse(fs.readFileSync((process.env.M2DATA || __dirname + "/2개월차_데이터.json"), "utf-8"));
pres.title = "형상 생성부터 설계최적화까지 — 2개월차";

const VL = {
  input_thick: "입구 유로 두께", input_angle: "입구 각도", power_input_thick: "분기 입구 두께",
  mid_thick: "중간 유로 두께", mid_angle: "중간 각도", mid_input_thick: "중간 입구 두께",
  output_thick: "출구 유로 두께", fin_thick_1: "1차 핀 두께", fin_count_1: "1차 핀 개수",
  fin_thick_2: "2차 핀 두께", fin_count_2: "2차 핀 개수"
};
const RL = {
  pressure_drop: "차압", temp_std: "온도편차", max_temp: "최고온도",
  std_pass1: "1차 균일도", std_pass2: "2차 균일도", power_module_flow: "분기비", weight: "중량"
};
const SEC1 = "설계공간 재정의 및 변수 선별";
const SEC2 = "머신러닝 대리모델 구축";
const SEC3 = "정확도 검증 및 지배 변수 식별";

function hexMix(a, b, t) {
  const pa = [0, 2, 4].map(i => parseInt(a.substr(i, 2), 16));
  const pb = [0, 2, 4].map(i => parseInt(b.substr(i, 2), 16));
  return pa.map((v, i) => Math.round(v + (pb[i] - v) * t).toString(16).padStart(2, "0")).join("").toUpperCase();
}
function chip(s, x, y, w, h, t, fill, color, fs = 10, bold = true) {
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.07, fill: { color: fill }, line: { color: fill === "FFFFFF" ? LINE : fill, width: 0.75 } });
  s.addText(t, { x, y, w, h, fontSize: fs, bold, color, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.05 });
}
function downArrow(s, cx, y, h, color = MUTED) {
  s.addShape(pres.ShapeType.line, { x: cx, y, w: 0, h, line: { color, width: 1.25, endArrowType: "triangle" } });
}

/* ─────────────────────────── 1. 표지 ─────────────────────────── */
{
  const s = pres.addSlide();
  s.background = { color: NAVY };
  s.addShape(pres.ShapeType.ellipse, { x: 9.7, y: -1.6, w: 5.4, h: 5.4, fill: { color: NAVY2, transparency: 55 }, line: { color: NAVY2, transparency: 100 } });
  s.addShape(pres.ShapeType.ellipse, { x: 11.2, y: 4.3, w: 3.4, h: 3.4, fill: { color: ACCENT, transparency: 78 }, line: { color: ACCENT, transparency: 100 } });
  s.addText("학습조직", { x: M + 0.3, y: 1.42, w: 8, h: 0.32, fontSize: 12, bold: true, color: ACCENT, fontFace: F, isTextBox: true, margin: 0, charSpacing: 2 });
  s.addText("형상 생성부터\n설계최적화까지", { x: M + 0.3, y: 1.88, w: 9.2, h: 1.9, fontSize: 40, bold: true, color: "FFFFFF", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.12 });
  s.addText("AI 기반 형상·해석 자동화 연계 설계최적화", { x: M + 0.3, y: 3.86, w: 9, h: 0.4, fontSize: 16, bold: true, color: ICE, fontFace: F, isTextBox: true, margin: 0 });
  s.addText("수냉식 냉각판 유로·방열핀 설계 사례", { x: M + 0.3, y: 4.26, w: 9, h: 0.32, fontSize: 12, color: ICE, fontFace: F, isTextBox: true, margin: 0 });
  // 월별 범위 — 매월 이 줄만 교체
  s.addShape(pres.ShapeType.roundRect, { x: M + 0.3, y: 4.92, w: 6.6, h: 0.62, rectRadius: 0.08, fill: { color: NAVY2 }, line: { color: NAVY2 } });
  s.addText("2개월차   |   변수 선별 및 대리모델 구축", { x: M + 0.3, y: 4.92, w: 6.6, h: 0.62, fontSize: 13, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  s.addText("소속 / 성명 / 발표일자", { x: M + 0.3, y: 5.9, w: 8, h: 0.32, fontSize: 12, color: ICE, fontFace: F, isTextBox: true, margin: 0 });
  s.addNotes("2개월차 산출물 발표. 1개월차에 구축한 자동해석 환경 위에서, 영향이 있는 설계변수를 먼저 선별하고 그 변수들로 머신러닝 대리모델을 구축한 과정을 다룬다.");
}

/* ─────────────────────────── 2. 목차 ─────────────────────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  s.addText("목   차", { x: M, y: 0.55, w: 6, h: 0.5, fontSize: 26, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0, charSpacing: 3 });
  const items = [
    ["01", SEC1, "1.  후보 설계변수 정의\n2.  선별 실험(DSD) 설계\n3.  선별 결과 및 활성 변수 확정"],
    ["02", SEC2, "1.  활성 변수 실험계획(OLHD)\n2.  가우시안 프로세스 회귀(GPR)\n3.  코드 구성 갱신"],
    ["03", SEC3, "1.  예측값 · 실측값 비교\n2.  지배 변수 교차 확인\n3.  한계 및 차월 계획"]
  ];
  let y = 1.62;
  items.forEach(([no, t, sub]) => {
    const h = 1.62;
    card(s, M, y, 12.23, h);
    s.addText(no, { x: M + 0.35, y: y + 0.34, w: 1.3, h: 0.95, fontSize: 44, bold: true, color: ICE, fontFace: F, isTextBox: true, margin: 0, align: "center" });
    s.addText(t, { x: M + 1.85, y: y + 0.28, w: 4.5, h: 1.05, fontSize: 15.5, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0, valign: "middle", lineSpacingMultiple: 1.2 });
    s.addShape(pres.ShapeType.rect, { x: M + 6.55, y: y + 0.34, w: 0.02, h: h - 0.68, fill: { color: LINE }, line: { color: LINE } });
    s.addText(sub, { x: M + 6.95, y: y + 0.3, w: 5.0, h: h - 0.6, fontSize: 11, color: TXT, fontFace: F, isTextBox: true, margin: 0, valign: "middle", lineSpacingMultiple: 1.45 });
    y += h + 0.22;
  });
  s.addNotes("01은 어떤 변수가 실제로 영향을 주는지 먼저 걸러낸 과정, 02는 남은 변수로 대리모델을 만든 과정, 03은 그 모델이 얼마나 정확한지와 어떤 변수가 성능을 좌우하는지 확인한 결과다.");
}

/* ───────────── 3. [01] 후보 설계변수 정의 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "01", SEC1, "후보 설계변수 정의");
  const y0 = 1.30, ch = 4.55;

  // 좌 — 핀을 통과별로 나눈 이유
  card(s, M, y0, CW, ch);
  cardTitle(s, M, y0, "핀을 통과별로 나눈 이유");
  const cx = M + CW / 2;
  chip(s, cx - 1.5, y0 + 0.78, 3.0, 0.4, "입구  ·  총 유량 4 LPM", "EEF2F7", NAVY, 10);
  downArrow(s, cx, y0 + 1.18, 0.2);
  chip(s, cx - 1.5, y0 + 1.38, 3.0, 0.42, "1차 통과  —  총 유량 전체", NAVY, "FFFFFF", 10);
  downArrow(s, cx, y0 + 1.80, 0.2);
  chip(s, cx - 0.75, y0 + 2.0, 1.5, 0.36, "분  기", ACCENT, "FFFFFF", 10);
  s.addShape(pres.ShapeType.line, { x: M + 1.62, y: y0 + 2.36, w: 2.72, h: 0, line: { color: MUTED, width: 1.25 } });
  downArrow(s, M + 1.62, y0 + 2.36, 0.2);
  downArrow(s, M + 4.34, y0 + 2.36, 0.2);
  chip(s, M + 0.37, y0 + 2.56, 2.5, 0.42, "전원공급모듈", "FFFFFF", NAVY, 10);
  chip(s, M + 3.09, y0 + 2.56, 2.5, 0.42, "2차 통과  —  분기 후 잔여 유량", NAVY, "FFFFFF", 9.5);
  s.addText("통과마다 지나는 유량이 달라, 핀 하나의 조건으로\n1차 · 2차 통과를 동시에 맞출 수 없음",
    { x: M + 0.34, y: y0 + 3.08, w: 5.3, h: 0.56, fontSize: 9.8, color: TXT, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });
  s.addShape(pres.ShapeType.roundRect, { x: M + 0.34, y: y0 + 3.76, w: 5.3, h: 0.54, rectRadius: 0.06, fill: { color: NAVY }, line: { color: NAVY } });
  s.addText("→  핀 두께 · 개수를 1차 · 2차 통과별로 독립 변수화", { x: M + 0.34, y: y0 + 3.76, w: 5.3, h: 0.54, fontSize: 11.5, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

  // 우 — 후보 설계변수 11개
  card(s, CX2, y0, CW, ch);
  cardTitle(s, CX2, y0, "후보 설계변수  —  11개");
  const grp = (t, n) => ({ text: t, options: { rowspan: n, bold: true, color: NAVY, fill: { color: "F7F9FC" }, valign: "middle", align: "center" } });
  const fin = (t) => ({ text: t, options: { bold: true, color: NAVY } });
  tbl(s, CX2 + 0.34, y0 + 0.72, 5.3, [
    [hdr("구분"), hdr("설계변수"), hdr("범위")],
    [grp("유로 형상\n(7)", 7), "입구 유로 두께", "13 ~ 25 mm"],
    ["입구 각도", "90 ~ 150 °"],
    ["분기 입구 두께", "3 ~ 10 mm"],
    ["중간 유로 두께", "10 ~ 25 mm"],
    ["중간 각도", "90 ~ 140 °"],
    ["중간 입구 두께", "10 ~ 25 mm"],
    ["출구 유로 두께", "13 ~ 35 mm"],
    [grp("1차 통과 핀\n(2)", 2), fin("1차 핀 두께"), fin("1.5 ~ 3.0 mm")],
    [fin("1차 핀 개수"), fin("10 ~ 24 개")],
    [grp("2차 통과 핀\n(2)", 2), fin("2차 핀 두께"), fin("1.5 ~ 3.0 mm")],
    [fin("2차 핀 개수"), fin("10 ~ 24 개")]
  ], [1.3, 2.2, 1.8], { rowH: 0.262, fontSize: 9.3 });
  s.addText("핀 갭은 두께 · 개수로 정해지는 종속값 — 최소 2.0 mm (제작 한계 2.5 mm는 최적화 단계 제약으로 적용)",
    { x: CX2 + 0.34, y: y0 + 4.0, w: 5.3, h: 0.4, fontSize: 8.6, color: MUTED, italic: true, fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.15 });

  bottomStrip(s, [
    ["후보 11개", "유로 형상 7 + 통과별 핀 두께 · 개수 4"],
    ["핀 통과별 독립", "1·2차 통과 유량 차이를 설계에 반영"],
    ["11차원 설계공간", "바로 대리모델을 만들기엔 차원이 큼 → 선별 필요"]
  ]);
  s.addNotes("냉각유는 1차 통과를 지난 뒤 분기에서 전원공급모듈 쪽으로 일부가 빠지기 때문에, 2차 통과는 1차 통과보다 적은 유량이 흐른다. 핀을 하나의 변수로 공유하면 한쪽 통과에 맞추는 순간 다른 쪽이 불리해지므로, 핀 두께와 개수를 통과별로 따로 두어 후보 변수는 11개가 된다. 11차원은 대리모델을 바로 만들기에 큰 공간이라, 먼저 영향이 있는 변수를 선별한다.");
}

/* ───────────── 4. [01] 선별 실험(DSD) 설계 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "01", SEC1, "선별 실험(DSD) 설계");
  const y0 = 1.30, ch = 5.55;

  // 좌 — 왜 선별부터
  card(s, M, y0, CW, ch);
  cardTitle(s, M, y0, "왜 선별부터 하는가");
  const why = [
    ["영향 없는 변수를 근거 있게 고정", "감이 아니라 통계 판정으로 고정 여부 결정"],
    ["대리모델 차원 축소", "같은 해석 횟수로 설계공간을 더 촘촘하게"],
    ["변수 영향도를 바로 확인", "실험 설계 단계에서 지배 변수 파악"]
  ];
  why.forEach(([h, d], i) => {
    const yy = y0 + 0.78 + i * 0.62;
    s.addShape(pres.ShapeType.ellipse, { x: M + 0.36, y: yy + 0.08, w: 0.32, h: 0.32, fill: { color: NAVY }, line: { color: NAVY } });
    s.addText(String(i + 1), { x: M + 0.36, y: yy + 0.08, w: 0.32, h: 0.32, fontSize: 10, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(h, { x: M + 0.82, y: yy, w: 4.8, h: 0.27, fontSize: 10.5, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0, valign: "middle" });
    s.addText(d, { x: M + 0.82, y: yy + 0.27, w: 4.8, h: 0.24, fontSize: 9.3, color: MUTED, fontFace: F, isTextBox: true, margin: 0, valign: "middle" });
  });

  s.addText("판정 규칙 — 실험 전에 고정", { x: M + 0.34, y: y0 + 2.75, w: 5.3, h: 0.3, fontSize: 11, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0 });
  tbl(s, M + 0.34, y0 + 3.10, 5.3, [
    [hdr("조건"), hdr("기준"), hdr("의미")],
    ["통계적 구분", { text: "p ≤ 0.05", options: { bold: true, color: NAVY } }, "가짜 인자(잡음 바닥)와 구분되는가"],
    ["실무적 의미", { text: "기여율 ≥ 2%", options: { bold: true, color: NAVY } }, "응답 변동의 2% 이상을 설명하는가"]
  ], [1.25, 1.25, 2.8], { rowH: 0.34 });
  s.addShape(pres.ShapeType.roundRect, { x: M + 0.34, y: y0 + 4.26, w: 5.3, h: 0.98, rectRadius: 0.06, fill: { color: "EEF2F7" }, line: { color: "EEF2F7" } });
  s.addText([
    { text: "두 조건을 모두 만족해야 '영향 있음'", options: { bold: true, color: NAVY, breakLine: true } },
    { text: "응답 7개 어디에서도 영향이 없으면 → 그 변수는 고정", options: { color: TXT, breakLine: true } },
    { text: "결과를 본 뒤 기준을 바꾸지 않도록 실험 전에 확정", options: { color: MUTED } }
  ], { x: M + 0.5, y: y0 + 4.26, w: 5.0, h: 0.98, fontSize: 9.5, valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });

  // 우 — 실험표 구조
  card(s, CX2, y0, CW, ch);
  cardTitle(s, CX2, y0, "실험표 구조  —  29회 × 14열");
  const L = DATA.plan.L, nC = L[0].length, nR = L.length;
  const gx = CX2 + 1.32, gy = y0 + 1.12, cw = 0.29, rh = 0.094;
  const colR = { "-1": "E4EBF3", "0": "8FB0D4", "1": NAVY };
  const colF = { "-1": "E2F4F8", "0": "8DD2E2", "1": "0090B0" };
  // 열 그룹 라벨
  s.addText("실제 변수 11개", { x: gx, y: y0 + 0.74, w: 11 * cw, h: 0.24, fontSize: 9, bold: true, color: NAVY, align: "center", fontFace: F, isTextBox: true, margin: 0 });
  s.addText("가짜 인자 3개", { x: gx + 11 * cw, y: y0 + 0.74, w: 3 * cw + 0.3, h: 0.24, fontSize: 9, bold: true, color: "0088A6", align: "center", fontFace: F, isTextBox: true, margin: 0 });
  s.addShape(pres.ShapeType.line, { x: gx, y: y0 + 1.0, w: 11 * cw - 0.03, h: 0, line: { color: NAVY, width: 1 } });
  s.addShape(pres.ShapeType.line, { x: gx + 11 * cw + 0.03, y: y0 + 1.0, w: 3 * cw - 0.03, h: 0, line: { color: ACCENT, width: 1 } });
  for (let r = 0; r < nR; r++) {
    for (let c = 0; c < nC; c++) {
      const v = String(L[r][c]);
      const fake = c >= 11;
      const gap = r >= 14 ? 0.05 : 0, gap2 = r >= 28 ? 0.05 : 0;
      s.addShape(pres.ShapeType.rect, {
        x: gx + c * cw, y: gy + r * rh + gap + gap2, w: cw - 0.025, h: rh - 0.018,
        fill: { color: fake ? colF[v] : colR[v] }, line: { color: fake ? colF[v] : colR[v], width: 0 }
      });
    }
  }
  // 행 그룹 라벨
  const grp = [["기본 14회", 0, 14, 0], ["거울상 14회", 14, 28, 0.05], ["중심점 1회", 28, 29, 0.10]];
  grp.forEach(([t, a, b, off]) => {
    const yy = gy + a * rh + off, hh = (b - a) * rh;
    s.addShape(pres.ShapeType.line, { x: gx - 0.1, y: yy + 0.01, w: 0, h: hh - 0.03, line: { color: MUTED, width: 1 } });
    s.addText(t, { x: CX2 + 0.26, y: yy + hh / 2 - 0.13, w: 0.95, h: 0.26, fontSize: 8.5, bold: true, color: NAVY, align: "right", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });
  // 범례
  const ly = gy + 29 * rh + 0.18;
  [["하한", "E4EBF3"], ["중간", "8FB0D4"], ["상한", NAVY]].forEach(([t, c], i) => {
    const x = gx + i * 1.05;
    s.addShape(pres.ShapeType.rect, { x, y: ly + 0.05, w: 0.2, h: 0.14, fill: { color: c }, line: { color: c } });
    s.addText(t, { x: x + 0.26, y: ly, w: 0.7, h: 0.24, fontSize: 8.5, color: TXT, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });
  s.addText([
    { text: "각 행: 변수 1개만 중간값, 나머지는 하한·상한 → 곡률(중간값이 나은지)까지 확인", options: { bullet: true, breakLine: true } },
    { text: "거울상: 부호를 뒤집은 쌍 → 주효과가 2변수 상호작용과 섞이지 않음", options: { bullet: true, breakLine: true } },
    { text: "가짜 인자: 어떤 치수와도 연결하지 않은 빈 열 → '효과 없음' 기준선", options: { bullet: true } }
  ], { x: CX2 + 0.34, y: ly + 0.32, w: 5.3, h: 0.9, fontSize: 8.6, color: TXT, fontFace: F, isTextBox: true, margin: 0, paraSpaceAfter: 3, lineSpacingMultiple: 1.1 });

  s.addNotes("후보 11개를 바로 대리모델 실험에 넣지 않고, 먼저 확정적 선별 설계(DSD) 29회로 영향이 있는 변수를 골랐다. 실험표는 변수 하나만 중간값에 두고 나머지를 상하한에 두는 행 14개와 그 거울상 14개, 중심점 1개로 구성된다. 가짜 인자 3열은 실제로는 효과가 0이어야 하므로 판정의 기준선이 된다. 판정 규칙은 결과를 보기 전에 고정했다.");
}

/* ───────────── 5. [01] 선별 결과 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "01", SEC1, "선별 결과 및 활성 변수 확정");
  const y0 = 1.30, ch = 4.55;
  card(s, M, y0, 12.23, ch);
  cardTitle(s, M, y0, "변수별 분산 기여율 (%)  —  DSD 29회");
  const { vars, resp, share, sig } = DATA.dsd;
  const fixedTxt = { input_angle: "고정  →  150°", mid_angle: "고정  →  115°", output_thick: "고정  →  35 mm" };
  const rows = [[hdr("설계변수"), ...resp.map(r => ({ text: RL[r], options: { bold: true, color: NAVY, fill: { color: "EEF2F7" }, align: "center" } })), { text: "판정", options: { bold: true, color: NAVY, fill: { color: "EEF2F7" }, align: "center" } }]];
  vars.forEach(v => {
    const fixed = !!fixedTxt[v];
    const row = [{ text: VL[v], options: { bold: true, color: fixed ? MUTED : NAVY, fill: { color: fixed ? "F3F5F8" : "FFFFFF" } } }];
    resp.forEach(r => {
      const val = share[v][r], ok = sig[v][r];
      if (ok) {
        const t = Math.min(val / 55, 1);
        const fill = hexMix("D3E7F1", "16305B", t);
        row.push({ text: val.toFixed(1), options: { bold: true, color: t > 0.42 ? "FFFFFF" : NAVY, fill: { color: fill }, align: "center" } });
      } else {
        row.push({ text: val.toFixed(1), options: { color: "A9B3C1", fill: { color: fixed ? "F3F5F8" : "FFFFFF" }, align: "center" } });
      }
    });
    row.push(fixed
      ? { text: fixedTxt[v], options: { bold: true, color: "0088A6", fill: { color: "E8F6FA" }, align: "center" } }
      : { text: "활성", options: { bold: true, color: NAVY, align: "center" } });
    rows.push(row);
  });
  s.addTable(rows, {
    x: M + 0.34, y: y0 + 0.68, w: 11.55, colW: [1.75, ...resp.map(() => 1.15), 1.75],
    fontSize: 9.5, fontFace: F, color: TXT, rowH: 0.285, valign: "middle", margin: [1, 4, 1, 4],
    border: [{ pt: 0.5, color: "FFFFFF" }, { pt: 0.5, color: "FFFFFF" }, { pt: 0.5, color: LINE }, { pt: 0.5, color: "FFFFFF" }]
  });
  s.addText("색 칸 = 영향 인정 (p ≤ 0.05 그리고 기여율 ≥ 2%)  ·  회색 숫자 = 영향 없음  ·  고정값: 유의한 목적함수가 유리한 끝값, 없으면 범위 중앙",
    { x: M + 0.34, y: y0 + 4.18, w: 11.55, h: 0.26, fontSize: 8.8, color: MUTED, italic: true, fontFace: F, isTextBox: true, margin: 0 });

  bottomStrip(s, [
    ["1차 핀 개수", "차압 56% · 최고온도 52% · 1차 균일도 52%"],
    ["2차 핀 개수", "온도편차 37% · 2차 균일도 51%"],
    ["분기 입구 두께", "분기비 84% — 분기 유량을 사실상 결정"]
  ]);
  s.addNotes("11개 중 8개가 활성, 3개(입구 각도, 중간 각도, 출구 유로 두께)는 어떤 응답에서도 기준을 넘지 못해 고정했다. 가장 눈여겨볼 점은 1차 핀 개수가 1차 균일도를, 2차 핀 개수가 2차 균일도를 각각 지배한다는 것이다. 핀을 통과별로 나눈 판단이 데이터로 뒷받침된다.");
}

/* ───────────── 6. [02] 활성 변수 실험계획(OLHD) ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "02", SEC2, "활성 변수 실험계획 (OLHD)");
  const y0 = 1.30, ch = 5.55;
  const o = DATA.olhd;

  card(s, M, y0, CW, ch);
  cardTitle(s, M, y0, "실험점 분포  —  80점");
  const sc = (x, y, title, xl, yl, xr, yr, px) => {
    s.addText(title, { x: px, y: y0 + 0.74, w: 2.75, h: 0.26, fontSize: 9.5, bold: true, color: NAVY, align: "center", fontFace: F, isTextBox: true, margin: 0 });
    s.addChart(pres.ChartType.scatter, [{ name: xl, values: x }, { name: yl, values: y }], {
      x: px, y: y0 + 1.0, w: 2.75, h: 3.1, lineSize: 0, lineDataSymbol: "circle", lineDataSymbolSize: 5,
      chartColors: [NAVY], showLegend: false,
      valAxisMinVal: yr[0], valAxisMaxVal: yr[1], catAxisMinVal: xr[0], catAxisMaxVal: xr[1],
      showValAxisTitle: true, valAxisTitle: yl, valAxisTitleFontSize: 8, valAxisTitleColor: MUTED,
      showCatAxisTitle: true, catAxisTitle: xl, catAxisTitleFontSize: 8, catAxisTitleColor: MUTED,
      valAxisLabelFontSize: 7.5, catAxisLabelFontSize: 7.5, valAxisLabelColor: MUTED, catAxisLabelColor: MUTED,
      valGridLine: { color: "E6EBF1", size: 0.5 }, catGridLine: { color: "E6EBF1", size: 0.5 }
    });
  };
  sc(o.fin_count_1, o.fin_thick_1, "1차 핀 개수 × 두께", "1차 핀 개수 [개]", "1차 핀 두께 [mm]", [10, 24], [1.4, 3.1], M + 0.18);
  sc(o.input_thick, o.power_input_thick, "입구 유로 × 분기 입구 두께", "입구 유로 두께 [mm]", "분기 입구 두께 [mm]", [12, 26], [2, 11], M + 3.0);
  s.addText([
    { text: "왼쪽: 핀이 많을수록 가능한 두께가 줄어드는 가공 제약 영역 안에 분포", options: { bullet: true, breakLine: true } },
    { text: "오른쪽: 제약이 없는 변수 쌍은 설계공간 전체에 고르게 분포", options: { bullet: true } }
  ], { x: M + 0.34, y: y0 + 4.32, w: 5.3, h: 0.9, fontSize: 9, color: TXT, fontFace: F, isTextBox: true, margin: 0, paraSpaceAfter: 4, lineSpacingMultiple: 1.15 });

  card(s, CX2, y0, CW, ch);
  cardTitle(s, CX2, y0, "실험계획 요약");
  [["8", "활성 변수"], ["80", "실험점 (10 × 8)"], ["3", "고정 변수"]].forEach(([v, l], i) => {
    const x = CX2 + 0.34 + i * 1.8;
    s.addShape(pres.ShapeType.roundRect, { x, y: y0 + 0.76, w: 1.62, h: 1.0, rectRadius: 0.07, fill: { color: i === 1 ? NAVY : "EEF2F7" }, line: { color: i === 1 ? NAVY : "EEF2F7" } });
    s.addText(v, { x, y: y0 + 0.8, w: 1.62, h: 0.58, fontSize: 26, bold: true, color: i === 1 ? "FFFFFF" : NAVY, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(l, { x, y: y0 + 1.38, w: 1.62, h: 0.3, fontSize: 9, color: i === 1 ? ICE : MUTED, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });
  tbl(s, CX2 + 0.34, y0 + 1.98, 5.3, [
    [hdr("구분"), hdr("내용")],
    ["활성 변수", "입구 유로 · 분기 입구 · 중간 유로 · 중간 입구 두께\n1차 · 2차 핀 두께 · 개수"],
    ["고정 변수", "입구 각도 150° · 중간 각도 115° · 출구 유로 35 mm"],
    ["실험계획법", "최적라틴방격법(OLHD) — 적은 점으로 균일 분포"]
  ], [1.2, 4.1], { rowH: 0.36 });
  s.addShape(pres.ShapeType.roundRect, { x: CX2 + 0.34, y: y0 + 3.92, w: 5.3, h: 1.3, rectRadius: 0.06, fill: { color: "E8F6FA" }, line: { color: ACCENT, width: 0.75 } });
  s.addText([
    { text: "핀 개수를 먼저 고르게 배치", options: { bold: true, color: NAVY, breakLine: true } },
    { text: "핀 개수가 지배 변수로 확인되어 10~24개 전 범위에 고르게 배치하고, 두께는 그 개수에서 가능한 범위로 맞춤", options: { color: TXT, breakLine: true } },
    { text: "두께를 먼저 뽑으면 22~24개 구간이 80점 중 1~2점에 그침", options: { color: MUTED } }
  ], { x: CX2 + 0.5, y: y0 + 3.92, w: 5.0, h: 1.3, fontSize: 9.3, valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2, paraSpaceAfter: 2 });
  s.addNotes("선별에서 남은 8개 변수로 최적라틴방격법 80점을 해석했다. 핀 개수가 가장 큰 영향을 주는 변수로 확인됐기 때문에, 개수를 10~24개 전 범위에 고르게 먼저 배치하고 두께는 그 개수에서 만들 수 있는 범위로 맞췄다.");
}

/* ───────────── 7. [02] GPR ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "02", SEC2, "가우시안 프로세스 회귀 (GPR)");
  const y0 = 1.30, ch = 5.55;

  card(s, M, y0, CW, ch);
  cardTitle(s, M, y0, "개념  —  예측값과 불확실성을 함께 제공");
  const g = DATA.gp1d;
  const PX = M + 0.55, PY = y0 + 0.95, PW = 4.9, PH = 2.75;
  const ups = g.m.map((m, i) => m + 2 * g.sd[i]), los = g.m.map((m, i) => m - 2 * g.sd[i]);
  const yMin = Math.min(...los) - 0.1, yMax = Math.max(...ups) + 0.1;
  const tx = (x) => x * PW, ty = (y) => (yMax - y) / (yMax - yMin) * PH;
  s.addShape(pres.ShapeType.rect, { x: PX, y: PY, w: PW, h: PH, fill: { color: "FAFBFD" }, line: { color: LINE, width: 0.75 } });
  const band = g.x.map((x, i) => ({ x: tx(x), y: ty(ups[i]) })).concat(g.x.slice().reverse().map((x, j) => {
    const i = g.x.length - 1 - j; return { x: tx(x), y: ty(los[i]) };
  }));
  band.push({ close: true });
  s.addShape(pres.ShapeType.custGeom, { x: PX, y: PY, w: PW, h: PH, points: band, fill: { color: ACCENT, transparency: 72 }, line: { color: ACCENT, transparency: 100 } });
  s.addShape(pres.ShapeType.custGeom, { x: PX, y: PY, w: PW, h: PH, points: g.x.map((x, i) => ({ x: tx(x), y: ty(g.m[i]) })), line: { color: NAVY, width: 2 } });
  g.xt.forEach((x, i) => {
    s.addShape(pres.ShapeType.ellipse, { x: PX + tx(x) - 0.07, y: PY + ty(g.yt[i]) - 0.07, w: 0.14, h: 0.14, fill: { color: "FFFFFF" }, line: { color: NAVY, width: 1.5 } });
  });
  s.addText("해석점 사이가 멀수록\n불확실성이 커짐", { x: PX + tx(0.56), y: PY + 0.1, w: 1.6, h: 0.44, fontSize: 8.5, bold: true, color: "0088A6", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.1 });
  s.addText("설계변수", { x: PX, y: PY + PH + 0.04, w: PW, h: 0.22, fontSize: 8.5, color: MUTED, align: "center", fontFace: F, isTextBox: true, margin: 0 });
  // 범례
  const ly = y0 + 4.12;
  s.addShape(pres.ShapeType.ellipse, { x: M + 0.55, y: ly + 0.05, w: 0.13, h: 0.13, fill: { color: "FFFFFF" }, line: { color: NAVY, width: 1.5 } });
  s.addText("해석 결과 (학습 데이터)", { x: M + 0.75, y: ly, w: 1.7, h: 0.24, fontSize: 8.5, color: TXT, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  s.addShape(pres.ShapeType.line, { x: M + 2.45, y: ly + 0.12, w: 0.3, h: 0, line: { color: NAVY, width: 2 } });
  s.addText("예측 평균", { x: M + 2.82, y: ly, w: 0.9, h: 0.24, fontSize: 8.5, color: TXT, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  s.addShape(pres.ShapeType.rect, { x: M + 3.7, y: ly + 0.04, w: 0.3, h: 0.16, fill: { color: ACCENT, transparency: 72 }, line: { color: ACCENT, transparency: 100 } });
  s.addText("불확실성 (±2σ)", { x: M + 4.07, y: ly, w: 1.3, h: 0.24, fontSize: 8.5, color: TXT, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  s.addShape(pres.ShapeType.roundRect, { x: M + 0.34, y: y0 + 4.52, w: 5.3, h: 0.72, rectRadius: 0.06, fill: { color: "EEF2F7" }, line: { color: "EEF2F7" } });
  s.addText("해석 없이도 임의의 설계에 대해 성능을 수 초 안에 예측하고,\n그 예측을 얼마나 믿을 수 있는지까지 함께 알려줌", { x: M + 0.5, y: y0 + 4.52, w: 5.0, h: 0.72, fontSize: 9.5, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });

  card(s, CX2, y0, CW, ch);
  cardTitle(s, CX2, y0, "GPR을 택한 이유");
  const why = [
    ["예측값 + 불확실성", "예측과 함께 신뢰 구간을 제공"],
    ["적은 데이터로 학습", "해석 수십 ~ 수백 점 규모에 적합"],
    ["변수 중요도 산출", "변수별 길이척도(ARD)로 영향도 확인"],
    ["추가 해석 위치 선정", "불확실성이 큰 곳을 다음 해석 후보로 (차월)"]
  ];
  why.forEach(([h, d], i) => {
    const yy = y0 + 0.74 + i * 0.5;
    s.addShape(pres.ShapeType.rect, { x: CX2 + 0.36, y: yy + 0.1, w: 0.07, h: 0.26, fill: { color: i === 3 ? ACCENT : NAVY }, line: { color: i === 3 ? ACCENT : NAVY } });
    s.addText(h, { x: CX2 + 0.55, y: yy, w: 1.85, h: 0.46, fontSize: 10, bold: true, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(d, { x: CX2 + 2.4, y: yy, w: 3.25, h: 0.46, fontSize: 9.3, color: TXT, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });
  s.addText("학습 구성", { x: CX2 + 0.34, y: y0 + 2.86, w: 5.3, h: 0.3, fontSize: 11, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0 });
  tbl(s, CX2 + 0.34, y0 + 3.2, 5.3, [
    [hdr("항목"), hdr("내용")],
    ["입력", "활성 변수 8개 (0 ~ 1 정규화)"],
    ["출력", "응답 7개 → 응답별 모델 1개\n(목적함수 5 + 제약조건 2)"],
    ["커널", "Matern(ν = 2.5) + 변수별 길이척도(ARD)"],
    ["전처리", "차압은 로그 변환 (값의 범위가 넓음)"]
  ], [1.2, 4.1], { rowH: 0.36 });
  s.addNotes("GPR은 해석 결과를 학습해 임의의 설계에 대한 성능을 예측하는 모델이다. 다른 회귀 모델과 달리 예측값과 함께 불확실성을 준다. 해석점이 촘촘한 곳은 불확실성이 작고, 해석점 사이가 먼 곳은 커진다. 이 불확실성은 차월에 어디를 추가로 해석할지 정하는 데 쓴다.");
}

/* ───────────── 8. [02] 코드 구성 갱신 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "02", SEC2, "코드 구성");
  const y0 = 1.30, ch = 4.55;
  card(s, M, y0, 12.23, ch);
  cardTitle(s, M, y0, "모듈 구성 및 실행 흐름  —  선별 단계 · 학습 모듈 추가");
  const X0 = M + 0.34, WALL = 11.55;
  const mY = y0 + 0.72, mH = 0.56;
  s.addShape(pres.ShapeType.roundRect, { x: X0, y: mY, w: WALL, h: mH, rectRadius: 0.07, fill: { color: NAVY }, line: { color: NAVY } });
  s.addText([{ text: "main.py", options: { fontFace: MONO, bold: true, fontSize: 12.5 } },
             { text: "     단계 관리  —  선별 29회 → 판정 확인 → 실험계획 80점, 실험점마다 아래 단계를 순서대로 호출", options: { fontSize: 10, color: ICE } }],
    { x: X0 + 0.25, y: mY, w: WALL - 2.1, h: mH, color: "FFFFFF", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  s.addShape(pres.ShapeType.roundRect, { x: X0 + WALL - 1.65, y: mY + 0.11, w: 1.45, h: mH - 0.22, rectRadius: 0.1, fill: { color: ACCENT }, line: { color: ACCENT } });
  s.addText("2단계 운영", { x: X0 + WALL - 1.65, y: mY + 0.11, w: 1.45, h: mH - 0.22, fontSize: 9.5, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

  const mods = [
    ["실험점 생성", "DSD.py · OLHD.py", "선별 실험표 29회\n활성 변수 80점", true],
    ["형상 빌드", "Solidworks.py", "전역변수 11개 갱신\n→ 리빌드 · STEP", false],
    ["해석", "icepak.py", "해석 모델 구성\n→ 결과 추출", false],
    ["결과 저장", "result_parser.py", "응답 7개 산출\n결과 누적", false],
    ["선별 · 학습", "DSD_analysis.py\nML.py", "선별 판정\nGPR 모델 7개", true]
  ];
  const n = mods.length, cW = 2.05, cG = (WALL - n * cW) / (n - 1), cY = mY + mH + 0.34, cH = 1.42;
  const arts = ["설계값", "STEP", "CSV", "결과표"];
  mods.forEach(([h, f, d, isNew], i) => {
    const x = X0 + i * (cW + cG);
    s.addShape(pres.ShapeType.line, { x: x + cW / 2, y: mY + mH, w: 0, h: 0.34, line: { color: "9FB0C6", width: 1, endArrowType: "triangle" } });
    s.addShape(pres.ShapeType.roundRect, { x, y: cY, w: cW, h: cH, rectRadius: 0.07, fill: { color: "FFFFFF" }, line: { color: isNew ? ACCENT : "B9C7D8", width: isNew ? 1.5 : 1.25 }, shadow: sh() });
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.12, y: cY + 0.12, w: 0.28, h: 0.28, fill: { color: isNew ? ACCENT : NAVY }, line: { color: isNew ? ACCENT : NAVY } });
    s.addText(String(i + 1), { x: x + 0.12, y: cY + 0.12, w: 0.28, h: 0.28, fontSize: 9, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(h, { x: x + 0.46, y: cY + 0.1, w: cW - 0.5, h: 0.32, fontSize: 10.5, bold: true, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(f, { x: x + 0.12, y: cY + 0.48, w: cW - 0.2, h: 0.38, fontSize: 8.5, bold: true, color: isNew ? "0088A6" : NAVY2, fontFace: MONO, isTextBox: true, margin: 0, valign: "middle", lineSpacingMultiple: 1.0 });
    s.addText(d, { x: x + 0.12, y: cY + 0.88, w: cW - 0.2, h: 0.48, fontSize: 8.5, color: TXT, fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.1 });
    if (isNew) {
      s.addShape(pres.ShapeType.roundRect, { x: x + cW - 0.52, y: cY - 0.12, w: 0.48, h: 0.22, rectRadius: 0.08, fill: { color: ACCENT }, line: { color: ACCENT } });
      s.addText("NEW", { x: x + cW - 0.52, y: cY - 0.12, w: 0.48, h: 0.22, fontSize: 7.5, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    }
  });
  mods.slice(0, n - 1).forEach((_, i) => {
    const ax = X0 + i * (cW + cG) + cW;
    s.addShape(pres.ShapeType.line, { x: ax + 0.04, y: cY + cH / 2 + 0.08, w: cG - 0.08, h: 0, line: { color: ACCENT, width: 1.5, endArrowType: "triangle" } });
    s.addText(arts[i], { x: ax - 0.2, y: cY + cH / 2 - 0.2, w: cG + 0.4, h: 0.22, fontSize: 7, bold: true, color: "0088A6", align: "center", fontFace: F, isTextBox: true, margin: 0 });
  });
  const eY = cY + cH + 0.28, eH = 0.44;
  [["params.py · 변수 정의", "F7F9FC", NAVY, null],
   ["SolidWorks", "E4EAF2", NAVY, "COM API"],
   ["Ansys Icepak", "E4EAF2", NAVY, "PyAEDT"],
   ["결과 데이터셋", "F7F9FC", NAVY, null],
   ["활성 변수 · 대리모델", "E8F6FA", "0088A6", null]].forEach(([t, f, c, api], i) => {
    const x = X0 + i * (cW + cG);
    s.addShape(pres.ShapeType.line, { x: x + cW / 2, y: cY + cH, w: 0, h: 0.28, line: { color: api ? NAVY : "C3CDDA", width: 1, dashType: api ? "solid" : "dash", beginArrowType: api ? "triangle" : undefined, endArrowType: "triangle" } });
    if (api) s.addText(api, { x: x + cW / 2 + 0.07, y: cY + cH + 0.02, w: 1.0, h: 0.24, fontSize: 7.5, color: MUTED, fontFace: MONO, isTextBox: true, margin: 0, valign: "middle" });
    s.addShape(pres.ShapeType.roundRect, { x: x + 0.12, y: eY, w: cW - 0.24, h: eH, rectRadius: 0.08, fill: { color: f }, line: { color: api ? "B9C7D8" : (i === 4 ? ACCENT : LINE), width: 0.75, dashType: api ? "solid" : "dash" } });
    s.addText(t, { x: x + 0.12, y: eY, w: cW - 0.24, h: eH, fontSize: 8.8, bold: true, color: c, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });
  const pY = y0 + ch - 0.5;
  s.addShape(pres.ShapeType.line, { x: X0, y: pY - 0.08, w: WALL, h: 0, line: { color: LINE, width: 0.75 } });
  s.addText([{ text: "paths.py", options: { fontFace: MONO, bold: true, color: NAVY } },
             { text: "   경로 일원화      ", options: { color: MUTED } },
             { text: "responses.py", options: { fontFace: MONO, bold: true, color: NAVY } },
             { text: "   목적함수 · 제약조건 목록 일원화", options: { color: MUTED } }],
    { x: X0, y: pY, w: WALL, h: 0.3, fontSize: 9.3, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

  bottomStrip(s, [
    ["단계별 자동 진행", "선별이 끝나면 판정을 확인한 뒤 2단계로 진행"],
    ["판정 규칙 코드화", "사전 고정 규칙을 코드에 명시 — 임의 변경 차단"],
    ["자동해석 모듈 그대로 활용", "형상 · 해석 · 결과 모듈 위에 선별 · 학습 단계 추가"]
  ]);
  s.addNotes("자동해석 구조에 선별 실험표 생성(DSD.py)과 선별 판정·대리모델 학습(DSD_analysis.py, ML.py)을 추가했다. 형상 빌드, 해석, 결과 저장 모듈은 그대로 활용한다. 선별이 끝나면 프로그램이 멈추고 판정 결과를 사람이 확인한 뒤 2단계로 넘어간다.");
}

/* ───────────── 9. [03] 예측값 · 실측값 비교 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "03", SEC3, "예측값 · 실측값 비교  —  교차검증");
  const order = ["pressure_drop", "temp_std", "max_temp", "std_pass1", "std_pass2", "power_module_flow", "weight"];
  const fmt = { pressure_drop: "0", temp_std: "0.0", max_temp: "0", std_pass1: "0.00", std_pass2: "0.00", power_module_flow: "0.0", weight: "0.00" };
  const unit = { pressure_drop: "Pa", temp_std: "°C", max_temp: "°C", std_pass1: "LPM", std_pass2: "LPM", power_module_flow: "-", weight: "kg" };
  const W = 2.9, G = (12.23 - 4 * W) / 3, H = 2.55;
  order.forEach((rp, k) => {
    const r = Math.floor(k / 4), c = k % 4;
    const x = M + c * (W + G), y = 1.24 + r * (H + 0.16);
    const cv = DATA.cv[rp];
    const idx = cv.y.map((_, i) => i).sort((a, b) => cv.y[a] - cv.y[b]);
    const ys = idx.map(i => cv.y[i]), ps = idx.map(i => cv.p[i]);
    const step = { pressure_drop: 500, temp_std: 0.2, max_temp: 2, std_pass1: 0.02, std_pass2: 0.01, power_module_flow: 0.1, weight: 0.05 }[rp];
    const lo0 = Math.min(...ys, ...ps), hi0 = Math.max(...ys, ...ps);
    const lo = Math.floor(lo0 / step) * step, hi = Math.ceil(hi0 / step) * step, pad = 0;
    const weak = rp === "std_pass2";
    s.addShape(pres.ShapeType.roundRect, { x, y, w: W, h: H, rectRadius: 0.05, fill: { color: CARD }, line: { color: weak ? ACCENT : LINE, width: weak ? 1.25 : 0.75 }, shadow: sh() });
    s.addText([{ text: RL[rp], options: { bold: true, color: NAVY } }, { text: `  [${unit[rp]}]`, options: { color: MUTED, fontSize: 8 } }],
      { x: x + 0.14, y: y + 0.08, w: 1.7, h: 0.28, fontSize: 10, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(`R² ${cv.r2.toFixed(3)}`, { x: x + W - 1.15, y: y + 0.08, w: 1.0, h: 0.28, fontSize: 10, bold: true, color: weak ? "0088A6" : NAVY, align: "right", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addChart(pres.ChartType.scatter, [{ name: "실측", values: ys }, { name: "예측", values: ps }, { name: "실측=예측", values: ys }], {
      x: x + 0.04, y: y + 0.36, w: W - 0.08, h: H - 0.42, lineSize: 1, lineDataSymbol: "circle", lineDataSymbolSize: 4,
      chartColors: [weak ? "0090B0" : NAVY2, "C0392B"], showLegend: false,
      valAxisMinVal: lo, valAxisMaxVal: hi, catAxisMinVal: lo, catAxisMaxVal: hi, valAxisMajorUnit: step * (rp === 'weight' || rp === 'std_pass2' ? 1 : 2), catAxisMajorUnit: step * (rp === 'weight' || rp === 'std_pass2' ? 1 : 2), valAxisCrossesAt: lo, catAxisCrossesAt: lo,
      valAxisLabelFormatCode: fmt[rp], catAxisLabelFormatCode: fmt[rp],
      valAxisLabelFontSize: 7, catAxisLabelFontSize: 7, valAxisLabelColor: MUTED, catAxisLabelColor: MUTED,
      valGridLine: { color: "EEF1F5", size: 0.5 }, catGridLine: { style: "none" },
      showValAxisTitle: true, valAxisTitle: "예측", valAxisTitleFontSize: 7, valAxisTitleColor: MUTED,
      showCatAxisTitle: true, catAxisTitle: "실측", catAxisTitleFontSize: 7, catAxisTitleColor: MUTED
    });
  });
  // 8번째 칸 — 요약
  const x = M + 3 * (W + G), y = 1.24 + H + 0.16;
  s.addShape(pres.ShapeType.roundRect, { x, y, w: W, h: H, rectRadius: 0.05, fill: { color: NAVY }, line: { color: NAVY } });
  s.addText("교차검증 R²", { x: x + 0.2, y: y + 0.18, w: W - 0.4, h: 0.28, fontSize: 10, color: ICE, fontFace: F, isTextBox: true, margin: 0 });
  s.addText("0.89 ~ 1.00", { x: x + 0.2, y: y + 0.46, w: W - 0.4, h: 0.6, fontSize: 26, bold: true, color: "FFFFFF", fontFace: F, isTextBox: true, margin: 0, valign: "middle" });
  s.addText([
    { text: "80점을 10묶음으로 나눠, 한 묶음씩 빼고 학습한 모델로 뺀 묶음을 예측", options: { breakLine: true } },
    { text: "→ 학습에 쓰지 않은 설계에 대한 정확도", options: { bold: true, color: "7FD6E8" } }
  ], { x: x + 0.2, y: y + 1.14, w: W - 0.4, h: 1.2, fontSize: 9, color: "FFFFFF", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25, valign: "top" });

  s.addText("점 = 설계 1개 · 빨간 선 = 예측이 실측과 정확히 같은 경우 · 균일도(유량 표준편차)는 0에 가까운 값이라 R²로 비교",
    { x: M, y: 6.82, w: 12.23, h: 0.26, fontSize: 8.5, color: MUTED, italic: true, fontFace: F, isTextBox: true, margin: 0 });
  s.addNotes("80점을 10묶음으로 나눠 한 묶음씩 빼고 학습한 모델로 빠진 묶음을 예측했다. 즉 모델이 처음 보는 설계를 얼마나 맞히는지 본 것이다. 점이 빨간 대각선에 가까울수록 정확하다. 7개 응답 모두 R² 0.89 이상이고, 2차 균일도가 0.893으로 가장 낮다.");
}

/* ───────────── 10. [03] 지배 변수 교차 확인 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "03", SEC3, "지배 변수 교차 확인  —  DSD vs GPR");
  const y0 = 1.30, ch = 4.55;
  card(s, M, y0, CW, ch);
  cardTitle(s, M, y0, "응답별 1순위 변수 비교");
  const order = ["pressure_drop", "temp_std", "max_temp", "std_pass1", "std_pass2", "power_module_flow", "weight"];
  let hit = 0;
  const rows = [[hdr("응답"), hdr("DSD 1순위 (29회)"), hdr("GPR 1순위 (80점)"), { text: "일치", options: { bold: true, color: NAVY, fill: { color: "EEF2F7" }, align: "center" } }]];
  order.forEach(rp => {
    const a = DATA.dsd_top[rp][0], b = DATA.ard[rp][0];
    const same = a === b; if (same) hit++;
    const top2 = DATA.dsd_top[rp].slice(0, 2).includes(b) && DATA.ard[rp].slice(0, 2).includes(a);
    rows.push([RL[rp], VL[a], VL[b],
      { text: same ? "●" : (top2 ? "◐" : "○"), options: { bold: true, color: same ? NAVY : "0088A6", align: "center" } }]);
  });
  tbl(s, M + 0.34, y0 + 0.74, 5.3, rows, [1.2, 1.65, 1.65, 0.8], { rowH: 0.36 });
  s.addText("● 1순위 일치   ◐ 1·2순위가 서로 바뀜", { x: M + 0.34, y: y0 + 3.7, w: 5.3, h: 0.24, fontSize: 8.5, color: MUTED, fontFace: F, isTextBox: true, margin: 0 });
  s.addText([{ text: `${hit} / 7`, options: { bold: true, color: NAVY, fontSize: 18 } }, { text: "   응답에서 1순위 일치, 나머지 1개도 상위 2개 안에서 일치", options: { color: TXT, fontSize: 9.5 } }],
    { x: M + 0.34, y: y0 + 3.98, w: 5.3, h: 0.42, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

  card(s, CX2, y0, CW, ch);
  cardTitle(s, CX2, y0, "확정된 지배 변수");
  const dom = [
    ["1차 핀 개수", "차압 · 최고온도 · 1차 균일도", NAVY],
    ["2차 핀 개수", "온도편차 · 2차 균일도 · 분기비", NAVY],
    ["분기 입구 두께", "분기비", ACCENT]
  ];
  dom.forEach(([h, d, col], i) => {
    const yy = y0 + 0.76 + i * 0.82;
    s.addShape(pres.ShapeType.roundRect, { x: CX2 + 0.34, y: yy, w: 5.3, h: 0.68, rectRadius: 0.07, fill: { color: "F7F9FC" }, line: { color: LINE, width: 0.75 } });
    s.addShape(pres.ShapeType.roundRect, { x: CX2 + 0.46, y: yy + 0.13, w: 1.75, h: 0.42, rectRadius: 0.08, fill: { color: col }, line: { color: col } });
    s.addText(h, { x: CX2 + 0.46, y: yy + 0.13, w: 1.75, h: 0.42, fontSize: 10.5, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText([{ text: "지배 응답  ", options: { color: MUTED, fontSize: 8.5 } }, { text: d, options: { bold: true, color: NAVY } }],
      { x: CX2 + 2.36, y: yy, w: 3.2, h: 0.68, fontSize: 10, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });
  s.addShape(pres.ShapeType.roundRect, { x: CX2 + 0.34, y: y0 + 3.3, w: 5.3, h: 1.0, rectRadius: 0.06, fill: { color: NAVY }, line: { color: NAVY } });
  s.addText([
    { text: "데이터도 방법도 다른데 같은 결론", options: { bold: true, color: "FFFFFF", breakLine: true } },
    { text: "DSD: 29회 · 3수준 근사   /   GPR: 80점 · 비선형 모델", options: { color: ICE } }
  ], { x: CX2 + 0.5, y: y0 + 3.3, w: 5.0, h: 1.0, fontSize: 10, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.3 });

  bottomStrip(s, [
    ["핀 개수가 성능을 좌우", "두께보다 개수의 영향이 압도적"],
    ["통과별 분리 타당성 확인", "1차 · 2차 핀이 각자 다른 응답을 지배"],
    ["분기비는 분기 입구가 결정", "전원모듈 유량 조절의 핵심 변수"]
  ]);
  s.addNotes("DSD는 29회 실험에서 3수준으로 근사한 결과이고, GPR은 80점으로 학습한 비선형 모델이다. 서로 다른 데이터와 방법인데도 7개 응답 중 6개에서 1순위 변수가 같았고, 나머지 하나도 상위 2개 안에서는 일치했다. 그래서 1차 핀 개수, 2차 핀 개수, 분기 입구 두께를 지배 변수로 확정했다.");
}

/* ───────────── 11. [03] 한계 및 차월 계획 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "03", SEC3, "한계 및 차월 계획");
  const y0 = 1.30, ch = 3.75;
  card(s, M, y0, CW, ch);
  cardTitle(s, M, y0, "정확도가 가장 낮은 응답  —  2차 균일도");
  s.addShape(pres.ShapeType.roundRect, { x: M + 0.34, y: y0 + 0.74, w: 1.7, h: 0.86, rectRadius: 0.07, fill: { color: "E8F6FA" }, line: { color: ACCENT, width: 0.75 } });
  s.addText([{ text: "R²", options: { fontSize: 9, color: MUTED, breakLine: true } }, { text: "0.893", options: { fontSize: 22, bold: true, color: "0088A6" } }],
    { x: M + 0.34, y: y0 + 0.74, w: 1.7, h: 0.86, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  s.addText([{ text: "2차 통과 유로 유량의 표준편차", options: { bold: true, color: NAVY, breakLine: true } },
             { text: "응답 7개 중 예측 정확도가 가장 낮음", options: { color: MUTED } }],
    { x: M + 2.22, y: y0 + 0.74, w: 3.4, h: 0.86, fontSize: 10, valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });
  s.addText("원인", { x: M + 0.34, y: y0 + 1.8, w: 5.3, h: 0.28, fontSize: 10.5, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0 });
  s.addText([
    { text: "값이 0에 가까워 작은 오차도 상대적으로 크게 나타남", options: { bullet: true, breakLine: true } },
    { text: "분기 이후 구간이라 분기 입구 · 2차 핀 · 중간 입구 등 여러 변수가 함께 작용", options: { bullet: true, breakLine: true } },
    { text: "80점만으로는 이 영역의 변화를 충분히 덮지 못함", options: { bullet: true } }
  ], { x: M + 0.34, y: y0 + 2.12, w: 5.3, h: 1.3, fontSize: 9.5, color: TXT, fontFace: F, isTextBox: true, margin: 0, paraSpaceAfter: 5, lineSpacingMultiple: 1.2, valign: "top" });

  card(s, CX2, y0, CW, ch);
  cardTitle(s, CX2, y0, "차월 계획  —  3개월차");
  [["적응 샘플링", "불확실성이 큰 지점을 골라 해석을 추가해 정확도 보강"],
   ["다목적 최적화", "대리모델 위에서 파레토 최적해 탐색"],
   ["사업 적용 검토", "실제 사업에서 AI 열해석 자동화 적용 가능성 검토"]].forEach(([h, d], i) => {
    const yy = y0 + 0.76 + i * 0.9;
    s.addShape(pres.ShapeType.ellipse, { x: CX2 + 0.36, y: yy + 0.1, w: 0.34, h: 0.34, fill: { color: i === 0 ? ACCENT : NAVY }, line: { color: i === 0 ? ACCENT : NAVY } });
    s.addText(String(i + 1), { x: CX2 + 0.36, y: yy + 0.1, w: 0.34, h: 0.34, fontSize: 10, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(h, { x: CX2 + 0.85, y: yy, w: 4.7, h: 0.3, fontSize: 11, bold: true, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(d, { x: CX2 + 0.85, y: yy + 0.3, w: 4.7, h: 0.3, fontSize: 9.5, color: TXT, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });

  // 하단 — 2개월차 요약
  const by = y0 + ch + 0.22;
  s.addShape(pres.ShapeType.roundRect, { x: M, y: by, w: 12.23, h: 6.98 - by, rectRadius: 0.06, fill: { color: NAVY }, line: { color: NAVY } });
  s.addText("2 개 월 차   요 약", { x: M + 0.42, y: by + 0.16, w: 4, h: 0.3, fontSize: 11, bold: true, color: ACCENT, fontFace: F, isTextBox: true, margin: 0, charSpacing: 1 });
  [["11 → 8", "변수 선별 (DSD 29회)"], ["80 점", "활성 변수 실험계획 (OLHD)"], ["0.89 ~ 1.00", "대리모델 교차검증 R²"]].forEach(([v, l], i) => {
    const x = M + 0.42 + i * 3.95;
    s.addText(v, { x, y: by + 0.5, w: 3.6, h: 0.62, fontSize: 26, bold: true, color: "FFFFFF", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(l, { x, y: by + 1.12, w: 3.6, h: 0.3, fontSize: 10, color: ICE, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });
  s.addNotes("가장 정확도가 낮은 응답은 2차 균일도다. 값 자체가 0에 가깝고 분기 이후 여러 변수가 함께 작용하는 구간이라, 80점만으로는 충분히 덮지 못했다. 차월에는 대리모델의 불확실성이 큰 지점을 골라 해석을 추가하는 적응 샘플링으로 이 부분을 보강하고, 그 위에서 다목적 최적화를 진행한다.");
}

pres.writeFile({ fileName: (process.env.M2OUT || __dirname + "/2개월차_변수선별_및_대리모델구축.pptx") }).then(f => console.log("생성 완료:", f));
