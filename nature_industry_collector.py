# ============================================================
# nature_industry_collector.py
#
# Korea Export Monitor
# Customs New-Nature Classification
# 20 Major Export Industries Collector
#
# 기능
# 1. 관세청조회코드_v1.2.xlsx 자동 탐색
# 2. 성질통합분류코드(header=3) 읽기
# 3. 20대 산업 소분류 자동 매칭
# 4. 산업별 하위 세세분류 코드 자동 추출
# 5. 신성질별 수출 API 호출
# 6. 2025.01~2026.08 월별 수출 집계
# 7. Monthly / Latest / YTD 자동 생성
# 8. 반도체 2026.08 Exact QC
# 9. CSV 일괄 저장
#
# 인증키:
# 기존 PASS 파일 nature_semiconductor_test.py 에서 자동 추출
# ============================================================

from __future__ import annotations

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
# 관세청 xlsx custom property 오류 우회
# ============================================================

from openpyxl.packaging.custom import CustomPropertyList


def _ignore_broken_custom_properties(cls, node):
    return cls()


CustomPropertyList.from_tree = classmethod(
    _ignore_broken_custom_properties
)


# ============================================================
# 1. PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

INDUSTRY_DATA_DIR = (
    BASE_DIR
    / "industry_data"
)


EXCEL_CANDIDATES = [
    INDUSTRY_DATA_DIR / "관세청조회코드_v1.2.xlsx",
    BASE_DIR / "관세청조회코드_v1.2.xlsx",
]


SEMICONDUCTOR_TEST_FILE = (
    BASE_DIR
    / "nature_semiconductor_test.py"
)


# ============================================================
# 2. OUTPUT
# ============================================================

OUTPUT_MASTER = (
    BASE_DIR
    / "nature_industry_master.csv"
)

OUTPUT_LEAF = (
    BASE_DIR
    / "nature_industry_leaf_codes.csv"
)

OUTPUT_RAW = (
    BASE_DIR
    / "nature_industry_api_raw.csv"
)

OUTPUT_MONTHLY = (
    BASE_DIR
    / "nature_industry_monthly.csv"
)

OUTPUT_LATEST = (
    BASE_DIR
    / "nature_industry_latest.csv"
)

OUTPUT_YTD = (
    BASE_DIR
    / "nature_industry_ytd.csv"
)

OUTPUT_STATUS = (
    BASE_DIR
    / "nature_industry_collection_status.csv"
)

OUTPUT_UNMATCHED = (
    BASE_DIR
    / "nature_industry_unmatched.csv"
)


# ============================================================
# 3. API
# ============================================================

API_URL = (
    "https://apis.data.go.kr/"
    "1220000/newtempertrade/"
    "getNewtempertradeList"
)

IMEX_TPCD = "1"

VERIFY_SSL = False

urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)

REQUEST_SLEEP = 0.05


# ============================================================
# 4. 조회 기간
#
# API 제한:
# 시작~종료 1년 이내
#
# 따라서 자동으로 두 구간 사용
# ============================================================

DATE_RANGES = [
    ("202501", "202512"),
    ("202601", "202608"),
]

LATEST_YM = "202608"


# ============================================================
# 5. 20대 산업
#
# 기존 Korea Export Monitor 기준
# ============================================================

TARGET_INDUSTRIES = [
    "반도체",
    "자동차",
    "석유제품",
    "컴퓨터",
    "일반기계",
    "석유화학",
    "선박류",
    "철강제품",
    "자동차부품",
    "무선통신기기",
    "전기기기",
    "비철금속",
    "디스플레이",
    "바이오헬스",
    "화장품",
    "농수산식품",
    "섬유류",
    "생활용품",
    "이차전지",
    "가전",
]


# ============================================================
# 6. 산업명 별칭
#
# 공식 코드표 이름이 약간 다를 경우 대응
# exact match를 먼저 하고,
# 이후 alias contains match
# ============================================================

