import pandas as pd, os
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ORDER_FILE = os.path.join(BASE_DIR, '씨마스_22개정 주문현황_학교코드총판코드.csv')
DISTRIBUTOR_FILE = os.path.join(BASE_DIR, '총판정보.csv')

def read_csv_safe(path):
    try:
        return pd.read_csv(path, encoding='cp949')
    except Exception:
        return pd.read_csv(path, encoding='utf-8')

order = read_csv_safe(ORDER_FILE)
dist = read_csv_safe(DISTRIBUTOR_FILE)
order.columns = order.columns.str.strip()
dist.columns = dist.columns.str.strip()
# build map keys
mapped=set()
if '총판명(공식)' in dist.columns:
    for _, row in dist.iterrows():
        if pd.isna(row.get('총판명(공식)')): continue
        for c in ['총판명','총판명1','총판']:
            if c in dist.columns and pd.notna(row.get(c)):
                mapped.add(str(row.get(c)).strip())
all_unique = set(order['총판'].astype(str).str.strip().unique())
unmapped = sorted([x for x in all_unique if x not in mapped])
print('전체 주문 고유 총판 수:', len(all_unique))
print('마스터 매핑 키 수:', len(mapped))
print('미매핑 고유 총판 수:', len(unmapped))
print('\n미매핑 예시(최대 100):')
for i,n in enumerate(unmapped[:100],1): print(i,n)
