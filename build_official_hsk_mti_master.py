from pathlib import Path
import pandas as pd


# ============================================================
# 1. 기본 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "industry_data"

INPUT_FILE = DATA_DIR / "2026 MTI-HSK 코드표_vFF_260507.xlsx"

OUTPUT_MASTER = BASE_DIR / "official_hsk_mti_master.csv"
OUTPUT_MTI20 = BASE_DIR / "official_mti20_master.csv"
OUTPUT_SUMMARY = BASE_DIR / "official_mti20_summary.csv"


# ============================================================
# 2. 입력 파일 확인
# ============================================================

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"공식 코드표를 찾을 수 없습니다:\n{INPUT_FILE}"
    )


print()
print("=" * 100)
print("OFFICIAL HSK-MTI MASTER BUILDER")
print("=" * 100)

print("입력 파일:", INPUT_FILE.name)


# ============================================================
# 3. 연계표 시트 찾기
# ============================================================

xls = pd.ExcelFile(INPUT_FILE)

target_sheet = None

for sheet in xls.sheet_names:

    normalized = (
        str(sheet)
        .replace(" ", "")
        .replace("-", "")
        .upper()
    )

    if (
        "HSK" in normalized
        and "MTI" in normalized
        and "연계" in normalized
    ):
        target_sheet = sheet
        break


if target_sheet is None:
    raise ValueError(
        "HSK-MTI 연계표 시트를 찾지 못했습니다."
    )


print("사용 시트:", target_sheet)


# ============================================================
# 4. 원본 읽기
# ============================================================

raw = pd.read_excel(
    INPUT_FILE,
    sheet_name=target_sheet,
    header=None,
    dtype=str
)


print(
    f"원본 크기: {len(raw):,}행 × {len(raw.columns):,}열"
)


# ============================================================
# 5. 필요한 4개 열 추출
#
# 이전 inspection 결과 기준:
# C1 = 적용연도
# C2 = HSK10
# C3 = MTI6
# C4 = 20대 산업
# ============================================================

df = raw.iloc[:, :4].copy()

df.columns = [
    "적용연도",
    "HSK10",
    "MTI6",
    "산업20"
]


# ============================================================
# 6. 헤더 / 공백 제거
# ============================================================

for col in df.columns:

    df[col] = (
        df[col]
        .astype(str)
        .str.strip()
    )


df = df[
    ~df["적용연도"].isin(
        [
            "",
            "nan",
            "None",
            "적용연도",
            "연도",
        ]
    )
].copy()


# ============================================================
# 7. 코드 정규화
# ============================================================

def normalize_hsk10(value):

    text = str(value).strip()

    if text in [
        "",
        "nan",
        "None"
    ]:
        return None

    text = text.replace(".0", "")

    if not text.isdigit():
        return None

    return text.zfill(10)


def normalize_mti6(value):

    text = str(value).strip()

    if text in [
        "",
        "nan",
        "None"
    ]:
        return None

    text = text.replace(".0", "")

    if not text.isdigit():
        return None

    return text.zfill(6)


df["HSK10"] = df["HSK10"].apply(
    normalize_hsk10
)

df["MTI6"] = df["MTI6"].apply(
    normalize_mti6
)


# ============================================================
# 8. 유효 행만 유지
# ============================================================

df = df[
    df["HSK10"].notna()
    &
    df["MTI6"].notna()
].copy()


# ============================================================
# 9. 산업명 정리
# ============================================================

df["산업20"] = (
    df["산업20"]
    .replace(
        {
            "nan": "",
            "None": "",
        }
    )
    .fillna("")
    .astype(str)
    .str.strip()
)


# ============================================================
# 10. 중복 제거
# ============================================================

before = len(df)

df = (
    df
    .drop_duplicates(
        subset=[
            "적용연도",
            "HSK10",
            "MTI6",
            "산업20",
        ]
    )
    .reset_index(drop=True)
)

after = len(df)


print()
print("=" * 100)
print("기본 정리")
print("=" * 100)

print(
    "정리 전 행 수:",
    f"{before:,}"
)

print(
    "정리 후 행 수:",
    f"{after:,}"
)

print(
    "고유 HSK10:",
    f"{df['HSK10'].nunique():,}"
)

print(
    "고유 MTI6:",
    f"{df['MTI6'].nunique():,}"
)


# ============================================================
# 11. HSK10 중복 연결 검증
#
# 하나의 HSK10이 복수 MTI6에 연결되는지 확인
# ============================================================

hsk_mti_count = (
    df
    .groupby("HSK10")["MTI6"]
    .nunique()
)


multi_mti_hsk = (
    hsk_mti_count[
        hsk_mti_count > 1
    ]
)


print()
print("=" * 100)
print("HSK10 → MTI6 무결성")
print("=" * 100)

print(
    "복수 MTI6에 연결된 HSK10 수:",
    len(multi_mti_hsk)
)


if len(multi_mti_hsk) == 0:

    print("HSK10 → MTI6 관계: PASS")

