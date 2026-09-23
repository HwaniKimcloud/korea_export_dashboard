import truststore
truststore.inject_into_ssl()

import requests
import urllib.parse
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np


# ============================================================
# 1. 기본 설정
# ============================================================

URL = "https://apis.data.go.kr/1220000/nationtrade/getNationtradeList"

SERVICE_KEY = "Jqr042WhXmRju%2F2E4uTPkTQqeJWPrWOjV2YRbdOkdF5B6QuZwyE5p1%2BJ1z1vLG6n2ZKpJBVejEavVIIWG8CrKQ%3D%3D"
SERVICE_KEY = urllib.parse.unquote(SERVICE_KEY)


# ============================================================
# 2. API 호출 함수
# ============================================================

def get_all_country_data(start_yymm, end_yymm):

    params = {
        "serviceKey": SERVICE_KEY,
        "strtYymm": start_yymm,
        "endYymm": end_yymm
    }

    response = requests.get(
        URL,
        params=params,
        timeout=60
    )

    root = ET.fromstring(response.text)

    result_code = root.findtext(".//resultCode")
    result_msg = root.findtext(".//resultMsg")

    print(
        f"{start_yymm} ~ {end_yymm} "
        f": {result_code} {result_msg}"
    )

    if result_code != "00":
        return pd.DataFrame()

    rows = []

    for item in root.findall(".//item"):

        rows.append({
            "국가코드": item.findtext("statCd"),
            "국가": item.findtext("statCdCntnKor1"),
            "기준월": item.findtext("year"),
            "수출건수": item.findtext("expCnt"),
            "수출액_USD": item.findtext("expDlr"),
            "수입건수": item.findtext("impCnt"),
            "수입액_USD": item.findtext("impDlr"),
            "무역수지_USD": item.findtext("balPayments")
        })

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    numeric_cols = [
        "수출건수",
        "수출액_USD",
        "수입건수",
        "수입액_USD",
        "무역수지_USD"
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    return df


# ============================================================
# 3. 2025 / 2026 데이터 호출
# ============================================================

print()
print("=" * 70)
print("전체 국가 데이터 수집 시작")
print("=" * 70)

df_2025 = get_all_country_data(
    "202501",
    "202512"
)

df_2026 = get_all_country_data(
    "202601",
    "202608"
)


# ============================================================
# 4. 통합
# ============================================================

all_data = []

if not df_2025.empty:
    all_data.append(df_2025)

if not df_2026.empty:
    all_data.append(df_2026)

if not all_data:
    raise Exception("수집된 국가 데이터가 없습니다.")

raw = pd.concat(
    all_data,
    ignore_index=True
)

print()
print("전체 원본 데이터 행 수:", len(raw))


# ============================================================
# 5. 날짜 정리
# ============================================================

raw["기준월"] = (
    raw["기준월"]
    .astype(str)
    .str.replace(".", "", regex=False)
)

raw["기준월"] = pd.to_datetime(
    raw["기준월"],
    format="%Y%m",
    errors="coerce"
)

invalid_rows = raw["기준월"].isna().sum()

print(
    "제외된 비월별 행 수:",
    invalid_rows
)

raw = (
    raw
    .dropna(subset=["기준월"])
    .copy()
)


# ============================================================
# 6. 국가명 정리
# ============================================================

raw["국가"] = (
    raw["국가"]
    .astype(str)
    .str.strip()
)

raw["국가코드"] = (
    raw["국가코드"]
    .astype(str)
    .str.strip()
)


# ============================================================
# 7. 월별 국가 데이터
# ============================================================

monthly = (
    raw
    .groupby(
        [
            "국가코드",
            "국가",
            "기준월"
        ],
        as_index=False
    )
    ["수출액_USD"]
    .sum()
)

monthly = monthly.sort_values(
    [
        "국가",
        "기준월"
    ]
)


# ============================================================
# 8. YoY
# ============================================================

monthly["전년동월_수출액_USD"] = (
    monthly
    .groupby("국가")
    ["수출액_USD"]
    .shift(12)
)

monthly["YoY_%"] = (
    (
        monthly["수출액_USD"]
        /
        monthly["전년동월_수출액_USD"]
        - 1
    )
    * 100
)


# ============================================================
# 9. MoM
# ============================================================

monthly["MoM_%"] = (
    monthly
    .groupby("국가")
    ["수출액_USD"]
    .pct_change()
    * 100
)


# ============================================================
# 10. 보기 좋은 단위
# ============================================================

monthly["수출액_십억달러"] = (
    monthly["수출액_USD"]
    / 1_000_000_000
)


# ============================================================
# 11. 최신월
# ============================================================

latest_date = monthly["기준월"].max()

latest_year = latest_date.year
latest_month = latest_date.month

previous_year = latest_year - 1

print()
print("=" * 70)
print("최신 데이터 시점")
print("=" * 70)

print(
    f"{latest_year}년 {latest_month}월"
)


# ============================================================
# 12. 최신월 국가 Ranking
# ============================================================

latest = (
    monthly[
        monthly["기준월"] == latest_date
    ]
    .copy()
)

latest = latest.sort_values(
    "수출액_USD",
    ascending=False
)


# ============================================================
# 13. 전체 수출 대비 비중
# ============================================================

latest_total_export = latest[
    "수출액_USD"
].sum()

latest["전체수출대비_비중_%"] = (
    latest["수출액_USD"]
    /
    latest_total_export
    *
    100
)


# ============================================================
# 14. 최신월 Top 10
# ============================================================

latest_top10 = (
    latest
    .head(10)
    .copy()
)

latest_top10["순위"] = (
    range(
        1,
        len(latest_top10) + 1
    )
)

latest_top10 = latest_top10[
    [
        "순위",
        "국가코드",
        "국가",
        "수출액_십억달러",
        "YoY_%",
        "MoM_%",
        "전체수출대비_비중_%"
    ]
]


print()
print("=" * 70)
print("최신월 수출 상위 10개국")
print("=" * 70)

print(
    latest_top10.to_string(
        index=False
    )
)


# ============================================================
# 15. YTD 계산
# ============================================================

ytd_rows = []

for country in monthly["국가"].unique():

    item = monthly[
        monthly["국가"] == country
    ]

    current_ytd = item[
        (
            item["기준월"].dt.year
            ==
            latest_year
        )
        &
        (
            item["기준월"].dt.month
            <=
            latest_month
        )
    ]["수출액_USD"].sum()

    previous_ytd = item[
        (
            item["기준월"].dt.year
            ==
            previous_year
        )
        &
        (
            item["기준월"].dt.month
            <=
            latest_month
        )
    ]["수출액_USD"].sum()

    if previous_ytd != 0:
        ytd_yoy = (
            current_ytd
            /
            previous_ytd
            -
            1
        ) * 100
    else:
        ytd_yoy = np.nan

    country_code_series = item[
        "국가코드"
    ].dropna()

    country_code = (
        country_code_series.iloc[0]
        if not country_code_series.empty
        else ""
    )

    ytd_rows.append({
        "국가코드":
            country_code,

        "국가":
            country,

        "비교기간":
            f"1-{latest_month}월",

        f"{previous_year}_YTD_USD":
            previous_ytd,

        f"{latest_year}_YTD_USD":
            current_ytd,

        f"{previous_year}_YTD_bn":
            previous_ytd
            /
            1_000_000_000,

        f"{latest_year}_YTD_bn":
            current_ytd
            /
            1_000_000_000,

        "YTD_YoY_%":
            ytd_yoy,

        "YTD_증감액_bn":
            (
                current_ytd
                -
                previous_ytd
            )
            /
            1_000_000_000
    })


ytd = pd.DataFrame(
    ytd_rows
)

ytd = ytd.sort_values(
    f"{latest_year}_YTD_bn",
    ascending=False
)


# ============================================================
# 16. YTD 전체 대비 비중
# ============================================================

current_total_ytd = ytd[
    f"{latest_year}_YTD_USD"
].sum()

ytd["YTD_전체수출대비_비중_%"] = (
    ytd[
        f"{latest_year}_YTD_USD"
    ]
    /
    current_total_ytd
    *
    100
)


# ============================================================
# 17. YTD Top 10
# ============================================================

ytd_top10 = (
    ytd
    .head(10)
    .copy()
)

ytd_top10["순위"] = (
    range(
        1,
        len(ytd_top10) + 1
    )
)

ytd_top10 = ytd_top10[
    [
        "순위",
        "국가코드",
        "국가",
        "비교기간",
        f"{previous_year}_YTD_bn",
        f"{latest_year}_YTD_bn",
        "YTD_YoY_%",
        "YTD_증감액_bn",
        "YTD_전체수출대비_비중_%"
    ]
]


print()
print("=" * 70)
print(
    f"YTD 수출 상위 10개국 "
    f"({latest_year}년 1~{latest_month}월)"
)
print("=" * 70)

print(
    ytd_top10.to_string(
        index=False
    )
)


# ============================================================
# 18. CSV 저장
# ============================================================

raw.to_csv(
    "country_trade_raw.csv",
    index=False,
    encoding="utf-8-sig"
)

monthly.to_csv(
    "country_monthly.csv",
    index=False,
    encoding="utf-8-sig"
)

latest.to_csv(
    "country_latest.csv",
    index=False,
    encoding="utf-8-sig"
)

latest_top10.to_csv(
    "country_latest_top10.csv",
    index=False,
    encoding="utf-8-sig"
)

ytd.to_csv(
    "country_ytd.csv",
    index=False,
    encoding="utf-8-sig"
)

ytd_top10.to_csv(
    "country_ytd_top10.csv",
    index=False,
    encoding="utf-8-sig"
)


print()
print("=" * 70)
print("CSV 저장 완료")
print("=" * 70)

print("- country_trade_raw.csv")
print("- country_monthly.csv")
print("- country_latest.csv")
print("- country_latest_top10.csv")
print("- country_ytd.csv")
print("- country_ytd_top10.csv")