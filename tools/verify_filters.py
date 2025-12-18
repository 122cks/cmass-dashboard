import pandas as pd
import os
BASE = os.path.dirname(os.path.abspath(__file__))
ORDER = os.path.join(BASE, '씨마스_22개정 주문현황_학교코드총판코드.csv')
TARGET = os.path.join(BASE, '22개정 총판별 목표.csv')

print('Reading order file:', ORDER)
order = pd.read_csv(ORDER, encoding='utf-8-sig')
print('order rows', len(order), 'sum 부수', int(order['부수'].sum()))

order_filtered = order[(order['학년도']==2026) & (order['목표과목'].isin(['목표과목1','목표과목2']))]
print('filtered rows', len(order_filtered), 'sum 부수', int(order_filtered['부수'].sum()))

if os.path.exists(TARGET):
    target = pd.read_csv(TARGET, encoding='utf-8-sig')
    print('target rows', len(target))
    cols = target.columns.tolist()
    print('target columns sample', cols[:20])
    target_summary = target.copy()
    for col in ['목표과목1 부수','목표과목2 부수','전체목표 부수']:
        if col in target_summary.columns:
            target_summary[col] = target_summary[col].astype(str).str.replace(',','').str.replace(' ','')
            target_summary[col] = pd.to_numeric(target_summary[col], errors='coerce').fillna(0)
    if '목표과목1 부수' in target_summary.columns and '목표과목2 부수' in target_summary.columns:
        target_summary['목표1'] = target_summary['목표과목1 부수']
        target_summary['목표2'] = target_summary['목표과목2 부수']
        target_summary['전체목표'] = target_summary['목표1'] + target_summary['목표2']
    else:
        target_summary['전체목표'] = target_summary.get('전체목표 부수', 0)
        target_summary['목표1'] = target_summary['전체목표'] * 0.5
        target_summary['목표2'] = target_summary['전체목표'] * 0.5
    print('total target sum', int(target_summary['전체목표'].sum()))
    actual = order_filtered.groupby('총판')['부수'].sum().reset_index()
    merged = pd.merge(target_summary[['총판명(공식)','전체목표']], actual, left_on='총판명(공식)', right_on='총판', how='outer').fillna(0)
    merged['달성률'] = merged['부수'] / merged['전체목표'] * 100
    merged_sorted = merged.sort_values('달성률', ascending=False)
    print('\nTop 10 by 달성률 (merged):')
    print(merged_sorted.head(10).to_string(index=False))
    # 통영)이문당 직접 확인
    imd = order[(order['총판'].str.contains('이문당', na=False, regex=False)) & (order['학년도']==2026)]
    print('\n통영)이문당 - 2026 전체 sum 부수:', int(imd['부수'].sum()))
    imd_filtered = imd[imd['목표과목'].isin(['목표과목1','목표과목2'])]
    print('통영)이문당 - 2026 목표과목1+2 sum 부수:', int(imd_filtered['부수'].sum()))
else:
    print('target file not found at', TARGET)
