# %%
from ansys.aedt.core import Desktop, Icepak
from ansys.aedt.core.generic.settings import settings
import os, shutil

# %%
from ansys.aedt.core import Desktop, Icepak
import os, shutil

proj_path = r"E:\Thermal_Anlaysis\Aedt\thermal_test"

# AEDT 한 번만 켜기
desktop = Desktop(version="2025.1", non_graphical=False, new_desktop=True)
print("AEDT 켜짐")

ipk = None   # 아직 프로젝트 없음

# %%
# 기존 프로젝트가 열려있으면 그것만 닫기 (AEDT는 유지)
if ipk is not None:
    oDesktop = ipk.odesktop
    proj_name = ipk.project_name
    ipk = None
    oDesktop.CloseProject(proj_name)
    print("기존 프로젝트 닫음")

# 디스크 파일도 삭제 (용량 관리)
if os.path.exists(proj_path + ".aedt"):
    os.remove(proj_path + ".aedt")
if os.path.exists(proj_path + ".aedtresults"):
    shutil.rmtree(proj_path + ".aedtresults")

# 새 Icepak 프로젝트 생성
ipk = Icepak(project=proj_path, new_desktop=False)
print("새 프로젝트 생성:", ipk.project_name)

# %%
step_path = r"E:\Thermal_Anlaysis\Step\test.STEP"
ipk.modeler.import_3d_cad(step_path)
print("임포트 완료:", step_path)

# %%
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

