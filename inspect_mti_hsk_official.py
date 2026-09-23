from pathlib import Path
import pandas as pd


# ============================================================
# 1. 기본 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "industry_data"

INPUT_FILE = DATA_DIR / "2026 MTI-HSK 코드표_vFF_260507.xlsx"


if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"파일을 찾을 수 없습니다:\n{INPUT_FILE}"
    )


print()
print("=" * 100)
print("2026 MTI-HSK OFFICIAL FILE INSPECTOR")
print("=" * 100)

print("입력 파일:", INPUT_FILE)


# ============================================================
# 2. Excel 시트 확인
# ============================================================

xls = pd.ExcelFile(INPUT_FILE)

print()
print("=" * 100)
print("시트 목록")
print("=" * 100)

for i, sheet in enumerate(xls.sheet_names, start=1):
    print(f"{i}. {sheet}")


# ============================================================
# 3. 각 시트 상단 구조 확인
# ============================================================

for sheet in xls.sheet_names:

    print()
    print("=" * 100)
    print(f"SHEET: {sheet}")
    print("=" * 100)

    raw = pd.read_excel(
        INPUT_FILE,
        sheet_name=sheet,
        header=None
    )

    print(
        f"행 수: {len(raw):,} / "
        f"열 수: {len(raw.columns):,}"
    )

    print()
    print("-" * 100)
    print("상단 30행 / 앞 20열")
    print("-" * 100)

    preview_cols = min(
        20,
        len(raw.columns)
    )

    print(
        raw.iloc[:30, :preview_cols]
        .to_string(
            index=True,
            header=True
        )
    )


# ============================================================
# 4. 핵심 키워드 위치 탐색
# ============================================================

KEYWORDS = [
    "MTI",
    "HSK",
    "HS",
    "품목명",
    "품명",
    "코드",
    "반도체",
    "자동차",
    "자동차부품",
    "선박",
    "디스플레이",
    "무선통신",
    "컴퓨터",
    "가전",
    "일반기계",
    "석유제품",
    "석유화학",
    "이차전지",
    "철강",
    "비철금속",
    "전기기기",
    "바이오",
    "농수산",
    "화장품",
    "생활용품",
    "섬유",
]


matches = []


for sheet in xls.sheet_names:

    raw = pd.read_excel(
        INPUT_FILE,
        sheet_name=sheet,
        header=None
    )

    for row_idx in range(len(raw)):

        for col_idx in range(len(raw.columns)):

            value = raw.iat[
                row_idx,
                col_idx
            ]

            if pd.isna(value):
                continue

            text = str(value).strip()

            if not text:
                continue

            for keyword in KEYWORDS:

                if keyword.lower() in text.lower():

                    matches.append({
                        "시트": sheet,
                        "검색어": keyword,
                        "행": row_idx,
                        "열": col_idx,
                        "셀내용": text,
                    })


match_df = pd.DataFrame(matches)


print()
print("=" * 100)
print("핵심 키워드 검색 결과")
print("=" * 100)


if match_df.empty:

    print("검색 결과 없음")

else:

    print(
        match_df
        .head(300)
        .to_string(
            index=False
        )
    )


# ============================================================
# 5. 20대 산업별 발견 위치 요약
# ============================================================

TARGETS = [
    "반도체",
    "자동차",
    "자동차부품",
    "선박",
    "디스플레이",
    "무선통신",
    "컴퓨터",
    "가전",
    "일반기계",
    "석유제품",
    "석유화학",
    "이차전지",
    "철강",
    "비철금속",
    "전기기기",
    "바이오",
    "농수산",
    "화장품",
    "생활용품",
    "섬유",
]


summary_rows = []


for target in TARGETS:

    if match_df.empty:

        temp = pd.DataFrame()

    else:

        temp = match_df[
            match_df["검색어"]
            ==
            target
        ]

    summary_rows.append({
        "산업": target,
        "발견여부": (
            "YES"
            if not temp.empty
            else "NO"
        ),
        "발견횟수": len(temp),
        "시트": (
            ", ".join(
                sorted(
                    temp["시트"]
                    .astype(str)
                    .unique()
                )
            )
            if not temp.empty
            else ""
        )
    })


summary_df = pd.DataFrame(
    summary_rows
)


print()
print("=" * 100)
print("20대 산업 공식 코드표 검색 결과")
print("=" * 100)

print(
    summary_df.to_string(
        index=False
    )
)


# ============================================================
# 6. CSV 저장
# ============================================================

if not match_df.empty:

    match_df.to_csv(
        BASE_DIR / "official_mti_hsk_keyword_matches.csv",
        index=False,
        encoding="utf-8-sig"
    )


summary_df.to_csv(
    BASE_DIR / "official_mti_hsk_20_summary.csv",
    index=False,
    encoding="utf-8-sig"
)


print()
print("=" * 100)
print("CSV 저장 완료")
print("=" * 100)

if not match_df.empty:
    print("- official_mti_hsk_keyword_matches.csv")

print("- official_mti_hsk_20_summary.csv")


print()
print("=" * 100)
print("INSPECTION COMPLETE")
print("=" * 100)