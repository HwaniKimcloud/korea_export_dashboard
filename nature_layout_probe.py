from pathlib import Path
import pandas as pd

from openpyxl.packaging.custom import CustomPropertyList


# ============================================================
# 관세청 Excel custom property 오류 우회
# ============================================================

def _ignore_broken_custom_properties(cls, node):
    return cls()


CustomPropertyList.from_tree = classmethod(
    _ignore_broken_custom_properties
)


# ============================================================
# 파일
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

FILE = (
    BASE_DIR
    / "industry_data"
    / "관세청조회코드_v1.2.xlsx"
)

SHEET = "성질통합분류코드"


# ============================================================
# 헤더 없이 원본 그대로 읽기
# ============================================================

df = pd.read_excel(
    FILE,
    sheet_name=SHEET,
    header=None,
    engine="openpyxl",
)


print()
print("=" * 100)
print("성질통합분류코드 RAW LAYOUT")
print("=" * 100)

print("행 수:", len(df))
print("열 수:", len(df.columns))

print()
print("[앞 20행]")
print()

pd.set_option(
    "display.max_columns",
    30,
)

pd.set_option(
    "display.width",
    250,
)

print(
    df.head(20).to_string(
        index=True,
        header=True,
    )
)


print()
print("=" * 100)
print("KEYWORD SEARCH")
print("=" * 100)


keywords = [
    "소분류",
    "세분류",
    "세세분류",
    "HSK",
    "신성질",
]


for keyword in keywords:

    print()
    print(
        f"[{keyword}]"
    )

    found = False

    for r in range(
        min(
            30,
            len(df),
        )
    ):

        values = [
            str(v)
            for v in df.iloc[r].tolist()
            if pd.notna(v)
        ]

        row_text = " | ".join(
            values
        )

        if keyword in row_text:

            print(
                f"ROW {r}: {row_text}"
            )

            found = True

    if not found:

        print(
            "검색 결과 없음"
        )


print()
print("=" * 100)
print("PROBE COMPLETE")
print("=" * 100)