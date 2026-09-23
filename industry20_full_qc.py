from pathlib import Path
import pandas as pd
import re


# ============================================================
# 1. 기본 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

CUSTOMS_FILE = BASE_DIR / "industry20_monthly.csv"
MAPPING_FILE = BASE_DIR / "official_mti20_master.csv"

# KITA MTI6 원본 파일이 저장된 폴더
INDUSTRY_DATA_DIR = BASE_DIR / "industry_data"

MTI_FILES = sorted(
    INDUSTRY_DATA_DIR.glob("KITA_MTI6_*.XLS")
) + sorted(
    INDUSTRY_DATA_DIR.glob("KITA_MTI6_*.xls")
)

OUTPUT_KITA_REF = BASE_DIR / "industry20_kita_reference.csv"
OUTPUT_QC = BASE_DIR / "industry20_full_qc_detail.csv"
OUTPUT_SUMMARY = BASE_DIR / "industry20_full_qc_summary.csv"
OUTPUT_FAIL = BASE_DIR / "industry20_full_qc_failures.csv"


# ============================================================
# 2. 입력 확인
# ============================================================

if not CUSTOMS_FILE.exists():
    raise FileNotFoundError(CUSTOMS_FILE)

if not MAPPING_FILE.exists():
    raise FileNotFoundError(MAPPING_FILE)

if not MTI_FILES:
    raise FileNotFoundError(
        "KITA_MTI6_01.XLS ~ KITA_MTI6_13.XLS 파일을 찾지 못했습니다."
    )


print()
print("=" * 100)
print("20 INDUSTRY FULL QC")
print("=" * 100)

print(f"KITA MTI6 파일 수 : {len(MTI_FILES)}")


# ============================================================
# 3. Mapping 읽기
# ============================================================

mapping = pd.read_csv(
    MAPPING_FILE,
    dtype=str
)


mapping["MTI6"] = (
    mapping["MTI6"]
    .astype(str)
    .str.replace(".0", "", regex=False)
    .str.zfill(6)
)


mti_to_industry = (
    mapping[
        [
            "MTI6",
            "산업20"
        ]
    ]
    .drop_duplicates()
)


# MTI6가 복수 산업에 걸치는지 확인
dup_check = (
    mti_to_industry
    .groupby("MTI6")["산업20"]
    .nunique()
)

dup_codes = dup_check[
    dup_check > 1
]

if len(dup_codes) > 0:
    raise RuntimeError(
        f"복수 산업에 매핑된 MTI6가 {len(dup_codes)}개 있습니다."
    )


print(
    "공식 MTI6 → 산업20 Mapping:",
    f"{mti_to_industry['MTI6'].nunique():,}"
)


# ============================================================
# 4. KITA MTI6 파일 읽기
# ============================================================

raw_frames = []


for file in MTI_FILES:

    print(f"읽는 중: {file.name}")

    raw = pd.read_excel(
        file,
        header=None
    )

    raw["원본파일"] = file.name

    raw_frames.append(
        raw
    )


all_raw = pd.concat(
    raw_frames,
    ignore_index=True
)


print(
    "전체 원본 행:",
    f"{len(all_raw):,}"
)


# ============================================================
# 5. MTI6 코드 후보 추출
#
# 각 행에서 6자리 숫자 코드 탐색
# ============================================================

records = []


for _, row in all_raw.iterrows():

    values = row.tolist()

    mti6 = None

    for value in values:

        if pd.isna(value):
            continue

        text = str(value).strip()
        text = re.sub(r"\.0$", "", text)
        text = text.replace(",", "")

        if re.fullmatch(r"\d{6}", text):

            if text in set(
                mti_to_industry["MTI6"]
            ):
                mti6 = text
                break


    if mti6 is None:
        continue


    records.append(
        {
            "MTI6": mti6,
            "원본행": values,
        }
    )


print(
    "MTI6 인식 행:",
    f"{len(records):,}"
)


# ============================================================
# 6. 월별 금액 파싱
#
# 이미 다운받은 KITA 파일은 기간별 누적표이므로
# 현재 파일 구조상 직접 월별 금액이 행 안에 있지 않을 수 있음.
#
# 그래서 여기서는 컬럼 구조를 먼저 자동 진단.
# ============================================================

print()
print("=" * 100)
print("KITA FILE STRUCTURE DIAGNOSIS")
print("=" * 100)


sample = all_raw.head(40)

print(
    sample.to_string(
        index=False,
        header=False
    )
)


# ============================================================
# 7. 컬럼별 데이터 형태 분석
# ============================================================

column_stats = []

for col in all_raw.columns:

    if col == "원본파일":
        continue

    series = all_raw[col].dropna()

    numeric_count = 0
    ym_count = 0
    mti6_count = 0

    for value in series.head(5000):

        text = str(value).strip()
        text2 = re.sub(r"\.0$", "", text)
        text2 = text2.replace(",", "")

        if re.fullmatch(r"\d{6}", text2):
            mti6_count += 1

        if re.fullmatch(r"20\d{4}", text2):
            ym_count += 1

        try:
            float(text2)
            numeric_count += 1
        except Exception:
            pass


    column_stats.append(
        {
            "열": col,
            "비어있지않은셀": len(series),
            "숫자셀": numeric_count,
            "6자리코드": mti6_count,
            "YYYYMM": ym_count,
        }
    )


stats_df = pd.DataFrame(
    column_stats
)


print()
print(
    stats_df.to_string(
        index=False
    )
)


print()
print("=" * 100)
print("STEP 1 COMPLETE")
print("=" * 100)

print(
    "다음 단계에서는 위 구조를 기준으로 "
    "KITA MTI6 월별 금액 열을 정확히 파싱합니다."
)