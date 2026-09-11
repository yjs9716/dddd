const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";           // 13.333 x 7.5
pres.author = "학습조직";
pres.title  = "AI 에이전트 활용방안 및 DOE 기반 해석 데이터 확보";

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

/* ─────────────────────────── 1. 표지 ─────────────────────────── */
{
  const s = pres.addSlide();
  s.background = { color: NAVY };
  s.addShape(pres.ShapeType.ellipse, { x: 9.7, y: -1.6, w: 5.4, h: 5.4, fill: { color: NAVY2, transparency: 55 }, line: { color: NAVY2, transparency: 100 } });
  s.addShape(pres.ShapeType.ellipse, { x: 11.2, y: 4.3, w: 3.4, h: 3.4, fill: { color: ACCENT, transparency: 78 }, line: { color: ACCENT, transparency: 100 } });

  s.addText("학습조직 1개월차 산출물", { x: M + 0.3, y: 1.55, w: 8, h: 0.32, fontSize: 12, bold: true, color: ACCENT, fontFace: F, isTextBox: true, margin: 0, charSpacing: 2 });
  s.addText("AI 에이전트 활용방안 및\nDOE 기반 해석 데이터 확보", { x: M + 0.3, y: 2.05, w: 9.2, h: 1.9, fontSize: 38, bold: true, color: "FFFFFF", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.15 });
  s.addText("수냉식 냉각판 유로·방열핀 설계최적화", { x: M + 0.3, y: 4.05, w: 9, h: 0.4, fontSize: 15, color: ICE, fontFace: F, isTextBox: true, margin: 0 });
  s.addShape(pres.ShapeType.rect, { x: M + 0.3, y: 5.05, w: 1.1, h: 0.035, fill: { color: ACCENT }, line: { color: ACCENT } });
  s.addText("소속 / 성명 / 발표일자", { x: M + 0.3, y: 5.3, w: 8, h: 0.32, fontSize: 12, color: ICE, fontFace: F, isTextBox: true, margin: 0 });
  s.addNotes("1개월차 산출물 발표. 해석 자동화 파이프라인 구축과 DOE 데이터 확보까지가 이번 달 범위이며, 대리모델 학습은 차월 주제임을 먼저 밝힌다.");
}

