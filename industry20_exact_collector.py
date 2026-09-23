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
# 1. 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MAPPING_FILE = BASE_DIR / "official_mti20_master.csv"
KITA_REFERENCE_FILE = BASE_DIR / "industry_monthly.csv"

OUTPUT_RAW = BASE_DIR / "industry20_hsk_raw.csv"
OUTPUT_MONTHLY = BASE_DIR / "industry20_monthly.csv"
OUTPUT_LATEST = BASE_DIR / "industry20_latest.csv"
OUTPUT_YTD = BASE_DIR / "industry20_ytd.csv"
OUTPUT_RECON = BASE_DIR / "industry20_reconciliation.csv"
OUTPUT_STATUS = BASE_DIR / "industry20_collection_status.csv"


# ============================================================
# 2. 관세청 API
# ============================================================

URL = "https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList"

SERVICE_KEY = (
    "Jqr042WhXmRju%2F2E4uTPkTQqeJWPrWOjV2YRbdOkdF5B6QuZwyE5p1%2BJ1z1vLG6n2ZKpJBVejEavVIIWG8CrKQ%3D%3D"
)

SERVICE_KEY = urllib.parse.unquote(SERVICE_KEY)


# ============================================================
# 3. 조회 기간
# ============================================================

PERIODS = [
    ("202501", "202512"),
    ("202601", "202607"),
]


# ============================================================
# 4. 유틸 함수
# ============================================================

def normalize_code(value, length):

    if pd.isna(value):
        return None

    text = str(value).strip()

    if text.endswith(".0"):
        text = text[:-2]

    text = "".join(
        ch for ch in text
        if ch.isdigit()
    )

    if not text:
        return None

    return text.zfill(length)


def get_text(item, candidates):

    for tag in candidates:

        value = item.findtext(tag)

        if value is not None:

            value = str(value).strip()

            if value != "":
                return value

    return None


def to_number(value):

    if value is None:
        return 0.0

    text = (
        str(value)
        .replace(",", "")
        .strip()
    )

    if text == "":
        return 0.0

    try:
        return float(text)

    except Exception:
        return 0.0


def normalize_ym(value):

    if value is None:
        return None

    text = (
        str(value)
        .replace(".", "")
        .replace("-", "")
        .replace("/", "")
        .strip()
    )

    digits = "".join(
        ch for ch in text
        if ch.isdigit()
    )

    if len(digits) >= 6:
        digits = digits[:6]

    if (
        len(digits) == 6
        and digits.isdigit()
    ):
        return digits

    return None


# ============================================================
# 5. 관세청 API 호출
#
# hs_prefix에는 HS2를 넣음
# 예: 85
#
# 응답 안에서는 HSK10 코드를 다시 추출
# ============================================================

def fetch_prefix(
    hs_prefix,
    start_ym,
    end_ym,
    max_retry=3
):

    params = {
        "serviceKey": SERVICE_KEY,
        "strtYymm": start_ym,
        "endYymm": end_ym,
        "hsSgn": hs_prefix,
    }

    last_error = None

    for attempt in range(
        1,
        max_retry + 1
    ):

        try:

            response = requests.get(
                URL,
                params=params,
                timeout=60
            )

            response.raise_for_status()

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
                or ""
            )


            if result_code not in [
                None,
                "00",
                "0"
            ]:

                raise RuntimeError(
                    f"API 오류 "
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
                        "period",
                        "baseYm",
                        "yymm",
                    ]
                )

                hs_code = get_text(
                    item,
                    [
                        "hsSgn",
                        "hsCd",
                        "hsCode",
                    ]
                )

                export_value = get_text(
                    item,
                    [
                        "expDlr",
                        "expDollar",
                        "exportDlr",
                    ]
                )


                ym = normalize_ym(
                    year_month
                )

                hsk10 = normalize_code(
                    hs_code,
                    10
                )


                if ym is None:
                    continue

                if hsk10 is None:
                    continue


                rows.append(
                    {
                        "기준월": ym,
                        "HSK10": hsk10,
                        "수출액_USD": to_number(
                            export_value
                        ),
                        "조회_HS2": hs_prefix,
                    }
                )


            return pd.DataFrame(
                rows
            )


        except Exception as e:

            last_error = e

            if attempt < max_retry:

                time.sleep(
                    2 * attempt
                )


    print(
        f"[FAIL] "
        f"HS2={hs_prefix} "
        f"{start_ym}~{end_ym} "
        f"{last_error}"
    )

    return pd.DataFrame()


