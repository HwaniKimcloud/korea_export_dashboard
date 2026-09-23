from pathlib import Path
import time
import urllib.parse
import xml.etree.ElementTree as ET

import pandas as pd
import requests
import truststore


# ============================================================
# 0. SSL 설정
# ============================================================

truststore.inject_into_ssl()


# ============================================================
# 1. 기본 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MAPPING_FILE = BASE_DIR / "official_mti20_master.csv"
KITA_REFERENCE_FILE = BASE_DIR / "industry_monthly.csv"

OUTPUT_RAW = BASE_DIR / "semiconductor_hsk10_raw.csv"
OUTPUT_MONTHLY = BASE_DIR / "semiconductor_customs_monthly.csv"
OUTPUT_RECON = BASE_DIR / "semiconductor_reconciliation.csv"


# ============================================================
# 2. 관세청 API
# ============================================================

URL = "https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList"

# 본인의 기존 관세청 API 서비스키를 아래에 입력
SERVICE_KEY = "Jqr042WhXmRju%2F2E4uTPkTQqeJWPrWOjV2YRbdOkdF5B6QuZwyE5p1%2BJ1z1vLG6n2ZKpJBVejEavVIIWG8CrKQ%3D%3D"

# Encoding key를 사용하는 경우 decode
SERVICE_KEY = urllib.parse.unquote(SERVICE_KEY)


# ============================================================
# 3. 조회 기간
# ============================================================

PERIODS = [
    ("202501", "202512"),
    ("202601", "202607"),
]

TARGET_INDUSTRY = "반도체"


# ============================================================
# 4. 유틸리티 함수
# ============================================================

def clean_code(value, length):
    if pd.isna(value):
        return None

    text = str(value).strip()
    text = text.replace(".0", "")
    text = "".join(ch for ch in text if ch.isdigit())

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


# ============================================================
# 5. 관세청 API 호출 함수
# ============================================================

