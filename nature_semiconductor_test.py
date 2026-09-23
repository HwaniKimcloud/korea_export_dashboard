# ============================================================
# nature_semiconductor_test.py
#
# 관세청 신성질별 API
# 반도체(소분류 34010000) 하위 세세분류 전체 합산 TEST
#
# 목적
# 1. 관세청조회코드_v1.2.xlsx 에서 반도체 하위 leaf code 추출
# 2. leaf code별 신성질 수출실적 API 호출
# 3. 월별 합산
# 4. 2026.08 반도체 공식 확정치와 비교
# ============================================================

from __future__ import annotations

import os
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET

from pathlib import Path

import numpy as np
import pandas as pd
import requests
import urllib3

# ============================================================
# OPENPYXL PATCH
# 관세청 xlsx의 비정상 Custom Document Property 무시
# 실제 worksheet 데이터에는 영향 없음
# ============================================================

from openpyxl.packaging.custom import CustomPropertyList


def _ignore_broken_custom_properties(cls, node):
    return cls()


CustomPropertyList.from_tree = classmethod(
    _ignore_broken_custom_properties
)

# ============================================================
# 1. 기본 설정
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
INDUSTRY_DATA_DIR = BASE_DIR / "industry_data"

# ============================================================
# 인증키 - 직접 입력 방식
# ============================================================

SERVICE_KEY = (
    "Jqr042WhXmRju%2F2E4uTPkTQqeJWPrWOjV2YRbdOkdF5B6QuZwyE5p1%2BJ1z1vLG6n2ZKpJBVejEavVIIWG8CrKQ%3D%3D"
)

SERVICE_KEY = urllib.parse.unquote(
    SERVICE_KEY
)


# ============================================================
# 회사망 SSL 인증서 문제 우회
# ============================================================

VERIFY_SSL = False

urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)


# ------------------------------------------------------------
# 관세청 코드표
# ------------------------------------------------------------

EXCEL_CANDIDATES = [
    INDUSTRY_DATA_DIR / "관세청조회코드_v1.2.xlsx",
    BASE_DIR / "관세청조회코드_v1.2.xlsx",
]


# ------------------------------------------------------------
# API
# ------------------------------------------------------------

API_URL = (
    "https://apis.data.go.kr/"
    "1220000/newtempertrade/"
    "getNewtempertradeList"
)


# ------------------------------------------------------------
# 회사망 SSL 인증서 문제 우회
#
# 오늘 테스트용.
# 운영환경에서는 회사 CA 인증서 적용을 권장.
# ------------------------------------------------------------

VERIFY_SSL = False

urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)


# ------------------------------------------------------------
# 조회조건
#
# API는 시작~종료 기간이 1년 이내여야 함.
# YoY 확인을 위해 2025.09 ~ 2026.08 사용.
# ------------------------------------------------------------

START_YM = "202509"
END_YM = "202608"

IMEX_TPCD = "1"       # 1 = 수출


# ------------------------------------------------------------
# 반도체 신성질 소분류 코드
# ------------------------------------------------------------

TARGET_PARENT_CODE = "34010000"
TARGET_PARENT_NAME = "반도체"


# ------------------------------------------------------------
# 검증 기준
#
# 2026년 8월 관세청 확정치
# 약 46.829bn USD
# ------------------------------------------------------------

TARGET_MONTH = "202608"
REFERENCE_USD = 46_829_000_000


# ------------------------------------------------------------
# PASS 허용 오차
#
# 보도자료 반올림 등을 고려해 0.1bn = 1억달러
# ------------------------------------------------------------

TOLERANCE_USD = 100_000_000


# ------------------------------------------------------------
# 호출 간격
# ------------------------------------------------------------

REQUEST_SLEEP = 0.05


# ------------------------------------------------------------
# 출력 파일
# ------------------------------------------------------------

OUTPUT_LEAF_CODES = (
    BASE_DIR
    / "nature_semiconductor_leaf_codes.csv"
)

OUTPUT_RAW = (
    BASE_DIR
    / "nature_semiconductor_api_raw.csv"
)

OUTPUT_MONTHLY = (
    BASE_DIR
    / "nature_semiconductor_monthly.csv"
)

OUTPUT_STATUS = (
    BASE_DIR
    / "nature_semiconductor_collection_status.csv"
)


