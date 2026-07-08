import win32com.client
import pythoncom
import os

# 경로 상수
PART_PATH = r"E:\Thermal_Anlaysis\Solidworks\plate_base.SLDPRT"
ASM_PATH  = r"E:\Thermal_Anlaysis\Solidworks\flowpath.SLDASM"

def connect_sw():
    """SW 연결 및 어셈블리 열기"""
    pythoncom.CoInitialize()
    app = win32com.client.Dispatch("SldWorks.Application")
    app.Visible = True
    errors   = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    warnings = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    swDocASSEMBLY = 2
    model = app.OpenDoc6(ASM_PATH, swDocASSEMBLY, 1, "", errors, warnings)
    print("SW 연결 완료:", model.GetTitle)
    return app, errors, warnings

def update_sw(app, errors, warnings, angle, flow_thickness):
    """글로벌 변수 업데이트 및 리빌드"""
    part  = app.ActivateDoc3(PART_PATH, False, 0, errors)
    eqMgr = part.GetEquationMgr
    def set_value(name, value):
        dispid = eqMgr._oleobj_.GetIDsOfNames("Equation")
        for i in range(eqMgr.GetCount):
            if eqMgr.Equation(i).split("=")[0].strip() == '"%s"' % name:
                eqMgr._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT,
                                      False, i, '"%s" = %s' % (name, value))
    set_value("각도", angle)
    set_value("유로두께", flow_thickness)
    part.EditRebuild3
    part.Save3(1, errors, warnings)
    asm = app.ActivateDoc3(ASM_PATH, False, 0, errors)
    asm.ForceRebuild3(False)
    asm.Save3(1, errors, warnings)
    print("SW 업데이트 완료")

def export_step(app, errors, angle, flow_thickness):
    """STEP 파일 저장 후 경로 반환"""
    os.makedirs(r"E:\Thermal_Anlaysis\Step", exist_ok=True)
    step_path = r"E:\Thermal_Anlaysis\Step\flowpath_a%.1f_t%.1f.STEP" % (angle, flow_thickness)
    asm = app.ActivateDoc3(ASM_PATH, False, 0, errors)
    asm.SaveAs3(step_path, 0, 0)
    print("STEP 저장 완료:", step_path)
    return step_path
