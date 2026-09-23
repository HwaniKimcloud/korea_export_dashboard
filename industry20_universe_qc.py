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

# 공식 HSK10 -> MTI6 -> 산업20(+기타) Master
MASTER_FILE = BASE_DIR / "official_hsk_mti_master.csv"

# 앞 단계에서 생성한 공식 20대 산업 월별 데이터
INDUSTRY20_MONTHLY_FILE = BASE_DIR / "industry20_monthly.csv"

# 관세청 한국 전체수출 월별 데이터
TOTAL_EXPORT_FILE = BASE_DIR / "korea_total_export_monthly.csv"

# 출력
OUTPUT_OTHER_RAW = BASE_DIR / "industry20_other_hsk_raw.csv"
OUTPUT_OTHER_MONTHLY = BASE_DIR / "industry20_other_monthly.csv"
OUTPUT_DETAIL = BASE_DIR / "industry20_universe_qc_detail.csv"
OUTPUT_COVERAGE = BASE_DIR / "industry20_universe_coverage.csv"
OUTPUT_SUMMARY = BASE_DIR / "industry20_universe_qc_summary.csv"
OUTPUT_STATUS = BASE_DIR / "industry20_other_collection_status.csv"


# ============================================================
# 2. 관세청 API
# ============================================================

URL = "https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList"

# 기존에 정상 작동한 본인의 관세청 API Key를 입력하세요.
SERVICE_KEY = "Jqr042WhXmRju%2F2E4uTPkTQqeJWPrWOjV2YRbdOkdF5B6QuZwyE5p1%2BJ1z1vLG6n2ZKpJBVejEavVIIWG8CrKQ%3D%3D"

SERVICE_KEY = urllib.parse.unquote(SERVICE_KEY)


# ============================================================
# 3. 조회기간
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


# ============================================================
# 5. HS2 단위 관세청 API 호출
#
# 기존 industry20_exact_collector.py와 같은 방식
# ============================================================

def fetch_prefix(
    hs2,
    start_ym,
    end_ym,
    max_retry=3
):

    params = {
        "serviceKey": SERVICE_KEY,
        "strtYymm": start_ym,
        "endYymm": end_ym,
        "hsSgn": hs2,
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
                root.findtext(".//returnReasonCode")
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
                        "조회_HS2": hs2,
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
        f"HS2={hs2} "
        f"{start_ym}~{end_ym} "
        f"{last_error}"
    )

    return pd.DataFrame()


# ============================================================
# 6. 입력 파일 확인
# ============================================================

for file in [
    MASTER_FILE,
    INDUSTRY20_MONTHLY_FILE,
    TOTAL_EXPORT_FILE,
]:

    if not file.exists():

        raise FileNotFoundError(
            f"파일을 찾을 수 없습니다:\n{file}"
        )


print()
print("=" * 105)
print("20 INDUSTRY UNIVERSE QC")
print("=" * 105)


# ============================================================
# 7. 공식 Master 읽기
# ============================================================

master = pd.read_csv(
    MASTER_FILE,
    dtype=str
)


required_master_cols = [
    "HSK10",
    "MTI6",
    "산업20",
]


for col in required_master_cols:

    if col not in master.columns:

        raise ValueError(
            f"Master 필수 컬럼 없음: {col}"
        )


master["HSK10"] = (
    master["HSK10"]
    .apply(
        lambda x:
        normalize_code(
            x,
            10
        )
    )
)


master["MTI6"] = (
    master["MTI6"]
    .apply(
        lambda x:
        normalize_code(
            x,
            6
        )
    )
)


master["산업20"] = (
    master["산업20"]
    .fillna("")
    .astype(str)
    .str.strip()
)


master = master[
    master["HSK10"].notna()
].copy()


# ============================================================
# 8. Master 구조 점검
# ============================================================

print()
print("=" * 105)
print("MASTER STRUCTURE")
print("=" * 105)

print(
    f"전체 HSK10 : "
    f"{master['HSK10'].nunique():,}"
)

print(
    f"전체 MTI6  : "
    f"{master['MTI6'].nunique():,}"
)

print(
    f"산업 분류 수 : "
    f"{master['산업20'].nunique()}"
)


# ------------------------------------------------------------
# HSK10 -> MTI6 중복
# ------------------------------------------------------------

hsk_mti_n = (
    master
    .groupby("HSK10")["MTI6"]
    .nunique()
)

multi_mti = hsk_mti_n[
    hsk_mti_n > 1
]


print(
    f"복수 MTI6 연결 HSK10 : "
    f"{len(multi_mti)}"
)


