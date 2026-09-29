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
  s.addText("1개월차   |   AI 에이전트 활용방안 및 DOE 결과", { x: M + 0.3, y: 4.92, w: 6.6, h: 0.62, fontSize: 13, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

  s.addText("소속 / 성명 / 발표일자", { x: M + 0.3, y: 5.9, w: 8, h: 0.32, fontSize: 12, color: ICE, fontFace: F, isTextBox: true, margin: 0 });
  s.addNotes("1개월차 산출물 발표. 해석 자동화 파이프라인 구축과 DOE 데이터 확보까지가 이번 달 범위이며, 대리모델 학습은 차월 주제임을 먼저 밝힌다.");
}

/* ─────────────────────────── 2. 목차 ─────────────────────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  s.addText("목   차", { x: M, y: 0.55, w: 6, h: 0.5, fontSize: 26, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0, charSpacing: 3 });

  const items = [
    ["01", "AI 에이전트 기반 개발환경 구축", "1.  망분리 환경에서의 AI 에이전트 활용 체계\n2.  저장소 기반 개발환경 구성\n3.  내부망 실행 구조"],
    ["02", "설계변수 정의 및 설계공간 설정", "1.  형상 및 유동 경로\n2.  설계변수 9종 / 고정 2종\n3.  방열핀 배치 및 가공 제약"],
    ["03", "실험계획법 기반 자동해석 수행 및 데이터 확보", "1.  자동해석 코드 구성\n2.  형상 자동 빌드 및 중량 산출 (SolidWorks)\n3.  해석 모델 자동 구성 및 결과 추출 (Icepak)\n4.  DOE 기법 및 무인 자동 해석 루프\n5.  DOE 데이터 확보 현황"]
  ];
  let y = 1.62;
  items.forEach(([no, t, sub], i) => {
    const h = 1.62;
    card(s, M, y, 12.23, h);
    s.addText(no, { x: M + 0.35, y: y + 0.34, w: 1.3, h: 0.95, fontSize: 44, bold: true, color: ICE, fontFace: F, isTextBox: true, margin: 0, align: "center" });
    s.addText(t, { x: M + 1.85, y: y + 0.28, w: 4.5, h: 1.05, fontSize: 15.5, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0, valign: "middle", lineSpacingMultiple: 1.2 });
    s.addShape(pres.ShapeType.rect, { x: M + 6.55, y: y + 0.34, w: 0.02, h: h - 0.68, fill: { color: LINE }, line: { color: LINE } });
    s.addText(sub, { x: M + 6.95, y: y + 0.3, w: 5.0, h: h - 0.6, fontSize: 11, color: TXT, fontFace: F, isTextBox: true, margin: 0, valign: "middle", lineSpacingMultiple: 1.45 });
    y += h + 0.22;
  });
  s.addText("부록   A-1  Icepak 해석 모델 GUI 설정 절차", { x: M, y: 7.0, w: 12.23, h: 0.26, fontSize: 9.5, color: MUTED, fontFace: F, isTextBox: true, margin: 0 });
  s.addNotes("01은 망분리 환경에서 AI를 어떻게 활용했는지, 02는 무엇을 설계변수로 두었는지, 03은 자동해석을 통해 실제로 확보한 데이터를 다룬다.");
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

/* ───────────── 6. [02] 형상·유동 경로 및 설계변수 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "02", "설계변수 정의 및 설계공간 설정", "형상 및 유동 경로 · 설계변수 선정");

  const y0 = 1.30, ch = 5.6;

  // 좌 — 유동 경로
  card(s, M, y0, CW, ch);
  cardTitle(s, M, y0, "형상 및 유동 경로");
  const steps = [
    ["입    구", "EEF2F7", NAVY],
    ["하단 유로 — 1차 통과", NAVY, "FFFFFF"],
    ["분    기", ACCENT, "FFFFFF"]
  ];
  let yy = y0 + 0.85;
  steps.forEach(([t, f, c]) => {
    s.addShape(pres.ShapeType.roundRect, { x: M + 1.32, y: yy, w: 3.3, h: 0.46, rectRadius: 0.06, fill: { color: f }, line: { color: f } });
    s.addText(t, { x: M + 1.32, y: yy, w: 3.3, h: 0.46, fontSize: 10.5, bold: true, color: c, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText("▼", { x: M + 1.32, y: yy + 0.46, w: 3.3, h: 0.24, fontSize: 8, color: MUTED, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    yy += 0.70;
  });
  // 분기 2갈래
  s.addShape(pres.ShapeType.roundRect, { x: M + 0.4, y: yy, w: 2.4, h: 0.46, rectRadius: 0.06, fill: { color: "EEF2F7" }, line: { color: LINE, width: 0.75 } });
  s.addText("전원공급모듈", { x: M + 0.4, y: yy, w: 2.4, h: 0.46, fontSize: 10, bold: true, color: NAVY, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  s.addShape(pres.ShapeType.roundRect, { x: M + 3.15, y: yy, w: 2.4, h: 0.46, rectRadius: 0.06, fill: { color: NAVY }, line: { color: NAVY } });
  s.addText("상단 유로 — 2차 통과", { x: M + 3.15, y: yy, w: 2.4, h: 0.46, fontSize: 9.5, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  s.addText("▼", { x: M + 1.32, y: yy + 0.46, w: 3.3, h: 0.24, fontSize: 8, color: MUTED, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  s.addShape(pres.ShapeType.roundRect, { x: M + 1.32, y: yy + 0.70, w: 3.3, h: 0.46, rectRadius: 0.06, fill: { color: "EEF2F7" }, line: { color: LINE, width: 0.75 } });
  s.addText("합류  →  출구", { x: M + 1.32, y: yy + 0.70, w: 3.3, h: 0.46, fontSize: 10.5, bold: true, color: NAVY, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

  body(s, M + 0.34, y0 + 4.15, 5.3, 1.1,
    [{ text: "총 유량 4 LPM 고정 / 발열채널 9개 (채널당 40 W)", options: { bullet: true, breakLine: true } },
     { text: "분기 구조 — 한쪽 경로가 유량을 많이 가져가면 반대쪽은 필연적으로 감소", options: { bullet: true, breakLine: true } },
     { text: "변수 간 상호작용이 커 개별 튜닝으로는 최적점 탐색이 어려움", options: { bullet: true } }],
    { fontSize: 10, paraSpaceAfter: 5 });

  // 우 — 설계변수
  card(s, CX2, y0, CW, ch);
  cardTitle(s, CX2, y0, "설계변수 — 자유 9종");
  tbl(s, CX2 + 0.34, y0 + 0.78, 5.3, [
    [hdr("설계변수"), hdr("범위")],
    ["input_thick / input_angle", "13 ~ 25 mm / 90 ~ 150°"],
    ["power_input_thick", "3 ~ 20 mm"],
    ["mid_thick / mid_angle", "10 ~ 25 mm / 90 ~ 140°"],
    ["mid_input_thick", "10 ~ 25 mm"],
    ["output_thick", "13 ~ 35 mm"],
    [{ text: "fin_thick (방열핀 두께)", options: { bold: true, color: NAVY } }, { text: "1.5 ~ 3.0 mm", options: { bold: true, color: NAVY } }],
    [{ text: "fin_count (방열핀 개수)", options: { bold: true, color: NAVY } }, { text: "10 ~ 21 개 (정수)", options: { bold: true, color: NAVY } }]
  ], [3.0, 2.3], { rowH: 0.295 });

  s.addText("고정 파라미터 2종", { x: CX2 + 0.34, y: y0 + 3.08, w: 5.3, h: 0.3, fontSize: 11, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0 });
  tbl(s, CX2 + 0.34, y0 + 3.42, 5.3, [
    [hdr("변수"), hdr("값"), hdr("고정 근거")],
    ["power_output_thick", "25 mm", "사전 분석 결과 트레이드오프 없음"],
    ["fin_height", "8.0 mm", "우회공간 제거 (메싱 안정성 확보)"]
  ], [1.75, 0.85, 2.7], { rowH: 0.34 });

  s.addShape(pres.ShapeType.roundRect, { x: CX2 + 0.34, y: y0 + 4.72, w: 5.3, h: 0.58, rectRadius: 0.06, fill: { color: NAVY } });
  s.addText("9차원 설계공간 → 전수탐색 불가능", { x: CX2 + 0.34, y: y0 + 4.72, w: 5.3, h: 0.58, fontSize: 11.5, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  s.addNotes("변수를 늘리기만 한 것이 아니라, 근거를 갖고 2개를 고정해 탐색 예산을 방열핀 쪽으로 재배분했다는 점을 강조.");
}

/* ───────────── 7. [02] 방열핀 배치 제약 및 평가 항목 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "02", "설계변수 정의 및 설계공간 설정", "방열핀 배치 및 가공 제약 · 평가 항목");

  const y0 = 1.30, ch = 5.6;

  // 좌 — 방열핀 배치
  card(s, M, y0, CW, ch);
  cardTitle(s, M, y0, "방열핀 등간격 배치");

  // 핀뱅크 도식
  const bx = M + 0.4, bw = 5.18, by = y0 + 0.85, bh = 1.05;
  s.addShape(pres.ShapeType.rect, { x: bx, y: by, w: bw, h: bh, fill: { color: "EEF2F7" }, line: { color: NAVY, width: 1 } });
  const nFin = 7, finW = 0.26, gap = (bw - nFin * finW) / (nFin + 1);
  for (let i = 0; i < nFin; i++) {
    s.addShape(pres.ShapeType.rect, { x: bx + gap * (i + 1) + finW * i, y: by + 0.13, w: finW, h: bh - 0.26, fill: { color: NAVY }, line: { color: NAVY } });
  }
  s.addText("t", { x: bx + gap + 0, y: by + bh + 0.02, w: finW, h: 0.24, fontSize: 9, bold: true, color: NAVY, align: "center", fontFace: F, isTextBox: true, margin: 0 });
  s.addText("g", { x: bx + gap * 2 + finW, y: by + bh + 0.02, w: gap, h: 0.24, fontSize: 9, bold: true, color: ACCENT, align: "center", fontFace: F, isTextBox: true, margin: 0 });

  s.addShape(pres.ShapeType.roundRect, { x: M + 0.4, y: y0 + 2.28, w: 5.18, h: 0.9, rectRadius: 0.06, fill: { color: "F7F9FC" }, line: { color: LINE, width: 0.75 } });
  s.addText([{ text: "L = N·t + (N+1)·g", options: { bold: true, color: NAVY, breakLine: true } },
             { text: "g = ( L − N·t ) / ( N+1 )        L = 86.5 mm (핀뱅크 길이)", options: { color: TXT } }],
    { x: M + 0.55, y: y0 + 2.34, w: 4.9, h: 0.78, fontSize: 11, fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.3 });

  body(s, M + 0.34, y0 + 3.35, 5.3, 1.3,
    [{ text: "폐합조건 하나로 벽↔핀 / 핀↔핀 / 핀↔벽 간격이 자동으로 동일", options: { bullet: true, breakLine: true } },
     { text: "갭은 설계변수가 아닌 종속 계산값 — CAD 수식으로 자체 산출", options: { bullet: true, breakLine: true } },
     { text: "가공 제약 : 갭 ≥ 2.5 mm (밀링 가공 한계 · 메시 확보)", options: { bullet: true, bold: true } }],
    { fontSize: 10, paraSpaceAfter: 5 });

  s.addShape(pres.ShapeType.roundRect, { x: M + 0.34, y: y0 + 4.75, w: 5.3, h: 0.55, rectRadius: 0.06, fill: { color: "EEF2F7" }, line: { color: "EEF2F7" } });
  s.addText("두께·개수 조합의 약 70%만 유효 — 두 변수가 독립이 아닌 유효영역 형성", { x: M + 0.45, y: y0 + 4.75, w: 5.1, h: 0.55, fontSize: 9.5, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

  // 우 — 평가 항목
  card(s, CX2, y0, CW, ch);
  cardTitle(s, CX2, y0, "평가 항목 정의");
  tbl(s, CX2 + 0.34, y0 + 0.82, 5.3, [
    [hdr("구분"), hdr("항목")],
    [{ text: "목적함수", options: { bold: true, color: NAVY } }, "차압 (압력강하)"],
    ["", "채널 온도편차"],
    ["", "최고온도"],
    ["", "유량 균일도"],
    [{ text: "제약조건", options: { bold: true, color: NAVY } }, "전원모듈 분기 유량비"],
    ["", "총 중량"]
  ], [1.5, 3.8], { rowH: 0.36 });

  s.addShape(pres.ShapeType.roundRect, { x: CX2 + 0.34, y: y0 + 3.6, w: 5.3, h: 1.5, rectRadius: 0.06, fill: { color: "F7F9FC" }, line: { color: LINE, width: 0.75 } });
  s.addText("본 단계 범위", { x: CX2 + 0.55, y: y0 + 3.76, w: 4.9, h: 0.3, fontSize: 10.5, bold: true, color: ACCENT, fontFace: F, isTextBox: true, margin: 0 });
  s.addText([{ text: "측정 · 기록 대상 항목의 정의까지 수행", options: { bullet: true, breakLine: true } },
             { text: "유량 균일도의 구체적 지표화 방식은 대리모델 구축 단계에서 확정 예정", options: { bullet: true } }],
    { x: CX2 + 0.55, y: y0 + 4.12, w: 4.9, h: 0.9, fontSize: 10, color: TXT, fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25, paraSpaceAfter: 5 });
  s.addNotes("핀 두께와 개수는 독립 변수처럼 보이지만 가공 제약 때문에 서로 묶인다. 이 점이 DOE 실험점 생성 방식에 영향을 준다.");
}

/* ───────────── 8. [03] 자동해석 코드 구성 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "03", "실험계획법 기반 자동해석 수행 및 데이터 확보", "자동해석 코드 구성");

  const y0 = 1.30, ch = 4.55;
  card(s, M, y0, 12.23, ch);
  cardTitle(s, M, y0, "모듈 구성 및 실행 흐름");

  const X0 = M + 0.34, WALL = 11.55;
  // ── main.py 제어 바 ──
  const mY = y0 + 0.72, mH = 0.56;
  s.addShape(pres.ShapeType.roundRect, { x: X0, y: mY, w: WALL, h: mH, rectRadius: 0.07, fill: { color: NAVY }, line: { color: NAVY } });
  s.addText([{ text: "main.py", options: { fontFace: MONO, bold: true, fontSize: 12.5 } },
             { text: "     루프 제어  —  실험점마다 아래 4단계를 순서대로 호출, 실패 시 기록 후 다음 점", options: { fontSize: 10, color: ICE } }],
    { x: X0 + 0.25, y: mY, w: WALL - 2.0, h: mH, color: "FFFFFF", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  s.addShape(pres.ShapeType.roundRect, { x: X0 + WALL - 1.55, y: mY + 0.11, w: 1.35, h: mH - 0.22, rectRadius: 0.1, fill: { color: ACCENT }, line: { color: ACCENT } });
  s.addText("90회 반복", { x: X0 + WALL - 1.55, y: mY + 0.11, w: 1.35, h: mH - 0.22, fontSize: 9.5, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

  // ── 모듈 4개 ──
  const mods = [
    ["실험점 생성", "OLHD.py · fins.py", "설계변수 정의 · 실험점 생성\n갭 가공 제약 반영"],
    ["형상 빌드", "Solidworks.py", "전역변수 갱신 → 리빌드\n질량 · 부피 취득"],
    ["해석", "icepak.py", "해석 모델 구성 → 해석\n결과 추출"],
    ["결과 저장", "result_parser.py", "차압 · 온도 · 유량 · 중량 산출\n결과 누적 저장"]
  ];
  const cW = 2.55, cG = (WALL - 4 * cW) / 3, cY = mY + mH + 0.34, cH = 1.36;
  const arts = ["설계값", "STEP", "CSV"];
  mods.forEach(([h, f, d], i) => {
    const x = X0 + i * (cW + cG);
    // main → 모듈 연결선
    s.addShape(pres.ShapeType.line, { x: x + cW / 2, y: mY + mH, w: 0, h: 0.34, line: { color: "9FB0C6", width: 1, endArrowType: "triangle" } });
    s.addShape(pres.ShapeType.roundRect, { x, y: cY, w: cW, h: cH, rectRadius: 0.07, fill: { color: "FFFFFF" }, line: { color: i === 3 ? ACCENT : "B9C7D8", width: 1.25 }, shadow: sh() });
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.14, y: cY + 0.14, w: 0.3, h: 0.3, fill: { color: i === 3 ? ACCENT : NAVY }, line: { color: i === 3 ? ACCENT : NAVY } });
    s.addText(String(i + 1), { x: x + 0.14, y: cY + 0.14, w: 0.3, h: 0.3, fontSize: 9.5, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(h, { x: x + 0.52, y: cY + 0.12, w: cW - 0.6, h: 0.34, fontSize: 11, bold: true, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(f, { x: x + 0.14, y: cY + 0.52, w: cW - 0.28, h: 0.26, fontSize: 9.5, bold: true, color: i === 3 ? "0088A6" : NAVY2, fontFace: MONO, isTextBox: true, margin: 0 });
    s.addText(d, { x: x + 0.14, y: cY + 0.80, w: cW - 0.28, h: 0.5, fontSize: 8.8, color: TXT, fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.15 });
    // 모듈 간 전달물
    if (i < 3) {
      const ax = x + cW;
      s.addShape(pres.ShapeType.line, { x: ax + 0.05, y: cY + cH / 2, w: cG - 0.1, h: 0, line: { color: ACCENT, width: 1.5, endArrowType: "triangle" } });
      s.addText(arts[i], { x: ax - 0.1, y: cY + cH / 2 - 0.3, w: cG + 0.2, h: 0.24, fontSize: 8.5, bold: true, color: "0088A6", align: "center", fontFace: F, isTextBox: true, margin: 0 });
    }
  });

  // ── 하단: 외부 프로그램 / 입출력 ──
  const eY = cY + cH + 0.30, eH = 0.46;
  const below = [
    ["초기 실험점 90개", "F7F9FC", NAVY, null],
    ["SolidWorks", "E4EAF2", NAVY, "COM API"],
    ["Ansys Icepak", "E4EAF2", NAVY, "PyAEDT"],
    ["결과 데이터셋 (CSV 누적)", "E8F6FA", "0088A6", null]
  ];
  below.forEach(([t, f, c, api], i) => {
    const x = X0 + i * (cW + cG);
    s.addShape(pres.ShapeType.line, { x: x + cW / 2, y: cY + cH, w: 0, h: 0.30, line: { color: api ? NAVY : "C3CDDA", width: 1, dashType: api ? "solid" : "dash", beginArrowType: api ? "triangle" : undefined, endArrowType: "triangle" } });
    if (api) s.addText(api, { x: x + cW / 2 + 0.08, y: cY + cH + 0.02, w: 1.2, h: 0.26, fontSize: 8, color: MUTED, fontFace: MONO, isTextBox: true, margin: 0, valign: "middle" });
    s.addShape(pres.ShapeType.roundRect, { x: x + 0.2, y: eY, w: cW - 0.4, h: eH, rectRadius: 0.08, fill: { color: f }, line: { color: api ? "B9C7D8" : (i === 3 ? ACCENT : LINE), width: 0.75, dashType: api ? "solid" : "dash" } });
    s.addText(t, { x: x + 0.2, y: eY, w: cW - 0.4, h: eH, fontSize: 9.5, bold: true, color: c, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });

  // ── paths.py ──
  const pY = y0 + ch - 0.52;
  s.addShape(pres.ShapeType.line, { x: X0, y: pY - 0.1, w: WALL, h: 0, line: { color: LINE, width: 0.75 } });
  s.addText([{ text: "paths.py", options: { fontFace: MONO, bold: true, color: NAVY } },
             { text: "   작업폴더 · 모델 파일 · 결과 파일 경로를 한 곳에서 관리 — 모든 모듈이 참조", options: { color: MUTED } }],
    { x: X0, y: pY, w: WALL, h: 0.32, fontSize: 9.5, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

  bottomStrip(s, [
    ["프로그램별 모듈 분리", "CAD·해석 제어를 독립 모듈로 구성해 서로 영향 없음"],
    ["단일 출처", "설계변수·경로는 한 파일에서만 정의하고 나머지는 참조"],
    ["실패 격리", "한 점이 실패해도 기록 후 다음 점으로 진행"]
  ]);
  s.addNotes("자동해석은 7개 파일로 구성된다. main.py가 실험점마다 실험점 생성, 형상 빌드, 해석, 결과 저장 모듈을 순서대로 호출하고, 모듈 사이에는 설계값, STEP 파일, 결과 CSV가 전달된다. SolidWorks는 COM API로, Icepak은 PyAEDT로 제어하며, 경로는 paths.py 한 곳에서 관리한다.");
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
    ["발열원", "최고 · 평균 온도", "9"],
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

/* ───────────── 10. [03] DOE 기법 및 무인 자동 해석 루프 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "03", "실험계획법 기반 자동해석 수행 및 데이터 확보", "DOE 기법 선정 및 무인 자동 해석 루프");

  const y1 = 1.30, y2 = 4.18, ch = 2.72;

  // 좌상 — DOE 기법
  card(s, M, y1, CW, ch);
  cardTitle(s, M, y1, "DOE 기법 선정");
  tbl(s, M + 0.34, y1 + 0.78, 5.3, [
    [hdr("방식"), hdr("판정")],
    ["격자 전수탐색", "✕   9차원 조합 수 폭증"],
    ["무작위 샘플링", "✕   설계공간 편중 발생"],
    [{ text: "최적라틴방격법 (OLHD)", options: { bold: true, color: NAVY } }, { text: "○   적은 점으로 균일 분포", options: { bold: true, color: NAVY } }]
  ], [2.5, 2.8], { rowH: 0.34 });
  s.addShape(pres.ShapeType.roundRect, { x: M + 0.34, y: y1 + 2.18, w: 5.3, h: 0.45, rectRadius: 0.06, fill: { color: NAVY } });
  s.addText("초기 실험점 = 10 × 변수 수 = 90 점", { x: M + 0.34, y: y1 + 2.18, w: 5.3, h: 0.45, fontSize: 11, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

  // 우상 — 제약 반영
  card(s, CX2, y1, CW, ch);
  cardTitle(s, CX2, y1, "가공 제약 반영 방식");
  s.addShape(pres.ShapeType.roundRect, { x: CX2 + 0.34, y: y1 + 0.8, w: 5.3, h: 0.78, rectRadius: 0.06, fill: { color: "F7F9FC" }, line: { color: LINE, width: 0.75 } });
  s.addText([{ text: "기각 방식", options: { bold: true, color: MUTED, breakLine: true } },
             { text: "뽑은 뒤 제약 위반이면 폐기 → 후보 30% 낭비 · 층화 붕괴", options: { color: MUTED } }],
    { x: CX2 + 0.5, y: y1 + 0.88, w: 5.0, h: 0.62, fontSize: 9.5, fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });
  s.addShape(pres.ShapeType.roundRect, { x: CX2 + 0.34, y: y1 + 1.7, w: 5.3, h: 0.78, rectRadius: 0.06, fill: { color: "E8F4F8" }, line: { color: ACCENT, width: 0.75 } });
  s.addText([{ text: "채택 방식", options: { bold: true, color: NAVY, breakLine: true } },
             { text: "두께별 허용 개수 범위 안으로 접어 넣어 생성 → 낭비 0 · 층화 유지", options: { color: TXT } }],
    { x: CX2 + 0.5, y: y1 + 1.78, w: 5.0, h: 0.62, fontSize: 9.5, fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });

  // 좌하 — 자동 해석 루프
  card(s, M, y2, CW, ch);
  cardTitle(s, M, y2, "자동 해석 루프");
  const loop = ["DOE 실험점 선정", "CAD 리빌드 · STEP 저장", "Icepak 해석 수행", "결과 파싱 · 데이터 누적"];
  loop.forEach((t, i) => {
    const yy = y2 + 0.76 + i * 0.38;
    s.addShape(pres.ShapeType.ellipse, { x: M + 0.36, y: yy, w: 0.3, h: 0.3, fill: { color: NAVY }, line: { color: NAVY } });
    s.addText(String(i + 1), { x: M + 0.36, y: yy, w: 0.3, h: 0.3, fontSize: 9, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(t, { x: M + 0.78, y: yy, w: 4.8, h: 0.3, fontSize: 10.5, color: TXT, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });
  s.addText("▶   종료 조건까지 자동 반복 — 1회차 약 17분", { x: M + 0.36, y: y2 + 2.28, w: 5.2, h: 0.3, fontSize: 10, bold: true, color: ACCENT, fontFace: F, isTextBox: true, margin: 0 });

  // 우하 — 예외 처리
  card(s, CX2, y2, CW, ch);
  cardTitle(s, CX2, y2, "예외 처리 및 무인 운전");
  tbl(s, CX2 + 0.34, y2 + 0.78, 5.3, [
    [hdr("상황"), hdr("처리")],
    ["형상 미성립", "이력 기록 후 다음 점 진행, 해당 영역 회피"],
    ["솔버 비정상 종료", "자동 재연결 후 동일 실험점 재시도"],
    ["연속 실패", "설정 오류로 판단하고 캠페인 중단"]
  ], [1.55, 3.75], { rowH: 0.36 });
  s.addText("CAD · 해석 프로그램 GUI 비활성화로 장기 연속 구동 확보", { x: CX2 + 0.34, y: y2 + 2.18, w: 5.3, h: 0.3, fontSize: 9.5, color: MUTED, italic: true, fontFace: F, isTextBox: true, margin: 0 });
  s.addNotes("1회 해석에 수십 분이 걸리므로 무인 연속 운전이 전제 조건. 사람이 붙어 있지 않아도 데이터가 쌓이는 구조를 만든 것이 이번 달의 실질적 성과.");
}

/* ───────────── 11. [03] 확보 현황 및 차월 계획 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "03", "실험계획법 기반 자동해석 수행 및 데이터 확보", "DOE 데이터 확보 현황 및 차월 계획");

  const tiles = [
    ["90", "점", "DOE 실험점"],
    ["2.50 ~ 6.41", "mm", "유로 갭 범위"],
    ["1,701 ~ 4,661", "Pa", "차압 분포"],
    ["4.90 ~ 5.24", "kg", "중량 분포"]
  ];
  tiles.forEach(([v, u, l], i) => {
    const x = M + i * 3.15;
    s.addShape(pres.ShapeType.roundRect, { x, y: 1.32, w: 2.85, h: 1.42, rectRadius: 0.06, fill: { color: i === 0 ? NAVY : CARD }, line: { color: i === 0 ? NAVY : LINE, width: 0.75 }, shadow: sh() });
    s.addText([{ text: v, options: { fontSize: i === 0 ? 34 : 21, bold: true, color: i === 0 ? "FFFFFF" : NAVY } },
               { text: "  " + u, options: { fontSize: 11, color: i === 0 ? ICE : MUTED } }],
      { x: x + 0.2, y: 1.52, w: 2.45, h: 0.72, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    s.addText(l, { x: x + 0.2, y: 2.24, w: 2.45, h: 0.3, fontSize: 10, color: i === 0 ? ICE : MUTED, align: "center", fontFace: F, isTextBox: true, margin: 0 });
  });

  card(s, M, 2.96, 12.23, 1.98);
  cardTitle(s, M, 2.96, "확보 범위 및 데이터 구조");
  tbl(s, M + 0.42, 3.56, 11.5, [
    [hdr("핀 두께 / 개수"), "1.5 ~ 3.0 mm / 10 ~ 21 개", hdr("최고온도"), "116.8 ~ 122.9 ℃"],
    [hdr("유로 갭"), "2.500 ~ 6.409 mm  (가공 제약 하한까지 도달)", hdr("데이터 구조"), "설계변수 9종 | 갭 | 목적함수 | 제약조건"]
  ], [2.0, 4.1, 1.7, 3.7], { rowH: 0.38, fontSize: 10 });
  s.addText("설계공간 전 영역에 고르게 분포 — 대리모델 학습 입력으로 사용", { x: M + 0.42, y: 4.42, w: 11.4, h: 0.3, fontSize: 9.5, color: MUTED, italic: true, fontFace: F, isTextBox: true, margin: 0 });

  s.addShape(pres.ShapeType.roundRect, { x: M, y: 5.15, w: 12.23, h: 1.75, rectRadius: 0.06, fill: { color: NAVY }, line: { color: NAVY } });
  s.addText("차 월 계 획", { x: M + 0.42, y: 5.35, w: 3.2, h: 0.32, fontSize: 12, bold: true, color: ACCENT, fontFace: F, isTextBox: true, margin: 0, charSpacing: 1 });
  const next = ["확보 데이터 기반 머신러닝 대리모델(GPR) 학습", "예측값 · 실측값 비교를 통한 정확도 검증", "설계변수별 민감도 산출 및 지배 변수 식별"];
  next.forEach((t, i) => {
    const x = M + 0.42 + i * 3.92;
    s.addText(String(i + 1).padStart(2, "0"), { x, y: 5.78, w: 0.5, h: 0.3, fontSize: 11, bold: true, color: ACCENT, fontFace: F, isTextBox: true, margin: 0 });
    s.addText(t, { x, y: 6.08, w: 3.6, h: 0.62, fontSize: 10.5, color: "FFFFFF", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });
  });
  s.addNotes("이번 달은 데이터 생산 설비를 만들고 초기 데이터셋을 확보한 단계. 다음 달부터 이 데이터를 학습시킨다.");
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

pres.writeFile({ fileName: "/home/user/dddd/1개월차_AI에이전트_활용방안_및_DOE결과.pptx" })
  .then(f => console.log("생성 완료:", f));
