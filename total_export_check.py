from pathlib import Path
import pandas as pd


# ============================================================
# 1. 파일 설정
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
FILE = BASE_DIR / "industry_monthly.csv"

if not FILE.exists():
    raise FileNotFoundError(
        "industry_monthly.csv 파일을 찾을 수 없습니다."
    )


# ============================================================
# 2. 데이터 읽기
# ============================================================

df = pd.read_csv(
    FILE,
    encoding="utf-8-sig"
)

df["기준월"] = pd.to_datetime(
    df["기준월"]
)


print()
print("=" * 80)
print("TOTAL EXPORT DATA CHECK")
print("=" * 80)

print()
print("전체 행 수:", len(df))
print("기간:", df["기준월"].min(), "~", df["기준월"].max())

print()
print("컬럼:")
print(df.columns.tolist())


# ============================================================
# 3. 2025년 7월 / 2026년 7월 확인
# ============================================================

CHECK_DATES = [
    pd.Timestamp("2025-07-01"),
    pd.Timestamp("2026-07-01")
]


for check_date in CHECK_DATES:

    temp = (
        df[
            df["기준월"] == check_date
        ]
        .copy()
    )

    print()
    print("=" * 80)
    print(check_date.strftime("%Y년 %m월"))
    print("=" * 80)

    if temp.empty:

        print("해당 월 데이터가 없습니다.")
        continue

    print()
    print("산업 행 수:", len(temp))

    print()
    print("전체수출_USD 고유값:")
    print(
        temp["전체수출_USD"]
        .dropna()
        .unique()
    )

    print()
    print("전체수출_USD 고유값 개수:")
    print(
        temp["전체수출_USD"]
        .dropna()
        .nunique()
    )

    print()
    print("산업별 값:")
    print(
        temp[
            [
                "산업",
                "수출액_USD",
                "전체수출_USD"
            ]
        ].to_string(
            index=False
        )
    )

    industry_sum = (
        temp["수출액_USD"]
        .sum()
    )

    total_values = (
        temp["전체수출_USD"]
        .dropna()
    )

    if not total_values.empty:

        total_export = (
            total_values.iloc[0]
        )

        print()
        print(
            "7개 산업 합계:",
            f"${industry_sum / 1_000_000_000:,.2f}B"
        )

        print(
            "전체수출_USD:",
            f"${total_export / 1_000_000_000:,.2f}B"
        )

        if total_export != 0:

            print(
                "7개 산업 / 전체수출 비중:",
                f"{industry_sum / total_export * 100:,.2f}%"
            )


# ============================================================
# 4. 월별 전체수출 값 확인
# ============================================================

print()
print("=" * 80)
print("월별 전체수출_USD 추이")
print("=" * 80)


total_monthly = (
    df[
        [
            "기준월",
            "전체수출_USD"
        ]
    ]
    .dropna()
    .drop_duplicates()
    .sort_values("기준월")
)


total_monthly["전체수출_bn"] = (
    total_monthly["전체수출_USD"]
    /
    1_000_000_000
)


print(
    total_monthly[
        [
            "기준월",
            "전체수출_bn"
        ]
    ]
    .tail(24)
    .to_string(
        index=False
    )
)


# ============================================================
# 5. 전년동월 비교
# ============================================================

def get_total(date):

    values = (
        df.loc[
            df["기준월"] == date,
            "전체수출_USD"
        ]
        .dropna()
        .unique()
    )

    if len(values) == 0:
        return None

    return values[0]


total_2025 = get_total(
    pd.Timestamp("2025-07-01")
)

total_2026 = get_total(
    pd.Timestamp("2026-07-01")
)


print()
print("=" * 80)
print("2025.07 vs 2026.07")
print("=" * 80)


if total_2025 is not None and total_2026 is not None:

    yoy = (
        total_2026
        /
        total_2025
        -
        1
    ) * 100

    print(
        f"2025.07: "
        f"${total_2025 / 1_000_000_000:,.2f}B"
    )

    print(
        f"2026.07: "
        f"${total_2026 / 1_000_000_000:,.2f}B"
    )

    print(
        f"YoY: {yoy:+.2f}%"
    )

else:

    print(
        "비교에 필요한 데이터가 없습니다."
    )


print()
print("=" * 80)
print("CHECK COMPLETE")
print("=" * 80)