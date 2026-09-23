from pathlib import Path
import pandas as pd
import re


# ============================================================
# 1. 기본 설정
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "industry_data"

INPUT_FILE = DATA_DIR / "KITA_MTI6_INDUSTRY_EXPORT_DATA.XLS"


if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"파일을 찾을 수 없습니다:\n{INPUT_FILE}"
    )


print()
print("=" * 100)
print("KITA MTI6 EXACT MASTER BUILDER")
print("=" * 100)
print("입력 파일:", INPUT_FILE)


# ============================================================
# 2. 원본 읽기
# ============================================================

raw = pd.read_excel(
    INPUT_FILE,
    header=None
)

print()
print("원본 행 수:", len(raw))
print("원본 열 수:", len(raw.columns))


# ============================================================
# 3. '코드' / '품목명' 헤더 위치 탐색
# ============================================================

header_candidates = []

for row_idx in range(min(50, len(raw))):

    row_values = [
        "" if pd.isna(v) else str(v).strip()
        for v in raw.iloc[row_idx]
    ]

    code_cols = [
        i for i, v in enumerate(row_values)
        if v == "코드"
    ]

    name_cols = [
        i for i, v in enumerate(row_values)
        if v == "품목명"
    ]

    for code_col in code_cols:
        for name_col in name_cols:

            if name_col > code_col:

                header_candidates.append({
                    "헤더행": row_idx,
                    "코드열": code_col,
                    "품목명열": name_col
                })


print()
print("=" * 100)
print("헤더 후보")
print("=" * 100)

if not header_candidates:

    print("코드 / 품목명 헤더를 찾지 못했습니다.")

    print()
    print("상단 30행 출력")
    print(
        raw.head(30).to_string(
            index=True,
            header=True
        )
    )

    raise SystemExit


candidate_df = pd.DataFrame(
    header_candidates
)

print(
    candidate_df.to_string(
        index=False
    )
)


# 첫 번째 유효 후보 사용
HEADER_ROW = int(
    candidate_df.iloc[0]["헤더행"]
)

CODE_COL = int(
    candidate_df.iloc[0]["코드열"]
)

NAME_COL = int(
    candidate_df.iloc[0]["품목명열"]
)


print()
print("선택된 헤더:")
print("헤더 행 =", HEADER_ROW)
print("코드 열 =", CODE_COL)
print("품목명 열 =", NAME_COL)


# ============================================================
# 4. MTI 코드 정리 함수
# ============================================================

def normalize_code(value):

    if pd.isna(value):
        return None

    # Excel 숫자형 대응
    if isinstance(value, (int, float)):

        try:
            number = int(value)

            text = str(number)

        except Exception:
            return None

    else:

        text = str(value).strip()

        # 831110.0 형태 대응
        text = re.sub(
            r"\.0$",
            "",
            text
        )

    # MTI 6단위는 정확히 숫자 6자리
    if not re.fullmatch(
        r"\d{6}",
        text
    ):
        return None

    return text


def normalize_name(value):

    if pd.isna(value):
        return None

    text = str(value).strip()

    if (
        text == ""
        or
        text.lower() == "nan"
    ):
        return None

    # 숫자만 있는 값은 품목명이 아님
    if re.fullmatch(
        r"[-+]?\d+(\.\d+)?",
        text.replace(",", "")
    ):
        return None

    return text


# ============================================================
# 5. 헤더 아래 데이터만 추출
# ============================================================

records = []

for row_idx in range(
    HEADER_ROW + 1,
    len(raw)
):

    code = normalize_code(
        raw.iat[
            row_idx,
            CODE_COL
        ]
    )

    if code is None:
        continue

    name = normalize_name(
        raw.iat[
            row_idx,
            NAME_COL
        ]
    )

    records.append({
        "MTI6코드": code,
        "품목명": name,
        "원본행": row_idx
    })


master = pd.DataFrame(
    records
)


if master.empty:

    print()
    print(
        "MTI6 코드가 한 건도 추출되지 않았습니다."
    )

    raise SystemExit


# ============================================================
# 6. 중복 제거
# ============================================================

master = (
    master
    .drop_duplicates(
        subset=[
            "MTI6코드",
            "품목명"
        ]
    )
    .sort_values(
        "MTI6코드"
    )
    .reset_index(drop=True)
)


# ============================================================
# 7. 상위 코드 생성
# ============================================================

master["MTI1"] = (
    master["MTI6코드"]
    .str[:1]
)

master["MTI2"] = (
    master["MTI6코드"]
    .str[:2]
)

master["MTI3"] = (
    master["MTI6코드"]
    .str[:3]
)

master["MTI4"] = (
    master["MTI6코드"]
    .str[:4]
)


