from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# 1. 기본 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MONTHLY_FILE = BASE_DIR / "industry_monthly.csv"


# ============================================================
# 2. 데이터 로드
# ============================================================

if not MONTHLY_FILE.exists():
    raise FileNotFoundError(
        "industry_monthly.csv 파일을 찾을 수 없습니다."
    )

df = pd.read_csv(
    MONTHLY_FILE,
    encoding="utf-8-sig"
)

df["기준월"] = pd.to_datetime(
    df["기준월"]
)


# ============================================================
# 3. 최신월 확인
# ============================================================

latest_date = df["기준월"].max()

latest_year = latest_date.year
latest_month = latest_date.month

previous_date = latest_date - pd.DateOffset(
    years=1
)


print()
print("=" * 80)
print("EXPORT PULSE 검증")
print("=" * 80)

print(
    f"최신 데이터: "
    f"{latest_year}년 {latest_month}월"
)


# ============================================================
# 4. 총수출 YoY
# ============================================================
#
# 전체수출_USD는 산업마다 반복되어 있으므로
# 해당 월에서 첫 번째 값만 사용합니다.
# ============================================================

latest_total = (
    df.loc[
        df["기준월"] == latest_date,
        "전체수출_USD"
    ]
    .dropna()
    .iloc[0]
)


previous_total_series = (
    df.loc[
        df["기준월"] == previous_date,
        "전체수출_USD"
    ]
    .dropna()
)


if previous_total_series.empty:

    previous_total = np.nan
    total_yoy = np.nan

else:

    previous_total = (
        previous_total_series.iloc[0]
    )

    total_yoy = (
        latest_total
        /
        previous_total
        -
        1
    ) * 100


print()
print("=" * 80)
print("1. 총수출 YoY")
print("=" * 80)

print(
    f"{previous_date.strftime('%Y-%m')} 총수출: "
    f"${previous_total / 1_000_000_000:,.2f}B"
)

print(
    f"{latest_date.strftime('%Y-%m')} 총수출: "
    f"${latest_total / 1_000_000_000:,.2f}B"
)

print(
    f"총수출 YoY: "
    f"{total_yoy:+.2f}%"
)


# ============================================================
# 5. 최신월 산업별 데이터
# ============================================================

latest = (
    df[
        df["기준월"]
        ==
        latest_date
    ]
    .copy()
)


previous = (
    df[
        df["기준월"]
        ==
        previous_date
    ]
    [
        [
            "산업",
            "수출액_USD"
        ]
    ]
    .copy()
)


previous = previous.rename(
    columns={
        "수출액_USD":
            "전년동월_수출액_USD"
    }
)


latest = latest.merge(
    previous,
    on="산업",
    how="left"
)

# ============================================================
# merge 후 실제 컬럼명 정리
# ============================================================

# merge 과정에서 동일 이름의 컬럼이 있을 경우
# pandas가 _x, _y를 붙일 수 있으므로 정리합니다.

if "전년동월_수출액_USD_y" in latest.columns:
    latest["전년동월_수출액_USD"] = latest["전년동월_수출액_USD_y"]

elif "전년동월_수출액_USD" not in latest.columns:

    # 전년동월 값을 산업별로 직접 매핑
    previous_map = (
        df[
            df["기준월"] == previous_date
        ]
        .set_index("산업")["수출액_USD"]
    )

    latest["전년동월_수출액_USD"] = (
        latest["산업"].map(previous_map)
    )


# ============================================================
# 산업별 증가액 계산
# ============================================================

latest["증가액_USD"] = (
    latest["수출액_USD"]
    -
    latest["전년동월_수출액_USD"]
)

latest["증가액_bn"] = (
    latest["증가액_USD"]
    /
    1_000_000_000
)


# ============================================================
# 6. 산업별 증가액
# ============================================================

latest["증가액_USD"] = (
    latest["수출액_USD"]
    -
    latest["전년동월_수출액_USD"]
)


latest["증가액_bn"] = (
    latest["증가액_USD"]
    /
    1_000_000_000
)


# ============================================================
# 7. 전체 총수출 증가액
# ============================================================

total_change_usd = (
    latest_total
    -
    previous_total
)


total_change_bn = (
    total_change_usd
    /
    1_000_000_000
)


# ============================================================
# 8. 증가기여도
# ============================================================
#
# 예:
# 총수출 증가액 +$20B
# 반도체 증가액 +$15B
# → 기여도 75%
# ============================================================

if total_change_usd != 0:

    latest["증가기여도_%"] = (
        latest["증가액_USD"]
        /
        total_change_usd
        *
        100
    )

