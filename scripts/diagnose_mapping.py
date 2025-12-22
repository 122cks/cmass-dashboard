import pandas as pd
import os

BASE = os.path.dirname(os.path.dirname(__file__))
ORDERS_CSV = os.path.join(BASE, '씨마스_22개정 주문현황_학교코드총판코드.csv')
DIST_CSV = os.path.join(BASE, '총판정보.csv')
OUT_MAP = os.path.join(BASE, 'outputs', 'distributor_code_mapping.csv')


def normalize(code_val):
    if pd.isna(code_val):
        return ''
    s = str(code_val).strip()
    s = s.replace(',', '').strip()
    # remove common invisible characters
    s = s.replace('\u200b', '')
    if s.endswith('.0'):
        s = s[:-2]
    try:
        f = float(s)
        if f.is_integer():
            return str(int(f))
        return s
    except Exception:
        return s


def load_orders():
    orders = pd.read_csv(ORDERS_CSV, dtype=str, low_memory=False)
    if '총판코드' not in orders.columns:
        print('ERROR: orders has no 총판코드 column')
        return None
    orders['총판코드_norm'] = orders['총판코드'].apply(normalize)
    if '부수' in orders.columns:
        orders['부수_num'] = pd.to_numeric(orders['부수'], errors='coerce').fillna(0)
    else:
        orders['부수_num'] = 0
    return orders


def build_dist_map_from_dist():
    df = pd.read_csv(DIST_CSV, dtype=str, low_memory=False)
    # find code column
    code_col = None
    for c in ['숫자코드', '총판코드', '숫자코드.1']:
        if c in df.columns:
            code_col = c
            break
    if code_col is None:
        print('No code column in distributor file')
        return {}
    if '총판명(공식)' not in df.columns and '총판명' in df.columns:
        df['총판명(공식)'] = df['총판명']
    if '총판명(공식)' not in df.columns:
        print('No official name column in distributor file')
        return {}

    df['code_norm'] = df[code_col].apply(normalize)
    dmap = df.dropna(subset=['code_norm']).set_index('code_norm')['총판명(공식)'].to_dict()
    return dmap


def load_out_map():
    if not os.path.exists(OUT_MAP):
        return None
    df = pd.read_csv(OUT_MAP, dtype=str)
    if 'order_code' not in df.columns or 'official_name' not in df.columns:
        return None
    df['order_code_norm'] = df['order_code'].apply(normalize)
    df_true = df[df['matched'].astype(str).str.lower()=='true']
    return df_true.set_index('order_code_norm')['official_name'].to_dict()


def analyze():
    orders = load_orders()
    if orders is None:
        return
    dist_map_dist = build_dist_map_from_dist()
    out_map = load_out_map()

    print('orders unique codes:', len(orders['총판코드_norm'].unique()))
    print('dist_map (from 총판정보) size:', len(dist_map_dist))
    print('out_map size:', len(out_map) if out_map else 'NO_OUT_MAP')

    # Compare
    order_codes = sorted(set([c for c in orders['총판코드_norm'].unique() if c!='']))
    keys_dist = set(dist_map_dist.keys())
    keys_out = set(out_map.keys()) if out_map else set()

    # If out_map exists, prefer it
    preferred = keys_out if out_map else keys_dist
    unmapped = [c for c in order_codes if c not in preferred]
    print('\nPreferred map source:', 'outputs/distributor_code_mapping.csv' if out_map else '총판정보.csv')
    print('order unique codes count:', len(order_codes))
    print('mapped by preferred count:', len(order_codes) - len(unmapped))
    print('unmapped count:', len(unmapped))
    print('\nSample unmapped (first 50):', unmapped[:50])

    # Show top unmapped by 부수
    unmapped_rows = orders[orders['총판코드_norm'].isin(unmapped)].groupby('총판코드_norm')['부수_num'].sum().reset_index().sort_values('부수_num', ascending=False)
    print('\nTop unmapped by 부수 (if any):')
    print(unmapped_rows.head(30).to_string(index=False))

    # Show mapping key differences (whitespace, leading zeros, non-digit)
    def inspect_codes(codes):
        rows = []
        for c in codes:
            rows.append({'code': c, 'is_digit': c.isdigit(), 'len': len(c)})
        return pd.DataFrame(rows)

    if unmapped:
        print('\nInspect first 30 unmapped code characteristics:')
        print(inspect_codes(unmapped[:30]).to_string(index=False))

    # Show any codes in orders that look numeric but have leading zeros
    leading_zero = [c for c in order_codes if c.isdigit() and c.startswith('0')]
    print('\nCodes with leading zeros sample (first 20):', leading_zero[:20])

    # Show examples of order rows for a few codes
    examples = order_codes[:20]
    for ex in examples:
        sample = orders[orders['총판코드_norm']==ex][['총판','총판코드','총판코드_norm','부수']].head(5)
        if not sample.empty:
            print(f"\nExample rows for code {ex}:")
            print(sample.to_string(index=False))

if __name__ == '__main__':
    analyze()
