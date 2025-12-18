import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="목표 대비 달성률", page_icon="🎯", layout="wide")

# Get data
if 'order_df' not in st.session_state:
    st.error("데이터를 불러올 수 없습니다. 메인 페이지로 돌아가주세요.")
    st.stop()

# 🚨 목표 대비 달성률은 목표과목 필터된 데이터 사용
order_df = st.session_state.get('order_df_target_filtered', st.session_state['order_df']).copy()
target_df = st.session_state.get('target_df', pd.DataFrame())
distributor_df = st.session_state.get('distributor_df', pd.DataFrame())

st.title("🎯 목표 대비 달성률 분석")
st.markdown("---")

# Check if target data exists
if target_df.empty or '총판명(공식)' not in target_df.columns:
    st.warning("⚠️ 목표 데이터가 없습니다. 메인 페이지에서 데이터를 확인해주세요.")
    st.stop()

# 목표 데이터 전처리
target_summary = target_df.copy()

# 쉼표 제거 및 숫자 변환
for col in ['목표과목1 부수', '목표과목2 부수', '전체목표 부수']:
    if col in target_summary.columns:
        target_summary[col] = target_summary[col].astype(str).str.replace(',', '').str.replace(' ', '')
        target_summary[col] = pd.to_numeric(target_summary[col], errors='coerce').fillna(0)

# 전체 목표 = 목표1 + 목표2
if '목표과목1 부수' in target_summary.columns and '목표과목2 부수' in target_summary.columns:
    target_summary['목표1'] = target_summary['목표과목1 부수']
    target_summary['목표2'] = target_summary['목표과목2 부수']
    target_summary['전체목표'] = target_summary['목표1'] + target_summary['목표2']
else:
    target_summary['전체목표'] = target_summary.get('전체목표 부수', 0)
    target_summary['목표1'] = target_summary['전체목표'] * 0.5
    target_summary['목표2'] = target_summary['전체목표'] * 0.5

# 총판별 실적 집계 - 2026년도 목표과목1, 목표과목2만
st.info("💡 목표는 2026년도 기준이므로, 2026년도 목표과목1·목표과목2 주문만 집계하여 달성률을 계산합니다.")

# order_df는 이미 목표과목 필터된 데이터이므로 바로 사용
order_2026 = order_df.copy()

school_code_col = '정보공시학교코드' if '정보공시학교코드' in order_2026.columns else '학교코드'

# 디버깅: 필터링 결과 확인
st.sidebar.write(f"✅ 2026+목표과목1/2: {len(order_2026):,}건 ({int(order_2026['부수'].sum()):,}부)")
test_imd = order_2026[order_2026['총판'].str.contains('이문당', na=False)]
if len(test_imd) > 0:
    imd_sum_filtered = int(test_imd['부수'].sum())
    st.sidebar.write(f"🎯 통영)이문당(필터): {imd_sum_filtered:,}부")
else:
    imd_sum_filtered = 0

# 명확한 시각적 확인을 위해 페이지 상단에 주요 KPI 노출
col_a, col_b, col_c = st.columns([2, 2, 6])
with col_a:
    st.metric("필터 적용 건수", f"{len(order_2026):,}건")
with col_b:
    st.metric("필터 적용 부수", f"{int(order_2026['부수'].sum()):,}부")
with col_c:
    st.metric("통영)이문당(목표과목)", f"{imd_sum_filtered:,}부", help="2026년 목표과목1/2만 집계")

actual_stats = order_2026.groupby('총판').agg({
    '부수': 'sum',
    school_code_col: 'nunique',
    '금액': 'sum' if '금액' in order_2026.columns else 'count'
}).reset_index()
actual_stats.columns = ['총판', '실적부수', '거래학교수', '주문금액']

# 🎯 총판코드 매핑 테이블 먼저 생성
dist_code_map = {}  # {총판코드: 총판명(공식)}

if not distributor_df.empty and '총판명(공식)' in distributor_df.columns and '총판코드' in distributor_df.columns:
    for _, r in distributor_df.iterrows():
        official = r.get('총판명(공식)')
        code_val = r.get('총판코드')
        
        if pd.isna(official) or pd.isna(code_val):
            continue
        
        official_str = str(official).strip()
        
        # 총판코드를 정규화 (123.0 → "123")
        try:
            if isinstance(code_val, (int, float)) and not pd.isna(code_val):
                code_str = str(int(code_val)) if float(code_val).is_integer() else str(code_val).strip()
            else:
                code_str = str(code_val).strip()
        except Exception:
            code_str = str(code_val).strip()
        
        dist_code_map[code_str] = official_str

st.sidebar.info(f"✅ 총판코드 매핑: {len(dist_code_map)}개 총판")

