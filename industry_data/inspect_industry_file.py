from pathlib import Path
import pandas as pd


# -------------------------------------------------
# 1. 현재 Python 파일이 있는 폴더를 기준으로 설정
# -------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent


# -------------------------------------------------
# 2. Excel 파일 검색
# -------------------------------------------------

target_file = DATA_DIR / "KITA_MTI3_CORE_MONTHLY.xls"

if not target_file.exists():
    print("파일을 찾지 못했습니다.")
    print("찾는 파일:", target_file)
    raise SystemExit

print("=" * 70)
print("확인할 파일")
print("=" * 70)
print(target_file.name)


# -------------------------------------------------
# 3. Excel 시트 확인
# -------------------------------------------------

excel_file = pd.ExcelFile(target_file)

print()
print("=" * 70)
print("Excel 시트")
print("=" * 70)

for sheet in excel_file.sheet_names:
    print("-", sheet)


# -------------------------------------------------
# 4. 첫 번째 시트를 헤더 없이 그대로 읽기
# -------------------------------------------------

sheet_name = excel_file.sheet_names[0]

raw = pd.read_excel(
    target_file,
    sheet_name=sheet_name,
    header=None
)


# -------------------------------------------------
# 5. 데이터 크기
# -------------------------------------------------

print()
print("=" * 70)
print("원본 데이터 크기")
print("=" * 70)

print("행 수:", len(raw))
print("열 수:", len(raw.columns))


# -------------------------------------------------
# 6. 맨 위 20행을 원본 그대로 출력
# -------------------------------------------------

print()
print("=" * 70)
print("원본 상단 20행")
print("=" * 70)
print()

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 300)

print(
    raw.head(20).to_string(
        index=True,
        header=True
    )
)


# -------------------------------------------------
# 7. 각 열 번호 확인
# -------------------------------------------------

print()
print("=" * 70)
print("열 번호")
print("=" * 70)

for col in raw.columns:
    print(f"열 {col}")


# -------------------------------------------------
# 8. 값이 들어있는 첫 15개 행을 CSV 형태로 출력
# -------------------------------------------------

print()
print("=" * 70)
print("상단 데이터 - 구분자 방식")
print("=" * 70)

for idx, row in raw.head(15).iterrows():

    values = []

    for value in row:
        values.append(str(value))

    print(
        f"ROW {idx}: "
        + " | ".join(values)
    )

    print()
print("=" * 70)
print("핵심 헤더 구조")
print("=" * 70)

for idx in range(min(5, len(raw))):
    print(f"\nROW {idx}")

    for col_idx, value in enumerate(raw.iloc[idx]):
        if pd.notna(value):
            print(f"  열 {col_idx}: {value}")