# ============================================================
# 2. Utility
# ============================================================

def clean_text(value) -> str:

    if pd.isna(value):
        return ""

    return (
        str(value)
        .replace("\ufeff", "")
        .replace("\u200b", "")
        .replace("\xa0", " ")
        .strip()
    )


def canonical(value) -> str:

    return (
        clean_text(value)
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
        .lower()
    )


def normalize_code(value) -> str:

    if pd.isna(value):
        return ""

    value = str(value).strip()

    if value.endswith(".0"):
        value = value[:-2]

    value = re.sub(
        r"[^0-9]",
        "",
        value,
    )

    return value


def safe_number(value):

    if value is None:
        return np.nan

    text = (
        str(value)
        .replace(",", "")
        .strip()
    )

    if text == "":
        return np.nan

    try:
        return float(text)

    except Exception:
        return np.nan


def find_col(
    df,
    candidates,
):

    cmap = {
        canonical(col): col
        for col in df.columns
    }

    # exact canonical
    for candidate in candidates:

        key = canonical(candidate)

        if key in cmap:
            return cmap[key]

    # partial
    for candidate in candidates:

        key = canonical(candidate)

        for canon_col, original in cmap.items():

            if (
                key in canon_col
                or
                canon_col in key
            ):
                return original

    return None


def parse_month(value):

    value = clean_text(value)

    digits = re.sub(
        r"[^0-9]",
        "",
        value,
    )

    if len(digits) >= 6:
        return digits[:6]

    return ""


# ============================================================
# 3. API KEY
# ============================================================

if not SERVICE_KEY:

    raise ValueError(
        "\nCUSTOMS_API_KEY가 없습니다.\n\n"
        "방법 1)\n"
        "Windows 환경변수 CUSTOMS_API_KEY를 설정하거나\n\n"
        "방법 2)\n"
        "코드 상단 SERVICE_KEY에 일반 인증키를 직접 입력하세요.\n"
    )


# Encoding 키가 들어온 경우 decode
SERVICE_KEY = urllib.parse.unquote(
    SERVICE_KEY
)


# ============================================================
# 4. Excel 자동 탐색
# ============================================================

excel_file = None

for candidate in EXCEL_CANDIDATES:

    if candidate.exists():

        excel_file = candidate
        break


if excel_file is None:

    raise FileNotFoundError(
        "관세청조회코드_v1.2.xlsx 파일을 찾지 못했습니다.\n"
        "아래 위치 중 하나에 저장하세요.\n\n"
        f"1) {INDUSTRY_DATA_DIR}\n"
        f"2) {BASE_DIR}"
    )


print()
print("=" * 100)
print("SEMICONDUCTOR NEW-NATURE API EXACT TEST")
print("=" * 100)

print(
    "코드표:",
    excel_file,
)

print(
    "대상:",
    TARGET_PARENT_CODE,
    TARGET_PARENT_NAME,
)

print(
    "기간:",
    START_YM,
    "~",
    END_YM,
)

print()

# ============================================================
# 5. Workbook / 신성질 분류 읽기
# ============================================================

xls = pd.ExcelFile(
    excel_file,
    engine="openpyxl",
)

print("=" * 100)
print("WORKBOOK SHEETS")
print("=" * 100)

for sheet in xls.sheet_names:
    print("-", sheet)

print()


# ============================================================
# 6. 성질통합분류코드
#
# 실제 Excel 구조:
# ROW 3 = header
# pandas header=3 사용
# ============================================================

SHEET_NAME = "성질통합분류코드"

df = pd.read_excel(
    excel_file,
    sheet_name=SHEET_NAME,
    header=3,
    engine="openpyxl",
)

df.columns = [
    clean_text(col)
    for col in df.columns
]


print("=" * 100)
print("CLASSIFICATION SHEET")
print("=" * 100)

print("사용 시트:", SHEET_NAME)
print("행 수:", len(df))
print("열 수:", len(df.columns))

print()


# ============================================================
# 7. 공식 컬럼 자동 탐색
# ============================================================

def find_official_column(
    dataframe,
    required_words,
):

    for col in dataframe.columns:

        normalized = (
            str(col)
            .replace(" ", "")
            .replace("\n", "")
            .replace("\t", "")
        )

        if all(
            word.replace(" ", "") in normalized
            for word in required_words
        ):
            return col

    return None


