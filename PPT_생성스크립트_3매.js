const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "망분리 환경에서의 AI 에이전트 활용 체계";

const NAVY = "16305B", ACCENT = "00A3C4", BG = "F3F5F8",
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
  ["반출 제한", "CAD·해석 모델 및 원본 결과는 반출 불가"],
  ["필요 사항", "내부 자산을 내보내지 않고 개발하는 방법"]
], [1.15, 4.15], { rowH: 0.34 });
s.addShape(pres.ShapeType.roundRect, { x: M + 0.34, y: y1 + 2.22, w: 5.3, h: 0.42, rectRadius: 0.06, fill: { color: "EEF2F7" }, line: { color: "EEF2F7" } });
s.addText("→  외부에서 만드는 것은 '코드'이고, 형상과 해석은 내부망에서만 수행", { x: M + 0.48, y: y1 + 2.22, w: 5.05, h: 0.42, fontSize: 9.5, bold: true, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

/* ── 우상 : 활용 구조 ── */
card(s, CX2, y1, CW, ch);
cardTitle(s, CX2, y1, "활용 구조");

const zoneY = y1 + 0.72;
s.addText("외부 (개발)", { x: CX2 + 0.34, y: zoneY, w: 2.0, h: 0.22, fontSize: 9, bold: true, color: MUTED, align: "left", fontFace: F, isTextBox: true, margin: 0, charSpacing: 1 });
s.addText("내부망", { x: CX2 + 3.64, y: zoneY, w: 2.0, h: 0.22, fontSize: 9, bold: true, color: MUTED, align: "right", fontFace: F, isTextBox: true, margin: 0, charSpacing: 1 });

// 망 경계
s.addShape(pres.ShapeType.line, { x: CX2 + 3.64, y: y1 + 0.68, w: 0, h: 1.58, line: { color: "B9C4D2", width: 1.25, dashType: "dash" } });

const bY = y1 + 1.02, bH = 0.5, bW = 1.5;
const bx = [CX2 + 0.34, CX2 + 2.04, CX2 + 3.74];
const boxes = [
  ["AI 에이전트", ACCENT, "FFFFFF"],
  ["저장소\n(코드 · 문서)", "FFFFFF", NAVY],
  ["CAD · 해석 실행", NAVY, "FFFFFF"]
];
boxes.forEach(([t, f, c], i) => {
  s.addShape(pres.ShapeType.roundRect, { x: bx[i], y: bY, w: bW, h: bH, rectRadius: 0.07, fill: { color: f }, line: { color: f === "FFFFFF" ? NAVY : f, width: 1.25 } });
  s.addText(t, { x: bx[i], y: bY, w: bW, h: bH, fontSize: i === 1 ? 9 : 10, bold: true, color: c, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 0.95 });
});
// 정방향 화살표
s.addShape(pres.ShapeType.line, { x: CX2 + 1.84, y: bY + bH / 2, w: 0.20, h: 0, line: { color: NAVY, width: 1.25, endArrowType: "triangle" } });
s.addShape(pres.ShapeType.line, { x: CX2 + 3.54, y: bY + bH / 2, w: 0.20, h: 0, line: { color: NAVY, width: 1.25, endArrowType: "triangle" } });
s.addText("코드 · 문서 반입", { x: CX2 + 2.85, y: bY + bH + 0.03, w: 1.45, h: 0.22, fontSize: 8, color: NAVY, align: "center", fontFace: F, isTextBox: true, margin: 0 });

// 복귀 경로 — 개발자 판단을 거쳐 요구사항만 전달
const rY = y1 + 1.92;
s.addShape(pres.ShapeType.line, { x: CX2 + 4.49, y: bY + bH, w: 0, h: rY - (bY + bH), line: { color: MUTED, width: 1.1 } });
s.addShape(pres.ShapeType.line, { x: CX2 + 1.09, y: rY, w: 3.40, h: 0, line: { color: MUTED, width: 1.1, beginArrowType: "triangle" } });
s.addShape(pres.ShapeType.line, { x: CX2 + 1.09, y: bY + bH, w: 0, h: rY - (bY + bH), line: { color: MUTED, width: 1.1, beginArrowType: "triangle" } });
s.addText("개발자가 결과를 확인하고 요구사항만 정리해 전달", { x: CX2 + 0.34, y: rY + 0.04, w: 5.3, h: 0.24, fontSize: 8.5, color: MUTED, align: "center", fontFace: F, isTextBox: true, margin: 0 });

s.addShape(pres.ShapeType.roundRect, { x: CX2 + 0.34, y: y1 + 2.28, w: 5.3, h: 0.32, rectRadius: 0.05, fill: { color: "EEF2F7" }, line: { color: "EEF2F7" } });
s.addText("형상·해석 모델과 원본 결과는 경계를 넘지 않음", { x: CX2 + 0.34, y: y1 + 2.28, w: 5.3, h: 0.32, fontSize: 9, bold: true, color: NAVY, align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

/* ── 좌하 : 맥락 구축 ── */
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

/* ── 우하 : 운영 방식 ── */
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

pres.writeFile({ fileName: "/home/user/dddd/1개월차_3매_망분리_AI활용체계.pptx" }).then(f => console.log("생성 완료:", f));
