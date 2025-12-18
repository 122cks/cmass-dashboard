import pandas as pd
import os
base = r'C:\Users\PC\OneDrive\01. CMASS\02. 영업팀\22개정 자사 실적표 조회화면'
order_file = os.path.join(base, '씨마스_22개정 주문현황_학교코드총판코드.csv')
print('Reading', order_file)
ord = pd.read_csv(order_file, encoding='utf-8-sig')
print('rows', len(ord), 'total 부수', int(ord['부수'].sum()))
ord2026 = ord[ord['학년도']==2026]
print('2026 rows', len(ord2026), '2026 부수', int(ord2026['부수'].sum()))
ord_filtered = ord2026[ord2026['목표과목'].isin(['목표과목1','목표과목2'])]
print('2026 filtered rows', len(ord_filtered), 'filtered 부수', int(ord_filtered['부수'].sum()))
imd_all = ord2026[ord2026['총판'].str.contains('이문당', na=False, regex=False)]
print('통영)이문당 2026 전체 부수', int(imd_all['부수'].sum()))
imd_filtered = ord_filtered[ord_filtered['총판'].str.contains('이문당', na=False, regex=False)]
print('통영)이문당 2026 목표과목1+2 부수', int(imd_filtered['부수'].sum()))
