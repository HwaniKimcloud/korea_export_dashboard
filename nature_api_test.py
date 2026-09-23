# ============================================================
# nature_api_test.py
#
# 관세청 신성질별 수출입실적 API TEST
#
# 목표:
# 1. 신성질별 API 정상 호출 확인
# 2. 반도체 코드 34010000 조회
# 3. 2025.08 ~ 2026.08 월별 수출액 확인
# 4. 2026.08 반도체 수출액이 약 46.829bn USD인지 검증
# ============================================================

from pathlib import Path
import urllib.parse
import xml.etree.ElementTree as ET

import pandas as pd
import requests

import urllib3

urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)


# ============================================================
# 1. 기본 설정
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

URL = (
    "https://apis.data.go.kr/"
    "1220000/newtempertrade/getNewtempertradeList"
)

# ------------------------------------------------------------
# 관세청 공공데이터포털 일반 인증키
# Encoding 인증키를 그대로 입력
# requests 전달 전 한 번 decode
# ------------------------------------------------------------

SERVICE_KEY = (
    "Jqr042WhXmRju%2F2E4uTPkTQqeJWPrWOjV2YRbdOkdF5B6QuZwyE5p1%2BJ1z1vLG6n2ZKpJBVejEavVIIWG8CrKQ%3D%3D"
)

SERVICE_KEY = urllib.parse.unquote(SERVICE_KEY)


# ------------------------------------------------------------
# 조회 기간
# ------------------------------------------------------------

START_YM = "202509"
END_YM = "202608"


# ------------------------------------------------------------
# 수출입 구분
#
# 1 = 수출
# ------------------------------------------------------------

EXPORT_CODE = "1"


# ------------------------------------------------------------
# 신성질별 코드
#
# 34010000 = 반도체
# ------------------------------------------------------------

NATURE_CODE = "34010000"


# ------------------------------------------------------------
# 검증 대상 월
# ------------------------------------------------------------

TARGET_MONTH = "202608"


# ------------------------------------------------------------
# 2026년 8월 관세청 월간 수출입 현황 확정치
#
# 반도체 수출 = 46.829bn USD
# ------------------------------------------------------------

REFERENCE_USD = 46_829_000_000


# ------------------------------------------------------------
# 결과 저장 파일
# ------------------------------------------------------------

OUTPUT_RAW = BASE_DIR / "nature_api_34010000_raw.csv"


# ============================================================
# 2. 숫자 변환 함수
# ============================================================

def safe_float(value):
    if value is None:
        return 0.0

    value = str(value).strip().replace(",", "")

    if value == "":
        return 0.0

    try:
        return float(value)

    except ValueError:
        return 0.0


# ============================================================
# 3. XML 텍스트 추출 함수
# ============================================================

def get_text(item, tag):
    node = item.find(tag)

    if node is None:
        return ""

    return (node.text or "").strip()


# ============================================================
# 4. API 호출
# ============================================================

print("=" * 80)
print("CUSTOMS NEW NATURE API TEST")
print("=" * 80)

print()
print(f"조회 기간      : {START_YM} ~ {END_YM}")
print(f"수출입 구분    : {EXPORT_CODE} (수출)")
print(f"신성질 코드    : {NATURE_CODE}")
print(f"검증 대상 월   : {TARGET_MONTH}")
print()

params = {
    "serviceKey": SERVICE_KEY,
    "strtYymm": START_YM,
    "endYymm": END_YM,
    "imexTpcd": EXPORT_CODE,
    "imexTmprUnfcClsfCd": NATURE_CODE,
}


try:

    response = requests.get(
    URL,
    params=params,
    timeout=60,
    verify=False,
)

    print(f"HTTP STATUS    : {response.status_code}")
    print(f"REQUEST URL    : {response.url[:180]}...")
    print()

    response.raise_for_status()

except Exception as e:

    print("=" * 80)
    print("API REQUEST ERROR")
    print("=" * 80)
    print(type(e).__name__, ":", e)

    raise SystemExit(1)


# ============================================================
# 5. XML 파싱
# ============================================================

try:

    root = ET.fromstring(response.content)

except ET.ParseError as e:

    print("=" * 80)
    print("XML PARSE ERROR")
    print("=" * 80)

    print(e)

    print()
    print("RAW RESPONSE")
    print(response.text[:2000])

    raise SystemExit(1)


# ============================================================
# 6. API 결과 코드 확인
# ============================================================

result_code = root.findtext(".//resultCode", default="")
result_msg = root.findtext(".//resultMsg", default="")

print("=" * 80)
print("API RESULT")
print("=" * 80)

print(f"resultCode : {result_code}")
print(f"resultMsg  : {result_msg}")
print()


if result_code and result_code != "00":

    print("API가 정상 응답을 반환하지 않았습니다.")

    raise SystemExit(1)


# ============================================================
# 7. ITEM 추출
# ============================================================

items = root.findall(".//item")

print(f"수신 ITEM 수 : {len(items):,}")
print()


if len(items) == 0:

    print("=" * 80)
    print("NO DATA")
    print("=" * 80)

    print("조회 결과가 없습니다.")
    print()
    print("응답 앞부분:")
    print(response.text[:3000])

    raise SystemExit(1)


# ============================================================
# 8. 전체 태그 확인
# ============================================================

all_tags = set()

for item in items:
    for child in item:
        all_tags.add(child.tag)


