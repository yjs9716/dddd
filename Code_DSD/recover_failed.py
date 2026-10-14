"""
OLHD 실패 점 되살리기 — 해석은 끝났는데 결과 파싱에서 실패한 점을, 다시 해석하지 않고 남은 결과 CSV 로 기록한다.

언제 쓰나
  예: 유로 측정면 하나가 '-nan(ind)' 로 나와 파싱이 실패한 점 (result_parser.py 가 이제는 메우지만,
  그렇게 고치기 전에 실패로 기록된 점). Icepak 해석 자체가 실패한 점은 CSV 가 없어 살릴 수 없다.

하는 일 (실패 기록 1건마다)
  1) SolidWorks 에 그 점의 설계값을 넣어 중량용 알루미늄 질량·부피를 다시 구한다 (해석은 안 함)
  2) 결과 CSV 를 result_parser.extract_and_save 로 파싱한다
  3) 성공하면 results_v6.csv 에 기록하고(idx = 지금까지 성공 건수), CSV 를 result_<idx>.csv 로 복사,
     failed_v6.csv 에서 그 행을 지운다
  성공 건수 + 실패 건수가 그대로라 main.py 가 다음에 돌릴 실험점은 바뀌지 않는다.

사용
  python recover_failed.py                  → 실패 기록 중 result_file 칸에 결과 CSV 가 남아 있는 점을 모두 시도
  python recover_failed.py <결과 CSV 경로>  → result_file 칸이 빈 실패 기록이 1건일 때, 그 점에 이 CSV 를 쓴다
                                              (result_file 칸이 생기기 전에 실패한 점 — 다음 실험이 같은 번호로
                                               덮어쓰기 전에 CSV 를 다른 이름으로 복사해 두고 그 경로를 줄 것)

⚠ main.py 와 동시에 실행하지 말 것 (같은 SolidWorks 사용, 같은 결과 파일 갱신).
"""
import os
import shutil
import sys

import ML
from params import CANDIDATES, to_dict
from paths import FAILED_PATH, icepak_result_path
from result_parser import extract_and_save
from Solidworks import connect_sw, update_sw


def main(path_arg=None):
    failed = ML._load_failed()
    failed["result_file"] = failed["result_file"].astype(object)   # 빈칸만 있으면 float 열로 읽힘
    if not len(failed):
        print("실패 기록이 없음 — 할 일 없음")
        return
    if path_arg:
        if not os.path.exists(path_arg):
            raise SystemExit(f"결과 CSV 가 없음: {path_arg}")
        empty = failed.index[failed["result_file"].isna()]
        if len(empty) != 1:
            raise SystemExit(f"result_file 칸이 빈 실패 기록이 {len(empty)}건 — 1건일 때만 경로를 지정할 수 있음.\n"
                             f"  {FAILED_PATH} 를 열어 확인할 것")
        failed.loc[empty[0], "result_file"] = path_arg

    todo = [i for i, f in failed["result_file"].items() if isinstance(f, str) and os.path.exists(f)]
    if not todo:
        print("결과 CSV 가 남아 있는 실패 기록이 없음 — 할 일 없음")
        return

    app, errors, warnings_ = connect_sw()
    recovered = []
    for i in todo:
        row = failed.loc[i]
        params = to_dict(row[CANDIDATES].values.astype(float))
        print(f"\n[복구] {row['result_file']}\n  " + ML._fmt(params))
        try:
            mass, vol = update_sw(app, errors, warnings_, params)
            results = extract_and_save("olhd:복구", params, row["result_file"], mass, vol)
        except Exception as e:
            print(f"  ⚠ 복구 실패 — 실패 기록은 그대로 둠: {e}")
            continue
        idx = ML.current_idx()
        shutil.copy(row["result_file"], icepak_result_path("olhd", idx))
        ML.record("olhd", idx, params, results)
        recovered.append(i)
        print(f"  복구 완료 → results 의 idx {idx}, 결과 CSV 사본 {icepak_result_path('olhd', idx)}")

    ML._write(failed.drop(index=recovered), FAILED_PATH, ML._FAILED_COLUMNS)
    print(f"\n복구 {len(recovered)}건 / 시도 {len(todo)}건. 남은 실패 기록 {len(failed) - len(recovered)}건")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
