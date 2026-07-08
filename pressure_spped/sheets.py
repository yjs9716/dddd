# 핀뱅크 입구 단면에 레인별 속도 측정용 비모델(NonModel) 시트 30개 생성
# 좌표 기준: 스크립트 레코더로 딴 실제 모델 좌표 (mm 단위 모델 기준)
# 주의: 모델 단위가 m로 바뀌어 있으면 좌표가 어긋남 → Modeler > Units 에서 mm 확인 후 실행

N_LANES  = 30
X_POS    = -168.499999983333    # 핀뱅크 시작(입구) X좌표 [mm]
Y_START  = 19.0000000166667     # 첫 레인 Y 시작 [mm]
Z_START  = 0.500000016666667    # 시트 하단 Z [mm]
WIDTH    = -4.00000003333333    # 레인 피치 (Y방향, 음수 = -Y로 진행) [mm]
HEIGHT   = 7.49999996666666     # 핀 높이 [mm]
PREFIX   = "V_inlet"


def create_inlet_sheets(oEditor):
    """입구 단면에 V_inlet_01 ~ V_inlet_30 시트 생성.
    NonModel이라 해석 결과에 영향 없음 → Solve 후에 만들어도 됨."""
    for i in range(N_LANES):
        y = Y_START + WIDTH * i
        oEditor.CreateRectangle(
            [
                "NAME:RectangleParameters",
                "IsCovered:=", True,
                "XStart:=", f"{X_POS}mm",
                "YStart:=", f"{y}mm",
                "ZStart:=", f"{Z_START}mm",
                "Width:=", f"{WIDTH}mm",
                "Height:=", f"{HEIGHT}mm",
                "WhichAxis:=", "X",
            ],
            [
                "NAME:Attributes",
                "Name:=", f"{PREFIX}_{i+1:02d}",
                "Flags:=", "NonModel#",
                "Color:=", "(143 175 143)",
                "Transparency:=", 0,
                "PartCoordinateSystem:=", "Global",
                "UDMId:=", "",
                "MaterialValue:=", "\"Al-Extruded\"",
                "SurfaceMaterialValue:=", "\"Steel-oxidised-surface\"",
                "SolveInside:=", True,
                "ShellElement:=", False,
                "ShellElementThickness:=", "0mm",
                "ReferenceTemperature:=", "20cel",
                "IsMaterialEditable:=", True,
                "IsSurfaceMaterialEditable:=", True,
                "UseMaterialAppearance:=", False,
                "IsLightweight:=", False,
            ],
        )
    print(f"측정 시트 {N_LANES}개 생성 완료 ({PREFIX}_01 ~ {PREFIX}_{N_LANES:02d})")
