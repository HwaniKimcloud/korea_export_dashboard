import truststore
truststore.inject_into_ssl()

import requests
import urllib.parse
import xml.etree.ElementTree as ET
import pandas as pd


# ============================================================
# 1. 기본 설정
# ============================================================

URL = "https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList"

SERVICE_KEY = "Jqr042WhXmRju%2F2E4uTPkTQqeJWPrWOjV2YRbdOkdF5B6QuZwyE5p1%2BJ1z1vLG6n2ZKpJBVejEavVIIWG8CrKQ%3D%3D"
SERVICE_KEY = urllib.parse.unquote(SERVICE_KEY)

START_YYMM = "202601"
END_YYMM = "202607"


# ============================================================
# 2. API 호출 함수
# ============================================================

def call_api(country_code, hs_code=None):

    params = {
        "serviceKey": SERVICE_KEY,
        "strtYymm": START_YYMM,
        "endYymm": END_YYMM,
        "cntyCd": country_code
    }

    if hs_code is not None:
        params["hsSgn"] = hs_code


    response = requests.get(
        URL,
        params=params,
        timeout=60
    )

    print()
    print("=" * 80)
    print(
        f"국가={country_code} "
        f"/ HS={hs_code if hs_code else '미지정'}"
    )
    print("=" * 80)

    print("실제 요청 URL:")
    print(response.url)

    root = ET.fromstring(response.text)

    result_code = root.findtext(".//resultCode")
    result_msg = root.findtext(".//resultMsg")

    print()
    print(
        "API 상태:",
        result_code,
        result_msg
    )


    rows = []

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

        print("데이터 없음")

        return df


    for col in [
        "수출액_USD",
        "수입액_USD",
        "무역수지_USD"
    ]:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )


    print()
    print("총 행 수:", len(df))

    print(
        "수출액 합계:",
        f"${df['수출액_USD'].sum() / 1_000_000_000:,.3f}bn"
    )

    print()
    print("앞 10개 데이터:")

    print(
        df.head(10).to_string(
            index=False
        )
    )


    return df


# ============================================================
# 3. TEST A
# 국가코드만 사용
# ============================================================

print()
print("#" * 80)
print("TEST A : cntyCd만 사용")
print("#" * 80)

us_all = call_api(
    country_code="US"
)

cn_all = call_api(
    country_code="CN"
)


# ============================================================
# 4. TEST A 비교
# ============================================================

print()
print("=" * 80)
print("TEST A 결과 비교")
print("=" * 80)

us_all_total = (
    us_all["수출액_USD"].sum()
    if not us_all.empty
    else 0
)

cn_all_total = (
    cn_all["수출액_USD"].sum()
    if not cn_all.empty
    else 0
)


print(
    "미국 수출액:",
    f"${us_all_total / 1_000_000_000:,.3f}bn"
)

print(
    "중국 수출액:",
    f"${cn_all_total / 1_000_000_000:,.3f}bn"
)


if us_all_total == cn_all_total:

    print()
    print(
        ">>> 미국과 중국 결과가 동일합니다."
    )

    print(
        ">>> cntyCd 단독 필터가 "
        "적용되지 않았을 가능성이 높습니다."
    )

else:

    print()
    print(
        ">>> 미국과 중국 결과가 다릅니다."
    )

    print(
        ">>> cntyCd 국가 필터가 "
        "정상 작동할 가능성이 높습니다."
    )


# ============================================================
# 5. TEST B
# 국가코드 + HS 8542
# ============================================================

print()
print()
print("#" * 80)
print("TEST B : cntyCd + hsSgn=8542")
print("#" * 80)

us_8542 = call_api(
    country_code="US",
    hs_code="8542"
)

cn_8542 = call_api(
    country_code="CN",
    hs_code="8542"
)


# ============================================================
# 6. TEST B 비교
# ============================================================

print()
print("=" * 80)
print("TEST B 결과 비교")
print("=" * 80)

us_8542_total = (
    us_8542["수출액_USD"].sum()
    if not us_8542.empty
    else 0
)

cn_8542_total = (
    cn_8542["수출액_USD"].sum()
    if not cn_8542.empty
    else 0
)


print(
    "미국 HS8542 수출액:",
    f"${us_8542_total / 1_000_000_000:,.3f}bn"
)

print(
    "중국 HS8542 수출액:",
    f"${cn_8542_total / 1_000_000_000:,.3f}bn"
)


if us_8542_total == cn_8542_total:

    print()
    print(
        ">>> HS8542에서도 미국과 중국이 동일합니다."
    )

    print(
        ">>> cntyCd 파라미터 자체가 "
        "현재 API에서 무시되고 있을 가능성이 있습니다."
    )

else:

    print()
    print(
        ">>> HS8542에서는 미국과 중국 결과가 다릅니다."
    )

    print(
        ">>> 이 경우 국가 필터는 "
        "HS코드와 함께 사용할 때 정상 작동합니다."
    )