print("=" * 80)
print("RESPONSE TAGS")
print("=" * 80)

for tag in sorted(all_tags):
    print(tag)

print()


# ============================================================
# 9. 데이터프레임 생성
# ============================================================

rows = []

for item in items:

    row = {}

    for child in item:

        row[child.tag] = (
            child.text.strip()
            if child.text
            else ""
        )

    rows.append(row)


df = pd.DataFrame(rows)


# ============================================================
# 10. 원본 CSV 저장
# ============================================================

df.to_csv(
    OUTPUT_RAW,
    index=False,
    encoding="utf-8-sig",
)

print("=" * 80)
print("RAW DATA SAVED")
print("=" * 80)

print(OUTPUT_RAW.name)
print()


# ============================================================
# 11. 주요 컬럼 자동 탐색
# ============================================================

# API 문서/응답 구조에 따라 필드명이 조금 다를 수 있으므로
# 후보 필드 가운데 실제 존재하는 컬럼을 자동 선택

month_candidates = [
    "year",
    "yearMonth",
    "yearMon",
    "yymm",
]

export_candidates = [
    "expDlr",
    "expUsd",
    "expAmt",
    "expDlrAmt",
]

code_candidates = [
    "imexTmprUnfcClsfCd",
    "godsCd",
]

name_candidates = [
    "imexTmprUnfcClsfNm",
    "godsKor",
]


def find_column(candidates):

    for col in candidates:

        if col in df.columns:
            return col

    return None


month_col = find_column(month_candidates)
export_col = find_column(export_candidates)
code_col = find_column(code_candidates)
name_col = find_column(name_candidates)


print("=" * 80)
print("COLUMN DETECTION")
print("=" * 80)

print(f"월 컬럼       : {month_col}")
print(f"수출액 컬럼   : {export_col}")
print(f"코드 컬럼     : {code_col}")
print(f"품목명 컬럼   : {name_col}")
print()


# ============================================================
# 12. 수출액 컬럼을 찾지 못했을 경우
# ============================================================

if export_col is None:

    print("=" * 80)
    print("EXPORT COLUMN NOT FOUND")
    print("=" * 80)

    print("현재 컬럼:")
    print(list(df.columns))

    print()
    print("첫 번째 데이터:")
    print(df.head().to_string(index=False))

    raise SystemExit(1)


# ============================================================
# 13. 숫자 변환
# ============================================================

df["_export_usd"] = (
    df[export_col]
    .apply(safe_float)
)


# ============================================================
# 14. 월 형식 정리
# ============================================================

if month_col is not None:

    df["_month"] = (
        df[month_col]
        .astype(str)
        .str.replace(".", "", regex=False)
        .str.replace("-", "", regex=False)
        .str.strip()
    )

else:

    df["_month"] = ""


# ============================================================
# 15. 월별 결과 출력
# ============================================================

print("=" * 80)
print("MONTHLY RESULT")
print("=" * 80)

display_cols = []

if month_col:
    display_cols.append(month_col)

if code_col:
    display_cols.append(code_col)

if name_col:
    display_cols.append(name_col)

display_cols.append(export_col)


temp = df[display_cols].copy()

temp["수출액_USD_bn"] = (
    df["_export_usd"] / 1_000_000_000
)


print(
    temp.to_string(
        index=False
    )
)

print()


# ============================================================
# 16. 2026.08 검증
# ============================================================

target = df[
    df["_month"] == TARGET_MONTH
].copy()


print("=" * 80)
print("2026.08 VALIDATION")
print("=" * 80)


if target.empty:

    print(
        f"{TARGET_MONTH} 데이터를 찾지 못했습니다."
    )

    print()
    print("확인된 월 값:")

    print(
        df["_month"]
        .drop_duplicates()
        .tolist()
    )

    raise SystemExit(1)


# 같은 월에 여러 행이 존재할 수도 있으므로 합산
actual_usd = target["_export_usd"].sum()

actual_bn = actual_usd / 1_000_000_000
reference_bn = REFERENCE_USD / 1_000_000_000

difference_usd = actual_usd - REFERENCE_USD
difference_bn = difference_usd / 1_000_000_000

difference_pct = (
    difference_usd / REFERENCE_USD * 100
    if REFERENCE_USD != 0
    else 0
)


print(
    f"API 반도체 수출액 : "
    f"${actual_bn:,.3f}bn"
)

print(
    f"관세청 확정치     : "
    f"${reference_bn:,.3f}bn"
)

print(
    f"차이              : "
    f"${difference_bn:,.6f}bn"
)

print(
    f"차이율            : "
    f"{difference_pct:+.6f}%"
)

print()


# ============================================================
# 17. PASS / CHECK 판정
# ============================================================

# 100만 달러 이내 차이면 PASS
tolerance_usd = 1_000_000


if abs(difference_usd) <= tolerance_usd:

    status = "PASS"

else:

    status = "CHECK"


print("=" * 80)
print("FINAL RESULT")
print("=" * 80)

print(f"Nature API Status : {status}")

if status == "PASS":

    print()
    print(
        "관세청 신성질별 API의 반도체 수출액이 "
        "2026년 8월 월간 수출입 현황 확정치와 일치합니다."
    )

else:

    print()
    print(
        "API 값과 확정치 사이에 차이가 있습니다."
    )

    print(
        "응답 필드 또는 신성질 코드 집계범위를 "
        "추가 확인해야 합니다."
    )


print()
print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)