from ansys.aedt.core import Desktop, Icepak
import os, shutil

from paths import AEDT_PROJ_PATH as PROJ_PATH, ICEPAK_RESULT_DIR

# 전원모듈 입구 측정 사각형(Rectangle1)의 폭 [mm]. 높이는 power_input_thick(설계변수).
#   유량 환산 면적은 CSV의 Area/Volume 열 실측값을 쓰므로(메시 이산화로 도면값과
#   어긋날 수 있어서) 이 상수는 사각형 생성에만 쓰임 — result_parser는 참조하지 않음
PM_INLET_WIDTH_MM = 8.0

# PAO 밀도 [kg/m^3] — AddMaterial의 mass_density와 동일해야 함
PAO_DENSITY = 794.0

# ── 측정 대상 개수 — CSV 행 구조를 결정하므로 result_parser가 이 값을 import해서 씀 ──
#   여기를 바꾸면 파싱 쪽 행 인덱스가 자동으로 따라감 (두 파일이 어긋날 일 없게)
N_SOURCE = 8   # 발열채널(source01~) 개수
N_LANE   = 7   # 통과 1회당 핀뱅크 레인(V_inlet / V_inlet2) 개수

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
        non_graphical=False,
        new_desktop=True,
        close_on_exit=False,
    )
    print("AEDT 켜짐")
    return desktop, None

