const pptxgen = require("pptxgenjs");
const fs = require("fs");
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "내부망 실행 구조";

const NAVY = "16305B", ACCENT = "00A3C4", BG = "F3F5F8",
      CARD = "FFFFFF", TXT = "1C2733", MUTED = "6B7A8F", LINE = "DDE3EB";
const F = "Malgun Gothic";
const M = 0.55;
const sh = () => ({ type: "outer", color: "9AA8BC", blur: 8, offset: 1, angle: 90, opacity: 0.18 });

const s = pres.addSlide();
s.background = { color: BG };

// ── 헤더 ──
s.addShape(pres.ShapeType.rect, { x: M, y: 0.42, w: 0.52, h: 0.52, fill: { color: NAVY }, line: { color: NAVY } });
s.addText("01", { x: M, y: 0.42, w: 0.52, h: 0.52, fontSize: 16, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
s.addText("AI 에이전트 기반 개발환경 구축", { x: M + 0.68, y: 0.40, w: 8, h: 0.26, fontSize: 10.5, bold: true, color: ACCENT, fontFace: F, isTextBox: true, margin: 0, charSpacing: 1 });
s.addText("내부망 실행 구조 — 시스템 아키텍처", { x: M + 0.68, y: 0.60, w: 11.6, h: 0.42, fontSize: 22, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0 });

// ── 리드 문장 ──
s.addShape(pres.ShapeType.rect, { x: M, y: 1.22, w: 0.07, h: 0.26, fill: { color: ACCENT }, line: { color: ACCENT } });
s.addText("작성된 코드가 CAD·해석 프로그램을 직접 제어 — 전 과정이 코드로 연결됨",
  { x: M + 0.18, y: 1.16, w: 11.6, h: 0.36, fontSize: 12.5, bold: true, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

// ── 아키텍처 이미지 ──
const IW = 8.55, IH = IW / 1.8044;      // 원본 비율 유지 (1144 x 634)
const IX = M, IY = 1.64;
s.addShape(pres.ShapeType.roundRect, { x: IX - 0.06, y: IY - 0.06, w: IW + 0.12, h: IH + 0.12, rectRadius: 0.05, fill: { color: CARD }, line: { color: LINE, width: 0.75 }, shadow: sh() });
s.addImage({ path: "/home/user/dddd/시스템아키텍처.PNG", x: IX, y: IY, w: IW, h: IH });

// ── 우측 설명 ──
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
  if (i < layers.length - 1) s.addText("▼", { x: RX + 0.02, y: ly - 0.22, w: 0.22, h: 0.2, fontSize: 7, color: LINE, align: "center", fontFace: F, isTextBox: true, margin: 0 });
});

s.addShape(pres.ShapeType.roundRect, { x: RX, y: IY + IH - 0.92, w: RW, h: 0.9, rectRadius: 0.06, fill: { color: NAVY }, line: { color: NAVY } });
s.addText("망분리 정책상\n외부망 ↔ 내부망 코드 이전은 수동 수행", { x: RX + 0.16, y: IY + IH - 0.92, w: RW - 0.32, h: 0.9, fontSize: 10, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });

// ── 하단 요약 ──
const by = IY + IH + 0.26;
s.addShape(pres.ShapeType.roundRect, { x: M, y: by, w: 12.23, h: 0.72, rectRadius: 0.06, fill: { color: CARD }, line: { color: LINE, width: 0.75 }, shadow: sh() });
const pts = [
  ["프로그램 간 연동", "CAD와 해석 프로그램을 코드 한 곳에서 제어"],
  ["수작업 개입 제거", "형상 수정·해석 실행·결과 정리를 무인 반복"],
  ["재사용 가능 구조", "설계변수 정의만 교체하면 타 과제 적용 가능"]
];
pts.forEach(([h, d], i) => {
  const x = M + 0.36 + i * 4.0;
  s.addShape(pres.ShapeType.rect, { x, y: by + 0.16, w: 0.07, h: 0.17, fill: { color: ACCENT }, line: { color: ACCENT } });
  s.addText(h, { x: x + 0.16, y: by + 0.10, w: 3.6, h: 0.28, fontSize: 10.5, bold: true, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  s.addText(d, { x: x + 0.16, y: by + 0.38, w: 3.7, h: 0.28, fontSize: 9.5, color: MUTED, fontFace: F, isTextBox: true, margin: 0 });
});

s.addNotes("지난 차수에서 구축한 해석 자동화 환경의 시스템 아키텍처다. 개발 환경에서 작성한 Python 코드가 API를 통해 CAD와 해석 프로그램을 직접 제어하며, 형상 생성부터 결과 추출까지 전 과정이 코드로 연결된다. 코드 이전은 망분리 정책에 따라 수동으로 수행한다.");

pres.writeFile({ fileName: "/home/user/dddd/1개월차_5매_내부망_실행구조.pptx" }).then(f => console.log("생성 완료:", f));