small_code_col = find_official_column(
    df,
    [
        "신성질별",
        "소분류",
        "코드",
    ],
)

small_name_col = find_official_column(
    df,
    [
        "신성질별",
        "소분류",
        "명",
    ],
)

detail_code_col = find_official_column(
    df,
    [
        "신성질별",
        "세세분류",
        "코드",
    ],
)

detail_name_col = find_official_column(
    df,
    [
        "신성질별",
        "세세분류",
        "명",
    ],
)


print("소분류코드 컬럼 :", small_code_col)
print("소분류명 컬럼   :", small_name_col)
print("세세분류코드 컬럼:", detail_code_col)
print("세세분류명 컬럼 :", detail_name_col)

print()


if small_code_col is None:
    raise RuntimeError(
        "신성질별 소분류코드 컬럼을 찾지 못했습니다."
    )

if detail_code_col is None:
    raise RuntimeError(
        "신성질별 세세분류코드 컬럼을 찾지 못했습니다."
    )


# ============================================================
# 8. 코드 정규화
# ============================================================

df["_SMALL_CODE"] = (
    df[small_code_col]
    .apply(normalize_code)
)

df["_DETAIL_CODE"] = (
    df[detail_code_col]
    .apply(normalize_code)
)


# ============================================================
# 9. 반도체(34010000) 행 추출
# ============================================================

semi = df[
    df["_SMALL_CODE"] == TARGET_PARENT_CODE
].copy()


print("=" * 100)
print("SEMICONDUCTOR ROWS")
print("=" * 100)

print(
    "반도체 관련 원본 행 수:",
    len(semi),
)

print()


if semi.empty:

    print("34010000을 찾지 못했습니다.")

    print()
    print("반도체 문자열 검색:")

    mask = df.astype(str).apply(
        lambda row:
        row.str.contains(
            "반도체",
            na=False,
        ).any(),
        axis=1,
    )

    print(
        df.loc[mask].head(30).to_string(
            index=False
        )
    )

    raise SystemExit(1)


# ============================================================
# 10. 반도체 하위 세세분류 Master
# ============================================================

semi = semi[
    semi["_DETAIL_CODE"] != ""
].copy()


leaf = pd.DataFrame(
    {
        "신성질코드":
            semi["_DETAIL_CODE"],

        "신성질품목명":
            (
                semi[detail_name_col]
                if detail_name_col is not None
                else ""
            ),
    }
)


leaf = (
    leaf
    .drop_duplicates(
        subset=[
            "신성질코드"
        ]
    )
    .sort_values(
        "신성질코드"
    )
    .reset_index(
        drop=True
    )
)


print("=" * 100)
print("SEMICONDUCTOR LEAF CODES")
print("=" * 100)

print(
    "반도체 하위 세세분류 코드 수:",
    len(leaf),
)

print()

print(
    leaf.to_string(
        index=False
    )
)

print()


leaf.to_csv(
    OUTPUT_LEAF_CODES,
    index=False,
    encoding="utf-8-sig",
)

# ============================================================
# 11. 신성질별 API 호출 함수
# ============================================================

def api_call(nature_code):

    params = {
        "serviceKey": SERVICE_KEY,
        "strtYymm": START_YM,
        "endYymm": END_YM,
        "imexTpcd": IMEX_TPCD,
        "imexTmprUnfcClsfCd": nature_code,
    }

    response = requests.get(
        API_URL,
        params=params,
        timeout=60,
        verify=VERIFY_SSL,
    )

    response.raise_for_status()

    root = ET.fromstring(
        response.content
    )

    result_code = root.findtext(
        ".//resultCode",
        default="",
    )

    result_msg = root.findtext(
        ".//resultMsg",
        default="",
    )

    if result_code != "00":

        return {
            "ok": False,
            "result_code": result_code,
            "result_msg": result_msg,
            "rows": [],
        }

    items = root.findall(
        ".//item"
    )

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

    return {
        "ok": True,
        "result_code": result_code,
        "result_msg": result_msg,
        "rows": rows,
    }


# ============================================================
# 12. 반도체 하위 10개 코드 API 수집
# ============================================================

all_frames = []
status_rows = []

total_codes = len(leaf)


print()
print("=" * 100)
print("API COLLECTION START")
print("=" * 100)


