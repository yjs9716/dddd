from ansys.aedt.core import Desktop, Icepak
import os, shutil, time

from paths import AEDT_PROJ_PATH as PROJ_PATH, ICEPAK_RESULT_DIR
from fins import channel_offsets, describe

# 전원모듈 입구 측정 사각형(Rectangle1)의 폭 [mm]. 높이는 power_input_thick(설계변수).
#   유량 환산 면적은 CSV의 Area/Volume 열 실측값을 쓰므로(메시 이산화로 도면값과
#   어긋날 수 있어서) 이 상수는 사각형 생성에만 쓰임 — result_parser는 참조하지 않음
PM_INLET_WIDTH_MM = 8.0

# PAO 밀도 [kg/m^3] — AddMaterial의 mass_density와 동일해야 함
PAO_DENSITY = 794.0

# ── 측정 대상 개수 — CSV 행 구조를 결정하므로 result_parser가 이 값을 import해서 씀 ──
#   여기를 바꾸면 파싱 쪽 행 인덱스가 자동으로 따라감 (두 파일이 어긋날 일 없게)
N_SOURCE = 9   # 발열채널(source01~) 개수 — 양 끝에 하나씩 추가되어 8→9
#   레인 측정 개수는 통과당 유로 전체(fin_count+1)라 설계마다 다르다 — 고정 상수
#   없음. result_parser가 params["fin_count"]로 매 idx마다 직접 계산한다.

# ── 핀뱅크 측정면 기준 좌표 [mm] ──────────────────────────────
#   V4에서는 레인 7개의 y좌표를 상수로 박아뒀지만(y_start − 9.857142857·i),
#   V5는 핀 개수·두께가 변수라 매 설계마다 계산해야 한다. 그래서 "기준점"만
#   상수로 두고, 각 유로의 위치는 fins.channel_offsets()가 계산한 오프셋을 더해 만든다.
#
#   V5 실제 형상(핀뱅크 86.5mm)에서 실측 확정한 값 — V4 값(-101.25 / -4.749999983,
#   핀뱅크 66.5mm 기준)에서 각각 +10mm 이동했다. 핀뱅크 길이가 66.5→86.5로 20mm
#   늘어난 만큼이 상단벽 기준으로 대칭 배분된 결과로 보인다.
FIN_BANK1_Y_START = -91.24999998     # 1차 통과 핀뱅크 상단벽 y좌표
FIN_BANK2_Y_START = 5.250000017      # 2차 통과 핀뱅크 상단벽 y좌표

#   측정 사각형의 z 범위 — 유로의 유동 단면 전체를 덮어야 한다.
#   fin_height는 8.0mm(OLHD.FIXED_PARAMS)로 유로 깊이와 정확히 같다 — 우회공간이
#   없으므로 측정 사각형도 그냥 유로 깊이 그대로 덮으면 된다(핀 높이를 따로 볼 필요 없음).
CHANNEL_Z_TOP    = 7.999999983       # 유로 천장 z좌표
CHANNEL_DEPTH_MM = 8.0               # 유로 깊이 = fin_height(고정값, fins.py 상단 주석 참고)

# ── 메시 크기 [mm] — 코드 흐름 검증용으로 크게 잡고 싶을 때 여기만 바꾸면 됨 ──
#   MESH_REGION_*  : SubRegion(유체 도메인)에 거는 로컬 메시
#   GLOBAL_MESH_*  : 전체 Region에 거는 글로벌 메시
#   실제 캠페인 돌릴 땐 다시 촘촘하게(예: 기존 X=2,Y/Z=1 / X=2,Y=2,Z=2) 낮춰야 함 —
#   거칠게 하면 얇은 두께(예: power_input_thick 5mm) 구간에서 메시 스냅으로 면적/유량이
#   틀어질 수 있음 (README 4-(3) 참고)
MESH_REGION_X = 1.0
MESH_REGION_Y = 1.0
MESH_REGION_Z = 1.0

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