# 목표 데이터를 총판코드로 그룹화
if '총판코드' in target_summary.columns:
    # 총판코드 정규화
    target_summary['총판코드_정규화'] = target_summary['총판코드'].apply(lambda x: 
        str(int(x)) if isinstance(x, (int, float)) and not pd.isna(x) and float(x).is_integer() 
        else str(x).strip() if pd.notna(x) else '')
    
    # 총판코드별 목표 집계 후 공식명 매핑
    target_by_code = target_summary.groupby('총판코드_정규화').agg({
        '전체목표': 'sum',
        '목표1': 'sum',
        '목표2': 'sum'
    }).reset_index()
    
    # 총판명(공식) 매핑
    target_by_code['총판명(공식)'] = target_by_code['총판코드_정규화'].map(dist_code_map)
    target_map = target_by_code[target_by_code['총판명(공식)'].notna()][[
        '총판명(공식)', '전체목표', '목표1', '목표2'
    ]].copy()
else:
    # Fallback: 총판명(공식)으로 그룹화
    target_map = target_summary.groupby('총판명(공식)').agg({
        '전체목표': 'sum',
        '목표1': 'sum',
        '목표2': 'sum'
    }).reset_index()
    st.sidebar.warning("⚠️ 목표 데이터에 총판코드가 없습니다!")

# --- 미매핑 총판 보고 (총판코드 기준)
if '총판코드' in order_2026.columns:
    # 총판코드 정규화
    order_2026['총판코드_정규화'] = order_2026['총판코드'].apply(lambda x: 
        str(int(x)) if isinstance(x, (int, float)) and not pd.isna(x) and float(x).is_integer() 
        else str(x).strip() if pd.notna(x) else '')
    
    mapped_codes = set(dist_code_map.keys())
    order_totals = order_2026.groupby(['총판', '총판코드_정규화'])['부수'].sum().reset_index()
    unmapped = order_totals[~order_totals['총판코드_정규화'].isin(mapped_codes)]
    unmapped = unmapped[unmapped['총판코드_정규화'] != '']  # 빈 코드 제외
    
    if not unmapped.empty:
        unmapped = unmapped.sort_values('부수', ascending=False)
        st.sidebar.warning(f"⚠️ 총판코드 미매핑: {len(unmapped)}개")
        st.sidebar.dataframe(
            unmapped[['총판', '총판코드_정규화', '부수']].rename(columns={'부수':'필터된 부수'}), 
            use_container_width=True
        )
        try:
            csv_unmapped = unmapped[['총판', '총판코드_정규화', '부수']].to_csv(index=False, encoding='utf-8-sig')
            st.sidebar.download_button("📥 미매핑 총판 CSV 다운로드", data=csv_unmapped, file_name='unmapped_distributors.csv', mime='text/csv')
        except Exception:
            pass
else:
    st.sidebar.error("⚠️ 총판코드 컬럼이 없습니다!")

# 🎯 총판코드 기반 매핑 완료

# --- 실적 집계: 총판코드로 매핑
order_actual_df = order_2026.copy()

def _map_row_to_official(row):
    """총판코드로만 매핑 (이름 기반 매핑 제거)"""
    if '총판코드' in row.index and pd.notna(row.get('총판코드')):
        code_val = row.get('총판코드')
        try:
            # 총판코드 정규화
            if isinstance(code_val, (int, float)) and not pd.isna(code_val):
                code_str = str(int(code_val)) if float(code_val).is_integer() else str(code_val).strip()
            else:
                code_str = str(code_val).strip()
        except Exception:
            code_str = str(code_val).strip()
        
        # 총판코드로 공식명 매핑
        if code_str in dist_code_map:
            return dist_code_map[code_str]
        else:
            # 매핑 실패 - 총판코드 반환 (디버깅용)
            return f"[미매핑:{code_str}]"
    
    # 총판코드가 없으면 총판명 반환 (경고)
    return f"[코드없음:{row.get('총판', 'N/A')}]"

# Aggregate by original identifiers then map to official names
if '총판코드' in order_actual_df.columns:
    agg_cols = ['총판', '총판코드']
else:
    agg_cols = ['총판']

order_actual = order_actual_df.groupby(agg_cols)['부수'].sum().reset_index()
order_actual['총판_key'] = order_actual.apply(_map_row_to_official, axis=1)
actual_by_official = order_actual.groupby('총판_key')['부수'].sum().to_dict()

# 추가 지표(거래학교수, 주문금액)도 동일한 방식으로 공식명 기준 집계
metric_agg = {'부수': 'sum'}
if school_code_col in order_actual_df.columns:
    metric_agg[school_code_col] = 'nunique'
if '금액' in order_actual_df.columns:
    metric_agg['금액'] = 'sum'
else:
    # 금액 컬럼이 없으면 0으로 채울 수 있도록 더미 집계(부수 합계 사용)
    metric_agg['금액'] = 'sum'

order_metrics = order_actual_df.groupby(agg_cols).agg(metric_agg).reset_index()
order_metrics['총판_key'] = order_metrics.apply(_map_row_to_official, axis=1)

# 그룹핑하여 공식명 기준으로 합산
metrics_by_official = order_metrics.groupby('총판_key').agg({
    '부수': 'sum',
    school_code_col: 'sum' if school_code_col in order_metrics.columns else 'sum',
    '금액': 'sum'
}).reset_index()
metrics_by_official.columns = ['총판명(공식)', '실적부수_tmp', '거래학교수', '주문금액']

