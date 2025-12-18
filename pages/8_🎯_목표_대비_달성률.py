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

order_df = st.session_state['order_df'].copy()
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

# 🚨 반드시 원본 주문 데이터에서 직접 필터링 (세션 order_df가 이미 필터됐을 수도 있으므로)
if 'order_df_original' in st.session_state:
    source_df = st.session_state['order_df_original'].copy()
else:
    # fallback: 현재 세션 order_df가 원본이라고 가정
    source_df = order_df.copy()

st.sidebar.success(f"✅ 원본 데이터 사용: {len(source_df):,}건")

school_code_col = '정보공시학교코드' if '정보공시학교코드' in source_df.columns else '학교코드'

# 목표과목 컬럼 탐색
target_col = None
for col in source_df.columns:
    if '목표과목' in str(col):
        target_col = col
        break

if target_col is None:
    st.error("❌ 목표과목 컬럼을 찾을 수 없습니다. CSV 파일에 '목표과목' 컬럼이 필요합니다.")
    st.stop()

# 2026년도 + 목표과목1/2 필터 적용
if '학년도' in source_df.columns:
    order_2026 = source_df[
        (source_df['학년도'] == 2026) & 
        (source_df[target_col].isin(['목표과목1', '목표과목2']))
    ].copy()
else:
    order_2026 = source_df[source_df[target_col].isin(['목표과목1', '목표과목2'])].copy()

# 디버깅: 필터링 결과 확인
st.sidebar.write(f"📦 원본 데이터: {len(source_df):,}건 ({int(source_df['부수'].sum()):,}부)")
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

# 목표와 실적 병합
target_map = target_summary.groupby('총판명(공식)').agg({
    '전체목표': 'sum',
    '목표1': 'sum',
    '목표2': 'sum'
}).reset_index()

# 안전한 실적 매핑: 목표 총판명(공식) 기준으로 필터된 주문(order_2026)에서 직접 실적 합계를 계산
# 1) distributor_df가 있으면 공식명 매핑 테이블 생성
# 2) order_2026에서 총판별 부수 합을 구해 공식명으로 매핑하여 실적 맵 생성
dist_map = {}
if not distributor_df.empty and '총판명(공식)' in distributor_df.columns:
    for _, r in distributor_df.iterrows():
        official = r.get('총판명(공식)')
        if pd.isna(official):
            continue
        # map any known name variants to official
        for col in ['총판명', '총판명1', '총판']:
            if col in distributor_df.columns and pd.notna(r.get(col)):
                dist_map[str(r.get(col)).strip()] = str(official).strip()

# Allow user-applied custom mappings stored in session to override dist_map
custom_map = st.session_state.get('dist_map_custom', {}) if isinstance(st.session_state.get('dist_map_custom', {}), dict) else {}
if custom_map:
    dist_map.update(custom_map)

