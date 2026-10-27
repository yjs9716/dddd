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
pres.title = "형상 생성부터 설계최적화까지 — 통합";

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
const ORDER = ["pressure_drop", "temp_std", "max_temp", "std_pass1", "std_pass2", "power_module_flow", "weight"];
const S1 = "AI 에이전트 기반 개발환경 구축";
const S2 = "설계변수 정의 및 설계공간 설정";
const S3 = "실험계획법 기반 자동해석 및 데이터 확보";
const S4 = "머신러닝 대리모델 구축";

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
// 응답별 머신러닝 영향도(Sobol) 정렬 — 단독 효과 S1 기준
const sobolRank = (rp) => Object.entries(DATA.sobol[rp].S1).sort((a, b) => b[1] - a[1]).map(e => e[0]);
const interShare = (rp) => Math.max(0, 1 - Object.values(DATA.sobol[rp].S1).reduce((a, b) => a + b, 0));

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
  s.addText("AI 기반 자동해석  ·  머신러닝 대리모델 구축", { x: M + 0.3, y: 4.92, w: 6.6, h: 0.62, fontSize: 13, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  s.addText("소속 / 성명 / 발표일자", { x: M + 0.3, y: 5.9, w: 8, h: 0.32, fontSize: 12, color: ICE, fontFace: F, isTextBox: true, margin: 0 });
  s.addNotes("AI 에이전트 기반 개발환경에서 형상·해석 자동화를 구축하고, 실험계획법으로 데이터를 확보해 머신러닝 대리모델까지 만든 과정을 다룬다.");
}

/* ─────────────────────────── 2. 목차 ─────────────────────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  s.addText("목   차", { x: M, y: 0.5, w: 6, h: 0.5, fontSize: 26, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0, charSpacing: 3 });
  const items = [
    ["01", S1, "망분리 환경 AI 에이전트 활용 체계 · 저장소 기반 개발환경 · 내부망 실행 구조"],
    ["02", S2, "유동 경로 · 핀 통과별 분리 · 후보 설계변수 11개"],
    ["03", S3, "자동해석 코드 · SolidWorks · Icepak 자동화 · 선별 실험(DSD) · 실험계획(OLHD)"],
    ["04", S4, "GPR · 예측값/실측값 교차검증 · Sobol 민감도 및 교호작용 · 한계 및 차월 계획"]
  ];
  let y = 1.35;
  items.forEach(([no, t, sub]) => {
    const h = 1.18;
    card(s, M, y, 12.23, h);
    s.addText(no, { x: M + 0.3, y: y + 0.14, w: 1.2, h: 0.9, fontSize: 38, bold: true, color: ICE, fontFace: F, isTextBox: true, margin: 0, align: "center", valign: "middle" });
    s.addText(t, { x: M + 1.7, y: y + 0.14, w: 4.9, h: 0.9, fontSize: 15, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0, valign: "middle" });
    s.addShape(pres.ShapeType.rect, { x: M + 6.65, y: y + 0.26, w: 0.02, h: h - 0.52, fill: { color: LINE }, line: { color: LINE } });
    s.addText(sub, { x: M + 6.95, y: y + 0.14, w: 5.0, h: 0.9, fontSize: 10.5, color: TXT, fontFace: F, isTextBox: true, margin: 0, valign: "middle", lineSpacingMultiple: 1.3 });
    y += h + 0.2;
  });
  s.addNotes("01 개발환경, 02 설계변수와 설계공간, 03 실험계획법 기반 자동해석과 데이터 확보, 04 머신러닝 대리모델 구축 순서로 진행한다.");
}

/* ───────────── 3. 개요 — 한눈에 보기 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  s.addShape(pres.ShapeType.rect, { x: M, y: 0.42, w: 0.52, h: 0.52, fill: { color: ACCENT }, line: { color: ACCENT } });
  s.addText("개요", { x: M, y: 0.42, w: 0.52, h: 0.52, fontSize: 11, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  s.addText("설계최적화 흐름 한눈에 보기", { x: M + 0.68, y: 0.40, w: 8.0, h: 0.26, fontSize: 10.5, bold: true, color: ACCENT, fontFace: F, isTextBox: true, margin: 0, charSpacing: 1 });
  s.addText("후보 설계변수 11개에서 대리모델까지", { x: M + 0.68, y: 0.60, w: 11.6, h: 0.42, fontSize: 22, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0 });

  // 상단 — 5단계 흐름
  const steps = [
    ["후보 설계변수 정의", "설계공간 정의", "유로 형상 7개 +\n핀 두께 · 개수 4개\n(1차 · 2차 통과별 독립)", "후보 11개"],
    ["변수 선별", "DSD  (확정적 선별 설계)", "적은 해석으로\n영향 있는 변수만\n빠르게 판정", "29회 → 활성 8개"],
    ["활성 변수 실험계획", "OLHD  (최적라틴방격법)", "설계공간을\n빈틈없이 고르게\n채우도록 실험점 배치", "80점 해석"],
    ["대리모델 구축", "GPR  (가우시안 프로세스 회귀)", "해석 결과를 학습해\n해석 없이도 성능을\n수 초 만에 예측", "응답별 모델 7개"],
    ["정확도 · 민감도 분석", "교차검증 · Sobol 지수", "처음 보는 설계도 맞히는지\n어떤 변수가 성능을\n좌우하는지 확인", "R² 0.89 ~ 1.00"]
  ];
  const fy = 1.30, fh = 2.3, gap = 0.28, fw = (12.23 - 4 * gap) / 5;
  steps.forEach(([t, tech, d, res], i) => {
    const x = M + i * (fw + gap), ml = i >= 3;
    card(s, x, fy, fw, fh);
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.16, y: fy + 0.17, w: 0.3, h: 0.3, fill: { color: ml ? ACCENT : NAVY }, line: { color: ml ? ACCENT : NAVY } });
    s.addText(String(i + 1), { x: x + 0.16, y: fy + 0.17, w: 0.3, h: 0.3, fontSize: 9.5, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(t, { x: x + 0.52, y: fy + 0.12, w: fw - 0.58, h: 0.4, fontSize: 10, bold: true, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    chip(s, x + 0.16, fy + 0.62, fw - 0.32, 0.3, tech, ml ? "E8F6FA" : "EEF2F7", ml ? "0088A6" : NAVY, 8.5);
    s.addText(d, { x: x + 0.1, y: fy + 1.0, w: fw - 0.2, h: 0.74, fontSize: 9, color: TXT, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.15 });
    s.addShape(pres.ShapeType.line, { x: x + 0.3, y: fy + 1.8, w: fw - 0.6, h: 0, line: { color: LINE, width: 0.75 } });
    s.addText(res, { x: x + 0.1, y: fy + 1.84, w: fw - 0.2, h: 0.4, fontSize: 14, bold: true, color: ml ? "0088A6" : NAVY, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    if (i < 4) s.addText("▶", { x: x + fw + 0.02, y: fy + fh / 2 - 0.15, w: gap - 0.04, h: 0.3, fontSize: 10, color: "9FB0C6", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });

  // 좌하 — 응답 7개
  const by = 3.80, bh = 3.18;
  card(s, M, by, CW, bh);
  cardTitle(s, M, by, "응답 7개  —  목적함수 5 + 제약조건 2");
  const good = (t) => ({ text: t, options: { color: NAVY, bold: true, align: "center" } });
  tbl(s, M + 0.34, by + 0.68, 5.3, [
    [hdr("응답"), hdr("의미"), { text: "구분", options: { bold: true, color: NAVY, fill: { color: "EEF2F7" }, align: "center" } }],
    [{ text: "차압", options: { bold: true } }, "입구 · 출구 사이 압력 차이 (펌프 부담)", good("목적함수 ↓")],
    [{ text: "최고온도", options: { bold: true } }, "발열원 중 가장 높은 온도", good("목적함수 ↓")],
    [{ text: "온도편차", options: { bold: true } }, "발열원 간 평균 온도의 표준편차", good("목적함수 ↓")],
    [{ text: "1차 균일도", options: { bold: true } }, "1차 통과 유로별 유량의 표준편차", good("목적함수 ↓")],
    [{ text: "2차 균일도", options: { bold: true } }, "2차 통과 유로별 유량의 표준편차", good("목적함수 ↓")],
    [{ text: "분기비", options: { bold: true } }, "전원공급모듈 쪽으로 빠지는 유량 비율", good("제약조건")],
    [{ text: "중량", options: { bold: true } }, "냉각판 무게", good("제약조건")]
  ], [1.05, 3.0, 1.25], { rowH: 0.285, fontSize: 9 });

  // 우하 — 왜 두 단계인가
  card(s, CX2, by, CW, bh);
  cardTitle(s, CX2, by, "왜 'DSD → GPR' 2단계인가");
  [["DSD", NAVY, "주효과(변수 하나만의 효과)를 29회로 판정", "→ 비활성 변수 3개를 고정해 해석 횟수 절약"],
   ["GPR", ACCENT, "교호작용(변수끼리 얽힌 효과)까지 학습", "→ 정밀 예측 · Sobol 민감도 분석"]].forEach(([tag, col, l1, l2], i) => {
    const yy = by + 0.70 + i * 0.72;
    s.addShape(pres.ShapeType.roundRect, { x: CX2 + 0.34, y: yy, w: 5.3, h: 0.62, rectRadius: 0.06, fill: { color: "F7F9FC" }, line: { color: LINE, width: 0.75 } });
    chip(s, CX2 + 0.46, yy + 0.14, 1.05, 0.34, tag, col, "FFFFFF", 9.5);
    s.addText([{ text: l1, options: { bold: true, color: NAVY, breakLine: true } }, { text: l2, options: { color: TXT } }],
      { x: CX2 + 1.64, y: yy, w: 3.95, h: 0.62, fontSize: 9.3, valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.15 });
  });
  s.addShape(pres.ShapeType.roundRect, { x: CX2 + 0.34, y: by + 2.16, w: 5.3, h: 0.86, rectRadius: 0.06, fill: { color: "E8F6FA" }, line: { color: ACCENT, width: 0.75 } });
  s.addText([
    { text: "교호작용이란?  ", options: { bold: true, color: "0088A6" } },
    { text: "두 변수가 함께 바뀔 때 생기는 추가 효과", options: { bold: true, color: NAVY, breakLine: true } },
    { text: "예) 핀 무게 ∝ 개수 × 두께 → 핀이 두꺼울수록 1개 늘릴 때 무게가 더 많이 늘어남", options: { color: TXT, fontSize: 8.8 } }
  ], { x: CX2 + 0.5, y: by + 2.16, w: 5.0, h: 0.86, fontSize: 9.5, valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });

  s.addNotes("설계최적화 전체 흐름이다. 후보 설계변수 11개를 정의하고, 확정적 선별 설계(DSD) 29회로 활성 변수 8개를 선별했다. 활성 변수로 최적라틴방격법(OLHD) 80점을 해석해 가우시안 프로세스 회귀(GPR) 대리모델을 학습시켰고, 교차검증으로 처음 보는 설계도 잘 맞히는지 확인했다. 2단계로 나눈 이유는 역할이 다르기 때문이다. DSD는 적은 해석으로 주효과(변수 하나만의 효과)를 판정하는 데 강하지만, 교호작용(변수끼리 얽힌 효과)의 크기는 정확히 분리하지 못한다. 그 부분은 GPR이 맡는다.");
}

/* ───────────── 3. [01] 망분리 환경에서의 AI 에이전트 활용 체계 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "01", "AI 에이전트 기반 개발환경 구축", "망분리 환경에서의 AI 에이전트 활용 체계");
  const y1 = 1.30, y2 = 4.18, ch = 2.72;

  // 좌상 — 제약 조건
  card(s, M, y1, CW, ch);
  cardTitle(s, M, y1, "제약 조건");
  tbl(s, M + 0.34, y1 + 0.80, 5.3, [
    [hdr("구분"), hdr("현황")],
    ["내부망", "보안 정책상 외부 AI 직접 접속 불가"],
    ["반출 제한", "CAD·해석 모델 및 원본 결과는 반출 불가"],
    ["필요 사항", "내부 자산을 내보내지 않고 개발하는 방법"]
  ], [1.15, 4.15], { rowH: 0.34 });
  s.addShape(pres.ShapeType.roundRect, { x: M + 0.34, y: y1 + 2.22, w: 5.3, h: 0.42, rectRadius: 0.06, fill: { color: "EEF2F7" }, line: { color: "EEF2F7" } });
  s.addText("→  외부에서 만드는 것은 '코드'이고, 형상과 해석은 내부망에서만 수행", { x: M + 0.48, y: y1 + 2.22, w: 5.05, h: 0.42, fontSize: 9.5, bold: true, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

  // 우상 — 활용 구조
  card(s, CX2, y1, CW, ch);
  cardTitle(s, CX2, y1, "활용 구조");
  const zoneY = y1 + 0.72;
  s.addText("외부 (개발)", { x: CX2 + 0.34, y: zoneY, w: 2.0, h: 0.22, fontSize: 9, bold: true, color: MUTED, align: "left", fontFace: F, isTextBox: true, margin: 0, charSpacing: 1 });
  s.addText("내부망", { x: CX2 + 3.64, y: zoneY, w: 2.0, h: 0.22, fontSize: 9, bold: true, color: MUTED, align: "right", fontFace: F, isTextBox: true, margin: 0, charSpacing: 1 });
  s.addShape(pres.ShapeType.line, { x: CX2 + 3.64, y: y1 + 0.68, w: 0, h: 1.58, line: { color: "B9C4D2", width: 1.25, dashType: "dash" } });
  const bY = y1 + 1.02, bH = 0.5, bW = 1.5;
  const bx = [CX2 + 0.34, CX2 + 2.04, CX2 + 3.74];
  [["AI 에이전트", ACCENT, "FFFFFF"], ["저장소\n(코드 · 문서)", "FFFFFF", NAVY], ["CAD · 해석 실행", NAVY, "FFFFFF"]].forEach(([t, f, c], i) => {
    s.addShape(pres.ShapeType.roundRect, { x: bx[i], y: bY, w: bW, h: bH, rectRadius: 0.07, fill: { color: f }, line: { color: f === "FFFFFF" ? NAVY : f, width: 1.25 } });
    s.addText(t, { x: bx[i], y: bY, w: bW, h: bH, fontSize: i === 1 ? 9 : 10, bold: true, color: c, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 0.95 });
  });
  s.addShape(pres.ShapeType.line, { x: CX2 + 1.84, y: bY + bH / 2, w: 0.20, h: 0, line: { color: NAVY, width: 1.25, endArrowType: "triangle" } });
  s.addShape(pres.ShapeType.line, { x: CX2 + 3.54, y: bY + bH / 2, w: 0.20, h: 0, line: { color: NAVY, width: 1.25, endArrowType: "triangle" } });
  s.addText("코드 · 문서 반입", { x: CX2 + 2.85, y: bY + bH + 0.03, w: 1.45, h: 0.22, fontSize: 8, color: NAVY, align: "center", fontFace: F, isTextBox: true, margin: 0 });
  const rY = y1 + 1.92;
  s.addShape(pres.ShapeType.line, { x: CX2 + 4.49, y: bY + bH, w: 0, h: rY - (bY + bH), line: { color: MUTED, width: 1.1 } });
  s.addShape(pres.ShapeType.line, { x: CX2 + 1.09, y: rY, w: 3.40, h: 0, line: { color: MUTED, width: 1.1, beginArrowType: "triangle" } });
  s.addShape(pres.ShapeType.line, { x: CX2 + 1.09, y: bY + bH, w: 0, h: rY - (bY + bH), line: { color: MUTED, width: 1.1, beginArrowType: "triangle" } });
  s.addText("개발자가 결과를 확인하고 요구사항만 정리해 전달", { x: CX2 + 0.34, y: rY + 0.04, w: 5.3, h: 0.24, fontSize: 8.5, color: MUTED, align: "center", fontFace: F, isTextBox: true, margin: 0 });
  s.addShape(pres.ShapeType.roundRect, { x: CX2 + 0.34, y: y1 + 2.28, w: 5.3, h: 0.32, rectRadius: 0.05, fill: { color: "EEF2F7" }, line: { color: "EEF2F7" } });
  s.addText("형상·해석 모델과 원본 결과는 경계를 넘지 않음", { x: CX2 + 0.34, y: y1 + 2.28, w: 5.3, h: 0.32, fontSize: 9, bold: true, color: NAVY, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

  // 좌하 — 맥락 구축
  card(s, M, y2, CW, ch);
  cardTitle(s, M, y2, "맥락(Context) 구축 방법");
  tbl(s, M + 0.34, y2 + 0.78, 5.3, [
    [hdr("저장소 구성"), hdr("담는 내용")],
    ["설계 로직 문서", "설계변수 구성 · 제약조건 · 처리 절차"],
    ["작업 규칙 문서", "임의 수정 금지 등 협업 규칙"],
    ["코드", "형상·해석 자동화 모듈"],
    ["인터페이스 규약", "결과 파일 형식, API 호출 규약"]
  ], [1.45, 3.85], { rowH: 0.30 });
  s.addText("코드 작성에 필요한 범위로 한정 — 매 세션 저장소를 읽어 이전 맥락을 그대로 이어받음",
    { x: M + 0.34, y: y2 + 2.34, w: 5.3, h: 0.30, fontSize: 9, color: MUTED, italic: true, fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });

  // 우하 — 운영 방식
  card(s, CX2, y2, CW, ch);
  cardTitle(s, CX2, y2, "운영 방식");
  tbl(s, CX2 + 0.34, y2 + 0.78, 5.3, [
    [hdr("항목"), hdr("내용")],
    ["버전 관리", "코드·문서 변경을 버전별 분기로 이력화"],
    ["변경 이력", "코드 수정 이력이 곧 설계 결정 이력"],
    ["반입 범위", "코드·문서만 내부망으로 반입"],
    ["코드 검증", "수식 검산 · 전수 검증 · 통합 테스트"]
  ], [1.25, 4.05], { rowH: 0.30 });
  s.addShape(pres.ShapeType.roundRect, { x: CX2 + 0.34, y: y2 + 2.30, w: 5.3, h: 0.38, rectRadius: 0.06, fill: { color: NAVY } });
  s.addText("내부 자산을 반출하지 않고 AI 협업 체계 구축", { x: CX2 + 0.34, y: y2 + 2.30, w: 5.3, h: 0.38, fontSize: 10, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

  s.addNotes("보안 정책상 CAD·해석 모델과 원본 결과는 외부로 나갈 수 없다. 따라서 외부에서는 코드와 문서만 작성하고, 형상 생성과 해석은 전적으로 내부망에서 수행한다. 실행 결과는 개발자가 확인한 뒤 필요한 요구사항만 정리해 전달하는 방식으로 운영했다.");
}

/* ───────────── 4. [01] 저장소 기반 개발환경 구성 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "01", "AI 에이전트 기반 개발환경 구축", "저장소 기반 개발환경 구성");

  const FW = 5.75, FH = 3.42, FY = 1.66;
  const FX = [M, 7.03];
  [["①", "AI 에이전트 — 작업 브랜치 연결", ACCENT], ["②", "저장소 — 버전별 브랜치로 저장", NAVY]].forEach(([no, title, col], i) => {
    s.addShape(pres.ShapeType.ellipse, { x: FX[i], y: 1.20, w: 0.30, h: 0.30, fill: { color: col }, line: { color: col } });
    s.addText(no, { x: FX[i], y: 1.20, w: 0.30, h: 0.30, fontSize: 11, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(title, { x: FX[i] + 0.42, y: 1.18, w: FW - 0.42, h: 0.34, fontSize: 13, bold: true, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addShape(pres.ShapeType.roundRect, { x: FX[i], y: FY, w: FW, h: FH, rectRadius: 0.05, fill: { color: CARD }, line: { color: "C3CDDA", width: 1, dashType: "dash" }, shadow: sh() });
    s.addText(`${no}  화면 캡처 삽입 영역`, { x: FX[i], y: FY + FH / 2 - 0.3, w: FW, h: 0.4, fontSize: 12, bold: true, color: "AAB6C6", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText("(프레임에 맞춰 캡처 이미지로 교체)", { x: FX[i], y: FY + FH / 2 + 0.06, w: FW, h: 0.3, fontSize: 9, color: "C3CDDA", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });
  s.addShape(pres.ShapeType.line, { x: 6.40, y: FY + FH / 2, w: 0.55, h: 0, line: { color: NAVY, width: 1.5, endArrowType: "triangle" } });
  s.addText("저장", { x: 6.28, y: FY + FH / 2 - 0.34, w: 0.80, h: 0.26, fontSize: 9, bold: true, color: NAVY, align: "center", fontFace: F, isTextBox: true, margin: 0 });
  ["세션 시작 시 저장소의 지정 브랜치를 연결\n→ 이전 작업 맥락을 그대로 이어받아 코드 작성",
   "작성된 코드·문서가 해당 브랜치에 반영\n→ 형상·변수 구성 변경이 버전별로 축적"].forEach((t, i) => {
    s.addText(t, { x: FX[i] + 0.04, y: 5.22, w: FW - 0.08, h: 0.68, fontSize: 10, color: TXT, fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });
  });
  s.addShape(pres.ShapeType.roundRect, { x: M, y: 6.06, w: 12.23, h: 0.92, rectRadius: 0.06, fill: { color: CARD }, line: { color: LINE, width: 0.75 }, shadow: sh() });
  [["작업 단위 = 브랜치", "형상·변수 구성이 바뀔 때마다 분기하여 관리"],
   ["맥락 유지", "세션이 바뀌어도 저장소를 읽어 이어서 작업"],
   ["이력 = 근거", "커밋 메시지가 곧 설계 변경 사유로 남음"]].forEach(([h, d], i) => {
    const x = M + 0.36 + i * 4.0;
    s.addShape(pres.ShapeType.rect, { x, y: 6.26, w: 0.07, h: 0.18, fill: { color: ACCENT }, line: { color: ACCENT } });
    s.addText(h, { x: x + 0.16, y: 6.20, w: 3.6, h: 0.28, fontSize: 10.5, bold: true, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(d, { x: x + 0.16, y: 6.50, w: 3.6, h: 0.34, fontSize: 9.5, color: MUTED, fontFace: F, isTextBox: true, margin: 0 });
  });
  s.addText("※ 화면 내 설계 세부값은 마스킹 처리", { x: M, y: 7.02, w: 6, h: 0.26, fontSize: 8.5, color: MUTED, italic: true, fontFace: F, isTextBox: true, margin: 0 });
  s.addNotes("왼쪽은 AI 에이전트에서 작업 브랜치를 연결하는 화면, 오른쪽은 그 결과가 저장소에 버전별 브랜치로 쌓이는 화면이다. 세션이 바뀌어도 저장소를 읽어 이전 맥락을 이어받기 때문에 같은 설명을 반복할 필요가 없고, 커밋 메시지가 설계 변경 사유로 남아 이력 추적이 가능하다. 화면에 보이는 설계 세부값은 마스킹 처리했다.");
}

/* ───────────── 5. [01] 내부망 실행 구조 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "01", "AI 에이전트 기반 개발환경 구축", "내부망 실행 구조 — 시스템 아키텍처");

  s.addShape(pres.ShapeType.rect, { x: M, y: 1.22, w: 0.07, h: 0.26, fill: { color: ACCENT }, line: { color: ACCENT } });
  s.addText("작성된 코드가 CAD·해석 프로그램을 직접 제어 — 전 과정이 코드로 연결됨",
    { x: M + 0.18, y: 1.16, w: 11.6, h: 0.36, fontSize: 12.5, bold: true, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

  const IW = 8.55, IH = IW / 1.8044, IX = M, IY = 1.64;
  s.addShape(pres.ShapeType.roundRect, { x: IX - 0.06, y: IY - 0.06, w: IW + 0.12, h: IH + 0.12, rectRadius: 0.05, fill: { color: CARD }, line: { color: LINE, width: 0.75 }, shadow: sh() });
  s.addImage({ path: "/home/user/dddd/시스템아키텍처.PNG", x: IX, y: IY, w: IW, h: IH });

  const RX = IX + IW + 0.45, RW = 13.333 - RX - M;
  s.addText("구성 계층", { x: RX, y: IY - 0.02, w: RW, h: 0.3, fontSize: 12, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0 });
  const layers = [
    ["개발 환경", "코드 편집 · 디버깅 · 인터프리터 설정"],
    ["실행 환경", "Python 기반 API 라이브러리로 명령 전달"],
    ["CAD", "형상 파라미터 갱신 · 리빌드 · STEP 내보내기"],
    ["해석", "해석 모델 구성 · 솔버 실행 · 결과 추출"]
  ];
  let ly = IY + 0.34;
  layers.forEach(([h, d], i) => {
    s.addShape(pres.ShapeType.ellipse, { x: RX, y: ly + 0.02, w: 0.26, h: 0.26, fill: { color: NAVY }, line: { color: NAVY } });
    s.addText(String(i + 1), { x: RX, y: ly + 0.02, w: 0.26, h: 0.26, fontSize: 8.5, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(h, { x: RX + 0.36, y: ly, w: RW - 0.36, h: 0.28, fontSize: 10.5, bold: true, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(d, { x: RX + 0.36, y: ly + 0.28, w: RW - 0.36, h: 0.42, fontSize: 9.5, color: MUTED, fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.15 });
    ly += 0.82;
  });
  s.addShape(pres.ShapeType.roundRect, { x: RX, y: IY + IH - 0.92, w: RW, h: 0.9, rectRadius: 0.06, fill: { color: NAVY }, line: { color: NAVY } });
  s.addText("망분리 정책상\n외부망 ↔ 내부망 코드 이전은 수동 수행", { x: RX + 0.16, y: IY + IH - 0.92, w: RW - 0.32, h: 0.9, fontSize: 10, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });

  const by = IY + IH + 0.26;
  s.addShape(pres.ShapeType.roundRect, { x: M, y: by, w: 12.23, h: 0.72, rectRadius: 0.06, fill: { color: CARD }, line: { color: LINE, width: 0.75 }, shadow: sh() });
  [["프로그램 간 연동", "CAD와 해석 프로그램을 코드 한 곳에서 제어"],
   ["수작업 개입 제거", "형상 수정·해석 실행·결과 정리를 무인 반복"],
   ["재사용 가능 구조", "설계변수 정의만 교체하면 타 과제 적용 가능"]].forEach(([h, d], i) => {
    const x = M + 0.36 + i * 4.0;
    s.addShape(pres.ShapeType.rect, { x, y: by + 0.16, w: 0.07, h: 0.17, fill: { color: ACCENT }, line: { color: ACCENT } });
    s.addText(h, { x: x + 0.16, y: by + 0.10, w: 3.6, h: 0.28, fontSize: 10.5, bold: true, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(d, { x: x + 0.16, y: by + 0.38, w: 3.7, h: 0.28, fontSize: 9.5, color: MUTED, fontFace: F, isTextBox: true, margin: 0 });
  });
  s.addNotes("지난 차수에서 구축한 해석 자동화 환경의 시스템 아키텍처다. 개발 환경에서 작성한 Python 코드가 API를 통해 CAD와 해석 프로그램을 직접 제어하며, 형상 생성부터 결과 추출까지 전 과정이 코드로 연결된다. 코드 이전은 망분리 정책에 따라 수동으로 수행한다.");
}

/* ───────────── 4. [01] 후보 설계변수 정의 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "02", S2, "후보 설계변수 정의");
  const y0 = 1.30, ch = 4.55;

  // 좌 — 핀을 통과별로 나눈 이유
  card(s, M, y0, CW, ch);
  cardTitle(s, M, y0, "왜 핀을 1차 · 2차로 나눴나");
  const cx = M + CW / 2;
  chip(s, cx - 1.5, y0 + 0.78, 3.0, 0.4, "입구  ·  총 유량 4 LPM", "EEF2F7", NAVY, 10);
  downArrow(s, cx, y0 + 1.18, 0.2);
  chip(s, cx - 1.5, y0 + 1.38, 3.0, 0.42, "1차 통과  —  유량 전체가 지나감", NAVY, "FFFFFF", 10);
  downArrow(s, cx, y0 + 1.80, 0.2);
  chip(s, cx - 0.75, y0 + 2.0, 1.5, 0.36, "분  기", ACCENT, "FFFFFF", 10);
  s.addShape(pres.ShapeType.line, { x: M + 1.62, y: y0 + 2.36, w: 2.72, h: 0, line: { color: MUTED, width: 1.25 } });
  downArrow(s, M + 1.62, y0 + 2.36, 0.2);
  downArrow(s, M + 4.34, y0 + 2.36, 0.2);
  chip(s, M + 0.37, y0 + 2.56, 2.5, 0.42, "전원공급모듈로 일부 빠짐", "FFFFFF", NAVY, 9.5);
  chip(s, M + 3.09, y0 + 2.56, 2.5, 0.42, "2차 통과  —  남은 유량만", NAVY, "FFFFFF", 9.5);
  s.addText("1차와 2차에 흐르는 유량이 달라서, 핀 조건을 하나로 묶으면\n한쪽에 맞추는 순간 다른 쪽이 불리해짐",
    { x: M + 0.34, y: y0 + 3.08, w: 5.3, h: 0.56, fontSize: 9.8, color: TXT, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });
  s.addShape(pres.ShapeType.roundRect, { x: M + 0.34, y: y0 + 3.76, w: 5.3, h: 0.54, rectRadius: 0.06, fill: { color: NAVY }, line: { color: NAVY } });
  s.addText("→  핀 두께 · 개수를 1차 · 2차 통과별 독립 변수로 분리", { x: M + 0.34, y: y0 + 3.76, w: 5.3, h: 0.54, fontSize: 11.5, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

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
  s.addText("핀 갭(핀 사이 간격)은 두께 · 개수로 정해지는 종속값 — 최소 2.0 mm (제작 한계 2.5 mm는 최적화 단계 제약으로 적용)",
    { x: CX2 + 0.34, y: y0 + 4.0, w: 5.3, h: 0.4, fontSize: 8.6, color: MUTED, italic: true, fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.15 });

  bottomStrip(s, [
    ["후보 11개", "유로 형상 7개 + 1차 · 2차 핀 두께 · 개수 4개"],
    ["핀을 통과별로 분리", "1차 · 2차 유량 차이를 설계에 반영"],
    ["11차원 설계공간", "변수가 많을수록 필요한 해석 수 급증 → 변수 선별 먼저"]
  ]);
  s.addNotes("냉각유는 1차 통과를 지난 뒤 분기에서 일부가 전원공급모듈로 빠지기 때문에, 2차 통과에는 남은 유량만 흐른다. 핀 조건을 하나로 묶으면 한쪽에 맞추는 순간 다른 쪽이 불리해지므로, 핀 두께와 개수를 1차·2차 따로 두어 후보 변수는 11개가 된다. 변수가 많을수록 학습에 필요한 해석 횟수가 크게 늘기 때문에, 먼저 영향 있는 변수만 골라낸다.");
}

/* ───────────── 9. [02] 코드 구성 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "03", S3, "자동해석 코드 구성");
  const y0 = 1.30, ch = 4.55;
  card(s, M, y0, 12.23, ch);
  cardTitle(s, M, y0, "모듈 구성 및 실행 흐름");
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
    if (false) {
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
    ["모듈 분리 구조", "형상 · 해석 · 결과 · 학습 모듈을 독립적으로 교체"]
  ]);
  s.addNotes("자동해석 구조에 선별 실험표 생성(DSD.py)과 선별 판정·대리모델 학습(DSD_analysis.py, ML.py)을 추가했다. 형상 빌드, 해석, 결과 저장 모듈은 그대로 활용한다. 선별이 끝나면 프로그램이 멈추고 판정 결과를 사람이 확인한 뒤 2단계로 넘어간다.");
}

/* ───────────── 8. [03] 형상 자동 빌드 및 중량 산출 — SolidWorks ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "03", "실험계획법 기반 자동해석 수행 및 데이터 확보", "형상 자동 빌드 및 중량 산출 — SolidWorks");
  const y0 = 1.30, ch = 4.55;

  // 좌 — 처리 절차
  card(s, M, y0, CW, ch);
  cardTitle(s, M, y0, "Equation Manager 기반 형상 빌드");
  ["전역변수 갱신", "파트·어셈블리 리빌드", "STEP 저장"].forEach((t, i) => {
    const x = M + 0.34 + i * 1.82;
    s.addShape(pres.ShapeType.roundRect, { x, y: y0 + 0.80, w: 1.6, h: 0.46, rectRadius: 0.07, fill: { color: i === 0 ? NAVY : "EEF2F7" }, line: { color: i === 0 ? NAVY : LINE, width: 0.75 } });
    s.addText(t, { x, y: y0 + 0.80, w: 1.6, h: 0.46, fontSize: 9, bold: true, color: i === 0 ? "FFFFFF" : NAVY, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    if (i < 2) s.addText("▶", { x: x + 1.6, y: y0 + 0.80, w: 0.22, h: 0.46, fontSize: 9, color: ACCENT, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });
  tbl(s, M + 0.34, y0 + 1.48, 5.3, [
    [hdr("단계"), hdr("처리")],
    ["변수 갱신", "수식 목록에서 변수명 → 인덱스 매핑 후 값 치환"],
    ["정수 변수", "핀 개수는 정수 문자열로 기입 (선형패턴 개수)"],
    ["리빌드", "파트 → 어셈블리 순으로 리빌드 후 저장"],
    ["질량 특성", "리빌드 직후 부피·질량 일괄 취득"],
    ["형상 저장", "실험점 번호별 STEP 파일로 내보내기"]
  ], [1.2, 4.1], { rowH: 0.36 });
  s.addShape(pres.ShapeType.roundRect, { x: M + 0.34, y: y0 + 3.80, w: 5.3, h: 0.56, rectRadius: 0.06, fill: { color: "F7F9FC" }, line: { color: LINE, width: 0.75 } });
  s.addText([{ text: "중량 = ", options: { bold: true, color: NAVY } },
             { text: "알루미늄 질량 + (완전충진 부피 − 알루미늄 부피) × 794 kg/m³", options: { color: TXT } }],
    { x: M + 0.48, y: y0 + 3.80, w: 5.05, h: 0.56, fontSize: 9.5, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

  // 우 — 중량 산출
  card(s, CX2, y0, CW, ch);
  cardTitle(s, CX2, y0, "중량 산출");
  s.addShape(pres.ShapeType.roundRect, { x: CX2 + 0.34, y: y0 + 0.80, w: 5.3, h: 0.95, rectRadius: 0.06, fill: { color: "F7F9FC" }, line: { color: LINE, width: 0.75 } });
  s.addText([{ text: "PAO 부피 = 완전충진 형상 부피(상수) − 알루미늄 부피", options: { breakLine: true, color: TXT } },
             { text: "중  량   = 알루미늄 질량 + PAO 부피 × 794 kg/m³", options: { bold: true, color: NAVY } }],
    { x: CX2 + 0.5, y: y0 + 0.86, w: 5.0, h: 0.83, fontSize: 10.5, fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.35 });
  tbl(s, CX2 + 0.34, y0 + 1.95, 5.3, [
    [hdr("항목"), hdr("내용")],
    ["취득 시점", "리빌드 직후 어셈블리에서 질량 특성 일괄 취득"],
    ["반환값 해석", "반환 순서 미문서화 → GUI 패널과 전량 대조해 확정"],
    ["검산", "산출값이 수기 계산값과 소수점까지 일치"],
    ["교차검증", "해석 측 유체 부피와 대조, 이상 시 로그 경고"]
  ], [1.3, 4.0], { rowH: 0.40 });

  bottomStrip(s, [
    ["변수명 검증", "불일치 시 즉시 중단 — 형상 미변경 해석 차단"],
    ["종속값 CAD 위임", "핀 간격은 CAD 수식이 계산 — 이중 계산 방지"],
    ["질량 특성 검증", "미문서화 반환값을 GUI 패널과 대조해 확정"]
  ]);
  s.addNotes("설계값을 Equation Manager 전역변수에 써넣고 리빌드한 뒤 질량 특성과 STEP 파일을 얻는 과정이다. 변수명이 어긋나면 즉시 중단해 형상이 바뀌지 않은 채 해석되는 사고를 막았고, 핀 간격처럼 다른 변수에서 결정되는 값은 CAD 수식에 맡겨 두 곳에서 따로 계산하지 않도록 했다.");
}

/* ───────────── 9. [03] 해석 모델 자동 구성 — Icepak ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "03", "실험계획법 기반 자동해석 수행 및 데이터 확보", "해석 모델 자동 구성 및 결과 추출 — Icepak");
  const y0 = 1.30, ch = 4.55;

  // 좌 — 자동화 전환 과정
  card(s, M, y0, CW, ch);
  cardTitle(s, M, y0, "자동화 전환 과정");
  const flow = [
    ["GUI 수동 설정", "해석 모델을 GUI로 한 번 직접 구성\n(프로젝트 생성 ~ 결과 추출 7단계)", "EEF2F7", NAVY],
    ["스크립트 리코더 기록", "GUI 조작 과정을 Python 스크립트로 기록", "EEF2F7", NAVY],
    ["AI 에이전트와 코드 정리", "기록된 고정값을 설계변수 기반으로 치환하고\n재사용 가능한 모듈로 구조화", NAVY, "FFFFFF"],
    ["매 회차 자동 반복", "형상(STEP)만 바뀌면 동일 절차를 코드가 재현", ACCENT, "FFFFFF"]
  ];
  flow.forEach(([h, d, f, c], i) => {
    const yy = y0 + 0.78 + i * 0.84;
    s.addShape(pres.ShapeType.roundRect, { x: M + 0.34, y: yy, w: 5.3, h: 0.64, rectRadius: 0.06, fill: { color: f }, line: { color: f === "EEF2F7" ? LINE : f, width: 0.75 } });
    s.addText(String(i + 1), { x: M + 0.46, y: yy, w: 0.34, h: 0.64, fontSize: 16, bold: true, color: f === "EEF2F7" ? ACCENT : "FFFFFF", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(h, { x: M + 0.86, y: yy + 0.04, w: 1.9, h: 0.56, fontSize: 10.5, bold: true, color: c, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(d, { x: M + 2.72, y: yy + 0.04, w: 2.84, h: 0.56, fontSize: 8.8, color: f === "EEF2F7" ? TXT : "FFFFFF", valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.1 });
    if (i < flow.length - 1) s.addText("▼", { x: M + 0.34, y: yy + 0.64, w: 5.3, h: 0.2, fontSize: 7, color: MUTED, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });
  s.addText("※ 단계별 GUI 설정은 부록 A-1 참고", { x: M + 0.34, y: y0 + 4.20, w: 5.3, h: 0.24, fontSize: 9, color: MUTED, italic: true, fontFace: F, isTextBox: true, margin: 0 });

  // 우상 — 수동 vs 자동
  const hA = 2.38;
  card(s, CX2, y0, CW, hA);
  cardTitle(s, CX2, y0, "GUI 수동 설정 vs 코드 자동 구성");
  tbl(s, CX2 + 0.34, y0 + 0.70, 5.3, [
    [hdr("항목"), hdr("GUI 수동"), hdr("코드 자동")],
    ["모델 구성", "7단계 매회 직접 설정", { text: "스크립트 1회 실행", options: { bold: true, color: NAVY } }],
    ["형상 변경 시", "처음부터 재설정", { text: "STEP 교체만으로 재구성", options: { bold: true, color: NAVY } }],
    ["측정면 배치", "유로마다 수작업", { text: "핀 개수 따라 자동 계산", options: { bold: true, color: NAVY } }],
    ["설정 일관성", "작업자·회차별 편차", { text: "전 회차 동일 조건", options: { bold: true, color: NAVY } }]
  ], [1.25, 1.95, 2.1], { rowH: 0.32 });

  // 우하 — 측정 항목
  const yB = y0 + hA + 0.17, hB = ch - hA - 0.17;
  card(s, CX2, yB, CW, hB);
  cardTitle(s, CX2, yB, "측정 항목 및 결과 출력");
  tbl(s, CX2 + 0.34, yB + 0.66, 5.3, [
    [hdr("측정 대상"), hdr("항목"), hdr("개수")],
    ["발열원", "최고 · 평균 온도", "17"],
    ["팬 통과면", "차압", "1"],
    ["1·2차 통과 유로", "유량", "각 핀 개수 + 1"],
    ["전원모듈 분기 입구", "유량", "1"]
  ], [1.9, 1.7, 1.7], { rowH: 0.26, fontSize: 9 });

  bottomStrip(s, [
    ["회차별 새 프로젝트", "이전 회차 설정 간섭·잠금 파일로 인한 정지 방지"],
    ["경계면 자동 탐지", "형상이 바뀌어도 팬·개구부 면을 좌표로 식별"],
    ["측정면 동적 생성", "핀 개수 변화에 맞춰 유로 전체 측정면 자동 배치"]
  ]);
  s.addNotes("해석 모델은 처음에 GUI로 한 번 직접 구성하고, 그 과정을 스크립트 리코더로 기록했다. 기록된 스크립트는 형상 치수가 고정값으로 박혀 있어 그대로는 재사용할 수 없으므로, AI 에이전트와 함께 설계변수 기반 코드로 정리했다. 이후에는 형상 파일만 바뀌면 같은 절차를 코드가 매 회차 재현한다. 단계별 GUI 설정은 부록 A-1에 정리했다.");
}

/* ───────────── 5. [01] 선별 실험(DSD) 설계 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "03", S3, "선별 실험 설계  —  DSD (확정적 선별 설계)");
  const y0 = 1.30, ch = 5.55;
  const W = 5.3;

  // 좌 — DSD 실험표
  card(s, M, y0, CW, ch);
  cardTitle(s, M, y0, "왜 선별부터 · 어떻게");
  const X = M + 0.34;
  [["왜", "11개 모두 학습하면 해석 수 급증 → 영향 없는 변수를 먼저 고정"],
   ["어떻게", "DSD (Jones & Nachtsheim, 2011) — 3수준 표준 선별 실험표, 29회 해석"]].forEach(([k, d], i) => {
    const yy = y0 + 0.64 + i * 0.4;
    chip(s, X, yy + 0.03, 0.75, 0.3, k, i === 0 ? NAVY : ACCENT, "FFFFFF", 9);
    s.addText(d, { x: X + 0.88, y: yy, w: W - 0.88, h: 0.36, fontSize: 9, color: TXT, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });
  const L = DATA.plan.L, nC = L[0].length, nR = L.length;
  const gx = M + 1.6, cw = 0.27, rh = 0.072, gy = y0 + 1.92;
  const colR = { "-1": "E4EBF3", "0": "8FB0D4", "1": NAVY };
  const colF = { "-1": "E2F4F8", "0": "8DD2E2", "1": "0090B0" };
  s.addText("실제 변수 11개", { x: gx, y: y0 + 1.5, w: 11 * cw, h: 0.22, fontSize: 8.5, bold: true, color: NAVY, align: "center", fontFace: F, isTextBox: true, margin: 0 });
  s.addText("가짜 인자 3개", { x: gx + 11 * cw, y: y0 + 1.5, w: 3 * cw + 0.3, h: 0.22, fontSize: 8.5, bold: true, color: "0088A6", align: "center", fontFace: F, isTextBox: true, margin: 0 });
  s.addShape(pres.ShapeType.line, { x: gx, y: y0 + 1.76, w: 11 * cw - 0.03, h: 0, line: { color: NAVY, width: 1 } });
  s.addShape(pres.ShapeType.line, { x: gx + 11 * cw + 0.03, y: y0 + 1.76, w: 3 * cw - 0.03, h: 0, line: { color: ACCENT, width: 1 } });
  for (let r = 0; r < nR; r++) {
    for (let c = 0; c < nC; c++) {
      const v = String(L[r][c]), fake = c >= 11;
      const off = (r >= 14 ? 0.05 : 0) + (r >= 28 ? 0.05 : 0);
      s.addShape(pres.ShapeType.rect, { x: gx + c * cw, y: gy + r * rh + off, w: cw - 0.025, h: rh - 0.016,
        fill: { color: fake ? colF[v] : colR[v] }, line: { color: fake ? colF[v] : colR[v], width: 0 } });
    }
  }
  [["① 기본 14회", 0, 14, 0], ["② 거울상 14회", 14, 28, 0.05], ["③ 중심점 1회", 28, 29, 0.10]].forEach(([t, a, b, off]) => {
    const yy = gy + a * rh + off, hh = (b - a) * rh;
    s.addShape(pres.ShapeType.line, { x: gx - 0.1, y: yy + 0.01, w: 0, h: hh - 0.03, line: { color: MUTED, width: 1 } });
    s.addText(t, { x: X - 0.1, y: yy + hh / 2 - 0.13, w: 1.25, h: 0.26, fontSize: 8.5, bold: true, color: NAVY, align: "right", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });
  const ly = gy + 29 * rh + 0.14;
  [["최소값", "E4EBF3"], ["중간값", "8FB0D4"], ["최대값", NAVY]].forEach(([t, c], i) => {
    const x = gx + i * 1.05;
    s.addShape(pres.ShapeType.rect, { x, y: ly + 0.05, w: 0.2, h: 0.14, fill: { color: c }, line: { color: c } });
    s.addText(t, { x: x + 0.26, y: ly, w: 0.75, h: 0.24, fontSize: 8.5, color: TXT, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });
  // 읽는 법
  const ry = ly + 0.36;
  [["①", "한 줄 = 해석 1회. 매번 변수 하나만 중간값, 나머지는 최소 · 최대값"],
   ["②", "①을 정반대(최소 ↔ 최대)로 뒤집어 한 번 더"],
   ["③", "모든 변수 중간값으로 한 번"]].forEach(([n, t], i) => {
    s.addText([{ text: n + "  ", options: { bold: true, color: NAVY } }, { text: t, options: { color: TXT } }],
      { x: X, y: ry + i * 0.27, w: W, h: 0.26, fontSize: 9, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });

  // 우 — 가짜 인자로 판정
  card(s, CX2, y0, CW, ch);
  cardTitle(s, CX2, y0, "가짜 인자로 잡음 수준 추정");
  const RX = CX2 + 0.34;
  s.addText([
    { text: "가짜 인자", options: { bold: true, color: "0088A6" } },
    { text: " = 표에 칸만 있고 형상은 바꾸지 않는 빈 변수 → 효과가 0이어야 정상", options: { color: TXT } }
  ], { x: RX, y: y0 + 0.62, w: W, h: 0.3, fontSize: 9.2, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  s.addText("최고온도 예시  —  최대값 13회 평균과 최소값 13회 평균의 차이", { x: RX, y: y0 + 0.98, w: W, h: 0.26, fontSize: 9.5, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0 });
  const ex = DATA.dsd_example.items;
  const NAME = Object.assign({}, VL, { fake_1: "가짜 인자 1", fake_2: "가짜 인자 2", fake_3: "가짜 인자 3" });
  const BX = RX + 1.3, BW = 3.25, VMAX = 2.6, by0 = y0 + 1.32, bh = 0.33;
  const noise = Math.max(...ex.filter(e => e[0].startsWith("fake")).map(e => e[1]));
  ex.forEach(([v, val, sig], i) => {
    const yy = by0 + i * bh, fake = v.startsWith("fake");
    const col = fake ? ACCENT : (sig ? NAVY : "B9C7D8");
    s.addText(NAME[v], { x: RX, y: yy, w: 1.22, h: 0.26, fontSize: 9, bold: !fake && sig, color: fake ? "0088A6" : (sig ? NAVY : MUTED), align: "right", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addShape(pres.ShapeType.rect, { x: BX, y: yy + 0.05, w: Math.max(0.025, BW * val / VMAX), h: 0.16, fill: { color: col }, line: { color: col } });
    s.addText(`${val.toFixed(2)} ℃`, { x: Math.max(BX + BW * val / VMAX, BX + BW * noise / VMAX) + 0.08, y: yy, w: 0.8, h: 0.26, fontSize: 9, bold: true, color: col === "B9C7D8" ? MUTED : col, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });
  const nx = BX + BW * noise / VMAX;
  s.addShape(pres.ShapeType.line, { x: nx, y: by0 - 0.04, w: 0, h: ex.length * bh + 0.04, line: { color: "0088A6", width: 1, dashType: "dash" } });
  s.addText("잡음 수준", { x: nx + 0.04, y: by0 + ex.length * bh - 0.02, w: 1.0, h: 0.22, fontSize: 8, bold: true, color: "0088A6", fontFace: F, isTextBox: true, margin: 0 });
  const cy = by0 + ex.length * bh + 0.26;
  s.addText([
    { text: `가짜 인자도 최대 ${noise.toFixed(2)} ℃ 차이 → 이 정도는 잡음`, options: { bullet: true, breakLine: true } },
    { text: `1차 핀 개수 ${ex[0][1].toFixed(2)} ℃ → 잡음보다 훨씬 큼 → 영향 있음`, options: { bullet: true, breakLine: true } },
    { text: `1차 핀 두께 ${ex[2][1].toFixed(2)} ℃ → 잡음과 비슷 → 최고온도에는 영향 없음`, options: { bullet: true } }
  ], { x: RX, y: cy, w: W, h: 0.8, fontSize: 9, color: TXT, fontFace: F, isTextBox: true, margin: 0, paraSpaceAfter: 2, lineSpacingMultiple: 1.1 });

  const ry2 = cy + 0.9, rh2 = y0 + ch - 0.14 - ry2;
  s.addShape(pres.ShapeType.roundRect, { x: RX, y: ry2, w: W, h: rh2, rectRadius: 0.06, fill: { color: "EEF2F7" }, line: { color: "EEF2F7" } });
  s.addText([
    { text: "판정 규칙  —  실험 전에 고정", options: { bold: true, color: NAVY, breakLine: true } },
    { text: "① 통계적 유의성  p ≤ 0.05 : 가짜 인자(잡음) 수준보다 확실히 큰가", options: { color: TXT, breakLine: true } },
    { text: "② 분산 기여율  ≥ 2% : 응답 변동의 2% 이상을 차지할 만큼 큰가", options: { color: TXT, breakLine: true } },
    { text: "→ 둘 다 만족하면 '영향 있음', 응답 7개 모두에서 영향 없으면 고정", options: { bold: true, color: "0088A6" } }
  ], { x: RX + 0.16, y: ry2, w: W - 0.3, h: rh2, fontSize: 8.8, valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });

  s.addNotes("후보 변수 11개 중 영향 있는 변수만 골라내기 위해 선별 실험을 했습니다. 기법은 DSD, 확정적 선별 설계로, 29번 해석으로 11개 변수를 판정하는 표준 실험표입니다. 왼쪽 표에서 한 줄이 해석 한 번이고, 매번 변수 하나만 중간값, 나머지는 최소·최대값에 둡니다. 아래 절반은 위 절반을 정반대로 뒤집은 것이고, 마지막 한 번은 전부 중간값입니다. 여기에 형상에 아무 영향도 주지 않는 가짜 인자 3개를 같이 넣었습니다. 오른쪽은 최고온도 예시인데, 가짜 인자에서도 0.15℃ 정도 차이가 나는데, 이게 잡음 수준입니다. 1차 핀 개수는 2.5℃로 이보다 훨씬 커서 영향 있는 변수로, 1차 핀 두께는 0.19℃로 잡음과 비슷해 최고온도에는 영향 없는 것으로 판정합니다. 판정 규칙은 결과를 보기 전에 고정했습니다.");
}

/* ───────────── 6. [01] 선별 결과 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "03", S3, "선별 결과 및 활성 변수 확정");
  const y0 = 1.30, ch = 4.55;
  card(s, M, y0, 12.23, ch);
  cardTitle(s, M, y0, "변수별 분산 기여율 (%)  —  DSD 29회");
  s.addText("분산 기여율 = 응답 변동 중 그 변수가 설명하는 비율", { x: M + 5.6, y: y0 + 0.22, w: 6.3, h: 0.36, fontSize: 9, color: MUTED, align: "right", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
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
  s.addText("색 칸 = 영향 인정 (p ≤ 0.05 그리고 기여율 ≥ 2%)  ·  회색 숫자 = 영향 없음  ·  고정값: 주효과가 유의한 목적함수(차압)가 유리한 끝값, 없으면 범위 중앙",
    { x: M + 0.34, y: y0 + 4.18, w: 11.55, h: 0.26, fontSize: 8.8, color: MUTED, italic: true, fontFace: F, isTextBox: true, margin: 0 });

  bottomStrip(s, [
    ["1차 핀 개수", "차압 56% · 최고온도 52% · 1차 균일도 52%"],
    ["2차 핀 개수", "온도편차 37% · 2차 균일도 51%"],
    ["분기 입구 두께", "분기비 84% — 전원모듈로 가는 유량을 사실상 결정"]
  ]);
  s.addNotes("표의 숫자는 분산 기여율, 즉 응답 변동 중 그 변수가 설명하는 비율이다. 11개 중 8개가 활성, 입구 각도·중간 각도·출구 유로 두께 3개는 어떤 응답에서도 기준을 넘지 못해 고정했다. 눈여겨볼 점은 1차 핀 개수가 1차 균일도를, 2차 핀 개수가 2차 균일도를 각각 좌우한다는 것이다. 핀을 1차·2차로 나눈 판단이 데이터로 뒷받침된다.");
}

/* ───────────── 7. [02] 활성 변수 실험계획 (OLHD) ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "03", S3, "활성 변수 실험계획  —  OLHD (최적라틴방격법)");
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
    { text: "왼쪽: 핀 갭 제약(핀이 많을수록 두께 상한이 낮아짐) 영역 안에만 분포", options: { bullet: true, breakLine: true } },
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
    ["실험계획법", "최적라틴방격법(OLHD) — 각 변수 범위를 80구간으로 나눠\n구간마다 한 점씩 + 점 간 최소 거리 최대화 → 균일 분포"]
  ], [1.2, 4.1], { rowH: 0.36 });
  s.addShape(pres.ShapeType.roundRect, { x: CX2 + 0.34, y: y0 + 4.02, w: 5.3, h: 1.2, rectRadius: 0.06, fill: { color: "E8F6FA" }, line: { color: ACCENT, width: 0.75 } });
  s.addText([
    { text: "핀 개수를 먼저 고르게 배치", options: { bold: true, color: NAVY, breakLine: true } },
    { text: "핀 개수가 가장 중요한 변수라서 10~24개 전 범위에 고르게 먼저 두고, 두께는 그 개수에서 만들 수 있는 범위로 맞춤", options: { color: TXT, breakLine: true } },
    { text: "두께를 먼저 정하면 22~24개 설계가 80점 중 1~2점밖에 안 나옴", options: { color: MUTED } }
  ], { x: CX2 + 0.5, y: y0 + 4.02, w: 5.0, h: 1.2, fontSize: 9.3, valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2, paraSpaceAfter: 2 });
  s.addNotes("활성 변수 8개로 최적라틴방격법(OLHD) 80점을 해석했다. OLHD는 각 변수의 범위를 80구간으로 나눠 구간마다 한 점씩 쓰고, 점 사이 최소 거리가 최대가 되도록 배치해 적은 점으로도 설계공간을 고르게 채우는 실험계획법이다. 핀 개수가 가장 중요한 변수로 나왔기 때문에 개수를 10~24개 전 범위에 고르게 먼저 두고, 두께는 그 개수에서 만들 수 있는 범위로 맞췄다.");
}

/* ───────────── 8. [02] GPR ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "04", S4, "대리모델  —  가우시안 프로세스 회귀 (GPR)");
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
  s.addText("실험점 사이가 멀수록\n불확실성이 커짐", { x: PX + tx(0.56), y: PY + 0.1, w: 1.7, h: 0.44, fontSize: 8.5, bold: true, color: "0088A6", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.1 });
  s.addText("설계변수", { x: PX, y: PY + PH + 0.04, w: PW, h: 0.22, fontSize: 8.5, color: MUTED, align: "center", fontFace: F, isTextBox: true, margin: 0 });
  // 범례
  const ly = y0 + 4.12;
  s.addShape(pres.ShapeType.ellipse, { x: M + 0.55, y: ly + 0.05, w: 0.13, h: 0.13, fill: { color: "FFFFFF" }, line: { color: NAVY, width: 1.5 } });
  s.addText("해석 결과 (학습 데이터)", { x: M + 0.75, y: ly, w: 1.7, h: 0.24, fontSize: 8.5, color: TXT, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  s.addShape(pres.ShapeType.line, { x: M + 2.45, y: ly + 0.12, w: 0.3, h: 0, line: { color: NAVY, width: 2 } });
  s.addText("예측 평균", { x: M + 2.82, y: ly, w: 0.8, h: 0.24, fontSize: 8.5, color: TXT, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  s.addShape(pres.ShapeType.rect, { x: M + 3.55, y: ly + 0.04, w: 0.3, h: 0.16, fill: { color: ACCENT, transparency: 72 }, line: { color: ACCENT, transparency: 100 } });
  s.addText("불확실성 (±2σ, 약 95%)", { x: M + 3.92, y: ly, w: 1.6, h: 0.24, fontSize: 8.5, color: TXT, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  s.addShape(pres.ShapeType.roundRect, { x: M + 0.34, y: y0 + 4.52, w: 5.3, h: 0.72, rectRadius: 0.06, fill: { color: "EEF2F7" }, line: { color: "EEF2F7" } });
  s.addText("해석(1회 약 17분) 없이도 아무 설계나 성능을 수 초 안에 예측하고,\n그 예측을 얼마나 믿을 수 있는지까지 함께 알려줌", { x: M + 0.5, y: y0 + 4.52, w: 5.0, h: 0.72, fontSize: 9.5, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });

  card(s, CX2, y0, CW, ch);
  cardTitle(s, CX2, y0, "GPR을 쓴 이유");
  const why = [
    ["예측값 + 불확실성", "예측과 함께 신뢰구간을 제공"],
    ["적은 데이터로 학습", "해석 수십 ~ 수백 점 규모에 적합"],
    ["민감도 해석", "학습된 모델로 Sobol 지수 · 교호작용 산출 (03)"],
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
    ["커널", "Matern(ν = 2.5) + ARD(변수별 길이척도)\n— 매끄러운 응답 가정, 변수마다 민감도 따로 학습"],
    ["전처리", "차압은 로그 변환 (값의 범위가 넓음)"]
  ], [1.2, 4.1], { rowH: 0.36 });
  s.addNotes("가우시안 프로세스 회귀(GPR)는 해석 결과를 학습해 해석하지 않은 설계의 성능을 예측하는 대리모델이다. 다른 회귀 모델과 달리 예측값과 함께 불확실성(신뢰구간)을 준다. 실험점이 촘촘한 곳은 불확실성이 작고, 실험점 사이가 먼 곳은 커진다. 불확실성이 큰 곳은 정보가 부족한 곳이라, 차월 적응 샘플링에서 어디를 추가로 해석할지 정하는 데 쓴다.");
}

/* ───────────── 10. [03] 예측값 · 실측값 비교 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "04", S4, "예측값 · 실측값 비교  —  10-fold 교차검증");
  const fmt = { pressure_drop: "0", temp_std: "0.0", max_temp: "0", std_pass1: "0.00", std_pass2: "0.00", power_module_flow: "0.0", weight: "0.00" };
  const unit = { pressure_drop: "Pa", temp_std: "°C", max_temp: "°C", std_pass1: "LPM", std_pass2: "LPM", power_module_flow: "-", weight: "kg" };
  const W = 2.9, G = (12.23 - 4 * W) / 3, H = 2.55;
  ORDER.forEach((rp, k) => {
    const r = Math.floor(k / 4), c = k % 4;
    const x = M + c * (W + G), y = 1.24 + r * (H + 0.16);
    const cv = DATA.cv[rp];
    const idx = cv.y.map((_, i) => i).sort((a, b) => cv.y[a] - cv.y[b]);
    const ys = idx.map(i => cv.y[i]), ps = idx.map(i => cv.p[i]);
    const step = { pressure_drop: 500, temp_std: 0.2, max_temp: 2, std_pass1: 0.02, std_pass2: 0.01, power_module_flow: 0.1, weight: 0.05 }[rp];
    const lo0 = Math.min(...ys, ...ps), hi0 = Math.max(...ys, ...ps);
    const lo = Math.floor(lo0 / step) * step, hi = Math.ceil(hi0 / step) * step;
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
  s.addText("교차검증 R²  (결정계수)", { x: x + 0.2, y: y + 0.14, w: W - 0.4, h: 0.28, fontSize: 10, color: ICE, fontFace: F, isTextBox: true, margin: 0 });
  s.addText("0.89 ~ 1.00", { x: x + 0.2, y: y + 0.4, w: W - 0.4, h: 0.55, fontSize: 26, bold: true, color: "FFFFFF", fontFace: F, isTextBox: true, margin: 0, valign: "middle" });
  s.addText([
    { text: "1에 가까울수록 정확 — 0.9 = 응답 변동의 90%를 설명", options: { bold: true, color: "7FD6E8", breakLine: true } },
    { text: "10-fold: 80점을 10묶음으로 나눠 한 묶음씩 빼고 학습 → 뺀 묶음을 예측", options: { breakLine: true } },
    { text: "→ 학습에 안 쓴 설계에 대한 정확도", options: { bold: true } }
  ], { x: x + 0.2, y: y + 1.0, w: W - 0.4, h: 1.42, fontSize: 9, color: "FFFFFF", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2, paraSpaceAfter: 3, valign: "top" });

  s.addText("점 = 설계 1개  ·  빨간 선 = 예측값 = 실측값 (선에 가까울수록 정확)",
    { x: M, y: 6.82, w: 12.23, h: 0.26, fontSize: 8.5, color: MUTED, italic: true, fontFace: F, isTextBox: true, margin: 0 });
  s.addNotes("10-fold 교차검증으로 정확도를 확인했다. 80점을 10묶음으로 나눠 한 묶음씩 빼고 학습한 모델로 빠진 묶음을 예측했다. 즉 모델이 처음 보는 설계를 얼마나 맞히는지 본 것이다. 점이 빨간 대각선에 가까울수록 정확하다. 결정계수 R²는 1에 가까울수록 정확한데, 응답 7개 모두 0.89 이상이고 2차 균일도가 0.893으로 가장 낮다.");
}

/* ───────────── 11. [03] 변수별 민감도 및 교호작용 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "04", S4, "변수별 민감도 및 교호작용  —  Sobol 지수");
  const y0 = 1.30, ch = 4.55;

  // 좌 — 1순위 변수 비교
  card(s, M, y0, CW, ch);
  cardTitle(s, M, y0, "응답별 1순위 변수  —  DSD vs GPR");
  let hit = 0;
  const rows = [[hdr("응답"), hdr("DSD 기여율 (29회)"), hdr("GPR Sobol S1 (80점)"), { text: "일치", options: { bold: true, color: NAVY, fill: { color: "EEF2F7" }, align: "center" } }]];
  ORDER.forEach(rp => {
    const a = DATA.dsd_top[rp][0], b = sobolRank(rp)[0];
    const same = a === b; if (same) hit++;
    rows.push([RL[rp], VL[a], VL[b], { text: same ? "●" : "△", options: { bold: true, color: same ? NAVY : "0088A6", align: "center" } }]);
  });
  tbl(s, M + 0.34, y0 + 0.74, 5.3, rows, [1.05, 1.65, 1.9, 0.7], { rowH: 0.36 });
  const wS1 = Object.values(DATA.sobol.weight.S1).sort((p, q) => q - p).slice(0, 4);
  s.addText(`● 일치   △ 중량은 핀 변수 4개가 ${Math.round(wS1[3] * 100)} ~ ${Math.round(wS1[0] * 100)}%로 비슷해 순위 차이가 의미 없음`,
    { x: M + 0.34, y: y0 + 3.7, w: 5.3, h: 0.24, fontSize: 8.5, color: MUTED, fontFace: F, isTextBox: true, margin: 0 });
  s.addText([{ text: `${hit} / 7`, options: { bold: true, color: NAVY, fontSize: 18 } }, { text: "   응답에서 1순위 일치 — 서로 다른 방법 · 데이터로 같은 결론", options: { color: TXT, fontSize: 9.5 } }],
    { x: M + 0.34, y: y0 + 3.98, w: 5.3, h: 0.42, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

  // 우 — 교호작용 비율
  card(s, CX2, y0, CW, ch);
  cardTitle(s, CX2, y0, "교호작용 비율  —  1 − ΣS1");
  s.addText("응답 변동 중 주효과(S1)로 설명되지 않는 부분 = 변수끼리 얽힌 효과",
    { x: CX2 + 0.34, y: y0 + 0.62, w: 5.3, h: 0.36, fontSize: 8.6, color: MUTED, fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.1 });
  const BX = CX2 + 1.5, BW = 3.45, VMAX = 0.20;
  ORDER.forEach((rp, i) => {
    const v = interShare(rp), yy = y0 + 1.06 + i * 0.355;
    const hot = rp === "std_pass1" || rp === "std_pass2";
    s.addText(RL[rp], { x: CX2 + 0.34, y: yy, w: 1.1, h: 0.28, fontSize: 9.5, bold: hot, color: hot ? NAVY : TXT, align: "right", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addShape(pres.ShapeType.rect, { x: BX, y: yy + 0.05, w: BW, h: 0.18, fill: { color: "F0F3F7" }, line: { color: "F0F3F7" } });
    s.addShape(pres.ShapeType.rect, { x: BX, y: yy + 0.05, w: Math.max(0.02, BW * Math.min(v / VMAX, 1)), h: 0.18, fill: { color: hot ? ACCENT : "9FB0C6" }, line: { color: hot ? ACCENT : "9FB0C6" } });
    s.addText(`${(v * 100).toFixed(0)}%`, { x: BX + BW + 0.06, y: yy, w: 0.55, h: 0.28, fontSize: 9.5, bold: true, color: hot ? "0088A6" : MUTED, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });
  const pS1 = DATA.sobol.std_pass2.S1.power_input_thick, pST = DATA.sobol.std_pass2.ST.power_input_thick;
  s.addShape(pres.ShapeType.roundRect, { x: CX2 + 0.34, y: y0 + 3.6, w: 5.3, h: 0.8, rectRadius: 0.06, fill: { color: "E8F6FA" }, line: { color: ACCENT, width: 0.75 } });
  s.addText([
    { text: `예) 2차 균일도 — 분기 입구 두께: 주효과 지수 S1 ${Math.round(pS1 * 100)}% → 총효과 지수 ST ${Math.round(pST * 100)}%`, options: { bold: true, color: NAVY, breakLine: true } },
    { text: "균일도는 변수별 개별 조정으로 최적점 탐색 곤란 → 대리모델 기반 최적화", options: { color: TXT } }
  ], { x: CX2 + 0.5, y: y0 + 3.6, w: 5.0, h: 0.8, fontSize: 9.2, valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });

  bottomStrip(s, [
    ["핀 개수가 성능을 좌우", "1 · 2차 핀 개수가 응답 5개에서 1순위"],
    ["DSD와 GPR 결론 일치", `서로 다른 방법 · 데이터인데 1순위 ${hit}/7 일치`],
    ["균일도는 교호작용이 큼", "13 ~ 19% → DSD로는 분리 못 하는 부분을 GPR로 확인"]
  ]);
  s.addNotes("왼쪽은 응답마다 1순위 변수를 DSD 분산 기여율(29회)과 GPR 기반 Sobol 주효과 지수 S1(80점 학습)에서 각각 뽑아 비교한 것이다. 방법도 데이터도 다른데 7개 중 6개가 같았고, 중량은 핀 변수 4개가 비슷하게 영향을 줘서 순위 차이에 의미가 없다. 오른쪽은 DSD로는 분리할 수 없는 교호작용의 비율로, 1에서 주효과 지수의 합을 뺀 값이다. 온도나 분기비는 거의 주효과로 설명되지만, 1차·2차 균일도는 13~19%가 교호작용이다. 예를 들어 분기 입구 두께는 2차 균일도에 주효과 지수 7% 정도지만, 교호작용까지 포함한 총효과 지수는 18%다. 그래서 균일도는 변수를 하나씩 조정해서는 최적점을 찾기 어렵고, 대리모델 기반으로 함께 탐색해야 한다.");
}

/* ───────────── 12. [03] 한계 및 차월 계획 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "04", S4, "한계 및 차월 계획");
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
    { text: "값 자체가 0에 가까워 작은 오차도 크게 보임", options: { bullet: true, breakLine: true } },
    { text: `분기 이후 구간이라 여러 변수가 함께 작용 — 교호작용 ${Math.round(interShare("std_pass2") * 100)}%로 응답 중 최대`, options: { bullet: true, breakLine: true } },
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
  s.addText("요   약", { x: M + 0.42, y: by + 0.16, w: 4, h: 0.3, fontSize: 11, bold: true, color: ACCENT, fontFace: F, isTextBox: true, margin: 0, charSpacing: 1 });
  [["11 → 8", "변수 선별 (DSD 29회)"], ["80 점", "활성 변수 실험계획 (OLHD)"], ["0.89 ~ 1.00", "대리모델 교차검증 R²"]].forEach(([v, l], i) => {
    const x = M + 0.42 + i * 3.95;
    s.addText(v, { x, y: by + 0.5, w: 3.6, h: 0.62, fontSize: 26, bold: true, color: "FFFFFF", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(l, { x, y: by + 1.12, w: 3.6, h: 0.3, fontSize: 10, color: ICE, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });
  s.addNotes("가장 정확도가 낮은 응답은 2차 균일도다. 값 자체가 0에 가깝고, 분기 이후 구간이라 교호작용이 응답 중 가장 크다. 80점만으로는 이 영역을 충분히 덮지 못했다. 차월에는 대리모델의 불확실성이 큰 지점을 골라 해석을 추가하는 적응 샘플링으로 이 부분을 보강하고, 그 위에서 다목적 최적화로 파레토 최적해를 찾는다.");
}

/* ───────────── 부록 A-1. Icepak GUI 설정 절차 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "A-1", "부록", "Icepak 해석 모델 GUI 설정 절차");
  const steps = [
    ["프로젝트 생성", "새 프로젝트 · 디자인 생성"],
    ["형상 불러오기", "STEP 불러오기 · 부품 이름·재질 지정"],
    ["유체 영역", "박스 생성 → 형상 Subtract → 분리"],
    ["경계조건", "발열원 · 팬(입구) · 개구부(출구)"],
    ["메시", "유체 영역 로컬 메시 · 글로벌 메시"],
    ["측정면", "유로 단면 · 분기 입구 측정면 생성"],
    ["해석 · 추출", "정상상태 해석 → Fields Summary 추출"]
  ];
  const W = 2.86, G = 0.263, FH = 2.05;
  steps.forEach(([h, d], i) => {
    const r = Math.floor(i / 4), c = i % 4;
    const x = M + c * (W + G), y = 1.28 + r * 2.9;
    s.addShape(pres.ShapeType.ellipse, { x, y, w: 0.28, h: 0.28, fill: { color: NAVY }, line: { color: NAVY } });
    s.addText(String(i + 1), { x, y, w: 0.28, h: 0.28, fontSize: 9, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(h, { x: x + 0.38, y: y - 0.02, w: W - 0.38, h: 0.32, fontSize: 11, bold: true, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addShape(pres.ShapeType.roundRect, { x, y: y + 0.40, w: W, h: FH, rectRadius: 0.05, fill: { color: CARD }, line: { color: "C3CDDA", width: 1, dashType: "dash" } });
    s.addText("GUI 캡처", { x, y: y + 0.40, w: W, h: FH, fontSize: 10, bold: true, color: "B5C0CF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(d, { x, y: y + 0.40 + FH + 0.05, w: W, h: 0.3, fontSize: 9, color: MUTED, fontFace: F, isTextBox: true, margin: 0 });
  });
  // 8번째 칸 — 요약
  const x = M + 3 * (W + G), y = 1.28 + 2.9;
  s.addShape(pres.ShapeType.roundRect, { x, y: y + 0.40, w: W, h: FH, rectRadius: 0.06, fill: { color: NAVY }, line: { color: NAVY } });
  s.addText([{ text: "위 7단계를", options: { breakLine: true } },
             { text: "스크립트 리코더로 기록", options: { breakLine: true, bold: true } },
             { text: "→ 코드화하여", options: { breakLine: true } },
             { text: "매 회차 자동 수행", options: { bold: true, color: "7FD6E8" } }],
    { x: x + 0.2, y: y + 0.40, w: W - 0.4, h: FH, fontSize: 11, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.3 });
}

/* ───────────── A-1. 부록 — DSD 구성 원리 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "A-2", "부록", "DSD 구성 원리  (질의응답용)");
  const y0 = 1.30, ch = 5.55, W = 5.3;

  // 좌 — 회의 행렬
  card(s, M, y0, CW, ch);
  cardTitle(s, M, y0, "기본 14회의 정체  —  회의 행렬");
  const X = M + 0.34;
  s.addText([
    { text: "규칙 ①  대각선은 0 (해석마다 변수 하나만 중간값)", options: { breakLine: true } },
    { text: "규칙 ②  나머지는 +1 또는 −1 (최대값 또는 최소값)", options: { breakLine: true } },
    { text: "규칙 ③  아무 두 변수를 골라도, 같은 쪽인 횟수 = 반대쪽인 횟수 (직교)", options: { bold: true, color: NAVY } }
  ], { x: X, y: y0 + 0.66, w: W, h: 0.86, fontSize: 9.3, color: TXT, valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });
  s.addText("변수 4개 예시", { x: X, y: y0 + 1.66, w: W, h: 0.26, fontSize: 10.5, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0 });
  const hc = (t) => ({ text: t, options: { bold: true, color: NAVY, fill: { color: "EEF2F7" }, align: "center" } });
  const z = { text: "0", options: { align: "center", bold: true, color: "FFFFFF", fill: { color: "8FB0D4" } } };
  const p = { text: "+", options: { align: "center", bold: true, color: NAVY } };
  const n = { text: "−", options: { align: "center", bold: true, color: NAVY } };
  tbl(s, X, y0 + 1.96, W, [
    [hdr("해석"), hc("A"), hc("B"), hc("C"), hc("D")],
    ["1", z, p, p, p],
    ["2", n, z, p, n],
    ["3", n, n, z, p],
    ["4", n, p, n, z]
  ], [1.3, 1.0, 1.0, 1.0, 1.0], { rowH: 0.3, fontSize: 10 });
  s.addShape(pres.ShapeType.roundRect, { x: X, y: y0 + 3.62, w: W, h: 1.7, rectRadius: 0.06, fill: { color: "F7F9FC" }, line: { color: LINE, width: 0.75 } });
  s.addText([
    { text: "A와 B가 함께 값을 갖는 해석은 3번 · 4번 두 번뿐", options: { color: TXT, breakLine: true } },
    { text: "3번: A −, B − → 같은 쪽   /   4번: A −, B + → 반대쪽", options: { bold: true, color: NAVY, breakLine: true } },
    { text: "→ 같은 쪽 1번, 반대쪽 1번 (다른 두 변수도 모두 동일)", options: { color: TXT, breakLine: true } },
    { text: "1번 행만 정하면 나머지는 규칙 ③을 맞추다 보면 자동으로 채워짐", options: { color: MUTED, breakLine: true } },
    { text: "본 과제 14 × 14는 Paley 구성법으로 코드가 자동 생성 · 검증", options: { color: MUTED } }
  ], { x: X + 0.16, y: y0 + 3.62, w: W - 0.3, h: 1.7, fontSize: 9, valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.3 });

  // 우 — 거울상
  card(s, CX2, y0, CW, ch);
  cardTitle(s, CX2, y0, "거울상을 붙이는 이유");
  const RX = CX2 + 0.34;
  s.addText("주효과 = 변수 하나만의 효과   ·   교호작용 = 두 변수가 함께 바뀔 때의 추가 효과", { x: RX, y: y0 + 0.66, w: W, h: 0.3, fontSize: 9, color: MUTED, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  const sg = (t) => ({ text: t, options: { align: "center", bold: true, color: NAVY, fontSize: 10 } });
  const keep = (t, col) => ({ text: t, options: { align: "center", bold: true, color: col, fill: { color: "F7F9FC" } } });
  tbl(s, RX, y0 + 1.1, W, [
    [hdr(""), hc("주효과 A"), hc("주효과 B"), hc("교호작용 A×B"), hc("곡률 A²")],
    ["기본 행  x", sg("+"), sg("−"), sg("−"), sg("+")],
    ["거울상  −x", sg("−"), sg("+"), sg("−"), sg("+")],
    [{ text: "쌍에서", options: { bold: true, color: NAVY, fill: { color: "F7F9FC" } } }, keep("부호 반전", NAVY), keep("부호 반전", NAVY), keep("부호 유지", "0088A6"), keep("부호 유지", "0088A6")]
  ], [1.1, 1.0, 1.0, 1.2, 1.0], { rowH: 0.3, fontSize: 9 });
  s.addShape(pres.ShapeType.roundRect, { x: RX, y: y0 + 2.5, w: W, h: 1.3, rectRadius: 0.06, fill: { color: "EEF2F7" }, line: { color: "EEF2F7" } });
  s.addText([
    { text: "쌍의 차이 → 주효과만 남음", options: { bold: true, color: NAVY, breakLine: true } },
    { text: "쌍의 평균 → 교호작용 · 곡률만 남음", options: { bold: true, color: "0088A6", breakLine: true } },
    { text: "→ 주효과가 교호작용 · 곡률과 섞이지 않음", options: { color: TXT } }
  ], { x: RX + 0.16, y: y0 + 2.5, w: W - 0.3, h: 1.3, fontSize: 9.5, valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.35 });
  s.addText([
    { text: "중심점 1회", options: { bold: true, color: NAVY, breakLine: true } },
    { text: "모든 변수 중간값 → 곡률(중간값이 나은지) 판단의 기준점", options: { color: TXT, breakLine: true } },
    { text: "한계", options: { bold: true, color: NAVY, breakLine: true } },
    { text: "교호작용끼리는 서로 일부 섞임 (부분 교락)", options: { color: TXT } }
  ], { x: RX, y: y0 + 4.0, w: W, h: 1.3, fontSize: 9.3, valign: "top", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.3 });
  s.addNotes("질문이 나올 때만 쓰는 부록이다. 기본 14회는 회의 행렬이라는 표로, 대각선은 0, 나머지는 ±1이고, 아무 두 변수를 골라도 같은 쪽인 횟수와 반대쪽인 횟수가 같다. 거울상은 기본 14회의 부호를 모두 뒤집은 것으로, 쌍에서 주효과는 부호가 뒤집히고 교호작용·곡률은 그대로라 주효과가 교호작용·곡률과 섞이지 않는다.");
}

pres.writeFile({ fileName: (process.env.OUT || __dirname + "/통합_AI기반_자동해석_및_대리모델.pptx") }).then(f => console.log("생성 완료:", f));
