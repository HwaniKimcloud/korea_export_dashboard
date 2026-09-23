from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# 1. 기본 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

TOTAL_FILE = BASE_DIR / "korea_total_export_monthly.csv"
INDUSTRY_FILE = BASE_DIR / "industry_monthly.csv"


# ============================================================
# 2. 파일 확인
# ============================================================

if not TOTAL_FILE.exists():
    raise FileNotFoundError(
        "korea_total_export_monthly.csv 파일을 찾을 수 없습니다."
    )

if not INDUSTRY_FILE.exists():
    raise FileNotFoundError(
        "industry_monthly.csv 파일을 찾을 수 없습니다."
    )


# ============================================================
# 3. 데이터 로드
# ============================================================

total = pd.read_csv(
    TOTAL_FILE,
    encoding="utf-8-sig"
)

industry = pd.read_csv(
    INDUSTRY_FILE,
    encoding="utf-8-sig"
)


total["기준월"] = pd.to_datetime(
    total["기준월"],
    errors="coerce"
)

industry["기준월"] = pd.to_datetime(
    industry["기준월"],
    errors="coerce"
)


total = total.dropna(
    subset=["기준월"]
).copy()

industry = industry.dropna(
    subset=["기준월"]
).copy()


# ============================================================
# 4. 최신월
# ============================================================

latest_date = total["기준월"].max()

latest_year = latest_date.year
latest_month = latest_date.month

previous_date = (
    latest_date
    -
    pd.DateOffset(years=1)
)


print()
print("=" * 80)
print("EX-SEMICONDUCTOR PULSE CHECK")
print("=" * 80)

print(
    f"최신 데이터: "
    f"{latest_year}년 {latest_month}월"
)


# ============================================================
# 5. Total Export 월별 데이터 정리
# ============================================================

total_monthly = (
    total[
        [
            "기준월",
            "수출액_USD"
        ]
    ]
    .copy()
    .sort_values("기준월")
)


# ============================================================
# 6. KITA 반도체 데이터
# ============================================================

semi = (
    industry[
        industry["산업"]
        ==
        "반도체 (831)"
    ]
    [
        [
            "기준월",
            "수출액_USD"
        ]
    ]
    .copy()
)


semi = semi.rename(
    columns={
        "수출액_USD":
            "반도체_USD"
    }
)


# ============================================================
# 7. KITA Core Basket 월별 합계
# ============================================================

core = (
    industry
    .groupby(
        "기준월",
        as_index=False
    )["수출액_USD"]
    .sum()
    .rename(
        columns={
            "수출액_USD":
                "Core_Basket_USD"
        }
    )
)


# ============================================================
# 8. 세 데이터 결합
# ============================================================

df = (
    total_monthly
    .merge(
        semi,
        on="기준월",
        how="left"
    )
    .merge(
        core,
        on="기준월",
        how="left"
    )
)


# ============================================================
# 9. Ex-Semiconductor 계산
# ============================================================

# ------------------------------------------------------------
# A. Core ex-Semiconductor
# 동일 KITA 데이터 안에서 계산하므로 정의상 가장 깔끔
# ------------------------------------------------------------

df[
    "Core_ex_Semi_USD"
] = (
    df["Core_Basket_USD"]
    -
    df["반도체_USD"]
)


# ------------------------------------------------------------
# B. Total ex-Semiconductor Proxy
# 관세청 전체 - KITA 반도체
# 서로 다른 분류체계이므로 Proxy로만 사용
# ------------------------------------------------------------

df[
    "Total_ex_Semi_Proxy_USD"
] = (
    df["수출액_USD"]
    -
    df["반도체_USD"]
)


# ============================================================
# 10. 보기 좋은 단위
# ============================================================

df["총수출_bn"] = (
    df["수출액_USD"]
    /
    1_000_000_000
)

df["반도체_bn"] = (
    df["반도체_USD"]
    /
    1_000_000_000
)

df["Core_Basket_bn"] = (
    df["Core_Basket_USD"]
    /
    1_000_000_000
)

df["Core_ex_Semi_bn"] = (
    df["Core_ex_Semi_USD"]
    /
    1_000_000_000
)

df["Total_ex_Semi_Proxy_bn"] = (
    df["Total_ex_Semi_Proxy_USD"]
    /
    1_000_000_000
)


# ============================================================
# 11. YoY 계산
# ============================================================

for col in [
    "수출액_USD",
    "반도체_USD",
    "Core_Basket_USD",
    "Core_ex_Semi_USD",
    "Total_ex_Semi_Proxy_USD"
]:

    yoy_col = col.replace(
        "_USD",
        "_YoY_%"
    )

    df[yoy_col] = (
        df[col]
        /
        df[col].shift(12)
        -
        1
    ) * 100


# ============================================================
# 12. 반도체 비중
# ============================================================