# --- 미매핑 총판 보고 (디버그 및 매핑 보강용)
mapped_keys = set(dist_map.keys())
order_totals = order_2026.groupby('총판')['부수'].sum().reset_index()
order_totals['총판_clean'] = order_totals['총판'].astype(str).str.strip()
unmapped = order_totals[~order_totals['총판_clean'].isin(mapped_keys)]
if not unmapped.empty:
    unmapped = unmapped.sort_values('부수', ascending=False)
    st.sidebar.warning(f"⚠️ 매핑되지 않은 총판 발견: {len(unmapped)}개")
    st.sidebar.dataframe(unmapped[['총판','부수']].rename(columns={'부수':'필터된 부수'}), use_container_width=True)
    try:
        csv_unmapped = unmapped[['총판','부수']].to_csv(index=False, encoding='utf-8-sig')
        st.sidebar.download_button("📥 미매핑 총판 CSV 다운로드", data=csv_unmapped, file_name='unmapped_distributors.csv', mime='text/csv')
    except Exception:
        pass

    # 자동 매핑 제안 (difflib 기반 유사도)
    try:
        from difflib import SequenceMatcher

        official_names = target_map['총판명(공식)'].astype(str).unique().tolist() if '총판명(공식)' in target_map.columns else []
        suggestions = []
        for raw in unmapped['총판_clean'].unique():
            best = None
            best_score = 0.0
            for off in official_names:
                score = SequenceMatcher(None, str(raw), str(off)).ratio()
                if score > best_score:
                    best_score = score
                    best = off
            suggestions.append({'원본': raw, '추천_공식명': best or '', '유사도(%)': int(best_score*100)})

        sug_df = pd.DataFrame(suggestions).sort_values('유사도(%)', ascending=False)
        st.sidebar.markdown("**자동 매핑 제안 (유사도 기준)**")
        st.sidebar.dataframe(sug_df, use_container_width=True)

        # 사용자 선택으로 적용
        apply_opts = [f"{r['원본']} -> {r['추천_공식명']} ({r['유사도(%)']}%)" for _, r in sug_df.iterrows() if r['추천_공식명'] and r['유사도(%)'] >= 50]
        if apply_opts:
            selected = st.sidebar.multiselect('자동매핑 적용할 항목 선택 (유사도 ≥50%)', options=apply_opts)
            if st.sidebar.button('✅ 선택 항목 매핑 적용') and selected:
                # parse and save to session custom map
                to_apply = {}
                for s in selected:
                    raw, rest = s.split(' -> ', 1)
                    match = rest.rsplit(' (', 1)[0]
                    to_apply[raw.strip()] = match.strip()
                existing = st.session_state.get('dist_map_custom', {})
                existing.update(to_apply)
                st.session_state['dist_map_custom'] = existing
                st.experimental_rerun()
    except Exception:
        pass

# --- 이제 사용자 매핑이 적용된 dist_map 기준으로 실적 합계 계산
order_actual = order_2026.groupby('총판')['부수'].sum().reset_index()
order_actual['총판_key'] = order_actual['총판'].map(lambda x: dist_map.get(str(x).strip(), str(x).strip()))
actual_by_official = order_actual.groupby('총판_key')['부수'].sum().to_dict()

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
    keys_to_clear = ['order_df', 'order_df_original', 'target_df', 'distributor_df']
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]
    st.experimental_rerun()

# --- 총판 매핑 상세 디버그: 어떤 원본 이름들이 특정 공식명으로 합쳐졌는지 확인
reverse_map = {}
for raw_name, official in dist_map.items():
    reverse_map.setdefault(official, []).append(raw_name)

