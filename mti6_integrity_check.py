from pathlib import Path
import pandas as pd
import re


# ============================================================
# 1. 기본 설정
# ============================================================

DATA_DIR = Path("industry_data")

EXPECTED_FILE_COUNT = 13
EXPECTED_TOTAL_ITEMS = 1291


print("=" * 100)
print("KITA MTI6 MASTER - INTEGRITY CHECK")
print("=" * 100)


# ============================================================
# 2. 대상 파일 자동 탐색
# ============================================================

files = sorted(DATA_DIR.glob("KITA_MTI6_*.XLS"))

print()
print("[1] 파일 탐색")
print("-" * 100)

for file in files:
    print(file.name)

print()
print(f"발견된 파일 수 : {len(files)}")


if len(files) != EXPECTED_FILE_COUNT:
    print()
    print("WARNING")
    print(
        f"예상 파일 수는 {EXPECTED_FILE_COUNT}개인데 "
        f"현재 {len(files)}개가 발견되었습니다."
    )
else:
    print("파일 수 검증    : PASS")


# ============================================================
# 3. 숫자 정리 함수
# ============================================================

def clean_code(value):
    """
    Excel에서 읽은 MTI 코드를 6자리 문자열로 정리
    예: 16400 -> 016400
    """

    if pd.isna(value):
        return None

    text = str(value).strip()

    # 831110.0 같은 형태 처리
    text = re.sub(r"\.0$", "", text)

    # 숫자가 아닌 문자 제거
    text = re.sub(r"[^0-9]", "", text)

    if not text:
        return None

    return text.zfill(6)


# ============================================================
# 4. 각 XLS 파일에서 MTI6 데이터 추출
#
# 이전 테스트에서 확인된 K-stat 구조:
# header row = 2
# code column = 1
# item name column = 2
# ============================================================

all_frames = []
file_summary = []


for file in files:

    print()
    print("-" * 100)
    print("읽는 파일:", file.name)

    try:
        raw = pd.read_excel(
            file,
            header=None
        )

    except Exception as e:
        print("파일 읽기 실패:", e)
        continue


    # --------------------------------------------------------
    # MTI 코드가 존재하는 실제 데이터 행 탐색
    # --------------------------------------------------------

    rows = []

    for idx in range(len(raw)):

        code_raw = raw.iloc[idx, 1] if raw.shape[1] > 1 else None
        name_raw = raw.iloc[idx, 2] if raw.shape[1] > 2 else None

        code = clean_code(code_raw)

        if code is None:
            continue

        # MTI6만 허용
        if len(code) != 6:
            continue

        # 품목명이 없으면 제외
        if pd.isna(name_raw):
            continue

        name = str(name_raw).strip()

        if not name:
            continue

        rows.append(
            {
                "MTI6코드": code,
                "품목명": name,
                "원본파일": file.name,
                "원본행": idx + 1,
            }
        )


    temp = pd.DataFrame(rows)

    print(f"추출 행 수      : {len(temp)}")
    print(f"고유 MTI6 코드  : {temp['MTI6코드'].nunique() if not temp.empty else 0}")

    file_summary.append(
        {
            "파일명": file.name,
            "추출행수": len(temp),
            "고유코드수": (
                temp["MTI6코드"].nunique()
                if not temp.empty
                else 0
            ),
        }
    )

    if not temp.empty:
        all_frames.append(temp)


# ============================================================
# 5. 전체 병합
# ============================================================

print()
print("=" * 100)
print("[2] 전체 병합")
print("=" * 100)


if not all_frames:
    print("추출된 데이터가 없습니다.")
    raise SystemExit


master = pd.concat(
    all_frames,
    ignore_index=True
)


total_rows = len(master)
unique_codes = master["MTI6코드"].nunique()
duplicate_rows = master.duplicated(
    subset=["MTI6코드"],
    keep=False
).sum()

missing_names = master["품목명"].isna().sum()
blank_names = (
    master["품목명"]
    .astype(str)
    .str.strip()
    .eq("")
    .sum()
)


