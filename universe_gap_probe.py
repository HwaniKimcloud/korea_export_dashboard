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
# 1. 기본 설정
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MASTER_FILE = BASE_DIR / "official_hsk_mti_master.csv"
TOTAL_FILE = BASE_DIR / "korea_total_export_monthly.csv"

OUTPUT_ALL = BASE_DIR / "universe_gap_202607_all_hsk.csv"
OUTPUT_MISSING = BASE_DIR / "universe_gap_202607_missing_hsk.csv"
OUTPUT_SUMMARY = BASE_DIR / "universe_gap_202607_summary.csv"


URL = "https://apis.data.go.kr/1220000/Itemtrade/getItemtradeList"

# 기존에 사용하던 본인의 API Key 입력
SERVICE_KEY = "Jqr042WhXmRju%2F2E4uTPkTQqeJWPrWOjV2YRbdOkdF5B6QuZwyE5p1%2BJ1z1vLG6n2ZKpJBVejEavVIIWG8CrKQ%3D%3D"
SERVICE_KEY = urllib.parse.unquote(SERVICE_KEY)


TARGET_YM = "202607"


# ============================================================
# 2. 유틸
# ============================================================

def clean_code(value, length=10):

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


def get_text(item, names):

    for name in names:

        value = item.findtext(name)

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

    try:
        return float(text)

    except Exception:
        return 0.0


# ============================================================
# 3. HS2 API
# ============================================================

def fetch_hs2(hs2, max_retry=3):

    params = {
        "serviceKey": SERVICE_KEY,
        "strtYymm": TARGET_YM,
        "endYymm": TARGET_YM,
        "hsSgn": hs2,
    }

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


            if result_code not in [
                None,
                "00",
                "0"
            ]:

                raise RuntimeError(
                    f"API ERROR: {result_code}"
                )


            rows = []


            for item in root.findall(
                ".//item"
            ):

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


                hsk10 = clean_code(
                    hs,
                    10
                )


                if hsk10 is None:
                    continue


                rows.append(
                    {
                        "HSK10": hsk10,
                        "수출액_USD": to_number(exp),
                        "HS2": hs2,
                    }
                )


            return pd.DataFrame(
                rows
            )


        except Exception as e:

            if attempt == max_retry:

                print(
                    f"[FAIL] HS2 {hs2}: {e}"
                )

                return pd.DataFrame()


            time.sleep(
                2 * attempt
            )


# ============================================================
# 4. Master
# ============================================================

master = pd.read_csv(
    MASTER_FILE,
    dtype=str
)


master["HSK10"] = (
    master["HSK10"]
    .apply(clean_code)
)


master_codes = set(
    master["HSK10"]
    .dropna()
    .unique()
)


print()
print("=" * 100)
print("UNIVERSE GAP PROBE")
print("=" * 100)

print(
    f"Master HSK10: "
    f"{len(master_codes):,}"
)


# ============================================================
# 5. HS Chapter 전체 조회
#
# 01~97
# ============================================================

frames = []


for chapter in range(
    1,
    100
):

    hs2 = f"{chapter:02d}"

    print(
        f"[{hs2}/97] 수집 중..."
    )

    temp = fetch_hs2(
        hs2
    )

    if not temp.empty:
        frames.append(
            temp
        )

    time.sleep(0.08)


if not frames:

    raise RuntimeError(
        "관세청 데이터를 받지 못했습니다."
    )


all_hsk = pd.concat(
    frames,
    ignore_index=True
)


all_hsk = (
    all_hsk
    .groupby(
        "HSK10",
        as_index=False
    )
    .agg(
        수출액_USD=(
            "수출액_USD",
            "sum"
        )
    )
)


all_hsk[
    "Master포함"
] = (
    all_hsk["HSK10"]
    .isin(
        master_codes
    )
)


all_hsk.to_csv(
    OUTPUT_ALL,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 6. Master에 없는 활성 HSK
# ============================================================

missing = (
    all_hsk[
        ~all_hsk["Master포함"]
    ]
    .copy()
)


# 실제 수출액 > 0만
missing = missing[
    missing["수출액_USD"] != 0
].copy()


missing = (
    missing
    .sort_values(
        "수출액_USD",
        ascending=False
    )
    .reset_index(drop=True)
)


missing[
    "수출액_mn"
] = (
    missing[
        "수출액_USD"
    ]
    / 1e6
)


missing.to_csv(
    OUTPUT_MISSING,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 7. Gap 합계
# ============================================================

missing_total = (
    missing[
        "수출액_USD"
    ]
    .sum()
)


all_total = (
    all_hsk[
        "수출액_USD"
    ]
    .sum()
)


mapped_total = (
    all_hsk[
        all_hsk["Master포함"]
    ][
        "수출액_USD"
    ]
    .sum()
)


print()
print("=" * 100)
print("GAP RESULT")
print("=" * 100)

print(
    f"관세청 활성 HSK10 수 : "
    f"{all_hsk['HSK10'].nunique():,}"
)

print(
    f"Master 포함 HSK10    : "
    f"{all_hsk[all_hsk['Master포함']]['HSK10'].nunique():,}"
)

print(
    f"Master 미포함 HSK10  : "
    f"{missing['HSK10'].nunique():,}"
)


print()
print(
    f"전체 HSK 합계       : "
    f"${all_total / 1e9:,.6f}bn"
)

print(
    f"Master 포함 합계    : "
    f"${mapped_total / 1e9:,.6f}bn"
)

print(
    f"Master 미포함 합계  : "
    f"${missing_total / 1e6:,.3f}mn"
)


# ============================================================
# 8. 상위 Missing Codes
# ============================================================

print()
print("=" * 100)
print("TOP MISSING HSK10")
print("=" * 100)


if missing.empty:

    print(
        "미매핑 활성 HSK10 없음"
    )

else:

    print(
        missing.head(50)
        .to_string(
            index=False
        )
    )


# ============================================================
# 9. Summary 저장
# ============================================================

summary = pd.DataFrame(
    [
        {
            "기준월": TARGET_YM,

            "전체_활성HSK10":
                all_hsk[
                    "HSK10"
                ].nunique(),

            "Master포함_HSK10":
                all_hsk[
                    all_hsk[
                        "Master포함"
                    ]
                ][
                    "HSK10"
                ].nunique(),

            "Master미포함_HSK10":
                missing[
                    "HSK10"
                ].nunique(),

            "전체수출_USD":
                all_total,

            "Master포함_USD":
                mapped_total,

            "Master미포함_USD":
                missing_total,

            "Missing_Coverage_%":
                (
                    missing_total
                    /
                    all_total
                    *
                    100
                )
                if all_total != 0
                else 0,
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
    "- universe_gap_202607_all_hsk.csv"
)

print(
    "- universe_gap_202607_missing_hsk.csv"
)

print(
    "- universe_gap_202607_summary.csv"
)


print()
print("=" * 100)
print("GAP PROBE COMPLETE")
print("=" * 100)