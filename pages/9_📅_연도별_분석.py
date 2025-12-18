import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="연도별 분석", page_icon="📅", layout="wide")

# 페이지 가이드
st.markdown("""
    <style>
        .page-guide { 
            background-color: #e8f4f8; 
            padding: 1rem; 
            border-radius: 0.5rem; 
            margin-bottom: 1.5rem; 
            color: #000000;
        }
        .page-guide h3 { color: #0066cc; margin-bottom: 0.5rem; }
        .page-guide p { margin: 0.3rem 0; color: #000000; }
    </style>
    <div class="page-guide">
        <h3>📅 연도별 분석 (2025 vs 2026)</h3>
        <p>• 2025년 대비 2026년 주문 변화를 다각도로 분석합니다</p>
        <p>• 학교 이탈/신규, 과목별 증감, 지역별 증감, 총판별 성과 변화를 확인하세요</p>
    </div>
""", unsafe_allow_html=True)

st.title("📅 연도별 분석 (2025 vs 2026)")

# 데이터 로드
order_df = st.session_state.get('order_df')
if 'order_df_original' in st.session_state:
    order_df_full = st.session_state['order_df_original'].copy()
    st.sidebar.success("✅ 원본 데이터 사용")
else:
    order_df_full = order_df.copy() if order_df is not None else None
    st.sidebar.info("ℹ️ 필터된 데이터 사용")

distributor_df = st.session_state.get('distributor_df')
product_df = st.session_state.get('product_df')

if order_df_full is None or order_df_full.empty:
    st.error("주문 데이터가 없습니다. 먼저 메인 페이지에서 데이터를 로드하세요.")
    st.stop()

# 필수 컬럼 체크
required_cols = ['학년도', '학교코드', '학교명', '제품', '부수']
missing = [c for c in required_cols if c not in order_df_full.columns]
if missing:
    st.error(f"필수 컬럼이 없습니다: {missing}")
    st.stop()

# 학년도 필터링
df_2025 = order_df_full[order_df_full['학년도'] == 2025].copy()
df_2026 = order_df_full[order_df_full['학년도'] == 2026].copy()

if df_2025.empty and df_2026.empty:
    st.warning("2025년 또는 2026년 데이터가 없습니다.")
    st.stop()

# 연도별 KPI
st.markdown("## 📊 연도별 주요 지표")
col1, col2, col3, col4, col5 = st.columns(5)

total_2025 = int(df_2025['부수'].sum()) if not df_2025.empty else 0
total_2026 = int(df_2026['부수'].sum()) if not df_2026.empty else 0
schools_2025 = df_2025['학교코드'].nunique() if not df_2025.empty else 0
schools_2026 = df_2026['학교코드'].nunique() if not df_2026.empty else 0

delta_volume = total_2026 - total_2025
delta_schools = schools_2026 - schools_2025
delta_pct = (delta_volume / total_2025 * 100) if total_2025 > 0 else 0

with col1:
    st.metric("2025년 총 부수", f"{total_2025:,}부")
with col2:
    st.metric("2026년 총 부수", f"{total_2026:,}부", delta=f"{delta_volume:+,}부")
with col3:
    st.metric("증감률", f"{delta_pct:+.1f}%")
with col4:
    st.metric("2025년 거래 학교", f"{schools_2025:,}개")
with col5:
    st.metric("2026년 거래 학교", f"{schools_2026:,}개", delta=f"{delta_schools:+,}개")

st.markdown("---")

# 탭 구성
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏫 학교 이탈/신규",
    "📚 과목별 증감",
    "🗺️ 지역별 증감",
    "🏢 총판별 증감",
    "📈 종합 대시보드"
])

