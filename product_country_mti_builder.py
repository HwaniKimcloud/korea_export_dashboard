from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# 1. PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

PRODUCT_COUNTRY_FILE = (
    BASE_DIR / "product_country_multi_monthly.csv"
)

MASTER_FILE = (
    BASE_DIR / "official_hsk_mti_master.csv"
)

OUTPUT_MAP = (
    BASE_DIR / "product_country_hs4_mapping_qc.csv"
)

OUTPUT_FINAL = (
    BASE_DIR / "product_country_mti_monthly.csv"
)


# ============================================================
# 2. LOAD
# ============================================================

pc = pd.read_csv(
    PRODUCT_COUNTRY_FILE,
    dtype={
        "조회HS": str,
        "국가코드": str,
    },
)

master = pd.read_csv(
    MASTER_FILE,
    dtype={
        "HSK10": str,
        "MTI6": str,
    },
)


print()
print("=" * 100)
print("PRODUCT × COUNTRY MTI BUILDER")
print("=" * 100)

print(
    "Product × Country rows :",
    f"{len(pc):,}",
)

print(
    "MTI-HSK Master rows    :",
    f"{len(master):,}",
)


# ============================================================
# 3. NORMALIZE
# ============================================================

pc["조회HS"] = (
    pc["조회HS"]
    .astype(str)
    .str.replace(".0", "", regex=False)
    .str.strip()
    .str.zfill(4)
)

master["HSK10"] = (
    master["HSK10"]
    .astype(str)
    .str.replace(".0", "", regex=False)
    .str.strip()
    .str.zfill(10)
)

master["MTI6"] = (
    master["MTI6"]
    .astype(str)
    .str.replace(".0", "", regex=False)
    .str.strip()
)

master["산업20"] = (
    master["산업20"]
    .astype(str)
    .str.strip()
)


# HSK10 → HS4
master["HS4"] = (
    master["HSK10"]
    .str[:4]
)


# ============================================================
# 4. HS4 → MTI / 산업20 구조 확인
# ============================================================

def unique_join(series):

    values = sorted(
        {
            str(x).strip()
            for x in series
            if pd.notna(x)
            and str(x).strip() != ""
            and str(x).strip().lower() != "nan"
        }
    )

    return " | ".join(values)


mapping = (
    master
    .groupby(
        "HS4",
        as_index=False,
    )
    .agg(
        HSK10수=(
            "HSK10",
            "nunique",
        ),

        MTI6수=(
            "MTI6",
            "nunique",
        ),

        산업20수=(
            "산업20",
            "nunique",
        ),

        MTI6목록=(
            "MTI6",
            unique_join,
        ),

        산업20목록=(
            "산업20",
            unique_join,
        ),
    )
)


# ============================================================
# 5. Product × Country에서 실제 사용 중인 HS4만 추출
# ============================================================

used_hs4 = (
    pc[
        [
            "조회HS",
            "대시보드품목",
        ]
    ]
    .drop_duplicates()
)


qc = used_hs4.merge(
    mapping,
    how="left",
    left_on="조회HS",
    right_on="HS4",
)


# ============================================================
# 6. Mapping 상태 판정
# ============================================================

def mapping_status(row):

    if pd.isna(
        row["HSK10수"]
    ):
        return "NO_MATCH"

    if (
        row["산업20수"] == 1
        and
        row["MTI6수"] == 1
    ):
        return "UNIQUE_MTI6"

    if (
        row["산업20수"] == 1
        and
        row["MTI6수"] > 1
    ):
        return "UNIQUE_INDUSTRY_MULTI_MTI"

    if row["산업20수"] > 1:
        return "MULTI_INDUSTRY"

    return "REVIEW"


qc["매핑상태"] = qc.apply(
    mapping_status,
    axis=1,
)


qc = (
    qc
    .sort_values(
        [
            "매핑상태",
            "조회HS",
        ]
    )
    .reset_index(
        drop=True
    )
)


qc.to_csv(
    OUTPUT_MAP,
    index=False,
    encoding="utf-8-sig",
)


# ============================================================
# 7. 안전하게 산업20 부여
#
# 산업20이 유일한 경우에만 사용
# MTI6가 여러 개인 경우는 억지로 하나 선택하지 않음
# ============================================================

safe_map = qc[
    qc["산업20수"] == 1
].copy()


safe_map["산업20"] = (
    safe_map["산업20목록"]
)


safe_map["MTI6"] = np.where(
    safe_map["MTI6수"] == 1,
    safe_map["MTI6목록"],
    "",
)


safe_map = safe_map[
    [
        "조회HS",
        "산업20",
        "MTI6",
        "MTI6수",
        "산업20수",
        "매핑상태",
    ]
]


# ============================================================
# 8. Product × Country에 매핑
# ============================================================

final = pc.merge(
    safe_map,
    how="left",
    on="조회HS",
)


# 원래 대시보드 품목명 보존
final = final[
    [
        "산업20",
        "대시보드품목",
        "MTI6",
        "조회HS",
        "국가코드",
        "국가",
        "기준월",
        "수출액_USD",
        "전년동월_수출액_USD",
        "YoY_%",
        "MoM_%",
        "수출액_십억달러",
        "매핑상태",
    ]
]


final.to_csv(
    OUTPUT_FINAL,
    index=False,
    encoding="utf-8-sig",
)


# ============================================================
# 9. QC OUTPUT
# ============================================================

print()
print("=" * 100)
print("HS4 MAPPING QC")
print("=" * 100)

summary = (
    qc[
        "매핑상태"
    ]
    .value_counts()
)

print(
    summary.to_string()
)


print()
print("=" * 100)
print("MULTI / UNMATCHED HS4")
print("=" * 100)

review = qc[
    ~qc[
        "매핑상태"
    ]
    .isin(
        [
            "UNIQUE_MTI6",
            "UNIQUE_INDUSTRY_MULTI_MTI",
        ]
    )
]


if review.empty:

    print(
        "검토 필요 HS4 없음"
    )

else:

    print(
        review[
            [
                "조회HS",
                "대시보드품목",
                "HSK10수",
                "MTI6수",
                "산업20수",
                "MTI6목록",
                "산업20목록",
                "매핑상태",
            ]
        ]
        .to_string(
            index=False
        )
    )


print()
print("=" * 100)
print("FINAL")
print("=" * 100)

mapped_rows = final[
    "산업20"
].notna().sum()

total_rows = len(
    final
)

coverage = (
    mapped_rows
    /
    total_rows
    *
    100
    if total_rows
    else 0
)

print(
    f"Product × Country rows : {total_rows:,}"
)

print(
    f"산업20 매핑 rows       : {mapped_rows:,}"
)

print(
    f"Row Coverage           : {coverage:.2f}%"
)

print()
print("CSV 저장 완료")
print(
    "-",
    OUTPUT_MAP.name,
)
print(
    "-",
    OUTPUT_FINAL.name,
)

print()
print("=" * 100)
print("BUILD COMPLETE")
print("=" * 100)