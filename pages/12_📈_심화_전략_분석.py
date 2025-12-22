import streamlit as st
from utils.style import apply_custom_style
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from typing import cast

st.set_page_config(page_title="심화 전략 분석", page_icon="📈", layout="wide")
apply_custom_style()

# Get data
if 'order_df' not in st.session_state or 'total_df' not in st.session_state:
    st.error("데이터를 불러올 수 없습니다. 메인 페이지로 돌아가주세요.")
    st.stop()

order_df = st.session_state.get('order_df', pd.DataFrame()).copy()
total_df = st.session_state.get('total_df', pd.DataFrame()).copy()
target_df = st.session_state.get('target_df', pd.DataFrame()).copy()

st.title("📈 심화 전략 분석 (Advanced Analytics)")
st.markdown("---")

# 데이터 전처리 (연도별 분리)
if '학년도' in order_df.columns:
    df_2025 = order_df[order_df['학년도'].astype(str) == '2025'].copy()
    df_2026 = order_df[order_df['학년도'].astype(str) == '2026'].copy()
    # 수치형 보장: 부수/금액 컬럼이 문자열일 수 있으므로 변환
    for df in (df_2025, df_2026):
        if '부수' in df.columns:
            df['부수'] = pd.to_numeric(df['부수'], errors='coerce').fillna(0)
        if '금액' in df.columns:
            df['금액'] = pd.to_numeric(df['금액'], errors='coerce').fillna(0)
else:
    st.error("'학년도' 컬럼이 없어 시계열 분석을 수행할 수 없습니다.")
    st.stop()

# 탭 구성
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 예측 및 목표 관리", 
    "📉 이탈 분석 (Churn)", 
    "📊 효율성 매트릭스", 
    "🔗 연계 판매 (Cross-sell)", 
    "🤖 AI 인사이트"
])

# 1. 예측 및 목표 관리
with tab1:
    st.header("🎯 목표 대비 달성률 & 예측")
    
    # KPI Gauge Chart
    # 목표 데이터 처리
    if not target_df.empty:
        # 목표 부수 합계 계산 (목표과목1 + 목표과목2)
        def parse_number(x):
            if pd.isna(x): return 0
            if isinstance(x, (int, float)): return x
            return float(str(x).replace(',', '').strip())

        target_cols = [c for c in target_df.columns if '부수' in c]
        total_target = 0
        for col in target_cols:
            total_target += target_df[col].apply(parse_number).sum()
        
        # 2026년 실적 (목표는 보통 미래/현재 기준이므로 2026년 데이터와 비교 가정)
        # 만약 2026 데이터가 적다면 2025와 비교할 수도 있음. 여기서는 2026년 목표라고 가정.
        current_performance = df_2026['부수'].sum()
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("🏆 2026 목표 달성률")
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = current_performance,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "전체 목표 달성률 (부수)"},
                delta = {'reference': total_target},
                gauge = {
                    'axis': {'range': [None, total_target * 1.2]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, total_target * 0.5], 'color': "lightgray"},
                        {'range': [total_target * 0.5, total_target * 0.8], 'color': "gray"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': total_target
                    }
                }
            ))
            st.plotly_chart(fig_gauge, use_container_width=True)
            
            st.metric("목표 부수", f"{total_target:,.0f}부")
            st.metric("현재 달성", f"{current_performance:,.0f}부")
            if total_target > 0:
                achievement_rate = (float(current_performance) / float(total_target)) * 100
                st.metric("달성률", f"{achievement_rate:.1f}%")

        with col2:
            st.subheader("📈 시계열 예측 (Forecasting)")
            # 2025, 2026 데이터만으로는 복잡한 예측이 어려우므로 단순 추세선 표시
            trend_data = pd.DataFrame({
                'Year': ['2025', '2026'],
                'Orders': [df_2025['부수'].sum(), df_2026['부수'].sum()]
            })
            # Ensure numeric and safe ops
            trend_data['Orders'] = pd.to_numeric(trend_data['Orders'], errors='coerce').fillna(0).astype(float)
            # 2027 예측 (단순 선형)
            orders_2025 = cast(float, trend_data.loc[0, 'Orders'])
            orders_2026 = cast(float, trend_data.loc[1, 'Orders'])
            base0 = orders_2025 if orders_2025 != 0 else 1.0
            growth_rate = (orders_2026 - orders_2025) / base0
            predicted_2027 = orders_2026 * (1.0 + cast(float, growth_rate))
            trend_data.loc[2] = ['2027 (예측)', predicted_2027]
            
            fig_trend = px.line(
                trend_data, 
                x='Year', 
                y='Orders', 
                markers=True,
                title="연도별 주문 추이 및 2027 예측 (단순 성장률 기반)",
                text='Orders'
            )
            fig_trend.update_traces(texttemplate='%{text:,.0f}', textposition='top center')
            fig_trend.add_annotation(
                x='2027 (예측)', 
                y=predicted_2027,
                text="예상 수주",
                showarrow=True,
                arrowhead=1
            )
            st.plotly_chart(fig_trend, use_container_width=True)
            st.info("💡 2025-2026 성장률을 기반으로 한 단순 예측입니다. 실제 시장 상황에 따라 달라질 수 있습니다.")

    else:
        st.warning("목표 데이터(target_df)가 없어 KPI를 표시할 수 없습니다.")