# --------------------- TAB 1: 학교 이탈/신규 ---------------------
with tab1:
    st.markdown("### 🏫 학교 주문 변화 분석")
    
    schools_2025_set = set(df_2025['학교코드'].unique()) if not df_2025.empty else set()
    schools_2026_set = set(df_2026['학교코드'].unique()) if not df_2026.empty else set()
    
    # 이탈 학교 (2025에는 있었으나 2026에는 없음)
    churned_schools = schools_2025_set - schools_2026_set
    # 신규 학교 (2026에 새로 나타남)
    new_schools = schools_2026_set - schools_2025_set
    # 지속 학교
    retained_schools = schools_2025_set & schools_2026_set
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("이탈 학교", f"{len(churned_schools):,}개", help="2025년에만 주문한 학교")
    with col_b:
        st.metric("신규 학교", f"{len(new_schools):,}개", help="2026년에 처음 주문한 학교")
    with col_c:
        st.metric("지속 학교", f"{len(retained_schools):,}개", help="2025/2026 모두 주문")
    
    # 과목별 이탈/신규 분석
    if '과목' in df_2025.columns and '과목' in df_2026.columns:
        st.markdown("#### 📚 과목별 이탈/신규 학교 수")
        
        # 이탈 학교 과목별 집계
        churned_df = df_2025[df_2025['학교코드'].isin(churned_schools)].copy()
        churned_by_subject = churned_df.groupby('과목').agg({
            '학교코드': 'nunique',
            '부수': 'sum'
        }).reset_index()
        churned_by_subject.columns = ['과목', '이탈학교수', '이탈부수']
        churned_by_subject = churned_by_subject.sort_values('이탈부수', ascending=False)
        
        # 신규 학교 과목별 집계
        new_df = df_2026[df_2026['학교코드'].isin(new_schools)].copy()
        new_by_subject = new_df.groupby('과목').agg({
            '학교코드': 'nunique',
            '부수': 'sum'
        }).reset_index()
        new_by_subject.columns = ['과목', '신규학교수', '신규부수']
        new_by_subject = new_by_subject.sort_values('신규부수', ascending=False)
        
        col_x, col_y = st.columns(2)
        with col_x:
            st.markdown("**이탈 학교 (과목별)**")
            if not churned_by_subject.empty:
                st.dataframe(churned_by_subject, use_container_width=True, height=300)
            else:
                st.info("이탈 학교 없음")
        with col_y:
            st.markdown("**신규 학교 (과목별)**")
            if not new_by_subject.empty:
                st.dataframe(new_by_subject, use_container_width=True, height=300)
            else:
                st.info("신규 학교 없음")
    
    # 이탈/신규 학교 상세 리스트
    st.markdown("#### 📋 이탈/신규 학교 상세")
    detail_option = st.radio("보기 옵션", ['이탈 학교 리스트', '신규 학교 리스트'], horizontal=True)
    
    if detail_option == '이탈 학교 리스트':
        if churned_schools:
            churned_detail = df_2025[df_2025['학교코드'].isin(churned_schools)].groupby(['학교코드','학교명']).agg({
                '부수': 'sum',
                '제품': 'count'
            }).reset_index()
            churned_detail.columns = ['학교코드', '학교명', '2025년 부수', '주문 건수']
            churned_detail = churned_detail.sort_values('2025년 부수', ascending=False)
            st.dataframe(churned_detail, use_container_width=True)
            
            # 다운로드
            csv = churned_detail.to_csv(index=False, encoding='utf-8-sig')
            st.download_button("📥 이탈 학교 CSV 다운로드", data=csv, file_name='churned_schools.csv', mime='text/csv')
        else:
            st.info("이탈 학교 없음")
    else:
        if new_schools:
            new_detail = df_2026[df_2026['학교코드'].isin(new_schools)].groupby(['학교코드','학교명']).agg({
                '부수': 'sum',
                '제품': 'count'
            }).reset_index()
            new_detail.columns = ['학교코드', '학교명', '2026년 부수', '주문 건수']
            new_detail = new_detail.sort_values('2026년 부수', ascending=False)
            st.dataframe(new_detail, use_container_width=True)
            
            # 다운로드
            csv = new_detail.to_csv(index=False, encoding='utf-8-sig')
            st.download_button("📥 신규 학교 CSV 다운로드", data=csv, file_name='new_schools.csv', mime='text/csv')
        else:
            st.info("신규 학교 없음")