# ============================================================
# 6. 공식 20대 산업 Master 읽기
# ============================================================

if not MAPPING_FILE.exists():

    raise FileNotFoundError(
        f"파일을 찾을 수 없습니다:\n"
        f"{MAPPING_FILE}"
    )


mapping = pd.read_csv(
    MAPPING_FILE,
    dtype=str
)


required_columns = [
    "HSK10",
    "MTI6",
    "산업20",
]


for col in required_columns:

    if col not in mapping.columns:

        raise ValueError(
            f"필수 컬럼 없음: {col}"
        )


mapping["HSK10"] = (
    mapping["HSK10"]
    .apply(
        lambda x:
        normalize_code(
            x,
            10
        )
    )
)


mapping["MTI6"] = (
    mapping["MTI6"]
    .apply(
        lambda x:
        normalize_code(
            x,
            6
        )
    )
)


mapping = mapping[
    mapping["HSK10"].notna()
    &
    mapping["산업20"].notna()
].copy()


mapping["산업20"] = (
    mapping["산업20"]
    .astype(str)
    .str.strip()
)


mapping["HS2"] = (
    mapping["HSK10"]
    .str[:2]
)


# ============================================================
# 7. Master 기본 상태
# ============================================================

industries = sorted(
    mapping["산업20"]
    .unique()
)


hs2_list = sorted(
    mapping["HS2"]
    .dropna()
    .unique()
)


print()
print("=" * 100)
print("KOREA 20 INDUSTRY EXACT COLLECTOR")
print("=" * 100)

print(
    f"20대 산업 수      : "
    f"{len(industries)}"
)

print(
    f"공식 HSK10 수     : "
    f"{mapping['HSK10'].nunique():,}"
)

print(
    f"공식 MTI6 수      : "
    f"{mapping['MTI6'].nunique():,}"
)

print(
    f"조회 HS2 수       : "
    f"{len(hs2_list)}"
)


print()
print("산업 목록")

for idx, industry in enumerate(
    industries,
    start=1
):

    print(
        f"{idx:>2}. {industry}"
    )


# ============================================================
# 8. 관세청 데이터 수집
# ============================================================

total_requests = (
    len(hs2_list)
    *
    len(PERIODS)
)


print()
print("=" * 100)
print("관세청 데이터 수집")
print("=" * 100)

print(
    f"총 API 호출 예정 : "
    f"{total_requests:,}"
)


all_frames = []
status_rows = []

request_no = 0


for hs2 in hs2_list:

    for start_ym, end_ym in PERIODS:

        request_no += 1


        print(
            f"[{request_no:>3}/"
            f"{total_requests}] "
            f"HS2 {hs2} "
            f"{start_ym}~{end_ym}"
        )


        temp = fetch_prefix(
            hs2,
            start_ym,
            end_ym
        )


        status_rows.append(
            {
                "HS2": hs2,
                "시작월": start_ym,
                "종료월": end_ym,
                "반환행수": len(temp),
                "고유HSK10": (
                    temp["HSK10"]
                    .nunique()
                    if not temp.empty
                    else 0
                ),
                "상태": (
                    "OK"
                    if not temp.empty
                    else "EMPTY"
                ),
            }
        )


        if not temp.empty:

            all_frames.append(
                temp
            )


        time.sleep(0.1)


status_df = pd.DataFrame(
    status_rows
)


status_df.to_csv(
    OUTPUT_STATUS,
    index=False,
    encoding="utf-8-sig"
)


if not all_frames:

    raise RuntimeError(
        "관세청에서 데이터를 "
        "가져오지 못했습니다."
    )