# 실적부수는 기존 actual_by_official과 합치거나 대체
metrics_by_official_map = metrics_by_official.set_index('총판명(공식)')['실적부수_tmp'].to_dict()
trade_school_map = metrics_by_official.set_index('총판명(공식)')['거래학교수'].to_dict()
order_amount_map = metrics_by_official.set_index('총판명(공식)')['주문금액'].to_dict()

# 디버그: 이문당 매핑 전/후 체크
raw_imd_sum = order_actual[order_actual['총판'].astype(str).str.contains('이문당', na=False)]['부수'].sum()
if raw_imd_sum > 0:
    st.sidebar.info(f"🔍 '이문당' 원본 실적: {int(raw_imd_sum):,}부")

if '통영)이문당' in actual_by_official:
    st.sidebar.success(f"✅ '통영)이문당' 최종 실적: {int(actual_by_official['통영)이문당']):,}부")
elif '이문당' in actual_by_official:
    st.sidebar.warning(f"⚠️ '이문당'이 매핑되지 않음: {int(actual_by_official['이문당']):,}부")

# 세션 초기화 버튼 (세션 캐시 문제로 인해 UI가 갱신되지 않을 때 사용)
if st.sidebar.button('🔁 세션 초기화 및 재실행'):
    keys_to_clear = ['order_df', 'order_df_original', 'target_df', 'distributor_df', 'order_df_target_filtered']
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()

# 실제 실적 상위 공식명 확인용 데이터프레임
actual_official_df = pd.DataFrame([{'총판명(공식)': k, '실적부수': v} for k, v in actual_by_official.items()])

# 등급 정보 추가
if not distributor_df.empty and '등급' in distributor_df.columns and '총판명(공식)' in distributor_df.columns:
    grade_map = distributor_df.set_index('총판명(공식)')['등급'].to_dict()
    target_map['등급'] = target_map['총판명(공식)'].map(grade_map)
    actual_official_df['등급'] = actual_official_df['총판명(공식)'].map(grade_map)

# --- 총판코드 기반 매핑 상세 디버그
if not actual_official_df.empty and '총판코드' in order_2026.columns:
    actual_official_df = actual_official_df.sort_values('실적부수', ascending=False)
    
    # [미매핑:xxx] 형식 제외한 정상 매핑만
    valid_officials = actual_official_df[~actual_official_df['총판명(공식)'].astype(str).str.contains(r'\[미매핑:', na=False, regex=True)]
    top_officials = valid_officials.head(10)['총판명(공식)'].tolist() if not valid_officials.empty else []

    # 기본 선택은 '통영)이문당'이 있으면 선택
    default_select = '통영)이문당' if '통영)이문당' in valid_officials['총판명(공식)'].values else (top_officials[0] if top_officials else None)

    if default_select and top_officials:
        sel = st.sidebar.selectbox('🔎 실적 상위 공식명 선택(매핑 상세)', options=top_officials, index=top_officials.index(default_select) if default_select in top_officials else 0)
        
        # 해당 공식명에 매핑된 총판코드 찾기
        reverse_code_map = {v: k for k, v in dist_code_map.items()}
        sel_code = reverse_code_map.get(sel)
        
        if sel_code and '총판코드_정규화' in order_2026.columns:
            contrib_rows = order_2026[order_2026['총판코드_정규화'] == sel_code].copy()
            contrib_sum = int(contrib_rows['부수'].sum()) if not contrib_rows.empty else 0

            st.sidebar.markdown(f"**선택 공식명:** {sel}")
            st.sidebar.markdown(f"**총판코드:** {sel_code}")
            st.sidebar.markdown(f"**합계 실적:** {contrib_sum:,}부")
            
            if not contrib_rows.empty:
                st.sidebar.dataframe(
                    contrib_rows.groupby('총판')['부수'].sum().reset_index().rename(columns={'부수':'필터된 부수'}), 
                    use_container_width=True
                )
        else:
            st.sidebar.info(f"{sel}에 매핑된 총판코드를 찾을 수 없습니다.")


# 상위 공식명 리스트(요약)도 노출
if not actual_official_df.empty:
    st.sidebar.markdown("**실적 상위 공식명(요약)**")
    # [미매핑:xxx] 형식 제외
    display_df = actual_official_df[~actual_official_df['총판명(공식)'].astype(str).str.contains(r'\[미매핑:', na=False, regex=True)]
    st.sidebar.dataframe(display_df.head(10).reset_index(drop=True), use_container_width=True)

# Build achievement_df from target_map and map 실적부수 from actual_by_official
achievement_df = target_map.copy()
achievement_df['실적부수'] = achievement_df['총판명(공식)'].map(lambda x: int(actual_by_official.get(str(x).strip(), 0)))
# 거래학교수 및 주문금액 채우기 (매핑된 값이 있으면 사용, 없으면 0)
achievement_df['거래학교수'] = achievement_df['총판명(공식)'].map(lambda x: int(trade_school_map.get(str(x).strip(), 0)))
achievement_df['주문금액'] = achievement_df['총판명(공식)'].map(lambda x: float(order_amount_map.get(str(x).strip(), 0)))