# ------------------------------------------------------------
# HSK10 -> 산업 중복
# ------------------------------------------------------------

hsk_industry_n = (
    master
    .groupby("HSK10")["산업20"]
    .nunique()
)

multi_industry = hsk_industry_n[
    hsk_industry_n > 1
]


print(
    f"복수 산업 연결 HSK10 : "
    f"{len(multi_industry)}"
)


if (
    len(multi_mti) == 0
    and
    len(multi_industry) == 0
):

    print(
        "Master uniqueness : PASS"
    )

else:

    raise RuntimeError(
        "Master 중복 관계가 존재합니다."
    )


# ============================================================
# 9. '기타' HSK10 추출
# ============================================================

other_master = (
    master[
        master["산업20"]
        ==
        "기타"
    ]
    .copy()
)


other_hsk = set(
    other_master[
        "HSK10"
    ]
    .dropna()
    .unique()
)


other_hs2 = sorted(
    {
        code[:2]
        for code in other_hsk
    }
)


print()
print("=" * 105)
print("OTHER CATEGORY")
print("=" * 105)

print(
    f"'기타' HSK10 수 : "
    f"{len(other_hsk):,}"
)

print(
    f"'기타' MTI6 수  : "
    f"{other_master['MTI6'].nunique():,}"
)

print(
    f"조회 HS2 수      : "
    f"{len(other_hs2)}"
)


if len(other_hsk) == 0:

    raise RuntimeError(
        "'기타' HSK10이 없습니다."
    )


# ============================================================
# 10. '기타' 데이터 수집
# ============================================================

total_requests = (
    len(other_hs2)
    *
    len(PERIODS)
)


print()
print("=" * 105)
print("COLLECT OTHER HSK10")
print("=" * 105)

print(
    f"총 API 호출 예정 : "
    f"{total_requests:,}"
)


frames = []
status_rows = []

request_no = 0