# ============================================================
# 9. API Raw 합치기
# ============================================================

raw_api = pd.concat(
    all_frames,
    ignore_index=True
)


raw_api = (
    raw_api
    .groupby(
        [
            "기준월",
            "HSK10"
        ],
        as_index=False
    )
    .agg(
        수출액_USD=(
            "수출액_USD",
            "sum"
        )
    )
)


print()
print("=" * 100)
print("API RAW SUMMARY")
print("=" * 100)

print(
    f"Raw 행 수         : "
    f"{len(raw_api):,}"
)

print(
    f"Raw 고유 HSK10    : "
    f"{raw_api['HSK10'].nunique():,}"
)


# ============================================================
# 10. 공식 Mapping과 JOIN
# ============================================================

merged = raw_api.merge(
    mapping[
        [
            "HSK10",
            "MTI6",
            "산업20"
        ]
    ],
    on="HSK10",
    how="inner",
    validate="many_to_one"
)


print()
print("=" * 100)
print("OFFICIAL MAPPING JOIN")
print("=" * 100)

print(
    f"JOIN 행 수        : "
    f"{len(merged):,}"
)

print(
    f"JOIN HSK10 수     : "
    f"{merged['HSK10'].nunique():,}"
)

print(
    f"JOIN MTI6 수      : "
    f"{merged['MTI6'].nunique():,}"
)

print(
    f"JOIN 산업 수      : "
    f"{merged['산업20'].nunique()}"
)


# ============================================================
# 11. 기준월 Date 변환
# ============================================================

merged["기준월"] = pd.to_datetime(
    merged["기준월"],
    format="%Y%m"
)


