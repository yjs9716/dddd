"""산점도 후처리 — '예측' 계열은 선 없이 점만, '실측=예측' 계열은 점 없이 선만.

pptxgenjs는 산점도의 선 굵기·표식을 계열별로 따로 줄 수 없어서, 생성된 차트 XML을
계열 이름 기준으로 고친다.
사용: python fix_charts.py deck.pptx
"""
import re
import sys
import zipfile
import shutil

src = sys.argv[1]
tmp = src + ".tmp"

NO_LINE = "<a:ln><a:noFill/></a:ln>"
NO_MARK = '<c:marker><c:symbol val="none"/></c:marker>'


def fix_ser(m):
    ser = m.group(0)
    name = re.search(r"<c:tx>.*?<c:v>(.*?)</c:v>", ser, re.S)
    name = name.group(1) if name else ""
    if name == "예측":
        ser = re.sub(r"<a:ln\b[^>]*>.*?</a:ln>", NO_LINE, ser, count=1, flags=re.S)
    elif name == "실측=예측":
        ser = re.sub(r"<c:marker>.*?</c:marker>", NO_MARK, ser, count=1, flags=re.S)
    return ser


n_fixed = 0
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if re.match(r"ppt/charts/chart\d+\.xml$", item.filename):
            xml = data.decode("utf-8")
            new = re.sub(r"<c:ser>.*?</c:ser>", fix_ser, xml, flags=re.S)
            if new != xml:
                n_fixed += 1
            data = new.encode("utf-8")
        zout.writestr(item, data)
shutil.move(tmp, src)
print(f"차트 {n_fixed}개 수정")
