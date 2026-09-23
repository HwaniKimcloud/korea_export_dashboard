from pathlib import Path
import pandas as pd


# ============================================================
# 1. 기본 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "mti_hierarchy_1291.csv"

OUTPUT_ALL = BASE_DIR / "mti20_mapping_candidates.csv"
OUTPUT_SUMMARY = BASE_DIR / "mti20_mapping_summary.csv"


if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"파일을 찾을 수 없습니다:\n{INPUT_FILE}"
    )


# ============================================================
# 2. 데이터 읽기
# ============================================================

df = pd.read_csv(
    INPUT_FILE,
    dtype={
        "MTI6코드": str,
        "MTI1": str,
        "MTI2": str,
        "MTI3": str,
        "MTI4": str,
    }
)


# ============================================================
# 3. 20대 산업 후보 키워드
# ============================================================
#
# 아직 최종 정의가 아닙니다.
# 이번 단계는 "후보 추출"용입니다.
# ============================================================

INDUSTRY_RULES = {

    "반도체": [
        "반도체",
        "D램",
        "낸드",
        "메모리",
        "프로세서",
        "컨트롤러",
        "집적회로",
    ],

    "디스플레이": [
        "LCD",
        "OLED",
        "디스플레이",
        "평판",
    ],

    "무선통신기기": [
        "무선통신",
        "휴대전화",
        "휴대폰",
        "통신기기",
    ],

    "컴퓨터": [
        "컴퓨터",
        "프린터",
        "스캐너",
        "키보드",
        "마우스",
        "저장장치",
        "전산기록매체",
    ],

    "가전": [
        "냉장고",
        "세탁기",
        "에어컨",
        "텔레비전",
        "TV",
        "청소기",
        "전자레인지",
        "가정용",
    ],

    "자동차": [
        "승용차",
        "자동차",
        "전기승용차",
        "하이브리드",
    ],

    "자동차부품": [
        "자동차부품",
        "자동차 부품",
    ],

    "선박": [
        "선박",
        "화물선",
        "유조선",
        "해양구조물",
    ],

    "일반기계": [
        "기계",
        "산업기계",
        "공작기계",
        "기계요소",
    ],

    "석유제품": [
        "휘발유",
        "경유",
        "제트유",
        "등유",
        "나프타",
        "석유제품",
    ],

    "석유화학": [
        "합성수지",
        "합성고무",
        "석유화학",
        "플라스틱원료",
        "에틸렌",
        "프로필렌",
    ],

    "이차전지": [
        "축전지",
        "배터리",
        "이차전지",
        "2차전지",
    ],

    "철강": [
        "철강",
        "강판",
        "철판",
        "열연",
        "냉연",
        "스테인리스",
        "철근",
    ],

    "비철금속": [
        "알루미늄",
        "구리",
        "동",
        "아연",
        "니켈",
        "비철",
    ],

    "전기기기": [
        "변압기",
        "차단기",
        "전력기기",
        "전기기기",
        "전동기",
        "발전기",
        "전선",
        "케이블",
    ],

    "바이오헬스": [
        "바이오",
        "의약품",
        "의료기기",
        "진단",
    ],

    "농수산식품": [
        "농산",
        "수산",
        "식품",
        "곡물",
        "과일",
        "어류",
        "가공식품",
    ],

    "화장품": [
        "화장품",
        "메이크업",
        "기초화장품",
        "향수",
    ],

    "생활용품": [
        "생활용품",
        "생활잡화",
        "가구",
        "주방용품",
        "위생용품",
    ],

    "섬유": [
        "섬유",
        "직물",
        "의류",
        "원사",
        "면직물",
        "화섬",
    ],
}


# ============================================================
# 4. 후보 매칭
# ============================================================

records = []


for industry, keywords in INDUSTRY_RULES.items():

    for _, row in df.iterrows():

        name = str(row["품목명"])

        matched_keywords = [
            keyword
            for keyword in keywords
            if keyword.lower() in name.lower()
        ]

        if not matched_keywords:
            continue

        records.append({
            "산업": industry,
            "MTI3": row["MTI3"],
            "MTI4": row["MTI4"],
            "MTI6코드": row["MTI6코드"],
            "품목명": row["품목명"],
            "매칭키워드": ", ".join(matched_keywords),
        })


candidate = pd.DataFrame(records)


# ============================================================
# 5. 후보 요약
# ============================================================

if candidate.empty:
    print("후보 매칭 결과가 없습니다.")
    raise SystemExit


summary = (
    candidate
    .groupby("산업", as_index=False)
    .agg(
        후보_MTI6_수=("MTI6코드", "nunique"),
        후보_MTI4_수=("MTI4", "nunique"),
        후보_MTI3_수=("MTI3", "nunique"),
    )
)


# 위 오타 방지를 위해 컬럼명 재정의
summary.columns = [
    "산업",
    "후보_MTI6_수",
    "후보_MTI4_수",
    "후보_MTI3_수",
]


# ============================================================
# 6. 산업별 출력
# ============================================================

print()
print("=" * 100)
print("20대 산업 MAPPING CANDIDATES")
print("=" * 100)


for industry in INDUSTRY_RULES.keys():

    temp = candidate[
        candidate["산업"] == industry
    ]

    print()
    print("-" * 100)
    print(
        f"[{industry}] "
        f"MTI6 후보 {temp['MTI6코드'].nunique()}개"
    )
    print("-" * 100)

    if temp.empty:
        print("후보 없음")
        continue

    print(
        temp[
            [
                "MTI3",
                "MTI4",
                "MTI6코드",
                "품목명",
                "매칭키워드"
            ]
        ]
        .sort_values(
            [
                "MTI3",
                "MTI4",
                "MTI6코드"
            ]
        )
        .head(100)
        .to_string(index=False)
    )


# ============================================================
# 7. 요약 출력
# ============================================================

print()
print("=" * 100)
print("산업별 후보 개수")
print("=" * 100)

print(
    summary
    .sort_values(
        "후보_MTI6_수",
        ascending=False
    )
    .to_string(index=False)
)


# ============================================================
# 8. CSV 저장
# ============================================================

candidate.to_csv(
    OUTPUT_ALL,
    index=False,
    encoding="utf-8-sig"
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

print("- mti20_mapping_candidates.csv")
print("- mti20_mapping_summary.csv")

print()
print("=" * 100)
print("MAPPING PROBE COMPLETE")
print("=" * 100)