merged.to_csv(
    OUTPUT_RAW,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 12. 20대 산업 월별 수출
# ============================================================

monthly = (
    merged
    .groupby(
        [
            "기준월",
            "산업20"
        ],
        as_index=False
    )
    .agg(
        수출액_USD=(
            "수출액_USD",
            "sum"
        ),
        HSK10_활성수=(
            "HSK10",
            "nunique"
        ),
        MTI6_활성수=(
            "MTI6",
            "nunique"
        )
    )
    .sort_values(
        [
            "산업20",
            "기준월"
        ]
    )
    .reset_index(drop=True)
)


monthly[
    "수출액_십억달러"
] = (
    monthly[
        "수출액_USD"
    ]
    / 1e9
)


monthly["YoY_%"] = (
    monthly
    .groupby(
        "산업20"
    )["수출액_USD"]
    .pct_change(12)
    * 100
)


monthly["MoM_%"] = (
    monthly
    .groupby(
        "산업20"
    )["수출액_USD"]
    .pct_change(1)
    * 100
)


# ============================================================
# 13. 최근 3개월 YoY 평균
# ============================================================

monthly["3M_YoY_%"] = (
    monthly
    .groupby(
        "산업20"
    )["YoY_%"]
    .transform(
        lambda x:
        x.rolling(
            3,
            min_periods=1
        ).mean()
    )
)


monthly["Momentum_Gap_pp"] = (
    monthly["YoY_%"]
    -
    monthly["3M_YoY_%"]
)


monthly.to_csv(
    OUTPUT_MONTHLY,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 14. 최신월
# ============================================================

latest_month = (
    monthly["기준월"]
    .max()
)


latest = (
    monthly[
        monthly["기준월"]
        ==
        latest_month
    ]
    .copy()
    .sort_values(
        "수출액_USD",
        ascending=False
    )
    .reset_index(drop=True)
)


latest[
    "순위"
] = (
    latest.index + 1
)


latest = latest[
    [
        "순위",
        "산업20",
        "기준월",
        "수출액_USD",
        "수출액_십억달러",
        "YoY_%",
        "MoM_%",
        "3M_YoY_%",
        "Momentum_Gap_pp",
        "HSK10_활성수",
        "MTI6_활성수",
    ]
]


latest.to_csv(
    OUTPUT_LATEST,
    index=False,
    encoding="utf-8-sig"
)


print()
print("=" * 100)
print("LATEST MONTH")
print("=" * 100)

print(
    latest_month.strftime(
        "%Y년 %m월"
    )
)


print()
print(
    latest[
        [
            "순위",
            "산업20",
            "수출액_십억달러",
            "YoY_%",
            "MoM_%",
            "3M_YoY_%",
        ]
    ]
    .to_string(
        index=False
    )
)


# ============================================================
# 15. YTD 계산
# ============================================================

latest_year = (
    latest_month.year
)

latest_month_num = (
    latest_month.month
)

previous_year = (
    latest_year - 1
)


current_ytd = monthly[
    (
        monthly["기준월"].dt.year
        ==
        latest_year
    )
    &
    (
        monthly["기준월"].dt.month
        <=
        latest_month_num
    )
].copy()


previous_ytd = monthly[
    (
        monthly["기준월"].dt.year
        ==
        previous_year
    )
    &
    (
        monthly["기준월"].dt.month
        <=
        latest_month_num
    )
].copy()


current_ytd = (
    current_ytd
    .groupby(
        "산업20",
        as_index=False
    )
    .agg(
        현재YTD_USD=(
            "수출액_USD",
            "sum"
        )
    )
)


previous_ytd = (
    previous_ytd
    .groupby(
        "산업20",
        as_index=False
    )
    .agg(
        전년YTD_USD=(
            "수출액_USD",
            "sum"
        )
    )
)


ytd = current_ytd.merge(
    previous_ytd,
    on="산업20",
    how="left"
)


ytd["YTD_YoY_%"] = (
    (
        ytd["현재YTD_USD"]
        /
        ytd["전년YTD_USD"]
    )
    - 1
) * 100


ytd["현재YTD_bn"] = (
    ytd["현재YTD_USD"]
    / 1e9
)


ytd["전년YTD_bn"] = (
    ytd["전년YTD_USD"]
    / 1e9
)


ytd["YTD_증감액_bn"] = (
    (
        ytd["현재YTD_USD"]
        -
        ytd["전년YTD_USD"]
    )
    / 1e9
)


ytd = (
    ytd
    .sort_values(
        "현재YTD_USD",
        ascending=False
    )
    .reset_index(drop=True)
)


ytd["순위"] = (
    ytd.index + 1
)


ytd.to_csv(
    OUTPUT_YTD,
    index=False,
    encoding="utf-8-sig"
)


print()
print("=" * 100)
print("20대 산업 YTD")
print("=" * 100)

print(
    ytd[
        [
            "순위",
            "산업20",
            "현재YTD_bn",
            "전년YTD_bn",
            "YTD_YoY_%",
            "YTD_증감액_bn",
        ]
    ]
    .to_string(
        index=False
    )
)


# ============================================================
# 16. 기존 KITA Reference와 Exact Reconciliation
#
# 현재 industry_monthly.csv에 존재하는 산업만 자동 검증.
# 향후 20개 Reference를 확보하면 동일 코드로 전부 검증 가능.
# ============================================================

recon_frames = []


if KITA_REFERENCE_FILE.exists():

    kita = pd.read_csv(
        KITA_REFERENCE_FILE
    )


    if (
        "기준월" in kita.columns
        and
        "산업" in kita.columns
    ):

        kita["기준월"] = pd.to_datetime(
            kita["기준월"]
        )


        exact_candidates = [
            "수출액_USD",
            "수출액_달러",
            "수출액",
        ]


        exact_col = None

        for col in exact_candidates:

            if col in kita.columns:

                exact_col = col
                break


        if exact_col is not None:

            kita[
                "KITA_공식_USD"
            ] = pd.to_numeric(
                kita[exact_col],
                errors="coerce"
            )


            # 기존 산업명에서 코드 괄호 제거
            # 예: 반도체 (831) -> 반도체
            kita["산업20"] = (
                kita["산업"]
                .astype(str)
                .str.replace(
                    r"\s*\([^)]*\)\s*$",
                    "",
                    regex=True
                )
                .str.strip()
            )


            recon = monthly.merge(
                kita[
                    [
                        "기준월",
                        "산업20",
                        "KITA_공식_USD"
                    ]
                ],
                on=[
                    "기준월",
                    "산업20"
                ],
                how="inner"
            )


            if not recon.empty:

                recon[
                    "관세청_천USD"
                ] = (
                    recon[
                        "수출액_USD"
                    ]
                    / 1000
                ).round().astype(
                    "Int64"
                )


                recon[
                    "KITA_천USD"
                ] = (
                    recon[
                        "KITA_공식_USD"
                    ]
                    / 1000
                ).round().astype(
                    "Int64"
                )


                recon[
                    "차이_천USD"
                ] = (
                    recon[
                        "관세청_천USD"
                    ]
                    -
                    recon[
                        "KITA_천USD"
                    ]
                )


                recon[
                    "원자료_차이_USD"
                ] = (
                    recon[
                        "수출액_USD"
                    ]
                    -
                    recon[
                        "KITA_공식_USD"
                    ]
                )


                recon[
                    "Exact_PASS"
                ] = (
                    recon[
                        "차이_천USD"
                    ]
                    == 0
                )


                recon.to_csv(
                    OUTPUT_RECON,
                    index=False,
                    encoding="utf-8-sig"
                )


                # 산업별 검증 요약
                recon_summary = (
                    recon
                    .groupby(
                        "산업20",
                        as_index=False
                    )
                    .agg(
                        비교월수=(
                            "기준월",
                            "count"
                        ),
                        PASS월수=(
                            "Exact_PASS",
                            "sum"
                        ),
                        최대절대차이_USD=(
                            "원자료_차이_USD",
                            lambda x:
                            x.abs().max()
                        ),
                    )
                )


                recon_summary[
                    "Exact_ALL_PASS"
                ] = (
                    recon_summary[
                        "비교월수"
                    ]
                    ==
                    recon_summary[
                        "PASS월수"
                    ]
                )


                print()
                print("=" * 100)
                print(
                    "KITA EXACT "
                    "RECONCILIATION"
                )
                print("=" * 100)


                print(
                    recon_summary
                    .to_string(
                        index=False
                    )
                )


                all_pass = (
                    recon_summary[
                        "Exact_ALL_PASS"
                    ]
                    .all()
                )


                print()

                if all_pass:

                    print(
                        "AVAILABLE KITA "
                        "REFERENCE : "
                        "ALL EXACT PASS"
                    )

                else:

                    print(
                        "KITA RECONCILIATION : "
                        "REVIEW REQUIRED"
                    )


# ============================================================
# 17. 최종 무결성 Check
# ============================================================

print()
print("=" * 100)
print("FINAL INTEGRITY CHECK")
print("=" * 100)


industry_count = (
    latest["산업20"]
    .nunique()
)


print(
    f"최신월 산업 수 : "
    f"{industry_count}"
)


if industry_count == 20:

    print(
        "20대 산업 월별 집계 : PASS"
    )

else:

    print(
        "20대 산업 월별 집계 : "
        "REVIEW REQUIRED"
    )


# 반도체 결과 재확인
semi_check = latest[
    latest["산업20"]
    ==
    "반도체"
]


if not semi_check.empty:

    value = (
        semi_check.iloc[0][
            "수출액_십억달러"
        ]
    )

    print(
        f"최신월 반도체 : "
        f"${value:.6f}bn"
    )


# ============================================================
# 18. 저장 안내
# ============================================================

print()
print("=" * 100)
print("CSV 저장 완료")
print("=" * 100)

print(
    "- industry20_hsk_raw.csv"
)

print(
    "- industry20_monthly.csv"
)

print(
    "- industry20_latest.csv"
)

print(
    "- industry20_ytd.csv"
)

print(
    "- industry20_collection_status.csv"
)

if OUTPUT_RECON.exists():

    print(
        "- industry20_reconciliation.csv"
    )


print()
print("=" * 100)
print(
    "20 INDUSTRY COLLECTION COMPLETE"
)
print("=" * 100)