import truststore
truststore.inject_into_ssl()

import requests
import urllib.parse
import xml.etree.ElementTree as ET
import pandas as pd

# -------------------------------------------------
# 1. 기본 설정
# -------------------------------------------------

url = "https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList"

SERVICE_KEY = "Jqr042WhXmRju%2F2E4uTPkTQqeJWPrWOjV2YRbdOkdF5B6QuZwyE5p1%2BJ1z1vLG6n2ZKpJBVejEavVIIWG8CrKQ%3D%3D"
SERVICE_KEY = urllib.parse.unquote(SERVICE_KEY)

HS_CODE = "8542"


# -------------------------------------------------
# 2. 관세청 API에서 데이터를 가져오는 함수
# -------------------------------------------------

def get_trade_data(start_yymm, end_yymm, hs_code):

    params = {
        "serviceKey": SERVICE_KEY,
        "strtYymm": start_yymm,
        "endYymm": end_yymm,
        "hsSgn": hs_code
    }

    response = requests.get(
        url,
        params=params,
        timeout=60
    )

    root = ET.fromstring(response.text)

    result_code = root.findtext(".//resultCode")
    result_msg = root.findtext(".//resultMsg")

    print(
        f"{start_yymm} ~ {end_yymm} API 상태:",
        result_code,
        result_msg
    )

    if result_code != "00":
        raise Exception(
            f"API 오류 발생: {result_code} / {result_msg}"
        )

    rows = []

    for item in root.findall(".//item"):

        rows.append({
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
# 3. 2025년 데이터 가져오기
# -------------------------------------------------

df_2025 = get_trade_data(
    "202501",
    "202512",
    HS_CODE
)


# -------------------------------------------------
# 4. 2026년 데이터 가져오기
# -------------------------------------------------

df_2026 = get_trade_data(
    "202601",
    "202608",
    HS_CODE
)


# -------------------------------------------------
# 5. 2025년 + 2026년 데이터 합치기
# -------------------------------------------------

df_raw = pd.concat(
    [df_2025, df_2026],
    ignore_index=True
)

print()
print("전체 원본 데이터 행 수:", len(df_raw))


# -------------------------------------------------
# 6. 기준월 형식 정리
# -------------------------------------------------

# "2025.01" 같은 실제 월 데이터만 남기고
# "총계" 등의 집계 행은 제외

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

# 날짜로 변환되지 않는 '총계' 등의 행 제거
invalid_rows = df_raw["기준월"].isna().sum()

print()
print("제외된 총계/비월별 행 수:", invalid_rows)

df_raw = df_raw.dropna(subset=["기준월"]).copy()

# -------------------------------------------------
# 7. 월별 HS 8542 수출액 합산
# -------------------------------------------------

monthly = (
    df_raw
    .groupby("기준월", as_index=False)
    ["수출액_USD"]
    .sum()
)


# -------------------------------------------------
# 8. 전년동월비 YoY 계산
# -------------------------------------------------

monthly = monthly.sort_values("기준월")

monthly["전년동월_수출액_USD"] = (
    monthly["수출액_USD"]
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


# -------------------------------------------------
# 9. 보기 좋은 단위 추가
# -------------------------------------------------

monthly["수출액_십억달러"] = (
    monthly["수출액_USD"]
    / 1_000_000_000
)


# -------------------------------------------------
# 10. 화면에 출력
# -------------------------------------------------

print()
print("===== HS 8542 월별 수출 =====")
print()

print(
    monthly[
        [
            "기준월",
            "수출액_USD",
            "수출액_십억달러",
            "YoY_%"
        ]
    ].to_string(
        index=False
    )
)


# -------------------------------------------------
# 11. YTD 누적 수출 비교
# -------------------------------------------------

# 현재 최신 데이터의 연도와 월 확인
latest_date = monthly["기준월"].max()

current_year = latest_date.year
latest_month = latest_date.month
previous_year = current_year - 1

print()
print("===== HS 8542 YTD 비교 =====")
print()
print(f"비교기간: 1~{latest_month}월")


# -------------------------------------------------
# 당해연도 YTD
# -------------------------------------------------

current_ytd = monthly[
    (monthly["기준월"].dt.year == current_year) &
    (monthly["기준월"].dt.month <= latest_month)
]["수출액_USD"].sum()


# -------------------------------------------------
# 전년도 동일기간 YTD
# -------------------------------------------------

previous_ytd = monthly[
    (monthly["기준월"].dt.year == previous_year) &
    (monthly["기준월"].dt.month <= latest_month)
]["수출액_USD"].sum()


# -------------------------------------------------
# YTD YoY 계산
# -------------------------------------------------

if previous_ytd != 0:
    ytd_yoy = (
        (current_ytd / previous_ytd) - 1
    ) * 100
else:
    ytd_yoy = None


# -------------------------------------------------
# 증감액 계산
# -------------------------------------------------

ytd_change = current_ytd - previous_ytd


# -------------------------------------------------
# 결과 출력
# -------------------------------------------------

print(
    f"{previous_year} YTD 수출액: "
    f"${previous_ytd / 1_000_000_000:,.2f}bn"
)

print(
    f"{current_year} YTD 수출액: "
    f"${current_ytd / 1_000_000_000:,.2f}bn"
)

if ytd_yoy is not None:
    print(
        f"YTD YoY: {ytd_yoy:+.1f}%"
    )

print(
    f"증감액: "
    f"${ytd_change / 1_000_000_000:+,.2f}bn"
)


# -------------------------------------------------
# YTD 결과를 표 형태로 만들기
# -------------------------------------------------

ytd_summary = pd.DataFrame({
    "구분": [
        f"{previous_year} 1-{latest_month}월",
        f"{current_year} 1-{latest_month}월"
    ],

    "수출액_USD": [
        previous_ytd,
        current_ytd
    ],

    "수출액_십억달러": [
        previous_ytd / 1_000_000_000,
        current_ytd / 1_000_000_000
    ]
})

ytd_summary["YoY_%"] = [
    None,
    ytd_yoy
]

print()
print(ytd_summary.to_string(index=False))

# -------------------------------------------------
# 12. CSV 파일 저장
# -------------------------------------------------

df_raw.to_csv(
    "trade_raw_8542.csv",
    index=False,
    encoding="utf-8-sig"
)

monthly.to_csv(
    "monthly_export_8542.csv",
    index=False,
    encoding="utf-8-sig"
)

ytd_summary.to_csv(
    "ytd_export_8542.csv",
    index=False,
    encoding="utf-8-sig"
)

print()
print("CSV 저장 완료")
print("- trade_raw_8542.csv")
print("- monthly_export_8542.csv")
print("- ytd_export_8542.csv")
