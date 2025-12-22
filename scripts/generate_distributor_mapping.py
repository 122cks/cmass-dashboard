import argparse
import pandas as pd
import os


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


def build_mapping(order_csv, distributor_csv, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    orders = pd.read_csv(order_csv, dtype=str, low_memory=False)
    dist = pd.read_csv(distributor_csv, dtype=str, low_memory=False)

    # Normalize distributor numeric code and official name
    if '숫자코드' not in dist.columns:
        raise RuntimeError('총판정보.csv에 `숫자코드` 컬럼이 필요합니다.')
    if '총판명(공식)' not in dist.columns:
        # try fallback
        if '총판명' in dist.columns:
            dist['총판명(공식)'] = dist['총판명']
        else:
            raise RuntimeError('총판정보.csv에 `총판명(공식)` 또는 `총판명` 컬럼이 필요합니다.')

    dist['숫자코드_norm'] = dist['숫자코드'].apply(_normalize_code)
    dist_map = dist.dropna(subset=['숫자코드_norm']).set_index('숫자코드_norm')['총판명(공식)'].to_dict()

    # Orders normalization
    if '총판코드' not in orders.columns:
        raise RuntimeError('주문현황 CSV에 `총판코드` 컬럼이 필요합니다.')
    orders['총판코드_norm'] = orders['총판코드'].apply(_normalize_code)

    # Prepare results
    # NOTE: 정책상 "주문현황의 총판(명칭)" 컬럼은 매핑 로직에 사용하지 않습니다.
    unique_order_codes = [c for c in orders['총판코드_norm'].dropna().unique().tolist() if c != '']
    all_dist_codes = sorted([c for c in dist_map.keys() if c != ''])

    rows = []
    seen = set()

    # 1) orders에 실제로 등장한 코드들을 우선 기록
    for code in unique_order_codes:
        if code in seen:
            continue
        seen.add(code)
        if code in dist_map:
            rows.append({'order_code': code, 'matched': True, 'official_code': code, 'official_name': dist_map.get(code), 'matched_by': 'code'})
        else:
            rows.append({'order_code': code, 'matched': False, 'official_code': '', 'official_name': '', 'matched_by': 'none'})

    # 2) 총판정보.csv에만 있는 코드들도 매핑 파일에 포함 (향후 주문 파일에 등장해도 즉시 매핑되도록)
    for code in all_dist_codes:
        if code in seen:
            continue
        seen.add(code)
        rows.append({'order_code': code, 'matched': True, 'official_code': code, 'official_name': dist_map.get(code), 'matched_by': 'dist_only'})

    df_map = pd.DataFrame(rows)
    mapped_count = df_map['matched'].sum()
    total = len(df_map)

    out_map_csv = os.path.join(out_dir, 'distributor_code_mapping.csv')
    out_unmapped_csv = os.path.join(out_dir, 'distributor_code_unmapped.csv')

    df_map.to_csv(out_map_csv, index=False, encoding='utf-8-sig')
    df_map[df_map['matched'] == False].to_csv(out_unmapped_csv, index=False, encoding='utf-8-sig')

    print(f"총 unique 주문코드: {total}")
    print(f"매핑된 코드: {int(mapped_count)}")
    print(f"매핑 결과: {out_map_csv}")
    print(f"미매핑 샘플(최대 20):")
    print(df_map[df_map['matched'] == False].head(20).to_string(index=False))
    return out_map_csv, out_unmapped_csv


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--orders', default=r'씨마스_22개정 주문현황_학교코드총판코드.csv')
    p.add_argument('--distributor', default=r'총판정보.csv')
    p.add_argument('--out', default='outputs')
    args = p.parse_args()

    build_mapping(args.orders, args.distributor, args.out)
