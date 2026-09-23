from pathlib import Path
import pandas as pd


# ============================================================
# 1. 파일 설정
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
FILE = BASE_DIR / "country_monthly.csv"

if not FILE.exists():
    raise FileNotFoundError(
        "country_monthly.csv 파일을 찾을 수 없습니다."
    )


# ============================================================
# 2. 데이터 읽기
# ============================================================

df = pd.read_csv(
    FILE,
    encoding="utf-8-sig"
)

print()
print("=" * 80)
print("KOREA CUSTOMS TOTAL EXPORT CHECK")
print("=" * 80)

print()
print("전체 행 수:", len(df))

print()
print("컬럼:")
print(df.columns.tolist())


# ============================================================
# 3. 기준월 변환
# ============================================================

df["기준월"] = pd.to_datetime(
    df["기준월"],
    errors="coerce"
)

df = df.dropna(
    subset=["기준월"]
).copy()


# ============================================================
# 4. 월별 한국 전체 수출 계산
# ============================================================

total_monthly = (
    df
    .groupby(
        "기준월",
        as_index=False
    )["수출액_USD"]
    .sum()
    .sort_values("기준월")
)

total_monthly["총수출_bn"] = (
    total_monthly["수출액_USD"]
    /
    1_000_000_000
)


# ============================================================
# 5. YoY / MoM 계산
# ============================================================

total_monthly["전년동월_USD"] = (
    total_monthly["수출액_USD"]
    .shift(12)
)

total_monthly["전월_USD"] = (
    total_monthly["수출액_USD"]
    .shift(1)
)

total_monthly["YoY_%"] = (
    (
        total_monthly["수출액_USD"]
        /
        total_monthly["전년동월_USD"]
        -
        1
    )
    *
    100
)

total_monthly["MoM_%"] = (
    (
        total_monthly["수출액_USD"]
        /
        total_monthly["전월_USD"]
        -
        1
    )
    *
    100
)


# ============================================================
# 6. 결과 출력
# ============================================================

print()
print("=" * 80)
print("월별 한국 전체 수출")
print("=" * 80)

print(
    total_monthly[
        [
            "기준월",
            "총수출_bn",
            "YoY_%",
            "MoM_%"
        ]
    ]
    .tail(24)
    .to_string(
        index=False
    )
)


# ============================================================
# 7. 2025.07 vs 2026.07
# ============================================================

check_dates = [
    pd.Timestamp("2025-07-01"),
    pd.Timestamp("2026-07-01")
]

print()
print("=" * 80)
print("CHECK: 2025.07 / 2026.07")
print("=" * 80)

for date in check_dates:

    row = total_monthly[
        total_monthly["기준월"] == date
    ]

    if row.empty:

        print(
            date.strftime("%Y.%m"),
            "데이터 없음"
        )

    else:

        value = row.iloc[0]

        print()
        print(
            date.strftime("%Y.%m"),
            f"총수출 = ${value['총수출_bn']:,.2f}B"
        )

        print(
            f"YoY = {value['YoY_%']:+.2f}%"
        )


# ============================================================
# 8. CSV 저장
# ============================================================

OUTPUT_FILE = (
    BASE_DIR
    /
    "korea_total_export_monthly.csv"
)

total_monthly.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

print()
print("=" * 80)
print("CSV 저장 완료")
print("=" * 80)

print(
    "- korea_total_export_monthly.csv"
)

print()
print("=" * 80)
print("CHECK COMPLETE")
print("=" * 80)