# ============================================================
# 8. 기본 검증
# ============================================================

print()
print("=" * 100)
print("MTI6 MASTER 검증")
print("=" * 100)

print(
    "추출 행 수:",
    len(master)
)

print(
    "고유 MTI6 코드 수:",
    master["MTI6코드"].nunique()
)

print(
    "품목명 확인 수:",
    master["품목명"].notna().sum()
)

print(
    "품목명 미확인 수:",
    master["품목명"].isna().sum()
)


print()
print("=" * 100)
print("앞부분 30개")
print("=" * 100)

print(
    master.head(30).to_string(
        index=False
    )
)


# ============================================================
# 9. 우리가 화면에서 직접 확인한 코드 검증
# ============================================================

KNOWN_CODES = [
    "831110",   # D램
    "831190",   # 기타 메모리반도체
    "831210",   # 프로세서와 컨트롤러
    "741310",   # 내연기관 승용차(신차)
    "746120",   # 화물선
    "813800",   # 전산기록매체
    "133200",   # 경유
    "742000",   # 자동차부품
    "741330",   # 하이브리드 승용차(신차)
    "831120",   # 낸드
    "837120",   # OLED
    "831230",   # 기타 집적회로반도체
    "133120",   # 자동차휘발유
    "227320",   # 메이크업, 기초화장품
    "133310",   # 제트유
    "812890",   # 기타무선통신기기부품
    "741350",   # 전기 승용차(신차)
    "931110",   # 바이오의약품
]


print()
print("=" * 100)
print("화면 확인 코드 검증")
print("=" * 100)


for code in KNOWN_CODES:

    temp = master[
        master["MTI6코드"]
        ==
        code
    ]

    if temp.empty:

        print(
            f"{code}: 찾지 못함"
        )

    else:

        print(
            temp[
                [
                    "MTI6코드",
                    "품목명"
                ]
            ].to_string(
                index=False
            )
        )


# ============================================================
# 10. 주요 산업 키워드 검색
# ============================================================

KEYWORDS = [
    "D램",
    "낸드",
    "메모리",
    "반도체",
    "프로세서",
    "컨트롤러",
    "자동차",
    "승용차",
    "자동차부품",
    "선박",
    "화물선",

    "컴퓨터",
    "전산",
    "디스플레이",
    "OLED",
    "무선통신",

    "배터리",
    "축전지",
    "전지",

    "가전",
    "냉장고",
    "세탁기",
    "에어컨",
    "TV",

    "석유",
    "휘발유",
    "경유",
    "제트유",

    "석유화학",
    "합성수지",
    "합성고무",

    "철강",
    "강판",
    "철",
    "알루미늄",
    "구리",

    "의약품",
    "바이오",
    "의료기기",

    "화장품",
    "메이크업",

    "섬유",
    "의류",
    "직물",

    "식품",
    "농산",
    "수산",
]


print()
print("=" * 100)
print("주요 키워드 검색")
print("=" * 100)


for keyword in KEYWORDS:

    temp = (
        master[
            master["품목명"]
            .fillna("")
            .str.contains(
                keyword,
                case=False,
                regex=False
            )
        ]
        [
            [
                "MTI6코드",
                "품목명",
                "MTI3",
                "MTI4"
            ]
        ]
    )

    print()
    print(
        f"[{keyword}] "
        f"{len(temp)}건"
    )

    if temp.empty:

        print("찾지 못함")

    else:

        print(
            temp.head(30)
            .to_string(
                index=False
            )
        )


# ============================================================
# 11. MTI3 그룹 요약
# ============================================================

mti3_summary = (
    master
    .groupby(
        "MTI3",
        as_index=False
    )
    .agg(
        품목수=(
            "MTI6코드",
            "nunique"
        )
    )
    .sort_values("MTI3")
)


print()
print("=" * 100)
print("MTI3 그룹")
print("=" * 100)

print(
    "MTI3 고유 그룹 수:",
    mti3_summary["MTI3"].nunique()
)


# ============================================================
# 12. CSV 저장
# ============================================================

master.to_csv(
    BASE_DIR / "mti6_master_exact.csv",
    index=False,
    encoding="utf-8-sig"
)

mti3_summary.to_csv(
    BASE_DIR / "mti3_group_summary_exact.csv",
    index=False,
    encoding="utf-8-sig"
)


print()
print("=" * 100)
print("CSV 저장 완료")
print("=" * 100)

print(
    "- mti6_master_exact.csv"
)

print(
    "- mti3_group_summary_exact.csv"
)


print()
print("=" * 100)
print("EXACT MASTER BUILD COMPLETE")
print("=" * 100)