/* ─────────────────────────── 2. 목차 ─────────────────────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  s.addText("목   차", { x: M, y: 0.55, w: 6, h: 0.5, fontSize: 26, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0, charSpacing: 3 });

  const items = [
    ["01", "AI 에이전트 기반 개발환경 구축", "1.  협업 방식 및 모듈 구성\n2.  단일 출처 원칙 및 코드 검증 절차"],
    ["02", "설계변수 정의 및 설계공간 설정", "1.  형상 및 유동 경로\n2.  설계변수 9종 / 고정 2종\n3.  방열핀 배치 및 가공 제약"],
    ["03", "실험계획법(DOE) 기반 데이터 확보", "1.  형상 자동 빌드 및 중량 산출\n2.  DOE 기법 및 무인 자동 해석 루프\n3.  DOE 데이터 확보 현황"]
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
  s.addNotes("01은 개발 방식, 02는 무엇을 변수로 두었는지, 03은 실제로 확보한 데이터를 다룬다.");
}

/* ───────────── 3. [01] 협업 방식 · 모듈 · 단일출처 · 검증 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "01", "AI 에이전트 기반 개발환경 구축", "협업 방식 및 모듈 구성 · 코드 검증 절차");

  const y1 = 1.30, y2 = 4.18, ch = 2.72;

  // 좌상 — 협업 흐름
  card(s, M, y1, CW, ch);
  cardTitle(s, M, y1, "협업 방식");
  const chips = ["설계자", "AI 에이전트", "자동화 코드"];
  chips.forEach((c, i) => {
    const x = M + 0.34 + i * 1.85;
    s.addShape(pres.ShapeType.roundRect, { x, y: y1 + 0.92, w: 1.62, h: 0.52, rectRadius: 0.08, fill: { color: i === 1 ? NAVY : "EEF2F7" }, line: { color: i === 1 ? NAVY : LINE, width: 0.75 } });
    s.addText(c, { x, y: y1 + 0.92, w: 1.62, h: 0.52, fontSize: 10.5, bold: true, color: i === 1 ? "FFFFFF" : NAVY, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    if (i < 2) s.addText("▶", { x: x + 1.62, y: y1 + 0.92, w: 0.23, h: 0.52, fontSize: 9, color: ACCENT, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });
  s.addText("◀   결과 검토 · 이상 징후 피드백", { x: M + 0.34, y: y1 + 1.55, w: 5.2, h: 0.3, fontSize: 9.5, color: ACCENT, fontFace: F, isTextBox: true, margin: 0 });
  body(s, M + 0.34, y1 + 1.92, 5.3, 0.65,
    "요구사항·물리조건 정의부터 지표 정의·검증 방법까지 대화 기반으로 진행\n— 단순 코드 생성이 아닌 설계 판단 단계부터 협업", { fontSize: 10, color: MUTED });

  // 우상 — 구축 모듈
  card(s, CX2, y1, CW, ch);
  cardTitle(s, CX2, y1, "구축 모듈 — 해석 자동화 파이프라인");
  tbl(s, CX2 + 0.34, y1 + 0.78, 5.3, [
    [hdr("모듈"), hdr("역할")],
    ["OLHD / fins", "설계변수·DOE / 핀 배치 수식"],
    ["Solidworks / icepak", "형상 리빌드 / 해석 실행"],
    ["result_parser", "결과 파싱 및 지표 산출"],
    ["main / paths", "루프 제어 / 경로 관리"]
  ], [1.85, 3.45], { rowH: 0.3 });
  body(s, CX2 + 0.34, y1 + 2.25, 5.3, 0.35, "데이터 생성까지의 파이프라인 — 대리모델은 차월 구축", { fontSize: 9.5, color: MUTED, italic: true });

  // 좌하 — 단일 출처 원칙
  card(s, M, y2, CW, ch);
  cardTitle(s, M, y2, "단일 출처(Single Source) 원칙");
  body(s, M + 0.34, y2 + 0.8, 5.3, 1.1,
    [{ text: "같은 값을 두 곳에 두지 않는다", options: { bullet: true, breakLine: true, bold: true } },
     { text: "한쪽만 수정했을 때 조용히 어긋나는 사고를 구조적으로 차단", options: { bullet: true, breakLine: true } },
     { text: "핀뱅크 길이 1곳 수정 → 갭 공식·유로 위치·최대 개수 자동 반영", options: { bullet: true } }],
    { paraSpaceAfter: 5 });
  s.addShape(pres.ShapeType.roundRect, { x: M + 0.34, y: y2 + 1.92, w: 5.3, h: 0.55, rectRadius: 0.06, fill: { color: "EEF2F7" }, line: { color: "EEF2F7" } });
  s.addText("설계변수 · DOE 점수 · 핀 배치 수식 · 채널 수 · 경로  →  각 1개 모듈에서만 정의", { x: M + 0.45, y: y2 + 1.92, w: 5.1, h: 0.55, fontSize: 9.5, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

  // 우하 — 검증 절차
  card(s, CX2, y2, CW, ch);
  cardTitle(s, CX2, y2, "코드 검증 절차");
  s.addText("① 요구사항 정의  ▶  ② AI 코드 생성  ▶  ③ 검증  ▶  ④ 반영", { x: CX2 + 0.34, y: y2 + 0.76, w: 5.3, h: 0.3, fontSize: 10, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0 });
  tbl(s, CX2 + 0.34, y2 + 1.18, 5.3, [
    [hdr("검증 방법"), hdr("실제 적용")],
    ["수식 검산", "중량 산출식 ↔ 수기 계산값 일치"],
    ["전수 검증", "후보 20만 개 → 제약 위반 0건"],
    ["통합 테스트", "해석 없이 생성·파싱 구간 구동 확인"]
  ], [1.55, 3.75], { rowH: 0.32 });
  s.addNotes("AI 출력을 그대로 쓰지 않고 검증을 절차화했다는 점, 그리고 값의 정의 위치를 한 곳으로 고정해 일관성을 유지했다는 점이 핵심.");
}

/* ───────────── 4. [02] 형상·유동 경로 및 설계변수 ───────────── */
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

/* ───────────── 5. [02] 방열핀 배치 제약 및 평가 항목 ───────────── */
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

