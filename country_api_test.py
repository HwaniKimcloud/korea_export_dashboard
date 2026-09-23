import truststore
truststore.inject_into_ssl()

import requests
import urllib.parse
import xml.etree.ElementTree as ET
import pandas as pd


# -------------------------------------------------
# 1. 기본 설정
# -------------------------------------------------

URL = "https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList"

SERVICE_KEY = "Jqr042WhXmRju%2F2E4uTPkTQqeJWPrWOjV2YRbdOkdF5B6QuZwyE5p1%2BJ1z1vLG6n2ZKpJBVejEavVIIWG8CrKQ%3D%3D"
SERVICE_KEY = urllib.parse.unquote(SERVICE_KEY)

COUNTRY_CODE = "US"


# -------------------------------------------------
# 2. API 호출 함수
# -------------------------------------------------

def get_country_data(start_yymm, end_yymm, country_code):

    params = {
        "serviceKey": SERVICE_KEY,
        "strtYymm": start_yymm,
        "endYymm": end_yymm,
        "cntyCd": country_code
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
        f"API 상태: {result_code} {result_msg}"
    )

    rows = []

    if result_code != "00":
        return pd.DataFrame()

    for item in root.findall(".//item"):

        rows.append({
            "기준월": item.findtext("year"),
            "HS코드": item.findtext("hsCode"),
            "품목명": item.findtext("statKor"),
            "수출액_USD": item.findtext("expDlr"),
            "수입액_USD": item.findtext("impDlr"),
            "무역수지_USD": item.findtext("balPayments")
        })

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    numeric_cols = [
        "수출액_USD",
        "수입액_USD",
        "무역수지_USD"
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    return df


# -------------------------------------------------
# 3. 2025년 데이터
# -------------------------------------------------

df_2025 = get_country_data(
    "202501",
    "202512",
    COUNTRY_CODE
)


# -------------------------------------------------
# 4. 2026년 데이터
# -------------------------------------------------

df_2026 = get_country_data(
    "202601",
    "202608",
    COUNTRY_CODE
)


# -------------------------------------------------
# 5. 데이터 합치기
# -------------------------------------------------

df = pd.concat(
    [df_2025, df_2026],
    ignore_index=True
)


# -------------------------------------------------
# 6. 결과 확인
# -------------------------------------------------

print()
print("총 데이터 행 수:", len(df))

print()
print(df.head(30).to_string(index=False))