def fetch_hsk10(hsk10, start_ym, end_ym, max_retry=3):

    params = {
        "serviceKey": SERVICE_KEY,
        "strtYymm": start_ym,
        "endYymm": end_ym,
        "hsSgn": hsk10,
    }

    last_error = None

    for attempt in range(1, max_retry + 1):

        try:
            response = requests.get(
                URL,
                params=params,
                timeout=30
            )

            response.raise_for_status()

            root = ET.fromstring(response.content)

            result_code = (
                root.findtext(".//resultCode")
                or root.findtext(".//returnReasonCode")
            )

            result_msg = (
                root.findtext(".//resultMsg")
                or ""
            )

            if result_code not in [None, "00", "0"]:
                raise RuntimeError(
                    f"API 오류 {result_code}: {result_msg}"
                )

            rows = []

            for item in root.findall(".//item"):

                year_month = get_text(
                    item,
                    [
                        "year",
                        "period",
                        "baseYm",
                        "yymm",
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

                returned_hs = get_text(
                    item,
                    [
                        "hsSgn",
                        "hsCd",
                        "hsCode",
                    ]
                )

                if year_month is None:
                    continue

                ym = (
                    str(year_month)
                    .replace(".", "")
                    .replace("-", "")
                    .replace("/", "")
                    .strip()
                )

                if len(ym) >= 6:
                    ym = ym[:6]

                if not (
                    ym.isdigit()
                    and len(ym) == 6
                ):
                    continue

                rows.append(
                    {
                        "기준월": ym,
                        "HSK10": clean_code(
                            returned_hs if returned_hs else hsk10,
                            10
                        ),
                        "요청_HSK10": hsk10,
                        "수출액_USD": to_number(export_value),
                    }
                )

            return pd.DataFrame(rows)

        except Exception as e:

            last_error = e

            if attempt < max_retry:
                time.sleep(1.5 * attempt)

    print(
        f"[FAIL] {hsk10} "
        f"{start_ym}~{end_ym} : {last_error}"
    )

    return pd.DataFrame()


# ============================================================
# 6. 공식 20대 산업 Master 읽기
# ============================================================

if not MAPPING_FILE.exists():
    raise FileNotFoundError(
        f"파일을 찾을 수 없습니다:\n{MAPPING_FILE}"
    )


mapping = pd.read_csv(
    MAPPING_FILE,
    dtype=str
)


mapping["HSK10"] = (
    mapping["HSK10"]
    .apply(lambda x: clean_code(x, 10))
)


semi = (
    mapping[
        mapping["산업20"] == TARGET_INDUSTRY
    ]
    .copy()
)


hsk_codes = (
    semi["HSK10"]
    .dropna()
    .drop_duplicates()
    .sort_values()
    .tolist()
)


print()
print("=" * 100)
print("SEMICONDUCTOR EXACT RECONCILIATION")
print("=" * 100)

print(
    f"반도체 HSK10 코드 수 : "
    f"{len(hsk_codes):,}"
)

print(
    f"반도체 MTI6 코드 수  : "
    f"{semi['MTI6'].nunique():,}"
)


if not hsk_codes:
    raise RuntimeError(
        "반도체 HSK10 코드가 없습니다."
    )


# ============================================================
# 7. 관세청 HSK10 데이터 수집
# ============================================================

all_frames = []

total_requests = (
    len(hsk_codes)
    * len(PERIODS)
)

request_no = 0


print()
print("=" * 100)
print("관세청 HSK10 데이터 수집")
print("=" * 100)


for hsk10 in hsk_codes:

    for start_ym, end_ym in PERIODS:

        request_no += 1

        print(
            f"[{request_no:>4}/{total_requests}] "
            f"HSK {hsk10} "
            f"{start_ym}~{end_ym}"
        )

        temp = fetch_hsk10(
            hsk10,
            start_ym,
            end_ym
        )

        if not temp.empty:
            all_frames.append(temp)

        time.sleep(0.08)


if not all_frames:
    raise RuntimeError(
        "관세청 API에서 데이터를 가져오지 못했습니다."
    )


raw = pd.concat(
    all_frames,
    ignore_index=True
)


# ============================================================
# 8. 동일 HSK / 월 중복 정리
# ============================================================

raw = (
    raw
    .groupby(
        [
            "기준월",
            "요청_HSK10"
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


raw["기준월"] = pd.to_datetime(
    raw["기준월"],
    format="%Y%m"
)


raw.to_csv(
    OUTPUT_RAW,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 9. 반도체 월별 합산
# ============================================================

monthly = (
    raw
    .groupby(
        "기준월",
        as_index=False
    )
    .agg(
        관세청_HSK합산_USD=(
            "수출액_USD",
            "sum"
        )
    )
    .sort_values("기준월")
    .reset_index(drop=True)
)


monthly["관세청_HSK합산_bn"] = (
    monthly["관세청_HSK합산_USD"]
    / 1e9
)


monthly["YoY_%"] = (
    monthly["관세청_HSK합산_USD"]
    .pct_change(12)
    * 100
)


monthly.to_csv(
    OUTPUT_MONTHLY,
    index=False,
    encoding="utf-8-sig"
)


print()
print("=" * 100)
print("관세청 기준 반도체 월별 수출")
print("=" * 100)

print(
    monthly.to_string(index=False)
)


# ============================================================
# 10. KITA Reference 읽기
# ============================================================

print()
print("=" * 100)
print("KITA REFERENCE RECONCILIATION")
print("=" * 100)


if not KITA_REFERENCE_FILE.exists():

    print(
        "industry_monthly.csv가 없어 "
        "관세청 합산 결과만 생성했습니다."
    )

    recon = monthly.copy()

else:

    kita = pd.read_csv(
        KITA_REFERENCE_FILE
    )


    # --------------------------------------------------------
    # 기준월 확인
    # --------------------------------------------------------

    if "기준월" not in kita.columns:
        raise ValueError(
            "industry_monthly.csv에 "
            "'기준월' 열이 없습니다."
        )


    kita["기준월"] = pd.to_datetime(
        kita["기준월"]
    )


    # --------------------------------------------------------
    # 반도체만 선택
    # --------------------------------------------------------

    if "산업" not in kita.columns:
        raise ValueError(
            "industry_monthly.csv에 "
            "'산업' 열이 없습니다."
        )


    kita = kita[
        kita["산업"]
        .astype(str)
        .str.contains(
            "반도체",
            na=False
        )
    ].copy()


    # ========================================================
    # 정확 금액 컬럼 탐색
    # ========================================================

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


    # ========================================================
    # CASE A
    # KITA 정확 금액 컬럼이 있는 경우
    # ========================================================

    if exact_col is not None:

        kita["KITA_공식_USD"] = pd.to_numeric(
            kita[exact_col],
            errors="coerce"
        )


        recon = monthly.merge(
            kita[
                [
                    "기준월",
                    "KITA_공식_USD"
                ]
            ],
            on="기준월",
            how="left"
        )


        # ====================================================
        # KITA 공표단위 = 천 달러
        #
        # 관세청은 달러 단위.
        # KITA는 천 달러 단위로 반올림된 값을 제공.
        #
        # 따라서 달러 단위 차이 = 0을 요구하면 안 됨.
        # 동일한 천 달러 단위로 변환 후 비교.
        # ====================================================

        recon["관세청_천USD"] = (
            recon["관세청_HSK합산_USD"]
            / 1000
        ).round().astype("Int64")


        recon["KITA_천USD"] = (
            recon["KITA_공식_USD"]
            / 1000
        ).round().astype("Int64")


        recon["차이_천USD"] = (
            recon["관세청_천USD"]
            -
            recon["KITA_천USD"]
        )


        # 참고용 원자료 달러 차이
        recon["원자료_차이_USD"] = (
            recon["관세청_HSK합산_USD"]
            -
            recon["KITA_공식_USD"]
        )


        # ====================================================
        # Exact PASS 기준
        #
        # KITA 공식 공표단위(천 달러)에서
        # 정확히 동일해야 PASS
        # ====================================================

        recon["Exact_PASS"] = (
            recon["차이_천USD"] == 0
        )


        print()
        print(
            recon[
                [
                    "기준월",
                    "관세청_HSK합산_USD",
                    "관세청_천USD",
                    "KITA_천USD",
                    "차이_천USD",
                    "원자료_차이_USD",
                    "Exact_PASS",
                ]
            ].to_string(index=False)
        )


        valid = recon[
            recon["KITA_공식_USD"].notna()
        ].copy()


        exact_months = int(
            valid["Exact_PASS"]
            .fillna(False)
            .sum()
        )


        print()
        print("=" * 100)
        print("EXACT RECONCILIATION RESULT")
        print("=" * 100)

        print(
            f"Exact 비교 가능 월 : {len(valid)}"
        )

        print(
            f"차이 0 월          : {exact_months}"
        )


        if (
            len(valid) > 0
            and exact_months == len(valid)
        ):

            print()
            print(
                "SEMICONDUCTOR EXACT "
                "RECONCILIATION : PASS"
            )

        else:

            print()
            print(
                "SEMICONDUCTOR "
                "RECONCILIATION : REVIEW REQUIRED"
            )


            failed = valid[
                ~valid["Exact_PASS"].fillna(False)
            ]


            if not failed.empty:

                print()
                print("불일치 월:")

                print(
                    failed[
                        [
                            "기준월",
                            "관세청_천USD",
                            "KITA_천USD",
                            "차이_천USD",
                            "원자료_차이_USD",
                        ]
                    ].to_string(index=False)
                )


    # ========================================================
    # CASE B
    # 십억 달러 가공값만 있는 경우
    # ========================================================

    elif "수출액_십억달러" in kita.columns:

        kita["KITA_bn"] = pd.to_numeric(
            kita["수출액_십억달러"],
            errors="coerce"
        )


        recon = monthly.merge(
            kita[
                [
                    "기준월",
                    "KITA_bn"
                ]
            ],
            on="기준월",
            how="left"
        )


        recon["차이_bn"] = (
            recon["관세청_HSK합산_bn"]
            -
            recon["KITA_bn"]
        )


        print(
            recon[
                [
                    "기준월",
                    "관세청_HSK합산_bn",
                    "KITA_bn",
                    "차이_bn"
                ]
            ].to_string(index=False)
        )


        print()
        print(
            "주의: KITA 데이터가 십억달러 "
            "가공값이므로 Exact 판정을 하지 않습니다."
        )


    # ========================================================
    # CASE C
    # 사용할 수 있는 금액 컬럼 없음
    # ========================================================

    else:

        print(
            "KITA 금액 컬럼을 찾지 못했습니다."
        )

        print(
            "industry_monthly.csv의 컬럼:"
        )

        print(
            list(kita.columns)
        )

        recon = monthly.copy()


    # ========================================================
    # 대사 결과 저장
    # ========================================================

    recon.to_csv(
        OUTPUT_RECON,
        index=False,
        encoding="utf-8-sig"
    )


# ============================================================
# 11. 저장 결과
# ============================================================

print()
print("=" * 100)
print("CSV 저장 완료")
print("=" * 100)

print(
    "- semiconductor_hsk10_raw.csv"
)

print(
    "- semiconductor_customs_monthly.csv"
)

if KITA_REFERENCE_FILE.exists():
    print(
        "- semiconductor_reconciliation.csv"
    )


print()
print("=" * 100)
print("SEMICONDUCTOR TEST COMPLETE")
print("=" * 100)