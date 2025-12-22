import pandas as pd


def normalize(code_val):
    import pandas as pd
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
    orders = pd.read_csv('씨마스_22개정 주문현황_학교코드총판코드.csv', dtype=str, low_memory=False)
    mapdf = pd.read_csv('outputs/distributor_code_mapping.csv', dtype=str)

    mapped_codes = set(mapdf[mapdf['matched'].astype(str).str.lower()=='true']['order_code'].apply(normalize))

    if '총판코드' not in orders.columns:
        print('NO 총판코드 column')
        return

    orders['총판코드_norm'] = orders['총판코드'].apply(normalize)
    unique_codes = sorted([c for c in orders['총판코드_norm'].unique() if c!=''])

    unmapped = [c for c in unique_codes if c not in mapped_codes]
    print('unique_codes_count:', len(unique_codes))
    print('mapped_codes_count:', len(mapped_codes))
    print('unmapped_count:', len(unmapped))
    print('sample_unmapped (first 50):', unmapped[:50])

    # Also show top unmapped by total 부수
    orders['부수'] = pd.to_numeric(orders['부수'], errors='coerce').fillna(0)
    unmapped_rows = orders[orders['총판코드_norm'].isin(unmapped)].groupby('총판코드_norm')['부수'].sum().reset_index().sort_values('부수', ascending=False)
    print('\nTop unmapped by 부수:')
    print(unmapped_rows.head(30).to_string(index=False))


if __name__ == '__main__':
    main()
