from pathlib import Path
import pandas as pd
import re


# ============================================================
# 1. 기본 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "industry_data"

OFFICIAL_FILE = DATA_DIR / "2026 MTI-HSK 코드표_vFF_260507.xlsx"
MTI6_MASTER_FILE = BASE_DIR / "mti6_master_1291.csv"

OUTPUT_MAPPING = BASE_DIR / "mti20_official_mapping.csv"
OUTPUT_SUMMARY = BASE_DIR / "mti20_official_summary.csv"
OUTPUT_RULES = BASE_DIR / "mti20_official_rules.csv"
OUTPUT_REVIEW = BASE_DIR / "mti20_official_review.csv"


# ============================================================
# 2. 입력 파일 확인
# ============================================================

for file in [
    OFFICIAL_FILE,
    MTI6_MASTER_FILE,
]:
    if not file.exists():
        raise FileNotFoundError(
            f"파일을 찾을 수 없습니다:\n{file}"
        )


print()
print("=" * 110)
print("OFFICIAL MTI20 MAPPING BUILDER")
print("=" * 110)

print("공식 코드표 :", OFFICIAL_FILE.name)
print("MTI6 Master :", MTI6_MASTER_FILE.name)


# ============================================================
# 3. 20대 산업
# ============================================================

TARGET_INDUSTRIES = [
    "반도체",
    "자동차",
    "자동차부품",
    "선박",
    "디스플레이",
    "무선통신기기",
    "컴퓨터",
    "가전",
    "일반기계",
    "석유제품",
    "석유화학",
    "이차전지",
    "철강",
    "비철금속",
    "전기기기",
    "바이오헬스",
    "농수산식품",
    "화장품",
    "생활용품",
    "섬유",
]


# ============================================================
# 4. 명칭 보조 Alias
#
# 공식 코드표의 명칭이 산업부 표현과 조금 다를 수 있으므로
# 상위 코드 탐색에만 사용합니다.
# 최종 MTI6 확장은 "코드 prefix"로 처리합니다.
# ============================================================