INDUSTRY_ALIASES = {

    "반도체": [
        "반도체",
    ],

    "자동차": [
        "자동차",
    ],

    "석유제품": [
        "석유제품",
    ],

    "컴퓨터": [
        "컴퓨터",
    ],

    "일반기계": [
        "일반기계",
    ],

    "석유화학": [
        "석유화학",
    ],

    "선박류": [
        "선박류",
        "선박",
    ],

    "철강제품": [
        "철강제품",
    ],

    "자동차부품": [
        "자동차부품",
    ],

    "무선통신기기": [
        "무선통신기기",
    ],

    "전기기기": [
        "전기기기",
    ],

    "비철금속": [
        "비철금속",
    ],

    "디스플레이": [
        "디스플레이",
    ],

    "바이오헬스": [
        "바이오헬스",
    ],

    "화장품": [
        "화장품",
    ],

    "농수산식품": [
        "농수산식품",
    ],

    "섬유류": [
        "섬유류",
        "섬유",
    ],

    "생활용품": [
        "생활용품",
    ],

    "이차전지": [
        "이차전지",
    ],

    "가전": [
        "가전",
    ],
}


# ============================================================
# 7. Semiconductor Exact QC
#
# API 재구성값:
# 2026.08 = 46,669,843,685 USD 수준
#
# 관세청 표시는 천달러 단위:
# 46,669,844,000
#
# 따라서 1,000 USD 이내 허용
# ============================================================

SEMICONDUCTOR_REFERENCE_YM = "202608"
SEMICONDUCTOR_REFERENCE_USD = 46_669_844_000

QC_TOLERANCE_USD = 1_000


# ============================================================
# 8. Utility
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
        .replace("/", "")
        .lower()
    )


def normalize_code(value) -> str:

    if pd.isna(value):
        return ""

    value = str(value).strip()

    if value.endswith(".0"):
        value = value[:-2]

    return re.sub(
        r"[^0-9]",
        "",
        value,
    )


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


def find_col(
    dataframe,
    candidates,
):

    cmap = {
        canonical(col): col
        for col
        in dataframe.columns
    }

    for candidate in candidates:

        key = canonical(candidate)

        if key in cmap:
            return cmap[key]

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
            word.replace(" ", "")
            in normalized
            for word
            in required_words
        ):
            return col

    return None


# ============================================================
# 9. 기존 PASS 파일에서 인증키 자동 추출
# ============================================================

def load_service_key():

    if not SEMICONDUCTOR_TEST_FILE.exists():

        raise FileNotFoundError(
            "\n"
            "nature_semiconductor_test.py를 찾지 못했습니다.\n"
            "PASS 완료한 파일을 현재 프로젝트 폴더에 두세요."
        )

    text = SEMICONDUCTOR_TEST_FILE.read_text(
        encoding="utf-8"
    )

    # SERVICE_KEY = (
    #     "xxxxx"
    # )
    match = re.search(
        r'SERVICE_KEY\s*=\s*\(\s*["\']([^"\']+)["\']',
        text,
        flags=re.MULTILINE,
    )

    if match is None:

        # SERVICE_KEY = "xxxxx"
        match = re.search(
            r'SERVICE_KEY\s*=\s*["\']([^"\']+)["\']',
            text,
            flags=re.MULTILINE,
        )

    if match is None:

        raise RuntimeError(
            "\n"
            "nature_semiconductor_test.py에서 "
            "SERVICE_KEY를 찾지 못했습니다."
        )

    key = match.group(1).strip()

    if not key:

        raise RuntimeError(
            "SERVICE_KEY가 비어 있습니다."
        )

    return urllib.parse.unquote(
        key
    )


SERVICE_KEY = load_service_key()


# ============================================================
# 10. Excel 자동 탐색
# ============================================================

excel_file = None

for candidate in EXCEL_CANDIDATES:

    if candidate.exists():

        excel_file = candidate
        break


if excel_file is None:

    raise FileNotFoundError(
        "\n관세청조회코드_v1.2.xlsx를 찾지 못했습니다.\n\n"
        f"1) {INDUSTRY_DATA_DIR}\n"
        f"2) {BASE_DIR}\n"
    )


# ============================================================
# 11. 시작
# ============================================================

print()
print("=" * 110)
print("20 MAJOR INDUSTRIES NEW-NATURE COLLECTOR")
print("=" * 110)

print(
    "코드표      :",
    excel_file,
)

