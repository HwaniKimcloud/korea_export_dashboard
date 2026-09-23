from pathlib import Path
import pandas as pd
import re


# ============================================================
# 1. 기본 설정
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "industry_data"

OFFICIAL_FILE = DATA_DIR / "2026 MTI-HSK 코드표_vFF_260507.xlsx"

OUTPUT_ALL = BASE_DIR / "official_mti_code_tree.csv"
OUTPUT_TARGET = BASE_DIR / "official_mti20_structure_candidates.csv"


if not OFFICIAL_FILE.exists():
    raise FileNotFoundError(
        f"파일을 찾을 수 없습니다:\n{OFFICIAL_FILE}"
    )


print()
print("=" * 110)
print("OFFICIAL MTI20 STRUCTURE PROBE")
print("=" * 110)


# ============================================================
# 2. 20대 산업 + 확장 Alias
# ============================================================

TARGETS = {

    "반도체": [
        "반도체"
    ],

    "자동차": [
        "자동차",
        "승용차"
    ],

    "자동차부품": [
        "자동차부품",
        "자동차 부품"
    ],

    "선박": [
        "선박",
        "해양구조물"
    ],

    "디스플레이": [
        "디스플레이",
        "평판디스플레이",
        "LCD",
        "OLED"
    ],

    "무선통신기기": [
        "무선통신기기",
        "무선통신"
    ],

    "컴퓨터": [
        "컴퓨터"
    ],

    "가전": [
        "가전",
        "가정용 전자제품",
        "가정용전기기기",
        "가정용 전기기기"
    ],

    "일반기계": [
        "일반기계",
        "산업기계",
        "기계요소",
        "공작기계",
        "제조장비",
        "에너지기계",
        "기계부품"
    ],

    "석유제품": [
        "석유제품"
    ],

    "석유화학": [
        "석유화학"
    ],

    "이차전지": [
        "이차전지",
        "2차전지",
        "배터리",
        "축전지",
        "리튬이온"
    ],

    "철강": [
        "철강"
    ],

    "비철금속": [
        "비철금속"
    ],

    "전기기기": [
        "전기기기",
        "전력기기"
    ],

    "바이오헬스": [
        "바이오헬스",
        "바이오",
        "의약품",
        "의료기기"
    ],

    "농수산식품": [
        "농수산식품",
        "농수산",
        "농산물",
        "수산물",
        "식품"
    ],

    "화장품": [
        "화장품"
    ],

    "생활용품": [
        "생활용품"
    ],

    "섬유": [
        "섬유"
    ],
}


# ============================================================
# 3. 코드 정리 함수
# ============================================================

def normalize_code(value):

    if pd.isna(value):
        return None

    text = str(value).strip()
    text = re.sub(r"\.0$", "", text)
    text = text.replace(",", "").replace(" ", "")

    if not re.fullmatch(r"\d{1,6}", text):
        return None

    return text


def clean_text(value):

    if pd.isna(value):
        return None

    text = str(value).strip()

    if text == "" or text.lower() == "nan":
        return None

    if re.fullmatch(r"[\d,.\-]+", text):
        return None

    return re.sub(r"\s+", " ", text)


# ============================================================
# 4. MTI 코드표 시트 찾기
# ============================================================

xls = pd.ExcelFile(OFFICIAL_FILE)

mti_sheet = None

for sheet in xls.sheet_names:

    normalized = str(sheet).replace(" ", "").upper()

    if "MTI코드표".upper() in normalized:
        mti_sheet = sheet
        break


if mti_sheet is None:
    raise ValueError("MTI코드표 시트를 찾지 못했습니다.")


print("사용 시트:", mti_sheet)


# ============================================================
# 5. 원본 읽기
# ============================================================

raw = pd.read_excel(
    OFFICIAL_FILE,
    sheet_name=mti_sheet,
    header=None
)

print(
    f"원본 크기: {len(raw):,}행 × {len(raw.columns):,}열"
)


# ============================================================
# 6. 코드-품목명 후보 추출
# ============================================================

records = []


for row_idx in range(len(raw)):

    row = raw.iloc[row_idx]

    code_positions = []
    text_positions = []

    for col_idx, value in enumerate(row):

        code = normalize_code(value)

        if code is not None:
            code_positions.append(
                (col_idx, code)
            )

        text = clean_text(value)

        if text is not None:
            text_positions.append(
                (col_idx, text)
            )


    if not code_positions or not text_positions:
        continue


    for code_col, code in code_positions:

        # 가장 가까운 오른쪽 텍스트 우선
        right_candidates = [
            (text_col, text)
            for text_col, text in text_positions
            if text_col > code_col
        ]

        if right_candidates:

            right_candidates.sort(
                key=lambda x: x[0] - code_col
            )

            text_col, name = right_candidates[0]

        else:

            # 오른쪽에 없으면 가장 가까운 텍스트
            candidates = sorted(
                text_positions,
                key=lambda x: abs(x[0] - code_col)
            )

            text_col, name = candidates[0]


        if abs(text_col - code_col) > 5:
            continue


        records.append({
            "MTI코드": code,
            "코드길이": len(code),
            "품목명": name,
            "행": row_idx,
            "코드열": code_col,
            "품목명열": text_col,
        })


