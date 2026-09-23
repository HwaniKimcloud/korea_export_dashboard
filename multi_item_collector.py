import truststore
truststore.inject_into_ssl()

import requests
import urllib.parse
import xml.etree.ElementTree as ET
import pandas as pd
import time


# -------------------------------------------------
# 1. 기본 설정
# -------------------------------------------------

URL = "https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList"

SERVICE_KEY = "Jqr042WhXmRju%2F2E4uTPkTQqeJWPrWOjV2YRbdOkdF5B6QuZwyE5p1%2BJ1z1vLG6n2ZKpJBVejEavVIIWG8CrKQ%3D%3D"
SERVICE_KEY = urllib.parse.unquote(SERVICE_KEY)


# -------------------------------------------------
# 2. 테스트할 주요 품목
# -------------------------------------------------
#
# 현재는 구조가 제대로 작동하는지 확인하기 위한
# 1차 품목 목록입니다.
#
# 향후 실제 리서치용 산업 정의는 별도로 정교화합니다.
# -------------------------------------------------

ITEMS = {
    "반도체": "8542",
    "승용차": "8703",
    "자동차부품": "8708",
    "선박": "8901"
}


# -------------------------------------------------
# 3. API 데이터 호출 함수
# -------------------------------------------------

def get_trade_data(start_yymm, end_yymm, hs_code, item_name):

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

    root = ET.fromstring(response.text)

    result_code = root.findtext(".//resultCode")
    result_msg = root.findtext(".//resultMsg")

    print(
        f"[{item_name}] "
        f"{start_yymm} ~ {end_yymm} : "
        f"{result_code} {result_msg}"
    )

    if result_code != "00":
        print(f"→ {item_name} 호출 실패")
        return pd.DataFrame()

    rows = []

    for item in root.findall(".//item"):

        rows.append({
            "대시보드품목": item_name,
            "조회HS": hs_code,
            "기준월": item.findtext("year"),
            "HS코드": item.findtext("hsCode"),
            "품목명": item.findtext("statKor"),
            "수출액_USD": item.findtext("expDlr"),
            "수입액_USD": item.findtext("impDlr"),
            "수출중량_KG": item.findtext("expWgt"),
            "수입중량_KG": item.findtext("impWgt"),
            "무역수지_USD": item.findtext("balPayments")
        })

    df = pd.DataFrame(rows)

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


# -------------------------------------------------
# 4. 여러 품목 데이터 수집
# -------------------------------------------------

all_data = []

for item_name, hs_code in ITEMS.items():

    print()
    print("=" * 60)
    print(f"{item_name} 데이터 수집 시작")
    print("=" * 60)

    df_2025 = get_trade_data(
        "202501",
        "202512",
        hs_code,
        item_name
    )

    time.sleep(0.3)

    df_2026 = get_trade_data(
        "202601",
        "202608",
        hs_code,
        item_name
    )

    if not df_2025.empty:
        all_data.append(df_2025)

    if not df_2026.empty:
        all_data.append(df_2026)

    time.sleep(0.3)


# -------------------------------------------------
# 5. 모든 품목 데이터 합치기
# -------------------------------------------------

if not all_data:
    raise Exception("수집된 데이터가 없습니다.")

df_raw = pd.concat(
    all_data,
    ignore_index=True
)

print()
print("전체 원본 데이터 행 수:", len(df_raw))


# -------------------------------------------------
# 6. 기준월 정리
# -------------------------------------------------

df_raw["기준월_원본"] = df_raw["기준월"].astype(str)

df_raw["기준월"] = (
    df_raw["기준월"]
    .astype(str)
    .str.replace(".", "", regex=False)
)

df_raw["기준월"] = pd.to_datetime(
    df_raw["기준월"],
    format="%Y%m",
    errors="coerce"
)

invalid_rows = df_raw["기준월"].isna().sum()

print("제외된 총계/비월별 행 수:", invalid_rows)

