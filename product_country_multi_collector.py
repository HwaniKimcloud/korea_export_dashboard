import truststore
truststore.inject_into_ssl()

import requests
import urllib.parse
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import time


# ============================================================
# 1. 기본 설정
# ============================================================

URL = "https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList"

SERVICE_KEY = "Jqr042WhXmRju%2F2E4uTPkTQqeJWPrWOjV2YRbdOkdF5B6QuZwyE5p1%2BJ1z1vLG6n2ZKpJBVejEavVIIWG8CrKQ%3D%3D"
SERVICE_KEY = urllib.parse.unquote(SERVICE_KEY)


# ============================================================
# 2. 대시보드용 주요 HS 품목
# ============================================================
#
# 앞으로 품목을 추가하고 싶으면
# 이 부분에 한 줄만 추가하면 됩니다.
#
# "표시명": "HS코드"
# ============================================================

PRODUCTS = {
    "전자집적회로": "8542",
    "반도체 제조장비": "8486",
    "승용차": "8703",
    "자동차부품": "8708",
    "선박": "8901"
}


# ============================================================
# 3. API 호출 함수
# ============================================================

def get_product_country_data(
    start_yymm,
    end_yymm,
    product_name,
    hs_code
):

    params = {
        "serviceKey": SERVICE_KEY,
        "strtYymm": start_yymm,
        "endYymm": end_yymm,
        "hsSgn": hs_code
    }

    response = requests.get(
        URL,
        params=params,
        timeout=60
    )

    root = ET.fromstring(
        response.text
    )

    result_code = root.findtext(
        ".//resultCode"
    )

    result_msg = root.findtext(
        ".//resultMsg"
    )

    print(
        f"[{product_name} / HS {hs_code}] "
        f"{start_yymm} ~ {end_yymm} "
        f": {result_code} {result_msg}"
    )

    if result_code != "00":
        return pd.DataFrame()

    rows = []

    for item in root.findall(".//item"):

        rows.append({
            "대시보드품목":
                product_name,

            "조회HS":
                hs_code,

            "국가코드":
                item.findtext("statCd"),

            "국가":
                item.findtext("statCdCntnKor1"),

            "기준월":
                item.findtext("year"),

            "HS코드":
                item.findtext("hsCd"),

            "품목명":
                item.findtext("statKor"),

            "수출액_USD":
                item.findtext("expDlr"),

            "수입액_USD":
                item.findtext("impDlr"),

            "수출중량_KG":
                item.findtext("expWgt"),

            "수입중량_KG":
                item.findtext("impWgt"),

            "무역수지_USD":
                item.findtext("balPayments")
        })

    df = pd.DataFrame(
        rows
    )

    if df.empty:
        return df

    numeric_cols = [
        "수출액_USD",
        "수입액_USD",
        "수출중량_KG",
        "수입중량_KG",
        "무역수지_USD"
    ]

    for col in numeric_cols:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    return df


# ============================================================
# 4. 모든 품목 수집
# ============================================================

all_data = []


print()
print("=" * 80)
print("Product × Country 다품목 데이터 수집")
print("=" * 80)


for product_name, hs_code in PRODUCTS.items():

    print()
    print("=" * 60)
    print(
        f"{product_name} / HS {hs_code}"
    )
    print("=" * 60)

    df_2025 = get_product_country_data(
        "202501",
        "202512",
        product_name,
        hs_code
    )

    time.sleep(0.3)

    df_2026 = get_product_country_data(
        "202601",
        "202608",
        product_name,
        hs_code
    )

    if not df_2025.empty:
        all_data.append(
            df_2025
        )

    if not df_2026.empty:
        all_data.append(
            df_2026
        )

    time.sleep(0.3)


if not all_data:

    raise Exception(
        "수집된 Product × Country 데이터가 없습니다."
    )


raw = pd.concat(
    all_data,
    ignore_index=True
)


print()
print(
    "전체 원본 데이터 행 수:",
    len(raw)
)


# ============================================================
# 5. 날짜 정리
# ============================================================

raw["기준월"] = (
    raw["기준월"]
    .astype(str)
    .str.replace(
        ".",
        "",
        regex=False
    )
)

raw["기준월"] = pd.to_datetime(
    raw["기준월"],
    format="%Y%m",
    errors="coerce"
)