tree = pd.DataFrame(records)


tree = (
    tree
    .drop_duplicates(
        subset=[
            "MTI코드",
            "품목명"
        ]
    )
    .sort_values(
        [
            "MTI코드",
            "코드길이"
        ]
    )
    .reset_index(drop=True)
)


print()
print("=" * 110)
print("공식 MTI 코드 Tree")
print("=" * 110)

print(
    "고유 코드:",
    tree["MTI코드"].nunique()
)

print(
    "코드 길이별 개수:"
)

print(
    tree.groupby("코드길이")["MTI코드"]
    .nunique()
    .to_string()
)


# ============================================================
# 7. 산업별 직접 검색
# ============================================================

candidate_rows = []


for industry, aliases in TARGETS.items():

    print()
    print("=" * 110)
    print(f"[{industry}]")
    print("=" * 110)

    industry_matches = []

    for alias in aliases:

        temp = tree[
            tree["품목명"]
            .astype(str)
            .str.contains(
                alias,
                case=False,
                na=False,
                regex=False
            )
        ].copy()

        if temp.empty:
            continue

        temp["산업"] = industry
        temp["검색어"] = alias

        industry_matches.append(temp)


    if not industry_matches:

        print("직접 검색 결과 없음")
        continue


    combined = (
        pd.concat(
            industry_matches,
            ignore_index=True
        )
        .drop_duplicates(
            subset=[
                "MTI코드",
                "품목명"
            ]
        )
        .sort_values(
            [
                "코드길이",
                "MTI코드"
            ]
        )
    )


    print(
        combined[
            [
                "MTI코드",
                "코드길이",
                "품목명",
                "검색어"
            ]
        ]
        .head(100)
        .to_string(index=False)
    )


    candidate_rows.append(
        combined
    )


# ============================================================
# 8. 전체 후보 통합
# ============================================================

if candidate_rows:

    candidates = pd.concat(
        candidate_rows,
        ignore_index=True
    )

else:

    candidates = pd.DataFrame()


# ============================================================
# 9. 각 후보의 하위 MTI6 개수 계산
# ============================================================

MTI6_MASTER = BASE_DIR / "mti6_master_1291.csv"

mti6 = pd.read_csv(
    MTI6_MASTER,
    dtype=str
)

mti6["MTI6코드"] = (
    mti6["MTI6코드"]
    .astype(str)
    .str.zfill(6)
)


if not candidates.empty:

    child_counts = []

    for _, row in candidates.iterrows():

        prefix = str(
            row["MTI코드"]
        )

        child_count = (
            mti6["MTI6코드"]
            .str.startswith(prefix)
            .sum()
        )

        child_counts.append(
            child_count
        )


    candidates[
        "하위_MTI6_개수"
    ] = child_counts


# ============================================================
# 10. 산업별 핵심 후보 출력
# ============================================================

print()
print("=" * 110)
print("20대 산업 핵심 구조 후보")
print("=" * 110)


for industry in TARGETS.keys():

    if candidates.empty:
        continue

    temp = candidates[
        candidates["산업"]
        ==
        industry
    ].copy()

    if temp.empty:

        print()
        print(
            f"{industry}: 후보 없음"
        )

        continue


    temp = temp.sort_values(
        [
            "코드길이",
            "하위_MTI6_개수",
            "MTI코드"
        ],
        ascending=[
            True,
            False,
            True
        ]
    )


    print()
    print(
        f"[{industry}]"
    )

    print(
        temp[
            [
                "MTI코드",
                "코드길이",
                "품목명",
                "하위_MTI6_개수"
            ]
        ]
        .head(30)
        .to_string(index=False)
    )


# ============================================================
# 11. 특히 미매핑 4개 산업 강조
# ============================================================

PROBLEM_TARGETS = [
    "가전",
    "일반기계",
    "이차전지",
    "농수산식품",
]


print()
print("=" * 110)
print("미매핑 4개 산업 집중 점검")
print("=" * 110)


for industry in PROBLEM_TARGETS:

    print()
    print("-" * 110)
    print(industry)
    print("-" * 110)

    if candidates.empty:

        print("후보 없음")
        continue


    temp = candidates[
        candidates["산업"]
        ==
        industry
    ].copy()


    if temp.empty:

        print("후보 없음")
        continue


    print(
        temp[
            [
                "MTI코드",
                "코드길이",
                "품목명",
                "검색어",
                "하위_MTI6_개수"
            ]
        ]
        .sort_values(
            [
                "코드길이",
                "MTI코드"
            ]
        )
        .head(100)
        .to_string(index=False)
    )


# ============================================================
# 12. CSV 저장
# ============================================================

tree.to_csv(
    OUTPUT_ALL,
    index=False,
    encoding="utf-8-sig"
)


if not candidates.empty:

    candidates.to_csv(
        OUTPUT_TARGET,
        index=False,
        encoding="utf-8-sig"
    )


print()
print("=" * 110)
print("CSV 저장 완료")
print("=" * 110)

print("- official_mti_code_tree.csv")

if not candidates.empty:
    print("- official_mti20_structure_candidates.csv")


print()
print("=" * 110)
print("STRUCTURE PROBE COMPLETE")
print("=" * 110)