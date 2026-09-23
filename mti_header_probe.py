from pathlib import Path
import pandas as pd


# ============================================================
# 1. 파일 위치
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "industry_data"

FILES = [
    DATA_DIR / "KITA_MTI_INDUSTRY_EXPORT_DATA.xls",
    DATA_DIR / "KITA_MTI3_CORE_MONTHLY.xls",
]


# ============================================================
# 2. 찾을 핵심 키워드
# ============================================================

KEYWORDS = [
    "반도체",
    "디스플레이",
    "무선통신",
    "컴퓨터",
    "가전",
    "자동차",
    "자동차부품",
    "선박",
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


print()
print("=" * 90)
print("KITA MTI HEADER PROBE")
print("=" * 90)


# ============================================================
# 3. 각 Excel 파일 전체 검사
# ============================================================

all_matches = []


for file in FILES:

    print()
    print("=" * 90)
    print("검사 파일:", file.name)
    print("=" * 90)

    if not file.exists():
        print(">>> 파일 없음")
        continue

    # header=None:
    # Excel의 어느 행이 헤더인지 미리 가정하지 않습니다.
    df = pd.read_excel(
        file,
        header=None
    )

    print("행 수:", len(df))
    print("열 수:", len(df.columns))

    print()
    print("-" * 90)
    print("상단 20행 원본")
    print("-" * 90)

    # 너무 넓은 파일이면 화면이 지나치게 길어지므로
    # 앞 30개 열까지만 보여줍니다.
    preview_cols = min(30, len(df.columns))

    print(
        df.iloc[:20, :preview_cols]
        .to_string(index=True, header=True)
    )


    # ========================================================
    # 4. 키워드 위치 검색
    # ========================================================

    print()
    print("-" * 90)
    print("산업 키워드 검색 결과")
    print("-" * 90)

    file_match_count = 0

    for row_idx in range(len(df)):

        for col_idx in range(len(df.columns)):

            value = df.iat[row_idx, col_idx]

            if pd.isna(value):
                continue

            text = str(value).strip()

            for keyword in KEYWORDS:

                if keyword in text:

                    result = {
                        "파일": file.name,
                        "검색어": keyword,
                        "행": row_idx,
                        "열": col_idx,
                        "셀내용": text,
                    }

                    all_matches.append(result)

                    print(
                        f"[{keyword}] "
                        f"행={row_idx}, 열={col_idx} "
                        f"→ {text}"
                    )

                    file_match_count += 1

    if file_match_count == 0:
        print(">>> 검색된 산업 키워드 없음")

    else:
        print()
        print(
            f">>> 이 파일에서 총 {file_match_count}개 "
            "키워드 매칭 발견"
        )


# ============================================================
# 5. 결과 DataFrame
# ============================================================

match_df = pd.DataFrame(all_matches)


print()
print("=" * 90)
print("전체 검색 결과 요약")
print("=" * 90)


if match_df.empty:

    print("산업 키워드를 찾지 못했습니다.")

else:

    print(
        match_df.to_string(
            index=False
        )
    )


# ============================================================
# 6. 검색어별 발견 여부
# ============================================================

print()
print("=" * 90)
print("20대 산업 검색어 발견 여부")
print("=" * 90)


summary_rows = []


for keyword in KEYWORDS:

    if match_df.empty:

        found = False
        count = 0

    else:

        temp = match_df[
            match_df["검색어"] == keyword
        ]

        found = not temp.empty
        count = len(temp)

    summary_rows.append({
        "검색어": keyword,
        "발견여부": "YES" if found else "NO",
        "발견횟수": count,
    })


summary_df = pd.DataFrame(summary_rows)


print(
    summary_df.to_string(
        index=False
    )
)


# ============================================================
# 7. CSV 저장
# ============================================================

if not match_df.empty:

    match_df.to_csv(
        BASE_DIR / "mti_header_probe_result.csv",
        index=False,
        encoding="utf-8-sig"
    )


summary_df.to_csv(
    BASE_DIR / "mti_header_probe_summary.csv",
    index=False,
    encoding="utf-8-sig"
)


print()
print("=" * 90)
print("CSV 저장 완료")
print("=" * 90)

if not match_df.empty:
    print("- mti_header_probe_result.csv")

print("- mti_header_probe_summary.csv")


print()
print("=" * 90)
print("PROBE COMPLETE")
print("=" * 90)