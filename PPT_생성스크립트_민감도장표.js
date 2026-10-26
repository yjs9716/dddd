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
const VL = { input_thick: "입구 유로 두께", power_input_thick: "분기 입구 두께", mid_thick: "중간 유로 두께", mid_input_thick: "중간 입구 두께",
  fin_thick_1: "1차 핀 두께", fin_count_1: "1차 핀 개수", fin_thick_2: "2차 핀 두께", fin_count_2: "2차 핀 개수" };
const RL = { pressure_drop: "차압", temp_std: "온도편차", max_temp: "최고온도", std_pass1: "1차 균일도", std_pass2: "2차 균일도", power_module_flow: "분기비", weight: "중량" };
const ORDER = Object.keys(RL), VARS = Object.keys(VL);
const inter = (rp) => Math.max(0, 1 - Object.values(DATA.sobol[rp].S1).reduce((a, b) => a + b, 0));
function hexMix(a, b, t) {
  const pa = [0, 2, 4].map(i => parseInt(a.substr(i, 2), 16)), pb = [0, 2, 4].map(i => parseInt(b.substr(i, 2), 16));
  return pa.map((v, i) => Math.round(v + (pb[i] - v) * t).toString(16).padStart(2, "0")).join("").toUpperCase();
}
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "04", "머신러닝 대리모델 구축", "변수별 민감도 및 교호작용  —  Sobol 지수");
  const y0 = 1.30, ch = 4.55;

  // 좌 — 민감도 히트맵 (총효과 ST)
  const LW = 7.0;
  card(s, M, y0, LW, ch);
  cardTitle(s, M, y0, "변수별 민감도  —  총효과 지수 ST (%)");
  const rows = [[hdr("설계변수"), ...ORDER.map(r => ({ text: RL[r], options: { bold: true, color: NAVY, fill: { color: "EEF2F7" }, align: "center" } }))]];
  VARS.forEach(v => {
    const row = [{ text: VL[v], options: { bold: true, color: NAVY } }];
    ORDER.forEach(r => {
      const val = DATA.sobol[r].ST[v] * 100;
      const tt = Math.min(val / 70, 1);
      row.push(val >= 2
        ? { text: val.toFixed(0), options: { bold: true, align: "center", color: tt > 0.45 ? "FFFFFF" : NAVY, fill: { color: hexMix("D3E7F1", "16305B", tt) } } }
        : { text: val.toFixed(0), options: { align: "center", color: "A9B3C1" } });
    });
    rows.push(row);
  });
  s.addTable(rows, { x: M + 0.3, y: y0 + 0.66, w: LW - 0.6, colW: [1.45, ...ORDER.map(() => (LW - 0.6 - 1.45) / 7)],
    fontSize: 9, fontFace: F, color: TXT, rowH: 0.33, valign: "middle", margin: [1, 3, 1, 3],
    border: [{ pt: 0.5, color: "FFFFFF" }, { pt: 0.5, color: "FFFFFF" }, { pt: 0.5, color: LINE }, { pt: 0.5, color: "FFFFFF" }] });
  s.addText("ST = 그 변수가 응답 변동에 미치는 전체 영향 (혼자 내는 효과 + 다른 변수와 얽힌 효과) · 색 칸 = 2% 이상 (선별 기준과 동일) · GPR 모델로 계산",
    { x: M + 0.3, y: y0 + 3.75, w: LW - 0.6, h: 0.5, fontSize: 8.5, color: MUTED, italic: true, fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.15 });

  // 우 — 교호작용 비율
  const RX0 = M + LW + 0.25, RW = 12.23 - LW - 0.25, RX = RX0 + 0.3, W = RW - 0.6;
  card(s, RX0, y0, RW, ch);
  cardTitle(s, RX0, y0, "교호작용 비율  —  1 − ΣS1");
  s.addText("응답 변동 중 변수끼리 얽혀서 생기는 부분", { x: RX, y: y0 + 0.6, w: W, h: 0.26, fontSize: 8.6, color: MUTED, fontFace: F, isTextBox: true, margin: 0 });
  const BX = RX + 0.95, BW = W - 1.55;
  ORDER.forEach((rp, i) => {
    const v = inter(rp), yy = y0 + 0.96 + i * 0.33, hot = rp === "std_pass1" || rp === "std_pass2";
    s.addText(RL[rp], { x: RX, y: yy, w: 0.88, h: 0.26, fontSize: 9, bold: hot, color: hot ? NAVY : TXT, align: "right", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addShape(pres.ShapeType.rect, { x: BX, y: yy + 0.05, w: BW, h: 0.16, fill: { color: "F0F3F7" }, line: { color: "F0F3F7" } });
    s.addShape(pres.ShapeType.rect, { x: BX, y: yy + 0.05, w: Math.max(0.02, BW * Math.min(v / 0.2, 1)), h: 0.16, fill: { color: hot ? ACCENT : "9FB0C6" }, line: { color: hot ? ACCENT : "9FB0C6" } });
    s.addText(`${(v * 100).toFixed(0)}%`, { x: BX + BW + 0.05, y: yy, w: 0.5, h: 0.26, fontSize: 9, bold: true, color: hot ? "0088A6" : MUTED, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });
  const p1 = DATA.sobol.std_pass2.S1.power_input_thick, pt = DATA.sobol.std_pass2.ST.power_input_thick;
  s.addShape(pres.ShapeType.roundRect, { x: RX, y: y0 + 3.38, w: W, h: 1.0, rectRadius: 0.06, fill: { color: "E8F6FA" }, line: { color: ACCENT, width: 0.75 } });
  s.addText([
    { text: `예) 2차 균일도 — 분기 입구 두께`, options: { bold: true, color: NAVY, breakLine: true } },
    { text: `혼자 ${Math.round(p1 * 100)}% → 얽힌 효과 포함 ${Math.round(pt * 100)}%`, options: { bold: true, color: "0088A6", breakLine: true } },
    { text: "변수를 하나씩 조정해서는 최적점을 찾기 어려움", options: { color: TXT } }
  ], { x: RX + 0.14, y: y0 + 3.38, w: W - 0.28, h: 1.0, fontSize: 9, valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });

  bottomStrip(s, [
    ["핀 개수가 성능을 좌우", "1차 핀 → 차압 · 1차 균일도  /  2차 핀 → 2차 균일도"],
    ["균일도는 교호작용이 큼", "1차 13% · 2차 19% → 변수 조합까지 함께 봐야 함"],
    ["차월 — 적응 샘플링", "80점으로는 데이터 부족 → 불확실성 큰 영역에 해석 추가"]
  ]);
  s.addNotes("GPR 모델로 Sobol 지수를 계산해 변수별 민감도를 봤습니다. 왼쪽 표는 총효과 지수로, 변수가 혼자 내는 효과와 다른 변수와 얽혀서 내는 효과를 합친 전체 영향입니다. 1차 핀 개수는 차압·최고온도·1차 균일도를, 2차 핀 개수는 온도편차·2차 균일도를 좌우합니다. 오른쪽은 교호작용 비율로, 온도나 분기비는 대부분 변수 하나씩의 효과로 설명되지만 균일도는 13~19%가 변수끼리 얽혀서 생깁니다. 이런 복잡한 영역은 80점으로는 아직 데이터가 부족해서, 차월에는 불확실성이 큰 영역에 해석을 추가하는 적응 샘플링을 진행합니다.");
}
pres.writeFile({ fileName: __dirname + "/민감도_장표.pptx" }).then(f => console.log("생성 완료:", f));
