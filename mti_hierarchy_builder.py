from pathlib import Path
import pandas as pd


# ============================================================
# 1. 기본 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "mti6_master_1291.csv"

OUTPUT_FILE = BASE_DIR / "mti_hierarchy_1291.csv"
OUTPUT_MTI3 = BASE_DIR / "mti3_master.csv"
OUTPUT_MTI4 = BASE_DIR / "mti4_master.csv"


# ============================================================
# 2. 입력 파일 확인
# ============================================================

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"파일을 찾을 수 없습니다:\n{INPUT_FILE}"
    )


print()
print("=" * 100)
print("MTI HIERARCHY BUILDER")
print("=" * 100)

print("입력 파일:", INPUT_FILE.name)


# ============================================================
# 3. MTI6 Master 읽기
# ============================================================

df = pd.read_csv(
    INPUT_FILE,
    dtype={
        "MTI6코드": str
    }
)


required_columns = [
    "MTI6코드",
    "품목명"
]


for col in required_columns:

    if col not in df.columns:
        raise ValueError(
            f"필수 열이 없습니다: {col}"
        )


# ============================================================
# 4. 코드 정리
# ============================================================

df["MTI6코드"] = (
    df["MTI6코드"]
    .astype(str)
    .str.strip()
    .str.zfill(6)
)


# ============================================================
# 5. 계층 코드 생성
# ============================================================

df["MTI1"] = (
    df["MTI6코드"]
    .str[:1]
)

df["MTI2"] = (
    df["MTI6코드"]
    .str[:2]
)

df["MTI3"] = (
    df["MTI6코드"]
    .str[:3]
)

df["MTI4"] = (
    df["MTI6코드"]
    .str[:4]
)


# ============================================================
# 6. 기본 검증
# ============================================================

print()
print("=" * 100)
print("기본 검증")
print("=" * 100)

print(
    "전체 행:",
    len(df)
)

print(
    "고유 MTI6:",
    df["MTI6코드"].nunique()
)

print(
    "고유 MTI4:",
    df["MTI4"].nunique()
)

print(
    "고유 MTI3:",
    df["MTI3"].nunique()
)

print(
    "고유 MTI2:",
    df["MTI2"].nunique()
)

print(
    "고유 MTI1:",
    df["MTI1"].nunique()
)


# ============================================================
# 7. MTI3 그룹 Master
# ============================================================

mti3_master = (
    df
    .groupby(
        "MTI3",
        as_index=False
    )
    .agg(
        MTI6_품목수=(
            "MTI6코드",
            "nunique"
        )
    )
    .sort_values(
        "MTI3"
    )
    .reset_index(drop=True)
)


# ============================================================
# 8. MTI4 그룹 Master
# ============================================================

mti4_master = (
    df
    .groupby(
        [
            "MTI3",
            "MTI4"
        ],
        as_index=False
    )
    .agg(
        MTI6_품목수=(
            "MTI6코드",
            "nunique"
        )
    )
    .sort_values(
        [
            "MTI3",
            "MTI4"
        ]
    )
    .reset_index(drop=True)
)


# ============================================================
# 9. 주요 그룹 샘플 확인
# ============================================================

TARGET_PREFIXES = [
    "831",  # 반도체
    "741",  # 자동차
    "742",  # 자동차부품
    "746",  # 선박
    "812",  # 무선통신
    "813",  # 컴퓨터
    "837",  # 디스플레이
    "931",  # 바이오의약품
]


print()
print("=" * 100)
print("주요 MTI3 그룹 샘플")
print("=" * 100)


for prefix in TARGET_PREFIXES:

    temp = (
        df[
            df["MTI3"]
            ==
            prefix
        ]
        [
            [
                "MTI3",
                "MTI4",
                "MTI6코드",
                "품목명"
            ]
        ]
    )

    print()
    print(
        f"[MTI3 {prefix}] "
        f"{len(temp)}개"
    )

    if temp.empty:
        print("없음")
    else:
        print(
            temp.head(30)
            .to_string(index=False)
        )


# ============================================================
# 10. CSV 저장
# ============================================================

df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)

mti3_master.to_csv(
    OUTPUT_MTI3,
    index=False,
    encoding="utf-8-sig"
)

mti4_master.to_csv(
    OUTPUT_MTI4,
    index=False,
    encoding="utf-8-sig"
)


print()
print("=" * 100)
print("CSV 저장 완료")
print("=" * 100)

print("- mti_hierarchy_1291.csv")
print("- mti3_master.csv")
print("- mti4_master.csv")


print()
print("=" * 100)
print("HIERARCHY BUILD COMPLETE")
print("=" * 100)