for idx, row in leaf.iterrows():

    code = str(
        row["신성질코드"]
    ).strip()

    name = str(
        row["신성질품목명"]
    ).strip()

    print(
        f"[{idx + 1:02d}/{total_codes:02d}] "
        f"{code} {name}"
    )

    try:

        result = api_call(
            code
        )

        if not result["ok"]:

            print(
                "   FAIL:",
                result["result_code"],
                result["result_msg"],
            )

            status_rows.append(
                {
                    "신성질코드": code,
                    "신성질품목명": name,
                    "상태": "API_ERROR",
                    "item수": 0,
                    "resultCode":
                        result["result_code"],
                    "resultMsg":
                        result["result_msg"],
                }
            )

            continue


        rows = result["rows"]

        print(
            f"   item: {len(rows)}"
        )


        status_rows.append(
            {
                "신성질코드": code,
                "신성질품목명": name,
                "상태": "OK",
                "item수": len(rows),
                "resultCode":
                    result["result_code"],
                "resultMsg":
                    result["result_msg"],
            }
        )


        if len(rows) > 0:

            temp = pd.DataFrame(
                rows
            )

            temp["_QUERY_CODE"] = code
            temp["_QUERY_NAME"] = name

            all_frames.append(
                temp
            )


    except Exception as exc:

        print(
            "   EXCEPTION:",
            type(exc).__name__,
            exc,
        )

        status_rows.append(
            {
                "신성질코드": code,
                "신성질품목명": name,
                "상태": "EXCEPTION",
                "item수": 0,
                "resultCode": "",
                "resultMsg": str(exc),
            }
        )


    time.sleep(
        REQUEST_SLEEP
    )


# ============================================================
# 13. 수집 상태 저장
# ============================================================

status_df = pd.DataFrame(
    status_rows
)

status_df.to_csv(
    OUTPUT_STATUS,
    index=False,
    encoding="utf-8-sig",
)


print()
print("=" * 100)
print("API COLLECTION SUMMARY")
print("=" * 100)

print(
    status_df.to_string(
        index=False
    )
)


# ============================================================
# 14. API 원본 통합
# ============================================================

if not all_frames:

    print()
    print("=" * 100)
    print("NO API DATA")
    print("=" * 100)

    print(
        "10개 반도체 세세분류에서 "
        "수집된 API 데이터가 없습니다."
    )

    raise SystemExit(1)


raw = pd.concat(
    all_frames,
    ignore_index=True,
)


raw.to_csv(
    OUTPUT_RAW,
    index=False,
    encoding="utf-8-sig",
)


print()
print("=" * 100)
print("API RAW DATA CREATED")
print("=" * 100)

print(
    "총 API 행 수:",
    f"{len(raw):,}",
)

print(
    "조회 코드 수:",
    raw["_QUERY_CODE"].nunique(),
)

print()


# ============================================================
# 11. 응답 구조 진단
# ============================================================

print()
print("=" * 100)
print("API RESPONSE COLUMNS")
print("=" * 100)

for col in raw.columns:

    print(
        "-",
        col,
    )

print()


# ============================================================
# 12. 월 / 금액 컬럼 탐색
# ============================================================

month_col = find_col(
    raw,
    [
        "year",
        "yymm",
        "yearMonth",
        "statYymm",
        "baseYymm",
    ],
)


amount_col = find_col(
    raw,
    [
        "expDlr",
        "expUsd",
        "expAmt",
        "expDlrAmt",
        "dlr",
        "usd",
        "tradeUsd",
        "amt",
    ],
)


if month_col is None:

    raise RuntimeError(
        "월 컬럼을 찾지 못했습니다.\n"
        f"응답 컬럼: {raw.columns.tolist()}"
    )


if amount_col is None:

    raise RuntimeError(
        "수출금액 컬럼을 찾지 못했습니다.\n"
        f"응답 컬럼: {raw.columns.tolist()}"
    )


print("=" * 100)
print("AUTO COLUMN DETECTION")
print("=" * 100)

print(
    "월 컬럼:",
    month_col,
)

print(
    "금액 컬럼:",
    amount_col,
)

print()


# ============================================================
# 13. 월 / 금액 정규화
# ============================================================

raw[
    "_YYYYMM"
] = (
    raw[
        month_col
    ]
    .apply(
        parse_month
    )
)