df_raw = (
    df_raw
    .dropna(subset=["기준월"])
    .copy()
)


# -------------------------------------------------
# 7. 품목별 월별 수출 합계
# -------------------------------------------------

monthly = (
    df_raw
    .groupby(
        ["대시보드품목", "조회HS", "기준월"],
        as_index=False
    )
    ["수출액_USD"]
    .sum()
)

monthly = monthly.sort_values(
    ["대시보드품목", "기준월"]
)


# -------------------------------------------------
# 8. 품목별 월간 YoY
# -------------------------------------------------

monthly["전년동월_수출액_USD"] = (
    monthly
    .groupby("대시보드품목")
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

monthly["수출액_십억달러"] = (
    monthly["수출액_USD"]
    / 1_000_000_000
)


# -------------------------------------------------
# 9. 월별 결과 출력
# -------------------------------------------------

print()
print("=" * 60)
print("주요 품목 월별 수출")
print("=" * 60)

print(
    monthly[
        [
            "대시보드품목",
            "기준월",
            "수출액_십억달러",
            "YoY_%"
        ]
    ]
    .tail(40)
    .to_string(index=False)
)


# -------------------------------------------------
# 10. 최신월 확인
# -------------------------------------------------

latest_date = monthly["기준월"].max()

current_year = latest_date.year
latest_month = latest_date.month
previous_year = current_year - 1

print()
print(
    f"현재 데이터 최신월: "
    f"{current_year}년 {latest_month}월"
)


# -------------------------------------------------
# 11. 품목별 YTD 계산
# -------------------------------------------------

ytd_rows = []

for item_name in ITEMS.keys():

    item_monthly = monthly[
        monthly["대시보드품목"] == item_name
    ]

    previous_ytd = item_monthly[
        (item_monthly["기준월"].dt.year == previous_year) &
        (item_monthly["기준월"].dt.month <= latest_month)
    ]["수출액_USD"].sum()

    current_ytd = item_monthly[
        (item_monthly["기준월"].dt.year == current_year) &
        (item_monthly["기준월"].dt.month <= latest_month)
    ]["수출액_USD"].sum()

    if previous_ytd != 0:
        ytd_yoy = (
            (current_ytd / previous_ytd) - 1
        ) * 100
    else:
        ytd_yoy = None

    ytd_change = current_ytd - previous_ytd

    ytd_rows.append({
        "품목": item_name,
        "비교기간": f"1-{latest_month}월",
        f"{previous_year}_YTD_USD": previous_ytd,
        f"{current_year}_YTD_USD": current_ytd,
        f"{previous_year}_YTD_bn": (
            previous_ytd / 1_000_000_000
        ),
        f"{current_year}_YTD_bn": (
            current_ytd / 1_000_000_000
        ),
        "YTD_YoY_%": ytd_yoy,
        "증감액_bn": (
            ytd_change / 1_000_000_000
        )
    })


ytd_summary = pd.DataFrame(ytd_rows)


# -------------------------------------------------
# 12. YTD 결과 출력
# -------------------------------------------------

print()
print("=" * 60)
print(
    f"주요 품목 YTD 비교 "
    f"({previous_year} vs {current_year}, "
    f"1~{latest_month}월)"
)
print("=" * 60)

print(
    ytd_summary.to_string(
        index=False
    )
)


# -------------------------------------------------
# 13. CSV 저장
# -------------------------------------------------

df_raw.to_csv(
    "trade_raw_all_items.csv",
    index=False,
    encoding="utf-8-sig"
)

monthly.to_csv(
    "monthly_export_all_items.csv",
    index=False,
    encoding="utf-8-sig"
)

ytd_summary.to_csv(
    "ytd_export_all_items.csv",
    index=False,
    encoding="utf-8-sig"
)

print()
print("CSV 저장 완료")
print("- trade_raw_all_items.csv")
print("- monthly_export_all_items.csv")
print("- ytd_export_all_items.csv")