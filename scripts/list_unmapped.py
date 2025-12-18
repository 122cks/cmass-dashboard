import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# one level up
BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, '..'))
ORDER_FILE = os.path.join(BASE_DIR, "씨마스_22개정 주문현황_학교코드총판코드.csv")
DISTRIBUTOR_FILE = os.path.join(BASE_DIR, "총판정보.csv")

def read_csv_fallback(path):
    try:
        return pd.read_csv(path, encoding='cp949')
    except Exception:
        try:
            return pd.read_csv(path, encoding='utf-8')
        except Exception as e:
            print(f"파일 읽기 실패: {path}: {e}")
            return pd.DataFrame()

order_df = read_csv_fallback(ORDER_FILE)
distributor_df = read_csv_fallback(DISTRIBUTOR_FILE)

# clean
order_df.columns = order_df.columns.str.strip()
distributor_df.columns = distributor_df.columns.str.strip()

# detect target column
target_col = None
for c in order_df.columns:
    if '목표과목' in str(c):
        target_col = c
        break

# filter order_2026 similar to app logic
if '학년도' in order_df.columns and target_col is not None:
    order_2026 = order_df[(order_df['학년도'] == 2026) & (order_df[target_col].isin(['목표과목1','목표과목2']))].copy()
elif '학년도' in order_df.columns:
    order_2026 = order_df[order_df['학년도'] == 2026].copy()
else:
    order_2026 = order_df.copy()

# build dist_map from distributor_df
mapped_keys = set()
if not distributor_df.empty and '총판명(공식)' in distributor_df.columns:
    for _, r in distributor_df.iterrows():
        official = r.get('총판명(공식)')
        if pd.isna(official):
            continue
        for col in ['총판명','총판명1','총판']:
            if col in distributor_df.columns and pd.notna(r.get(col)):
                mapped_keys.add(str(r.get(col)).strip())

# compute unmapped
if '총판' not in order_2026.columns:
    print("주문 데이터에 '총판' 컬럼이 없습니다.")
    exit(1)

order_totals = order_2026.groupby('총판')['부수'].sum().reset_index()
order_totals['총판_clean'] = order_totals['총판'].astype(str).str.strip()
unmapped = order_totals[~order_totals['총판_clean'].isin(mapped_keys)].copy()

print(f"전체 필터된 총판 수: {len(order_totals)}")
print(f"미매핑 총판 수: {len(unmapped)}")

if not unmapped.empty:
    unmapped = unmapped.sort_values('부수', ascending=False)
    print('\n상위 미매핑 총판 (최대 50개):')
    print(unmapped.head(50).to_string(index=False))
    out_path = os.path.join(BASE_DIR, 'unmapped_distributors_local.csv')
    unmapped[['총판','부수']].to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"\nCSV로 저장: {out_path}")
else:
    print('미매핑 총판이 없습니다.')
