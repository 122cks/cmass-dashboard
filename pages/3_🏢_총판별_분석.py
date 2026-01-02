import streamlit as st
from utils.style import apply_custom_style
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# Use utils package imports
from utils.common_filters import apply_common_filters, show_filter_summary
from utils.year_filter import add_year_filter_sidebar, filter_by_years, create_year_comparison_metrics
from utils.market_share_calculator import calculate_both_shares, compare_year_shares

st.set_page_config(page_title="총판별 분석", page_icon="🏢", layout="wide")
apply_custom_style()

# Get data
if 'total_df' not in st.session_state or 'order_df' not in st.session_state:
    st.error("데이터를 불러올 수 없습니다. 메인 페이지로 돌아가주세요.")
    st.stop()

total_df = st.session_state['total_df']
order_df_orig = st.session_state['order_df'].copy()

# 학년도 필터 추가
selected_years, comparison_mode = add_year_filter_sidebar(order_df_orig, default_year='2026')
if selected_years:
    order_df = filter_by_years(order_df_orig, selected_years)
else:
    order_df = order_df_orig

target_df = st.session_state.get('target_df', pd.DataFrame())  # 목표 데이터 로드
distributor_df = st.session_state.get('distributor_df', pd.DataFrame())  # 총판 정보 로드

st.title("🏢 총판별 상세 분석")
st.markdown("---")

# 연도별 비교 모드 안내
if comparison_mode:
    st.info("📊 **연도 비교 모드**: 2025년과 2026년 데이터를 비교하여 부수, 학교점유율, 학생수점유율의 증감을 확인할 수 있습니다.")

