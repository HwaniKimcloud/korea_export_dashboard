from pathlib import Path
import pandas as pd
import re


# ============================================================
# 1. 기본 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "industry_data"

FILES = [
    DATA_DIR / "KITA_MTI_INDUSTRY_EXPORT_DATA.xls",
    DATA_DIR / "KITA_MTI3_CORE_MONTHLY.xls",
]


# ============================================================
# 2. 우리가 최종적으로 추적하려는 20개 품목
# ============================================================

TARGETS = {
    "반도체": [
        "반도체",
    ],

    "디스플레이": [
        "디스플레이",
        "평판디스플레이",
        "평판디스플레이 및 센서",
        "OLED",
    ],

    "무선통신기기": [
        "무선통신",
        "무선통신기기",
        "휴대폰",
        "휴대전화",
    ],

    "컴퓨터": [
        "컴퓨터",
        "컴퓨터기기",
        "컴퓨터 및 주변기기",
    ],

    "가전": [
        "가전",
        "가정용전자",
        "가정용전기",
        "가정용기기",
        "전자제품",
    ],

    "자동차": [
        "자동차",
        "승용차",
    ],

    "자동차부품": [
        "자동차부품",
        "자동차 부품",
    ],

    "선박": [
        "선박",
        "선박해양구조물",
        "선박해양구조물및부품",
        "선박 및 부품",
    ],

    "일반기계": [
        "일반기계",
        "기계류",
        "기계요소",
        "산업기계",
    ],

    "석유제품": [
        "석유제품",
        "석유제품류",
        "석유",
        "정유",
    ],

    "석유화학": [
        "석유화학",
        "석유화학제품",
        "합성수지",
        "합성고무",
    ],

    "이차전지": [
        "이차전지",
        "2차전지",
        "축전지",
        "배터리",
    ],

    "철강": [
        "철강",
        "철강제품",
        "철강재",
        "철강판",
    ],

    "비철금속": [
        "비철금속",
        "비철금속제품",
        "알루미늄",
        "구리제품",
    ],

    "전기기기": [
        "전기기기",
        "전력용기기",
        "전력기기",
        "전기장비",
        "전기전자",
    ],

    "바이오헬스": [
        "바이오",
        "바이오헬스",
        "의약품",
        "의료기기",
    ],

    "농수산식품": [
        "농수산",
        "농수산식품",
        "농림수산",
        "식품",
        "농산물",
        "수산물",
    ],

    "화장품": [
        "화장품",
        "화장용품",
    ],

    "생활용품": [
        "생활용품",
        "생활잡화",
        "잡제품",
        "소비재",
    ],

    "섬유": [
        "섬유",
        "섬유제품",
        "의류",
        "직물",
    ],
}


# ============================================================
# 3. 문자열 정리 함수
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


# ============================================================
# 4. MTI 코드 후보 추출
# ============================================================

def extract_mti_code(text):

    if text is None:
        return None

    # 예: 반도체 (831)
    match = re.search(
        r"\((\d{3,6})\)",
        text
    )

    if match:
        return match.group(1)

    # 셀 내용이 "831 반도체" 같은 형태도 대응
    match = re.match(
        r"^\s*(\d{3,6})\s+",
        text
    )

    if match:
        return match.group(1)

    return None


# ============================================================
# 5. 모든 셀에서 산업명 후보 수집
# ============================================================

records = []


print()
print("=" * 100)
print("KITA MTI ACTUAL MASTER EXTRACTION")
print("=" * 100)


for file in FILES:

    print()
    print("-" * 100)
    print("파일:", file.name)
    print("-" * 100)

    if not file.exists():
        print("파일 없음")
        continue

    df = pd.read_excel(
        file,
        header=None
    )

    print(
        f"행={len(df)}, 열={len(df.columns)}"
    )

    for row_idx in range(len(df)):

        for col_idx in range(len(df.columns)):

            text = clean_text(
                df.iat[row_idx, col_idx]
            )

            if text is None:
                continue

            # 너무 긴 설명문은 산업명 후보에서 제외
            if len(text) > 80:
                continue

            # 숫자만 있는 셀 제외
            if re.fullmatch(
                r"[-+]?\d+(\.\d+)?",
                text
            ):
                continue

            # 기간/단위/메타정보성 셀 제외
            exclude_keywords = [
                "기간",
                "수출입",
                "증감률",
                "금액",
                "중량",
                "합계",
                "전년",
                "단위",
                "한국무역협회",
                "K-stat",
            ]

            if any(
                keyword in text
                for keyword in exclude_keywords
            ):
                continue

            mti_code = extract_mti_code(
                text
            )

            records.append({
                "파일": file.name,
                "행": row_idx,
                "열": col_idx,
                "셀내용": text,
                "MTI코드후보": mti_code,
            })


candidate_df = pd.DataFrame(
    records
)


# ============================================================
# 6. 중복 제거
# ============================================================

candidate_unique = (
    candidate_df
    .drop_duplicates(
        subset=[
            "파일",
            "셀내용"
        ]
    )
    .sort_values(
        [
            "파일",
            "행",
            "열"
        ]
    )
    .reset_index(drop=True)
)