# Fill numeric NaNs for 목표 컬럼
for col in ['전체목표', '목표1', '목표2', '실적부수']:
    if col in achievement_df.columns:
        achievement_df[col] = achievement_df[col].fillna(0)

# 총판 통일
achievement_df['총판'] = achievement_df['총판명(공식)']

# --- 디버그: 통영)이문당 관련 매핑/실적 출처 확인
debug_official = '통영)이문당'
if debug_official in achievement_df['총판'].values and '총판코드_정규화' in order_2026.columns:
    official_row = achievement_df[achievement_df['총판'] == debug_official].iloc[0]
    sidebar_debug = []
    sidebar_debug.append({'항목':'achievement_df 실적부수', '값': int(official_row['실적부수'])})
    sidebar_debug.append({'항목':'achievement_df 전체목표', '값': int(official_row['전체목표'])})
    
    # 해당 공식명의 총판코드 찾기
    reverse_code_map = {v: k for k, v in dist_code_map.items()}
    debug_code = reverse_code_map.get(debug_official)
    
    if debug_code:
        sidebar_debug.append({'항목':'총판코드', '값': debug_code})
        contribs = order_2026[order_2026['총판코드_정규화'] == debug_code].groupby('총판')['부수'].sum().reset_index()
        if not contribs.empty:
            for _, r in contribs.iterrows():
                sidebar_debug.append({'항목':f"원본 총판: {r['총판']}", '값': int(r['부수'])})

    # actual_by_official value
    sidebar_debug.append({'항목':'actual_by_official[통영)이문당]', '값': int(actual_by_official.get(debug_official, 0))})
    try:
        st.sidebar.markdown('**[디버그] 통영)이문당 매핑/실적 출처**')
        st.sidebar.dataframe(pd.DataFrame(sidebar_debug), use_container_width=True)
    except Exception:
        pass