print(
    "산업 수     :",
    len(TARGET_INDUSTRIES),
)

print(
    "조회 기간   :",
    DATE_RANGES,
)

print(
    "Latest Month:",
    LATEST_YM,
)

print()


# ============================================================
# 12. 공식 코드표 읽기
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
    for col
    in df.columns
]


# ============================================================
# 13. 공식 컬럼 탐색
# ============================================================

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

year_col = find_col(
    df,
    [
        "년도",
        "연도",
    ],
)


required = {
    "소분류코드":
        small_code_col,

    "소분류명":
        small_name_col,

    "세세분류코드":
        detail_code_col,

    "세세분류명":
        detail_name_col,
}


for name, col in required.items():

    if col is None:

        raise RuntimeError(
            f"{name} 컬럼을 찾지 못했습니다."
        )


print("=" * 110)
print("OFFICIAL COLUMN CHECK")
print("=" * 110)

print(
    "소분류코드   :",
    small_code_col,
)

print(
    "소분류명     :",
    small_name_col,
)

print(
    "세세분류코드 :",
    detail_code_col,
)

print(
    "세세분류명   :",
    detail_name_col,
)

print(
    "년도         :",
    year_col,
)

print()


# ============================================================
# 14. 2026 기준 필터
# ============================================================

if year_col is not None:

    year_numeric = pd.to_numeric(
        df[year_col],
        errors="coerce",
    )

    if (
        year_numeric
        ==
        2026
    ).any():

        df = df[
            year_numeric
            ==
            2026
        ].copy()


# ============================================================
# 15. 코드 정규화
# ============================================================

df["_SMALL_CODE"] = (
    df[small_code_col]
    .apply(
        normalize_code
    )
)

df["_SMALL_NAME"] = (
    df[small_name_col]
    .apply(
        clean_text
    )
)

df["_SMALL_CANON"] = (
    df["_SMALL_NAME"]
    .apply(
        canonical
    )
)

df["_DETAIL_CODE"] = (
    df[detail_code_col]
    .apply(
        normalize_code
    )
)

df["_DETAIL_NAME"] = (
    df[detail_name_col]
    .apply(
        clean_text
    )
)


# ============================================================
# 16. 소분류 Catalog
# ============================================================

small_catalog = (
    df[
        [
            "_SMALL_CODE",
            "_SMALL_NAME",
            "_SMALL_CANON",
        ]
    ]
    .loc[
        lambda x:
        (
            x["_SMALL_CODE"] != ""
        )
        &
        (
            x["_SMALL_NAME"] != ""
        )
    ]
    .drop_duplicates()
    .sort_values(
        [
            "_SMALL_CODE",
            "_SMALL_NAME",
        ]
    )
    .reset_index(
        drop=True
    )
)


# ============================================================
# 17. 산업 → 공식 소분류 매칭
# ============================================================

def resolve_industry(
    industry_name,
):

    aliases = INDUSTRY_ALIASES.get(
        industry_name,
        [
            industry_name
        ],
    )

    # --------------------------------------------------------
    # 1순위:
    # 공식 소분류명 exact canonical match
    # --------------------------------------------------------

    exact_hits = []

    for alias in aliases:

        alias_canon = canonical(
            alias
        )

        temp = small_catalog[
            small_catalog[
                "_SMALL_CANON"
            ]
            ==
            alias_canon
        ]

        if not temp.empty:

            exact_hits.append(
                temp
            )

    if exact_hits:

        result = pd.concat(
            exact_hits,
            ignore_index=True,
        )

        return (
            result
            .drop_duplicates(
                subset=[
                    "_SMALL_CODE"
                ]
            )
        )


    # --------------------------------------------------------
    # 2순위:
    # contains
    #
    # 자동차는 자동차부품 제외
    # --------------------------------------------------------

    contains_hits = []

    for alias in aliases:

        alias_canon = canonical(
            alias
        )

        temp = small_catalog[
            small_catalog[
                "_SMALL_CANON"
            ]
            .str.contains(
                alias_canon,
                na=False,
                regex=False,
            )
        ].copy()

        if industry_name == "자동차":

            temp = temp[
                ~temp[
                    "_SMALL_CANON"
                ]
                .str.contains(
                    canonical(
                        "자동차부품"
                    ),
                    na=False,
                    regex=False,
                )
            ]

        if not temp.empty:

            contains_hits.append(
                temp
            )

    if contains_hits:

        result = pd.concat(
            contains_hits,
            ignore_index=True,
        )

        return (
            result
            .drop_duplicates(
                subset=[
                    "_SMALL_CODE"
                ]
            )
        )


    return pd.DataFrame(
        columns=
        small_catalog.columns
    )


