import pandas as pd
import os
base = r'C:\Users\PC\OneDrive\01. CMASS\02. 영업팀\22개정 자사 실적표 조회화면'
ORDER = os.path.join(base, '씨마스_22개정 주문현황_학교코드총판코드.csv')
TARGET = os.path.join(base, '22개정 총판별 목표.csv')
DIST = os.path.join(base, '총판정보.csv')

print('=== 통영)이문당 실적 디버그 ===\n')

ord = pd.read_csv(ORDER, encoding='utf-8-sig')
ord.columns = ord.columns.str.strip()

# 목표과목 컬럼 찾기
target_col = None
if '목표과목' in ord.columns:
    target_col = '목표과목'
elif '2026 목표과목' in ord.columns:
    target_col = '2026 목표과목'
print(f'목표과목 컬럼: {target_col}')

# 2026년도 필터링
ord2026 = ord[ord['학년도'] == 2026].copy()
print(f'\n2026년 전체 주문: {len(ord2026):,}건, {int(ord2026["부수"].sum()):,}부')

# 목표과목1/2 필터링
if target_col:
    ord_filtered = ord2026[ord2026[target_col].isin(['목표과목1', '목표과목2'])].copy()
    print(f'2026년 목표과목1/2 주문: {len(ord_filtered):,}건, {int(ord_filtered["부수"].sum()):,}부')
else:
    ord_filtered = ord2026.copy()
    print('⚠️ 목표과목 컬럼 없음')

# 통영)이문당 관련 원본 총판명 찾기
imd_all = ord2026[ord2026['총판'].str.contains('이문당', na=False)]
print(f'\n통영)이문당 관련 원본 총판명들:')
for name in imd_all['총판'].unique():
    cnt = len(imd_all[imd_all['총판'] == name])
    ssum = int(imd_all[imd_all['총판'] == name]['부수'].sum())
    print(f'  - {name}: {cnt}건, {ssum:,}부')

print(f'\n통영)이문당 2026 전체 합계: {int(imd_all["부수"].sum()):,}부')

imd_filtered = ord_filtered[ord_filtered['총판'].str.contains('이문당', na=False)]
print(f'통영)이문당 2026 목표과목1/2 합계: {int(imd_filtered["부수"].sum()):,}부')

# 총판정보에서 공식명 확인
if os.path.exists(DIST):
    dist_df = pd.read_csv(DIST, encoding='utf-8-sig')
    dist_df.columns = dist_df.columns.str.strip()
    print(f'\n총판정보 파일 로드 완료 ({len(dist_df)}행)')
    
    if '총판명(공식)' in dist_df.columns:
        imd_official = dist_df[dist_df['총판명(공식)'].str.contains('이문당', na=False)]
        print(f'총판명(공식)에 이문당 포함된 행: {len(imd_official)}')
        for _, row in imd_official.iterrows():
            print(f'  공식명: {row.get("총판명(공식)")}')
            for col in ['총판명', '총판명1', '총판']:
                if col in dist_df.columns and pd.notna(row.get(col)):
                    print(f'    {col}: {row.get(col)}')
    
    # 주문 데이터의 총판명 중 이문당이 총판정보에 어떻게 매핑되는지 확인
    print(f'\n주문 데이터 총판명 → 총판정보 매핑 확인:')
    dist_map = {}
    for _, r in dist_df.iterrows():
        official = r.get('총판명(공식)')
        if pd.isna(official):
            continue
        for col in ['총판명', '총판명1', '총판']:
            if col in dist_df.columns and pd.notna(r.get(col)):
                dist_map[str(r.get(col)).strip()] = str(official).strip()
    
    for raw_name in imd_all['총판'].unique():
        mapped = dist_map.get(str(raw_name).strip(), '(매핑 없음)')
        print(f'  {raw_name} → {mapped}')

# 목표 확인
if os.path.exists(TARGET):
    tgt = pd.read_csv(TARGET, encoding='utf-8-sig')
    tgt.columns = tgt.columns.str.strip()
    imd_target = tgt[tgt['총판명(공식)'].str.contains('이문당', na=False)]
    if len(imd_target) > 0:
        print(f'\n목표 데이터에서 통영)이문당:')
        for _, row in imd_target.iterrows():
            t1 = str(row.get('목표과목1 부수', '')).replace(',', '').strip()
            t2 = str(row.get('목표과목2 부수', '')).replace(',', '').strip()
            t1 = int(float(t1)) if t1 and t1 != 'nan' else 0
            t2 = int(float(t2)) if t2 and t2 != 'nan' else 0
            print(f'  총판명(공식): {row.get("총판명(공식)")}')
            print(f'  목표과목1: {t1:,}부, 목표과목2: {t2:,}부, 합계: {t1+t2:,}부')