# 달성률 계산
achievement_df['전체달성률(%)'] = (achievement_df['실적부수'] / achievement_df['전체목표'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
achievement_df['목표1달성률(%)'] = (achievement_df['실적부수'] / achievement_df['목표1'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
achievement_df['목표2달성률(%)'] = (achievement_df['실적부수'] / achievement_df['목표2'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
achievement_df['차이'] = achievement_df['실적부수'] - achievement_df['전체목표']

# 데이터 정제: 숫자형 NaN 제거 및 총판명 결측치 처리
num_cols = ['전체목표', '목표1', '목표2', '실적부수', '전체달성률(%)', '차이']
for c in num_cols:
    if c in achievement_df.columns:
        achievement_df[c] = pd.to_numeric(achievement_df[c], errors='coerce').fillna(0)
achievement_df['총판'] = achievement_df['총판'].fillna('')

# 등급 정보 추가
if not distributor_df.empty and '총판명(공식)' in distributor_df.columns and '등급' in distributor_df.columns:
    # 중복 제거하여 매핑
    grade_map = distributor_df.drop_duplicates(subset='총판명(공식)').set_index('총판명(공식)')['등급'].to_dict()
    achievement_df['등급'] = achievement_df['총판'].map(grade_map).fillna('미분류')
else:
    achievement_df['등급'] = '미분류'

# 학생수 기반 시장규모 및 점유율 추가
distributor_market = st.session_state.get('distributor_market', pd.DataFrame())
if not distributor_market.empty and '총판명(공식)' in distributor_market.columns:
    # 시장규모 매핑
    market_size_map = distributor_market.set_index('총판명(공식)')['시장규모'].to_dict()
    achievement_df['시장규모'] = achievement_df['총판'].map(market_size_map).fillna(0)
    # 점유율 계산
    achievement_df['점유율(%)'] = achievement_df.apply(
        lambda row: (row['실적부수'] / row['시장규모'] * 100) if row['시장규모'] > 0 else 0,
        axis=1
    )
else:
    # Fallback: 전체 학생수 기반
    total_students = st.session_state.get('total_df', pd.DataFrame())['학생수(계)'].sum() if 'total_df' in st.session_state else 0
    achievement_df['시장규모'] = total_students
    achievement_df['점유율(%)'] = (achievement_df['실적부수'] / total_students * 100) if total_students > 0 else 0

# 목표가 있는 총판만 필터링
achievement_df = achievement_df[achievement_df['전체목표'] > 0]

# Sidebar Filters
st.sidebar.header("🔍 필터 옵션")

# Grade Filter
if '등급' in achievement_df.columns:
    grade_order = ['S', 'A', 'B', 'C', 'D', 'E', 'G', '미분류']
    available_grades = [g for g in grade_order if g in achievement_df['등급'].unique()]
    selected_grades = st.sidebar.multiselect(
        "등급 선택",
        available_grades,
        default=available_grades
    )
    if selected_grades:
        achievement_df = achievement_df[achievement_df['등급'].isin(selected_grades)]

# Achievement Filter
achievement_filter = st.sidebar.radio(
    "달성률 필터",
    ["전체", "달성 (≥100%)", "미달성 (<100%)", "우수 (≥120%)", "부진 (<80%)"]
)

if achievement_filter == "달성 (≥100%)":
    achievement_df = achievement_df[achievement_df['전체달성률(%)'] >= 100]
elif achievement_filter == "미달성 (<100%)":
    achievement_df = achievement_df[achievement_df['전체달성률(%)'] < 100]
elif achievement_filter == "우수 (≥120%)":
    achievement_df = achievement_df[achievement_df['전체달성률(%)'] >= 120]
elif achievement_filter == "부진 (<80%)":
    achievement_df = achievement_df[achievement_df['전체달성률(%)'] < 80]

achievement_df = achievement_df.sort_values('전체달성률(%)', ascending=False)

st.sidebar.markdown("---")
st.sidebar.info(f"📊 분석 대상 총판: {len(achievement_df)}개")

# Main Metrics
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    total_target = achievement_df['전체목표'].sum()
    st.metric("전체 목표", f"{total_target:,.0f}부")

with col2:
    total_actual = achievement_df['실적부수'].sum()
    st.metric("전체 실적", f"{total_actual:,.0f}부")

with col3:
    overall_rate = (total_actual / total_target * 100) if total_target > 0 else 0
    st.metric("전체 달성률", f"{overall_rate:.1f}%", 
             delta=f"{total_actual - total_target:,.0f}부")

with col4:
    total_market = achievement_df['시장규모'].sum()
    overall_share = (total_actual / total_market * 100) if total_market > 0 else 0
    st.metric("학생수 대비 점유율", f"{overall_share:.2f}%",
             help="담당 학교 학생수(중등/고등 1,2학년) 대비 주문 비율")

with col5:
    achieved_count = len(achievement_df[achievement_df['전체달성률(%)'] >= 100])
    st.metric("목표 달성 총판", f"{achieved_count}/{len(achievement_df)}개")

st.markdown("---")

# Tab Layout
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 전체 현황", "🏆 TOP/BOTTOM", "📈 등급별 분석", "📋 상세 테이블", "📉 갭 분석"])

with tab1:
    st.subheader("📊 목표 대비 달성률 전체 현황")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 목표 vs 실적 비교 차트
        fig1 = go.Figure()
        
        top_20 = achievement_df.head(20).copy()
        # 안전성: 결측치 채우기
        for col in ['총판', '전체목표', '실적부수']:
            if col in top_20.columns:
                top_20[col] = top_20[col].fillna('' if col == '총판' else 0)

        if top_20.empty:
            st.info('표시할 데이터가 없습니다.')
        else:
            fig1.add_trace(go.Bar(
                name='목표',
                x=top_20['총판'],
                y=top_20['전체목표'],
                marker_color='lightblue',
                text=top_20['전체목표'],
                texttemplate='%{text:,.0f}',
                textposition='outside'
            ))

            fig1.add_trace(go.Bar(
                name='실적',
                x=top_20['총판'],
                y=top_20['실적부수'],
                marker_color='green',
                text=top_20['실적부수'],
                texttemplate='%{text:,.0f}',
                textposition='outside'
            ))

            fig1.update_layout(
                title="목표 vs 실적 비교 TOP 20",
                barmode='group',
                xaxis_tickangle=-45,
                height=500
            )
            st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # 달성률 차트
        df_top_rate = achievement_df.head(20).copy()
        if df_top_rate.empty:
            st.info('달성률 데이터가 없습니다.')
        else:
            df_top_rate['전체달성률(%)'] = df_top_rate['전체달성률(%)'].fillna(0)
            fig2 = px.bar(
                df_top_rate,
                x='총판',
                y='전체달성률(%)',
                title="목표 달성률 TOP 20",
                text='전체달성률(%)',
                color='전체달성률(%)',
                color_continuous_scale='RdYlGn'
            )
            fig2.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig2.update_layout(xaxis_tickangle=-45, height=500)
            fig2.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="목표선")
            st.plotly_chart(fig2, use_container_width=True)
    
    # 달성률 분포
    st.markdown("---")
    st.subheader("📊 달성률 분포")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 히스토그램
        fig_hist = px.histogram(
            achievement_df,
            x='전체달성률(%)',
            nbins=20,
            title="달성률 분포",
            labels={'전체달성률(%)': '달성률 (%)', 'count': '총판 수'}
        )
        fig_hist.add_vline(x=100, line_dash="dash", line_color="red", annotation_text="목표선")
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
        # 달성률 구간별 총판 수
        achievement_df['달성구간'] = pd.cut(
            achievement_df['전체달성률(%)'],
            bins=[0, 50, 80, 100, 120, float('inf')],
            labels=['50% 미만', '50-80%', '80-100%', '100-120%', '120% 이상']
        )
        
        interval_dist = achievement_df['달성구간'].value_counts().reset_index()
        interval_dist.columns = ['달성구간', '총판수']
        
        fig_pie = px.pie(
            interval_dist,
            values='총판수',
            names='달성구간',
            title="달성률 구간별 총판 분포",
            color_discrete_sequence=px.colors.diverging.RdYlGn
        )
        st.plotly_chart(fig_pie, use_container_width=True)

with tab2:
    st.subheader("🏆 TOP/BOTTOM 달성 총판")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🥇 TOP 10 (달성률 기준)")
        top10 = achievement_df.head(10)
        
        for idx, row in top10.iterrows():
            rank = top10.index.tolist().index(idx) + 1
            emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "⭐"
            
            st.markdown(f"""
            <div style="border: 2px solid #4CAF50; border-radius: 10px; padding: 15px; margin: 10px 0;">
                <h4>{emoji} #{rank} {row['총판']} ({row['등급']}등급)</h4>
                <p><b>달성률:</b> {row['전체달성률(%)']:.1f}%</p>
                <p><b>목표:</b> {row['전체목표']:,.0f}부 → <b>실적:</b> {row['실적부수']:,.0f}부</p>
                <p><b>초과:</b> <span style="color: green;">{row['차이']:,.0f}부</span></p>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 📉 BOTTOM 10 (달성률 기준)")
        bottom10 = achievement_df.tail(10).iloc[::-1]
        
        for idx, row in bottom10.iterrows():
            rank = len(achievement_df) - achievement_df.index.tolist().index(idx)
            
            st.markdown(f"""
            <div style="border: 2px solid #E94B3C; border-radius: 10px; padding: 15px; margin: 10px 0;">
                <h4>#{rank} {row['총판']} ({row['등급']}등급)</h4>
                <p><b>달성률:</b> {row['전체달성률(%)']:.1f}%</p>
                <p><b>목표:</b> {row['전체목표']:,.0f}부 → <b>실적:</b> {row['실적부수']:,.0f}부</p>
                <p><b>부족:</b> <span style="color: red;">{row['차이']:,.0f}부</span></p>
            </div>
            """, unsafe_allow_html=True)

with tab3:
    st.subheader("📈 등급별 달성률 분석")
    
    if '등급' not in achievement_df.columns or achievement_df['등급'].isna().all():
        st.warning("등급 정보가 없습니다. 총판정보.csv에 등급 컬럼이 있는지 확인해주세요.")
    else:
        # 등급별 집계
        grade_achievement = achievement_df.groupby('등급').agg({
            '전체목표': 'sum',
            '실적부수': 'sum',
            '시장규모': 'sum',
            '거래학교수': 'sum',
            '총판': 'count'
        }).reset_index()
        grade_achievement.columns = ['등급', '목표합계', '실적합계', '시장규모', '거래학교수', '총판수']
        grade_achievement['평균달성률(%)'] = (grade_achievement['실적합계'] / grade_achievement['목표합계'] * 100).fillna(0)
        grade_achievement['점유율(%)'] = (grade_achievement['실적합계'] / grade_achievement['시장규모'] * 100).fillna(0)
        grade_achievement['총판당평균실적'] = (grade_achievement['실적합계'] / grade_achievement['총판수']).fillna(0)
        
        # 등급 순서 정렬
        grade_order = ['S', 'A', 'B', 'C', 'D', 'E', 'G', '미분류']
        grade_achievement['등급_order'] = grade_achievement['등급'].apply(lambda x: grade_order.index(x) if x in grade_order else 99)
        grade_achievement = grade_achievement.sort_values('등급_order')
        
        # 주요 지표 표시
        st.markdown("#### 📊 등급별 주요 지표")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            best_grade = grade_achievement.loc[grade_achievement['평균달성률(%)'].idxmax(), '등급'] if not grade_achievement.empty else 'N/A'
            best_rate = grade_achievement['평균달성률(%)'].max() if not grade_achievement.empty else 0
            st.metric("최고 달성률 등급", f"{best_grade}등급", f"{best_rate:.1f}%")
        
        with col2:
            worst_grade = grade_achievement.loc[grade_achievement['평균달성률(%)'].idxmin(), '등급'] if not grade_achievement.empty else 'N/A'
            worst_rate = grade_achievement['평균달성률(%)'].min() if not grade_achievement.empty else 0
            st.metric("최저 달성률 등급", f"{worst_grade}등급", f"{worst_rate:.1f}%")
        
        with col3:
            best_share_grade = grade_achievement.loc[grade_achievement['점유율(%)'].idxmax(), '등급'] if not grade_achievement.empty else 'N/A'
            best_share = grade_achievement['점유율(%)'].max() if not grade_achievement.empty else 0
            st.metric("최고 점유율 등급", f"{best_share_grade}등급", f"{best_share:.2f}%")
        
        with col4:
            total_grades = len(grade_achievement[grade_achievement['등급'] != '미분류'])
            st.metric("등급 분포", f"{total_grades}개 등급", f"{grade_achievement['총판수'].sum()}개 총판")
        
        st.markdown("---")
        
        # 차트
        col1, col2 = st.columns(2)
        
        with col1:
            # 등급별 평균 달성률
            fig1 = px.bar(
                grade_achievement,
                x='등급',
                y='평균달성률(%)',
                title="등급별 평균 달성률",
                text='평균달성률(%)',
                color='평균달성률(%)',
                color_continuous_scale='RdYlGn'
            )
            fig1.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig1.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="목표선")
            fig1.update_layout(height=400)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # 등급별 목표 vs 실적
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=grade_achievement['등급'],
                y=grade_achievement['목표합계'],
                name='목표',
                marker_color='lightblue',
                text=grade_achievement['목표합계'],
                texttemplate='%{text:,.0f}',
                textposition='outside'
            ))
            fig2.add_trace(go.Bar(
                x=grade_achievement['등급'],
                y=grade_achievement['실적합계'],
                name='실적',
                marker_color='orange',
                text=grade_achievement['실적합계'],
                texttemplate='%{text:,.0f}',
                textposition='outside'
            ))
            fig2.update_layout(
                title="등급별 목표 vs 실적",
                barmode='group',
                height=400
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        # 등급별 점유율 및 효율성
        st.markdown("---")
        st.markdown("#### 📈 등급별 시장 점유율 및 효율성")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig3 = px.bar(
                grade_achievement,
                x='등급',
                y='점유율(%)',
                title="등급별 학생수 대비 점유율",
                text='점유율(%)',
                color='점유율(%)',
                color_continuous_scale='Blues'
            )
            fig3.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
            fig3.update_layout(height=400)
            st.plotly_chart(fig3, use_container_width=True)
        
        with col2:
            fig4 = px.bar(
                grade_achievement,
                x='등급',
                y='총판당평균실적',
                title="등급별 총판당 평균 실적",
                text='총판당평균실적',
                color='총판당평균실적',
                color_continuous_scale='Greens'
            )
            fig4.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig4.update_layout(height=400)
            st.plotly_chart(fig4, use_container_width=True)
        
        # 상세 테이블
        st.markdown("---")
        st.markdown("#### 📋 등급별 상세 데이터")
        
        display_df = grade_achievement[[
            '등급', '총판수', '목표합계', '실적합계', '평균달성률(%)', 
            '시장규모', '점유율(%)', '거래학교수', '총판당평균실적'
        ]].copy()
        
        st.dataframe(
            display_df.style.format({
                '총판수': '{:,.0f}',
                '목표합계': '{:,.0f}',
                '실적합계': '{:,.0f}',
                '평균달성률(%)': '{:.1f}',
                '시장규모': '{:,.0f}',
                '점유율(%)': '{:.2f}',
                '거래학교수': '{:,.0f}',
                '총판당평균실적': '{:,.0f}'
            }).background_gradient(subset=['평균달성률(%)'], cmap='RdYlGn', vmin=0, vmax=150)
              .background_gradient(subset=['점유율(%)'], cmap='Blues'),
            use_container_width=True
        )
        
        # 등급별 총판 리스트
        st.markdown("---")
        st.markdown("#### 🔍 등급별 총판 상세")
        
        selected_grade = st.selectbox(
            "등급 선택",
            grade_achievement['등급'].tolist(),
            key="grade_detail_select"
        )
        
        if selected_grade:
            grade_data = achievement_df[achievement_df['등급'] == selected_grade].copy()
            grade_data = grade_data.sort_values('전체달성률(%)', ascending=False)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(f"{selected_grade}등급 총판 수", f"{len(grade_data)}개")
            with col2:
                avg_rate = grade_data['전체달성률(%)'].mean()
                st.metric(f"{selected_grade}등급 평균 달성률", f"{avg_rate:.1f}%")
            with col3:
                achieved = len(grade_data[grade_data['전체달성률(%)'] >= 100])
                st.metric(f"{selected_grade}등급 목표달성", f"{achieved}/{len(grade_data)}개")
            
            st.markdown(f"**{selected_grade}등급 총판 리스트**")
            st.dataframe(
                grade_data[[
                    '총판', '전체목표', '실적부수', '전체달성률(%)', '차이',
                    '시장규모', '점유율(%)', '거래학교수'
                ]].style.format({
                    '전체목표': '{:,.0f}',
                    '실적부수': '{:,.0f}',
                    '전체달성률(%)': '{:.1f}',
                    '차이': '{:,.0f}',
                    '시장규모': '{:,.0f}',
                    '점유율(%)': '{:.2f}',
                    '거래학교수': '{:,.0f}'
                }).background_gradient(subset=['전체달성률(%)'], cmap='RdYlGn', vmin=0, vmax=150),
                use_container_width=True,
                height=400
            )
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 등급별 평균 달성률
        fig = px.bar(
            grade_achievement,
            x='등급',
            y='평균달성률(%)',
            title="등급별 평균 달성률",
            text='평균달성률(%)',
            color='등급',
            color_discrete_map={'S': '#FFD700', 'A': '#C0C0C0', 'B': '#CD7F32', 'C': '#4CAF50', 'D': '#2196F3', '미분류': '#9E9E9E'}
        )
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="목표선")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # 등급별 목표/실적 비교
        fig2 = go.Figure()
        
        fig2.add_trace(go.Bar(
            name='목표',
            x=grade_achievement['등급'],
            y=grade_achievement['목표합계'],
            marker_color='lightblue'
        ))
        
        fig2.add_trace(go.Bar(
            name='실적',
            x=grade_achievement['등급'],
            y=grade_achievement['실적합계'],
            marker_color='green'
        ))
        
        fig2.update_layout(
            title="등급별 목표 vs 실적",
            barmode='group'
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    # 등급별 상세 테이블
    st.dataframe(
        grade_achievement[['등급', '총판수', '목표합계', '실적합계', '평균달성률(%)']].style.format({
            '총판수': '{:,.0f}',
            '목표합계': '{:,.0f}',
            '실적합계': '{:,.0f}',
            '평균달성률(%)': '{:.1f}'
        }),
        use_container_width=True
    )

with tab4:
    st.subheader("📋 총판별 상세 달성률 데이터")
    
    # 순위 추가 (이미 정렬되어 있음)
    achievement_df['순위'] = range(1, len(achievement_df) + 1)
    
    display_df = achievement_df[[
        '순위', '총판', '등급', '전체목표', '실적부수', '전체달성률(%)', 
        '차이', '시장규모', '점유율(%)', '거래학교수', '주문금액'
    ]].copy()
    
    st.dataframe(
        display_df,
        column_config={
            "순위": st.column_config.NumberColumn("순위", format="#%d"),
            "총판": "총판명",
            "등급": "등급",
            "전체목표": st.column_config.NumberColumn("목표 부수", format="%d부"),
            "실적부수": st.column_config.NumberColumn("실적 부수", format="%d부"),
            "전체달성률(%)": st.column_config.ProgressColumn(
                "달성률",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
            "차이": st.column_config.NumberColumn("차이 (실적-목표)", format="%d부"),
            "시장규모": st.column_config.NumberColumn("시장규모 (학생수)", format="%d명"),
            "점유율(%)": st.column_config.NumberColumn("학생수 대비 점유율", format="%.2f%%"),
            "거래학교수": st.column_config.NumberColumn("거래 학교", format="%d개교"),
            "주문금액": st.column_config.NumberColumn("주문 금액", format="₩%d"),
        },
        hide_index=True,
        use_container_width=True,
        height=600
    )
    
    # CSV 다운로드
    csv = display_df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 CSV 다운로드",
        data=csv,
        file_name="목표_대비_달성률.csv",
        mime="text/csv"
    )

with tab5:
    st.subheader("📉 목표 갭 분석")
    
    # 갭이 큰 순서대로 정렬
    gap_df = achievement_df.copy()
    gap_df['절대갭'] = abs(gap_df['차이'])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔼 초과 달성 TOP 10")
        over_achievement = gap_df[gap_df['차이'] > 0].sort_values('차이', ascending=False).head(10)
        
        if len(over_achievement) > 0:
            # 안전한 텍스트 포맷: 값에 따라 + 기호를 붙인 문자열을 만들어 사용
            over_achievement = over_achievement.copy()
            over_achievement['text_label'] = over_achievement['차이'].apply(lambda v: f"+{int(v):,}" if v > 0 else f"{int(v):,}")
            fig = px.bar(
                over_achievement,
                x='총판',
                y='차이',
                title="목표 초과 달성 TOP 10",
                text='text_label',
                color='차이',
                color_continuous_scale='Greens'
            )
            fig.update_traces(texttemplate='%{text}', textposition='outside')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("초과 달성 총판이 없습니다.")
    
    with col2:
        st.markdown("### 🔽 미달성 TOP 10")
        under_achievement = gap_df[gap_df['차이'] < 0].sort_values('차이').head(10)
        
        if len(under_achievement) > 0:
            under_achievement = under_achievement.copy()
            under_achievement['text_label'] = under_achievement['차이'].apply(lambda v: f"{int(v):,}")
            fig = px.bar(
                under_achievement,
                x='총판',
                y='차이',
                title="목표 미달성 TOP 10",
                text='text_label',
                color='차이',
                color_continuous_scale='Reds_r'
            )
            fig.update_traces(texttemplate='%{text}', textposition='outside')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("미달성 총판이 없습니다.")
    
    # 갭 분포
    st.markdown("---")
    st.subheader("📊 목표 갭 분포")
    
    fig_scatter = px.scatter(
        gap_df,
        x='전체목표',
        y='실적부수',
        size='절대갭',
        color='등급',
        hover_data=['총판', '전체달성률(%)'],
        title="목표 vs 실적 분포 (점 크기 = 갭)",
        labels={'전체목표': '목표 부수', '실적부수': '실적 부수'}
    )
    
    # 대각선 (목표=실적 기준선)
    max_val = max(gap_df['전체목표'].max(), gap_df['실적부수'].max())
    fig_scatter.add_trace(go.Scatter(
        x=[0, max_val],
        y=[0, max_val],
        mode='lines',
        line=dict(dash='dash', color='red'),
        name='목표선 (100%)',
        showlegend=True
    ))
    
    st.plotly_chart(fig_scatter, use_container_width=True)
