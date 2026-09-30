"""SolidWorks 자동화 래퍼 (pywin32).

모든 길이 인자/반환값은 mm 단위다. 내부에서 미터로 변환한다.
"""
import os

import pythoncom
import win32com.client

DOC_TYPES = {".sldprt": 1, ".sldasm": 2, ".slddrw": 3}

SW_OPEN_SILENT = 1
SW_SAVEAS_CURRENT_VERSION = 0
SW_SAVEAS_SILENT = 1
SW_CUSTOM_INFO_TEXT = 30
SW_CUSTOM_PROPERTY_REPLACE = 2


def _byref_int():
    """SolidWorks API의 ByRef long 인자 (errors, warnings 등)."""
    return win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)


def _call(obj, name, *args):
    """pywin32가 인자 없는 메서드를 속성으로 노출하는 문제를 처리한다."""
    attr = getattr(obj, name)
    return attr(*args) if callable(attr) else attr


def connect(visible=True):
    sw = win32com.client.Dispatch("SldWorks.Application")
    sw.Visible = visible
    return sw


def open_doc(sw, path):
    path = os.path.abspath(path)
    ext = os.path.splitext(path)[1].lower()
    if ext not in DOC_TYPES:
        raise ValueError(f"지원하지 않는 확장자: {ext}")
    errors, warnings = _byref_int(), _byref_int()
    model = sw.OpenDoc6(path, DOC_TYPES[ext], SW_OPEN_SILENT, "", errors, warnings)
    if model is None:
        raise RuntimeError(f"열기 실패: {path} (errors={errors.value})")
    return model


def _get_dim(model, name):
    dim = model.Parameter(name)
    if dim is None:
        raise KeyError(f"치수를 찾을 수 없음: {name} (형식: 'D1@Sketch1')")
    return dim


def get_dimension_mm(model, name):
    return _get_dim(model, name).SystemValue * 1000.0


def set_dimension_mm(model, name, value_mm):
    _get_dim(model, name).SystemValue = value_mm / 1000.0
    _call(model, "EditRebuild3")


def set_custom_property(model, name, value):
    mgr = model.Extension.CustomPropertyManager("")
    mgr.Add3(name, SW_CUSTOM_INFO_TEXT, str(value), SW_CUSTOM_PROPERTY_REPLACE)


def get_mass_kg(model):
    return model.Extension.CreateMassProperty().Mass


def save_as(model, path):
    """확장자로 형식 결정: .sldprt, .step, .igs, .stl, .pdf, .dxf 등"""
    path = os.path.abspath(path)
    errors, warnings = _byref_int(), _byref_int()
    export_data = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
    ok = model.Extension.SaveAs(
        path, SW_SAVEAS_CURRENT_VERSION, SW_SAVEAS_SILENT, export_data, errors, warnings
    )
    if not ok:
        raise RuntimeError(f"저장 실패: {path} (errors={errors.value})")


def close_doc(sw, model):
    sw.CloseDoc(_call(model, "GetTitle"))
