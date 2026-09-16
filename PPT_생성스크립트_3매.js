const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "망분리 환경에서의 AI 에이전트 활용 체계";

const NAVY = "16305B", NAVY2 = "2C4E82", ACCENT = "00A3C4", BG = "F3F5F8",
      CARD = "FFFFFF", TXT = "1C2733", MUTED = "6B7A8F", LINE = "DDE3EB";
const F = "Malgun Gothic";
const M = 0.55, CW = 5.95, CX2 = 6.93;
const sh = () => ({ type: "outer", color: "9AA8BC", blur: 8, offset: 1, angle: 90, opacity: 0.18 });

function card(s, x, y, w, h) {
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h, fill: { color: CARD }, rectRadius: 0.06, line: { color: LINE, width: 0.75 }, shadow: sh() });
}
function cardTitle(s, x, y, t) {
  s.addShape(pres.ShapeType.rect, { x: x + 0.28, y: y + 0.30, w: 0.09, h: 0.20, fill: { color: ACCENT }, line: { color: ACCENT } });
  s.addText(t, { x: x + 0.46, y: y + 0.20, w: 5.2, h: 0.4, fontSize: 13, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0 });
}
function tbl(s, x, y, w, rows, colW, opt = {}) {
  s.addTable(rows, Object.assign({
    x, y, w, colW, fontSize: 9.5, fontFace: F, color: TXT,
    border: [{ type: "none" }, { type: "none" }, { pt: 0.5, color: LINE }, { type: "none" }],
    rowH: 0.3, valign: "middle", margin: [2, 4, 2, 4]
  }, opt));
}
const hdr = (t) => ({ text: t, options: { bold: true, color: NAVY, fill: { color: "EEF2F7" } } });

const s = pres.addSlide();
s.background = { color: BG };

