"""
V7 — Icepak 해석 (V6 icepak.py 기반)

V6 대비 변경점
  · 발열: FR-4 블록 17개(13.3 × 183 × 8 mm, 부피 발열) → 슬롯 바닥 접촉면 2D 시트 17개(13.3 × 183 mm)에
    Source 경계 Total Power 40 W 씩. 블록이 없으니 블록 내부 전도로 온도가 80~90 K 더 오르던 몫이 사라지고,
    측정 온도가 곧 냉각판 표면(접촉면) 온도가 된다. 시트 이름은 V6 블록과 같은 source01~17.
    해석 영역(Region) 윗면은 입출구 포트(깊이 8 mm 에서 z 18.5 mm)가 정하므로 블록을 지워도 바뀌지 않는다.
  · 유로 깊이(params["fin_height"], 기본 8 mm)를 바꿀 수 있다. SolidWorks 모델은 판 바닥이 기준이고 바닥·덮개
    두께와 포트 높이는 그대로라서, 유로 천장 위의 모든 높이(유로 천장, 판 윗면·발열면, 포트 윗면)가 (깊이 − 8)만큼
    올라간다는 전제다. 그래서 run_icepak 은
      - 높이 좌표를 깊이 8 mm 기준 상수 + (깊이 − 8)로 계산하고, z 메시는 깊이에 비례시켜 유로 깊이당 칸 수를 유지하고,
      - 냉각수 상자를 고정 좌표 대신 불러온 판의 외곽 범위로 만들고(z 는 판 바닥 ~ 포트 윗면에 딱 맞춤),
      - 분리된 냉각수 덩어리를 이름이 아니라 "상자 바깥면에 닿지 않는 것"으로 고르고,
      - 팬·출구 면을 z 18.5 고정값 대신 냉각수 덩어리의 가장 높은 면 두 개로 찾는다.
    깊이 8 mm 에서는 V7 처음 버전과 같은 형상·설정이 된다.
  · 측정: 유로별 측정면(V_inlet_00~, V_inlet2_00~)을 없앴다. 채널 균일도는 발열면 온도로 직접 잰다.
    대신 분기비 정규화용으로 2차 통과 전체 유량 측정면(Q_pass2)과, 단면 유량 측정 편향 확인용으로 1차 통과 후
    통로 전체 유량 측정면(Q_mid, 4 LPM 이어야 함)을 둔다. 분기(Rectangle1)까지 유량 측정면 셋은 모두 핀 없는
    통로 단면을 덮고, 벽 속으로 FLOW_PLANE_OVERLAP_MM 만큼 더 나가게 그린다 — 면 테두리가 벽 표면과 딱 겹치면
    드물게 AEDT 가 면적을 못 구해 nan 이 났다(V6). 고체 속 속도는 0 이라 평균 × 면적(= 유량)은 그대로다.
  · Fields Summary 행 순서가 설계와 무관하게 고정됐다 (N_SOURCE + 7 행, 아래 run_icepak 주석).

V6 에서 그대로인 것: 형상 불러오기, 재질, 팬(4 LPM, 20 °C), 출구 역류 차단, 메시, 해석 설정.
"""
from ansys.aedt.core import Desktop, Icepak
import os, shutil, time

from paths import AEDT_PROJ_PATH as PROJ_PATH, icepak_result_path
from fins import describe_bank


# 유량 측정면(Rectangle1 · Q_pass2 · Q_mid)을 통로 벽 속으로 더 그리는 길이 [mm] (모듈 설명 참고).
#   0 으로 두면 V6 처럼 통로 단면에 딱 맞춘다.
FLOW_PLANE_OVERLAP_MM = 0.2

# PAO 물성·운전 조건 — 해석 설정과 result_parser 의 열수지 계산이 같은 값을 쓰도록 여기서만 정한다
PAO_DENSITY       = 794.0    # [kg/m^3]  AddMaterial mass_density
PAO_SPECIFIC_HEAT = 2219.0   # [J/(kg·K)] AddMaterial specific_heat
INLET_TEMP_C      = 20.0     # 팬 흡입 PAO 온도 [°C] (외기 AmbientTemp 와 별개)
SOURCE_POWER_W    = 40.0     # 발열채널(CCA) 하나의 발열 [W]

# ── 1차 통과 후 PAO 온도 측정면 (T_pass1) ──────────────────────
#   1차 핀뱅크 출구와 2차 핀뱅크 입구 사이 가운데 통로(법선 y). 분기 전이라 4 LPM 전부가 지난다.
#   통로: x = MID_PASSAGE_X_WALL ~ (mid_input_thick + MID_PASSAGE_X_WALL), z = 0 ~ CHANNEL_DEPTH_MM.
#   벽에서 T_PASS1_INSET_MM 만큼 띄운 사각형의 면적평균을 쓴다 — 시험 설계(mid_input_thick 24.9)에서
#   유량가중 평균(Temp·Vy 격자 내보내기) 22.5 °C와 1 mm 띄움 면적평균 22.45 °C가 일치했다
#   (0.5 mm 22.95, 2 mm 21.84 °C). 벽 쪽 셀(z 2 mm)에서 판 온도로 보간되는 값을 빼기 위한 띄움이라
#   메시(MESH_REGION_X/Z)를 바꾸면 다시 맞춰 볼 것.
MID_PASSAGE_Y      = -86.25    # 1차 뱅크 상단벽(-91.25)과 2차 뱅크 하단벽(-81.25) 사이 가운데
MID_PASSAGE_X_WALL = -195.0    # 통로 바깥벽 x (Rectangle1 시작점과 같음)
T_PASS1_INSET_MM   = 1.0       # ⚠ z 2.0 mm 메시에서 맞춘 값 — z 1.6 mm 로 바꿨으니 캠페인 전에 다시 맞출 것

# ── 2차 통과 후·합류 전 PAO 온도 측정면 (T_pass2) ─────────────
#   2차 핀뱅크 출구 쪽 통로(법선 y, y = PASS2_EXIT_Y). 판 오른쪽 끝 입구 통로(폭 input_thick) 안쪽에 있어
#   input_thick 에 따라 움직인다: 통로 벽 x = 오른쪽 바깥 벽(195) − input_thick − 15.
#   통로 폭은 mid_thick(벽에서 −x 쪽으로), 깊이는 유로 전체(z 0~8).
#   T_pass1 과 같이 벽마다 T_PASS1_INSET_MM 띄운 면적평균.
#   예: input_thick 23.2 → 사각형 시작 (155.8, 10, 7), 크기 x −(mid_thick − 2), z −6 (GUI 에서 확인한 값)
PASS2_EXIT_Y          = 10.0
PLATE_X_RIGHT_WALL    = 195.0    # 판 오른쪽 바깥 벽 x (입구 통로 시작) — 왼쪽 바깥 벽 −195 와 대칭
PASS2_EXIT_FROM_INPUT = 15.0     # 입구 통로 안쪽 벽에서 2차 통과 출구 통로 벽까지 [mm]

# ── 발열면 (슬롯 바닥 접촉면) ─────────────────────────────────
#   V6 FR-4 블록의 바닥면 자리 그대로 — 실제 CCA 열이 들어오는 자리와 같다.
#     x = SOURCE_X0 + i·SOURCE_PITCH  ~  + SOURCE_WIDTH_X,   y = SOURCE_Y0 ~ SOURCE_Y0 + SOURCE_LEN_Y,   z = 판 윗면
#   슬롯 하나가 y 방향으로 2차 통과(위쪽 절반, y 5.25 ~ −81.25)와 1차 통과(아래쪽 절반, y −91.25 ~ −177.75)를
#   함께 덮는다 — 그래서 슬롯 안 온도편차에는 두 통과의 유로별 유량 차이와 1·2차 냉각수 온도 차이가 다 들어간다.
#   N_SOURCE 는 CSV 행 구조를 결정하므로 result_parser 가 이 값을 import 해서 쓴다.
N_SOURCE = 17  # 발열면(source01~) 개수 = 슬롯 전부 (20.8 mm 간격)
#   범용 냉각판이라 전 슬롯 실장을 설계 기준으로 삼는다 — 유동은 발열과 무관하고 온도는 발열에 선형이라
#   (층류, 중력·복사 끔, 물성 일정) 발열원을 더하면 모든 지점의 온도가 오르거나 그대로다. 따라서 슬롯당
#   SOURCE_POWER_W 이하로 일부만 꽂은 장비는 전 지점에서 이 조건보다 낮은 온도가 된다.
SOURCE_X0      = -172.9        # 슬롯 1 (가장 왼쪽) x 시작 [mm]
SOURCE_PITCH   = 20.8          # 슬롯 간격 [mm]
SOURCE_WIDTH_X = 13.3          # 발열면 x 폭 [mm]
SOURCE_Y0      = 5.24999998    # 발열면 y 시작 (2차 통과 핀뱅크 상단벽) [mm]
SOURCE_LEN_Y   = -183.0        # 발열면 y 길이 (−y 방향) [mm]
SOURCE_Z       = 10.50000002   # 판 윗면 z — 깊이 8 mm 기준 (V6 블록 바닥과 같은 값) [mm]. run_icepak 이 깊이만큼 올린다

