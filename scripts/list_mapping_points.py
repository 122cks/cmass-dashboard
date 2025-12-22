import os
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ORDER_FILE = os.path.join(BASE_DIR, '씨마스_22개정 주문현황_학교코드총판코드.csv')
DISTRIBUTOR_FILE = os.path.join(BASE_DIR, '총판정보.csv')
OUT_DIR = os.path.join(BASE_DIR, 'outputs')
os.makedirs(OUT_DIR, exist_ok=True)


def _normalize_code(code_val) -> str:
    if pd.isna(code_val):
        return ''
    s = str(code_val).strip()
    s = s.replace(',', '').strip()
    if s.endswith('.0'):
        s = s[:-2]
    try:
        f = float(s)
        if f.is_integer():
            return str(int(f))
        return s
    except Exception:
        return s


def main():
    print('Loading files:')
    print('-', ORDER_FILE)
    print('-', DISTRIBUTOR_FILE)

    orders = pd.read_csv(ORDER_FILE, dtype=str, low_memory=False)
    dist = pd.read_csv(DISTRIBUTOR_FILE, dtype=str, low_memory=False)

    if '총판코드' not in orders.columns:
        print('ERROR: 주문 파일에 `총판코드` 컬럼이 없습니다.')
        return
    if '숫자코드' not in dist.columns and '총판코드' not in dist.columns:
        print('ERROR: 총판정보.csv에 `숫자코드` 또는 `총판코드` 컬럼이 없습니다.')
        return

    # Normalize
    orders['총판코드_norm'] = orders['총판코드'].apply(_normalize_code)
    dist_code_col = '숫자코드' if '숫자코드' in dist.columns else '총판코드'
    dist['숫자코드_norm'] = dist[dist_code_col].apply(_normalize_code)

    # Build sets
    order_codes = set([c for c in orders['총판코드_norm'].unique() if c and str(c).strip() != ''])
    dist_codes = set([c for c in dist['숫자코드_norm'].unique() if c and str(c).strip() != ''])

    matched = sorted(list(order_codes & dist_codes), key=lambda x: int(x) if x.isdigit() else x)
    only_in_orders = sorted(list(order_codes - dist_codes), key=lambda x: int(x) if x.isdigit() else x)
    only_in_dist = sorted(list(dist_codes - order_codes), key=lambda x: int(x) if x.isdigit() else x)

    print('\nCounts:')
    print(' total unique order codes:', len(order_codes))
    print(' total unique dist codes :', len(dist_codes))
    print(' matched codes          :', len(matched))
    print(' only in orders         :', len(only_in_orders))
    print(' only in dist           :', len(only_in_dist))

    # Produce CSV summaries
    # matched details: code, official_name (first), orders_count
    dist_name_map = dist.dropna(subset=['숫자코드_norm']).groupby('숫자코드_norm').first().to_dict(orient='index') if '숫자코드_norm' in dist.columns else {}

    rows = []
    for c in matched:
        name = ''
        # try find official name column variants
        for col in ['총판명(공식)', '총판명', '총판명_공식']:
            if col in dist.columns:
                val = dist[dist['숫자코드_norm'] == c][col].dropna().astype(str)
                if not val.empty:
                    name = val.iloc[0]
                    break
        orders_count = int(orders[orders['총판코드_norm'] == c].shape[0])
        rows.append({'code': c, 'official_name': name, 'orders_rows': orders_count})

    pd.DataFrame(rows).to_csv(os.path.join(OUT_DIR, 'mapping_matches.csv'), index=False, encoding='utf-8-sig')

    # orders-only (unmapped in dist)
    orders_unmapped = []
    for c in only_in_orders:
        cnt = int(orders[orders['총판코드_norm'] == c].shape[0])
        sample_names = orders[orders['총판코드_norm'] == c]['총판'].dropna().astype(str).unique().tolist()[:5]
        orders_unmapped.append({'code': c, 'orders_rows': cnt, 'sample_order_names': ';'.join(sample_names)})
    pd.DataFrame(orders_unmapped).to_csv(os.path.join(OUT_DIR, 'unmatched_orders_codes.csv'), index=False, encoding='utf-8-sig')

    # dist-only (codes in distributor list but not present in orders)
    dist_unmapped = []
    for c in only_in_dist:
        name = ''
        for col in ['총판명(공식)', '총판명', '총판명_공식']:
            if col in dist.columns:
                val = dist[dist['숫자코드_norm'] == c][col].dropna().astype(str)
                if not val.empty:
                    name = val.iloc[0]
                    break
        dist_unmapped.append({'code': c, 'official_name': name})
    pd.DataFrame(dist_unmapped).to_csv(os.path.join(OUT_DIR, 'unmatched_dist_codes.csv'), index=False, encoding='utf-8-sig')

    # Also write a small sample report
    report_lines = []
    report_lines.append(f"total unique order codes: {len(order_codes)}")
    report_lines.append(f"total unique dist codes : {len(dist_codes)}")
    report_lines.append(f"matched codes          : {len(matched)}")
    report_lines.append(f"only in orders         : {len(only_in_orders)}")
    report_lines.append(f"only in dist           : {len(only_in_dist)}")
    report_lines.append('\nfirst 20 matched codes:')
    report_lines.extend(matched[:20])
    report_lines.append('\nfirst 20 only_in_orders:')
    report_lines.extend(only_in_orders[:20])

    with open(os.path.join(OUT_DIR, 'mapping_report.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(map(str, report_lines)) + '\n')

    print('\nWrote outputs to', OUT_DIR)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise
