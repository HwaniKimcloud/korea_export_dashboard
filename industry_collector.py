from pathlib import Path
import pandas as pd
import numpy as np
import re


# =================================================
# 1. 기본 설정
# =================================================

DATA_DIR = Path("industry_data")

INPUT_FILE = DATA_DIR / "KITA_MTI3_CORE_MONTHLY.xls"

OUTPUT_MONTHLY = "industry_monthly.csv"
OUTPUT_YTD = "industry_ytd.csv"
OUTPUT_MOMENTUM = "industry_momentum.csv"


# =================================================
# 2. 입력 파일 확인
# =================================================

if not INPUT_FILE.exists():

    print("KITA 월별 MTI 파일을 찾을 수 없습니다.")
    print("찾는 위치:", INPUT_FILE)

    raise SystemExit


print("=" * 70)
print("KITA MTI Industry Collector")
print("=" * 70)

print()
print("입력 파일:", INPUT_FILE)


# =================================================
# 3. Excel 원본 읽기
# =================================================

raw = pd.read_excel(
    INPUT_FILE,
    header=None
)

print()
print("원본 행 수:", len(raw))
print("원본 열 수:", len(raw.columns))


# =================================================
# 4. 헤더 구조 읽기
# =================================================
#
# K-stat 파일 구조
#
# 열 0 : 주기
# 열 1 : 합계금액
#
# 이후부터는
#
# 산업 금액 | 산업 증감률
#
# 두 열씩 반복
#
# 예:
# 열2 반도체 금액
# 열3 반도체 증감률
# 열4 자동차 금액
# 열5 자동차 증감률
#
# =================================================

header_row = raw.iloc[2]


industry_columns = []

for col in range(2, len(raw.columns), 2):

    if col >= len(header_row):
        break

    industry_name = header_row.iloc[col]

    if pd.isna(industry_name):
        continue

    industry_name = str(industry_name).strip()

    if industry_name == "" or industry_name.lower() == "nan":
        continue

    industry_columns.append({
        "산업": industry_name,
        "금액열": col,
        "증감률열": col + 1
    })


print()
print("=" * 70)
print("인식된 산업")
print("=" * 70)

for item in industry_columns:
    print(
        f"{item['산업']} "
        f"| 금액열={item['금액열']} "
        f"| 증감률열={item['증감률열']}"
    )


# =================================================
# 5. 월별 데이터 추출
# =================================================

rows = []

current_year = None


for row_idx in range(3, len(raw)):

    period_value = raw.iloc[row_idx, 0]

    if pd.isna(period_value):
        continue

    period_text = str(period_value).strip()


    # ---------------------------------------------
    # 연도 행 찾기
    # 예: 2025년 / 2026년
    # ---------------------------------------------

    if "년" in period_text and "월" not in period_text:

        year_match = re.search(r"(\d{4})", period_text)

        if year_match:
            current_year = int(year_match.group(1))

        continue


    # ---------------------------------------------
    # 월 행 찾기
    #
    # K-stat에서는
    # "..1월", "..2월"처럼 표시될 수 있으므로
    # 숫자만 추출
    # ---------------------------------------------

    if "월" not in period_text:
        continue

    if current_year is None:
        continue


    month_match = re.search(r"(\d{1,2})\s*월", period_text)

    if not month_match:
        continue

    month = int(month_match.group(1))


    if month < 1 or month > 12:
        continue


    # ---------------------------------------------
    # 전체 수출 금액
    # ---------------------------------------------

    total_export = pd.to_numeric(
        raw.iloc[row_idx, 1],
        errors="coerce"
    )


    # ---------------------------------------------
    # 산업별 금액 / KITA 증감률
    # ---------------------------------------------

    for info in industry_columns:

        industry = info["산업"]
        amount_col = info["금액열"]
        yoy_col = info["증감률열"]


        amount = pd.to_numeric(
            raw.iloc[row_idx, amount_col],
            errors="coerce"
        )


        kita_yoy = np.nan

        if yoy_col < len(raw.columns):

            kita_yoy = pd.to_numeric(
                raw.iloc[row_idx, yoy_col],
                errors="coerce"
            )


        date = pd.Timestamp(
            year=current_year,
            month=month,
            day=1
        )


        rows.append({
            "기준월": date,
            "연도": current_year,
            "월": month,
            "산업": industry,

            "수출액_천달러": amount,

            "수출액_USD": (
                amount * 1000
                if pd.notna(amount)
                else np.nan
            ),

            "수출액_십억달러": (
                amount / 1_000_000
                if pd.notna(amount)
                else np.nan
            ),

            "KITA_YoY_%": kita_yoy,

            "전체수출_천달러": total_export,

            "전체수출_USD": (
                total_export * 1000
                if pd.notna(total_export)
                else np.nan
            )
        })


monthly = pd.DataFrame(rows)


if monthly.empty:

    print()
    print("월별 데이터를 찾지 못했습니다.")

    raise SystemExit


monthly = monthly.sort_values(
    ["산업", "기준월"]
).reset_index(drop=True)


# =================================================
# 6. Python에서 YoY 재계산
# =================================================
#
# KITA가 제공한 증감률과
# Python 계산 결과를 비교하기 위한 용도
#
# =================================================

monthly["전년동월_수출액_USD"] = (
    monthly
    .groupby("산업")
    ["수출액_USD"]
    .shift(12)
)


monthly["계산_YoY_%"] = (
    (
        monthly["수출액_USD"]
        /
        monthly["전년동월_수출액_USD"]
        - 1
    )
    * 100
)