else:

    latest["증가기여도_%"] = np.nan


# ============================================================
# 9. Momentum Gap
# ============================================================
#
# 3M YoY - 당월 YoY
#
# 양수:
# 최근 3개월 추세가 당월보다 강함
#
# 음수:
# 당월이 최근 3개월 평균보다 강함
#
# ============================================================

latest["Momentum_Gap_%p"] = (
    latest["3M_YoY_%"]
    -
    latest["KITA_YoY_%"]
)


# ============================================================
# 10. Momentum Quadrant
# ============================================================
#
# 단순하고 직관적인 4분면
#
# YoY > 0, 3M YoY > YoY
# → 성장 + 가속
#
# YoY > 0, 3M YoY <= YoY
# → 성장 + 둔화
#
# YoY <= 0, 3M YoY > YoY
# → 부진 + 회복
#
# YoY <= 0, 3M YoY <= YoY
# → 부진 + 약화
# ============================================================

def classify_momentum(row):

    yoy = row["KITA_YoY_%"]
    yoy_3m = row["3M_YoY_%"]

    if pd.isna(yoy) or pd.isna(yoy_3m):
        return "N/A"

    if yoy > 0 and yoy_3m > yoy:
        return "성장·가속"

    elif yoy > 0 and yoy_3m <= yoy:
        return "성장·둔화"

    elif yoy <= 0 and yoy_3m > yoy:
        return "부진·회복"

    else:
        return "부진·약화"


latest["Momentum_국면"] = (
    latest.apply(
        classify_momentum,
        axis=1
    )
)


# ============================================================
# 11. 출력용 테이블
# ============================================================

pulse_table = (
    latest[
        [
            "산업",
            "수출액_십억달러",
            "KITA_YoY_%",
            "3M_YoY_%",
            "MoM_%",
            "증가액_bn",
            "증가기여도_%",
            "Momentum_Gap_%p",
            "Momentum_국면"
        ]
    ]
    .sort_values(
        "증가액_bn",
        ascending=False
    )
)


print()
print("=" * 80)
print("2. 산업별 수출 증가기여도")
print("=" * 80)

print(
    f"전체 총수출 증가액: "
    f"${total_change_bn:+.2f}B"
)

print()

print(
    pulse_table[
        [
            "산업",
            "증가액_bn",
            "증가기여도_%",
            "KITA_YoY_%",
            "3M_YoY_%"
        ]
    ].to_string(
        index=False
    )
)


# ============================================================
# 12. Momentum Quadrant 출력
# ============================================================

print()
print("=" * 80)
print("3. Momentum Quadrant")
print("=" * 80)

momentum_table = (
    pulse_table[
        [
            "산업",
            "KITA_YoY_%",
            "3M_YoY_%",
            "Momentum_Gap_%p",
            "Momentum_국면"
        ]
    ]
    .sort_values(
        [
            "Momentum_국면",
            "KITA_YoY_%"
        ],
        ascending=[
            True,
            False
        ]
    )
)


print(
    momentum_table.to_string(
        index=False
    )
)


# ============================================================
# 13. Top Contributors
# ============================================================

positive_contributors = (
    pulse_table[
        pulse_table[
            "증가액_bn"
        ]
        >
        0
    ]
    .head(5)
)


negative_contributors = (
    pulse_table[
        pulse_table[
            "증가액_bn"
        ]
        <
        0
    ]
    .sort_values(
        "증가액_bn",
        ascending=True
    )
    .head(5)
)


print()
print("=" * 80)
print("4. Top Positive Contributors")
print("=" * 80)

if positive_contributors.empty:

    print(
        "증가 기여 산업 없음"
    )

else:

    print(
        positive_contributors[
            [
                "산업",
                "증가액_bn",
                "증가기여도_%"
            ]
        ].to_string(
            index=False
        )
    )


print()
print("=" * 80)
print("5. Top Negative Contributors")
print("=" * 80)

if negative_contributors.empty:

    print(
        "감소 기여 산업 없음"
    )

else:

    print(
        negative_contributors[
            [
                "산업",
                "증가액_bn",
                "증가기여도_%"
            ]
        ].to_string(
            index=False
        )
    )


# ============================================================
# 14. CSV 저장
# ============================================================

pulse_table.to_csv(
    BASE_DIR / "export_pulse_industry.csv",
    index=False,
    encoding="utf-8-sig"
)


print()
print("=" * 80)
print("CSV 저장 완료")
print("=" * 80)

print(
    "- export_pulse_industry.csv"
)