for hs2 in other_hs2:

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
            frames.append(
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


if not frames:

    raise RuntimeError(
        "'기타' 데이터를 "
        "수집하지 못했습니다."
    )


# ============================================================
# 11. API Raw 통합
# ============================================================

api_raw = pd.concat(
    frames,
    ignore_index=True
)


api_raw = (
    api_raw
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


# ============================================================
# 12. '기타' HSK10만 필터
# ============================================================

other_raw = (
    api_raw[
        api_raw["HSK10"]
        .isin(
            other_hsk
        )
    ]
    .copy()
)


other_raw["기준월"] = pd.to_datetime(
    other_raw["기준월"],
    format="%Y%m"
)


other_raw.to_csv(
    OUTPUT_OTHER_RAW,
    index=False,
    encoding="utf-8-sig"
)


print()
print("=" * 105)
print("OTHER RAW CHECK")
print("=" * 105)

print(
    f"수집된 기타 HSK10 : "
    f"{other_raw['HSK10'].nunique():,}"
)

print(
    f"Master 기타 HSK10 : "
    f"{len(other_hsk):,}"
)


# ============================================================
# 13. '기타' 월별 합계
# ============================================================

other_monthly = (
    other_raw
    .groupby(
        "기준월",
        as_index=False
    )
    .agg(
        기타수출_USD=(
            "수출액_USD",
            "sum"
        ),
        기타_활성HSK10=(
            "HSK10",
            "nunique"
        )
    )
    .sort_values(
        "기준월"
    )
    .reset_index(drop=True)
)


other_monthly[
    "기타수출_bn"
] = (
    other_monthly[
        "기타수출_USD"
    ]
    / 1e9
)


other_monthly.to_csv(
    OUTPUT_OTHER_MONTHLY,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 14. 기존 20대 산업 월별 합계
# ============================================================

industry20 = pd.read_csv(
    INDUSTRY20_MONTHLY_FILE
)


industry20["기준월"] = pd.to_datetime(
    industry20["기준월"]
)


if "수출액_USD" not in industry20.columns:

    raise ValueError(
        "industry20_monthly.csv에 "
        "'수출액_USD' 열이 없습니다."
    )


industry20_sum = (
    industry20
    .groupby(
        "기준월",
        as_index=False
    )
    .agg(
        산업20_수출_USD=(
            "수출액_USD",
            "sum"
        ),
        산업수=(
            "산업20",
            "nunique"
        )
    )
    .sort_values(
        "기준월"
    )
)


industry20_sum[
    "산업20_수출_bn"
] = (
    industry20_sum[
        "산업20_수출_USD"
    ]
    / 1e9
)


# ============================================================
# 15. 한국 전체수출 읽기
# ============================================================

total = pd.read_csv(
    TOTAL_EXPORT_FILE
)


if "기준월" not in total.columns:

    raise ValueError(
        "korea_total_export_monthly.csv에 "
        "'기준월' 열이 없습니다."
    )


total["기준월"] = pd.to_datetime(
    total["기준월"]
)


# ============================================================
# 16. 전체수출 정확 USD 컬럼 탐색
# ============================================================

exact_total_candidates = [
    "전체수출_USD",
    "총수출_USD",
    "수출액_USD",
    "expDlr",
]


total_exact_col = None


for col in exact_total_candidates:

    if col in total.columns:

        total_exact_col = col
        break


if total_exact_col is not None:

    total[
        "한국전체수출_USD"
    ] = pd.to_numeric(
        total[
            total_exact_col
        ],
        errors="coerce"
    )


else:

    # --------------------------------------------------------
    # exact USD 열이 없고 bn만 있는 경우
    # --------------------------------------------------------

    bn_candidates = [
        "전체수출_bn",
        "총수출_bn",
        "수출액_bn",
    ]

    total_bn_col = None

    for col in bn_candidates:

        if col in total.columns:

            total_bn_col = col
            break


    if total_bn_col is None:

        print()
        print(
            "현재 전체수출 파일 컬럼:"
        )

        print(
            list(total.columns)
        )

        raise ValueError(
            "전체수출 금액 컬럼을 "
            "찾지 못했습니다."
        )


    print()
    print("=" * 105)
    print("WARNING")
    print("=" * 105)

    print(
        "korea_total_export_monthly.csv에 "
        "exact USD 컬럼이 없습니다."
    )

    print(
        f"'{total_bn_col}'를 이용해 "
        "USD로 환산합니다."
    )

    print(
        "이 경우 달러 단위 Exact PASS 대신 "
        "공표단위 기준 검증을 수행합니다."
    )


    total[
        "한국전체수출_USD"
    ] = (
        pd.to_numeric(
            total[
                total_bn_col
            ],
            errors="coerce"
        )
        * 1e9
    )


# ============================================================
# 17. Universe 결합
# ============================================================

qc = (
    industry20_sum
    .merge(
        other_monthly,
        on="기준월",
        how="outer"
    )
    .merge(
        total[
            [
                "기준월",
                "한국전체수출_USD"
            ]
        ],
        on="기준월",
        how="inner"
    )
    .sort_values(
        "기준월"
    )
    .reset_index(drop=True)
)


# ============================================================
# 18. 재구성 전체수출
# ============================================================

qc[
    "재구성전체수출_USD"
] = (
    qc[
        "산업20_수출_USD"
    ]
    +
    qc[
        "기타수출_USD"
    ]
)


qc[
    "원자료차이_USD"
] = (
    qc[
        "재구성전체수출_USD"
    ]
    -
    qc[
        "한국전체수출_USD"
    ]
)


# ============================================================
# 19. 천 달러 공표단위 비교
# ============================================================

qc[
    "재구성_천USD"
] = (
    qc[
        "재구성전체수출_USD"
    ]
    / 1000
).round().astype(
    "Int64"
)


qc[
    "전체수출_천USD"
] = (
    qc[
        "한국전체수출_USD"
    ]
    / 1000
).round().astype(
    "Int64"
)


qc[
    "차이_천USD"
] = (
    qc[
        "재구성_천USD"
    ]
    -
    qc[
        "전체수출_천USD"
    ]
)


qc[
    "Exact_PASS"
] = (
    qc[
        "차이_천USD"
    ]
    == 0
)


# ============================================================
# 20. Coverage 계산
# ============================================================

qc[
    "산업20_Coverage_%"
] = (
    qc[
        "산업20_수출_USD"
    ]
    /
    qc[
        "한국전체수출_USD"
    ]
    * 100
)


qc[
    "기타_Coverage_%"
] = (
    qc[
        "기타수출_USD"
    ]
    /
    qc[
        "한국전체수출_USD"
    ]
    * 100
)


qc[
    "Coverage합계_%"
] = (
    qc[
        "산업20_Coverage_%"
    ]
    +
    qc[
        "기타_Coverage_%"
    ]
)


qc[
    "한국전체수출_bn"
] = (
    qc[
        "한국전체수출_USD"
    ]
    / 1e9
)


qc[
    "재구성전체수출_bn"
] = (
    qc[
        "재구성전체수출_USD"
    ]
    / 1e9
)


# ============================================================
# 21. 상세 출력
# ============================================================

print()
print("=" * 105)
print("UNIVERSE QC DETAIL")
print("=" * 105)


display_cols = [
    "기준월",
    "산업수",
    "산업20_수출_bn",
    "기타수출_bn",
    "한국전체수출_bn",
    "재구성전체수출_bn",
    "차이_천USD",
    "산업20_Coverage_%",
    "Exact_PASS",
]


print(
    qc[
        display_cols
    ]
    .to_string(
        index=False
    )
)


# ============================================================
# 22. 최종 Summary
# ============================================================

valid = qc[
    qc[
        "한국전체수출_USD"
    ].notna()
].copy()


compare_months = len(
    valid
)


pass_months = int(
    valid[
        "Exact_PASS"
    ]
    .fillna(False)
    .sum()
)


max_abs_diff_usd = (
    valid[
        "원자료차이_USD"
    ]
    .abs()
    .max()
)


max_abs_diff_kusd = (
    valid[
        "차이_천USD"
    ]
    .abs()
    .max()
)


latest_row = (
    valid
    .sort_values(
        "기준월"
    )
    .iloc[-1]
)


summary = pd.DataFrame(
    [
        {
            "비교월수":
                compare_months,

            "PASS월수":
                pass_months,

            "전체_PASS":
                (
                    compare_months > 0
                    and
                    compare_months
                    ==
                    pass_months
                ),

            "최대절대차이_USD":
                max_abs_diff_usd,

            "최대절대차이_천USD":
                max_abs_diff_kusd,

            "최신월":
                latest_row[
                    "기준월"
                ],

            "최신월_20대Coverage_%":
                latest_row[
                    "산업20_Coverage_%"
                ],

            "최신월_기타Coverage_%":
                latest_row[
                    "기타_Coverage_%"
                ],

            "최신월_Coverage합계_%":
                latest_row[
                    "Coverage합계_%"
                ],
        }
    ]
)


print()
print("=" * 105)
print("UNIVERSE QC SUMMARY")
print("=" * 105)

print(
    f"비교 가능 월 : "
    f"{compare_months}"
)

print(
    f"차이 0 월    : "
    f"{pass_months}"
)

print(
    f"최대 절대차이(USD) : "
    f"{max_abs_diff_usd:,.0f}"
)

print(
    f"최대 절대차이(천USD) : "
    f"{max_abs_diff_kusd:,.0f}"
)


print()
print(
    f"최신월 20대 산업 Coverage : "
    f"{latest_row['산업20_Coverage_%']:.2f}%"
)

print(
    f"최신월 기타 Coverage      : "
    f"{latest_row['기타_Coverage_%']:.2f}%"
)

print(
    f"Coverage 합계             : "
    f"{latest_row['Coverage합계_%']:.4f}%"
)


print()


if (
    compare_months > 0
    and
    compare_months
    ==
    pass_months
):

    print(
        "20 INDUSTRY + OTHER "
        "= TOTAL EXPORT : PASS"
    )

else:

    print(
        "UNIVERSE QC : REVIEW REQUIRED"
    )


# ============================================================
# 23. 실패월 출력
# ============================================================

failed = valid[
    ~valid[
        "Exact_PASS"
    ].fillna(False)
].copy()


if not failed.empty:

    print()
    print("=" * 105)
    print("FAILED MONTHS")
    print("=" * 105)

    print(
        failed[
            [
                "기준월",
                "산업20_수출_USD",
                "기타수출_USD",
                "재구성전체수출_USD",
                "한국전체수출_USD",
                "원자료차이_USD",
                "차이_천USD",
            ]
        ]
        .to_string(
            index=False
        )
    )


# ============================================================
# 24. CSV 저장
# ============================================================

qc.to_csv(
    OUTPUT_DETAIL,
    index=False,
    encoding="utf-8-sig"
)


qc[
    [
        "기준월",
        "산업20_수출_USD",
        "기타수출_USD",
        "한국전체수출_USD",
        "산업20_Coverage_%",
        "기타_Coverage_%",
        "Coverage합계_%",
    ]
].to_csv(
    OUTPUT_COVERAGE,
    index=False,
    encoding="utf-8-sig"
)


summary.to_csv(
    OUTPUT_SUMMARY,
    index=False,
    encoding="utf-8-sig"
)


print()
print("=" * 105)
print("CSV 저장 완료")
print("=" * 105)

print(
    "- industry20_other_hsk_raw.csv"
)

print(
    "- industry20_other_monthly.csv"
)

print(
    "- industry20_universe_qc_detail.csv"
)

print(
    "- industry20_universe_coverage.csv"
)

print(
    "- industry20_universe_qc_summary.csv"
)

print(
    "- industry20_other_collection_status.csv"
)


print()
print("=" * 105)
print("UNIVERSE QC COMPLETE")
print("=" * 105)