def run_icepak(desktop, ipk, step_file, idx, params):
    """
    반환: (ipk, result_path, pao_volume_mm3)
      result_path     : 이번 idx의 Fields Summary CSV 경로
      pao_volume_mm3  : 유로를 채운 PAO 부피 [mm^3] — 중량 계산용
                        (SolidWorks 알루미늄 중량 + PAO 중량 = 총 중량)
    """
    # 기존 프로젝트 닫기 (AEDT는 유지)
    if ipk is not None:
        oDesktop = ipk.odesktop
        proj_name = ipk.project_name
        ipk = None
        oDesktop.CloseProject(proj_name)
        print("기존 프로젝트 닫음")
    else:
        # ipk가 None인 경우 = 스크립트를 새로 시작한 첫 회차.
        #   이때 AEDT는 이전 실행에서 켜진 채 남아있을 수 있고(PyAEDT가
        #   new_desktop=True여도 기존 세션을 재사용함), 그 세션이 같은 이름의
        #   프로젝트를 열어둔 상태다. 위 분기를 못 타서 그걸 안 닫으면,
        #   아래에서 같은 이름으로 새 프로젝트를 만들 때 이미 열린 프로젝트와
        #   충돌해 AEDT가 응답하지 않는다("Project ... has been created"까지만
        #   찍히고 디자인이 생성되지 않는 증상).
        #   → 디스크 파일을 지우기 전에, 열려 있는 동명 프로젝트를 먼저 닫는다.
        # os.path.basename은 실행 OS의 구분자만 인식하므로 \와 / 둘 다 직접 처리
        want = PROJ_PATH.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
        try:
            od = desktop.odesktop
            for name in list(od.GetProjectList()):
                if str(name) == want:
                    od.CloseProject(name)
                    print(f"이전 실행에서 열린 채 남은 프로젝트 닫음: {name}")
        except Exception as e:
            print(f"  ⚠ 남은 프로젝트 정리 실패(계속 진행): {e}")

    # 프로젝트를 저장할 폴더가 없으면 미리 만들어 둔다.
    #   폴더가 없으면 AEDT가 저장 단계에서 GUI에 모달 에러 팝업을 띄우는데,
    #   그 팝업이 COM 호출을 막아버려서 Icepak() 생성자가 영원히 반환되지 않는다
    #   ("Project ... has been created"까지 찍히고 그 뒤로 아무것도 안 나오는 증상).
    #   작업폴더를 새로 팠을 때 AEDT 하위폴더를 안 만들어두면 바로 이 상태가 됨.
    os.makedirs(os.path.dirname(PROJ_PATH), exist_ok=True)

    # 디스크 파일 삭제
    if os.path.exists(PROJ_PATH + ".aedt"):
        os.remove(PROJ_PATH + ".aedt")
    if os.path.exists(PROJ_PATH + ".aedtresults"):
        shutil.rmtree(PROJ_PATH + ".aedtresults")

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
    print("새 프로젝트 생성:", ipk.project_name)

    # STEP import
    ipk.modeler.import_3d_cad(step_file)
    print("임포트 완료:", step_file)

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
    base_x = -152.1
    step = 20.8*2
    for i in range(N_SOURCE):
        x_pos = base_x + i * step
        box_name = f"source{i + 1:02d}"   # source01 ~ source08

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
            "Objects:="		, ["source01","source02","source03","source04","source05","source06","source07","source08"],
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
    # x_pos: 1차통과 측정위치 — 형상 변수에 따라 동적 계산 (19/20/21mm 실측 기준 기울기 -1 확인)
    # (기존엔 159 고정값이라 input_thick이 바뀌면 측정면이 핀뱅크 시작점과 어긋났음)
    x_pos = 194 - params['input_thick']
    y_start = -101.25
    z_start = 7.999999983
    width = -7.357142857
    height = -7.499999967

    for i in range(N_LANE):
        y = y_start - (9.857142857 * i)

        oEditor.CreateRectangle(
            [
                "NAME:RectangleParameters",
                "IsCovered:=", True,
                "XStart:=", f"{x_pos}mm",
                "YStart:=", f"{y}mm",
                "ZStart:=", f"{z_start}mm",
                "Width:=", f"{width}mm",
                "Height:=", f"{height}mm",
                "WhichAxis:=", "X",
            ],
            [
                "NAME:Attributes",
                "Name:=", f"V_inlet_{i+1:02d}",
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

    # %%
    # x_pos2: 2차통과 핀뱅크 시작위치(mid_input_thick - 195)에서 1mm 안쪽 — 형상 변수에 따라 동적 계산
    # (기존엔 -159 고정값이라 mid_input_thick이 바뀌면 측정면이 핀뱅크 시작점과 어긋났음)
    x_pos2 = params['mid_input_thick'] - 194
    y_start2 = -4.749999983
    z_start2 = 7.999999983
    width2 = -7.357142857
    height2 = -7.499999967

    for i in range(N_LANE):
        y2 = y_start2 - (9.857142857 * i)

        oEditor.CreateRectangle(
            [
                "NAME:RectangleParameters",
                "IsCovered:=", True,
                "XStart:=", f"{x_pos2}mm",
                "YStart:=", f"{y2}mm",
                "ZStart:=", f"{z_start2}mm",
                "Width:=", f"{width2}mm",
                "Height:=", f"{height2}mm",
                "WhichAxis:=", "X",
            ],
            [
                "NAME:Attributes",
                "Name:=", f"V_inlet2_{i+1:02d}",
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
    oDesign.AnalyzeAll()


    # %%
    # ── 결과 CSV 경로 (idx별) ──
    result_path = os.path.join(ICEPAK_RESULT_DIR, f"result_{idx:03d}.csv")
    os.makedirs(ICEPAK_RESULT_DIR, exist_ok=True)

    # Fields Summary는 "Solutions" 모듈 소속.
    #   위에서 oModule이 AnalysisSetup으로 덮여 있으므로 반드시 다시 잡아야 함.
    oModule = oDesign.GetModule("Solutions")
    oModule.EditFieldsSummarySetting(
        [
            "SolutionName:="	, "Setup1 : SteadyState",
            "Variation:="		, "Nominal",
            "Calculation:="		, ["Object","Surface","source01","Temperature","","Default","Reduced","Nominal",True],
            "Calculation:="		, ["Object","Surface","source02","Temperature","","Default","Reduced","Nominal",True],
            "Calculation:="		, ["Object","Surface","source03","Temperature","","Default","Reduced","Nominal",True],
            "Calculation:="		, ["Object","Surface","source04","Temperature","","Default","Reduced","Nominal",True],
            "Calculation:="		, ["Object","Surface","source05","Temperature","","Default","Reduced","Nominal",True],
            "Calculation:="		, ["Object","Surface","source06","Temperature","","Default","Reduced","Nominal",True],
            "Calculation:="		, ["Object","Surface","source07","Temperature","","Default","Reduced","Nominal",True],
            "Calculation:="		, ["Object","Surface","source08","Temperature","","Default","Reduced","Nominal",True],
            # 행 8: 차압 (목적함수) — 스크립트 리코더본에 빠져 있어 V1 설정 그대로 복원함.
            #       Fan1_Passage는 Fan1 삽입 시 자동 생성되는 면 이름 (첫 실행에서 존재 확인 필요)
            "Calculation:="		, ["Object","Surface","Fan1_Passage","Pressure","0.00,0.00,1.00","Default","Reduced","Nominal",False],
            "Calculation:="		, ["Object","Surface","V_inlet_01","Speed","1.00,-0.00,-0.00","Default","Reduced","Nominal",True],
            "Calculation:="		, ["Object","Surface","V_inlet_02","Speed","1.00,-0.00,-0.00","Default","Reduced","Nominal",True],
            "Calculation:="		, ["Object","Surface","V_inlet_03","Speed","1.00,-0.00,-0.00","Default","Reduced","Nominal",True],
            "Calculation:="		, ["Object","Surface","V_inlet_04","Speed","1.00,-0.00,-0.00","Default","Reduced","Nominal",True],
            "Calculation:="		, ["Object","Surface","V_inlet_05","Speed","1.00,-0.00,-0.00","Default","Reduced","Nominal",True],
            "Calculation:="		, ["Object","Surface","V_inlet_06","Speed","1.00,-0.00,-0.00","Default","Reduced","Nominal",True],
            "Calculation:="		, ["Object","Surface","V_inlet_07","Speed","1.00,-0.00,-0.00","Default","Reduced","Nominal",True],
            "Calculation:="		, ["Object","Surface","V_inlet2_01","Speed","1.00,-0.00,-0.00","Default","Reduced","Nominal",True],
            "Calculation:="		, ["Object","Surface","V_inlet2_02","Speed","1.00,-0.00,-0.00","Default","Reduced","Nominal",True],
            "Calculation:="		, ["Object","Surface","V_inlet2_03","Speed","1.00,-0.00,-0.00","Default","Reduced","Nominal",True],
            "Calculation:="		, ["Object","Surface","V_inlet2_04","Speed","1.00,-0.00,-0.00","Default","Reduced","Nominal",True],
            "Calculation:="		, ["Object","Surface","V_inlet2_05","Speed","1.00,-0.00,-0.00","Default","Reduced","Nominal",True],
            "Calculation:="		, ["Object","Surface","V_inlet2_06","Speed","1.00,-0.00,-0.00","Default","Reduced","Nominal",True],
            "Calculation:="		, ["Object","Surface","V_inlet2_07","Speed","1.00,-0.00,-0.00","Default","Reduced","Nominal",True],
            "Calculation:="		, ["Object","Surface","Rectangle1","Speed","0.00,-1.00,0.00","Default","Reduced","Nominal",False]
        ])
    oModule.ExportFieldsSummary(
        [
            "SolutionName:="	, "Setup1 : SteadyState",
            "DesignVariationKey:="	, "Nominal",
            "ExportFileName:="	, result_path,
            "IntrinsicValue:="	, ""
        ])
    print(f"[{idx}] CSV 저장 완료: {result_path}")

    # ── PAO 부피 (교차검증용 로그) ──
    #   중량은 SolidWorks 값만으로 계산함(result_parser.FULL_SOLID_VOLUME_MM3 참고).
    #   이 값은 그 상수가 현재 형상과 맞는지 확인하는 용도로만 출력 —
    #   '알루미늄 부피 + 이 값'이 FULL_SOLID_VOLUME_MM3와 크게 다르면 상수를 다시 재야 함.
    pao_volume_mm3 = float(ipk.modeler["PAO_Separate1"].volume)
    print(f"[{idx}] PAO 부피: {pao_volume_mm3:.1f} mm^3 "
          f"(≈ {pao_volume_mm3 * 1e-9 * PAO_DENSITY:.4f} kg)")

    return ipk, result_path, pao_volume_mm3