#   유량·온도 측정면의 z 범위 — 유로 깊이 전체 (fin_height 8.0 mm = 유로 깊이, 우회공간 없음)
#   아래 값은 깊이 8 mm 기준이다. run_icepak 은 깊이(params["fin_height"])에 맞춰 천장 = CHANNEL_Z_TOP + (깊이 − 8),
#   깊이 = params["fin_height"] 로 계산해 쓴다(유로 바닥 z ≈ 0 은 그대로).
NOMINAL_DEPTH_MM = 8.0               # 기준 유로 깊이 = params.FIXED_GEOMETRY 의 fin_height
CHANNEL_Z_TOP    = 7.999999983       # 유로 천장 z좌표 (깊이 8 mm)
CHANNEL_DEPTH_MM = NOMINAL_DEPTH_MM  # 유로 깊이 = fin_height (깊이 8 mm)
PAO_BOX_MARGIN_XY_MM = 30.0          # 냉각수 상자를 판 외곽보다 x·y 로 더 크게 그리는 여유 (z 는 여유 없이 딱 맞춤)

# ── 메시 크기 [mm] — 코드 흐름 검증용으로 크게 잡고 싶을 때 여기만 바꾸면 됨 ──
#   MESH_REGION_*  : SubRegion(유체 도메인)에 거는 로컬 메시
#   GLOBAL_MESH_*  : 전체 Region에 거는 글로벌 메시
#   실제 캠페인 돌릴 땐 다시 촘촘하게(예: 기존 X=2,Y/Z=1 / X=2,Y=2,Z=2) 낮춰야 함 —
#   거칠게 하면 얇은 두께(예: power_input_thick 5mm) 구간에서 메시 스냅으로 면적/유량이
#   틀어질 수 있음 (README 4-(3) 참고)
MESH_REGION_X = 2.0
MESH_REGION_Y = 0.3   # V6: 격자 시험(grid_convergence.py, y 0.75~0.25, x·z 2.0 고정)으로 확정
MESH_REGION_Z = 1.6   # 깊이 8 mm 기준 — run_icepak 은 깊이에 비례시켜 유로 깊이당 5칸을 유지한다. V6: 격자 시험 z(유로 8 mm당 2~6셀)에서 6셀 대비 차압 −1.6%, 최고온도 −0.04 K,
#                       분기비 −0.2%로 통과한 가장 성긴 5셀. DSD 29회는 2.0 mm(4셀)였다.

# 전원분기 입구 국소 메시 (MeshRegion2) — 입구 폭(power_input_thick, x방향)이 3mm까지 내려가는데
#   MESH_REGION_X=2.0이면 1.5셀뿐이라 메시가 입구를 막아 분기 유량이 0이 됨(DSD run 4,7~10에서 확인).
#   입구를 감싸는 박스(x폭 = power_input_thick)에만 x를 촘촘하게 건다. 값은 GUI 시험에서 확인한 설정.
#   PM_MESH_Z 는 MESH_REGION_Z 와 같게 둔다 — 분기 유량 측정면(Rectangle1, y = 9 mm)이 이 박스 안에
#   있어서, z 가 다르면 정규화 분기비의 분자(분기)와 분모(2차 유로)가 서로 다른 단면 편향을 갖는다.
#   (격자 시험 z 에서는 2.0 고정이었다 — 분기비가 z 셀 수에 거의 반응하지 않은 이유로 보임)
PM_MESH_X = 0.5
PM_MESH_Y = 2.0   # 분기 통로의 흐름 방향
PM_MESH_Z = MESH_REGION_Z

# 유체 서브리전 메시의 최소 분할 수 — 갭 해상도 시험용으로 여기서 바꿀 수 있게 상수로 뺐다
#   MIN_ELEMENTS_IN_GAP  : 서로 다른 물체 사이 틈을 최소 N셀로 (핀 사이 유로에는 안 먹는 것으로 확인됨)
#   MIN_ELEMENTS_ON_EDGE : 물체 모서리 하나를 최소 N셀로 — 유로 폭을 가로지르는 PAO 모서리에 걸리길 기대.
#                          모든 모서리에 적용되므로 총 셀 수도 같이 확인할 것
MIN_ELEMENTS_IN_GAP  = 3          # MeshRegion1 (유체 서브리전)
MIN_ELEMENTS_ON_EDGE = 2          # MeshRegion1 (유체 서브리전)
GLOBAL_MIN_ELEMENTS_IN_GAP  = 3   # 글로벌 메시 (전체 Region)
GLOBAL_MIN_ELEMENTS_ON_EDGE = 2   # 글로벌 메시 (전체 Region)

GLOBAL_MESH_X = 2.0
GLOBAL_MESH_Y = 2.0
GLOBAL_MESH_Z = 2.0

def connect_aedt():
    desktop = Desktop(
        version="2025.1",
        non_graphical=True,   # 리소스 절약 목적. 이전에 True로 의심됐던 export 무응답은
                               # 실제로는 로컬에 이 변경이 반영도 안 된 채(GUI 모드) 발생한
                               # 것으로 확인됨(업무시간 자원경합이 실제 원인으로 추정) —
                               # non_graphical 자체가 원인이라는 증거는 없었음. 재적용.
        new_desktop=True,
        close_on_exit=False,
    )
    print("AEDT 켜짐")
    return desktop, None


def _rect(oEditor, name, start, width, height, axis, model=False):
    """사각형 시트 하나 [mm]. axis 별 (Width, Height) 방향: "X" → (y, z), "y" → (z, x), "Z" → (x, y).
    model=False 면 측정 전용(NonModel — 해석에 영향 없음), True 면 경계조건을 거는 실제 물체(발열면)."""
    oEditor.CreateRectangle(
        [
            "NAME:RectangleParameters",
            "IsCovered:="		, True,
            "XStart:="		, f"{start[0]:.12g}mm",
            "YStart:="		, f"{start[1]:.12g}mm",
            "ZStart:="		, f"{start[2]:.12g}mm",
            "Width:="		, f"{width:.12g}mm",
            "Height:="		, f"{height:.12g}mm",
            "WhichAxis:="		, axis
        ],
        [
            "NAME:Attributes",
            "Name:="		, name,
            "Flags:="		, "" if model else "NonModel#",
            "Color:="		, "(143 175 143)",
            "Transparency:="	, 0,
            "PartCoordinateSystem:=", "Global",
            "UDMId:="		, "",
            "MaterialValue:="	, "\"Al-Extruded\"",
            "SurfaceMaterialValue:=", "\"Steel-oxidised-surface\"",
            "SolveInside:="		, True,
            "ShellElement:="	, False,
            "ShellElementThickness:=", "0mm",
            "ReferenceTemperature:=", "20cel",
            "IsMaterialEditable:="	, True,
            "IsSurfaceMaterialEditable:=", True,
            "UseMaterialAppearance:=", False,
            "IsLightweight:="	, False
        ])


