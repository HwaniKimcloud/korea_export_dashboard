from pathlib import Path
import time
import urllib.parse
import xml.etree.ElementTree as ET

import pandas as pd
import requests
import truststore


# ============================================================
# 0. SSL
# ============================================================

truststore.inject_into_ssl()


# ============================================================
# 1. 기본 경로 / 설정
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

TOTAL_FILE = BASE_DIR / "korea_total_export_monthly.csv"

# universe_gap_probe.py에서 이미 생성한 파일
HS_ALL_FILE = BASE_DIR / "universe_gap_202607_all_hsk.csv"

OUTPUT_RAW = BASE_DIR / "total_scope_gap_api_raw.csv"
OUTPUT_SUMMARY = BASE_DIR / "total_scope_gap_summary.csv"


# ============================================================
# 2. 관세청 Itemtrade API
# ============================================================

URL = "https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList"

# ------------------------------------------------------------
# 중요:
# universe_gap_probe.py에서 정상 작동한 동일한 API Key 입력
# ------------------------------------------------------------

SERVICE_KEY = "Jqr042WhXmRju%2F2E4uTPkTQqeJWPrWOjV2YRbdOkdF5B6QuZwyE5p1%2BJ1z1vLG6n2ZKpJBVejEavVIIWG8CrKQ%3D%3D"

SERVICE_KEY = urllib.parse.unquote(
    SERVICE_KEY
)


TARGET_YM = "202607"


# ============================================================
# 3. 유틸 함수
# ============================================================

def to_number(value):

    if value is None:
        return 0.0

    text = (
        str(value)
        .replace(",", "")
        .strip()
    )

    try:
        return float(text)

    except Exception:
        return 0.0


def get_text(item, names):

    for name in names:

        value = item.findtext(name)

        if value is not None:

            value = str(value).strip()

            if value != "":
                return value

    return None


# ============================================================
# 4. Itemtrade API를 HS 조건 없이 조회
# ============================================================

def fetch_itemtrade_without_hs(max_retry=3):

    params = {
        "serviceKey": SERVICE_KEY,
        "strtYymm": TARGET_YM,
        "endYymm": TARGET_YM,
    }

    for attempt in range(
        1,
        max_retry + 1
    ):

        try:

            print(
                f"Itemtrade 무품목 조회 "
                f"{attempt}/{max_retry} ..."
            )

            response = requests.get(
                URL,
                params=params,
                timeout=60
            )

            response.raise_for_status()

            print(
                f"HTTP Status : "
                f"{response.status_code}"
            )

            root = ET.fromstring(
                response.content
            )


            result_code = (
                root.findtext(".//resultCode")
                or
                root.findtext(
                    ".//returnReasonCode"
                )
            )

            result_msg = (
                root.findtext(".//resultMsg")
                or
                root.findtext(
                    ".//returnAuthMsg"
                )
            )


            print(
                f"Result Code : {result_code}"
            )

            print(
                f"Result Msg  : {result_msg}"
            )


            if result_code not in [
                None,
                "00",
                "0",
            ]:

                raise RuntimeError(
                    f"API ERROR "
                    f"{result_code}: "
                    f"{result_msg}"
                )


            rows = []


            for item in root.findall(
                ".//item"
            ):

                year_month = get_text(
                    item,
                    [
                        "year",
                        "yearMonth",
                        "balPayments",
                    ]
                )

                hs = get_text(
                    item,
                    [
                        "hsSgn",
                        "hsCd",
                        "hsCode",
                    ]
                )

                exp = get_text(
                    item,
                    [
                        "expDlr",
                        "expDollar",
                        "exportDlr",
                    ]
                )

                imp = get_text(
                    item,
                    [
                        "impDlr",
                        "impDollar",
                        "importDlr",
                    ]
                )


                rows.append(
                    {
                        "기준값": year_month,
                        "HS_raw": hs,
                        "수출액_USD": to_number(
                            exp
                        ),
                        "수입액_USD": to_number(
                            imp
                        ),
                    }
                )


            df = pd.DataFrame(
                rows
            )


            print(
                f"반환 item 수 : "
                f"{len(df):,}"
            )


            return df


        except Exception as e:

            print(
                f"[ERROR] {e}"
            )

            if attempt == max_retry:
                raise

            time.sleep(
                2 * attempt
            )


# ============================================================
# 5. 시작
# ============================================================

print()
print("=" * 100)
print("TOTAL EXPORT SCOPE GAP CHECK")
print("=" * 100)

print(
    f"기준월 : {TARGET_YM}"
)


# ============================================================
# 6. 기존 HS01~99 결과 읽기
# ============================================================

if not HS_ALL_FILE.exists():

    raise FileNotFoundError(
        "universe_gap_202607_all_hsk.csv "
        "파일을 찾지 못했습니다."
    )


hs_all = pd.read_csv(
    HS_ALL_FILE,
    dtype={
        "HSK10": str
    }
)