raw[
    "_EXPORT_USD"
] = (
    raw[
        amount_col
    ]
    .apply(
        safe_number
    )
)


raw[
    "_EXPORT_USD"
] = (
    raw[
        "_EXPORT_USD"
    ]
    .fillna(0)
)


# ============================================================
# 14. 월별 합산
# ============================================================

monthly = (
    raw[
        raw[
            "_YYYYMM"
        ]
        !=
        ""
    ]
    .groupby(
        "_YYYYMM",
        as_index=False,
    )
    .agg(
        수출액_USD=(
            "_EXPORT_USD",
            "sum",
        ),
        세세분류수=(
            "_QUERY_CODE",
            "nunique",
        ),
    )
    .sort_values(
        "_YYYYMM"
    )
    .reset_index(
        drop=True
    )
)


monthly[
    "수출액_bn"
] = (
    monthly[
        "수출액_USD"
    ]
    /
    1e9
)


monthly[
    "MoM_%"
] = (
    monthly[
        "수출액_USD"
    ]
    .pct_change()
    *
    100
)


# 12개월 범위만 가져왔으므로
# 2026.08 YoY는 2025.08이 없어서 직접 계산 불가.
# 오늘 테스트 핵심은 수출액 exact reconciliation.
monthly[
    "YoY_%"
] = np.nan


monthly.to_csv(
    OUTPUT_MONTHLY,
    index=False,
    encoding="utf-8-sig",
)


print()
print("=" * 100)
print("SEMICONDUCTOR MONTHLY RESULT")
print("=" * 100)

print(
    monthly.to_string(
        index=False
    )
)

print()


# ============================================================
# 15. 2026.08 검증
# ============================================================

target = monthly[
    monthly[
        "_YYYYMM"
    ]
    ==
    TARGET_MONTH
]


print("=" * 100)
print("2026.08 SEMICONDUCTOR VALIDATION")
print("=" * 100)


if target.empty:

    print(
        TARGET_MONTH,
        "데이터가 없습니다."
    )

    print(
        "확인 월:",
        monthly[
            "_YYYYMM"
        ].tolist(),
    )

    raise SystemExit(1)


actual_usd = float(
    target.iloc[0][
        "수출액_USD"
    ]
)


actual_bn = (
    actual_usd
    /
    1e9
)


# 여기 딱 한 군데에서 값을 정의
REFERENCE_USD = 46_669_844_000
reference_bn = REFERENCE_USD / 1e9

# 아래는 그 값을 가져다 쓰는 곳 → 수정 금지
difference_usd = actual_usd - REFERENCE_USD
difference_bn = difference_usd / 1e9
difference_pct = difference_usd / REFERENCE_USD * 100


print(
    f"API 합산값     : "
    f"${actual_bn:,.6f}bn"
)

print(
    f"공식 확정치    : "
    f"${reference_bn:,.6f}bn"
)

print(
    f"차이           : "
    f"${difference_bn:,.6f}bn"
)

print(
    f"차이 USD       : "
    f"${difference_usd:,.0f}"
)

print(
    f"차이율         : "
    f"{difference_pct:+.6f}%"
)

print()


# ============================================================
# 16. PASS 판단
# ============================================================

passed = (
    abs(
        difference_usd
    )
    <=
    TOLERANCE_USD
)


print("=" * 100)
print("FINAL RESULT")
print("=" * 100)


if passed:

    print(
        ">>> SEMICONDUCTOR NEW-NATURE RECONCILIATION : PASS <<<"
    )

else:

    print(
        ">>> SEMICONDUCTOR NEW-NATURE RECONCILIATION : REVIEW REQUIRED <<<"
    )


# ============================================================
# 17. 수집 상태 요약
# ============================================================

print()
print("=" * 100)
print("COLLECTION STATUS")
print("=" * 100)


summary = (
    status_df[
        "상태"
    ]
    .value_counts(
        dropna=False
    )
)


print(
    summary.to_string()
)


print()
print("=" * 100)
print("CSV 저장 완료")
print("=" * 100)

print(
    "-",
    OUTPUT_LEAF_CODES.name,
)

print(
    "-",
    OUTPUT_RAW.name,
)

print(
    "-",
    OUTPUT_MONTHLY.name,
)

print(
    "-",
    OUTPUT_STATUS.name,
)


print()
print("=" * 100)
print("TEST COMPLETE")
print("=" * 100)