# 2. 이탈 분석
with tab2:
    st.header("📉 이탈 학교 분석 (Churn Analysis)")
    st.markdown("2025년에는 주문했으나, **2026년에는 주문이 없는 학교**를 식별합니다.")
    
    school_col = '정보공시학교코드' if '정보공시학교코드' in order_df.columns else '학교코드'
    
    schools_2025 = set(df_2025[school_col].unique())
    schools_2026 = set(df_2026[school_col].unique())
    
    churned_schools = schools_2025 - schools_2026
    
    if churned_schools:
        churn_df = df_2025[df_2025[school_col].isin(churned_schools)].copy()
        
        # 학교별 요약
        churn_summary = churn_df.groupby([school_col, '학교명', '총판', '본사담당자(2025.09)']).agg({
            '부수': 'sum',
            '금액': 'sum',
            '과목명': lambda x: ', '.join(x.unique())
        }).reset_index()
        
        churn_summary = churn_summary.sort_values('부수', ascending=False)
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.metric("이탈 학교 수", f"{len(churned_schools):,}개")
            churn_amt_sum = pd.to_numeric(churn_summary['금액'].sum(), errors='coerce')
            churn_amt_sum = float(churn_amt_sum) if not pd.isna(churn_amt_sum) else 0.0
            st.metric("이탈 예상 금액", f"{churn_amt_sum:,.0f}원")
            
            # 총판별 이탈
            churn_by_dist = churn_summary['총판'].value_counts().head(10)
            st.subheader("🚨 총판별 이탈 학교 수 (Top 10)")
            st.dataframe(churn_by_dist, use_container_width=True)
            
        with col2:
            st.subheader("📋 재공략 대상 학교 리스트")
            st.dataframe(
                churn_summary.style.format({
                    '부수': '{:,.0f}',
                    '금액': '{:,.0f}'
                }).background_gradient(subset=['부수'], cmap='Reds'),
                use_container_width=True,
                height=600
            )
            
            # 엑셀 다운로드
            csv = churn_summary.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "📥 이탈 학교 리스트 다운로드 (CSV)",
                csv,
                "churn_schools.csv",
                "text/csv",
                key='download-churn'
            )
    else:
        st.success("2025년 주문 학교 중 2026년에 이탈한 학교가 없습니다! 🎉")