# =================================================
# 7. 전체 수출 대비 산업 비중
# =================================================

monthly["전체수출대비_비중_%"] = (
    monthly["수출액_USD"]
    /
    monthly["전체수출_USD"]
    * 100
)


# =================================================
# 8. 월간 증감률 MoM
# =================================================

monthly["MoM_%"] = (
    monthly
    .groupby("산업")
    ["수출액_USD"]
    .pct_change()
    * 100
)


# =================================================
# 9. 최근 3개월 이동합계
# =================================================

monthly["3M_수출액_USD"] = (
    monthly
    .groupby("산업")
    ["수출액_USD"]
    .transform(
        lambda x:
        x.rolling(
            window=3,
            min_periods=3
        ).sum()
    )
)


monthly["3M_전년동기_USD"] = (
    monthly
    .groupby("산업")
    ["3M_수출액_USD"]
    .shift(12)
)


monthly["3M_YoY_%"] = (
    (
        monthly["3M_수출액_USD"]
        /
        monthly["3M_전년동기_USD"]
        - 1
    )
    * 100
)


# =================================================
# 10. 최신 데이터 확인
# =================================================

latest_date = monthly["기준월"].max()

latest_year = latest_date.year
latest_month = latest_date.month

previous_year = latest_year - 1


print()
print("=" * 70)
print("데이터 최신 시점")
print("=" * 70)

print(
    f"{latest_year}년 {latest_month}월"
)


# =================================================
# 11. 최신월 산업별 현황
# =================================================

latest_snapshot = (
    monthly[
        monthly["기준월"] == latest_date
    ]
    .copy()
)


latest_snapshot = latest_snapshot[
    [
        "산업",
        "수출액_십억달러",
        "KITA_YoY_%",
        "계산_YoY_%",
        "MoM_%",
        "3M_YoY_%",
        "전체수출대비_비중_%"
    ]
]


latest_snapshot = latest_snapshot.sort_values(
    "수출액_십억달러",
    ascending=False
)


print()
print("=" * 70)
print("최신월 주요 산업")
print("=" * 70)

print(
    latest_snapshot.to_string(
        index=False
    )
)


# =================================================
# 12. YTD 계산
# =================================================

ytd_rows = []


for industry in monthly["산업"].unique():

    item = monthly[
        monthly["산업"] == industry
    ]


    current_ytd = item[
        (item["기준월"].dt.year == latest_year)
        &
        (item["기준월"].dt.month <= latest_month)
    ]["수출액_USD"].sum()


    previous_ytd = item[
        (item["기준월"].dt.year == previous_year)
        &
        (item["기준월"].dt.month <= latest_month)
    ]["수출액_USD"].sum()


    if previous_ytd != 0:

        ytd_yoy = (
            current_ytd
            /
            previous_ytd
            - 1
        ) * 100

    else:

        ytd_yoy = np.nan


    ytd_rows.append({
        "산업": industry,
        "비교기간": f"1-{latest_month}월",

        f"{previous_year}_YTD_USD":
            previous_ytd,

        f"{latest_year}_YTD_USD":
            current_ytd,

        f"{previous_year}_YTD_bn":
            previous_ytd / 1_000_000_000,

        f"{latest_year}_YTD_bn":
            current_ytd / 1_000_000_000,

        "YTD_YoY_%":
            ytd_yoy,

        "YTD_증감액_bn":
            (
                current_ytd
                -
                previous_ytd
            )
            / 1_000_000_000
    })


ytd = pd.DataFrame(ytd_rows)


ytd = ytd.sort_values(
    f"{latest_year}_YTD_bn",
    ascending=False
)


print()
print("=" * 70)
print(
    f"YTD 비교 "
    f"({previous_year} vs {latest_year}, "
    f"1~{latest_month}월)"
)
print("=" * 70)


print(
    ytd.to_string(
        index=False
    )
)


# =================================================
# 13. Momentum Snapshot
# =================================================

momentum = (
    monthly[
        monthly["기준월"] == latest_date
    ]
    [
        [
            "기준월",
            "산업",
            "수출액_십억달러",
            "계산_YoY_%",
            "MoM_%",
            "3M_YoY_%",
            "전체수출대비_비중_%"
        ]
    ]
    .copy()
)


momentum = momentum.sort_values(
    "계산_YoY_%",
    ascending=False
)


# =================================================
# 14. CSV 저장
# =================================================

monthly.to_csv(
    OUTPUT_MONTHLY,
    index=False,
    encoding="utf-8-sig"
)


ytd.to_csv(
    OUTPUT_YTD,
    index=False,
    encoding="utf-8-sig"
)


momentum.to_csv(
    OUTPUT_MOMENTUM,
    index=False,
    encoding="utf-8-sig"
)


print()
print("=" * 70)
print("CSV 저장 완료")
print("=" * 70)

print("-", OUTPUT_MONTHLY)
print("-", OUTPUT_YTD)
print("-", OUTPUT_MOMENTUM)

print()
print("=" * 70)
print("반도체 YoY 검증")
print("=" * 70)

check = monthly[
    (monthly["산업"] == "반도체 (831)") &
    (
        (monthly["기준월"] == pd.Timestamp("2025-07-01")) |
        (monthly["기준월"] == pd.Timestamp("2026-07-01"))
    )
]

print(
    check[
        [
            "기준월",
            "산업",
            "수출액_십억달러",
            "KITA_YoY_%",
            "계산_YoY_%"
        ]
    ].to_string(index=False)
)