df[
    "반도체_전체수출비중_%"
] = (
    df["반도체_USD"]
    /
    df["수출액_USD"]
    *
    100
)


df[
    "반도체_Core비중_%"
] = (
    df["반도체_USD"]
    /
    df["Core_Basket_USD"]
    *
    100
)


# ============================================================
# 13. 최신월 결과
# ============================================================

latest = (
    df[
        df["기준월"]
        ==
        latest_date
    ]
    .iloc[0]
)


print()
print("=" * 80)
print("1. 최신월 구조")
print("=" * 80)

print(
    f"한국 총수출              : "
    f"${latest['총수출_bn']:,.2f}B"
)

print(
    f"KITA 반도체             : "
    f"${latest['반도체_bn']:,.2f}B"
)

print(
    f"Core Basket             : "
    f"${latest['Core_Basket_bn']:,.2f}B"
)

print(
    f"Core ex-Semiconductor   : "
    f"${latest['Core_ex_Semi_bn']:,.2f}B"
)

print(
    f"Total ex-Semi Proxy     : "
    f"${latest['Total_ex_Semi_Proxy_bn']:,.2f}B"
)

print()

print(
    f"반도체 / 전체수출 비중   : "
    f"{latest['반도체_전체수출비중_%']:,.1f}%"
)

print(
    f"반도체 / Core Basket 비중: "
    f"{latest['반도체_Core비중_%']:,.1f}%"
)


# ============================================================
# 14. 성장률 비교
# ============================================================

print()
print("=" * 80)
print("2. YoY 성장률 비교")
print("=" * 80)

print(
    f"전체 수출 YoY            : "
    f"{latest['수출액_YoY_%']:+.1f}%"
)

print(
    f"반도체 YoY               : "
    f"{latest['반도체_YoY_%']:+.1f}%"
)

print(
    f"Core Basket YoY          : "
    f"{latest['Core_Basket_YoY_%']:+.1f}%"
)

print(
    f"Core ex-Semiconductor YoY: "
    f"{latest['Core_ex_Semi_YoY_%']:+.1f}%"
)

print(
    f"Total ex-Semi Proxy YoY  : "
    f"{latest['Total_ex_Semi_Proxy_YoY_%']:+.1f}%"
)


# ============================================================
# 15. 최신 18개월 시계열
# ============================================================

print()
print("=" * 80)
print("3. 최근 월별 추이")
print("=" * 80)


display = (
    df[
        [
            "기준월",
            "총수출_bn",
            "반도체_bn",
            "Core_ex_Semi_bn",
            "Total_ex_Semi_Proxy_bn",
            "수출액_YoY_%",
            "반도체_YoY_%",
            "Core_ex_Semi_YoY_%",
            "Total_ex_Semi_Proxy_YoY_%"
        ]
    ]
    .tail(18)
)


print(
    display.to_string(
        index=False
    )
)


# ============================================================
# 16. 전년동월 증가액 분해
# ============================================================

previous_row = (
    df[
        df["기준월"]
        ==
        previous_date
    ]
)


if not previous_row.empty:

    previous = previous_row.iloc[0]

    total_change = (
        latest["수출액_USD"]
        -
        previous["수출액_USD"]
    )

    semi_change = (
        latest["반도체_USD"]
        -
        previous["반도체_USD"]
    )

    core_ex_change = (
        latest["Core_ex_Semi_USD"]
        -
        previous["Core_ex_Semi_USD"]
    )


    print()
    print("=" * 80)
    print("4. YoY 증가액 분해")
    print("=" * 80)

    print(
        f"전체 수출 증가액      : "
        f"${total_change / 1_000_000_000:+.2f}B"
    )

    print(
        f"반도체 증가액         : "
        f"${semi_change / 1_000_000_000:+.2f}B"
    )

    print(
        f"Core ex-Semi 증가액   : "
        f"${core_ex_change / 1_000_000_000:+.2f}B"
    )


    if total_change != 0:

        semi_contribution = (
            semi_change
            /
            total_change
            *
            100
        )

        core_ex_contribution = (
            core_ex_change
            /
            total_change
            *
            100
        )

        print()

        print(
            f"반도체 증가기여도      : "
            f"{semi_contribution:,.1f}%"
        )

        print(
            f"Core ex-Semi 기여도    : "
            f"{core_ex_contribution:,.1f}%"
        )


# ============================================================
# 17. CSV 저장
# ============================================================

OUTPUT_FILE = (
    BASE_DIR
    /
    "ex_semiconductor_pulse.csv"
)


df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)


print()
print("=" * 80)
print("CSV 저장 완료")
print("=" * 80)

print(
    "- ex_semiconductor_pulse.csv"
)

print()
print("=" * 80)
print("CHECK COMPLETE")
print("=" * 80)