// 헤더
s.addShape(pres.ShapeType.rect, { x: M, y: 0.42, w: 0.52, h: 0.52, fill: { color: NAVY }, line: { color: NAVY } });
s.addText("01", { x: M, y: 0.42, w: 0.52, h: 0.52, fontSize: 16, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
s.addText("AI 에이전트 기반 개발환경 구축", { x: M + 0.68, y: 0.40, w: 8, h: 0.26, fontSize: 10.5, bold: true, color: ACCENT, fontFace: F, isTextBox: true, margin: 0, charSpacing: 1 });
s.addText("망분리 환경에서의 AI 에이전트 활용 체계", { x: M + 0.68, y: 0.60, w: 11.6, h: 0.42, fontSize: 22, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0 });

const y1 = 1.30, y2 = 4.18, ch = 2.72;

/* ── 좌상 : 제약 조건 ── */
card(s, M, y1, CW, ch);
cardTitle(s, M, y1, "제약 조건");
tbl(s, M + 0.34, y1 + 0.80, 5.3, [
  [hdr("구분"), hdr("현황")],
  ["내부망", "보안 정책상 외부 AI 직접 접속 불가"],
  ["해석 환경", "CAD·해석 프로그램과 원본 데이터는 내부망에만 존재"],
  ["필요 사항", "AI를 내부망에 들이지 않고 개발하는 방법"]
], [1.15, 4.15], { rowH: 0.38 });
s.addText("※ 반출·반입은 사내 보안 절차에 따라 수행", { x: M + 0.34, y: y1 + 2.38, w: 5.3, h: 0.26, fontSize: 9.5, color: MUTED, italic: true, fontFace: F, isTextBox: true, margin: 0 });

/* ── 우상 : 활용 구조 ── */
card(s, CX2, y1, CW, ch);
cardTitle(s, CX2, y1, "활용 구조");

const zoneY = y1 + 0.70;
s.addText("내부망", { x: CX2 + 0.40, y: zoneY, w: 2.30, h: 0.24, fontSize: 9, bold: true, color: MUTED, align: "center", fontFace: F, isTextBox: true, margin: 0, charSpacing: 1 });
s.addText("외부 (개발)", { x: CX2 + 3.25, y: zoneY, w: 2.30, h: 0.24, fontSize: 9, bold: true, color: MUTED, align: "center", fontFace: F, isTextBox: true, margin: 0, charSpacing: 1 });

// 망분리 경계
s.addShape(pres.ShapeType.line, { x: CX2 + 2.975, y: y1 + 0.66, w: 0, h: 1.72, line: { color: "B9C4D2", width: 1, dashType: "dash" } });

const bY = y1 + 0.96, bH = 0.52;
s.addShape(pres.ShapeType.roundRect, { x: CX2 + 0.40, y: bY, w: 2.30, h: bH, rectRadius: 0.07, fill: { color: NAVY }, line: { color: NAVY } });
s.addText("CAD · 해석 실행", { x: CX2 + 0.40, y: bY, w: 2.30, h: bH, fontSize: 10, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
s.addShape(pres.ShapeType.roundRect, { x: CX2 + 3.25, y: bY, w: 2.30, h: bH, rectRadius: 0.07, fill: { color: ACCENT }, line: { color: ACCENT } });
s.addText("AI 에이전트", { x: CX2 + 3.25, y: bY, w: 2.30, h: bH, fontSize: 10, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

// 저장소
const rY = y1 + 1.90, rH = 0.5;
s.addShape(pres.ShapeType.roundRect, { x: CX2 + 0.95, y: rY, w: 4.05, h: rH, rectRadius: 0.07, fill: { color: "FFFFFF" }, line: { color: NAVY, width: 1.25 } });
s.addText("형상관리 저장소 (GitHub)", { x: CX2 + 0.95, y: rY, w: 4.05, h: rH, fontSize: 10.5, bold: true, color: NAVY, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

// 양방향 화살표
const aTop = bY + bH, aH = rY - (bY + bH);
s.addShape(pres.ShapeType.line, { x: CX2 + 1.55, y: aTop, w: 0, h: aH, line: { color: NAVY, width: 1.25, beginArrowType: "triangle", endArrowType: "triangle" } });
s.addShape(pres.ShapeType.line, { x: CX2 + 4.40, y: aTop, w: 0, h: aH, line: { color: ACCENT, width: 1.25, beginArrowType: "triangle", endArrowType: "triangle" } });
s.addText("반출 / 반입", { x: CX2 + 1.66, y: aTop + 0.02, w: 1.2, h: 0.3, fontSize: 8.5, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
s.addText("읽기 / 반영", { x: CX2 + 3.40, y: aTop + 0.02, w: 0.94, h: 0.3, fontSize: 8.5, color: ACCENT, align: "right", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

s.addText("저장소를 매개로 맥락 전달 — AI는 내부망에 접속하지 않음", { x: CX2 + 0.34, y: y1 + 2.46, w: 5.3, h: 0.24, fontSize: 9.5, color: MUTED, italic: true, align: "center", fontFace: F, isTextBox: true, margin: 0 });

/* ── 좌하 : 맥락 구축 ── */
card(s, M, y2, CW, ch);
cardTitle(s, M, y2, "맥락(Context) 구축 방법");
tbl(s, M + 0.34, y2 + 0.78, 5.3, [
  [hdr("저장소 구성"), hdr("담는 내용")],
  ["설계 문서", "설계변수·목적함수 정의, 값의 결정 근거, 검증 상태"],
  ["작업 규칙 문서", "임의 수정 금지 등 협업 규칙"],
  ["코드", "형상·해석 자동화 모듈"],
  ["결과 요약", "파싱 후 정리된 해석 결과"]
], [1.45, 3.85], { rowH: 0.30 });
s.addText("매 세션 저장소를 읽어 이전 맥락을 그대로 이어받음 — 결정 근거가 사람과 AI 양쪽에 남음",
  { x: M + 0.34, y: y2 + 2.34, w: 5.3, h: 0.30, fontSize: 9, color: MUTED, italic: true, fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });

/* ── 우하 : 운영 방식 ── */
card(s, CX2, y2, CW, ch);
cardTitle(s, CX2, y2, "운영 방식");
tbl(s, CX2 + 0.34, y2 + 0.78, 5.3, [
  [hdr("항목"), hdr("내용")],
  ["버전 관리", "형상·변수 구성 변경을 버전별 분기로 이력화"],
  ["변경 이력", "코드 수정 이력이 곧 설계 결정 이력"],
  ["반출 범위", "코드·문서 중심, 해석 원본 파일은 제외"],
  ["코드 검증", "수식 검산 · 전수 검증 · 통합 테스트"]
], [1.25, 4.05], { rowH: 0.30 });
s.addShape(pres.ShapeType.roundRect, { x: CX2 + 0.34, y: y2 + 2.30, w: 5.3, h: 0.38, rectRadius: 0.06, fill: { color: NAVY } });
s.addText("망분리 환경에서도 저장소를 매개로 AI 협업 체계 구축", { x: CX2 + 0.34, y: y2 + 2.30, w: 5.3, h: 0.38, fontSize: 10, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

s.addNotes("내부망에서는 외부 AI를 직접 쓸 수 없으므로, 형상관리 저장소를 맥락 매개체로 삼아 코드와 문서만 주고받는 방식으로 운영했다. 저장소에 값의 결정 근거와 검증 상태를 남겨두기 때문에 매 세션 같은 설명을 반복하지 않고 이어서 작업할 수 있다.");

pres.writeFile({ fileName: "/home/user/dddd/1개월차_3매_망분리_AI활용체계.pptx" }).then(f => console.log("생성 완료:", f));