# --------------------- TAB 2: 과목별 증감 ---------------------
with tab2:
    st.markdown("### 📚 과목별 주문 증감 분석")
    
    if '과목' not in df_2025.columns and '과목' not in df_2026.columns:
        st.warning("과목 정보가 없습니다.")
    else:
        # 2025 과목별 합계
        subj_2025 = df_2025.groupby('과목')['부수'].sum().reset_index()
        subj_2025.columns = ['과목', '2025년']
        
        # 2026 과목별 합계
        subj_2026 = df_2026.groupby('과목')['부수'].sum().reset_index()
        subj_2026.columns = ['과목', '2026년']
        
        # 병합
        subj_comp = pd.merge(subj_2025, subj_2026, on='과목', how='outer').fillna(0)
        subj_comp['증감'] = subj_comp['2026년'] - subj_comp['2025년']
        subj_comp['증감률(%)'] = subj_comp.apply(
            lambda r: (r['증감'] / r['2025년'] * 100) if r['2025년'] > 0 else 0, axis=1
        )
        subj_comp = subj_comp.sort_values('증감', ascending=False)
        
        # 숫자 포맷팅
        subj_comp['2025년_fmt'] = subj_comp['2025년'].apply(lambda x: f"{int(x):,}")
        subj_comp['2026년_fmt'] = subj_comp['2026년'].apply(lambda x: f"{int(x):,}")
        subj_comp['증감_fmt'] = subj_comp['증감'].apply(lambda x: f"{int(x):+,}")
        subj_comp['증감률_fmt'] = subj_comp['증감률(%)'].apply(lambda x: f"{x:+.1f}%")
        
        # 표시용 데이터프레임
        display_df = subj_comp[['과목', '2025년_fmt', '2026년_fmt', '증감_fmt', '증감률_fmt']].copy()
        display_df.columns = ['과목', '2025년', '2026년', '증감', '증감률(%)']
        
        st.dataframe(display_df, use_container_width=True, height=400)
        
        # 차트
        st.markdown("#### 📊 과목별 증감 시각화")
        chart_df = subj_comp[['과목', '2025년', '2026년']].melt(id_vars='과목', var_name='연도', value_name='부수')
        chart_df['부수'] = chart_df['부수'].astype(int)
        
        fig = px.bar(chart_df, x='과목', y='부수', color='연도', barmode='group',
                     title='과목별 연도별 부수 비교',
                     color_discrete_map={'2025년':'#636EFA', '2026년':'#EF553B'})
        fig.update_layout(xaxis_tickangle=-45, height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        # 증감 차트
        fig2 = px.bar(subj_comp.head(20), x='과목', y='증감',
                      title='과목별 증감 (상위 20개)',
                      color='증감',
                      color_continuous_scale='RdYlGn')
        fig2.update_layout(xaxis_tickangle=-45, height=500)
        st.plotly_chart(fig2, use_container_width=True)
        
        # CSV 다운로드
        csv = subj_comp[['과목', '2025년', '2026년', '증감', '증감률(%)']].to_csv(index=False, encoding='utf-8-sig')
        st.download_button("📥 과목별 증감 CSV 다운로드", data=csv, file_name='subject_yoy.csv', mime='text/csv')

# --------------------- TAB 3: 지역별 증감 ---------------------
with tab3:
    st.markdown("### 🗺️ 지역별 주문 증감 분석")
    
    # 지역 정보는 학교 데이터 또는 총판 데이터에서 추출
    # 여기서는 '지역' 또는 '시도' 컬럼이 있다고 가정
    region_col = None
    for col in ['지역', '시도', '시·도', '광역시도']:
        if col in df_2025.columns or col in df_2026.columns:
            region_col = col
            break
    
    if not region_col:
        st.warning("지역 정보 컬럼(지역, 시도 등)이 없습니다. 지역별 분석을 건너뜁니다.")
    else:
        # 2025 지역별 합계
        reg_2025 = df_2025.groupby(region_col)['부수'].sum().reset_index()
        reg_2025.columns = ['지역', '2025년']
        
        # 2026 지역별 합계
        reg_2026 = df_2026.groupby(region_col)['부수'].sum().reset_index()
        reg_2026.columns = ['지역', '2026년']
        
        # 병합
        reg_comp = pd.merge(reg_2025, reg_2026, on='지역', how='outer').fillna(0)
        reg_comp['증감'] = reg_comp['2026년'] - reg_comp['2025년']
        reg_comp['증감률(%)'] = reg_comp.apply(
            lambda r: (r['증감'] / r['2025년'] * 100) if r['2025년'] > 0 else 0, axis=1
        )
        reg_comp = reg_comp.sort_values('증감', ascending=False)
        
        # 포맷팅
        reg_comp['2025년_fmt'] = reg_comp['2025년'].apply(lambda x: f"{int(x):,}")
        reg_comp['2026년_fmt'] = reg_comp['2026년'].apply(lambda x: f"{int(x):,}")
        reg_comp['증감_fmt'] = reg_comp['증감'].apply(lambda x: f"{int(x):+,}")
        reg_comp['증감률_fmt'] = reg_comp['증감률(%)'].apply(lambda x: f"{x:+.1f}%")
        
        display_df = reg_comp[['지역', '2025년_fmt', '2026년_fmt', '증감_fmt', '증감률_fmt']].copy()
        display_df.columns = ['지역', '2025년', '2026년', '증감', '증감률(%)']
        
        st.dataframe(display_df, use_container_width=True, height=400)
        
        # 차트
        st.markdown("#### 📊 지역별 증감 시각화")
        chart_df = reg_comp[['지역', '2025년', '2026년']].melt(id_vars='지역', var_name='연도', value_name='부수')
        chart_df['부수'] = chart_df['부수'].astype(int)
        
        fig = px.bar(chart_df, x='지역', y='부수', color='연도', barmode='group',
                     title='지역별 연도별 부수 비교',
                     color_discrete_map={'2025년':'#636EFA', '2026년':'#EF553B'})
        fig.update_layout(xaxis_tickangle=-45, height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        # 증감 차트
        fig2 = px.bar(reg_comp, x='지역', y='증감',
                      title='지역별 증감',
                      color='증감',
                      color_continuous_scale='RdYlGn')
        fig2.update_layout(xaxis_tickangle=-45, height=500)
        st.plotly_chart(fig2, use_container_width=True)
        
        # CSV 다운로드
        csv = reg_comp[['지역', '2025년', '2026년', '증감', '증감률(%)']].to_csv(index=False, encoding='utf-8-sig')
        st.download_button("📥 지역별 증감 CSV 다운로드", data=csv, file_name='region_yoy.csv', mime='text/csv')

# --------------------- TAB 4: 총판별 증감 ---------------------
with tab4:
    st.markdown("### 🏢 총판별 주문 증감 분석")
    
    if '총판' not in df_2025.columns and '총판' not in df_2026.columns:
        st.warning("총판 정보가 없습니다.")
    else:
        # 총판 매핑 (distributor_df 활용)
        dist_map = {}
        if distributor_df is not None and not distributor_df.empty and '총판명(공식)' in distributor_df.columns:
            for _, r in distributor_df.iterrows():
                official = r.get('총판명(공식)')
                if pd.isna(official):
                    continue
                for col in ['총판명', '총판명1', '총판']:
                    if col in distributor_df.columns and pd.notna(r.get(col)):
                        dist_map[str(r.get(col)).strip()] = str(official).strip()
        
        # 2025 총판별 합계
        df_2025_mapped = df_2025.copy()
        df_2025_mapped['총판_공식'] = df_2025_mapped['총판'].astype(str).str.strip().map(lambda x: dist_map.get(x, x))
        dist_2025 = df_2025_mapped.groupby('총판_공식')['부수'].sum().reset_index()
        dist_2025.columns = ['총판', '2025년']
        
        # 2026 총판별 합계
        df_2026_mapped = df_2026.copy()
        df_2026_mapped['총판_공식'] = df_2026_mapped['총판'].astype(str).str.strip().map(lambda x: dist_map.get(x, x))
        dist_2026 = df_2026_mapped.groupby('총판_공식')['부수'].sum().reset_index()
        dist_2026.columns = ['총판', '2026년']
        
        # 병합
        dist_comp = pd.merge(dist_2025, dist_2026, on='총판', how='outer').fillna(0)
        dist_comp['증감'] = dist_comp['2026년'] - dist_comp['2025년']
        dist_comp['증감률(%)'] = dist_comp.apply(
            lambda r: (r['증감'] / r['2025년'] * 100) if r['2025년'] > 0 else 0, axis=1
        )
        dist_comp = dist_comp.sort_values('증감', ascending=False)
        
        # 포맷팅
        dist_comp['2025년_fmt'] = dist_comp['2025년'].apply(lambda x: f"{int(x):,}")
        dist_comp['2026년_fmt'] = dist_comp['2026년'].apply(lambda x: f"{int(x):,}")
        dist_comp['증감_fmt'] = dist_comp['증감'].apply(lambda x: f"{int(x):+,}")
        dist_comp['증감률_fmt'] = dist_comp['증감률(%)'].apply(lambda x: f"{x:+.1f}%")
        
        display_df = dist_comp[['총판', '2025년_fmt', '2026년_fmt', '증감_fmt', '증감률_fmt']].copy()
        display_df.columns = ['총판', '2025년', '2026년', '증감', '증감률(%)']
        
        st.dataframe(display_df, use_container_width=True, height=400)
        
        # 차트 - 상위/하위 각 15개
        st.markdown("#### 📊 총판별 증감 시각화")
        
        col_top, col_bot = st.columns(2)
        with col_top:
            top15 = dist_comp.head(15)
            fig_top = px.bar(top15, x='총판', y='증감',
                             title='증가 상위 15개 총판',
                             color='증감',
                             color_continuous_scale='Greens')
            fig_top.update_layout(xaxis_tickangle=-45, height=400)
            st.plotly_chart(fig_top, use_container_width=True)
        
        with col_bot:
            bot15 = dist_comp.tail(15).sort_values('증감')
            fig_bot = px.bar(bot15, x='총판', y='증감',
                             title='감소 하위 15개 총판',
                             color='증감',
                             color_continuous_scale='Reds')
            fig_bot.update_layout(xaxis_tickangle=-45, height=400)
            st.plotly_chart(fig_bot, use_container_width=True)
        
        # CSV 다운로드
        csv = dist_comp[['총판', '2025년', '2026년', '증감', '증감률(%)']].to_csv(index=False, encoding='utf-8-sig')
        st.download_button("📥 총판별 증감 CSV 다운로드", data=csv, file_name='distributor_yoy.csv', mime='text/csv')

# --------------------- TAB 5: 종합 대시보드 ---------------------
with tab5:
    st.markdown("### 📈 종합 대시보드")
    
    # 전체 트렌드 라인 차트
    st.markdown("#### 📉 연도별 총 부수 추이")
    
    trend_data = pd.DataFrame({
        '연도': [2025, 2026],
        '총 부수': [total_2025, total_2026]
    })
    
    fig_trend = px.line(trend_data, x='연도', y='총 부수', markers=True,
                        title='2025 vs 2026 총 부수 추이',
                        text='총 부수')
    fig_trend.update_traces(texttemplate='%{text:,}부', textposition='top center')
    fig_trend.update_layout(height=400)
    st.plotly_chart(fig_trend, use_container_width=True)
    
    # 주요 인사이트 요약
    st.markdown("#### 💡 주요 인사이트")
    
    insights = []
    
    # 1. 전체 증감
    if delta_volume > 0:
        insights.append(f"✅ 2026년 총 부수는 2025년 대비 **{delta_volume:,}부 증가** ({delta_pct:+.1f}%)")
    elif delta_volume < 0:
        insights.append(f"⚠️ 2026년 총 부수는 2025년 대비 **{abs(delta_volume):,}부 감소** ({delta_pct:.1f}%)")
    else:
        insights.append(f"➡️ 2026년 총 부수는 2025년과 동일합니다")
    
    # 2. 학교 수 변화
    if delta_schools > 0:
        insights.append(f"✅ 거래 학교 수가 **{delta_schools:,}개 증가**하여 신규 고객 확보에 성공했습니다")
    elif delta_schools < 0:
        insights.append(f"⚠️ 거래 학교 수가 **{abs(delta_schools):,}개 감소**했습니다 — 이탈 학교 관리가 필요합니다")
    
    # 3. 이탈/신규 학교
    churn_rate = len(churned_schools) / len(schools_2025_set) * 100 if schools_2025_set else 0
    new_rate = len(new_schools) / len(schools_2026_set) * 100 if schools_2026_set else 0
    insights.append(f"📊 이탈률: **{churn_rate:.1f}%** ({len(churned_schools):,}개) / 신규율: **{new_rate:.1f}%** ({len(new_schools):,}개)")
    
    # 4. 과목별 최대 증가/감소
    if '과목' in df_2025.columns and '과목' in df_2026.columns:
        max_increase = subj_comp.iloc[0] if not subj_comp.empty else None
        max_decrease = subj_comp.iloc[-1] if not subj_comp.empty else None
        
        if max_increase is not None and max_increase['증감'] > 0:
            insights.append(f"📚 최대 증가 과목: **{max_increase['과목']}** (+{int(max_increase['증감']):,}부, {max_increase['증감률(%)']:+.1f}%)")
        
        if max_decrease is not None and max_decrease['증감'] < 0:
            insights.append(f"📚 최대 감소 과목: **{max_decrease['과목']}** ({int(max_decrease['증감']):,}부, {max_decrease['증감률(%)']:.1f}%)")
    
    # 5. 총판별 최대 증가/감소
    if '총판' in df_2025.columns and '총판' in df_2026.columns:
        max_dist_inc = dist_comp.iloc[0] if not dist_comp.empty else None
        max_dist_dec = dist_comp.iloc[-1] if not dist_comp.empty else None
        
        if max_dist_inc is not None and max_dist_inc['증감'] > 0:
            insights.append(f"🏢 최대 증가 총판: **{max_dist_inc['총판']}** (+{int(max_dist_inc['증감']):,}부, {max_dist_inc['증감률(%)']:+.1f}%)")
        
        if max_dist_dec is not None and max_dist_dec['증감'] < 0:
            insights.append(f"🏢 최대 감소 총판: **{max_dist_dec['총판']}** ({int(max_dist_dec['증감']):,}부, {max_dist_dec['증감률(%)']:.1f}%)")
    
    for insight in insights:
        st.markdown(f"- {insight}")
    
    # 종합 데이터 다운로드
    st.markdown("#### 📥 종합 데이터 다운로드")
    
    summary = {
        '구분': ['총 부수', '거래 학교 수', '이탈 학교', '신규 학교', '지속 학교'],
        '2025년': [total_2025, schools_2025, len(churned_schools), 0, len(retained_schools)],
        '2026년': [total_2026, schools_2026, 0, len(new_schools), len(retained_schools)],
        '증감': [delta_volume, delta_schools, -len(churned_schools), len(new_schools), 0]
    }
    summary_df = pd.DataFrame(summary)
    
    csv_summary = summary_df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button("📥 종합 요약 CSV 다운로드", data=csv_summary, file_name='year_summary.csv', mime='text/csv')

st.markdown("---")
st.caption("📅 연도별 분석 페이지 | 2025 vs 2026 비교 분석")