# 3. 효율성 매트릭스
with tab3:
    st.header("📊 영업 효율성 매트릭스 (Quadrant Analysis)")
    st.markdown("X축: 시장 점유율 (Market Share), Y축: 성장률 (Growth Rate)")
    
    # 분석 단위 선택
    analysis_unit = st.radio("분석 단위", ["총판", "지역(시도)"], horizontal=True)
    
    group_col = '총판' if analysis_unit == "총판" else '시도명'
    
    # 2025, 2026 집계
    agg_2025 = df_2025.groupby(group_col)['부수'].sum().reset_index(name='부수_2025')
    agg_2026 = df_2026.groupby(group_col)['부수'].sum().reset_index(name='부수_2026')
    
    # 시장 규모 (2026 기준)
    if analysis_unit == "총판":
        # 총판별 시장 규모는 복잡하므로 전체 학생수 대비가 아니라 해당 총판 관할 지역 학생수로 해야 함
        # 여기서는 간단히 '주문 부수' 자체를 X축으로 하거나, 전체 대비 점유율로 근사
        market_size = agg_2026['부수_2026'].sum()
        merged = pd.merge(agg_2025, agg_2026, on=group_col, how='outer').fillna(0)
        merged['부수_2026'] = pd.to_numeric(merged['부수_2026'], errors='coerce').fillna(0)
        market_size = float(market_size) if market_size != 0 else 1
        merged['점유율(%)'] = (merged['부수_2026'] / market_size) * 100
    else:
        # 지역별 시장 규모
        market_agg = total_df.groupby('시도명')['학생수(계)'].sum().reset_index(name='시장규모')
        merged = pd.merge(agg_2025, agg_2026, on=group_col, how='outer').fillna(0)
        merged = pd.merge(merged, market_agg, left_on=group_col, right_on='시도명', how='left')
        if '시장규모' in merged.columns:
            merged['시장규모'] = pd.to_numeric(merged['시장규모'], errors='coerce').fillna(0).astype(float)
        else:
            merged['시장규모'] = 0.0
        merged['부수_2026'] = pd.to_numeric(merged['부수_2026'], errors='coerce').fillna(0).astype(float)
        merged['점유율(%)'] = (merged['부수_2026'] / merged['시장규모'].replace(0, 1).astype(float)) * 100
    
    # 성장률 계산
    merged['부수_2025'] = pd.to_numeric(merged['부수_2025'], errors='coerce').fillna(0)
    merged['부수_2026'] = pd.to_numeric(merged['부수_2026'], errors='coerce').fillna(0)
    merged['성장률(%)'] = ((merged['부수_2026'] - merged['부수_2025']) / merged['부수_2025'].replace(0, 1)) * 100
    
    # 이상치 제거 (성장률 무한대 등)
    merged = merged[merged['부수_2025'] > 0] # 2025 데이터가 있는 경우만 성장률 계산 의미 있음
    
    # 4분면 시각화
    fig_quad = px.scatter(
        merged,
        x='점유율(%)',
        y='성장률(%)',
        text=group_col,
        size='부수_2026',
        color='성장률(%)',
        color_continuous_scale='RdYlGn',
        title=f"{analysis_unit}별 효율성 매트릭스",
        hover_data=['부수_2025', '부수_2026']
    )
    
    # 기준선 (평균)
    avg_share = merged['점유율(%)'].mean()
    avg_growth = merged['성장률(%)'].mean()
    
    fig_quad.add_hline(y=avg_growth, line_dash="dash", line_color="gray", annotation_text="평균 성장률")
    fig_quad.add_vline(x=avg_share, line_dash="dash", line_color="gray", annotation_text="평균 점유율")
    
    fig_quad.update_traces(textposition='top center')
    fig_quad.update_layout(height=600)
    
    st.plotly_chart(fig_quad, use_container_width=True)
    
    st.info(f"""
    **해석 가이드:**
    - **1사분면 (우상단)**: ⭐ Star (점유율 높음, 성장률 높음) - 집중 투자 및 유지
    - **2사분면 (좌상단)**: ❓ Question Mark (점유율 낮음, 성장률 높음) - 점유율 확대 전략 필요
    - **3사분면 (좌하단)**: 🐕 Dog (점유율 낮음, 성장률 낮음) - 철수 또는 전략 수정 고려
    - **4사분면 (우하단)**: 🐄 Cash Cow (점유율 높음, 성장률 낮음) - 수익 창출 및 방어
    """)

