from pathlib import Path
import pandas as pd
import re


# ============================================================
# 1. 기본 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "industry_data"

FILES = [
    DATA_DIR / "KITA_MTI6_INDUSTRY_EXPORT_DATA.XLS",  # 1페이지
    DATA_DIR / "KITA_MTI6_02.XLS",                    # 2페이지
]


# ============================================================
# 2. 공통 함수
# ============================================================

def normalize_code(value):

    if pd.isna(value):
        return None

    if isinstance(value, (int, float)):

        try:
            text = str(int(value))
        except Exception:
            return None

    else:

        text = str(value).strip()
        text = re.sub(r"\.0$", "", text)

    if not re.fullmatch(r"\d{6}", text):
        return None

    return text


def normalize_name(value):

    if pd.isna(value):
        return None

    text = str(value).strip()

    if text == "" or text.lower() == "nan":
        return None

    if re.fullmatch(
        r"[-+]?\d+(\.\d+)?",
        text.replace(",", "")
    ):
        return None

    return text


def read_mti_file(file_path):

    raw = pd.read_excel(
        file_path,
        header=None
    )

    # ----------------------------------------
    # 코드 / 품목명 헤더 찾기
    # ----------------------------------------

    header_candidates = []

    for row_idx in range(min(50, len(raw))):

        row_values = [
            "" if pd.isna(v)
            else str(v).strip()
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


    if not header_candidates:

        raise ValueError(
            f"{file_path.name}: 코드/품목명 헤더를 찾지 못했습니다."
        )


    header = header_candidates[0]

    header_row = header["헤더행"]
    code_col = header["코드열"]
    name_col = header["품목명열"]


    # ----------------------------------------
    # 데이터 추출
    # ----------------------------------------

    records = []

    for row_idx in range(
        header_row + 1,
        len(raw)
    ):

        code = normalize_code(
            raw.iat[
                row_idx,
                code_col
            ]
        )

        if code is None:
            continue

        name = normalize_name(
            raw.iat[
                row_idx,
                name_col
            ]
        )

        records.append({
            "MTI6코드": code,
            "품목명": name,
            "원본파일": file_path.name,
            "원본행": row_idx
        })


    df = pd.DataFrame(records)

    if df.empty:
        return df


    df = (
        df
        .drop_duplicates(
            subset=[
                "MTI6코드",
                "품목명"
            ]
        )
        .sort_values("MTI6코드")
        .reset_index(drop=True)
    )


    return df


# ============================================================
# 3. 파일별 읽기
# ============================================================

print()
print("=" * 90)
print("KITA MTI6 PAGE MERGE TEST")
print("=" * 90)


dataframes = []


for file in FILES:

    print()
    print("-" * 90)
    print("읽는 파일:", file.name)
    print("-" * 90)

    if not file.exists():

        print(">>> 파일 없음")
        continue

    df = read_mti_file(file)

    print(
        "추출 행 수:",
        len(df)
    )

    print(
        "고유 MTI6 코드 수:",
        df["MTI6코드"].nunique()
        if not df.empty
        else 0
    )

    print()

    if not df.empty:

        print(
            df.head(10)
            .to_string(index=False)
        )

        dataframes.append(df)


# ============================================================
# 4. 파일 개수 검증
# ============================================================

if len(dataframes) < 2:

    print()
    print(
        "2개 파일을 모두 정상적으로 읽지 못했습니다."
    )

    raise SystemExit


page1 = dataframes[0]
page2 = dataframes[1]


# ============================================================
# 5. 페이지간 중복 확인
# ============================================================

codes1 = set(
    page1["MTI6코드"]
)

codes2 = set(
    page2["MTI6코드"]
)


duplicates = sorted(
    codes1.intersection(
        codes2
    )
)


print()
print("=" * 90)
print("페이지간 중복 검증")
print("=" * 90)

print(
    "1페이지 고유 코드:",
    len(codes1)
)

print(
    "2페이지 고유 코드:",
    len(codes2)
)

print(
    "중복 코드 수:",
    len(duplicates)
)


if duplicates:

    print()
    print("중복 코드 예시:")

    print(
        duplicates[:20]
    )


# ============================================================
# 6. 통합
# ============================================================

merged = pd.concat(
    dataframes,
    ignore_index=True
)


before = len(merged)


merged = (
    merged
    .drop_duplicates(
        subset=[
            "MTI6코드"
        ],
        keep="first"
    )
    .sort_values("MTI6코드")
    .reset_index(drop=True)
)


after = len(merged)


# ============================================================
# 7. 통합 결과
# ============================================================

print()
print("=" * 90)
print("통합 결과")
print("=" * 90)

print(
    "병합 전 행 수:",
    before
)

print(
    "병합 후 고유 MTI6:",
    after
)

print(
    "품목명 확인 수:",
    merged["품목명"]
    .notna()
    .sum()
)


# ============================================================
# 8. 페이지별 범위 확인
# ============================================================

print()
print("=" * 90)
print("페이지 범위 확인")
print("=" * 90)


for df in dataframes:

    filename = df.iloc[0][
        "원본파일"
    ]

    print()
    print(filename)

    print(
        "첫 코드:",
        df.iloc[0][
            "MTI6코드"
        ],
        "/",
        df.iloc[0][
            "품목명"
        ]
    )

    print(
        "마지막 코드:",
        df.iloc[-1][
            "MTI6코드"
        ],
        "/",
        df.iloc[-1][
            "품목명"
        ]
    )


# ============================================================
# 9. 샘플 출력
# ============================================================

print()
print("=" * 90)
print("통합 앞부분 20개")
print("=" * 90)

print(
    merged.head(20)
    .to_string(index=False)
)


print()
print("=" * 90)
print("통합 뒷부분 20개")
print("=" * 90)

print(
    merged.tail(20)
    .to_string(index=False)
)


# ============================================================
# 10. CSV 저장
# ============================================================

OUTPUT = (
    BASE_DIR
    /
    "mti6_merge_test_200.csv"
)


merged.to_csv(
    OUTPUT,
    index=False,
    encoding="utf-8-sig"
)


print()
print("=" * 90)
print("CSV 저장 완료")
print("=" * 90)

print(
    "- mti6_merge_test_200.csv"
)


print()
print("=" * 90)
print("MERGE TEST COMPLETE")
print("=" * 90)