/* ───────────── 6. [03] 형상 자동 빌드 및 중량 산출 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "03", "실험계획법(DOE) 기반 데이터 확보", "형상 자동 빌드 및 중량 산출");

  const y0 = 1.30, ch = 5.6;

  // 좌 — 형상 빌드
  card(s, M, y0, CW, ch);
  cardTitle(s, M, y0, "Equation Manager 기반 형상 빌드");
  const bsteps = ["전역변수 갱신", "파트·어셈블리 리빌드", "STEP 저장"];
  bsteps.forEach((t, i) => {
    const x = M + 0.34 + i * 1.82;
    s.addShape(pres.ShapeType.roundRect, { x, y: y0 + 0.82, w: 1.6, h: 0.5, rectRadius: 0.07, fill: { color: i === 0 ? NAVY : "EEF2F7" }, line: { color: i === 0 ? NAVY : LINE, width: 0.75 } });
    s.addText(t, { x, y: y0 + 0.82, w: 1.6, h: 0.5, fontSize: 9, bold: true, color: i === 0 ? "FFFFFF" : NAVY, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
    if (i < 2) s.addText("▶", { x: x + 1.6, y: y0 + 0.82, w: 0.22, h: 0.5, fontSize: 9, color: ACCENT, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  });
  tbl(s, M + 0.34, y0 + 1.55, 5.3, [
    [hdr("항목"), hdr("처리 방식")],
    ["변수 기입", "수식 목록에서 변수명 → 인덱스 매핑 후 치환"],
    ["변수명 검증", "없는 변수명이면 즉시 중단 + 실제 변수 목록 출력"],
    ["정수 변수", "핀 개수는 정수 문자열로 기입 (패턴 개수 해석)"],
    ["종속값", "핀 간격은 CAD 수식이 자체 계산 — 이중 계산 방지"],
    ["고정값", "전역변수로 만들지 않고 스케치에 직접 기입"]
  ], [1.3, 4.0], { rowH: 0.45 });
  s.addShape(pres.ShapeType.roundRect, { x: M + 0.34, y: y0 + 4.5, w: 5.3, h: 0.72, rectRadius: 0.06, fill: { color: "EEF2F7" }, line: { color: "EEF2F7" } });
  s.addText("변수명이 어긋나면 형상이 바뀌지 않은 채 해석이 수행될 수 있음\n→ 사전 차단이 데이터 신뢰성의 핵심", { x: M + 0.48, y: y0 + 4.5, w: 5.05, h: 0.72, fontSize: 9.5, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });

  // 우 — 중량 산출
  card(s, CX2, y0, CW, ch);
  cardTitle(s, CX2, y0, "중량 산출");
  s.addShape(pres.ShapeType.roundRect, { x: CX2 + 0.34, y: y0 + 0.8, w: 5.3, h: 1.0, rectRadius: 0.06, fill: { color: "F7F9FC" }, line: { color: LINE, width: 0.75 } });
  s.addText([{ text: "PAO 부피 = 완전충진 형상 부피(상수) − 알루미늄 부피", options: { breakLine: true, color: TXT } },
             { text: "중  량   = 알루미늄 질량 + PAO 부피 × 794 kg/m³", options: { bold: true, color: NAVY } }],
    { x: CX2 + 0.5, y: y0 + 0.9, w: 5.0, h: 0.82, fontSize: 10.5, fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.35 });
  tbl(s, CX2 + 0.34, y0 + 2.0, 5.3, [
    [hdr("항목"), hdr("내용")],
    ["취득 시점", "리빌드 직후 어셈블리에서 질량 특성 일괄 취득"],
    ["반환값 해석", "반환 순서가 미문서화 → CAD 질량특성 패널과 전량 대조하여 부피·질량 위치 확정"],
    ["검산", "산출값이 수기 계산값과 소수점까지 일치 확인"],
    ["교차검증", "해석 측 유체 부피값과 대조, 이상 시 로그 경고"]
  ], [1.3, 4.0], { rowH: 0.5 });
  s.addText("유로(빈 공간)는 형상에 존재하지 않는 개념 → 완전충진 부피 기준으로 역산", { x: CX2 + 0.34, y: y0 + 4.75, w: 5.3, h: 0.4, fontSize: 9.5, color: MUTED, italic: true, fontFace: F, isTextBox: true, margin: 0 });
  s.addNotes("조용히 잘못된 데이터가 쌓이는 실패 모드를 어떻게 막았는지가 이 장의 요지.");
}

/* ───────────── 7. [03] DOE 기법 및 무인 자동 해석 루프 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "03", "실험계획법(DOE) 기반 데이터 확보", "DOE 기법 선정 및 무인 자동 해석 루프");

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

/* ───────────── 8. [03] 확보 현황 및 차월 계획 ───────────── */
{
  const s = pres.addSlide();
  s.background = { color: BG };
  header(s, "03", "실험계획법(DOE) 기반 데이터 확보", "DOE 데이터 확보 현황 및 차월 계획");

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

pres.writeFile({ fileName: "/home/user/dddd/1개월차_AI에이전트_활용방안_및_DOE결과.pptx" })
  .then(f => console.log("생성 완료:", f));