if "수출액_USD" not in hs_all.columns:

    raise RuntimeError(
        "universe_gap_202607_all_hsk.csv에 "
        "'수출액_USD' 열이 없습니다."
    )


hs_all[
    "수출액_USD"
] = pd.to_numeric(
    hs_all[
        "수출액_USD"
    ],
    errors="coerce"
).fillna(0)


hs_total = (
    hs_all[
        "수출액_USD"
    ]
    .sum()
)


print()
print("=" * 100)
print("STEP 1. HS01~99 기존 합계")
print("=" * 100)

print(
    f"활성 HSK10 : "
    f"{hs_all['HSK10'].nunique():,}"
)

print(
    f"HS01~99 합계 : "
    f"${hs_total / 1e9:,.9f}bn"
)


# ============================================================
# 7. 한국 전체수출 CSV 읽기
# ============================================================

if not TOTAL_FILE.exists():

    raise FileNotFoundError(
        "korea_total_export_monthly.csv "
        "파일을 찾지 못했습니다."
    )


total_df = pd.read_csv(
    TOTAL_FILE
)


print()
print("=" * 100)
print("STEP 2. TOTAL FILE 구조 확인")
print("=" * 100)

print(
    "컬럼:",
    list(
        total_df.columns
    )
)


# ------------------------------------------------------------
# 날짜 컬럼 자동 탐색
# ------------------------------------------------------------

date_candidates = [
    "기준월",
    "년월",
    "year_month",
    "month",
    "date",
    "Date",
]


date_col = None


for col in date_candidates:

    if col in total_df.columns:

        date_col = col
        break


# ------------------------------------------------------------
# 수출액 컬럼 자동 탐색
# ------------------------------------------------------------

export_candidates = [
    "수출액_USD",
    "수출금액",
    "export_usd",
    "export",
    "exports",
    "Export",
]


export_col = None


for col in export_candidates:

    if col in total_df.columns:

        export_col = col
        break


# ============================================================
# 8. 날짜 컬럼을 찾지 못했을 경우 보조 탐색
# ============================================================

if date_col is None:

    for col in total_df.columns:

        sample = (
            total_df[col]
            .astype(str)
            .head(20)
        )

        normalized = (
            sample
            .str.replace(
                "-",
                "",
                regex=False
            )
            .str.replace(
                "/",
                "",
                regex=False
            )
        )

        if normalized.str.contains(
            "202607",
            na=False
        ).any():

            date_col = col
            break


if export_col is None:

    for col in total_df.columns:

        col_text = str(col).lower()

        if (
            "수출" in str(col)
            or
            "export" in col_text
        ):

            export_col = col
            break


if date_col is None:

    raise RuntimeError(
        "korea_total_export_monthly.csv에서 "
        "기준월 컬럼을 자동으로 찾지 못했습니다."
    )


if export_col is None:

    raise RuntimeError(
        "korea_total_export_monthly.csv에서 "
        "수출액 컬럼을 자동으로 찾지 못했습니다."
    )


print(
    f"날짜 컬럼 : {date_col}"
)

print(
    f"수출 컬럼 : {export_col}"
)


# ============================================================
# 9. 202607 전체수출 추출
# ============================================================

temp_date = (
    total_df[
        date_col
    ]
    .astype(str)
    .str.replace(
        "-",
        "",
        regex=False
    )
    .str.replace(
        "/",
        "",
        regex=False
    )
    .str.replace(
        ".0",
        "",
        regex=False
    )
    .str.strip()
)


target_mask = (
    temp_date
    .str.contains(
        TARGET_YM,
        na=False
    )
)


target_total_rows = (
    total_df[
        target_mask
    ]
    .copy()
)


if target_total_rows.empty:

    print()
    print(
        "202607 행을 직접 찾지 못했습니다."
    )

    print(
        "TOTAL FILE 마지막 10행:"
    )

    print(
        total_df.tail(10)
        .to_string(
            index=False
        )
    )

    raise RuntimeError(
        "202607 전체수출 데이터를 "
        "찾지 못했습니다."
    )


target_total_rows[
    export_col
] = pd.to_numeric(
    target_total_rows[
        export_col
    ]
    .astype(str)
    .str.replace(
        ",",
        "",
        regex=False
    ),
    errors="coerce"
)


customs_total = (
    target_total_rows[
        export_col
    ]
    .dropna()
    .iloc[0]
)


# 단위 자동 보정
#
# 기존 데이터가 USD면 그대로,
# 천달러 단위라면 ×1000
#
# 2026년 7월 총수출은 약 990억달러이므로
# 1e9보다 지나치게 작으면 천달러로 간주

if customs_total < 1e9:

    customs_total = (
        customs_total
        * 1000
    )


print()
print("=" * 100)
print("STEP 3. 한국 전체수출")
print("=" * 100)

print(
    f"한국 전체수출 : "
    f"${customs_total / 1e9:,.9f}bn"
)