# 4. 연계 판매
with tab4:
    st.header("🔗 과목 간 연계 판매 분석 (Cross-sell)")
    st.markdown("특정 과목을 구매한 학교가 다른 과목도 구매했는지 분석합니다.")
    
    if '과목명' in order_df.columns:
        # 학교별 구매 과목 리스트 생성
        school_subjects = df_2026.groupby(school_col)['과목명'].unique().apply(list)
        
        # 과목 목록
        all_subjects = sorted(df_2026['과목명'].unique())
        
        # Co-occurrence Matrix 생성
        co_occurrence = pd.DataFrame(0, index=all_subjects, columns=all_subjects)
        
        for subjects in school_subjects:
            for s1 in subjects:
                for s2 in subjects:
                    co_occurrence.loc[s1, s2] += 1
        
        # 자기 자신과의 관계는 제외 (또는 최대값으로 두어 스케일링)
        # 여기서는 0으로 두어 다른 과목과의 관계 강조
        np.fill_diagonal(co_occurrence.values, 0)
        
        fig_heatmap = px.imshow(
            co_occurrence,
            text_auto=True,
            color_continuous_scale='Viridis',
            title="과목 간 동시 구매 빈도 (2026년 기준)"
        )
        fig_heatmap.update_layout(height=700)
        st.plotly_chart(fig_heatmap, use_container_width=True)
        
        st.markdown("### 💡 패키지 영업 추천")
        # 가장 강한 연관관계 찾기
        pairs = co_occurrence.stack().reset_index()
        pairs.columns = ['과목A', '과목B', '동시구매수']
        pairs = pairs[pairs['과목A'] < pairs['과목B']] # 중복 제거
        top_pairs = pairs.sort_values('동시구매수', ascending=False).head(5)
        
        for _, row in top_pairs.iterrows():
            st.success(f"**{row['과목A']}** + **{row['과목B']}**: {row['동시구매수']}개 학교에서 함께 구매했습니다. 묶음 제안이 효과적일 수 있습니다.")

# 5. AI 인사이트 (Rule-based)
with tab5:
    st.header("🤖 자동 인사이트 요약")
    st.markdown("데이터 기반으로 생성된 자동 리포트입니다.")
    
    # 1. 성장 챔피언
    top_growth_dist = merged.sort_values('성장률(%)', ascending=False).head(1)
    if not top_growth_dist.empty:
        name = top_growth_dist.iloc[0][group_col]
        rate = top_growth_dist.iloc[0]['성장률(%)']
        st.info(f"🚀 **성장 챔피언**: **{name}**이(가) 전년 대비 **{rate:.1f}%** 성장하며 가장 높은 성장률을 보였습니다.")
    
    # 2. 이탈 경고
    if churned_schools:
        churn_amt = pd.to_numeric(churn_summary['금액'].sum(), errors='coerce')
        churn_amt = float(churn_amt) if not pd.isna(churn_amt) else 0.0
        st.warning(f"⚠️ **이탈 경고**: 총 **{len(churned_schools)}개 학교**가 이탈하여 약 **{churn_amt/100000000:.1f}억원**의 매출 감소가 예상됩니다. '이탈 분석' 탭에서 명단을 확인하세요.")
    
    # 3. 지역별 강세
    if '지역구분' in df_2026.columns:
        region_counts = df_2026['지역구분'].value_counts()
        top_region = region_counts.index[0]
        pct = (float(region_counts.iloc[0]) / float(region_counts.sum())) * 100 if region_counts.sum() != 0 else 0.0
        st.success(f"🏙️ **지역 강세**: **{top_region}** 지역에서의 주문이 전체의 **{pct:.1f}%**를 차지하고 있습니다.")
    
    # 4. 과목 트렌드
    if '과목명' in df_2026.columns and not df_2026.empty:
        try:
            top_subject = df_2026.groupby('과목명')['부수'].sum().idxmax()
            st.info(f"📚 **베스트셀러**: **{top_subject}** 과목이 올해 가장 많은 사랑을 받았습니다.")
        except Exception:
            st.info("📚 과목별 데이터를 계산할 수 없습니다.")

    st.markdown("---")
    st.caption("※ 이 리포트는 규칙 기반 알고리즘에 의해 자동 생성되었습니다.")
