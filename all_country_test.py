import truststore
truststore.inject_into_ssl()

import requests
import urllib.parse
import xml.etree.ElementTree as ET
import pandas as pd


# ============================================================
# 1. 기본 설정
# ============================================================

URL = "https://apis.data.go.kr/1220000/nationtrade/getNationtradeList"

SERVICE_KEY = "Jqr042WhXmRju%2F2E4uTPkTQqeJWPrWOjV2YRbdOkdF5B6QuZwyE5p1%2BJ1z1vLG6n2ZKpJBVejEavVIIWG8CrKQ%3D%3D"
SERVICE_KEY = urllib.parse.unquote(SERVICE_KEY)

START_YYMM = "202601"
END_YYMM = "202607"


# ============================================================
# 2. 국가코드 없이 API 호출
# ============================================================

params = {
    "serviceKey": SERVICE_KEY,
    "strtYymm": START_YYMM,
    "endYymm": END_YYMM

    # 중요:
    # cntyCd를 일부러 넣지 않습니다.
}


response = requests.get(
    URL,
    params=params,
    timeout=60
)


print()
print("=" * 80)
print("실제 요청 URL")
print("=" * 80)

print(response.url)


# ============================================================
# 3. XML 읽기
# ============================================================

root = ET.fromstring(
    response.text
)


result_code = root.findtext(
    ".//resultCode"
)

result_msg = root.findtext(
    ".//resultMsg"
)


print()
print("=" * 80)
print("API 상태")
print("=" * 80)

print(
    result_code,
    result_msg
)


# ============================================================
# 4. 반환된 item 구조 확인
# ============================================================

items = root.findall(
    ".//item"
)


print()
print("=" * 80)
print("총 item 수")
print("=" * 80)

print(len(items))


# ============================================================
# 5. 첫 번째 item의 모든 필드 확인
# ============================================================

if items:

    print()
    print("=" * 80)
    print("첫 번째 item의 XML 필드")
    print("=" * 80)

    for child in items[0]:

        print(
            child.tag,
            "=",
            child.text
        )


# ============================================================
# 6. 가능한 국가 필드 자동 탐색
# ============================================================

rows = []


for item in items:

    row = {}

    for child in item:

        row[child.tag] = child.text

    rows.append(row)


df = pd.DataFrame(
    rows
)


print()
print("=" * 80)
print("반환된 열 이름")
print("=" * 80)

print(
    df.columns.tolist()
)


# ============================================================
# 7. 앞 20개 행 출력
# ============================================================

print()
print("=" * 80)
print("앞 20개 데이터")
print("=" * 80)


if df.empty:

    print(
        "데이터가 없습니다."
    )

else:

    print(
        df.head(20).to_string(
            index=False
        )
    )


# ============================================================
# 8. 국가 관련 필드 후보 확인
# ============================================================

country_candidates = [
    col
    for col in df.columns
    if (
        "cnty" in col.lower()
        or
        "country" in col.lower()
        or
        "stat" in col.lower()
    )
]


print()
print("=" * 80)
print("국가 관련 필드 후보")
print("=" * 80)

print(
    country_candidates
)


# ============================================================
# 9. 간단 판정
# ============================================================

print()
print("=" * 80)
print("TEST 결과")
print("=" * 80)


if result_code != "00":

    print(
        ">>> 국가코드 없이 호출하는 방식은 "
        "허용되지 않는 것으로 보입니다."
    )

elif df.empty:

    print(
        ">>> 정상 응답이지만 "
        "전체 국가 데이터는 반환되지 않았습니다."
    )

else:

    print(
        ">>> 국가코드 없이도 데이터가 반환됐습니다."
    )

    print(
        ">>> 다음 단계에서 전체 국가 Ranking을 "
        "자동으로 만들 수 있는지 확인하면 됩니다."
    )