# 실제 실적 상위 공식명 확인용 데이터프레임
actual_official_df = pd.DataFrame([{'총판명(공식)': k, '실적부수': v} for k, v in actual_by_official.items()])
if not actual_official_df.empty:
    actual_official_df = actual_official_df.sort_values('실적부수', ascending=False)
    top_officials = actual_official_df.head(10)['총판명(공식)'].tolist()

    # 기본 선택은 '통영)이문당'이 있으면 선택
    default_select = '통영)이문당' if '통영)이문당' in actual_official_df['총판명(공식)'].values else (top_officials[0] if top_officials else None)

    if default_select:
        sel = st.sidebar.selectbox('🔎 실적 상위 공식명 선택(매핑 상세)', options=top_officials, index=top_officials.index(default_select) if default_select in top_officials else 0)
    else:
        sel = None

    if sel:
        contributors = reverse_map.get(sel, [])
        if not contributors:
            # contributors가 없으면 sel 자체를 원본 이름으로 간주
            contributors = [sel]

        contrib_rows = order_2026[order_2026['총판'].astype(str).str.strip().isin(contributors)].copy()
        contrib_sum = int(contrib_rows['부수'].sum()) if not contrib_rows.empty else 0

        st.sidebar.markdown(f"**선택 공식명:** {sel} — 합계 실적: {contrib_sum:,}부")
        if not contrib_rows.empty:
            st.sidebar.dataframe(contrib_rows.groupby('총판')['부수'].sum().reset_index().rename(columns={'부수':'필터된 부수'}), use_container_width=True)
        else:
            st.sidebar.info("해당 공식명에 매핑된 원본 총판이 없습니다.")

        # 통영)이문당 — 전체 2026(주관주문 포함) vs 필터(목표과목1/2) 비교
        try:
            if '학년도' in source_df.columns:
                order_all_2026 = source_df[source_df['학년도'] == 2026].copy()
            else:
                order_all_2026 = source_df.copy()

            # 원본 2026 전체에서 contributors가 차지하는 합
            all_contrib_rows = order_all_2026[order_all_2026['총판'].astype(str).str.strip().isin(contributors)]
            all_contrib_sum = int(all_contrib_rows['부수'].sum()) if not all_contrib_rows.empty else 0

            st.sidebar.markdown(f"**비교(전체 2026 vs 목표과목 필터)**")
            st.sidebar.write(f"- 필터(목표과목1/2) 합계: {contrib_sum:,}부")
            st.sidebar.write(f"- 전체 2026 주문 합계: {all_contrib_sum:,}부")

            if all_contrib_sum != contrib_sum:
                st.sidebar.info("전체 2026 합계가 필터 합계와 다릅니다 — 목표과목 외 주문이 포함되어 있습니다.")
        except Exception:
            pass

    # 상위 공식명 리스트(요약)도 노출
    st.sidebar.markdown("**실적 상위 공식명(요약)**")
    st.sidebar.dataframe(actual_official_df.head(10).reset_index(drop=True), use_container_width=True)

# Build achievement_df from target_map and map 실적부수 from actual_by_official
achievement_df = target_map.copy()
achievement_df['실적부수'] = achievement_df['총판명(공식)'].map(lambda x: int(actual_by_official.get(str(x).strip(), 0)))

# Fill numeric NaNs for 목표 컬럼
for col in ['전체목표', '목표1', '목표2', '실적부수']:
    if col in achievement_df.columns:
        achievement_df[col] = achievement_df[col].fillna(0)

# 총판 통일
achievement_df['총판'] = achievement_df['총판명(공식)']

# --- 디버그: 통영)이문당 관련 매핑/실적 출처 확인
debug_official = '통영)이문당'
if debug_official in achievement_df['총판'].values:
    official_row = achievement_df[achievement_df['총판'] == debug_official].iloc[0]
    sidebar_debug = []
    sidebar_debug.append({'항목':'achievement_df 실적부수', '값': int(official_row['실적부수'])})
    sidebar_debug.append({'항목':'achievement_df 전체목표', '값': int(official_row['전체목표'])})
    # contributors from order_2026 grouped by raw 총판
    contribs = order_2026[order_2026['총판'].astype(str).str.contains('이문당', na=False)].groupby('총판')['부수'].sum().reset_index()
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
col1, col2, col3, col4 = st.columns(4)

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
    
    # 등급별 집계
    grade_achievement = achievement_df.groupby('등급').agg({
        '전체목표': 'sum',
        '실적부수': 'sum',
        '총판': 'count'
    }).reset_index()
    grade_achievement.columns = ['등급', '목표합계', '실적합계', '총판수']
    grade_achievement['평균달성률(%)'] = (grade_achievement['실적합계'] / grade_achievement['목표합계'] * 100).fillna(0)
    
    # 등급 순서 정렬
    grade_order = ['S', 'A', 'B', 'C', 'D', 'E', 'G', '미분류']
    grade_achievement['등급_order'] = grade_achievement['등급'].apply(lambda x: grade_order.index(x) if x in grade_order else 99)
    grade_achievement = grade_achievement.sort_values('등급_order')
    
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
        '차이', '거래학교수', '주문금액'
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
