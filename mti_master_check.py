from pathlib import Path
import pandas as pd


# ============================================================
# 1. 경로 설정
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "industry_data"

FILE = DATA_DIR / "KITA_MTI_INDUSTRY_EXPORT_DATA.xls"


if not FILE.exists():
    raise FileNotFoundError(
        f"파일을 찾을 수 없습니다:\n{FILE}"
    )


print()
print("=" * 80)
print("KITA MTI MASTER CHECK")
print("=" * 80)

print("입력 파일:", FILE)


# ============================================================
# 2. 원본 읽기
# ============================================================

raw = pd.read_excel(
    FILE,
    header=None
)


print()
print("원본 행 수:", len(raw))
print("원본 열 수:", len(raw.columns))


# ============================================================
# 3. 상단 구조 확인
# ============================================================

print()
print("=" * 80)
print("상단 15행")
print("=" * 80)

print(
    raw.head(15).to_string(
        index=True,
        header=True
    )
)


# ============================================================
# 4. 산업 헤더 행 추출
# ============================================================
#
# 이전 검증 결과상
# row 2에 산업명들이 2열 간격으로 들어 있었음
#
# 예:
# 반도체 (831)
# 자동차 (741)
# 자동차부품 (742)
# ...
# ============================================================

HEADER_ROW_INDEX = 2

header_row = raw.iloc[HEADER_ROW_INDEX]


industries = []


for col in range(2, len(raw.columns), 2):

    if col >= len(header_row):
        break

    value = header_row.iloc[col]

    if pd.isna(value):
        continue

    value = str(value).strip()

    if value == "" or value.lower() == "nan":
        continue

    industries.append({
        "열번호": col,
        "원본산업명": value
    })


industry_df = pd.DataFrame(industries)


print()
print("=" * 80)
print("원본 산업 헤더")
print("=" * 80)

print(
    industry_df.to_string(
        index=False
    )
)


# ============================================================
# 5. MTI 코드 분리
# ============================================================
#
# 예:
# 반도체 (831)
# 자동차 (741)
# ============================================================

industry_df["산업명"] = (
    industry_df["원본산업명"]
    .str.replace(
        r"\s*\(\d+\)\s*$",
        "",
        regex=True
    )
    .str.strip()
)


industry_df["MTI코드"] = (
    industry_df["원본산업명"]
    .str.extract(
        r"\((\d+)\)"
    )[0]
)


print()
print("=" * 80)
print("산업명 / MTI 코드")
print("=" * 80)

print(
    industry_df[
        [
            "산업명",
            "MTI코드",
            "원본산업명",
            "열번호"
        ]
    ].to_string(
        index=False
    )
)


# ============================================================
# 6. 중복 확인
# ============================================================

print()
print("=" * 80)
print("중복 체크")
print("=" * 80)


name_dup = (
    industry_df[
        industry_df["산업명"]
        .duplicated(keep=False)
    ]
)

code_dup = (
    industry_df[
        industry_df["MTI코드"]
        .duplicated(keep=False)
        &
        industry_df["MTI코드"].notna()
    ]
)


print()
print("산업명 중복:")

if name_dup.empty:
    print("없음")
else:
    print(name_dup.to_string(index=False))


print()
print("MTI코드 중복:")

if code_dup.empty:
    print("없음")
else:
    print(code_dup.to_string(index=False))


# ============================================================
# 7. 후보 20대 산업 자동 검색
# ============================================================

TARGET_KEYWORDS = [
    "반도체",
    "디스플레이",
    "무선통신",
    "컴퓨터",
    "가전",
    "자동차",
    "자동차부품",
    "선박",
    "일반기계",
    "석유제품",
    "석유화학",
    "이차전지",
    "철강",
    "비철금속",
    "전기기기",
    "바이오",
    "농수산",
    "화장품",
    "생활용품",
    "섬유"
]


matches = []


for keyword in TARGET_KEYWORDS:

    temp = industry_df[
        industry_df["산업명"]
        .str.contains(
            keyword,
            case=False,
            na=False
        )
    ].copy()

    if temp.empty:

        matches.append({
            "검색어": keyword,
            "매칭산업명": "찾지 못함",
            "MTI코드": ""
        })

    else:

        for _, row in temp.iterrows():

            matches.append({
                "검색어": keyword,
                "매칭산업명": row["산업명"],
                "MTI코드": row["MTI코드"]
            })


match_df = pd.DataFrame(matches)


print()
print("=" * 80)
print("20대 산업 후보 매칭")
print("=" * 80)

print(
    match_df.to_string(
        index=False
    )
)


# ============================================================
# 8. CSV 저장
# ============================================================

industry_df.to_csv(
    BASE_DIR / "mti_industry_master.csv",
    index=False,
    encoding="utf-8-sig"
)


match_df.to_csv(
    BASE_DIR / "mti_20_target_match.csv",
    index=False,
    encoding="utf-8-sig"
)


print()
print("=" * 80)
print("CSV 저장 완료")
print("=" * 80)

print("- mti_industry_master.csv")
print("- mti_20_target_match.csv")

print()
print("=" * 80)
print("CHECK COMPLETE")
print("=" * 80)