def _create_lane_rectangles(oEditor, name_prefix, x_pos, y_bank_start, params):
    """핀뱅크의 유로 전체(fin_count+1개)에 측정 사각형을 만든다.

    핀 개수가 설계변수라 유로 개수(=fin_count+1)도 설계마다 달라진다. 예전처럼
    상대위치 몇 점만 골라 재면 "몇 번째가 대표점인가"가 애매해지는 문제가 있어서
    (짝수 유로에서 정중앙 유로가 없는 등), 그냥 전체를 다 재고 result_parser가
    표준편차로 압축하는 쪽으로 바꿨다. fins.channel_offsets()가 이미 전체 유로의
    위치를 계산해주므로 여기서는 그 개수만큼 반복 생성만 하면 된다.

      name_prefix   : "V_inlet" (1차) 또는 "V_inlet2" (2차)
      x_pos         : 측정 단면의 x좌표 [mm]
      y_bank_start  : 핀뱅크 상단벽의 y좌표 [mm] — 여기서 아래(-y)로 오프셋을 더해감

    y는 -방향으로 진행하므로 오프셋을 빼고, Width도 음수로 준다(V4와 동일한 규약).
    Height(z 방향)는 유로 깊이 전체(CHANNEL_DEPTH_MM) — fin_height가 고정값(8.0)으로
    유로 깊이와 같아 우회공간이 없으므로 핀 높이를 따로 신경 쓸 필요는 없다.

    이름은 인덱스 기반(`V_inlet_00`, `V_inlet_01`, ...)이라 fin_count가 몇이든
    항상 고유하다. result_parser가 이 개수(N=fin_count+1)를 알고 있어야
    CSV를 올바른 행수로 읽으므로, 이름 규칙이 바뀌면 result_parser도 같이 고칠 것.
    """
    channels = channel_offsets(params["fin_thick"], params["fin_count"])

    for k, (offset, gap) in enumerate(channels):
        y = y_bank_start - offset

        oEditor.CreateRectangle(
            [
                "NAME:RectangleParameters",
                "IsCovered:=", True,
                "XStart:=", f"{x_pos}mm",
                "YStart:=", f"{y}mm",
                "ZStart:=", f"{CHANNEL_Z_TOP}mm",
                "Width:=", f"{-gap}mm",
                "Height:=", f"{-CHANNEL_DEPTH_MM}mm",
                "WhichAxis:=", "X",
            ],
            [
                "NAME:Attributes",
                "Name:=", f"{name_prefix}_{k:02d}",
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

    print(f"  측정면 {name_prefix} (x={x_pos:.3f}mm) — 유로 {len(channels)}개 전부 생성 "
          f"(y {y_bank_start:.3f} ~ {y_bank_start - channels[-1][0] - channels[-1][1]:.3f})")


def run_icepak(desktop, ipk, step_file, idx, params):
    """
    반환: (ipk, result_path, pao_volume_mm3)
      result_path     : 이번 idx의 Fields Summary CSV 경로
      pao_volume_mm3  : 유로를 채운 PAO 부피 [mm^3] — 중량 계산용
                        (SolidWorks 알루미늄 중량 + PAO 중량 = 총 중량)
    """
    print(f"[T0] run_icepak 진입: {time.strftime('%H:%M:%S')}")

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
        design=f"IcepakDesign_{idx:03d}",
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
                        "mass_density:="	, "794",
                        "specific_heat:="	, "2219",
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
    oEditor.CreateBox(
        [
            "NAME:BoxParameters",
            "XPosition:="		, "231.499999983333mm",
            "YPosition:="		, "215mm",
            "ZPosition:="		, "-2.49999998333333mm",
            "XSize:="		, "-462.999999983333mm",
            "YSize:="		, "-430mm",
            "ZSize:="		, "20.9999999666667mm"
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
    oEditor.Delete(
        [
            "NAME:Selections",
            "Selections:="		, "PAO"
        ])

    # %%
    base_x = -172.9   # 기존 -152.1에서 step의 절반(20.8mm)만큼 이동 — 양 끝 채널 추가분
    step = 20.8*2
    for i in range(N_SOURCE):
        x_pos = base_x + i * step
        box_name = f"source{i + 1:02d}"   # source01 ~ source09

        oEditor.CreateBox(
            [
                "NAME:BoxParameters",
                "XPosition:=", f"{x_pos}mm",
                "YPosition:=", "5.24999998mm",
                "ZPosition:=", "10.50000002mm",
                "XSize:=", "13.3mm",
                "YSize:=", "-183mm",
                "ZSize:=", "8mm"
            ],
            [
                "NAME:Attributes",
                "Name:=", box_name,
                "Flags:=", "",
                "Color:=", "(143 175 143)",
                "Transparency:=", 0,
                "PartCoordinateSystem:=", "Global",
                "UDMId:=", "",
                "MaterialValue:=", "\"FR-4\"",
                "SurfaceMaterialValue:=", "\"Steel-oxidised-surface\"",
                "SolveInside:=", True,
                "ShellElement:=", False,
                "ShellElementThickness:=", "0mm",
                "ReferenceTemperature:=", "20cel",
                "IsMaterialEditable:=", True,
                "IsSurfaceMaterialEditable:=", True,
                "UseMaterialAppearance:=", False,
                "IsLightweight:=", False
            ])

    # %%
    box1 = ipk.modeler["PAO_Separate1"]
    target_faces = [face for face in box1.faces if abs(face.center[2] - 18.5) < 0.1]
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
                "IntakeTemp:="		, "20cel",
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
            "No Reverse Flow:=", False
        ])

    # %%
    oModule = oDesign.GetModule("BoundarySetup")
    oModule.AssignBlockBoundary(
        [
            "NAME:Block1",
            "Objects:="		, ["source01","source02","source03","source04","source05","source06","source07","source08","source09"],
            "Block Type:="		, "Solid",
            "Use External Conditions:=", False,
            "Use Total Power:="	, True,
            "Total Power:="		, "40W"
        ])


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
            "MaxElementSizeZ:="	, f"{MESH_REGION_Z}mm",
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
    # 측정면 x좌표 — 형상 변수에 따라 동적 계산 (V4에서 실측으로 확인한 기울기 그대로)
    #   1차: 194 − input_thick        (기존 159 고정값이면 input_thick이 바뀔 때 어긋남)
    #   2차: mid_input_thick − 194    (기존 -159 고정값이면 mid_input_thick에 대해 같은 문제)
    x_pos  = 194 - params['input_thick']
    x_pos2 = params['mid_input_thick'] - 194

    print(f"  {describe(params['fin_thick'], params['fin_count'])}")
    _create_lane_rectangles(oEditor, "V_inlet",  x_pos,  FIN_BANK1_Y_START, params)
    _create_lane_rectangles(oEditor, "V_inlet2", x_pos2, FIN_BANK2_Y_START, params)

    # %%
    oEditor.CreateRectangle(
        [
            "NAME:RectangleParameters",
            "IsCovered:="		, True,
            "XStart:="		, "-195mm",
            "YStart:="		, "6mm",   # 분기 안쪽으로 이동 — PAO 경계면 공유 회피
            "ZStart:="		, "7.999999983mm",
            "Width:="		, f"-{PM_INLET_WIDTH_MM}mm",
            # 전원모듈 입구 폭은 형상 변수에 따라 바뀌므로 동적 할당
            "Height:="		, f"{params['power_input_thick']}mm",
            "WhichAxis:="		, "y"
        ], 
        [
            "NAME:Attributes",
            "Name:="		, "Rectangle1",
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
    result_path = os.path.join(ICEPAK_RESULT_DIR, f"result_{idx:03d}.csv")
    os.makedirs(ICEPAK_RESULT_DIR, exist_ok=True)

    # Fields Summary는 "Solutions" 모듈 소속.
    #   위에서 oModule이 AnalysisSetup으로 덮여 있으므로 반드시 다시 잡아야 함.
    oModule = oDesign.GetModule("Solutions")

    # Calculation 추가 순서 = CSV 행 순서. result_parser의 ROW_* 인덱스가 이 순서를
    # 그대로 전제하므로, 여기 순서를 바꾸면 파싱이 통째로 어긋난다.
    #   행 0~8           : source01~09 온도
    #   행 9             : Fan1_Passage 차압
    #   행 10~(10+n-1)   : V_inlet_00~(n-1)   (1차 통과, n=fin_count+1, 설계마다 가변)
    #   행 (10+n)~(10+2n-1): V_inlet2_00~(n-1) (2차 통과)
    #   행 (10+2n)       : Rectangle1 (전원모듈 분기 입구)
    # V4는 레인 14줄을 손으로 나열했지만, V5는 유로 전체(개수 가변)를 다 재므로
    # 반복문으로 만든다 — result_parser도 같은 개수(params["fin_count"]+1)를 계산해서
    # 행 위치를 맞춘다.
    n_channels = int(round(params["fin_count"])) + 1
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

    for prefix in ("V_inlet", "V_inlet2"):
        for k in range(n_channels):
            calc_args += ["Calculation:=",
                          ["Object", "Surface", f"{prefix}_{k:02d}", "Speed",
                           "1.00,-0.00,-0.00", "Default", "Reduced", "Nominal", True]]

    calc_args += ["Calculation:=",
                  ["Object", "Surface", "Rectangle1", "Speed", "0.00,-1.00,0.00",
                   "Default", "Reduced", "Nominal", False]]

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