ALIASES = {

    "반도체": [
        "반도체"
    ],

    "자동차": [
        "자동차"
    ],

    "자동차부품": [
        "자동차부품",
        "자동차 부품"
    ],

    "선박": [
        "선박"
    ],

    "디스플레이": [
        "디스플레이",
        "평판디스플레이"
    ],

    "무선통신기기": [
        "무선통신기기",
        "무선통신"
    ],

    "컴퓨터": [
        "컴퓨터"
    ],

    "가전": [
        "가전"
    ],

    "일반기계": [
        "일반기계"
    ],

    "석유제품": [
        "석유제품"
    ],

    "석유화학": [
        "석유화학"
    ],

    "이차전지": [
        "이차전지",
        "배터리"
    ],

    "철강": [
        "철강"
    ],

    "비철금속": [
        "비철금속"
    ],

    "전기기기": [
        "전기기기"
    ],

    "바이오헬스": [
        "바이오헬스",
        "바이오"
    ],

    "농수산식품": [
        "농수산식품",
        "농수산"
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
# 5. 문자열 / 코드 정리 함수
# ============================================================

def clean_text(value):

    if pd.isna(value):
        return None

    text = str(value).strip()

    if text == "":
        return None

    if text.lower() == "nan":
        return None

    text = re.sub(r"\s+", " ", text)

    return text


def normalize_mti_code(value):
    """
    MTI 코드를 문자열로 정리.
    1~6자리 코드 허용.
    """

    if pd.isna(value):
        return None

    text = str(value).strip()

    # Excel 숫자형 831.0 대응
    text = re.sub(r"\.0$", "", text)

    # 쉼표/공백 제거
    text = text.replace(",", "")
    text = text.replace(" ", "")

    if not re.fullmatch(r"\d{1,6}", text):
        return None

    return text


# ============================================================
# 6. MTI6 Master 읽기
# ============================================================

mti6 = pd.read_csv(
    MTI6_MASTER_FILE,
    dtype=str
)


if "MTI6코드" not in mti6.columns:
    raise ValueError(
        "mti6_master_1291.csv에 'MTI6코드' 열이 없습니다."
    )


if "품목명" not in mti6.columns:
    raise ValueError(
        "mti6_master_1291.csv에 '품목명' 열이 없습니다."
    )


mti6["MTI6코드"] = (
    mti6["MTI6코드"]
    .astype(str)
    .str.strip()
    .str.zfill(6)
)


print()
print("=" * 110)
print("MTI6 MASTER")
print("=" * 110)

print(
    "MTI6 고유 코드:",
    mti6["MTI6코드"].nunique()
)


# ============================================================
# 7. 공식 Excel 시트 확인
# ============================================================

xls = pd.ExcelFile(
    OFFICIAL_FILE
)

print()
print("=" * 110)
print("공식 파일 시트")
print("=" * 110)

for sheet in xls.sheet_names:
    print("-", sheet)


# ============================================================
# 8. MTI코드표 시트 선택
# ============================================================

mti_sheet = None

for sheet in xls.sheet_names:

    normalized = (
        str(sheet)
        .replace(" ", "")
        .lower()
    )

    if "mti코드표".lower() in normalized:
        mti_sheet = sheet
        break


if mti_sheet is None:

    for sheet in xls.sheet_names:

        if "MTI" in str(sheet).upper():
            mti_sheet = sheet
            break


if mti_sheet is None:
    raise ValueError(
        "MTI 코드표 시트를 찾지 못했습니다."
    )


print()
print(
    "사용 MTI 시트:",
    mti_sheet
)


# ============================================================
# 9. MTI 코드표 전체 읽기
# ============================================================

raw = pd.read_excel(
    OFFICIAL_FILE,
    sheet_name=mti_sheet,
    header=None
)


print(
    f"MTI 코드표 크기: "
    f"{len(raw):,}행 × {len(raw.columns):,}열"
)


# ============================================================
# 10. 모든 셀에서
#     MTI 코드 + 품목명 관계 후보 탐색
#
# 같은 행 안에서:
# 숫자형 MTI 코드 셀 + 텍스트 셀
# 관계를 최대한 보수적으로 추출
# ============================================================

official_records = []


for row_idx in range(len(raw)):

    row = raw.iloc[row_idx]

    code_cells = []
    text_cells = []

    for col_idx, value in enumerate(row):

        code = normalize_mti_code(value)

        if code is not None:
            code_cells.append(
                (
                    col_idx,
                    code
                )
            )

        text = clean_text(value)

        if text is not None:

            # 숫자만 있는 셀은 품목명 후보 제외
            if not re.fullmatch(
                r"[\d,.]+",
                text
            ):
                text_cells.append(
                    (
                        col_idx,
                        text
                    )
                )


    if not code_cells:
        continue

    if not text_cells:
        continue


    for code_col, code in code_cells:

        # 가장 가까운 텍스트 셀을 우선 연결
        candidates = []

        for text_col, text in text_cells:

            distance = abs(
                text_col - code_col
            )

            candidates.append(
                (
                    distance,
                    text_col,
                    text
                )
            )


        candidates.sort(
            key=lambda x: x[0]
        )


        # 너무 멀리 있는 텍스트는 제외
        for distance, text_col, text in candidates[:3]:

            if distance > 5:
                continue

            official_records.append({
                "공식MTI코드": code,
                "공식품목명": text,
                "행": row_idx,
                "코드열": code_col,
                "품목명열": text_col,
                "거리": distance,
            })


official = pd.DataFrame(
    official_records
)


if official.empty:
    raise ValueError(
        "공식 MTI 코드/품목명 관계를 추출하지 못했습니다."
    )


# 동일 코드/명칭 중복 제거
official = (
    official
    .drop_duplicates(
        subset=[
            "공식MTI코드",
            "공식품목명"
        ]
    )
    .reset_index(drop=True)
)


print()
print("=" * 110)
print("공식 MTI 후보")
print("=" * 110)

print(
    "추출 관계 수:",
    len(official)
)

print(
    "고유 MTI 코드:",
    official["공식MTI코드"].nunique()
)


# ============================================================
# 11. 산업별 공식 상위코드 탐색
# ============================================================

rule_records = []


for industry in TARGET_INDUSTRIES:

    aliases = ALIASES[
        industry
    ]

    matches = []

    for _, row in official.iterrows():

        name = str(
            row["공식품목명"]
        ).strip()

        for alias in aliases:

            if alias.lower() in name.lower():

                score = 0

                # 완전 일치
                if (
                    name.replace(" ", "")
                    ==
                    alias.replace(" ", "")
                ):
                    score += 100

                # 명칭 시작
                if (
                    name.replace(" ", "")
                    .startswith(
                        alias.replace(" ", "")
                    )
                ):
                    score += 40

                # 짧은 MTI 코드일수록
                # 상위 산업 코드일 가능성이 높으므로 가점
                code_len = len(
                    str(
                        row[
                            "공식MTI코드"
                        ]
                    )
                )

                score += (
                    7 - code_len
                ) * 5

                # 거리가 가까울수록 가점
                score += max(
                    0,
                    10 - int(
                        row["거리"]
                    )
                )

                matches.append({
                    "산업": industry,
                    "alias": alias,
                    "공식MTI코드": row[
                        "공식MTI코드"
                    ],
                    "공식품목명": row[
                        "공식품목명"
                    ],
                    "코드길이": code_len,
                    "점수": score,
                    "행": row[
                        "행"
                    ],
                })


    if not matches:

        rule_records.append({
            "산업": industry,
            "alias": "",
            "공식MTI코드": "",
            "공식품목명": "찾지 못함",
            "코드길이": 0,
            "점수": 0,
            "행": "",
        })

    else:

        match_df = pd.DataFrame(
            matches
        )

        # 중복 제거
        match_df = (
            match_df
            .drop_duplicates(
                subset=[
                    "산업",
                    "공식MTI코드",
                    "공식품목명"
                ]
            )
            .sort_values(
                [
                    "점수",
                    "코드길이"
                ],
                ascending=[
                    False,
                    True
                ]
            )
        )

        # 후보를 모두 저장
        rule_records.extend(
            match_df
            .head(30)
            .to_dict(
                orient="records"
            )
        )


rules_all = pd.DataFrame(
    rule_records
)


# ============================================================
# 12. 산업별 Best Rule 선택
# ============================================================

best_rules = []


for industry in TARGET_INDUSTRIES:

    temp = (
        rules_all[
            rules_all["산업"]
            ==
            industry
        ]
        .copy()
    )

    temp = temp.sort_values(
        [
            "점수",
            "코드길이"
        ],
        ascending=[
            False,
            True
        ]
    )

    best = temp.iloc[0]

    best_rules.append(
        best
    )


best_rules = pd.DataFrame(
    best_rules
)


print()
print("=" * 110)
print("20대 산업 BEST OFFICIAL RULE")
print("=" * 110)

print(
    best_rules[
        [
            "산업",
            "공식MTI코드",
            "공식품목명",
            "코드길이",
            "점수"
        ]
    ].to_string(
        index=False
    )
)


# ============================================================
# 13. 공식 상위 MTI 코드 → MTI6 확장
# ============================================================

mapping_records = []


for _, rule in best_rules.iterrows():

    industry = rule["산업"]

    prefix = str(
        rule["공식MTI코드"]
    ).strip()

    official_name = str(
        rule["공식품목명"]
    ).strip()


    if (
        prefix == ""
        or
        official_name == "찾지 못함"
    ):
        continue


    temp = (
        mti6[
            mti6["MTI6코드"]
            .str.startswith(
                prefix
            )
        ]
        .copy()
    )


    for _, item in temp.iterrows():

        mapping_records.append({
            "산업": industry,
            "공식상위MTI": prefix,
            "공식상위품목명": official_name,
            "MTI6코드": item["MTI6코드"],
            "MTI6품목명": item["품목명"],
        })


mapping = pd.DataFrame(
    mapping_records
)


# ============================================================
# 14. 산업별 Mapping Summary
# ============================================================

if mapping.empty:

    summary = pd.DataFrame(
        columns=[
            "산업",
            "MTI6_수"
        ]
    )

else:

    summary = (
        mapping
        .groupby(
            "산업",
            as_index=False
        )
        .agg(
            MTI6_수=(
                "MTI6코드",
                "nunique"
            )
        )
    )


# 20대 산업 전체를 반드시 표시
summary = (
    pd.DataFrame(
        {
            "산업":
            TARGET_INDUSTRIES
        }
    )
    .merge(
        summary,
        on="산업",
        how="left"
    )
)


summary[
    "MTI6_수"
] = (
    summary[
        "MTI6_수"
    ]
    .fillna(0)
    .astype(int)
)


# ============================================================
# 15. MTI6 중복 산업 검증
#
# 하나의 MTI6가 복수 산업에 들어가면
# 반드시 검토 필요
# ============================================================

if mapping.empty:

    overlap = pd.DataFrame()

else:

    overlap_count = (
        mapping
        .groupby(
            "MTI6코드"
        )["산업"]
        .nunique()
    )


    overlap_codes = (
        overlap_count[
            overlap_count > 1
        ]
        .index
    )


    overlap = (
        mapping[
            mapping[
                "MTI6코드"
            ].isin(
                overlap_codes
            )
        ]
        .sort_values(
            [
                "MTI6코드",
                "산업"
            ]
        )
    )


# ============================================================
# 16. 미매핑 산업
# ============================================================

missing_industries = (
    summary[
        summary["MTI6_수"]
        ==
        0
    ]
)


# ============================================================
# 17. Review 결과 출력
# ============================================================

print()
print("=" * 110)
print("산업별 공식 MTI6 Mapping 수")
print("=" * 110)

print(
    summary.to_string(
        index=False
    )
)


print()
print("=" * 110)
print("미매핑 산업")
print("=" * 110)

if missing_industries.empty:
    print("없음")
else:
    print(
        missing_industries
        .to_string(
            index=False
        )
    )


print()
print("=" * 110)
print("복수 산업 중복 MTI6")
print("=" * 110)

if overlap.empty:

    print("없음")

else:

    print(
        overlap[
            [
                "MTI6코드",
                "MTI6품목명",
                "산업",
                "공식상위MTI",
                "공식상위품목명"
            ]
        ]
        .head(100)
        .to_string(
            index=False
        )
    )


# ============================================================
# 18. 최종 Coverage
# ============================================================

mapped_unique = (
    mapping["MTI6코드"]
    .nunique()
    if not mapping.empty
    else 0
)


coverage = (
    mapped_unique
    /
    mti6["MTI6코드"].nunique()
    *
    100
)


print()
print("=" * 110)
print("전체 MTI6 Coverage")
print("=" * 110)

print(
    f"전체 MTI6       : "
    f"{mti6['MTI6코드'].nunique():,}"
)

print(
    f"20대 산업 포함  : "
    f"{mapped_unique:,}"
)

print(
    f"Coverage        : "
    f"{coverage:.2f}%"
)


# ============================================================
# 19. Review Table
# ============================================================

review = (
    best_rules[
        [
            "산업",
            "공식MTI코드",
            "공식품목명",
            "점수"
        ]
    ]
    .merge(
        summary,
        on="산업",
        how="left"
    )
)


review[
    "검토상태"
] = "CHECK"


review.loc[
    review["MTI6_수"] > 0,
    "검토상태"
] = "FOUND"


review.loc[
    review["MTI6_수"] == 0,
    "검토상태"
] = "MISSING"


# ============================================================
# 20. CSV 저장
# ============================================================

rules_all.to_csv(
    OUTPUT_RULES,
    index=False,
    encoding="utf-8-sig"
)

mapping.to_csv(
    OUTPUT_MAPPING,
    index=False,
    encoding="utf-8-sig"
)

summary.to_csv(
    OUTPUT_SUMMARY,
    index=False,
    encoding="utf-8-sig"
)

review.to_csv(
    OUTPUT_REVIEW,
    index=False,
    encoding="utf-8-sig"
)


if not overlap.empty:

    overlap.to_csv(
        BASE_DIR /
        "mti20_official_overlap.csv",
        index=False,
        encoding="utf-8-sig"
    )


print()
print("=" * 110)
print("CSV 저장 완료")
print("=" * 110)

print("- mti20_official_rules.csv")
print("- mti20_official_mapping.csv")
print("- mti20_official_summary.csv")
print("- mti20_official_review.csv")

if not overlap.empty:
    print("- mti20_official_overlap.csv")


print()
print("=" * 110)
print("OFFICIAL MAPPING BUILD COMPLETE")
print("=" * 110)