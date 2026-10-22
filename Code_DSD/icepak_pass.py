"""
1·2·4패스 비교 전용 Icepak 해석 — icepak.run_icepak 에서 측정면만 뺀 복사본

캠페인 코드(icepak.py)는 건드리지 않는다. 형상 임포트·재질·발열원(17개 × 40 W)·팬·오프닝(역류 차단)·
메시·솔버 설정은 icepak.run_icepak 을 줄 단위로 그대로 옮겼고, 아래만 다르다.
  · 2패스 전용 측정면(유로 단면 V_inlet/V_inlet2, 분기 입구 Rectangle1, T_pass1, T_pass2)을 만들지 않는다.
  · Fields Summary 에 발열원 온도(source01~)와 팬 차압(Fan1_Passage)만 넣는다.
  · 결과 CSV 경로를 인자로 받는다(캠페인 Result 폴더와 섞이지 않게).
⚠ icepak.py 의 해석 설정(메시·물성·경계조건)을 바꾸면 이 파일도 같이 고칠 것.

전원분기 입구 국소 메시(power_input_mesh) 폭만 power_input_thick 값을 쓴다 — 1·2·4패스 모두 분기 입구가
같은 자리에 있으므로 STEP 형상의 실제 폭을 넣는다.
"""
import os, shutil, time

from ansys.aedt.core import Icepak

# 해석 상수는 캠페인(icepak.py) 값을 그대로 쓴다
from icepak import (PROJ_PATH, N_SOURCE, SOURCE_POWER_W, INLET_TEMP_C, PAO_DENSITY, PAO_SPECIFIC_HEAT,
                    MESH_REGION_X, MESH_REGION_Y, MESH_REGION_Z, PM_MESH_X, PM_MESH_Y, PM_MESH_Z,
                    MIN_ELEMENTS_IN_GAP, MIN_ELEMENTS_ON_EDGE,
                    GLOBAL_MESH_X, GLOBAL_MESH_Y, GLOBAL_MESH_Z,
                    GLOBAL_MIN_ELEMENTS_IN_GAP, GLOBAL_MIN_ELEMENTS_ON_EDGE)


def run_icepak_pass(desktop, ipk, step_file, idx, power_input_thick, result_path):
    """반환: (ipk, result_path). CSV 행: source01~ 온도 N_SOURCE 행 → Fan1_Passage 차압 1행."""
    phase = "pass"
    params = {"power_input_thick": power_input_thick}
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
        design=f"IcepakDesign_{phase + '_' if phase in ('dsd', 'gci') else ''}{idx:03d}",
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
    base_x = -172.9   # 슬롯 1 (가장 왼쪽)
    step = 20.8       # 슬롯 간격 — DSD·격자 시험은 20.8*2(한 칸 건너, 9개)였다
    for i in range(N_SOURCE):
        x_pos = base_x + i * step
        box_name = f"source{i + 1:02d}"   # source01 ~ source{N_SOURCE}

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
    oModule = oDesign.GetModule("BoundarySetup")
    oModule.AssignBlockBoundary(
        [
            "NAME:Block1",
            "Objects:="		, [f"source{i + 1:02d}" for i in range(N_SOURCE)],
            "Block Type:="		, "Solid",
            "Use External Conditions:=", False,
            "Use Total Power:="	, True,
            "Total Power:="		, f"{SOURCE_POWER_W:g}W"
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
            "ZPosition:="		, "7.99999998333333mm",
            "XSize:="		, f"{params['power_input_thick']}mm",   # 전원분기 입구 폭 = 설계변수
            "YSize:="		, "-42.29999997mm",
            "ZSize:="		, "-7.99999998333333mm"
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
            "MaxElementSizeZ:="	, f"{PM_MESH_Z}mm",
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
    # Fields Summary — 발열원 온도와 팬 차압만 (행 순서 = 추가 순서)
    os.makedirs(os.path.dirname(result_path), exist_ok=True)
    oModule = oDesign.GetModule("Solutions")
    calc_args = ["SolutionName:=", "Setup1 : SteadyState", "Variation:=", "Nominal"]
    for i in range(N_SOURCE):
        calc_args += ["Calculation:=",
                      ["Object", "Surface", f"source{i+1:02d}", "Temperature", "",
                       "Default", "Reduced", "Nominal", True]]
    calc_args += ["Calculation:=",
                  ["Object", "Surface", "Fan1_Passage", "Pressure", "0.00,0.00,1.00",
                   "Default", "Reduced", "Nominal", False]]
    oModule.EditFieldsSummarySetting(calc_args)
    oModule.ExportFieldsSummary(
        [
            "SolutionName:="	, "Setup1 : SteadyState",
            "DesignVariationKey:="	, "Nominal",
            "ExportFileName:="	, result_path,
            "IntrinsicValue:="	, ""
        ])
    print(f"[{idx}] CSV 저장 완료: {result_path}")
    return ipk, result_path