# ============================================================
# 18. 20개 산업 Master 구축
# ============================================================

master_rows = []
unmatched_rows = []


print("=" * 110)
print("20 INDUSTRY OFFICIAL MAPPING")
print("=" * 110)


for order, industry in enumerate(
    TARGET_INDUSTRIES,
    start=1,
):

    matches = resolve_industry(
        industry
    )

    if matches.empty:

        print(
            f"[{order:02d}/20] "
            f"{industry:10s} : NOT FOUND"
        )

        unmatched_rows.append(
            {
                "순위": order,
                "산업20": industry,
            }
        )

        continue


    code_list = (
        matches[
            "_SMALL_CODE"
        ]
        .tolist()
    )

    name_list = (
        matches[
            "_SMALL_NAME"
        ]
        .tolist()
    )


    print(
        f"[{order:02d}/20] "
        f"{industry:10s} : "
        f"{len(matches)} code(s)"
    )

    for code, official_name in zip(
        code_list,
        name_list,
    ):

        print(
            f"             "
            f"{code}  "
            f"{official_name}"
        )

        master_rows.append(
            {
                "순위":
                    order,

                "산업20":
                    industry,

                "소분류코드":
                    code,

                "공식소분류명":
                    official_name,
            }
        )


master = pd.DataFrame(
    master_rows
)


unmatched = pd.DataFrame(
    unmatched_rows
)


master.to_csv(
    OUTPUT_MASTER,
    index=False,
    encoding="utf-8-sig",
)


unmatched.to_csv(
    OUTPUT_UNMATCHED,
    index=False,
    encoding="utf-8-sig",
)


print()


# ============================================================
# 19. 산업별 leaf master
# ============================================================

leaf_frames = []


for _, row in master.iterrows():

    industry = row[
        "산업20"
    ]

    parent_code = row[
        "소분류코드"
    ]

    official_name = row[
        "공식소분류명"
    ]


    temp = df[
        df[
            "_SMALL_CODE"
        ]
        ==
        parent_code
    ].copy()


    temp = temp[
        temp[
            "_DETAIL_CODE"
        ]
        !=
        ""
    ].copy()


    temp = temp[
        [
            "_DETAIL_CODE",
            "_DETAIL_NAME",
        ]
    ].drop_duplicates(
        subset=[
            "_DETAIL_CODE"
        ]
    )


    temp["산업20"] = industry

    temp[
        "소분류코드"
    ] = parent_code

    temp[
        "공식소분류명"
    ] = official_name


    temp = temp.rename(
        columns={
            "_DETAIL_CODE":
                "신성질코드",

            "_DETAIL_NAME":
                "신성질품목명",
        }
    )


    leaf_frames.append(
        temp
    )


if not leaf_frames:

    raise RuntimeError(
        "산업별 세세분류 코드를 "
        "하나도 만들지 못했습니다."
    )


leaf = pd.concat(
    leaf_frames,
    ignore_index=True,
)


leaf = (
    leaf
    .drop_duplicates(
        subset=[
            "산업20",
            "신성질코드",
        ]
    )
    .sort_values(
        [
            "산업20",
            "신성질코드",
        ]
    )
    .reset_index(
        drop=True
    )
)


leaf.to_csv(
    OUTPUT_LEAF,
    index=False,
    encoding="utf-8-sig",
)


print("=" * 110)
print("LEAF CODE SUMMARY")
print("=" * 110)


leaf_summary = (
    leaf
    .groupby(
        "산업20"
    )[
        "신성질코드"
    ]
    .nunique()
    .reindex(
        TARGET_INDUSTRIES
    )
)


print(
    leaf_summary.to_string()
)