print(f"전체 추출 행 수     : {total_rows:,}")
print(f"고유 MTI6 코드 수   : {unique_codes:,}")
print(f"중복 관련 행 수     : {duplicate_rows:,}")
print(f"품목명 결측 수      : {missing_names:,}")
print(f"품목명 공백 수      : {blank_names:,}")


# ============================================================
# 6. 중복 상세 확인
# ============================================================

duplicates = (
    master[
        master.duplicated(
            subset=["MTI6코드"],
            keep=False
        )
    ]
    .sort_values(
        ["MTI6코드", "원본파일"]
    )
)


print()
print("=" * 100)
print("[3] 중복 검증")
print("=" * 100)


if duplicates.empty:

    print("중복 MTI6 코드 없음 : PASS")

else:

    print(
        f"중복 MTI6 관련 행이 "
        f"{len(duplicates):,}개 발견되었습니다."
    )

    print()
    print(
        duplicates[
            [
                "MTI6코드",
                "품목명",
                "원본파일",
                "원본행",
            ]
        ]
        .head(50)
        .to_string(index=False)
    )


# ============================================================
# 7. 파일별 페이지 검증
# ============================================================

summary = pd.DataFrame(file_summary)


print()
print("=" * 100)
print("[4] 페이지별 추출 결과")
print("=" * 100)

print(
    summary.to_string(
        index=False
    )
)


# ============================================================
# 8. 최종 판정
# ============================================================

file_count_ok = (
    len(files) == EXPECTED_FILE_COUNT
)

total_rows_ok = (
    total_rows == EXPECTED_TOTAL_ITEMS
)

unique_codes_ok = (
    unique_codes == EXPECTED_TOTAL_ITEMS
)

duplicates_ok = (
    duplicate_rows == 0
)

names_ok = (
    missing_names == 0
    and blank_names == 0
)


print()
print("=" * 100)
print("[5] FINAL INTEGRITY RESULT")
print("=" * 100)

print(
    f"13개 파일 존재       : "
    f"{'PASS' if file_count_ok else 'FAIL'}"
)

print(
    f"전체 1,291행         : "
    f"{'PASS' if total_rows_ok else 'FAIL'} "
    f"({total_rows:,})"
)

print(
    f"고유 MTI6 1,291개    : "
    f"{'PASS' if unique_codes_ok else 'FAIL'} "
    f"({unique_codes:,})"
)

print(
    f"MTI6 코드 중복 없음  : "
    f"{'PASS' if duplicates_ok else 'FAIL'}"
)

print(
    f"품목명 결측 없음     : "
    f"{'PASS' if names_ok else 'FAIL'}"
)


all_pass = all(
    [
        file_count_ok,
        total_rows_ok,
        unique_codes_ok,
        duplicates_ok,
        names_ok,
    ]
)


print()
print("=" * 100)

if all_pass:

    print(">>> INTEGRITY CHECK : ALL PASS <<<")
    print(">>> KITA MTI6 MASTER 1,291개 확보 완료 <<<")

else:

    print(">>> INTEGRITY CHECK : REVIEW REQUIRED <<<")
    print(">>> 위 FAIL 항목을 확인하세요. <<<")

print("=" * 100)


# ============================================================
# 9. 검증용 CSV 저장
# ============================================================

master_sorted = (
    master
    .sort_values("MTI6코드")
    .reset_index(drop=True)
)


master_sorted.to_csv(
    "mti6_master_1291.csv",
    index=False,
    encoding="utf-8-sig"
)


summary.to_csv(
    "mti6_integrity_page_summary.csv",
    index=False,
    encoding="utf-8-sig"
)


if not duplicates.empty:

    duplicates.to_csv(
        "mti6_integrity_duplicates.csv",
        index=False,
        encoding="utf-8-sig"
    )


print()
print("CSV 저장 완료")
print("- mti6_master_1291.csv")
print("- mti6_integrity_page_summary.csv")

if not duplicates.empty:
    print("- mti6_integrity_duplicates.csv")

print()
print("=" * 100)
print("CHECK COMPLETE")
print("=" * 100)