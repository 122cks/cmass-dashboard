import pandas as pd
import os
base = r'C:\Users\PC\OneDrive\01. CMASS\02. 영업팀\22개정 자사 실적표 조회화면'
ORDER_FILE = os.path.join(base, '씨마스_22개정 주문현황_학교코드총판코드.csv')
PRODUCT_FILE = os.path.join(base, '제품정보.csv')
print('Loading', ORDER_FILE)
order = pd.read_csv(ORDER_FILE, encoding='utf-8-sig')
print('Loading', PRODUCT_FILE)
product = pd.read_csv(PRODUCT_FILE, encoding='utf-8-sig')
print('\nproduct 학교급 unique values:')
print(product['학교급'].dropna().unique()[:50])
# prepare
product = product.dropna(subset=['코드'])
product['코드'] = product['코드'].astype(int).astype(str)
order['도서코드(교지명구분)'] = order['도서코드(교지명구분)'].astype(str)
merge_cols = ['코드', '학교급', '교과군', '교과서명']
pm = product[merge_cols].rename(columns={'교과군':'교과군_제품'})
merged = pd.merge(order, pm, left_on='도서코드(교지명구분)', right_on='코드', how='left')
print('\nMerged columns:')
print(merged.columns.tolist())

def add_school_level_to_subject(row):
    if pd.notna(row.get('학교급')) and pd.notna(row.get('교과서명')):
        school_level = str(row['학교급']).strip()
        subject = str(row['교과서명']).strip()
        try:
            lvl_num = int(school_level)
        except Exception:
            lvl_num = None
        if lvl_num == 3:
            return f'[중등] {subject}'
        if lvl_num == 4:
            return f'[고등] {subject}'
        low = school_level.lower()
        if '중' in low and '고' not in low:
            return f'[중등] {subject}'
        if '고' in low:
            return f'[고등] {subject}'
    return row.get('교과서명', '')

merged['교과서명_구분_calc'] = merged.apply(add_school_level_to_subject, axis=1)

# Find rows where 교과서명_구분_calc indicates 중등 but 학교급 contains 고등
mask = merged['교과서명_구분_calc'].str.contains(r'\[중등\]', na=False) & merged['학교급'].astype(str).str.contains('고', na=False)
mismatch1 = merged[mask]
print('\nRows where calculated [중등] but 학교급 contains "고" (sample 10):')
print(mismatch1[['도서코드(교지명구분)','학교급','교과서명','교과서명_구분_calc']].head(10).to_string(index=False))

# And vice versa: computed [고등] but 학교급 contains '중'
mask2 = merged['교과서명_구분_calc'].str.contains(r'\[고등\]', na=False) & merged['학교급'].astype(str).str.contains('중', na=False)
mismatch2 = merged[mask2]
print('\nRows where calculated [고등] but 학교급 contains "중" (sample 10):')
print(mismatch2[['도서코드(교지명구분)','학교급','교과서명','교과서명_구분_calc']].head(10).to_string(index=False))

# Count nulls in merge
print('\nCount of merged rows where 학교급 is null:', merged['학교급'].isna().sum())
print('Count where 교과서명 is null:', merged['교과서명'].isna().sum())

# Show examples where product merge failed but 교과서명 exists
fail_merge = merged[merged['교과서명'].isna() & merged['도서코드(교지명구분)'].notna()]
print('\nSample orders where product merge failed (교과서명 missing) 10 rows:')
print(fail_merge[['도서코드(교지명구분)','총판','학년도']].head(10).to_string(index=False))