print()
print("=" * 100)
print("실제 문자열 후보 수")
print("=" * 100)

print(
    len(candidate_unique)
)


# ============================================================
# 7. 20개 품목 자동 매칭
# ============================================================

matches = []


for target_name, aliases in TARGETS.items():

    matched_rows = []

    for _, row in candidate_unique.iterrows():

        text = row["셀내용"]

        matched_alias = None

        for alias in aliases:

            if alias.lower() in text.lower():

                matched_alias = alias
                break

        if matched_alias is None:
            continue

        matched_rows.append({
            "목표품목": target_name,
            "매칭키워드": matched_alias,
            "파일": row["파일"],
            "행": row["행"],
            "열": row["열"],
            "실제셀내용": text,
            "MTI코드후보": row["MTI코드후보"],
        })

    if matched_rows:

        matches.extend(
            matched_rows
        )

    else:

        matches.append({
            "목표품목": target_name,
            "매칭키워드": "",
            "파일": "",
            "행": "",
            "열": "",
            "실제셀내용": "찾지 못함",
            "MTI코드후보": "",
        })


match_df = pd.DataFrame(
    matches
)


# ============================================================
# 8. 매칭 강도 계산
# ============================================================

def score_match(row):

    if row["실제셀내용"] == "찾지 못함":
        return 0

    target = str(
        row["목표품목"]
    )

    text = str(
        row["실제셀내용"]
    )

    alias = str(
        row["매칭키워드"]
    )

    score = 0

    # 완전 일치
    if text == target:
        score += 100

    # 목표품목 포함
    if target in text:
        score += 50

    # 별칭 포함
    if alias and alias in text:
        score += 30

    # MTI 코드까지 포함된 셀이면 가점
    if pd.notna(
        row["MTI코드후보"]
    ) and str(
        row["MTI코드후보"]
    ).strip() != "":
        score += 20

    # 너무 긴 문구는 감점
    if len(text) > 30:
        score -= 10

    return score


match_df[
    "매칭점수"
] = match_df.apply(
    score_match,
    axis=1
)


# ============================================================
# 9. 목표 품목별 Best Match
# ============================================================

best_rows = []


for target in TARGETS.keys():

    temp = (
        match_df[
            match_df["목표품목"]
            ==
            target
        ]
        .copy()
    )

    temp = temp.sort_values(
        [
            "매칭점수",
            "실제셀내용"
        ],
        ascending=[
            False,
            True
        ]
    )

    best_rows.append(
        temp.iloc[0]
    )


best_df = pd.DataFrame(
    best_rows
)


# ============================================================
# 10. 결과 출력
# ============================================================

print()
print("=" * 100)
print("20대 산업 BEST MATCH")
print("=" * 100)

print(
    best_df[
        [
            "목표품목",
            "실제셀내용",
            "MTI코드후보",
            "파일",
            "행",
            "열",
            "매칭점수"
        ]
    ].to_string(
        index=False
    )
)


# ============================================================
# 11. 미매칭 품목
# ============================================================

missing = best_df[
    best_df["실제셀내용"]
    ==
    "찾지 못함"
]


print()
print("=" * 100)
print("미매칭 품목")
print("=" * 100)


if missing.empty:

    print("없음")

else:

    print(
        missing[
            [
                "목표품목"
            ]
        ].to_string(
            index=False
        )
    )


# ============================================================
# 12. 다중 매칭 품목 확인
# ============================================================

print()
print("=" * 100)
print("다중 매칭 후보")
print("=" * 100)


for target in TARGETS.keys():

    temp = (
        match_df[
            (
                match_df["목표품목"]
                ==
                target
            )
            &
            (
                match_df["실제셀내용"]
                !=
                "찾지 못함"
            )
        ]
        .sort_values(
            "매칭점수",
            ascending=False
        )
    )

    if len(temp) <= 1:
        continue

    print()
    print(
        f"[{target}]"
    )

    print(
        temp[
            [
                "실제셀내용",
                "MTI코드후보",
                "파일",
                "행",
                "열",
                "매칭점수"
            ]
        ]
        .head(10)
        .to_string(
            index=False
        )
    )


# ============================================================
# 13. CSV 저장
# ============================================================

candidate_unique.to_csv(
    BASE_DIR / "mti_actual_candidates.csv",
    index=False,
    encoding="utf-8-sig"
)

match_df.to_csv(
    BASE_DIR / "mti_20_all_matches.csv",
    index=False,
    encoding="utf-8-sig"
)

best_df.to_csv(
    BASE_DIR / "mti_20_best_match.csv",
    index=False,
    encoding="utf-8-sig"
)


print()
print("=" * 100)
print("CSV 저장 완료")
print("=" * 100)

print(
    "- mti_actual_candidates.csv"
)

print(
    "- mti_20_all_matches.csv"
)

print(
    "- mti_20_best_match.csv"
)

print()
print("=" * 100)
print("EXTRACTION COMPLETE")
print("=" * 100)