invalid_date_rows = (
    raw["기준월"]
    .isna()
    .sum()
)

print(
    "제외된 비월별 행 수:",
    invalid_date_rows
)

raw = (
    raw
    .dropna(
        subset=["기준월"]
    )
    .copy()
)


# ============================================================
# 6. 국가 코드 / 국가명 정리
# ============================================================

raw["국가코드"] = (
    raw["국가코드"]
    .fillna("")
    .astype(str)
    .str.strip()
)

raw["국가"] = (
    raw["국가"]
    .fillna("")
    .astype(str)
    .str.strip()
)


# 국가 정보가 없는 총계/기타 행 제외
raw = raw[
    (raw["국가코드"] != "")
    &
    (raw["국가"] != "")
].copy()


print(
    "국가정보 정리 후 행 수:",
    len(raw)
)


# ============================================================
# 7. 품목 × 국가 × 월 집계
# ============================================================

monthly = (
    raw
    .groupby(
        [
            "대시보드품목",
            "조회HS",
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
        "대시보드품목",
        "국가",
        "기준월"
    ]
)


# ============================================================
# 8. YoY
# ============================================================

monthly["전년동월_수출액_USD"] = (
    monthly
    .groupby(
        [
            "대시보드품목",
            "국가"
        ]
    )
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
    .groupby(
        [
            "대시보드품목",
            "국가"
        ]
    )
    ["수출액_USD"]
    .pct_change()
    * 100
)


# ============================================================
# 10. 보기 좋은 단위
# ============================================================

monthly["수출액_십억달러"] = (
    monthly["수출액_USD"]
    /
    1_000_000_000
)


# ============================================================
# 11. 최신월
# ============================================================

latest_date = (
    monthly["기준월"]
    .max()
)

latest_year = (
    latest_date.year
)

latest_month = (
    latest_date.month
)

previous_year = (
    latest_year - 1
)


print()
print("=" * 80)
print("최신 데이터 시점")
print("=" * 80)

print(
    f"{latest_year}년 {latest_month}월"
)


# ============================================================
# 12. 최신월 전체 데이터
# ============================================================

latest = (
    monthly[
        monthly["기준월"]
        ==
        latest_date
    ]
    .copy()
)


# ============================================================
# 13. 품목별 최신월 총수출
# ============================================================

latest["품목총수출_USD"] = (
    latest
    .groupby(
        "대시보드품목"
    )
    ["수출액_USD"]
    .transform("sum")
)


latest[
    "품목수출대비_비중_%"
] = (
    latest["수출액_USD"]
    /
    latest["품목총수출_USD"]
    *
    100
)


# ============================================================
# 14. 품목별 최신월 Top 10
# ============================================================

latest_top10_list = []


for product in PRODUCTS.keys():

    item = latest[
        latest[
            "대시보드품목"
        ]
        ==
        product
    ].copy()

    item = item.sort_values(
        "수출액_USD",
        ascending=False
    ).head(10)

    item["순위"] = range(
        1,
        len(item) + 1
    )

    latest_top10_list.append(
        item
    )


latest_top10 = pd.concat(
    latest_top10_list,
    ignore_index=True
)


latest_top10 = latest_top10[
    [
        "대시보드품목",
        "조회HS",
        "순위",
        "국가코드",
        "국가",
        "수출액_십억달러",
        "YoY_%",
        "MoM_%",
        "품목수출대비_비중_%"
    ]
]


# ============================================================
# 15. 최신월 Top 10 화면 출력
# ============================================================

for product in PRODUCTS.keys():

    print()
    print("=" * 80)

    print(
        f"{latest_year}년 "
        f"{latest_month}월 "
        f"{product} "
        f"수출 상위 10개국"
    )

    print("=" * 80)

    tmp = latest_top10[
        latest_top10[
            "대시보드품목"
        ]
        ==
        product
    ]

    print(
        tmp.to_string(
            index=False
        )
    )


# ============================================================
# 16. YTD 계산
# ============================================================

ytd_rows = []


for product in PRODUCTS.keys():

    product_data = monthly[
        monthly[
            "대시보드품목"
        ]
        ==
        product
    ]

    for country in (
        product_data[
            "국가"
        ]
        .dropna()
        .unique()
    ):

        item = product_data[
            product_data["국가"]
            ==
            country
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


        country_code_series = (
            item["국가코드"]
            .dropna()
        )

        country_code = (
            country_code_series.iloc[0]
            if not country_code_series.empty
            else ""
        )


        hs_series = (
            item["조회HS"]
            .dropna()
        )

        hs_code = (
            hs_series.iloc[0]
            if not hs_series.empty
            else ""
        )


        ytd_rows.append({
            "대시보드품목":
                product,

            "조회HS":
                hs_code,

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


# ============================================================
# 17. 품목별 YTD 전체 수출
# ============================================================

ytd[
    "YTD_품목총수출_USD"
] = (
    ytd
    .groupby(
        "대시보드품목"
    )
    [
        f"{latest_year}_YTD_USD"
    ]
    .transform("sum")
)


ytd[
    "YTD_품목수출대비_비중_%"
] = (
    ytd[
        f"{latest_year}_YTD_USD"
    ]
    /
    ytd[
        "YTD_품목총수출_USD"
    ]
    *
    100
)


# ============================================================
# 18. 품목별 YTD Top 10
# ============================================================

ytd_top10_list = []


for product in PRODUCTS.keys():

    item = ytd[
        ytd[
            "대시보드품목"
        ]
        ==
        product
    ].copy()


    item = item.sort_values(
        f"{latest_year}_YTD_USD",
        ascending=False
    ).head(10)


    item["순위"] = range(
        1,
        len(item) + 1
    )


    ytd_top10_list.append(
        item
    )


ytd_top10 = pd.concat(
    ytd_top10_list,
    ignore_index=True
)


ytd_top10 = ytd_top10[
    [
        "대시보드품목",
        "조회HS",
        "순위",
        "국가코드",
        "국가",
        "비교기간",
        f"{previous_year}_YTD_bn",
        f"{latest_year}_YTD_bn",
        "YTD_YoY_%",
        "YTD_증감액_bn",
        "YTD_품목수출대비_비중_%"
    ]
]


# ============================================================
# 19. YTD Top 10 화면 출력
# ============================================================

for product in PRODUCTS.keys():

    print()
    print("=" * 80)

    print(
        f"{product} "
        f"YTD 수출 상위 10개국 "
        f"({latest_year}년 1~{latest_month}월)"
    )

    print("=" * 80)

    tmp = ytd_top10[
        ytd_top10[
            "대시보드품목"
        ]
        ==
        product
    ]

    print(
        tmp.to_string(
            index=False
        )
    )


# ============================================================
# 20. 품목 Master 생성
# ============================================================

product_master = pd.DataFrame(
    [
        {
            "대시보드품목":
                product_name,

            "HS":
                hs_code
        }

        for product_name, hs_code
        in PRODUCTS.items()
    ]
)


# ============================================================
# 21. CSV 저장
# ============================================================

raw.to_csv(
    "product_country_multi_raw.csv",
    index=False,
    encoding="utf-8-sig"
)


monthly.to_csv(
    "product_country_multi_monthly.csv",
    index=False,
    encoding="utf-8-sig"
)


latest.to_csv(
    "product_country_multi_latest.csv",
    index=False,
    encoding="utf-8-sig"
)


latest_top10.to_csv(
    "product_country_multi_latest_top10.csv",
    index=False,
    encoding="utf-8-sig"
)


ytd.to_csv(
    "product_country_multi_ytd.csv",
    index=False,
    encoding="utf-8-sig"
)


ytd_top10.to_csv(
    "product_country_multi_ytd_top10.csv",
    index=False,
    encoding="utf-8-sig"
)


product_master.to_csv(
    "product_master.csv",
    index=False,
    encoding="utf-8-sig"
)


print()
print("=" * 80)
print("CSV 저장 완료")
print("=" * 80)

print(
    "- product_country_multi_raw.csv"
)

print(
    "- product_country_multi_monthly.csv"
)

print(
    "- product_country_multi_latest.csv"
)

print(
    "- product_country_multi_latest_top10.csv"
)

print(
    "- product_country_multi_ytd.csv"
)

print(
    "- product_country_multi_ytd_top10.csv"
)

print(
    "- product_master.csv"
)