print()


# ============================================================
# 20. API
# ============================================================

def api_call(
    nature_code,
    start_ym,
    end_ym,
):

    params = {
        "serviceKey":
            SERVICE_KEY,

        "strtYymm":
            start_ym,

        "endYymm":
            end_ym,

        "imexTpcd":
            IMEX_TPCD,

        "imexTmprUnfcClsfCd":
            nature_code,
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


    result_code = (
        root.findtext(
            ".//resultCode",
            default="",
        )
    )

    result_msg = (
        root.findtext(
            ".//resultMsg",
            default="",
        )
    )


    if result_code != "00":

        return {
            "ok":
                False,

            "result_code":
                result_code,

            "result_msg":
                result_msg,

            "rows":
                [],
        }


    items = root.findall(
        ".//item"
    )


    rows = []


    for item in items:

        item_row = {}

        for child in item:

            item_row[
                child.tag
            ] = (
                child.text.strip()
                if child.text
                else ""
            )

        rows.append(
            item_row
        )


    return {
        "ok":
            True,

        "result_code":
            result_code,

        "result_msg":
            result_msg,

        "rows":
            rows,
    }


# ============================================================
# 21. 전체 API 수집
# ============================================================

all_frames = []
status_rows = []


total_leaf = len(
    leaf
)


print("=" * 110)
print("API COLLECTION START")
print("=" * 110)

print(
    "총 산업-세세분류 조합:",
    f"{total_leaf:,}",
)

print()


for idx, row in leaf.iterrows():

    industry = str(
        row["산업20"]
    )

    parent_code = str(
        row["소분류코드"]
    )

    official_parent_name = str(
        row["공식소분류명"]
    )

    code = str(
        row["신성질코드"]
    )

    name = str(
        row["신성질품목명"]
    )


    print(
        f"[{idx + 1:03d}/{total_leaf:03d}] "
        f"{industry} | "
        f"{code} | "
        f"{name}"
    )


    for (
        start_ym,
        end_ym,
    ) in DATE_RANGES:

        try:

            result = api_call(
                code,
                start_ym,
                end_ym,
            )


            if not result[
                "ok"
            ]:

                print(
                    f"   {start_ym}~{end_ym} "
                    f"FAIL "
                    f"{result['result_code']} "
                    f"{result['result_msg']}"
                )

                status_rows.append(
                    {
                        "산업20":
                            industry,

                        "소분류코드":
                            parent_code,

                        "공식소분류명":
                            official_parent_name,

                        "신성질코드":
                            code,

                        "신성질품목명":
                            name,

                        "시작월":
                            start_ym,

                        "종료월":
                            end_ym,

                        "상태":
                            "API_ERROR",

                        "item수":
                            0,

                        "resultCode":
                            result[
                                "result_code"
                            ],

                        "resultMsg":
                            result[
                                "result_msg"
                            ],
                    }
                )

                continue


            rows = result[
                "rows"
            ]


            print(
                f"   {start_ym}~{end_ym} "
                f"item={len(rows)}"
            )


            status_rows.append(
                {
                    "산업20":
                        industry,

                    "소분류코드":
                        parent_code,

                    "공식소분류명":
                        official_parent_name,

                    "신성질코드":
                        code,

                    "신성질품목명":
                        name,

                    "시작월":
                        start_ym,

                    "종료월":
                        end_ym,

                    "상태":
                        "OK",

                    "item수":
                        len(rows),

                    "resultCode":
                        result[
                            "result_code"
                        ],

                    "resultMsg":
                        result[
                            "result_msg"
                        ],
                }
            )


            if rows:

                temp = pd.DataFrame(
                    rows
                )


                temp[
                    "_INDUSTRY"
                ] = industry

                temp[
                    "_PARENT_CODE"
                ] = parent_code

                temp[
                    "_PARENT_NAME"
                ] = official_parent_name

                temp[
                    "_QUERY_CODE"
                ] = code

                temp[
                    "_QUERY_NAME"
                ] = name

                temp[
                    "_START_YM"
                ] = start_ym

                temp[
                    "_END_YM"
                ] = end_ym


                all_frames.append(
                    temp
                )


        except Exception as exc:

            print(
                f"   EXCEPTION: "
                f"{type(exc).__name__}: "
                f"{exc}"
            )


            status_rows.append(
                {
                    "산업20":
                        industry,

                    "소분류코드":
                        parent_code,

                    "공식소분류명":
                        official_parent_name,

                    "신성질코드":
                        code,

                    "신성질품목명":
                        name,

                    "시작월":
                        start_ym,

                    "종료월":
                        end_ym,

                    "상태":
                        "EXCEPTION",

                    "item수":
                        0,

                    "resultCode":
                        "",

                    "resultMsg":
                        str(exc),
                }
            )


        time.sleep(
            REQUEST_SLEEP
        )


# ============================================================
# 22. Status
# ============================================================

status_df = pd.DataFrame(
    status_rows
)


status_df.to_csv(
    OUTPUT_STATUS,
    index=False,
    encoding="utf-8-sig",
)


if not all_frames:

    raise RuntimeError(
        "API에서 수집된 데이터가 없습니다."
    )


# ============================================================
# 23. Raw
# ============================================================

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
print("=" * 110)
print("API RAW CREATED")
print("=" * 110)

print(
    "Raw 행 수:",
    f"{len(raw):,}",
)

print()


# ============================================================
# 24. API 필드 탐색
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
        "API 응답에서 월 컬럼을 찾지 못했습니다.\n"
        f"{raw.columns.tolist()}"
    )