else:

    print("검토 필요")

    problem_codes = (
        multi_mti_hsk
        .head(30)
        .index
    )

    print(
        df[
            df["HSK10"].isin(
                problem_codes
            )
        ]
        .sort_values(
            [
                "HSK10",
                "MTI6"
            ]
        )
        .to_string(
            index=False
        )
    )


# ============================================================
# 12. 공식 20대 산업만 추출
# ============================================================

mti20 = df[
    (df["산업20"] != "") &
    (df["산업20"] != "기타")
].copy()

print()
print("=" * 100)
print("20대 산업 분류")
print("=" * 100)

print(
    "20대 산업 포함 HSK10:",
    f"{mti20['HSK10'].nunique():,}"
)

print(
    "20대 산업 포함 MTI6:",
    f"{mti20['MTI6'].nunique():,}"
)

print(
    "고유 산업 수:",
    mti20["산업20"].nunique()
)


# ============================================================
# 13. 산업명 목록
# ============================================================

industry_list = sorted(
    mti20["산업20"]
    .dropna()
    .unique()
)


print()
print("=" * 100)
print("산업명 목록")
print("=" * 100)

for idx, industry in enumerate(
    industry_list,
    start=1
):
    print(
        f"{idx:>2}. {industry}"
    )


# ============================================================
# 14. 산업별 Summary
# ============================================================

summary = (
    mti20
    .groupby(
        "산업20",
        as_index=False
    )
    .agg(
        HSK10_수=(
            "HSK10",
            "nunique"
        ),
        MTI6_수=(
            "MTI6",
            "nunique"
        )
    )
    .sort_values(
        "산업20"
    )
    .reset_index(drop=True)
)


print()
print("=" * 100)
print("산업별 HSK10 / MTI6 구성")
print("=" * 100)

print(
    summary.to_string(
        index=False
    )
)


# ============================================================
# 15. 산업 간 HSK 중복 검증
# ============================================================

hsk_industry_count = (
    mti20
    .groupby("HSK10")["산업20"]
    .nunique()
)


overlap_hsk = (
    hsk_industry_count[
        hsk_industry_count > 1
    ]
)


print()
print("=" * 100)
print("산업 간 HSK10 중복")
print("=" * 100)

print(
    "복수 산업에 속한 HSK10:",
    len(overlap_hsk)
)


if len(overlap_hsk) == 0:

    print("산업 간 HSK10 중복: PASS")

else:

    print("검토 필요")

    overlap_codes = (
        overlap_hsk
        .head(50)
        .index
    )

    print(
        mti20[
            mti20["HSK10"].isin(
                overlap_codes
            )
        ]
        .sort_values(
            [
                "HSK10",
                "산업20"
            ]
        )
        .to_string(
            index=False
        )
    )


# ============================================================
# 16. 산업 간 MTI6 중복 검증
#
# 하나의 MTI6가 여러 산업에 속할 수도 있으므로
# 확인만 하고 바로 오류 처리하지는 않음
# ============================================================

mti_industry_count = (
    mti20
    .groupby("MTI6")["산업20"]
    .nunique()
)


overlap_mti = (
    mti_industry_count[
        mti_industry_count > 1
    ]
)


print()
print("=" * 100)
print("산업 간 MTI6 중복")
print("=" * 100)

print(
    "복수 산업에 걸친 MTI6:",
    len(overlap_mti)
)


if len(overlap_mti) == 0:

    print("산업 간 MTI6 중복: PASS")

else:

    print("공식 연계표상 복수 산업 사용 MTI6 존재")

    overlap_codes = (
        overlap_mti
        .head(50)
        .index
    )

    print(
        mti20[
            mti20["MTI6"].isin(
                overlap_codes
            )
        ][
            [
                "HSK10",
                "MTI6",
                "산업20"
            ]
        ]
        .sort_values(
            [
                "MTI6",
                "산업20",
                "HSK10"
            ]
        )
        .head(100)
        .to_string(
            index=False
        )
    )


# ============================================================
# 17. 20개 여부 검증
# ============================================================

industry_count = (
    mti20["산업20"]
    .nunique()
)


print()
print("=" * 100)
print("FINAL CHECK")
print("=" * 100)


print(
    f"고유 산업 수: {industry_count}"
)


if industry_count == 20:

    print("20대 산업 수 검증: PASS")

else:

    print(
        "20대 산업 수 검증: REVIEW REQUIRED"
    )


# ============================================================
# 18. CSV 저장
# ============================================================

df.to_csv(
    OUTPUT_MASTER,
    index=False,
    encoding="utf-8-sig"
)


mti20.to_csv(
    OUTPUT_MTI20,
    index=False,
    encoding="utf-8-sig"
)


summary.to_csv(
    OUTPUT_SUMMARY,
    index=False,
    encoding="utf-8-sig"
)


print()
print("=" * 100)
print("CSV 저장 완료")
print("=" * 100)

print("- official_hsk_mti_master.csv")
print("- official_mti20_master.csv")
print("- official_mti20_summary.csv")


print()
print("=" * 100)
print("MASTER BUILD COMPLETE")
print("=" * 100)