# Modal for detailed distributor info
@st.dialog("🏢 총판 상세 정보", width="large")
def show_distributor_detail(dist_name):
    """총판별 상세 정보 모달"""
    st.subheader(f"🏢 {dist_name}")
    
    # 해당 총판의 모든 주문 데이터
    dist_orders = st.session_state['order_df'][
        st.session_state['order_df']['총판'] == dist_name
    ].copy()
    
    # 기본 통계
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 주문 부수", f"{dist_orders['부수'].sum():,.0f}부")
    with col2:
        school_col = '정보공시학교코드' if '정보공시학교코드' in dist_orders.columns else '학교코드'
        st.metric("담당 학교 수", f"{dist_orders[school_col].nunique():,}개")
    with col3:
        st.metric("총 주문 금액", f"{dist_orders['금액'].sum():,.0f}원" if '금액' in dist_orders.columns else "N/A")
    with col4:
        st.metric("과목 수", f"{dist_orders['과목명'].nunique():,}개" if '과목명' in dist_orders.columns else "N/A")
    
    st.markdown("---")
    
    # 탭으로 구분
    detail_tab1, detail_tab2, detail_tab3 = st.tabs(["📚 과목별 현황", "🗺️ 지역별 분포", "🏫 학교별 주문"])
    
    with detail_tab1:
        st.subheader("과목별 주문 현황")
        if '과목명' in dist_orders.columns:
            subject_orders = dist_orders.groupby('과목명').agg({
                '부수': 'sum',
                school_col: 'nunique'
            }).reset_index()
            subject_orders.columns = ['과목명', '주문부수', '학교수']
            subject_orders = subject_orders.sort_values('주문부수', ascending=False)
            
            fig = px.bar(
                subject_orders.head(20),
                x='주문부수',
                y='과목명',
                orientation='h',
                title="과목별 주문 TOP 20",
                color='학교수',
                color_continuous_scale='Viridis'
            )
            fig.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(
                subject_orders.style.format({
                    '주문부수': '{:,.0f}',
                    '학교수': '{:,.0f}'
                }),
                use_container_width=True,
                height=300
            )
        else:
            st.info("과목 정보가 없습니다.")
    
    with detail_tab2:
        st.subheader("지역별 분포")
        if '시도' in dist_orders.columns:
            region_orders = dist_orders.groupby('시도').agg({
                '부수': 'sum',
                school_col: 'nunique'
            }).reset_index()
            region_orders.columns = ['지역', '주문부수', '학교수']
            region_orders = region_orders.sort_values('주문부수', ascending=False)
            
            fig = px.pie(
                region_orders,
                values='주문부수',
                names='지역',
                title="지역별 주문 비중"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(
                region_orders.style.format({
                    '주문부수': '{:,.0f}',
                    '학교수': '{:,.0f}'
                }),
                use_container_width=True
            )
        else:
            st.info("지역 정보가 없습니다.")
    
    with detail_tab3:
        st.subheader("학교별 주문 현황")
        school_orders = dist_orders.groupby('학교명').agg({
            '부수': 'sum',
            '금액': 'sum' if '금액' in dist_orders.columns else 'count'
        }).reset_index()
        school_orders.columns = ['학교명', '주문부수', '주문금액']
        school_orders = school_orders.sort_values('주문부수', ascending=False)
        
        fig = px.bar(
            school_orders.head(30),
            x='주문부수',
            y='학교명',
            orientation='h',
            title="학교별 주문 TOP 30"
        )
        fig.update_layout(height=700, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(
            school_orders.style.format({
                '주문부수': '{:,.0f}',
                '주문금액': '{:,.0f}'
            }),
            use_container_width=True,
            height=400
        )

# Apply common filters
filtered_order_df = apply_common_filters(order_df)
show_filter_summary(filtered_order_df, st.session_state['order_df'])

st.sidebar.markdown("---")
st.sidebar.info(f"📊 필터링된 데이터: {len(filtered_order_df):,}건")

# Main Metrics
if '총판' in filtered_order_df.columns:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_orders = filtered_order_df['부수'].sum()
        st.metric("총 주문 부수", f"{total_orders:,.0f}부")
    
    with col2:
        total_amount = filtered_order_df['금액'].sum() if '금액' in filtered_order_df.columns else 0
        st.metric("총 주문 금액", f"{total_amount:,.0f}원")
    
    with col3:
        num_distributors = filtered_order_df['총판'].nunique()
        st.metric("총판 수", f"{num_distributors}개")
    
    with col4:
        avg_per_dist = total_orders / num_distributors if num_distributors > 0 else 0
        st.metric("총판당 평균", f"{avg_per_dist:,.0f}부")
    
    st.markdown("---")
    
    # Tab Layout
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["📊 총판별 현황", "🎯 목표 대비 실적", "📈 실적 비교", "🎯 성과 분석", "💡 효율성 분석", "🗺️ 시군구별 분석", "📋 상세 테이블"])
    
    with tab1:
        st.subheader("총판별 판매 현황")
        
        st.info("💡 **목표는 2026년도 기준**이므로, 2026년도 목표과목1·목표과목2 주문만 집계하여 달성률을 계산합니다.")
        
        # 🚨 원본 주문 데이터에서 직접 필터링 (세션 필터가 적용되지 않은 경우 대비)
        if 'order_df_original' in st.session_state:
            source_df = st.session_state['order_df_original'].copy()
        else:
            source_df = filtered_order_df.copy()
        
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
            filtered_order_2026 = source_df[
                (source_df['학년도'] == 2026) & 
                (source_df[target_col].isin(['목표과목1', '목표과목2']))
            ].copy()
        else:
            filtered_order_2026 = source_df[source_df[target_col].isin(['목표과목1', '목표과목2'])].copy()
        
        # Distributor statistics (전체 주문 데이터는 참고용)
        school_code_col = '정보공시학교코드' if '정보공시학교코드' in filtered_order_2026.columns else '학교코드'
        
        # 2026년도 데이터로 집계
        dist_stats = filtered_order_2026.groupby('총판').agg({
            '부수': 'sum',
            '금액': 'sum' if '금액' in filtered_order_2026.columns else 'count',
            school_code_col: 'nunique',
            '과목명': 'nunique' if '과목명' in filtered_order_2026.columns else 'count'
        }).reset_index()
        
        dist_stats.columns = ['총판', '주문부수', '주문금액', '거래학교수', '취급과목수']
        dist_stats['판매비중(%)'] = (dist_stats['주문부수'] / dist_stats['주문부수'].sum()) * 100
        dist_stats['학교당평균'] = dist_stats['주문부수'] / dist_stats['거래학교수']
        
        # 학생수 기반 시장규모 및 점유율 추가
        distributor_market = st.session_state.get('distributor_market', pd.DataFrame())
        if not distributor_market.empty and '총판명(공식)' in distributor_market.columns:
            # 총판명 매핑 (공식명으로)
            market_map = distributor_market.set_index('총판명(공식)')[['시장규모', '주문부수']].to_dict('index')
            
            def get_market_data(dist_name):
                # 정확한 이름 매치
                if dist_name in market_map:
                    return market_map[dist_name]
                # 부분 매치 (괄호 뒤 이름)
                dist_short = dist_name.split(')')[-1] if ')' in dist_name else dist_name
                for official_name in market_map.keys():
                    if dist_short in official_name or official_name.endswith(dist_short):
                        return market_map[official_name]
                return {'시장규모': 0, '주문부수': 0}
            
            dist_stats['시장규모'] = dist_stats['총판'].apply(lambda x: get_market_data(x)['시장규모'])
            dist_stats['점유율(%)'] = dist_stats.apply(
                lambda row: (row['주문부수'] / row['시장규모'] * 100) if row['시장규모'] > 0 else 0,
                axis=1
            )
        else:
            # Fallback: 전체 학생수 기반
            total_students = st.session_state.get('total_df', pd.DataFrame())['학생수(계)'].sum()
            dist_stats['시장규모'] = total_students
            dist_stats['점유율(%)'] = (dist_stats['주문부수'] / total_students * 100) if total_students > 0 else 0
        
        # 목표 데이터 병합 (목표1 + 목표2)
        if not target_df.empty and '총판명(공식)' in target_df.columns:
            # 목표1 부수와 목표2 부수 합산하여 전체 목표 계산
            target_summary = target_df.copy()
            
            # 쉼표 제거 및 숫자 변환
            for col in ['목표과목1 부수', '목표과목2 부수', '전체목표 부수']:
                if col in target_summary.columns:
                    target_summary[col] = target_summary[col].astype(str).str.replace(',', '').str.replace(' ', '')
                    target_summary[col] = pd.to_numeric(target_summary[col], errors='coerce').fillna(0)
            
            # 전체 목표 = 목표1 + 목표2
            if '목표과목1 부수' in target_summary.columns and '목표과목2 부수' in target_summary.columns:
                target_summary['전체목표'] = target_summary['목표과목1 부수'] + target_summary['목표과목2 부수']
            else:
                target_summary['전체목표'] = target_summary.get('전체목표 부수', 0)
            
            # 총판명으로 병합
            target_map = target_summary.groupby('총판명(공식)')['전체목표'].sum().to_dict()
            dist_stats['목표부수'] = dist_stats['총판'].map(target_map).fillna(0)
            dist_stats['달성률(%)'] = (dist_stats['주문부수'] / dist_stats['목표부수'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
        else:
            dist_stats['목표부수'] = 0
            dist_stats['달성률(%)'] = 0
        
        dist_stats = dist_stats.sort_values('주문부수', ascending=False)
        
        # 총판 클릭 안내
        st.info("💡 **아래 차트와 테이블에서 총판을 클릭**하면 해당 총판의 상세 정보를 확인할 수 있습니다.")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 학생수 기반 점유율 차트
            fig = px.bar(
                dist_stats.head(20),
                x='총판',
                y='점유율(%)',
                title="총판별 학생수 대비 점유율 TOP 20 (담당 학교 학생수 기준)",
                text='점유율(%)',
                color='점유율(%)',
                color_continuous_scale='Blues',
                hover_data=['주문부수', '시장규모', '거래학교수']
            )
            fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
            fig.update_layout(height=500, xaxis_tickangle=-45, showlegend=False, yaxis_title="점유율 (%)")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Pie chart
            fig_pie = px.pie(
                dist_stats.head(10),
                values='주문부수',
                names='총판',
                title="총판별 판매 비중 TOP 10"
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # 클릭 가능한 총판 테이블
        st.markdown("### 📋 총판별 상세 데이터 (클릭하여 상세보기)")
        
        for rank, (idx, row) in enumerate(dist_stats.head(20).iterrows(), 1):
            col_btn, col_name, col_orders, col_schools, col_share = st.columns([1, 3, 2, 2, 2])
            
            with col_btn:
                if st.button("🏢", key=f"dist_btn_{idx}", help="상세 정보 보기"):
                    show_distributor_detail(row['총판'])
            
            with col_name:
                st.write(f"**#{rank} {row['총판']}**")
            with col_orders:
                st.write(f"{row['주문부수']:,.0f}부")
            with col_schools:
                st.write(f"{row['거래학교수']:,.0f}개교")
            with col_share:
                market_share = row.get('점유율(%)', row.get('판매비중(%)', 0))
                st.write(f"{market_share:.2f}% (학생수 대비)")
        
        # Market share visualization
        st.markdown("---")
        st.subheader("📊 시장 점유율 분포")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Donut chart
            fig_donut = go.Figure(data=[go.Pie(
                labels=dist_stats['총판'],
                values=dist_stats['판매비중(%)'],
                hole=.4
            )])
            fig_donut.update_layout(title="총판별 시장 점유율")
            st.plotly_chart(fig_donut, use_container_width=True)
        
        with col2:
            # Waterfall chart for top distributors
            dist_waterfall = dist_stats.head(10).copy()
            fig_waterfall = go.Figure(go.Waterfall(
                name="주문량",
                orientation="v",
                x=dist_waterfall['총판'],
                y=dist_waterfall['주문부수'],
                text=dist_waterfall['주문부수'],
                textposition="outside",
                connector={"line": {"color": "rgb(63, 63, 63)"}},
            ))
            fig_waterfall.update_layout(title="TOP 10 총판 주문량 누적")
            st.plotly_chart(fig_waterfall, use_container_width=True)
    
    with tab2:
        st.subheader("🎯 목표 대비 실적 분석")
        
        # 목표가 있는 총판만 필터링
        target_dists = dist_stats[dist_stats['목표부수'] > 0].copy()
        
        if len(target_dists) > 0:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_target = target_dists['목표부수'].sum()
                st.metric("전체 목표", f"{total_target:,.0f}부")
            
            with col2:
                total_achieved = target_dists['주문부수'].sum()
                st.metric("전체 실적", f"{total_achieved:,.0f}부")
            
            with col3:
                overall_rate = (total_achieved / total_target * 100) if total_target > 0 else 0
                st.metric("전체 달성률", f"{overall_rate:.1f}%",
                         delta=f"{total_achieved - total_target:,.0f}부")
            
            with col4:
                achieved_count = len(target_dists[target_dists['달성률(%)'] >= 100])
                st.metric("목표 달성 총판", f"{achieved_count}/{len(target_dists)}개")
            
            st.markdown("---")
            
            # 달성률 분포
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # 목표 vs 실적 비교 차트
                fig_compare = go.Figure()
                
                top_target = target_dists.head(20)
                
                fig_compare.add_trace(go.Bar(
                    name='목표',
                    x=top_target['총판'],
                    y=top_target['목표부수'],
                    marker_color='lightblue',
                    text=top_target['목표부수'],
                    texttemplate='%{text:,.0f}',
                    textposition='outside'
                ))
                
                fig_compare.add_trace(go.Bar(
                    name='실적',
                    x=top_target['총판'],
                    y=top_target['주문부수'],
                    marker_color='darkblue',
                    text=top_target['주문부수'],
                    texttemplate='%{text:,.0f}',
                    textposition='outside'
                ))
                
                fig_compare.update_layout(
                    title="총판별 목표 vs 실적 (TOP 20)",
                    barmode='group',
                    xaxis_tickangle=-45,
                    height=500,
                    yaxis_title="부수"
                )
                st.plotly_chart(fig_compare, use_container_width=True)
            
            with col2:
                # 달성률 분포 파이 차트
                achievement_groups = pd.cut(
                    target_dists['달성률(%)'],
                    bins=[0, 50, 80, 100, 150, float('inf')],
                    labels=['50% 미만', '50-80%', '80-100%', '100-150%', '150% 이상']
                )
                achievement_dist = achievement_groups.value_counts()
                
                fig_pie = px.pie(
                    values=achievement_dist.values,
                    names=achievement_dist.index,
                    title="달성률 분포",
                    color_discrete_sequence=px.colors.diverging.RdYlGn
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            # 달성률 상세
            st.markdown("---")
            st.subheader("📊 총판 간 달성률 비교")
            
            # 달성률 순위 추가
            target_dists_sorted = target_dists.sort_values('달성률(%)', ascending=False).reset_index(drop=True)
            target_dists_sorted['달성률순위'] = range(1, len(target_dists_sorted) + 1)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # 달성률 TOP 20 차트
                fig_achievement = px.bar(
                    target_dists_sorted.head(20),
                    x='총판',
                    y='달성률(%)',
                    title="총판별 목표 달성률 비교 TOP 20",
                    text='달성률(%)',
                    color='달성률(%)',
                    color_continuous_scale='RdYlGn',
                    range_color=[0, 200]
                )
                fig_achievement.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig_achievement.update_layout(xaxis_tickangle=-45, height=500)
                fig_achievement.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="목표선 (100%)")
                st.plotly_chart(fig_achievement, use_container_width=True)
            
            with col2:
                # 달성률 vs 주문부수 산점도
                fig_scatter = px.scatter(
                    target_dists_sorted,
                    x='주문부수',
                    y='달성률(%)',
                    size='목표부수',
                    color='달성률(%)',
                    hover_data=['총판', '목표부수'],
                    title="달성률 vs 주문규모",
                    labels={'주문부수': '실적 부수', '달성률(%)': '달성률 (%)'},
                    color_continuous_scale='RdYlGn',
                    range_color=[0, 200]
                )
                fig_scatter.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="목표선")
                fig_scatter.update_layout(height=500)
                st.plotly_chart(fig_scatter, use_container_width=True)
            
            # 순위 테이블
            st.markdown("---")
            st.subheader("🏆 달성률 순위 TOP 20")
            
            display_cols = ['달성률순위', '총판', '목표부수', '주문부수', '달성률(%)', '판매비중(%)']
            st.dataframe(
                target_dists_sorted[display_cols].head(20).style.format({
                    '목표부수': '{:,.0f}',
                    '주문부수': '{:,.0f}',
                    '달성률(%)': '{:.1f}',
                    '판매비중(%)': '{:.2f}'
                }).background_gradient(subset=['달성률(%)'], cmap='RdYlGn', vmin=0, vmax=200),
                use_container_width=True,
                height=500
            )
            
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### ⭐ 목표 초과 달성 (100% 이상)")
                over_achieved = target_dists[target_dists['달성률(%)'] >= 100].sort_values('달성률(%)', ascending=False)
                
                if len(over_achieved) > 0:
                    display_cols = ['총판', '목표부수', '주문부수', '달성률(%)']
                    st.dataframe(
                        over_achieved[display_cols].style.format({
                            '목표부수': '{:,.0f}',
                            '주문부수': '{:,.0f}',
                            '달성률(%)': '{:.1f}%'
                        }),
                        use_container_width=True,
                        height=300
                    )
                else:
                    st.info("목표 달성 총판이 없습니다.")
            
            with col2:
                st.markdown("#### 🎯 목표 미달성 (<100%)")
                under_achieved = target_dists[target_dists['달성률(%)'] < 100].sort_values('달성률(%)', ascending=False)
                
                if len(under_achieved) > 0:
                    display_cols = ['총판', '목표부수', '주문부수', '달성률(%)']
                    st.dataframe(
                        under_achieved[display_cols].style.format({
                            '목표부수': '{:,.0f}',
                            '주문부수': '{:,.0f}',
                            '달성률(%)': '{:.1f}%'
                        }),
                        use_container_width=True,
                        height=300
                    )
                else:
                    st.success("모든 총판이 목표를 달성했습니다!")
            
            # 갭 분석
            st.markdown("---")
            st.subheader("📉 목표 대비 갭 분석")
            
            target_dists['갭'] = target_dists['주문부수'] - target_dists['목표부수']
            gap_chart = target_dists.sort_values('갭').head(20)
            
            colors = ['red' if x < 0 else 'green' for x in gap_chart['갭']]
            
            fig_gap = go.Figure(go.Bar(
                x=gap_chart['총판'],
                y=gap_chart['갭'],
                marker_color=colors,
                text=gap_chart['갭'],
                texttemplate='%{text:,.0f}',
                textposition='outside'
            ))
            
            fig_gap.update_layout(
                title="총판별 목표 대비 갭 (실적 - 목표)",
                xaxis_tickangle=-45,
                yaxis_title="갭 (부수)",
                height=400
            )
            fig_gap.add_hline(y=0, line_dash="dash", line_color="black")
            st.plotly_chart(fig_gap, use_container_width=True)
            
        else:
            st.warning("목표 데이터가 없습니다.")
    
    with tab3:
        st.subheader("📈 총판 실적 비교")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Scatter plot - Schools vs Orders
            fig_scatter = px.scatter(
                dist_stats,
                x='거래학교수',
                y='주문부수',
                size='주문금액',
                color='판매비중(%)',
                hover_name='총판',
                title="거래 학교 수 vs 주문량",
                labels={'거래학교수': '거래 학교 수', '주문부수': '주문 부수'},
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
        
        with col2:
            # Average per school
            fig_avg = px.bar(
                dist_stats.head(15),
                x='총판',
                y='학교당평균',
                title="총판별 학교당 평균 주문량 TOP 15",
                text='학교당평균',
                color='학교당평균',
                color_continuous_scale='Blues'
            )
            fig_avg.update_traces(texttemplate='%{text:.1f}', textposition='outside')
            fig_avg.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_avg, use_container_width=True)
        
        # Multi-metric comparison
        st.markdown("---")
        st.subheader("🔄 다차원 비교")
        
        # Radar chart for top 5 distributors
        top5_dists = dist_stats.head(5)
        
        # Normalize metrics for radar chart
        metrics_to_compare = ['주문부수', '주문금액', '거래학교수', '취급과목수', '학교당평균']
        normalized_data = top5_dists[metrics_to_compare].copy()
        for col in metrics_to_compare:
            max_val = normalized_data[col].max()
            normalized_data[col] = (normalized_data[col] / max_val) * 100 if max_val > 0 else 0
        
        fig_radar = go.Figure()
        
        for idx, row in top5_dists.iterrows():
            dist_name = row['총판']
            values = normalized_data.loc[idx].tolist()
            values.append(values[0])  # Close the radar
            
            fig_radar.add_trace(go.Scatterpolar(
                r=values,
                theta=metrics_to_compare + [metrics_to_compare[0]],
                name=dist_name,
                fill='toself'
            ))
        
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            title="TOP 5 총판 다차원 비교 (정규화)"
        )
        st.plotly_chart(fig_radar, use_container_width=True)
    
    with tab4:
        st.subheader("🎯 총판별 성과 심층 분석")
        
        # Performance ranking
        st.markdown("#### 🏆 종합 성과 순위")
        
        # Calculate composite score
        dist_stats['종합점수'] = (
            (dist_stats['주문부수'] / dist_stats['주문부수'].max() * 40) +
            (dist_stats['판매비중(%)'] / dist_stats['판매비중(%)'].max() * 30) +
            (dist_stats['거래학교수'] / dist_stats['거래학교수'].max() * 20) +
            (dist_stats['취급과목수'] / dist_stats['취급과목수'].max() * 10)
        )
        dist_stats = dist_stats.sort_values('종합점수', ascending=False)
        
        # Display top performers
        # Display top performers with school level breakdown
        st.markdown("👉 카드를 클릭하면 해당 총판의 세부 주문 내역과 지역별 학교급별 현황을 확인할 수 있습니다.")
        
        cols = st.columns(3)
        for idx, row in dist_stats.head(9).iterrows():
            col_idx = dist_stats.head(9).index.tolist().index(idx)
            with cols[col_idx % 3]:
                rank = col_idx + 1
                medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"
                dist_name = row['총판']
                
                # Card button
                if st.button(f"{medal} {dist_name}", key=f"dist_card_{idx}"):
                    st.session_state[f'show_dist_detail_{dist_name}'] = not st.session_state.get(f'show_dist_detail_{dist_name}', False)
                
                st.markdown(f"""
                <div style="border: 2px solid {'#FFD700' if rank == 1 else '#C0C0C0' if rank == 2 else '#CD7F32' if rank == 3 else '#4CAF50'}; 
                            border-radius: 10px; padding: 15px; margin: 10px 0;">
                    <h4>{medal} {dist_name}</h4>
                    <p><b>종합점수:</b> {row['종합점수']:.1f}</p>
                    <p><b>주문:</b> {row['주문부수']:,.0f}부 ({row['판매비중(%)']:.1f}%)</p>
                    <p><b>거래학교:</b> {row['거래학교수']}개교</p>
                    <p><b>평균/학교:</b> {row['학교당평균']:.1f}부</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Show detail when clicked
                if st.session_state.get(f'show_dist_detail_{dist_name}', False):
                    with st.expander(f"📊 {dist_name} 상세 정보", expanded=True):
                        dist_orders = filtered_order_df[filtered_order_df['총판'] == dist_name]
                        
                        # Subject breakdown
                        subject_col = '교과서명_구분' if '교과서명_구분' in dist_orders.columns else '교과서명'
                        st.markdown("**📚 과목별 주문**")
                        subject_summary = dist_orders.groupby(subject_col)['부수'].sum().reset_index()
                        subject_summary = subject_summary.sort_values('부수', ascending=False)
                        subject_summary.columns = ['과목명', '주문부수']
                        st.dataframe(
                            subject_summary.style.format({'주문부수': '{:,.0f}'}),
                            use_container_width=True,
                            height=150
                        )
                        
                        st.markdown("---")
                        
                        # Regional breakdown with school level
                        if '시도교육청' in dist_orders.columns:
                            st.markdown("**🗺️ 지역별 주문 현황**")
                            
                            # Get school codes from orders and merge with total data
                            if '정보공시학교코드' in dist_orders.columns:
                                # Merge to get school level info
                                dist_with_level = pd.merge(
                                    dist_orders,
                                    total_df[['정보공시 학교코드', '학교급코드', '학생수(계)']].drop_duplicates(),
                                    left_on='정보공시학교코드',
                                    right_on='정보공시 학교코드',
                                    how='left'
                                )
                                
                                school_level_names = {2: '초등학교', 3: '중학교', 4: '고등학교'}
                                dist_with_level['학교급'] = dist_with_level['학교급코드'].map(school_level_names)
                                
                                # Group by region and school level
                                region_school_summary = dist_with_level.groupby(['시도교육청', '학교급']).agg({
                                    '부수': 'sum',
                                    '학생수(계)': 'sum'
                                }).reset_index()
                                
                                # Display by region
                                for region in region_school_summary['시도교육청'].unique():
                                    region_data = region_school_summary[region_school_summary['시도교육청'] == region]
                                    st.write(f"**{region}**")
                                    for _, level_row in region_data.iterrows():
                                        if pd.notna(level_row['학교급']):
                                            st.write(f"  - {level_row['학교급']}: 주문 {level_row['부수']:,.0f}부 / 전체학생 {level_row['학생수(계)']:,.0f}명")
                            else:
                                # Simple regional breakdown
                                region_summary = dist_orders.groupby('시도교육청')['부수'].sum().reset_index()
                                region_summary = region_summary.sort_values('부수', ascending=False)
                                for _, reg_row in region_summary.iterrows():
                                    st.write(f"- {reg_row['시도교육청']}: {reg_row['부수']:,.0f}부")
        
        # Regional distribution by distributor
        st.markdown("---")
        st.subheader("📍 총판별 지역 분포")
        
        if '시도교육청' in filtered_order_df.columns:
            selected_dist = st.selectbox("총판 선택", dist_stats['총판'].tolist())
            
            dist_regional = filtered_order_df[filtered_order_df['총판'] == selected_dist].groupby('시도교육청')['부수'].sum().reset_index()
            dist_regional = dist_regional.sort_values('부수', ascending=False)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig = px.bar(
                    dist_regional,
                    x='시도교육청',
                    y='부수',
                    title=f"{selected_dist} - 지역별 주문 분포",
                    text='부수',
                    color='부수',
                    color_continuous_scale='Oranges'
                )
                fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                fig.update_layout(xaxis_tickangle=-45, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig_pie = px.pie(
                    dist_regional.head(10),
                    values='부수',
                    names='시도교육청',
                    title=f"{selected_dist} 지역 비중"
                )
                st.plotly_chart(fig_pie, use_container_width=True)
    
    with tab5:
        st.subheader("� 총판 효율성 및 성장 분석")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 효율성 지표")
            
            # Add efficiency metrics
            dist_stats['과목당평균부수'] = dist_stats['주문부수'] / dist_stats['취급과목수']
            dist_stats['과목다양성'] = dist_stats['취급과목수']
            
            # Efficiency score
            dist_stats['효율성점수'] = (
                (dist_stats['학교당평균'] / dist_stats['학교당평균'].max() * 50) +
                (dist_stats['과목당평균부수'] / dist_stats['과목당평균부수'].max() * 50)
            )
            
            top_efficient = dist_stats.nlargest(10, '효율성점수')
            
            fig = px.bar(
                top_efficient,
                x='총판',
                y='효율성점수',
                title="효율성 TOP 10 총판",
                text='효율성점수',
                color='효율성점수',
                color_continuous_scale='RdYlGn'
            )
            fig.update_traces(texttemplate='%{text:.1f}', textposition='outside')
            fig.update_layout(xaxis_tickangle=-45, showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # Detailed efficiency table
            st.markdown("**효율성 상세 지표**")
            efficiency_display = top_efficient[['총판', '학교당평균', '과목당평균부수', '효율성점수']].copy()
            st.dataframe(
                efficiency_display.style.format({
                    '학교당평균': '{:.1f}',
                    '과목당평균부수': '{:.1f}',
                    '효율성점수': '{:.2f}'
                }),
                use_container_width=True,
                height=300
            )
        
        with col2:
            st.markdown("#### 🎯 성장 잠재력 분석")
            
            # Growth potential based on low penetration but high efficiency
            dist_stats['성장잠재력'] = (
                (100 - dist_stats['판매비중(%)']) * dist_stats['효율성점수'] / 100
            )
            
            high_potential = dist_stats.nlargest(10, '성장잠재력')
            
            fig = px.scatter(
                high_potential,
                x='판매비중(%)',
                y='효율성점수',
                size='성장잠재력',
                color='성장잠재력',
                hover_name='총판',
                title="성장 잠재력 매트릭스 (크기 = 잠재력)",
                labels={'판매비중(%)': '현재 시장 점유율 (%)', '효율성점수': '효율성 점수'},
                color_continuous_scale='Viridis'
            )
            fig.add_hline(y=50, line_dash="dash", line_color="red", 
                         annotation_text="효율성 기준선", annotation_position="right")
            fig.add_vline(x=5, line_dash="dash", line_color="blue",
                         annotation_text="점유율 기준선", annotation_position="top")
            st.plotly_chart(fig, use_container_width=True)
            
            # Strategic recommendations
            st.markdown("**🎯 전략적 분류**")
            
            # Classify distributors
            high_eff = dist_stats['효율성점수'].median()
            high_share = dist_stats['판매비중(%)'].median()
            
            stars = dist_stats[(dist_stats['효율성점수'] >= high_eff) & (dist_stats['판매비중(%)'] >= high_share)]
            rising_stars = dist_stats[(dist_stats['효율성점수'] >= high_eff) & (dist_stats['판매비중(%)'] < high_share)]
            cash_cows = dist_stats[(dist_stats['효율성점수'] < high_eff) & (dist_stats['판매비중(%)'] >= high_share)]
            question_marks = dist_stats[(dist_stats['효율성점수'] < high_eff) & (dist_stats['판매비중(%)'] < high_share)]
            
            st.success(f"⭐ **Star 총판** ({len(stars)}개): 높은 점유율 + 높은 효율성")
            if len(stars) > 0:
                st.write(f"- {', '.join(stars['총판'].head(5).tolist())}")
            
            st.info(f"🌟 **Rising Star** ({len(rising_stars)}개): 낮은 점유율 + 높은 효율성 (성장 잠재력)")
            if len(rising_stars) > 0:
                st.write(f"- {', '.join(rising_stars['총판'].head(5).tolist())}")
            
            st.warning(f"💰 **Cash Cow** ({len(cash_cows)}개): 높은 점유율 + 낮은 효율성 (개선 필요)")
            if len(cash_cows) > 0:
                st.write(f"- {', '.join(cash_cows['총판'].head(5).tolist())}")
            
            st.error(f"❓ **Question Mark** ({len(question_marks)}개): 낮은 점유율 + 낮은 효율성 (전략 재검토)")
            if len(question_marks) > 0:
                st.write(f"- {', '.join(question_marks['총판'].head(3).tolist())}")
        
        # Network analysis
        st.markdown("---")
        st.markdown("#### 🌐 총판 네트워크 분석")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Coverage concentration
            coverage_ratio = dist_stats['거래학교수'].sum() / len(dist_stats)
            st.metric("평균 거래 학교 수", f"{coverage_ratio:.0f}개",
                     help="총판당 평균 거래 학교 수")
        
        with col2:
            # Subject diversity
            avg_subjects = dist_stats['취급과목수'].mean()
            st.metric("평균 취급 과목 수", f"{avg_subjects:.1f}개",
                     help="총판당 평균 취급 과목 종류")
        
        with col3:
            # Market concentration (HHI)
            hhi = (dist_stats['판매비중(%)'] ** 2).sum()
            concentration_level = "높음" if hhi > 2500 else "중간" if hhi > 1500 else "낮음"
            st.metric("시장 집중도", concentration_level,
                     delta=f"HHI: {hhi:.0f}",
                     help="HHI (Herfindahl-Hirschman Index): 시장 집중도 지표")
    
    with tab6:
        st.subheader("🗺️ 시군구별 총판 분석")
        
        # Extract region info from orders
        if '시도교육청' in filtered_order_df.columns and '시군구' in filtered_order_df.columns:
            # Region-level aggregation
            region_stats = filtered_order_df.groupby('시군구').agg({
                '부수': 'sum',
                '총판': 'nunique',
                '정보공시학교코드' if '정보공시학교코드' in filtered_order_df.columns else '학교코드': 'nunique'
            }).reset_index()
            region_stats.columns = ['시군구', '주문부수', '총판수', '학교수']
            region_stats = region_stats.sort_values('주문부수', ascending=False)
            
            st.markdown("### 📍 시군구별 주문 현황")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Top regions chart
                fig = px.bar(
                    region_stats.head(20),
                    x='시군구',
                    y='주문부수',
                    title="시군구별 주문량 TOP 20",
                    text='주문부수',
                    color='총판수',
                    color_continuous_scale='Viridis',
                    hover_data=['학교수']
                )
                fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                fig.update_layout(xaxis_tickangle=-45, height=500)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Region distribution pie
                fig_pie = px.pie(
                    region_stats.head(10),
                    values='주문부수',
                    names='시군구',
                    title="상위 10개 시군구 비중"
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            st.markdown("---")
            st.markdown("### 🔍 시군구 상세 분석")
            
            # Select region for detailed analysis
            selected_region = st.selectbox(
                "시군구 선택",
                region_stats['시군구'].tolist(),
                key="region_select"
            )
            
            if selected_region:
                region_orders = filtered_order_df[filtered_order_df['시군구'] == selected_region]
                
                # Region summary
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("총 주문부수", f"{region_orders['부수'].sum():,.0f}부")
                with col2:
                    st.metric("활동 총판 수", f"{region_orders['총판'].nunique()}개")
                with col3:
                    school_col = '정보공시학교코드' if '정보공시학교코드' in region_orders.columns else '학교코드'
                    st.metric("학교 수", f"{region_orders[school_col].nunique()}개")
                with col4:
                    avg_per_dist = region_orders['부수'].sum() / region_orders['총판'].nunique()
                    st.metric("총판당 평균", f"{avg_per_dist:,.0f}부")
                
                st.markdown("---")
                
                # Distributor comparison within region
                st.markdown(f"#### 📊 {selected_region} 내 총판별 비교")
                
                region_dist_stats = region_orders.groupby('총판').agg({
                    '부수': 'sum',
                    school_col: 'nunique',
                    '금액': 'sum' if '금액' in region_orders.columns else 'count'
                }).reset_index()
                region_dist_stats.columns = ['총판', '주문부수', '학교수', '주문금액']
                region_dist_stats['지역점유율(%)'] = (region_dist_stats['주문부수'] / region_dist_stats['주문부수'].sum()) * 100
                region_dist_stats['학교당평균'] = region_dist_stats['주문부수'] / region_dist_stats['학교수']
                region_dist_stats = region_dist_stats.sort_values('주문부수', ascending=False)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Distributor ranking in region
                    fig_dist = px.bar(
                        region_dist_stats,
                        y='총판',
                        x='주문부수',
                        orientation='h',
                        title=f"{selected_region} 총판별 주문량",
                        text='주문부수',
                        color='지역점유율(%)',
                        color_continuous_scale='RdYlGn'
                    )
                    fig_dist.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                    fig_dist.update_layout(yaxis={'categoryorder': 'total ascending'}, height=400)
                    st.plotly_chart(fig_dist, use_container_width=True)
                
                with col2:
                    # Market share pie in region
                    fig_share = px.pie(
                        region_dist_stats,
                        values='주문부수',
                        names='총판',
                        title=f"{selected_region} 총판별 점유율"
                    )
                    fig_share.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_share, use_container_width=True)
                
                # Detailed table
                st.markdown("---")
                st.subheader(f"📋 {selected_region} 총판 상세 데이터")
                
                st.dataframe(
                    region_dist_stats.style.format({
                        '주문부수': '{:,.0f}',
                        '학교수': '{:,.0f}',
                        '주문금액': '{:,.0f}',
                        '지역점유율(%)': '{:.2f}',
                        '학교당평균': '{:.1f}'
                    }).background_gradient(subset=['지역점유율(%)'], cmap='Greens'),
                    use_container_width=True
                )
                
                # Competitive analysis
                st.markdown("---")
                st.markdown(f"#### ⚖️ {selected_region} 경쟁 구도 분석")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Market leader
                    leader = region_dist_stats.iloc[0]
                    st.success(f"**1위 총판**: {leader['총판']}")
                    st.write(f"점유율: {leader['지역점유율(%)']:.1f}%")
                    st.write(f"주문: {leader['주문부수']:,.0f}부")
                
                with col2:
                    # Competition intensity
                    if len(region_dist_stats) > 1:
                        top2_share = region_dist_stats.head(2)['지역점유율(%)'].sum()
                        competition = "높음" if top2_share < 60 else "중간" if top2_share < 80 else "낮음"
                        st.info(f"**경쟁 강도**: {competition}")
                        st.write(f"상위 2개사 점유율: {top2_share:.1f}%")
                    else:
                        st.info("**경쟁 강도**: 독점")
                
                with col3:
                    # Number of competitors
                    active_dists = len(region_dist_stats)
                    st.warning(f"**활동 총판**: {active_dists}개사")
                    if active_dists > 5:
                        st.write("높은 경쟁 시장")
                    elif active_dists > 2:
                        st.write("적정 경쟁 시장")
                    else:
                        st.write("과점 시장")
            
            # Regional comparison
            st.markdown("---")
            st.markdown("### 🗺️ 시군구 간 비교 분석")
            
            # Top regions comparison
            top_regions = region_stats.head(10)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Orders per school by region
                region_stats['학교당평균'] = region_stats['주문부수'] / region_stats['학교수']
                top_efficient_regions = region_stats.nlargest(10, '학교당평균')
                
                fig_eff = px.bar(
                    top_efficient_regions,
                    x='시군구',
                    y='학교당평균',
                    title="학교당 평균 주문량 TOP 10 시군구",
                    text='학교당평균',
                    color='학교당평균',
                    color_continuous_scale='Blues'
                )
                fig_eff.update_traces(texttemplate='%{text:.1f}', textposition='outside')
                fig_eff.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_eff, use_container_width=True)
            
            with col2:
                # Distributor density by region
                region_stats['총판밀도'] = region_stats['총판수'] / region_stats['학교수']
                top_density = region_stats.nlargest(10, '총판밀도')
                
                fig_density = px.bar(
                    top_density,
                    x='시군구',
                    y='총판밀도',
                    title="학교당 총판 수 TOP 10 시군구 (경쟁도)",
                    text='총판밀도',
                    color='총판밀도',
                    color_continuous_scale='Reds'
                )
                fig_density.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                fig_density.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_density, use_container_width=True)
        
        elif '시도교육청' in filtered_order_df.columns:
            st.info("💡 시군구 정보가 없습니다. 시도 단위로 분석합니다.")
            
            # Fallback to 시도 level
            sido_stats = filtered_order_df.groupby('시도교육청').agg({
                '부수': 'sum',
                '총판': 'nunique',
                '정보공시학교코드' if '정보공시학교코드' in filtered_order_df.columns else '학교코드': 'nunique'
            }).reset_index()
            sido_stats.columns = ['시도', '주문부수', '총판수', '학교수']
            sido_stats = sido_stats.sort_values('주문부수', ascending=False)
            
            fig = px.bar(
                sido_stats,
                x='시도',
                y='주문부수',
                title="시도별 주문량",
                text='주문부수',
                color='총판수',
                color_continuous_scale='Viridis'
            )
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ 지역 정보가 없습니다.")
    
    with tab7:
        st.subheader("📋 총판별 상세 데이터")
        
        # Search
        search_term = st.text_input("🔍 총판명 검색", "")
        
        if search_term:
            display_stats = dist_stats[dist_stats['총판'].str.contains(search_term, case=False, na=False, regex=False)]
        else:
            display_stats = dist_stats
        
        # Display table
        st.dataframe(
            display_stats.style.format({
                '주문부수': '{:,.0f}',
                '주문금액': '{:,.0f}',
                '거래학교수': '{:,.0f}',
                '취급과목수': '{:,.0f}',
                '판매비중(%)': '{:.2f}%',
                '학교당평균': '{:.2f}',
                '종합점수': '{:.2f}',
                '과목당평균부수': '{:.1f}',
                '효율성점수': '{:.2f}',
                '성장잠재력': '{:.2f}'
            }),
            use_container_width=True,
            height=400
        )
        
        # Download
        csv = display_stats.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 CSV 다운로드",
            data=csv,
            file_name="총판별_분석_데이터.csv",
            mime="text/csv"
        )

else:
    st.warning("총판 정보가 없습니다.")

st.markdown("---")
st.caption("🏢 총판별 분석 페이지")