# ============================================================
# 10. Itemtrade API - hsSgn 없이 조회
# ============================================================

print()
print("=" * 100)
print("STEP 4. ITEMTRADE 무품목 조회")
print("=" * 100)


api_df = (
    fetch_itemtrade_without_hs()
)


api_df.to_csv(
    OUTPUT_RAW,
    index=False,
    encoding="utf-8-sig"
)


if api_df.empty:

    api_total = 0.0

else:

    api_total = (
        api_df[
            "수출액_USD"
        ]
        .sum()
    )


print()
print(
    f"Itemtrade 무품목 합계 : "
    f"${api_total / 1e9:,.9f}bn"
)


print()
print(
    "반환 원본:"
)

if api_df.empty:

    print(
        "반환 item 없음"
    )

else:

    print(
        api_df.head(30)
        .to_string(
            index=False
        )
    )


# ============================================================
# 11. 세 Universe 비교
# ============================================================

gap_total_vs_hs = (
    customs_total
    - hs_total
)


gap_total_vs_api = (
    customs_total
    - api_total
)


gap_api_vs_hs = (
    api_total
    - hs_total
)


print()
print("=" * 100)
print("FINAL SCOPE COMPARISON")
print("=" * 100)


print(
    f"A. 한국 전체수출         : "
    f"${customs_total / 1e9:,.9f}bn"
)

print(
    f"B. Itemtrade 무품목 합계 : "
    f"${api_total / 1e9:,.9f}bn"
)

print(
    f"C. HS01~99 합계          : "
    f"${hs_total / 1e9:,.9f}bn"
)


print()
print(
    f"A - C : "
    f"${gap_total_vs_hs / 1e6:,.3f}mn"
)

print(
    f"A - B : "
    f"${gap_total_vs_api / 1e6:,.3f}mn"
)

print(
    f"B - C : "
    f"${gap_api_vs_hs / 1e6:,.3f}mn"
)


# ============================================================
# 12. 자동 판정
# ============================================================

# 관세청 값은 정수 USD 기준일 수 있으므로
# $1,000 이내는 사실상 동일로 판단

TOLERANCE_USD = 1000


if abs(
    api_total
    - hs_total
) <= TOLERANCE_USD:

    diagnosis = (
        "CASE A: "
        "Itemtrade 무품목 합계와 HS01~99 합계가 동일. "
        "전체수출 통계와 Itemtrade 품목통계 사이의 "
        "집계범위 차이 가능성이 높음."
    )


elif abs(
    api_total
    - customs_total
) <= TOLERANCE_USD:

    diagnosis = (
        "CASE B: "
        "Itemtrade 무품목 합계와 한국 전체수출이 동일. "
        "HS01~99 개별 품목 조회에서 포착되지 않는 "
        "수출 항목이 존재할 가능성이 높음."
    )


else:

    diagnosis = (
        "CASE C: "
        "세 값이 서로 다름. "
        "Itemtrade 무품목 응답 구조 또는 "
        "전체수출/품목별 통계의 집계범위를 "
        "추가 확인해야 함."
    )


print()
print("=" * 100)
print("DIAGNOSIS")
print("=" * 100)

print(
    diagnosis
)


# ============================================================
# 13. Coverage 계산
# ============================================================

hs_coverage = (
    hs_total
    /
    customs_total
    *
    100
    if customs_total != 0
    else 0
)


api_coverage = (
    api_total
    /
    customs_total
    *
    100
    if customs_total != 0
    else 0
)


print()
print("=" * 100)
print("COVERAGE")
print("=" * 100)

print(
    f"HS01~99 / 전체수출 : "
    f"{hs_coverage:,.6f}%"
)

print(
    f"무품목 API / 전체수출 : "
    f"{api_coverage:,.6f}%"
)


# ============================================================
# 14. Summary 저장
# ============================================================

summary = pd.DataFrame(
    [
        {
            "기준월":
                TARGET_YM,

            "한국전체수출_USD":
                customs_total,

            "Itemtrade무품목_USD":
                api_total,

            "HS01_99합계_USD":
                hs_total,

            "전체수출_minus_HS_USD":
                gap_total_vs_hs,

            "전체수출_minus_API_USD":
                gap_total_vs_api,

            "API_minus_HS_USD":
                gap_api_vs_hs,

            "HS_Coverage_%":
                hs_coverage,

            "API_Coverage_%":
                api_coverage,

            "진단":
                diagnosis,
        }
    ]
)


summary.to_csv(
    OUTPUT_SUMMARY,
    index=False,
    encoding="utf-8-sig"
)


print()
print("=" * 100)
print("CSV 저장 완료")
print("=" * 100)

print(
    "- total_scope_gap_api_raw.csv"
)

print(
    "- total_scope_gap_summary.csv"
)


print()
print("=" * 100)
print("TOTAL SCOPE GAP CHECK COMPLETE")
print("=" * 100)