oDesign.SetDesignSettings(
	[
		"NAME:Design Settings Data",
		"Perform Minimal validation:=", False,
		"Default Fluid Material:=", "air",
		"Default Solid Material:=", "Al-Extruded",
		"Default Surface Material:=", "Steel-oxidised-surface",
		"AmbientTemperature:="	, "25cel",
		"AmbientPressure:="	, "0n_per_meter_sq",
		"AmbientRadiationTemperature:=", "20cel",
		"Gravity Vector CS ID:=", 1,
		"Gravity Vector Axis:="	, "Z",
		"Positive:="		, False,
		"ExportOnSimulationComplete:=", False,
		"ExportDirectory:="	, "",
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
oEditor.ChangeProperty(
	[
		"NAME:AllTabs",
		[
			"NAME:Geometry3DAttributeTab",
			[
				"NAME:PropServers", 
				"ttpkp_attribute151", 
				"ttpkp_attribute104"
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
		"Tool Parts:="		, "ttpkp_attribute104,ttpkp_attribute151"
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
base_x = -191.1
step = 20.5
n_boxes = 19

for i in range(n_boxes):
    x_pos = base_x + i * step
    box_name = f"source{i + 1}"  # source1, source2, ..., source15

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
# %%
##오프닝, 팬 원 만들기 ##
oEditor.CreateCircle(
	[
		"NAME:CircleParameters",
		"IsCovered:="		, True,
		"XCenter:="		, "-26.75mm",
		"YCenter:="		, "195mm",
		"ZCenter:="		, "18.49999998mm",
		"Radius:="		, "6mm",
		"WhichAxis:="		, "Z",
		"NumSegments:="		, "0"
	], 
	[
		"NAME:Attributes",
		"Name:="		, "Circle1",
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
oEditor.CreateCircle(
	[
		"NAME:CircleParameters",
		"IsCovered:="		, True,
		"XCenter:="		, "26.75mm",
		"YCenter:="		, "195mm",
		"ZCenter:="		, "18.49999998mm",
		"Radius:="		, "6mm",
		"WhichAxis:="		, "Z",
		"NumSegments:="		, "0"
	], 
	[
		"NAME:Attributes",
		"Name:="		, "Circle2",
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
# %%
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
			"IntakeTemp:="		, "AmbientTemp",
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
		"TranslateVectorX:="	, "-26.75mm",
		"TranslateVectorY:="	, "195mm",
		"TranslateVectorZ:="	, "18.49999998mm"
	])
oModule = oDesign.GetModule("BoundarySetup")
oModule.AssignOpeningBoundary(
	[
		"NAME:Opening1",
		"Objects:="		, ["Circle2"],
		"Temperature:="		, "AmbientTemp",
		"External Rad. Temperature:=", "AmbientRadTemp",
		"Inlet Type:="		, "Pressure",
		"Total Pressure:="	, "AmbientPressure",
		"No Reverse Flow:="	, False
	])


# %%
oModule.AssignBlockBoundary(
	[
		"NAME:Block1",
		"Objects:="		, ["source1","source9","source10","source11","source12","source13","source14","source15","source16","source17","source18"],
		"Block Type:="		, "Solid",
		"Use External Conditions:=", False,
		"Use Total Power:="	, True,
		"Total Power:="		, "22.607W"
	])
oModule.AssignBlockBoundary(
	[
		"NAME:Block2",
		"Objects:="		, ["source2","source3","source4","source5","source6","source7","source19"],
		"Block Type:="		, "Solid",
		"Use External Conditions:=", False,
		"Use Total Power:="	, True,
		"Total Power:="		, "38.468W"
	])
oModule.AssignBlockBoundary(
	[
		"NAME:Block3",
		"Objects:="		, ["source8"],
		"Block Type:="		, "Solid",
		"Use External Conditions:=", False,
		"Use Total Power:="	, True,
		"Total Power:="		, "46.871W"
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
		"MaxElementSizeX:="	, "2mm",
		"MaxElementSizeY:="	, "1mm",
		"MaxElementSizeZ:="	, "1mm",
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
		"MaxElementSizeX:="	, "2mm",
		"MaxElementSizeY:="	, "2mm",
		"MaxElementSizeZ:="	, "2mm",
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
			"EntityList:="		, "ttpkp_attribute151, ttpkp_attribute104",
			"PriorityNumber:="	, 3,
			"PriorityListType:="	, "3D"
		],
        
	])
# %%
oEditor.Unite(
	[
		"NAME:Selections",
		"Selections:="		, "ttpkp_attribute104,ttpkp_attribute151"
	], 
	[
		"NAME:UniteParameters",
		"KeepOriginals:="	, False,
		"TurnOnNBodyBoolean:="	, True
	])

# %%
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
oDesktop.RestoreWindow()
oProject = oDesktop.SetActiveProject("thermal_test")
oProject.Save()
oDesign = oProject.SetActiveDesign("Icepak_MMK")
oDesign.AnalyzeAll()

# %%
###후처리####
oModule = oDesign.GetModule("Solutions")
oModule.EditFieldsSummarySetting(
	[
		"SolutionName:="	, "Setup1 : SteadyState",
		"Variation:="		, "Nominal",
		"Calculation:="		, ["Object","Volume","source1","Temperature","","Default","All","Nominal",True],
		"Calculation:="		, ["Object","Volume","source10","Temperature","","Default","All","Nominal",True],
		"Calculation:="		, ["Object","Volume","source11","Temperature","","Default","All","Nominal",True],
		"Calculation:="		, ["Object","Volume","source12","Temperature","","Default","All","Nominal",True],
		"Calculation:="		, ["Object","Volume","source13","Temperature","","Default","All","Nominal",True],
		"Calculation:="		, ["Object","Volume","source14","Temperature","","Default","All","Nominal",True],
		"Calculation:="		, ["Object","Volume","source15","Temperature","","Default","All","Nominal",True],
		"Calculation:="		, ["Object","Volume","source16","Temperature","","Default","All","Nominal",True],
		"Calculation:="		, ["Object","Volume","source17","Temperature","","Default","All","Nominal",True],
		"Calculation:="		, ["Object","Volume","source18","Temperature","","Default","All","Nominal",True],
		"Calculation:="		, ["Object","Volume","source19","Temperature","","Default","All","Nominal",True],
		"Calculation:="		, ["Object","Volume","source2","Temperature","","Default","All","Nominal",True],
		"Calculation:="		, ["Object","Volume","source3","Temperature","","Default","All","Nominal",True],
		"Calculation:="		, ["Object","Volume","source4","Temperature","","Default","All","Nominal",True],
		"Calculation:="		, ["Object","Volume","source5","Temperature","","Default","All","Nominal",True],
		"Calculation:="		, ["Object","Volume","source6","Temperature","","Default","All","Nominal",True],
		"Calculation:="		, ["Object","Volume","source7","Temperature","","Default","All","Nominal",True],
		"Calculation:="		, ["Object","Volume","source8","Temperature","","Default","All","Nominal",True],
		"Calculation:="		, ["Object","Volume","source9","Temperature","","Default","All","Nominal",True],
		"Calculation:="		, ["Object","Surface","Fan1_Passage","Pressure","0.00,0.00,1.00","Default","Reduced","Nominal",False]
	])
oModule.ExportFieldsSummary(
	[
		"SolutionName:="	, "Setup1 : SteadyState",
		"DesignVariationKey:="	, "Nominal",
		"ExportFileName:="	, "E:\\Thermal_Anlaysis\\export_aedt\\summaryReport1.csv",
		"IntrinsicValue:="	, ""
	])
