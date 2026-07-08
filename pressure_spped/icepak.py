from ansys.aedt.core import Desktop, Icepak
import os, shutil

PROJ_PATH = r"E:\Thermal_Anlaysis\Aedt\thermal_test"

def connect_aedt():
    desktop = Desktop(
        version="2025.1",
        non_graphical=False,
        new_desktop=True,
        close_on_exit=False,
    )
    print("AEDT 켜짐")
    return desktop, None

def run_icepak(desktop, ipk, step_file, idx):
    # 기존 프로젝트 닫기 (AEDT는 유지)
    if ipk is not None:
        oDesktop = ipk.odesktop
        proj_name = ipk.project_name
        ipk = None
        oDesktop.CloseProject(proj_name)
        print("기존 프로젝트 닫음")

    # 디스크 파일 삭제
    if os.path.exists(PROJ_PATH + ".aedt"):
        os.remove(PROJ_PATH + ".aedt")
    if os.path.exists(PROJ_PATH + ".aedtresults"):
        shutil.rmtree(PROJ_PATH + ".aedtresults")

    # 새 프로젝트 생성
    ipk = Icepak(
        project=PROJ_PATH,
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

    # Region 패딩 0으로
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
                    ["NAME:+X Padding Data", "Value:=", "0"],
                    ["NAME:-X Padding Data", "Value:=", "0"],
                    ["NAME:+Y Padding Data", "Value:=", "0"],
                    ["NAME:-Y Padding Data", "Value:=", "0"],
                    ["NAME:+Z Padding Data", "Value:=", "0"],
                    ["NAME:-Z Padding Data", "Value:=", "0"]
                ]
            ]
        ])

    # Design Settings
    oDesign.SetDesignSettings(
        [
            "NAME:Design Settings Data",
            "Perform Minimal validation:=", False,
            "Default Fluid Material:=", "air",
            "Default Solid Material:=", "Al-Extruded",
            "Default Surface Material:=", "Steel-oxidised-surface",
            "AmbientTemperature:=", "25cel",
            "AmbientPressure:=", "0n_per_meter_sq",
            "AmbientRadiationTemperature:=", "20cel",
            "Gravity Vector CS ID:=", 1,
            "Gravity Vector Axis:=", "Z",
            "Positive:=", False,
            "ExportOnSimulationComplete:=", False,
            "ExportDirectory:=", "",
            "SherlockExportOnSimulationComplete:=", False,
            "SherlockExportAsFatigue:=", True,
            "SherlockExportDirectory:=", "E:/Thermal_Anlaysis/Aedt/thermal_test.aedtexport/Icepak_M6C/",
            "AutoLaunchMeshViewer:=", True,
            "MeshCadAsLightWeight:=", True,
            "EnableTransitionTemplate:=", False,
            "TempSecondaryGradientSkewMesh:=", False,
            "EnableMeshByLayerFor2DMLM:=", False,
            "BoundaryBasedMeshRefinement:=", False,
            "EnableAltitudeEffects:=", False,
            "UpdateFanCurve:=", False,
            "Altitude:=", "0meter",
            "EnableIdealGasLaw:=", False,
            "OperatingPressure:=", "101325n_per_meter_sq",
            "EnableOperatingDensity:=", False,
            "OperatingDensity:=", "1.225kg_per_m3",
            "AppendTemplateToFieldsSummaryReport:=", False,
            "EnableLoadSolution:=", False
        ],
        [
            "NAME:Model Validation Settings",
            "EntityCheckLevel:=", "Strict",
            "IgnoreUnclassifiedObjects:=", False,
            "SkipIntersectionChecks:=", False
        ])

    # PAO 재질 생성
    oDefinitionManager = oProject.GetDefinitionManager()
    if not oDefinitionManager.DoesMaterialExist("PAO"):
        try:
            oDefinitionManager.AddMaterial(
                [
                    "NAME:PAO",
                    "CoordinateSystemType:=", "Cartesian",
                    "BulkOrSurfaceType:=", 1,
                    ["NAME:PhysicsTypes", "set:=", ["Thermal"]],
                    "thermal_conductivity:=", "0.142",
                    "mass_density:=", "794",
                    "specific_heat:=", "2219",
                    "thermal_expansion_coefficient:=", "0.00083",
                    ["NAME:thermal_material_type", "property_type:=", "ChoiceProperty", "Choice:=", "Fluid"],
                    "diffusivity:=", "1",
                    "molecular_mass:=", "1",
                    "viscosity:=", "0.0099",
                    ["NAME:clarity_type", "property_type:=", "ChoiceProperty", "Choice:=", "Opaque"]
                ])
            print("로그: PAO 재질 생성 완료")
        except:
            print("로그: PAO 이미 존재, 스킵")

    # STEP import 후 오브젝트 이름 변경 (부피 기준 정렬)
    objects = [ipk.modeler[name] for name in ipk.modeler.object_names if "ttpkp" in name]
    objects.sort(key=lambda o: o.volume)
    objects[0].name = "plate"
    objects[1].name = "plate_base"
    print(f"이름 변경 완료: {[o.name for o in objects]}")

    # 재질 Al-Extruded 할당
    oEditor.ChangeProperty(
        [
            "NAME:AllTabs",
            [
                "NAME:Geometry3DAttributeTab",
                ["NAME:PropServers", "plate", "plate_base"],
                [
                    "NAME:ChangedProps",
                    ["NAME:Material", "Value:=", "\"Al-Extruded\""]
                ]
            ]
        ])

    # PAO 박스 생성 → Subtract → SeparateBody → 불필요한 PAO 삭제
    oEditor.CreateBox(
        [
            "NAME:BoxParameters",
            "XPosition:=", "231.499999983333mm",
            "YPosition:=", "215mm",
            "ZPosition:=", "-2.49999998333333mm",
            "XSize:=", "-462.999999983333mm",
            "YSize:=", "-430mm",
            "ZSize:=", "20.9999999666667mm"
        ],
        [
            "NAME:Attributes",
            "Name:=", "PAO",
            "Flags:=", "",
            "Color:=", "(143 175 143)",
            "Transparency:=", 0,
            "PartCoordinateSystem:=", "Global",
            "UDMId:=", "",
            "MaterialValue:=", "\"PAO\"",
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
    oEditor.Subtract(
        [
            "NAME:Selections",
            "Blank Parts:=", "PAO",
            "Tool Parts:=", "plate, plate_base"
        ],
        [
            "NAME:SubtractParameters",
            "KeepOriginals:=", True,
            "TurnOnNBodyBoolean:=", True
        ])
    oEditor.SeparateBody(
        [
            "NAME:Selections",
            "Selections:=", "PAO",
            "NewPartsModelFlag:=", "Model"
        ],
        ["CreateGroupsForNewObjects:=", False])
    oEditor.Delete(
        ["NAME:Selections", "Selections:=", "PAO"])

    # source 박스 19개 생성
    base_x = -191.1
    step   = 20.5
    for i in range(19):
        x_pos    = base_x + i * step
        box_name = f"source{i + 1}"
        oEditor.CreateBox(
            [
                "NAME:BoxParameters",
                "XPosition:=", f"{x_pos}mm",
                "YPosition:=", "29.99999998mm",
                "ZPosition:=", "10.50000002mm",
                "XSize:=", "13.3mm",
                "YSize:=", "-167mm",
                "ZSize:=", "3mm"
            ],
            [
                "NAME:Attributes",
                "Name:=", box_name,
                "Flags:=", "",
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
                "IsLightweight:=", False
            ])

    # Fan/Opening face 동적 탐지
    box1         = ipk.modeler["PAO_Separate1"]
    target_faces = [face for face in box1.faces if abs(face.center[2] - 18.5) < 0.1]
    fan_face     = [face for face in target_faces if face.center[0] < 0][0]
    opening_face = [face for face in target_faces if face.center[0] > 0][0]
    fan_x = fan_face.center[0]
    fan_y = fan_face.center[1]
    fan_z = fan_face.center[2]

    # Fan 생성
    oEditor.InsertNativeComponent(
        [
            "NAME:InsertNativeComponentData",
            "TargetCS:=", "Global",
            "SubmodelDefinitionName:=", "Fan1",
            ["NAME:ComponentPriorityLists"],
            "NextUniqueID:=", 0,
            "MoveBackwards:=", False,
            "DatasetType:=", "ComponentDatasetType",
            ["NAME:DatasetDefinitions"],
            [
                "NAME:BasicComponentInfo",
                "ComponentName:=", "Fan1",
                "Company:=", "",
                "Company URL:=", "",
                "Model Number:=", "",
                "Help URL:=", "",
                "Version:=", "1.0",
                "Notes:=", "",
                "IconType:=", "Fan"
            ],
            ["NAME:GeometryDefinitionParameters", ["NAME:VariableOrders"]],
            ["NAME:DesignDefinitionParameters", ["NAME:VariableOrders"]],
            ["NAME:MaterialDefinitionParameters", ["NAME:VariableOrders"]],
            "DefReferenceCSID:=", 1,
            "MapInstanceParameters:=", "DesignVariable",
            "UniqueDefinitionIdentifier:=", "c0cbeca3-60a5-4c2b-91f5-5871ba115f42",
            "OriginFilePath:=", "",
            "IsLocal:=", False,
            "ChecksumString:=", "",
            "ChecksumHistory:=", [],
            "VersionHistory:=", [],
            [
                "NAME:NativeComponentDefinitionProvider",
                "Type:=", "Fan",
                "Unit:=", "mm",
                "Version:=", 0,
                "ModelAs:=", "2D",
                "Shape:=", "Circular",
                "MovePlane:=", "XY",
                "Radius:=", "6mm",
                "HubRadius:=", "0mm",
                "CaseSide:=", True,
                "FlowDirChoice:=", "NormalNegative",
                "FlowType:=", "FixedVolumetric",
                "SwirlType:=", "Magnitude",
                "FailedFan:=", False,
                ["NAME:DimUnits", "m3_per_s", "n_per_meter_sq"],
                "X:=", ["0", "0.01"],
                "Y:=", ["30", "0"],
                [
                    "NAME:Pressure Loss Curve",
                    ["NAME:DimUnits", "m_per_sec", "n_per_meter_sq"],
                    "X:=", ["0", "1", "2", "3"],
                    "Y:=", ["1", "10", "100", "0"]
                ],
                "IntakeTemp:=", "20cel",
                "Volumetric:=", "4ltr_per_min",
                "Swirl:=", "0",
                "OperatingRPM:=", "0",
                "LayerName:=", "1"
            ],
            ["NAME:InstanceParameters", "GeometryParameters:=", "", "MaterialParameters:=", "", "DesignParameters:=", ""]
        ])
    oEditor = oDesign.SetActiveEditor("3D Modeler")
    oEditor.Move(
        [
            "NAME:Selections",
            "Selections:=", "Fan1_1",
            "NewPartsModelFlag:=", "Model"
        ],
        [
            "NAME:TranslateParameters",
            "TranslateVectorX:=", f"{fan_x}mm",
            "TranslateVectorY:=", f"{fan_y}mm",
            "TranslateVectorZ:=", f"{fan_z}mm"
        ])

    # Opening 경계조건
    oModule = oDesign.GetModule("BoundarySetup")
    oModule.AssignOpeningBoundary(
        [
            "NAME:Opening1",
            "Faces:=", [opening_face.id],
            "Temperature:=", "AmbientTemp",
            "External Rad. Temperature:=", "AmbientRadTemp",
            "Inlet Type:=", "Pressure",
            "Total Pressure:=", "AmbientPressure",
            "No Reverse Flow:=", False
        ])

    # 발열 경계조건
    oModule.AssignBlockBoundary(
        [
            "NAME:Block1",
            "Objects:=", ["source1","source9","source10","source11","source12","source13","source14","source15","source16","source17","source18"],
            "Block Type:=", "Solid",
            "Use External Conditions:=", False,
            "Use Total Power:=", True,
            "Total Power:=", "22.607W"
        ])
    oModule.AssignBlockBoundary(
        [
            "NAME:Block2",
            "Objects:=", ["source2","source3","source4","source5","source6","source7","source19"],
            "Block Type:=", "Solid",
            "Use External Conditions:=", False,
            "Use Total Power:=", True,
            "Total Power:=", "38.468W"
        ])
    oModule.AssignBlockBoundary(
        [
            "NAME:Block3",
            "Objects:=", ["source8"],
            "Block Type:=", "Solid",
            "Use External Conditions:=", False,
            "Use Total Power:=", True,
            "Total Power:=", "46.871W"
        ])

    # SubRegion 생성
    oEditor.CreateSubRegion(
        [
            "NAME:SubRegionParameters",
            "+XPaddingType:=", "Percentage Offset", "+XPadding:=", "0",
            "-XPaddingType:=", "Percentage Offset", "-XPadding:=", "0",
            "+YPaddingType:=", "Percentage Offset", "+YPadding:=", "0",
            "-YPaddingType:=", "Percentage Offset", "-YPadding:=", "0",
            "+ZPaddingType:=", "Percentage Offset", "+ZPadding:=", "0",
            "-ZPaddingType:=", "Percentage Offset", "-ZPadding:=", "0",
            ["NAME:BoxForVirtualObjects", ["NAME:LowPoint", 1, 1, 1], ["NAME:HighPoint", -1, -1, -1]],
            ["NAME:SubRegionPartNames", "PAO_Separate1"],
            ["NAME:SubRegionSubmodelNames"]
        ],
        [
            "NAME:Attributes",
            "Name:=", "SubRegion",
            "Flags:=", "NonModel#Wireframe#",
            "Color:=", "(143 175 143)",
            "Transparency:=", 0,
            "PartCoordinateSystem:=", "Global",
            "UDMId:=", "",
            "MaterialValue:=", "\"air\"",
            "SurfaceMaterialValue:=", "\"\"",
            "SolveInside:=", True,
            "ShellElement:=", False,
            "ShellElementThickness:=", "nan ",
            "ReferenceTemperature:=", "nan ",
            "IsMaterialEditable:=", True,
            "IsSurfaceMaterialEditable:=", True,
            "UseMaterialAppearance:=", False,
            "IsLightweight:=", False
        ])

    # 메시 설정
    oModule = oDesign.GetModule("MeshRegion")
    oModule.AssignMeshRegion(
        [
            "NAME:MeshRegion1",
            "Enable:=", True,
            "MeshMethod:=", "MesherHD",
            "UserSpecifiedSettings:=", True,
            "MaxElementSizeX:=", "2mm",
            "MaxElementSizeY:=", "1mm",
            "MaxElementSizeZ:=", "1mm",
            "MinElementsInGap:=", "3",
            "MinElementsOnEdge:=", "2",
            "MaxSizeRatio:=", "2",
            "NoOGrids:=", True,
            "EnableMLM:=", True,
            "EnforeMLMType:=", "3D",
            "MaxLevels:=", "0",
            "BufferLayers:=", "0",
            "UniformMeshParametersType:=", "XYZ Max Sizes",
            "StairStepMeshing:=", False,
            "2DMLMType:=", "2DMLM_None",
            "MinGapX:=", "0.1mm",
            "MinGapY:=", "0.1mm",
            "MinGapZ:=", "0.1mm",
            "Objects:=", ["SubRegion"],
            "ProximitySizeFunction:=", True,
            "CurvatureSizeFunction:=", True,
            "EnableTransition:=", False,
            "OptimizePCBMesh:=", True,
            "Enable2DCutCell:=", False,
            "EnforceCutCellMeshing:=", False,
            "Enforce2dot5DCutCell:=", False
        ],
        [
            "NAME:Geometrical Attributes",
            "MinSlackX:=", "0mm", "MaxSlackX:=", "0mm",
            "MinSlackY:=", "0mm", "MaxSlackY:=", "0mm",
            "MinSlackZ:=", "0mm", "MaxSlackZ:=", "0mm",
            "MinBboxX:=", "0mm", "MaxBboxX:=", "0mm",
            "MinBboxY:=", "0mm", "MaxBboxY:=", "0mm",
            "MinBboxZ:=", "0mm", "MaxBboxZ:=", "0mm"
        ])
    oModule.EditGlobalMeshRegion(
        [
            "NAME:Settings",
            "MeshMethod:=", "MesherHD",
            "UserSpecifiedSettings:=", True,
            "ComputeGap:=", True,
            "MaxElementSizeX:=", "2mm",
            "MaxElementSizeY:=", "2mm",
            "MaxElementSizeZ:=", "2mm",
            "MinElementsInGap:=", "3",
            "MinElementsOnEdge:=", "2",
            "MaxSizeRatio:=", "2",
            "NoOGrids:=", True,
            "EnableMLM:=", True,
            "EnforeMLMType:=", "3D",
            "MaxLevels:=", "0",
            "BufferLayers:=", "0",
            "UniformMeshParametersType:=", "XYZ Max Sizes",
            "StairStepMeshing:=", False,
            "MinGapX:=", "0.1mm",
            "MinGapY:=", "0.1mm",
            "MinGapZ:=", "0.1mm",
            "Objects:=", ["Region"],
            "StairStepSliderMeshing:=", False,
            "FacetLevel:=", "3",
            "ProximitySizeFunction:=", True,
            "CurvatureSizeFunction:=", True,
            "EnableTransition:=", False,
            "OptimizePCBMesh:=", True,
            "Enable2DCutCell:=", False,
            "EnforceCutCellMeshing:=", False,
            "Enforce2dot5DCutCell:=", False
        ])

    # Priority List
    oEditor.UpdatePriorityList(
        [
            "NAME:UpdatePriorityListData",
            [
                "NAME:PriorityListParameters",
                "EntityType:=", "Object",
                "EntityList:=", "PAO_Separate1",
                "PriorityNumber:=", 2,
                "PriorityListType:=", "3D"
            ],
            [
                "NAME:PriorityListParameters",
                "EntityType:=", "Object",
                "EntityList:=", "plate, plate_base",
                "PriorityNumber:=", 3,
                "PriorityListType:=", "3D"
            ],
        ])

    # Unite
    oEditor.Unite(
        [
            "NAME:Selections",
            "Selections:=", "plate, plate_base"
        ],
        [
            "NAME:UniteParameters",
            "KeepOriginals:=", False,
            "TurnOnNBodyBoolean:=", True
        ])

    # Solve Setup
    oModule = oDesign.GetModule("AnalysisSetup")
    oModule.InsertSetup("IcepakSteadyState",
        [
            "NAME:Setup1",
            "Enabled:=", True,
            ["NAME:MeshLink", "ImportMesh:=", False],
            "Flow Regime:=", "Laminar",
            "Include Temperature:=", True,
            "Include Flow:=", True,
            "Include Gravity:=", False,
            "Include Solar:=", False,
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
            "IsEnabled:=", False,
            "Radiation Model:=", "Off",
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
            "Secondary Gradient:=", False,
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
            "Maximum Cycles:=", "30",
            "Linear Solver Stabilization - Pressure:=", "None",
            "Linear Solver Stabilization - Temperature:=", "None",
            "Linear Solver Stabilization - Joule Heating:=", "None",
            "Coupled pressure-velocity formulation:=", False,
            "Turn off auto-pairing for grid interface creation:=", False,
            "2D Profile Interpolation Method:=", "Inverse Distance Weighted",
            "Frozen Flow Simulation:=", False,
            "TEC Coupling:=", False,
            "Sequential Solve of Flow and Energy Equations:=", False,
            "Convergence Criteria - Max Iterations:=", 1000
        ])

    # 저장 후 해석 실행
    oProject.Save()
    oDesign.AnalyzeAll()
    print(f"[{idx}] 해석 완료")

    # 결과 CSV 저장 (idx별 동적 경로)
    result_path = rf"E:\Thermal_Anlaysis\Results\result_{idx:03d}.csv"
    os.makedirs(r"E:\Thermal_Anlaysis\Results", exist_ok=True)

    oModule = oDesign.GetModule("Solutions")
    oModule.EditFieldsSummarySetting(
        [
            "SolutionName:=", "Setup1 : SteadyState",
            "Variation:=", "Nominal",
            "Calculation:=", ["Object","Volume","source1","Temperature","","Default","All","Nominal",True],
            "Calculation:=", ["Object","Volume","source2","Temperature","","Default","All","Nominal",True],
            "Calculation:=", ["Object","Volume","source3","Temperature","","Default","All","Nominal",True],
            "Calculation:=", ["Object","Volume","source4","Temperature","","Default","All","Nominal",True],
            "Calculation:=", ["Object","Volume","source5","Temperature","","Default","All","Nominal",True],
            "Calculation:=", ["Object","Volume","source6","Temperature","","Default","All","Nominal",True],
            "Calculation:=", ["Object","Volume","source7","Temperature","","Default","All","Nominal",True],
            "Calculation:=", ["Object","Volume","source8","Temperature","","Default","All","Nominal",True],
            "Calculation:=", ["Object","Volume","source9","Temperature","","Default","All","Nominal",True],
            "Calculation:=", ["Object","Volume","source10","Temperature","","Default","All","Nominal",True],
            "Calculation:=", ["Object","Volume","source11","Temperature","","Default","All","Nominal",True],
            "Calculation:=", ["Object","Volume","source12","Temperature","","Default","All","Nominal",True],
            "Calculation:=", ["Object","Volume","source13","Temperature","","Default","All","Nominal",True],
            "Calculation:=", ["Object","Volume","source14","Temperature","","Default","All","Nominal",True],
            "Calculation:=", ["Object","Volume","source15","Temperature","","Default","All","Nominal",True],
            "Calculation:=", ["Object","Volume","source16","Temperature","","Default","All","Nominal",True],
            "Calculation:=", ["Object","Volume","source17","Temperature","","Default","All","Nominal",True],
            "Calculation:=", ["Object","Volume","source18","Temperature","","Default","All","Nominal",True],
            "Calculation:=", ["Object","Volume","source19","Temperature","","Default","All","Nominal",True],
            "Calculation:=", ["Object","Surface","Fan1_Passage","Pressure","0.00,0.00,1.00","Default","Reduced","Nominal",False]
        ])
    oModule.ExportFieldsSummary(
        [
            "SolutionName:=", "Setup1 : SteadyState",
            "DesignVariationKey:=", "Nominal",
            "ExportFileName:=", result_path,
            "IntrinsicValue:=", ""
        ])
    print(f"[{idx}] CSV 저장 완료: {result_path}")

    # ── 핀뱅크 입구 레인별 속도 측정 시트 30개 생성 (NonModel, 피치 6.5mm = 틈4 + 핀2.5) ──
    x_pos = -168.499999983333
    y_start = 19.0000000166667
    z_start = 0.500000016666667
    width = -4.00000003333333
    height = 7.49999996666666

    for i in range(30):
        y = y_start - (6.5 * i)

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
    print(f"[{idx}] 측정 시트 30개 생성 완료 (V_inlet_01 ~ V_inlet_30)")

    # ── 30개 시트 Speed 요약 export (반드시 온도/차압 export 뒤에 실행 —
    #    EditFieldsSummarySetting은 설정을 통째로 교체하므로 순서 변경 금지) ──
    speed_path = rf"E:\Thermal_Anlaysis\Results\speed_{idx:03d}.csv"

    speed_setting = [
        "SolutionName:=", "Setup1 : SteadyState",
        "Variation:=", "Nominal",
    ]
    for i in range(30):
        speed_setting += [
            "Calculation:=",
            ["Object", "Surface", f"V_inlet_{i+1:02d}", "Speed", "", "Default", "All", "Nominal", True],
        ]

    oModule.EditFieldsSummarySetting(speed_setting)
    oModule.ExportFieldsSummary(
        [
            "SolutionName:=", "Setup1 : SteadyState",
            "DesignVariationKey:=", "Nominal",
            "ExportFileName:=", speed_path,
            "IntrinsicValue:=", ""
        ])
    print(f"[{idx}] 속도 CSV 저장 완료: {speed_path}")

    return ipk, result_path, speed_path
