const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "저장소 기반 개발환경 구성";

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
s.addText("저장소 기반 개발환경 구성", { x: M + 0.68, y: 0.60, w: 11.6, h: 0.42, fontSize: 22, bold: true, color: NAVY, fontFace: F, isTextBox: true, margin: 0 });

// ── 캡처 프레임 2개 ──
const FW = 5.75, FH = 3.42, FY = 1.66;
const FX = [M, 7.03];
const heads = [
  ["①", "AI 에이전트 — 작업 브랜치 연결", ACCENT],
  ["②", "저장소 — 버전별 브랜치로 저장", NAVY]
];

heads.forEach(([no, title, col], i) => {
  // 번호 배지 + 제목
  s.addShape(pres.ShapeType.ellipse, { x: FX[i], y: 1.20, w: 0.30, h: 0.30, fill: { color: col }, line: { color: col } });
  s.addText(no, { x: FX[i], y: 1.20, w: 0.30, h: 0.30, fontSize: 11, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  s.addText(title, { x: FX[i] + 0.42, y: 1.18, w: FW - 0.42, h: 0.34, fontSize: 13, bold: true, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });

  // 캡처 자리 (실제 캡처로 교체)
  s.addShape(pres.ShapeType.roundRect, {
    x: FX[i], y: FY, w: FW, h: FH, rectRadius: 0.05,
    fill: { color: CARD }, line: { color: "C3CDDA", width: 1, dashType: "dash" }, shadow: sh()
  });
  s.addText(`${no}  화면 캡처 삽입 영역`, {
    x: FX[i], y: FY + FH / 2 - 0.3, w: FW, h: 0.4, fontSize: 12, bold: true,
    color: "AAB6C6", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0
  });
  s.addText("(프레임에 맞춰 캡처 이미지로 교체)", {
    x: FX[i], y: FY + FH / 2 + 0.06, w: FW, h: 0.3, fontSize: 9,
    color: "C3CDDA", align: "center", valign: "middle", fontFace: F, isTextBox: true, margin: 0
  });
});

// ── 사이 연결 화살표 ──
s.addShape(pres.ShapeType.line, { x: 6.40, y: FY + FH / 2, w: 0.55, h: 0, line: { color: NAVY, width: 1.5, endArrowType: "triangle" } });
s.addText("저장", { x: 6.28, y: FY + FH / 2 - 0.34, w: 0.80, h: 0.26, fontSize: 9, bold: true, color: NAVY, align: "center", fontFace: F, isTextBox: true, margin: 0 });

// ── 캡처 설명 ──
const caps = [
  "세션 시작 시 저장소의 지정 브랜치를 연결\n→ 이전 작업 맥락을 그대로 이어받아 코드 작성",
  "작성된 코드·문서가 해당 브랜치에 반영\n→ 형상·변수 구성 변경이 버전별로 축적"
];
caps.forEach((t, i) => {
  s.addText(t, { x: FX[i] + 0.04, y: 5.22, w: FW - 0.08, h: 0.68, fontSize: 10, color: TXT, fontFace: F, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });
});

// ── 하단 요약 ──
s.addShape(pres.ShapeType.roundRect, { x: M, y: 6.06, w: 12.23, h: 0.92, rectRadius: 0.06, fill: { color: CARD }, line: { color: LINE, width: 0.75 }, shadow: sh() });
const pts = [
  ["작업 단위 = 브랜치", "형상·변수 구성이 바뀔 때마다 분기하여 관리"],
  ["맥락 유지", "세션이 바뀌어도 저장소를 읽어 이어서 작업"],
  ["이력 = 근거", "커밋 메시지가 곧 설계 변경 사유로 남음"]
];
pts.forEach(([h, d], i) => {
  const x = M + 0.36 + i * 4.0;
  s.addShape(pres.ShapeType.rect, { x, y: 6.26, w: 0.07, h: 0.18, fill: { color: ACCENT }, line: { color: ACCENT } });
  s.addText(h, { x: x + 0.16, y: 6.20, w: 3.6, h: 0.28, fontSize: 10.5, bold: true, color: NAVY, valign: "middle", fontFace: F, isTextBox: true, margin: 0 });
  s.addText(d, { x: x + 0.16, y: 6.50, w: 3.6, h: 0.34, fontSize: 9.5, color: MUTED, fontFace: F, isTextBox: true, margin: 0 });
});

s.addText("※ 화면 내 설계 세부값은 마스킹 처리", { x: M, y: 7.02, w: 6, h: 0.26, fontSize: 8.5, color: MUTED, italic: true, fontFace: F, isTextBox: true, margin: 0 });

s.addNotes("왼쪽은 AI 에이전트에서 작업 브랜치를 연결하는 화면, 오른쪽은 그 결과가 저장소에 버전별 브랜치로 쌓이는 화면이다. 세션이 바뀌어도 저장소를 읽어 이전 맥락을 이어받기 때문에 같은 설명을 반복할 필요가 없고, 커밋 메시지가 설계 변경 사유로 남아 이력 추적이 가능하다. 화면에 보이는 설계 세부값은 마스킹 처리했다.");

pres.writeFile({ fileName: "/home/user/dddd/1개월차_4매_저장소_기반_개발환경.pptx" }).then(f => console.log("생성 완료:", f));