if amount_col is None:

    raise RuntimeError(
        "API 응답에서 수출액 컬럼을 찾지 못했습니다.\n"
        f"{raw.columns.tolist()}"
    )


print(
    "월 컬럼    :",
    month_col,
)

print(
    "금액 컬럼  :",
    amount_col,
)

print()


# ============================================================
# 25. Normalize
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
    .fillna(0)
)


# ============================================================
# 26. 중복 제거
#
# 같은 산업 / leaf / 월의 API row가
# 중복될 경우 한 번만 사용
# ============================================================

raw = (
    raw
    .sort_values(
        [
            "_INDUSTRY",
            "_QUERY_CODE",
            "_YYYYMM",
        ]
    )
    .drop_duplicates(
        subset=[
            "_INDUSTRY",
            "_QUERY_CODE",
            "_YYYYMM",
        ],
        keep="last",
    )
    .reset_index(
        drop=True
    )
)


# ============================================================
# 27. Monthly
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
        [
            "_INDUSTRY",
            "_YYYYMM",
        ],
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
    .rename(
        columns={
            "_INDUSTRY":
                "산업20",

            "_YYYYMM":
                "기준월",
        }
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


monthly = (
    monthly
    .sort_values(
        [
            "산업20",
            "기준월",
        ]
    )
    .reset_index(
        drop=True
    )
)


monthly[
    "MoM_%"
] = (
    monthly
    .groupby(
        "산업20"
    )[
        "수출액_USD"
    ]
    .pct_change()
    *
    100
)


monthly[
    "YoY_%"
] = (
    monthly
    .groupby(
        "산업20"
    )[
        "수출액_USD"
    ]
    .pct_change(
        12
    )
    *
    100
)


# ============================================================
# 28. 3M YoY
# ============================================================

monthly[
    "_ROLL3"
] = (
    monthly
    .groupby(
        "산업20"
    )[
        "수출액_USD"
    ]
    .transform(
        lambda x:
        x.rolling(
            3
        ).sum()
    )
)


monthly[
    "3M_YoY_%"
] = (
    monthly
    .groupby(
        "산업20"
    )[
        "_ROLL3"
    ]
    .pct_change(
        12
    )
    *
    100
)


monthly = monthly.drop(
    columns=[
        "_ROLL3"
    ]
)


# ============================================================
# 29. 산업순위
# ============================================================

industry_order = {
    industry:
        idx

    for idx, industry
    in enumerate(
        TARGET_INDUSTRIES,
        start=1,
    )
}


monthly[
    "산업순위"
] = (
    monthly[
        "산업20"
    ]
    .map(
        industry_order
    )
)


monthly = (
    monthly
    [
        [
            "산업순위",
            "산업20",
            "기준월",
            "수출액_USD",
            "수출액_bn",
            "MoM_%",
            "YoY_%",
            "3M_YoY_%",
            "세세분류수",
        ]
    ]
    .sort_values(
        [
            "산업순위",
            "기준월",
        ]
    )
    .reset_index(
        drop=True
    )
)


monthly.to_csv(
    OUTPUT_MONTHLY,
    index=False,
    encoding="utf-8-sig",
)


# ============================================================
# 30. Latest
# ============================================================

latest = (
    monthly[
        monthly[
            "기준월"
        ]
        ==
        LATEST_YM
    ]
    .copy()
)


latest = (
    latest
    .sort_values(
        "수출액_USD",
        ascending=False,
    )
    .reset_index(
        drop=True
    )
)


latest[
    "수출액순위"
] = (
    np.arange(
        1,
        len(latest) + 1,
    )
)


latest = latest[
    [
        "수출액순위",
        "산업순위",
        "산업20",
        "기준월",
        "수출액_USD",
        "수출액_bn",
        "MoM_%",
        "YoY_%",
        "3M_YoY_%",
        "세세분류수",
    ]
]


latest.to_csv(
    OUTPUT_LATEST,
    index=False,
    encoding="utf-8-sig",
)


# ============================================================
# 31. YTD
# ============================================================

latest_year = int(
    LATEST_YM[:4]
)

latest_month_num = int(
    LATEST_YM[4:6]
)


monthly[
    "_YEAR"
] = (
    monthly[
        "기준월"
    ]
    .str[:4]
    .astype(int)
)


monthly[
    "_MONTH"
] = (
    monthly[
        "기준월"
    ]
    .str[4:6]
    .astype(int)
)


current_ytd = (
    monthly[
        (
            monthly[
                "_YEAR"
            ]
            ==
            latest_year
        )
        &
        (
            monthly[
                "_MONTH"
            ]
            <=
            latest_month_num
        )
    ]
    .groupby(
        "산업20"
    )[
        "수출액_USD"
    ]
    .sum()
)


previous_ytd = (
    monthly[
        (
            monthly[
                "_YEAR"
            ]
            ==
            latest_year - 1
        )
        &
        (
            monthly[
                "_MONTH"
            ]
            <=
            latest_month_num
        )
    ]
    .groupby(
        "산업20"
    )[
        "수출액_USD"
    ]
    .sum()
)


ytd = pd.DataFrame(
    {
        "산업20":
            TARGET_INDUSTRIES
    }
)


ytd[
    "산업순위"
] = (
    ytd[
        "산업20"
    ]
    .map(
        industry_order
    )
)


ytd[
    "현재YTD_USD"
] = (
    ytd[
        "산업20"
    ]
    .map(
        current_ytd
    )
    .fillna(0)
)


ytd[
    "전년YTD_USD"
] = (
    ytd[
        "산업20"
    ]
    .map(
        previous_ytd
    )
    .fillna(0)
)


ytd[
    "현재YTD_bn"
] = (
    ytd[
        "현재YTD_USD"
    ]
    /
    1e9
)


ytd[
    "전년YTD_bn"
] = (
    ytd[
        "전년YTD_USD"
    ]
    /
    1e9
)


ytd[
    "YTD증감액_bn"
] = (
    (
        ytd[
            "현재YTD_USD"
        ]
        -
        ytd[
            "전년YTD_USD"
        ]
    )
    /
    1e9
)


ytd[
    "YTD_YoY_%"
] = np.where(
    ytd[
        "전년YTD_USD"
    ]
    !=
    0,

    (
        ytd[
            "현재YTD_USD"
        ]
        /
        ytd[
            "전년YTD_USD"
        ]
        -
        1
    )
    *
    100,

    np.nan,
)


ytd = (
    ytd
    .sort_values(
        "현재YTD_USD",
        ascending=False,
    )
    .reset_index(
        drop=True
    )
)


ytd[
    "YTD수출순위"
] = (
    np.arange(
        1,
        len(ytd) + 1,
    )
)


ytd = ytd[
    [
        "YTD수출순위",
        "산업순위",
        "산업20",
        "현재YTD_USD",
        "현재YTD_bn",
        "전년YTD_USD",
        "전년YTD_bn",
        "YTD증감액_bn",
        "YTD_YoY_%",
    ]
]


ytd.to_csv(
    OUTPUT_YTD,
    index=False,
    encoding="utf-8-sig",
)


# ============================================================
# 32. Semiconductor Exact QC
# ============================================================

semi_qc = monthly[
    (
        monthly[
            "산업20"
        ]
        ==
        "반도체"
    )
    &
    (
        monthly[
            "기준월"
        ]
        ==
        SEMICONDUCTOR_REFERENCE_YM
    )
]


print()
print("=" * 110)
print("SEMICONDUCTOR EXACT QC")
print("=" * 110)


if semi_qc.empty:

    print(
        "반도체 2026.08 데이터 없음"
    )

    semi_pass = False

else:

    semi_actual = float(
        semi_qc.iloc[0][
            "수출액_USD"
        ]
    )

    semi_diff = (
        semi_actual
        -
        SEMICONDUCTOR_REFERENCE_USD
    )

    semi_pass = (
        abs(
            semi_diff
        )
        <=
        QC_TOLERANCE_USD
    )


    print(
        f"API      : "
        f"${semi_actual / 1e9:,.6f}bn"
    )

    print(
        f"Reference: "
        f"${SEMICONDUCTOR_REFERENCE_USD / 1e9:,.6f}bn"
    )

    print(
        f"Difference: "
        f"${semi_diff:,.0f}"
    )

    print(
        "Result   :",
        (
            "PASS"
            if semi_pass
            else "REVIEW REQUIRED"
        ),
    )


# ============================================================
# 33. Final QC
# ============================================================

matched_industries = (
    master[
        "산업20"
    ]
    .nunique()
)


latest_industries = (
    latest[
        "산업20"
    ]
    .nunique()
)


api_error_count = int(
    (
        status_df[
            "상태"
        ]
        !=
        "OK"
    ).sum()
)


print()
print("=" * 110)
print("FINAL QC")
print("=" * 110)

print(
    "20대 산업 Master :",
    f"{matched_industries}/20",
)

print(
    "Latest 산업 수   :",
    f"{latest_industries}/20",
)

print(
    "API 오류 건수    :",
    api_error_count,
)

print(
    "반도체 Exact QC  :",
    (
        "PASS"
        if semi_pass
        else "REVIEW REQUIRED"
    ),
)


production_ready = (
    matched_industries
    ==
    20
    and
    latest_industries
    ==
    20
    and
    api_error_count
    ==
    0
    and
    semi_pass
)


print()


if production_ready:

    print(
        ">>> "
        "20 INDUSTRY NEW-NATURE COLLECTION : "
        "PRODUCTION READY "
        "<<<"
    )

else:

    print(
        ">>> "
        "20 INDUSTRY NEW-NATURE COLLECTION : "
        "REVIEW REQUIRED "
        "<<<"
    )


# ============================================================
# 34. Latest 출력
# ============================================================

print()
print("=" * 110)
print(f"LATEST MONTH : {LATEST_YM}")
print("=" * 110)

print(
    latest[
        [
            "수출액순위",
            "산업20",
            "수출액_bn",
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
# 35. YTD 출력
# ============================================================

print()
print("=" * 110)
print(
    f"{latest_year} YTD "
    f"(JAN-{latest_month_num:02d})"
)
print("=" * 110)

print(
    ytd[
        [
            "YTD수출순위",
            "산업20",
            "현재YTD_bn",
            "YTD_YoY_%",
            "YTD증감액_bn",
        ]
    ]
    .to_string(
        index=False
    )
)


# ============================================================
# 36. CSV
# ============================================================

print()
print("=" * 110)
print("CSV 저장 완료")
print("=" * 110)


for path in [
    OUTPUT_MASTER,
    OUTPUT_LEAF,
    OUTPUT_RAW,
    OUTPUT_MONTHLY,
    OUTPUT_LATEST,
    OUTPUT_YTD,
    OUTPUT_STATUS,
    OUTPUT_UNMATCHED,
]:

    print(
        "-",
        path.name,
    )


print()
print("=" * 110)
print("COLLECTION COMPLETE")
print("=" * 110)