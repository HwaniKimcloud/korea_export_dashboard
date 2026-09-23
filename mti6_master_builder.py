from pathlib import Path
import pandas as pd
import re


# ============================================================
# 1. 기본 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "industry_data"

INPUT_FILE = DATA_DIR / "KITA_MTI6_INDUSTRY_EXPORT_DATA.XLS"


# ============================================================
# 2. 파일 존재 확인
# ============================================================

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"파일을 찾을 수 없습니다:\n{INPUT_FILE}"
    )


print()
print("=" * 100)
print("KITA MTI6 MASTER BUILDER")
print("=" * 100)

print("입력 파일:", INPUT_FILE)


# ============================================================
# 3. Excel 읽기
# ============================================================

raw = pd.read_excel(
    INPUT_FILE,
    header=None
)


print()
print("원본 행 수:", len(raw))
print("원본 열 수:", len(raw.columns))


# ============================================================
# 4. 상단 구조 확인
# ============================================================

print()
print("=" * 100)
print("상단 20행")
print("=" * 100)

print(
    raw.head(20).to_string(
        index=True,
        header=True
    )
)


# ============================================================
# 5. MTI 6단위 코드/품목명 후보 탐색
# ============================================================
#
# 목표:
# 831110 | D램
# 831190 | 기타 메모리반도체
# 741310 | 내연기관 승용차(신차)
# ...
#
# 파일 구조가 어떻게 되어 있든,
# 6자리 숫자 코드가 있는 셀을 기준으로 탐색합니다.
# ============================================================

records = []


for row_idx in range(len(raw)):

    for col_idx in range(len(raw.columns)):

        value = raw.iat[row_idx, col_idx]

        if pd.isna(value):
            continue

        text = str(value).strip()

        # 6자리 숫자 코드만 탐색
        if not re.fullmatch(r"\d{6}", text):
            continue

        code = text

        # ----------------------------------------------------
        # 품목명 후보 탐색
        # 보통 코드 오른쪽 셀에 품목명이 위치한다고 가정하되,
        # 오른쪽 1~3칸까지 확인
        # ----------------------------------------------------

        name = None
        name_col = None

        for offset in [1, 2, 3]:

            candidate_col = col_idx + offset

            if candidate_col >= len(raw.columns):
                break

            candidate = raw.iat[
                row_idx,
                candidate_col
            ]

            if pd.isna(candidate):
                continue

            candidate_text = str(candidate).strip()

            if (
                candidate_text == ""
                or
                candidate_text.lower() == "nan"
            ):
                continue

            # 숫자만 있는 값은 품목명으로 보지 않음
            if re.fullmatch(
                r"[-+]?\d+(\.\d+)?",
                candidate_text
            ):
                continue

            name = candidate_text
            name_col = candidate_col
            break


        records.append({
            "MTI6코드": code,
            "품목명": name,
            "행": row_idx,
            "코드열": col_idx,
            "품목명열": name_col
        })


master = pd.DataFrame(records)


# ============================================================
# 6. 중복 제거
# ============================================================

if master.empty:

    print()
    print("6자리 MTI 코드를 찾지 못했습니다.")
    raise SystemExit


master = (
    master
    .drop_duplicates(
        subset=["MTI6코드"]
    )
    .sort_values("MTI6코드")
    .reset_index(drop=True)
)


# ============================================================
# 7. 결과 요약
# ============================================================

print()
print("=" * 100)
print("MTI6 MASTER 요약")
print("=" * 100)

print(
    f"고유 MTI6 코드 수: "
    f"{master['MTI6코드'].nunique():,}"
)

print(
    f"품목명 확인 수: "
    f"{master['품목명'].notna().sum():,}"
)

print(
    f"품목명 미확인 수: "
    f"{master['품목명'].isna().sum():,}"
)


# ============================================================
# 8. 앞부분 확인
# ============================================================

print()
print("=" * 100)
print("앞부분 30개")
print("=" * 100)

print(
    master.head(30).to_string(
        index=False
    )
)


# ============================================================
# 9. 주요 코드 키워드 확인
# ============================================================

KEYWORDS = [
    "D램",
    "낸드",
    "반도체",
    "프로세서",
    "자동차",
    "승용차",
    "자동차부품",
    "선박",
    "화장품",
    "바이오",
    "의약품",
    "축전지",
    "배터리",
    "철강",
    "석유",
    "섬유",
    "가전",
    "컴퓨터",
    "무선통신",
    "디스플레이"
]


print()
print("=" * 100)
print("주요 키워드 검색")
print("=" * 100)


for keyword in KEYWORDS:

    temp = master[
        master["품목명"]
        .astype(str)
        .str.contains(
            keyword,
            case=False,
            na=False
        )
    ]

    print()
    print(f"[{keyword}]")

    if temp.empty:
        print("찾지 못함")
    else:
        print(
            temp[
                [
                    "MTI6코드",
                    "품목명"
                ]
            ]
            .head(20)
            .to_string(
                index=False
            )
        )


# ============================================================
# 10. MTI 상위코드 생성
# ============================================================
#
# MTI 6단위에서 앞자리 기준으로
# 1/2/3/4단위 코드를 자동 생성합니다.
# ============================================================

master["MTI1"] = (
    master["MTI6코드"]
    .str[:1]
)

master["MTI2"] = (
    master["MTI6코드"]
    .str[:2]
)

master["MTI3"] = (
    master["MTI6코드"]
    .str[:3]
)

master["MTI4"] = (
    master["MTI6코드"]
    .str[:4]
)


# ============================================================
# 11. MTI3 그룹 통계
# ============================================================

mti3_summary = (
    master
    .groupby(
        "MTI3",
        as_index=False
    )
    .agg(
        품목수=(
            "MTI6코드",
            "count"
        )
    )
    .sort_values(
        "MTI3"
    )
)


print()
print("=" * 100)
print("MTI3 그룹 수")
print("=" * 100)

print(
    f"MTI3 고유 그룹 수: "
    f"{mti3_summary['MTI3'].nunique():,}"
)


print()
print(
    mti3_summary.head(50)
    .to_string(index=False)
)


# ============================================================
# 12. CSV 저장
# ============================================================

OUTPUT_MASTER = (
    BASE_DIR
    /
    "mti6_master.csv"
)

OUTPUT_MTI3 = (
    BASE_DIR
    /
    "mti3_group_summary.csv"
)


master.to_csv(
    OUTPUT_MASTER,
    index=False,
    encoding="utf-8-sig"
)

mti3_summary.to_csv(
    OUTPUT_MTI3,
    index=False,
    encoding="utf-8-sig"
)


print()
print("=" * 100)
print("CSV 저장 완료")
print("=" * 100)

print("- mti6_master.csv")
print("- mti3_group_summary.csv")


print()
print("=" * 100)
print("MASTER BUILD COMPLETE")
print("=" * 100)