def run_icepak(desktop, ipk, step_file, phase, idx, params, measure=True):
    """
    measure=False 면 2패스 전용 측정면(Rectangle1·Q_pass2·Q_mid·T_pass1·T_pass2)을 만들지 않고, Fields Summary 는
    발열면 온도·팬 차압·출구 온도 N_SOURCE + 2 행만 쓴다(pass_compare.py — 1·2·4패스 비교). 그 밖의 해석 설정은 같다.
    params 는 measure=False 일 때 power_input_thick(분기 입구 국소 메시 폭)만 있으면 된다.
    반환: (ipk, result_path, pao_volume_mm3)
      result_path     : 이번 idx의 Fields Summary CSV 경로
      pao_volume_mm3  : 유로를 채운 PAO 부피 [mm^3] — 중량 계산용
                        (SolidWorks 알루미늄 중량 + PAO 중량 = 총 중량)
    """
    print(f"[T0] run_icepak 진입: {time.strftime('%H:%M:%S')}")

    # 유로 깊이 — 유로 천장 위의 높이는 전부 (깊이 − 8)만큼 올라가고, z 메시는 깊이에 비례 (모듈 설명 참고)
    depth = float(params.get("fin_height", NOMINAL_DEPTH_MM))
    dz = depth - NOMINAL_DEPTH_MM
    ch_top = CHANNEL_Z_TOP + dz                    # 유로 천장 z
    src_z = SOURCE_Z + dz                          # 판 윗면(발열면) z
    mesh_z = MESH_REGION_Z * depth / NOMINAL_DEPTH_MM
    pm_mesh_z = PM_MESH_Z * depth / NOMINAL_DEPTH_MM
    if abs(dz) > 1e-9:
        print(f"  유로 깊이 {depth:g} mm — 유로 천장 z {ch_top:.4f}, 발열면 z {src_z:.4f}, z 메시 {mesh_z:.4g} mm")

    # 기존 프로젝트 닫기 (AEDT는 유지)
    if ipk is not None:
        oDesktop = ipk.odesktop
        proj_name = ipk.project_name
        ipk = None
        oDesktop.CloseProject(proj_name)
        print(f"[T1] 기존 프로젝트 닫음: {time.strftime('%H:%M:%S')}")

    # 디스크 파일 삭제
    #   .aedt.lock도 같이 지운다 — 스크립트가 중간에 끊기면(F5 재시작, 예외로 죽음 등)
    #   AEDT가 프로젝트에 걸어둔 잠금 파일이 안 지워진 채 남는다. 다음 실행이 같은
    #   이름으로 프로젝트를 새로 만들려 할 때 이 잠금 때문에 AEDT가 GUI 모달 팝업을
    #   띄우고, 그 팝업이 COM 호출을 막아 Icepak() 생성자가 영원히 반환되지 않는다
    #   ("Project ... has been created"까지만 찍히고 디자인이 생성되지 않는 증상 —
    #   실제로 이 잠금 파일을 지우고 나니 해결됨을 확인함).
    if os.path.exists(PROJ_PATH + ".aedt"):
        os.remove(PROJ_PATH + ".aedt")
    if os.path.exists(PROJ_PATH + ".aedt.lock"):
        os.remove(PROJ_PATH + ".aedt.lock")
    if os.path.exists(PROJ_PATH + ".aedtresults"):
        shutil.rmtree(PROJ_PATH + ".aedtresults")
    print(f"[T2] 파일삭제(rmtree 등) 끝: {time.strftime('%H:%M:%S')}")

    # 새 프로젝트 생성
    # design을 안 주면 PyAEDT가 매번 랜덤 접미사로 디자인 이름을 자동 생성함
    # (Icepak_ZZ0, Icepak_IC3 등) — 그 자동 생성 로직 내부(_insert_design ->
    # active_design)에서 이따금 크래시가 나서(active_design이 None 반환), 아예
    # 직접 고정 이름을 줘서 그 경로를 타지 않게 함
    ipk = Icepak(
        project=PROJ_PATH,
        design=f"IcepakDesign_{'gci_' if phase == 'gci' else ''}{idx:03d}",
        new_desktop=False,
        close_on_exit=False,
    )
    print(f"[T3] 새 프로젝트 생성: {ipk.project_name}  {time.strftime('%H:%M:%S')}")

    # STEP import
    ipk.modeler.import_3d_cad(step_file)
    print(f"[T4] STEP 임포트 완료: {step_file}  {time.strftime('%H:%M:%S')}")

    # oDesktop/oProject/oDesign/oEditor 매핑
    oDesktop = ipk.odesktop
    oProject = ipk.oproject
    oDesign  = ipk.odesign
    oEditor  = oDesign.SetActiveEditor("3D Modeler")


    # %%
    oEditor.ChangeProperty(
        [
            "NAME:AllTabs",
            [
                "NAME:Geometry3DCmdTab",
                [
                    "NAME:PropServers", 
                    "Region:CreateRegion:1"
                ],
                [
                    "NAME:ChangedProps",
                    [
                        "NAME:+X Padding Data",
                        "Value:="		, "0"
                    ],
                    [
                        "NAME:-X Padding Data",
                        "Value:="		, "0"
                    ],
                    [
                        "NAME:+Y Padding Data",
                        "Value:="		, "0"
                    ],
                    [
                        "NAME:-Y Padding Data",
                        "Value:="		, "0"
                    ],
                    [
                        "NAME:+Z Padding Data",
                        "Value:="		, "0"
                    ],
                    [
                        "NAME:-Z Padding Data",
                        "Value:="		, "0"
                    ]
                ]
            ]
        ])

    # %%
    oDesign.SetDesignSettings(
        [
            "NAME:Design Settings Data",
            "Perform Minimal validation:=", False,
            "Default Fluid Material:=", "air",
            "Default Solid Material:=", "Al-Extruded",
            "Default Surface Material:=", "Steel-oxidised-surface",
            "AmbientTemperature:="	, "43cel",
            "AmbientPressure:="	, "0n_per_meter_sq",
            "AmbientRadiationTemperature:=", "20cel",
            "Gravity Vector CS ID:=", 1,
            "Gravity Vector Axis:="	, "Z",
            "Positive:="		, False,
            "ExportOnSimulationComplete:=", False,
            "ExportDirectory:="	, "",
            "SherlockExportOnSimulationComplete:=", False,
            "SherlockExportAsFatigue:=", True,
            "AutoLaunchMeshViewer:=", True,
            "MeshCadAsLightWeight:=", True,
            "EnableTransitionTemplate:=", False,
            "TempSecondaryGradientSkewMesh:=", False,
            "EnableMeshByLayerFor2DMLM:=", False,
            "BoundaryBasedMeshRefinement:=", False,
            "EnableAltitudeEffects:=", False,
            "UpdateFanCurve:="	, False,
            "Altitude:="		, "0meter",
            "EnableIdealGasLaw:="	, False,
            "OperatingPressure:="	, "101325n_per_meter_sq",
            "EnableOperatingDensity:=", False,
            "OperatingDensity:="	, "1.225kg_per_m3",
            "AppendTemplateToFieldsSummaryReport:=", False,
            "EnableLoadSolution:="	, False
        ], 
        [
            "NAME:Model Validation Settings",
            "EntityCheckLevel:="	, "Strict",
            "IgnoreUnclassifiedObjects:=", False,
            "SkipIntersectionChecks:=", False
        ])

    # %%
    oDefinitionManager = oProject.GetDefinitionManager()
    if not oDefinitionManager.DoesMaterialExist("PAO"):
            try:
                # 이 코드는 PAO가 없을 땐 생성하고, 있을 땐 에러를 냅니다.
            
                oDefinitionManager.AddMaterial(
                    [
                        "NAME:PAO",
                        "CoordinateSystemType:=", "Cartesian",
                        "BulkOrSurfaceType:="	, 1,
                        [
                            "NAME:PhysicsTypes",
                            "set:="			, ["Thermal"]
                        ],
                        "thermal_conductivity:=", "0.142",
                        "mass_density:="	, f"{PAO_DENSITY:g}",
                        "specific_heat:="	, f"{PAO_SPECIFIC_HEAT:g}",
                        "thermal_expansion_coefficient:=", "0.00083",
                        [
                            "NAME:thermal_material_type",
                            "property_type:="	, "ChoiceProperty",
                            "Choice:="		, "Fluid"
                        ],
                        "diffusivity:="		, "1",
                        "molecular_mass:="	, "1",
                        "viscosity:="		, "0.0099",
                        [
                            "NAME:clarity_type",
                            "property_type:="	, "ChoiceProperty",
                            "Choice:="		, "Opaque"
                        ]
                    ])
                print("로그: PAO 재질이 새로 생성되었습니다.")
            except:
                # 재질이 이미 존재하면 위에서 에러가 나는데, 
                # except가 그 에러를 잡아먹고 그냥 아래로 내려보냅니다.
                print("로그: PAO가 이미 존재하거나 생성할 수 없어 스킵합니다.")


    # %%
    # STEP import 후 오브젝트 이름 변경
    objects = [ipk.modeler[name] for name in ipk.modeler.object_names if "ttpkp" in name]
    objects.sort(key=lambda o: o.volume)

    objects[0].name = "plate"       # 작은 것
    objects[1].name = "plate_base"  # 큰 것

    print(f"이름 변경 완료: {[o.name for o in objects]}")

    # %%

    oEditor.ChangeProperty(
        [
            "NAME:AllTabs",
            [
                "NAME:Geometry3DAttributeTab",
                [
                    "NAME:PropServers", 
                    "plate", 
                    "plate_base"
                ],
                [
                    "NAME:ChangedProps",
                    [
                        "NAME:Material",
                        "Value:="		, "\"Al-Extruded\""
                    ]
                ]
            ]
        ])


    # %%
    # 냉각수 상자 — 불러온 판의 외곽 범위로 만든다. x·y 는 여유를 두고, z 는 판 바닥 ~ 포트 윗면에 딱 맞춘다.
    #   상자가 포트 윗면보다 높으면 유로 속 냉각수가 포트 구멍으로 바깥 덩어리와 이어져 분리되지 않는다.
    #   (깊이 8 mm 에서 V6 고정값은 x ±231.5, y ±215, z −2.5 ~ 18.5 였다)
    bbs = [o.bounding_box for o in objects]
    bx0, by0, bz0 = (min(float(b[i]) for b in bbs) for i in range(3))
    bx1, by1, bz1 = (max(float(b[i]) for b in bbs) for i in range(3, 6))
    m = PAO_BOX_MARGIN_XY_MM
    pao_box = (bx0 - m, by0 - m, bz0, bx1 + m, by1 + m, bz1)
    print(f"  판 외곽: x {bx0:.3f}~{bx1:.3f}, y {by0:.3f}~{by1:.3f}, z {bz0:.3f}~{bz1:.3f} mm")
    oEditor.CreateBox(
        [
            "NAME:BoxParameters",
            "XPosition:="		, f"{pao_box[0]:.12g}mm",
            "YPosition:="		, f"{pao_box[1]:.12g}mm",
            "ZPosition:="		, f"{pao_box[2]:.12g}mm",
            "XSize:="		, f"{pao_box[3] - pao_box[0]:.12g}mm",
            "YSize:="		, f"{pao_box[4] - pao_box[1]:.12g}mm",
            "ZSize:="		, f"{pao_box[5] - pao_box[2]:.12g}mm"
        ], 
        [
            "NAME:Attributes",
            "Name:="		, "PAO",
            "Flags:="		, "",
            "Color:="		, "(143 175 143)",
            "Transparency:="	, 0,
            "PartCoordinateSystem:=", "Global",
            "UDMId:="		, "",
            "MaterialValue:="	, "\"PAO\"",
            "SurfaceMaterialValue:=", "\"Steel-oxidised-surface\"",
            "SolveInside:="		, True,
            "ShellElement:="	, False,
            "ShellElementThickness:=", "0mm",
            "ReferenceTemperature:=", "20cel",
            "IsMaterialEditable:="	, True,
            "IsSurfaceMaterialEditable:=", True,
            "UseMaterialAppearance:=", False,
            "IsLightweight:="	, False
        ])
    oEditor.Subtract(
        [
            "NAME:Selections",
            "Blank Parts:="		, "PAO",
            "Tool Parts:="		, "plate,plate_base"
        ], 
        [
            "NAME:SubtractParameters",
            "KeepOriginals:="	, True,
            "TurnOnNBodyBoolean:="	, True
        ])
    oEditor.SeparateBody(
        [
            "NAME:Selections",
            "Selections:="		, "PAO",
            "NewPartsModelFlag:="	, "Model"
        ], 
        [
            "CreateGroupsForNewObjects:=", False
        ])
    # 분리된 덩어리 중 냉각수(유로 속) 고르기 — 상자 x·y 바깥면에 닿지 않는 것. 바깥 덩어리는 상자 x·y 끝까지 닿는다.
    #   이름("PAO"=바깥, "PAO_Separate1"=유로)은 형상에 따라 바뀔 수 있어 쓰지 않는다. 고른 것을 PAO_Separate1 로 둔다.
    pieces = [n for n in ipk.modeler.object_names if n == "PAO" or n.startswith("PAO_Separate")]
    tol = 1e-3
    def _inside(name):
        b = [float(v) for v in ipk.modeler[name].bounding_box]
        return (b[0] > pao_box[0] + tol and b[1] > pao_box[1] + tol
                and b[3] < pao_box[3] - tol and b[4] < pao_box[4] - tol)
    fluid = [n for n in pieces if _inside(n)]
    if len(fluid) != 1:
        raise RuntimeError(f"냉각수 덩어리를 하나로 고르지 못함 — 분리된 덩어리 {pieces}, 유로 속으로 판단한 것 {fluid}. "
                           "판 형상(포트가 막혔는지, 유로가 두 덩어리로 끊겼는지)을 확인할 것")
    others = [n for n in pieces if n != fluid[0]]
    if others:
        oEditor.Delete(["NAME:Selections", "Selections:=", ",".join(others)])
    if fluid[0] != "PAO_Separate1":
        ipk.modeler[fluid[0]].name = "PAO_Separate1"
    print(f"  냉각수 덩어리: {fluid[0]} → PAO_Separate1 (지운 바깥 덩어리 {others})")

    # %%
    # 발열면 — 슬롯 바닥 접촉면 2D 시트 (상단 상수 주석 참고). 경계조건(Source)은 아래 출구 경계 다음에 건다.
    for i in range(N_SOURCE):
        _rect(oEditor, f"source{i + 1:02d}",
              (SOURCE_X0 + i * SOURCE_PITCH, SOURCE_Y0, src_z), SOURCE_WIDTH_X, SOURCE_LEN_Y, "Z", model=True)

    # %%
    box1 = ipk.modeler["PAO_Separate1"]
    # 팬·출구 면 = 냉각수 덩어리의 가장 높은 면 두 개(포트 윗면, 깊이 8 mm 에서 z 18.5)
    z_top = max(face.center[2] for face in box1.faces)
    target_faces = [face for face in box1.faces if abs(face.center[2] - z_top) < 0.1]
    if len(target_faces) != 2:
        raise RuntimeError(f"냉각수 덩어리 맨 위(z {z_top:.3f})에서 포트 면이 {len(target_faces)}개 — 2개여야 함. "
                           "포트 윗면보다 높은 형상이 있는지 확인할 것")
    target_faces.sort(key=lambda face: face.center[0])
    fan_face     = target_faces[-1]   # x값이 큰 쪽(120.3) = Fan
    opening_face = target_faces[0]    # x값이 작은 쪽(78.3) = Opening

    # 팬 위치를 동적으로
    fan_x = fan_face.center[0]
    fan_y = fan_face.center[1]
    fan_z = fan_face.center[2]
    oEditor.InsertNativeComponent(
        [
            "NAME:InsertNativeComponentData",
            "TargetCS:="		, "Global",
            "SubmodelDefinitionName:=", "Fan1",
            [
                "NAME:ComponentPriorityLists"
            ],
            "NextUniqueID:="	, 0,
            "MoveBackwards:="	, False,
            "DatasetType:="		, "ComponentDatasetType",
            [
                "NAME:DatasetDefinitions"
            ],
            [
                "NAME:BasicComponentInfo",
                "ComponentName:="	, "Fan1",
                "Company:="		, "",
                "Company URL:="		, "",
                "Model Number:="	, "",
                "Help URL:="		, "",
                "Version:="		, "1.0",
                "Notes:="		, "",
                "IconType:="		, "Fan"
            ],
            [
                "NAME:GeometryDefinitionParameters",
                [
                    "NAME:VariableOrders"
                ]
            ],
            [
                "NAME:DesignDefinitionParameters",
                [
                    "NAME:VariableOrders"
                ]
            ],
            [
                "NAME:MaterialDefinitionParameters",
                [
                    "NAME:VariableOrders"
                ]
            ],
            "DefReferenceCSID:="	, 1,
            "MapInstanceParameters:=", "DesignVariable",
            "UniqueDefinitionIdentifier:=", "c0cbeca3-60a5-4c2b-91f5-5871ba115f42",
            "OriginFilePath:="	, "",
            "IsLocal:="		, False,
            "ChecksumString:="	, "",
            "ChecksumHistory:="	, [],
            "VersionHistory:="	, [],
            [
                "NAME:NativeComponentDefinitionProvider",
                "Type:="		, "Fan",
                "Unit:="		, "mm",
                "Version:="		, 0,
                "ModelAs:="		, "2D",
                "Shape:="		, "Circular",
                "MovePlane:="		, "XY",
                "Radius:="		, "6mm",
                "HubRadius:="		, "0mm",
                "CaseSide:="		, True,
                "FlowDirChoice:="	, "NormalNegative",
                "FlowType:="		, "FixedVolumetric",
                "SwirlType:="		, "Magnitude",
                "FailedFan:="		, False,
                [
                    "NAME:DimUnits", 
                    "m3_per_s", 
                    "n_per_meter_sq"
                ],
                "X:="			, ["0","0.01"],
                "Y:="			, ["30","0"],
                [
                    "NAME:Pressure Loss Curve",
                    [
                        "NAME:DimUnits", 
                        "m_per_sec", 
                        "n_per_meter_sq"
                    ],
                    "X:="			, ["0","1","2","3"],
                    "Y:="			, ["1","10","100","0"]
                ],
                "IntakeTemp:="		, f"{INLET_TEMP_C:g}cel",
                "Volumetric:="		, "4ltr_per_min",
                "Swirl:="		, "0",
                "OperatingRPM:="	, "0",
                "LayerName:="		, "1"
            ],
            [
                "NAME:InstanceParameters",
                "GeometryParameters:="	, "",
                "MaterialParameters:="	, "",
                "DesignParameters:="	, ""
            ]
        ])
    oEditor = oDesign.SetActiveEditor("3D Modeler")
    oEditor.Move(
        [
            "NAME:Selections",
            "Selections:="		, "Fan1_1",
            "NewPartsModelFlag:="	, "Model"
        ], 
        [
            "NAME:TranslateParameters",
            "TranslateVectorX:="	, f"{fan_x}mm",
            "TranslateVectorY:="	, f"{fan_y}mm",
            "TranslateVectorZ:="	, f"{fan_z}mm"
        ])


    # %%
    oModule = oDesign.GetModule("BoundarySetup")
    oModule.AssignOpeningBoundary(
        [
            "NAME:Opening1",
            "Faces:=", [opening_face.id],   # Circle2 대신 face ID 직접
            "Temperature:=", "AmbientTemp",
            "External Rad. Temperature:=", "AmbientRadTemp",
            "Inlet Type:=", "Pressure",
            "Total Pressure:=", "AmbientPressure",
            # 역류 차단 — 허용하면 AmbientTemp(43 °C) PAO가 출구로 들어와 열수지가 틀어짐 (모듈 설명 참고)
            "No Reverse Flow:=", True
        ])

    # %%
    # 발열면마다 Source 경계를 따로 만든다 — "시트 하나당 Total Power 40 W" 를 확실히 하려고(한 경계에 여러 시트를
    #   묶었을 때 총 발열을 시트마다 주는지 나눠 갖는지는 버전마다 확인이 필요하다). 총 발열로 주므로 면적이
    #   메시 이산화로 조금 달라져도 시트당 40 W, 합계 N_SOURCE × 40 W 가 지켜진다(열수지 점검 기준과 같음).
    for i in range(N_SOURCE):
        name = f"source{i + 1:02d}"
        bound = ipk.assign_source(name, "Total Power", f"{SOURCE_POWER_W:g}W", boundary_name=f"Source{i + 1:02d}")
        if not bound:
            raise RuntimeError(f"발열면 Source 경계 생성 실패: {name}")
    print(f"  발열면 {N_SOURCE}개 — 각 {SOURCE_POWER_W:g} W (Total Power), 합계 {N_SOURCE * SOURCE_POWER_W:g} W")


    # %%
    oEditor.CreateSubRegion(
        [
            "NAME:SubRegionParameters",
            "+XPaddingType:="	, "Percentage Offset",
            "+XPadding:="		, "0",
            "-XPaddingType:="	, "Percentage Offset",
            "-XPadding:="		, "0",
            "+YPaddingType:="	, "Percentage Offset",
            "+YPadding:="		, "0",
            "-YPaddingType:="	, "Percentage Offset",
            "-YPadding:="		, "0",
            "+ZPaddingType:="	, "Percentage Offset",
            "+ZPadding:="		, "0",
            "-ZPaddingType:="	, "Percentage Offset",
            "-ZPadding:="		, "0",
            [
                "NAME:BoxForVirtualObjects",
                [
                    "NAME:LowPoint", 
                    1, 
                    1, 
                    1
                ],
                [
                    "NAME:HighPoint", 
                    -1, 
                    -1, 
                    -1
                ]
            ],
            [
                "NAME:SubRegionPartNames", 
                "PAO_Separate1"
            ],
            [
                "NAME:SubRegionSubmodelNames"
            ]
        ], 
        [
            "NAME:Attributes",
            "Name:="		, "SubRegion",
            "Flags:="		, "NonModel#Wireframe#",
            "Color:="		, "(143 175 143)",
            "Transparency:="	, 0,
            "PartCoordinateSystem:=", "Global",
            "UDMId:="		, "",
            "MaterialValue:="	, "\"air\"",
            "SurfaceMaterialValue:=", "\"\"",
            "SolveInside:="		, True,
            "ShellElement:="	, False,
            "ShellElementThickness:=", "nan ",
            "ReferenceTemperature:=", "nan ",
            "IsMaterialEditable:="	, True,
            "IsSurfaceMaterialEditable:=", True,
            "UseMaterialAppearance:=", False,
            "IsLightweight:="	, False
        ])
    oModule = oDesign.GetModule("MeshRegion")
    oModule.AssignMeshRegion(
        [
            "NAME:MeshRegion1",
            "Enable:="		, True,
            "MeshMethod:="		, "MesherHD",
            "UserSpecifiedSettings:=", True,
            "MaxElementSizeX:="	, f"{MESH_REGION_X}mm",
            "MaxElementSizeY:="	, f"{MESH_REGION_Y}mm",
            "MaxElementSizeZ:="	, f"{mesh_z:.6g}mm",
            "MinElementsInGap:="	, str(MIN_ELEMENTS_IN_GAP),
            "MinElementsOnEdge:="	, str(MIN_ELEMENTS_ON_EDGE),
            "MaxSizeRatio:="	, "2",
            "NoOGrids:="		, True,
            "EnableMLM:="		, True,
            "EnforeMLMType:="	, "3D",
            "MaxLevels:="		, "0",
            "BufferLayers:="	, "0",
            "UniformMeshParametersType:=", "XYZ Max Sizes",
            "StairStepMeshing:="	, False,
            "2DMLMType:="		, "2DMLM_None",
            "MinGapX:="		, "0.1mm",
            "MinGapY:="		, "0.1mm",
            "MinGapZ:="		, "0.1mm",
            "Objects:="		, ["SubRegion"],
            "ProximitySizeFunction:=", True,
            "CurvatureSizeFunction:=", True,
            "EnableTransition:="	, False,
            "OptimizePCBMesh:="	, True,
            "Enable2DCutCell:="	, False,
            "EnforceCutCellMeshing:=", False,
            "Enforce2dot5DCutCell:=", False
        ], 
        [
            "NAME:Geometrical Attributes",
            "MinSlackX:="		, "0mm",
            "MaxSlackX:="		, "0mm",
            "MinSlackY:="		, "0mm",
            "MaxSlackY:="		, "0mm",
            "MinSlackZ:="		, "0mm",
            "MaxSlackZ:="		, "0mm",
            "MinBboxX:="		, "0mm",
            "MaxBboxX:="		, "0mm",
            "MinBboxY:="		, "0mm",
            "MaxBboxY:="		, "0mm",
            "MinBboxZ:="		, "0mm",
            "MaxBboxZ:="		, "0mm"
        ])
    oModule.EditGlobalMeshRegion(
        [
            "NAME:Settings",
            "MeshMethod:="		, "MesherHD",
            "UserSpecifiedSettings:=", True,
            "ComputeGap:="		, True,
            "MaxElementSizeX:="	, f"{GLOBAL_MESH_X}mm",
            "MaxElementSizeY:="	, f"{GLOBAL_MESH_Y}mm",
            "MaxElementSizeZ:="	, f"{GLOBAL_MESH_Z}mm",
            "MinElementsInGap:="	, str(GLOBAL_MIN_ELEMENTS_IN_GAP),
            "MinElementsOnEdge:="	, str(GLOBAL_MIN_ELEMENTS_ON_EDGE),
            "MaxSizeRatio:="	, "2",
            "NoOGrids:="		, True,
            "EnableMLM:="		, True,
            "EnforeMLMType:="	, "3D",
            "MaxLevels:="		, "0",
            "BufferLayers:="	, "0",
            "UniformMeshParametersType:=", "XYZ Max Sizes",
            "StairStepMeshing:="	, False,
            "MinGapX:="		, "0.1mm",
            "MinGapY:="		, "0.1mm",
            "MinGapZ:="		, "0.1mm",
            "Objects:="		, ["Region"],
            "StairStepSliderMeshing:=", False,
            "FacetLevel:="		, "3",
            "ProximitySizeFunction:=", True,
            "CurvatureSizeFunction:=", True,
            "EnableTransition:="	, False,
            "OptimizePCBMesh:="	, True,
            "Enable2DCutCell:="	, False,
            "EnforceCutCellMeshing:=", False,
            "Enforce2dot5DCutCell:=", False
        ])


    # %%
    # 전원분기 입구 국소 메시 — 박스 x폭을 power_input_thick 에 맞춰 동적으로 만든다
    #   (위 PM_MESH_* 주석 참고). 서브리전 이름은 유체 전체용 "SubRegion"과 겹치지 않게
    #   "SubRegion_PM"으로 고정 — 같은 이름이면 AEDT가 자동으로 이름을 바꿔서 MeshRegion2가
    #   유체 전체 서브리전에 걸릴 수 있음.
    oEditor = oDesign.SetActiveEditor("3D Modeler")
    oEditor.CreateBox(
        [
            "NAME:BoxParameters",
            "XPosition:="		, "-195mm",
            "YPosition:="		, "47.5499999833333mm",
            "ZPosition:="		, f"{ch_top:.12g}mm",            # 유로 천장
            "XSize:="		, f"{params['power_input_thick']}mm",   # 전원분기 입구 폭 = 설계변수
            "YSize:="		, "-42.29999997mm",
            "ZSize:="		, f"{-depth:.12g}mm"
        ], 
        [
            "NAME:Attributes",
            "Name:="		, "power_input_mesh",
            "Flags:="		, "",
            "Color:="		, "(143 175 143)",
            "Transparency:="	, 0,
            "PartCoordinateSystem:=", "Global",
            "UDMId:="		, "",
            "MaterialValue:="	, "\"Al-Extruded\"",
            "SurfaceMaterialValue:=", "\"Steel-oxidised-surface\"",
            "SolveInside:="		, True,
            "ShellElement:="	, False,
            "ShellElementThickness:=", "0mm",
            "ReferenceTemperature:=", "20cel",
            "IsMaterialEditable:="	, True,
            "IsSurfaceMaterialEditable:=", True,
            "UseMaterialAppearance:=", False,
            "IsLightweight:="	, False
        ])
    oEditor.ChangeProperty(
        [
            "NAME:AllTabs",
            [
                "NAME:Geometry3DAttributeTab",
                [
                    "NAME:PropServers", 
                    "power_input_mesh"
                ],
                [
                    "NAME:ChangedProps",
                    [
                        "NAME:Model",
                        "Value:="		, False
                    ]
                ]
            ]
        ])
    oEditor.CreateSubRegion(
        [
            "NAME:SubRegionParameters",
            "+XPaddingType:="	, "Percentage Offset",
            "+XPadding:="		, "0",
            "-XPaddingType:="	, "Percentage Offset",
            "-XPadding:="		, "0",
            "+YPaddingType:="	, "Percentage Offset",
            "+YPadding:="		, "0",
            "-YPaddingType:="	, "Percentage Offset",
            "-YPadding:="		, "0",
            "+ZPaddingType:="	, "Percentage Offset",
            "+ZPadding:="		, "0",
            "-ZPaddingType:="	, "Percentage Offset",
            "-ZPadding:="		, "0",
            [
                "NAME:BoxForVirtualObjects",
                [
                    "NAME:LowPoint", 
                    1, 
                    1, 
                    1
                ],
                [
                    "NAME:HighPoint", 
                    -1, 
                    -1, 
                    -1
                ]
            ],
            [
                "NAME:SubRegionPartNames", 
                "power_input_mesh"
            ],
            [
                "NAME:SubRegionSubmodelNames"
            ]
        ], 
        [
            "NAME:Attributes",
            "Name:="		, "SubRegion_PM",
            "Flags:="		, "NonModel#Wireframe#",
            "Color:="		, "(143 175 143)",
            "Transparency:="	, 0,
            "PartCoordinateSystem:=", "Global",
            "UDMId:="		, "",
            "MaterialValue:="	, "\"air\"",
            "SurfaceMaterialValue:=", "\"\"",
            "SolveInside:="		, True,
            "ShellElement:="	, False,
            "ShellElementThickness:=", "nan ",
            "ReferenceTemperature:=", "nan ",
            "IsMaterialEditable:="	, True,
            "IsSurfaceMaterialEditable:=", True,
            "UseMaterialAppearance:=", False,
            "IsLightweight:="	, False
        ])
    oModule = oDesign.GetModule("MeshRegion")
    oModule.AssignMeshRegion(
        [
            "NAME:MeshRegion2",
            "Enable:="		, True,
            "MeshMethod:="		, "MesherHD",
            "UserSpecifiedSettings:=", True,
            "MaxElementSizeX:="	, f"{PM_MESH_X}mm",
            "MaxElementSizeY:="	, f"{PM_MESH_Y}mm",
            "MaxElementSizeZ:="	, f"{pm_mesh_z:.6g}mm",
            "MinElementsInGap:="	, "3",
            "MinElementsOnEdge:="	, "2",
            "MaxSizeRatio:="	, "2",
            "NoOGrids:="		, True,
            "EnableMLM:="		, True,
            "EnforeMLMType:="	, "3D",
            "MaxLevels:="		, "0",
            "BufferLayers:="	, "0",
            "UniformMeshParametersType:=", "XYZ Max Sizes",
            "StairStepMeshing:="	, False,
            "2DMLMType:="		, "2DMLM_None",
            "MinGapX:="		, "0.1mm",
            "MinGapY:="		, "0.1mm",
            "MinGapZ:="		, "0.1mm",
            "Objects:="		, ["SubRegion_PM"],
            "ProximitySizeFunction:=", True,
            "CurvatureSizeFunction:=", True,
            "EnableTransition:="	, False,
            "OptimizePCBMesh:="	, True,
            "Enable2DCutCell:="	, False,
            "EnforceCutCellMeshing:=", False,
            "Enforce2dot5DCutCell:=", False
        ], 
        [
            "NAME:Geometrical Attributes",
            "MinSlackX:="		, "0mm",
            "MaxSlackX:="		, "0mm",
            "MinSlackY:="		, "0mm",
            "MaxSlackY:="		, "0mm",
            "MinSlackZ:="		, "0mm",
            "MaxSlackZ:="		, "0mm",
            "MinBboxX:="		, "0mm",
            "MaxBboxX:="		, "0mm",
            "MinBboxY:="		, "0mm",
            "MaxBboxY:="		, "0mm",
            "MinBboxZ:="		, "0mm",
            "MaxBboxZ:="		, "0mm"
        ])

    # %%
    oEditor.UpdatePriorityList(
        [
            "NAME:UpdatePriorityListData",
            [
                "NAME:PriorityListParameters",
                "EntityType:="		, "Object",
                "EntityList:="		, "PAO_Separate1",
                "PriorityNumber:="	, 2,
                "PriorityListType:="	, "3D"
            ],
            [
                "NAME:PriorityListParameters",
                "EntityType:="		, "Object",
                "EntityList:="		, "plate, plate_base",
                "PriorityNumber:="	, 3,
                "PriorityListType:="	, "3D"
            ],
            
        ])

    # %%
    # 2패스 전용 측정면 — measure=False(pass_compare.py)면 만들지 않는다
    if measure:
        # 유량 측정면 셋 — 모두 핀 없는 통로의 단면 전체를 덮고, 벽 속으로 FLOW_PLANE_OVERLAP_MM 더 나간다
        #   (모듈 설명 참고). 분기비 = Rectangle1 ÷ (Rectangle1 + Q_pass2) 로 같은 방식으로 잰 두 유량의 비라 단면 측정
        #   편향이 상쇄되고, Q_mid(4 LPM 이어야 함)로 그 편향의 크기를 매 회차 기록한다.
        print(f"  {describe_bank(params, 1)}")
        print(f"  {describe_bank(params, 2)}")
        ov = FLOW_PLANE_OVERLAP_MM
        #   Rectangle1 : 전원모듈 분기 입구 — 분기 입구(y=5.25)에서 약 4 mm 안쪽(y=9), 입구 직후의 꺾인 흐름을 피함.
        #                x 폭 = power_input_thick(설계변수)
        _rect(oEditor, "Rectangle1", (MID_PASSAGE_X_WALL - ov, 9.0, ch_top + ov),
              -(depth + 2 * ov), params['power_input_thick'] + 2 * ov, "y")
        #   Q_pass2    : 2차 통과 출구 통로(T_pass2 와 같은 단면) — 2차 핀뱅크를 다 지나고 분기와 합류하기 전
        t2_wall_x = PLATE_X_RIGHT_WALL - params['input_thick'] - PASS2_EXIT_FROM_INPUT
        _rect(oEditor, "Q_pass2", (t2_wall_x + ov, PASS2_EXIT_Y, ch_top + ov),
              -(depth + 2 * ov), -(params['mid_thick'] + 2 * ov), "y")
        #   Q_mid      : 1차 통과 후 가운데 통로(T_pass1 과 같은 단면) — 분기 전이라 4 LPM 전부가 지난다
        _rect(oEditor, "Q_mid", (MID_PASSAGE_X_WALL - ov, MID_PASSAGE_Y, ch_top - depth - ov),
              depth + 2 * ov, params['mid_input_thick'] + 2 * ov, "y")

        # %%
        # 1차 통과 후 PAO 온도 측정면 (T_pass1) — 가운데 통로 단면에서 벽마다 T_PASS1_INSET_MM 띄움
        #   (상단 상수 주석 참고). WhichAxis y 에서 Width 는 z 방향, Height 는 x 방향(Rectangle1 과 같음).
        #   통로 폭이 mid_input_thick 이라 사각형 폭도 설계마다 따라간다.
        t1_inset = T_PASS1_INSET_MM
        oEditor.CreateRectangle(
            [
                "NAME:RectangleParameters",
                "IsCovered:="		, True,
                "XStart:="		, f"{round(MID_PASSAGE_X_WALL + t1_inset, 6)}mm",
                "YStart:="		, f"{MID_PASSAGE_Y}mm",
                "ZStart:="		, f"{round(ch_top - depth + t1_inset, 6)}mm",
                "Width:="		, f"{round(depth - 2 * t1_inset, 6)}mm",
                "Height:="		, f"{round(params['mid_input_thick'] - 2 * t1_inset, 6)}mm",
                "WhichAxis:="		, "y"
            ],
            [
                "NAME:Attributes",
                "Name:="		, "T_pass1",
                "Flags:="		, "NonModel#",
                "Color:="		, "(143 175 143)",
                "Transparency:="	, 0,
                "PartCoordinateSystem:=", "Global",
                "UDMId:="		, "",
                "MaterialValue:="	, "\"Al-Extruded\"",
                "SurfaceMaterialValue:=", "\"Steel-oxidised-surface\"",
                "SolveInside:="		, True,
                "ShellElement:="	, False,
                "ShellElementThickness:=", "0mm",
                "ReferenceTemperature:=", "20cel",
                "IsMaterialEditable:="	, True,
                "IsSurfaceMaterialEditable:=", True,
                "UseMaterialAppearance:=", False,
                "IsLightweight:="	, False
            ])

        # 2차 통과 후·합류 전 PAO 온도 측정면 (T_pass2) — 상단 상수 주석 참고. 크기는 음수(−x, −z 방향)로 그린다.
        #   (t2_wall_x 는 위 Q_pass2 에서 계산한 같은 통로 벽)
        oEditor.CreateRectangle(
            [
                "NAME:RectangleParameters",
                "IsCovered:="		, True,
                "XStart:="		, f"{round(t2_wall_x - t1_inset, 6)}mm",
                "YStart:="		, f"{PASS2_EXIT_Y}mm",
                "ZStart:="		, f"{round(ch_top - t1_inset, 6)}mm",
                "Width:="		, f"{-round(depth - 2 * t1_inset, 6)}mm",
                "Height:="		, f"{-round(params['mid_thick'] - 2 * t1_inset, 6)}mm",
                "WhichAxis:="		, "y"
            ],
            [
                "NAME:Attributes",
                "Name:="		, "T_pass2",
                "Flags:="		, "NonModel#",
                "Color:="		, "(143 175 143)",
                "Transparency:="	, 0,
                "PartCoordinateSystem:=", "Global",
                "UDMId:="		, "",
                "MaterialValue:="	, "\"Al-Extruded\"",
                "SurfaceMaterialValue:=", "\"Steel-oxidised-surface\"",
                "SolveInside:="		, True,
                "ShellElement:="	, False,
                "ShellElementThickness:=", "0mm",
                "ReferenceTemperature:=", "20cel",
                "IsMaterialEditable:="	, True,
                "IsSurfaceMaterialEditable:=", True,
                "UseMaterialAppearance:=", False,
                "IsLightweight:="	, False
            ])

    # %%
    oEditor.Unite(
        [
            "NAME:Selections",
            "Selections:="		, "plate,plate_base"
        ], 
        [
            "NAME:UniteParameters",
            "KeepOriginals:="	, False,
            "TurnOnNBodyBoolean:="	, True
        ])

    # %%
    oModule = oDesign.GetModule("AnalysisSetup")
    oModule.InsertSetup("IcepakSteadyState", 
        [
            "NAME:Setup1",
            "Enabled:="		, True,
            [
                "NAME:MeshLink",
                "ImportMesh:="		, False
            ],
            "Flow Regime:="		, "Laminar",
            "Include Temperature:="	, True,
            "Include Flow:="	, True,
            "Include Gravity:="	, False,
            "Include Solar:="	, False,
            "Solution Initialization - X Velocity:=", "0m_per_sec",
            "Solution Initialization - Y Velocity:=", "0m_per_sec",
            "Solution Initialization - Z Velocity:=", "0m_per_sec",
            "Solution Initialization - Temperature:=", "AmbientTemp",
            "Solution Initialization - Turbulent Kinetic Energy:=", "1m2_per_s2",
            "Solution Initialization - Turbulent Dissipation Rate:=", "1m2_per_s3",
            "Solution Initialization - Specific Dissipation Rate:=", "1diss_per_s",
            "Solution Initialization - Use Model Based Flow Initialization:=", False,
            "Convergence Criteria - Flow:=", "0.001",
            "Convergence Criteria - Energy:=", "1e-07",
            "Convergence Criteria - Turbulent Kinetic Energy:=", "0.001",
            "Convergence Criteria - Turbulent Dissipation Rate:=", "0.001",
            "Convergence Criteria - Specific Dissipation Rate:=", "0.001",
            "Convergence Criteria - Discrete Ordinates:=", "1e-06",
            "Convergence Criteria - Joule Heating:=", "1e-07",
            "GPU Convergence Criteria - Flow:=", "0.001",
            "GPU Convergence Criteria - Energy:=", "1e-05",
            "GPU Convergence Criteria - Turbulent Kinetic Energy:=", "0.001",
            "GPU Convergence Criteria - Turbulent Dissipation Rate:=", "0.001",
            "GPU Convergence Criteria - Specific Dissipation Rate:=", "0.001",
            "GPU Convergence Criteria - Discrete Ordinates:=", "1e-05",
            "GPU Convergence Criteria - Joule Heating:=", "1e-07",
            "IsEnabled:="		, False,
            "Radiation Model:="	, "Off",
            "Solar Radiation Model:=", "Solar Radiation Calculator",
            "Solar Enable Participating Solids:=", False,
            "Solar Radiation - Scattering Fraction:=", "0",
            "Solar Radiation - North X:=", "0",
            "Solar Radiation - North Y:=", "0",
            "Solar Radiation - North Z:=", "1",
            "Solar Radiation - Day:=", 1,
            "Solar Radiation - Month:=", 1,
            "Solar Radiation - Hours:=", 0,
            "Solar Radiation - Minutes:=", 0,
            "Solar Radiation - GMT:=", "0",
            "Solar Radiation - Latitude:=", "0",
            "Solar Radiation - Latitude Direction:=", "North",
            "Solar Radiation - Longitude:=", "0",
            "Solar Radiation - Longitude Direction:=", "East",
            "Solar Radiation - Ground Reflectance:=", "0",
            "Solar Radiation - Sunshine Fraction:=", "0",
            "Under-relaxation - Pressure:=", "0.3",
            "Under-relaxation - Momentum:=", "0.7",
            "Under-relaxation - Temperature:=", "1",
            "Under-relaxation - Turbulent Kinetic Energy:=", "0.8",
            "Under-relaxation - Turbulent Dissipation Rate:=", "0.8",
            "Under-relaxation - Specific Dissipation Rate:=", "0.8",
            "Under-relaxation - Joule Heating:=", "1",
            "Under-relaxation - Body Force:=", "1",
            "Under-relaxation - Turbulent Viscosity:=", "1",
            "Discretization Scheme - Pressure:=", "Standard",
            "Discretization Scheme - Momentum:=", "First",
            "Discretization Scheme - Temperature:=", "First",
            "Secondary Gradient:="	, False,
            "Discretization Scheme - Turbulent Kinetic Energy:=", "First",
            "Discretization Scheme - Turbulent Dissipation Rate:=", "First",
            "Discretization Scheme - Specific Dissipation Rate:=", "First",
            "Discretization Scheme - Discrete Ordinates:=", "First",
            "Linear Solver Type - Pressure:=", "V",
            "Linear Solver Type - Momentum:=", "flex",
            "Linear Solver Type - Temperature:=", "F",
            "Linear Solver Type - Turbulent Kinetic Energy:=", "flex",
            "Linear Solver Type - Turbulent Dissipation Rate:=", "flex",
            "Linear Solver Type - Specific Dissipation Rate:=", "flex",
            "Linear Solver Type - Joule Heating:=", "F",
            "Linear Solver Termination Criterion - Pressure:=", "0.1",
            "Linear Solver Termination Criterion - Momentum:=", "0.1",
            "Linear Solver Termination Criterion - Temperature:=", "0.1",
            "Linear Solver Termination Criterion - Turbulent Kinetic Energy:=", "0.1",
            "Linear Solver Termination Criterion - Turbulent Dissipation Rate:=", "0.1",
            "Linear Solver Termination Criterion - Specific Dissipation Rate:=", "0.1",
            "Linear Solver Termination Criterion - Joule Heating:=", "1e-09",
            "Linear Solver Residual Reduction Tolerance - Pressure:=", "0.1",
            "Linear Solver Residual Reduction Tolerance - Momentum:=", "0.1",
            "Linear Solver Residual Reduction Tolerance - Temperature:=", "0.1",
            "Linear Solver Residual Reduction Tolerance - Turbulent Kinetic Energy:=", "0.1",
            "Linear Solver Residual Reduction Tolerance - Turbulent Dissipation Rate:=", "0.1",
            "Linear Solver Residual Reduction Tolerance - Specific Dissipation Rate:=", "0.1",
            "Linear Solver Residual Reduction Tolerance - Joule Heating:=", "1e-09",
            "Maximum Cycles:="	, "30",
            "Linear Solver Stabilization - Pressure:=", "None",
            "Linear Solver Stabilization - Temperature:=", "None",
            "Linear Solver Stabilization - Joule Heating:=", "None",
            "Coupled pressure-velocity formulation:=", False,
            "Turn off auto-pairing for grid interface creation:=", False,
            "2D Profile Interpolation Method:=", "Inverse Distance Weighted",
            "Frozen Flow Simulation:=", False,
            "TEC Coupling:="	, False,
            "Sequential Solve of Flow and Energy Equations:=", False,
            "Convergence Criteria - Max Iterations:=", 1000
        ])

    # %%
    print(f"[T5] AnalyzeAll 시작(메싱+솔브): {time.strftime('%H:%M:%S')}")
    oDesign.AnalyzeAll()
    print(f"[T6] AnalyzeAll 끝(메싱+솔브 완료): {time.strftime('%H:%M:%S')}")


    # %%
    # ── 결과 CSV 경로 (idx별) ──
    result_path = icepak_result_path(phase, idx)
    os.makedirs(os.path.dirname(result_path), exist_ok=True)

    # Fields Summary는 "Solutions" 모듈 소속.
    #   위에서 oModule이 AnalysisSetup으로 덮여 있으므로 반드시 다시 잡아야 함.
    oModule = oDesign.GetModule("Solutions")

    # Calculation 추가 순서 = CSV 행 순서. result_parser 의 ROW_* 인덱스가 이 순서를 그대로 전제하므로,
    # 여기 순서를 바꾸면 파싱이 통째로 어긋난다. V7 은 유로별 측정면이 없어 설계와 무관하게 N_SOURCE + 7 행이다.
    #   (S = N_SOURCE)
    #   행 0~(S-1) : source01~ 온도 (발열면 = 슬롯 바닥 접촉면 — 최저·최고·평균·표준편차)
    #   행 S       : Fan1_Passage 차압
    #   행 S+1     : Rectangle1 유량 (전원모듈 분기 입구)
    #   행 S+2     : Q_pass2 유량 (2차 통과 출구 통로, 합류 전)
    #   행 S+3     : Q_mid 유량 (1차 통과 후 가운데 통로, 4 LPM 이어야 함)
    #   행 S+4     : T_pass1 온도 (1차 통과 후 PAO)
    #   행 S+5     : Opening1 온도 (출구 PAO, 열수지 점검용)
    #   행 S+6     : T_pass2 온도 (2차 통과 후·합류 전 PAO)
    #   measure=False 면 행 S 차압 다음 행 S+1 이 Opening1 온도 (N_SOURCE + 2 행)
    calc_args = ["SolutionName:=", "Setup1 : SteadyState", "Variation:=", "Nominal"]

    for i in range(N_SOURCE):
        calc_args += ["Calculation:=",
                      ["Object", "Surface", f"source{i+1:02d}", "Temperature", "",
                       "Default", "Reduced", "Nominal", True]]

    # 차압 — 스크립트 리코더본에 빠져 있어 V1 설정 그대로 복원한 항목.
    #   Fan1_Passage는 Fan1 삽입 시 자동 생성되는 면 이름 (첫 실행에서 존재 확인 필요)
    calc_args += ["Calculation:=",
                  ["Object", "Surface", "Fan1_Passage", "Pressure", "0.00,0.00,1.00",
                   "Default", "Reduced", "Nominal", False]]

    # 출구 온도 — Opening1 행은 GUI 스크립트 리코더 기록 그대로 (Boundary 로 선택)
    opening_row = ["Calculation:=",
                   ["Boundary", "Surface", "Opening1", "Temperature", "0.00,0.00,1.00",
                    "Default", "Reduced", "Nominal", False]]
    if measure:
        # 유량 측정면 셋 — 모두 법선 y 단면이라 V6 Rectangle1 과 같은 설정으로 잰다
        for name in ("Rectangle1", "Q_pass2", "Q_mid"):
            calc_args += ["Calculation:=",
                          ["Object", "Surface", name, "Speed", "0.00,-1.00,0.00",
                           "Default", "Reduced", "Nominal", False]]
        # PAO 온도 셋
        calc_args += ["Calculation:=",
                      ["Object", "Surface", "T_pass1", "Temperature", "",
                       "Default", "Reduced", "Nominal", True]]
        calc_args += opening_row
        calc_args += ["Calculation:=",
                      ["Object", "Surface", "T_pass2", "Temperature", "",
                       "Default", "Reduced", "Nominal", True]]
    else:
        calc_args += opening_row

    oModule.EditFieldsSummarySetting(calc_args)
    print(f"[T7] Fields Summary 설정 끝, export 시작: {time.strftime('%H:%M:%S')}")
    oModule.ExportFieldsSummary(
        [
            "SolutionName:="	, "Setup1 : SteadyState",
            "DesignVariationKey:="	, "Nominal",
            "ExportFileName:="	, result_path,
            "IntrinsicValue:="	, ""
        ])
    print(f"[T8] Fields Summary export 끝: {time.strftime('%H:%M:%S')}")
    print(f"[{idx}] CSV 저장 완료: {result_path}")

    # ── PAO 부피 (교차검증용 로그) ──
    #   중량은 SolidWorks 값만으로 계산함(result_parser.FULL_SOLID_VOLUME_MM3 참고).
    #   이 값은 그 상수가 현재 형상과 맞는지 확인하는 용도로만 출력 —
    #   '알루미늄 부피 + 이 값'이 FULL_SOLID_VOLUME_MM3와 크게 다르면 상수를 다시 재야 함.
    pao_volume_mm3 = float(ipk.modeler["PAO_Separate1"].volume)
    print(f"[{idx}] PAO 부피: {pao_volume_mm3:.1f} mm^3 "
          f"(≈ {pao_volume_mm3 * 1e-9 * PAO_DENSITY:.4f} kg)")

    return ipk, result_path, pao_volume_mm3

