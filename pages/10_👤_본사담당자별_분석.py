import streamlit as st
from utils.style import apply_custom_style
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

st.set_page_config(page_title="본사담당자별 분석", page_icon="👤", layout="wide")
apply_custom_style()

# Get data
if 'order_df' not in st.session_state or 'total_df' not in st.session_state:
    st.error("데이터를 불러올 수 없습니다. 메인 페이지로 돌아가주세요.")
    st.stop()

order_df = st.session_state.get('order_df', pd.DataFrame()).copy()
total_df = st.session_state.get('total_df', pd.DataFrame()).copy()
product_df = st.session_state.get('product_df', pd.DataFrame()).copy()

st.title("👤 본사담당자별 분석")
st.markdown("---")

# 본사담당자별 학교 매칭
if '본사담당자(2025.09)' in total_df.columns and '정보공시 학교코드' in total_df.columns:
    school_manager_map = total_df[['정보공시 학교코드', '본사담당자(2025.09)']].drop_duplicates()
    
    # 주문 데이터에 본사담당자 매핑
    school_code_col = '정보공시학교코드' if '정보공시학교코드' in order_df.columns else '학교코드'
    if school_code_col in order_df.columns:
        order_df = pd.merge(
            order_df,
            school_manager_map,
            left_on=school_code_col,
            right_on='정보공시 학교코드',
            how='left'
        )
    
    # 본사담당자 목록
    managers = sorted([m for m in total_df['본사담당자(2025.09)'].dropna().unique() if m != ''])
    
    if len(managers) == 0:
        st.warning("본사담당자 정보가 없습니다.")
        st.stop()
    
    # Sidebar - 담당자 선택
    st.sidebar.header("🔍 담당자 선택")
    selected_managers = st.sidebar.multiselect(
        "본사담당자",
        options=managers,
        default=managers
    )
    
    if not selected_managers:
        st.warning("최소 1명 이상의 담당자를 선택해주세요.")
        st.stop()
    
    # 필터링
    filtered_total = total_df[total_df['본사담당자(2025.09)'].isin(selected_managers)].copy()
    filtered_order = order_df[order_df['본사담당자(2025.09)'].isin(selected_managers)].copy()
    
    # ===== 전체 요약 통계 =====
    st.header("📊 전체 요약")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_orders = filtered_order['부수'].sum()
        st.metric("총 주문 부수", f"{total_orders:,.0f}부")
    
    with col2:
        total_schools = filtered_order[school_code_col].nunique() if school_code_col in filtered_order.columns else 0
        st.metric("주문 학교 수", f"{total_schools:,}개")
    
    with col3:
        total_amount = filtered_order['금액'].sum() if '금액' in filtered_order.columns else 0
        st.metric("총 주문 금액", f"{total_amount:,.0f}원")
    
    with col4:
        total_subjects = filtered_order['과목명'].nunique() if '과목명' in filtered_order.columns else 0
        st.metric("과목 수", f"{total_subjects}개")
    
    with col5:
        total_market_size = filtered_total['학생수(계)'].sum() if '학생수(계)' in filtered_total.columns else 0
        st.metric("시장 규모 (학생수)", f"{total_market_size:,.0f}명")
    
    st.markdown("---")
    
    # ===== 담당자별 상세 분석 =====
    st.header("👥 담당자별 상세 분석")
    
    # 담당자별 집계
    manager_summary = []
    for manager in selected_managers:
        mgr_total = filtered_total[filtered_total['본사담당자(2025.09)'] == manager]
        mgr_order = filtered_order[filtered_order['본사담당자(2025.09)'] == manager]
        
        summary = {
            '담당자': manager,
            '담당학교수': mgr_total['정보공시 학교코드'].nunique(),
            '주문학교수': mgr_order[school_code_col].nunique() if school_code_col in mgr_order.columns else 0,
            '총주문부수': mgr_order['부수'].sum(),
            '총주문금액': mgr_order['금액'].sum() if '금액' in mgr_order.columns else 0,
            '시장규모': mgr_total['학생수(계)'].sum() if '학생수(계)' in mgr_total.columns else 0,
            '과목수': mgr_order['과목명'].nunique() if '과목명' in mgr_order.columns else 0,
            '총판수': mgr_order['총판'].nunique() if '총판' in mgr_order.columns else 0
        }
        
        # 침투율 계산
        if summary['담당학교수'] > 0:
            summary['학교침투율(%)'] = (summary['주문학교수'] / summary['담당학교수']) * 100
        else:
            summary['학교침투율(%)'] = 0
        
        manager_summary.append(summary)
    
    summary_df = pd.DataFrame(manager_summary)
    
    # 담당자 비교 차트
    tab1, tab2, tab3, tab4 = st.tabs(["📈 주요 지표 비교", "🎯 성과 분석", "🗺️ 지역 분포", "📚 과목별 분석"])
    
    with tab1:
        st.subheader("📊 담당자별 주요 지표")
        
        # 메트릭 카드
        cols = st.columns(len(selected_managers))
        for idx_val, row in summary_df.iterrows():
            idx = int(idx_val) if isinstance(idx_val, (int, np.integer)) else 0
            with cols[idx]:
                st.markdown(f"### {row['담당자']}")
                st.metric("주문 부수", f"{row['총주문부수']:,.0f}부")
                st.metric("주문 학교", f"{row['주문학교수']:,}개")
                st.metric("침투율", f"{row['학교침투율(%)']:.1f}%")
                st.metric("주문 금액", f"{row['총주문금액']/1000000:.1f}백만원")
        
        st.markdown("---")
        
        # 비교 차트
        col1, col2 = st.columns(2)
        
        with col1:
            fig1 = px.bar(
                summary_df,
                x='담당자',
                y='총주문부수',
                title="담당자별 총 주문 부수",
                color='담당자',
                text='총주문부수'
            )
            fig1.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig1.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            fig2 = px.bar(
                summary_df,
                x='담당자',
                y='학교침투율(%)',
                title="담당자별 학교 침투율",
                color='담당자',
                text='학교침투율(%)'
            )
            fig2.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig2.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig2, use_container_width=True)
        
        # 상세 테이블
        st.subheader("📋 담당자별 상세 통계")
        display_df = summary_df.copy()
        st.dataframe(
            display_df.style.format({
                '담당학교수': '{:,.0f}',
                '주문학교수': '{:,.0f}',
                '총주문부수': '{:,.0f}',
                '총주문금액': '{:,.0f}',
                '시장규모': '{:,.0f}',
                '과목수': '{:.0f}',
                '총판수': '{:.0f}',
                '학교침투율(%)': '{:.1f}'
            }).background_gradient(subset=['총주문부수', '학교침투율(%)'], cmap='YlGn'),
            use_container_width=True,
            height=200
        )
    
    with tab2:
        st.subheader("🎯 성과 분석")
        
        # 파이 차트 - 부수 점유율
        col1, col2 = st.columns(2)
        
        with col1:
            fig3 = px.pie(
                summary_df,
                values='총주문부수',
                names='담당자',
                title="주문 부수 점유율",
                hole=0.4
            )
            fig3.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig3, use_container_width=True)
        
        with col2:
            fig4 = px.pie(
                summary_df,
                values='총주문금액',
                names='담당자',
                title="주문 금액 점유율",
                hole=0.4
            )
            fig4.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig4, use_container_width=True)
        
        # 효율성 분석
        st.markdown("---")
        st.subheader("📊 효율성 지표")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # 학교당 평균 주문 부수
            summary_df['학교당평균부수'] = summary_df['총주문부수'] / summary_df['주문학교수'].replace(0, 1)
            fig5 = px.bar(
                summary_df,
                x='담당자',
                y='학교당평균부수',
                title="학교당 평균 주문 부수",
                color='담당자',
                text='학교당평균부수'
            )
            fig5.update_traces(texttemplate='%{text:.0f}', textposition='outside')
            fig5.update_layout(showlegend=False)
            st.plotly_chart(fig5, use_container_width=True)
        
        with col2:
            # 학교당 평균 금액
            summary_df['학교당평균금액'] = summary_df['총주문금액'] / summary_df['주문학교수'].replace(0, 1)
            fig6 = px.bar(
                summary_df,
                x='담당자',
                y='학교당평균금액',
                title="학교당 평균 주문 금액",
                color='담당자',
                text='학교당평균금액'
            )
            fig6.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig6.update_layout(showlegend=False)
            st.plotly_chart(fig6, use_container_width=True)
        
        with col3:
            # 시장점유율 (주문부수/시장규모)
            summary_df['시장점유율(%)'] = (summary_df['총주문부수'] / summary_df['시장규모'].replace(0, 1)) * 100
            fig7 = px.bar(
                summary_df,
                x='담당자',
                y='시장점유율(%)',
                title="시장 점유율",
                color='담당자',
                text='시장점유율(%)'
            )
            fig7.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig7.update_layout(showlegend=False)
            st.plotly_chart(fig7, use_container_width=True)
    
    with tab3:
        st.subheader("🗺️ 담당자별 지역 분포")
        
        # 담당자별 시도 분포
        if '시도명' in filtered_order.columns:
            for manager in selected_managers:
                with st.expander(f"📍 {manager} - 지역별 상세", expanded=True):
                    mgr_order = filtered_order[filtered_order['본사담당자(2025.09)'] == manager]
                    
                    region_summary = mgr_order.groupby('시도명').agg({
                        '부수': 'sum',
                        school_code_col: 'nunique' if school_code_col in mgr_order.columns else lambda x: 0,
                        '금액': 'sum' if '금액' in mgr_order.columns else lambda x: 0
                    }).reset_index()
                    region_summary.columns = ['시도명', '주문부수', '학교수', '주문금액']
                    region_summary = region_summary.sort_values('주문부수', ascending=False)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig_region = px.bar(
                            region_summary,
                            x='주문부수',
                            y='시도명',
                            orientation='h',
                            title=f"{manager} - 시도별 주문 부수",
                            color='주문부수',
                            color_continuous_scale='Blues'
                        )
                        fig_region.update_layout(yaxis={'categoryorder': 'total ascending'}, height=400)
                        st.plotly_chart(fig_region, use_container_width=True)
                    
                    with col2:
                        fig_schools = px.bar(
                            region_summary,
                            x='학교수',
                            y='시도명',
                            orientation='h',
                            title=f"{manager} - 시도별 학교 수",
                            color='학교수',
                            color_continuous_scale='Greens'
                        )
                        fig_schools.update_layout(yaxis={'categoryorder': 'total ascending'}, height=400)
                        st.plotly_chart(fig_schools, use_container_width=True)
                    
                    st.dataframe(
                        region_summary.style.format({
                            '주문부수': '{:,.0f}',
                            '학교수': '{:,.0f}',
                            '주문금액': '{:,.0f}'
                        }),
                        use_container_width=True
                    )
    
    with tab4:
        st.subheader("📚 담당자별 과목 분석")
        
        if '과목명' in filtered_order.columns:
            # 담당자별 Top 과목
            for manager in selected_managers:
                with st.expander(f"📖 {manager} - 과목별 주문 현황", expanded=True):
                    mgr_order = filtered_order[filtered_order['본사담당자(2025.09)'] == manager]
                    
                    subject_summary = mgr_order.groupby('과목명').agg({
                        '부수': 'sum',
                        school_code_col: 'nunique' if school_code_col in mgr_order.columns else lambda x: 0
                    }).reset_index()
                    subject_summary.columns = ['과목명', '주문부수', '학교수']
                    subject_summary = subject_summary.sort_values('주문부수', ascending=False).head(15)
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        fig_subject = px.bar(
                            subject_summary,
                            x='주문부수',
                            y='과목명',
                            orientation='h',
                            title=f"{manager} - Top 15 과목별 주문",
                            color='주문부수',
                            color_continuous_scale='Viridis'
                        )
                        fig_subject.update_layout(yaxis={'categoryorder': 'total ascending'}, height=500)
                        st.plotly_chart(fig_subject, use_container_width=True)
                    
                    with col2:
                        st.dataframe(
                            subject_summary.style.format({
                                '주문부수': '{:,.0f}',
                                '학교수': '{:,.0f}'
                            }),
                            use_container_width=True,
                            height=500
                        )
        
        # 담당자간 과목 비교
        st.markdown("---")
        st.subheader("📊 담당자간 주요 과목 비교")
        
        if '과목명' in filtered_order.columns:
            # 상위 10개 과목 선정
            top_subjects = filtered_order.groupby('과목명')['부수'].sum().nlargest(10).index
            
            comparison_data = []
            for manager in selected_managers:
                mgr_order = filtered_order[filtered_order['본사담당자(2025.09)'] == manager]
                for subject in top_subjects:
                    subj_data = mgr_order[mgr_order['과목명'] == subject]
                    comparison_data.append({
                        '담당자': manager,
                        '과목명': subject,
                        '주문부수': subj_data['부수'].sum()
                    })
            
            comparison_df = pd.DataFrame(comparison_data)
            
            fig_comp = px.bar(
                comparison_df,
                x='과목명',
                y='주문부수',
                color='담당자',
                barmode='group',
                title="담당자별 주요 과목 주문 비교",
                height=500
            )
            fig_comp.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_comp, use_container_width=True)
    
    # ===== 학교급별 분석 =====
    st.markdown("---")
    st.header("🏫 학교급별 담당자 성과")
    
    if '학교급' in filtered_order.columns:
        school_level_data = []
        for manager in selected_managers:
            mgr_order = filtered_order[filtered_order['본사담당자(2025.09)'] == manager]
            for level in ['초등학교', '중학교', '고등학교']:
                level_data = mgr_order[mgr_order['학교급'] == level]
                school_level_data.append({
                    '담당자': manager,
                    '학교급': level,
                    '주문부수': level_data['부수'].sum(),
                    '학교수': level_data[school_code_col].nunique() if school_code_col in level_data.columns else 0
                })
        
        level_df = pd.DataFrame(school_level_data)
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_level1 = px.bar(
                level_df,
                x='학교급',
                y='주문부수',
                color='담당자',
                barmode='group',
                title="담당자별 학교급 주문 부수",
                text='주문부수'
            )
            fig_level1.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            st.plotly_chart(fig_level1, use_container_width=True)
        
        with col2:
            fig_level2 = px.bar(
                level_df,
                x='학교급',
                y='학교수',
                color='담당자',
                barmode='group',
                title="담당자별 학교급 학교 수",
                text='학교수'
            )
            fig_level2.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            st.plotly_chart(fig_level2, use_container_width=True)
    
    # ===== 시계열 분석 (학년도별) =====
    if '학년도' in filtered_order.columns:
        st.markdown("---")
        st.header("📅 연도별 추이 분석")
        
        year_data = []
        for manager in selected_managers:
            mgr_order = filtered_order[filtered_order['본사담당자(2025.09)'] == manager]
            for year in sorted(mgr_order['학년도'].unique()):
                year_order = mgr_order[mgr_order['학년도'] == year]
                year_data.append({
                    '담당자': manager,
                    '학년도': year,
                    '주문부수': year_order['부수'].sum(),
                    '주문금액': year_order['금액'].sum() if '금액' in year_order.columns else 0
                })
        
        year_df = pd.DataFrame(year_data)
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_year1 = px.line(
                year_df,
                x='학년도',
                y='주문부수',
                color='담당자',
                markers=True,
                title="담당자별 연도별 주문 부수 추이"
            )
            st.plotly_chart(fig_year1, use_container_width=True)
        
        with col2:
            fig_year2 = px.line(
                year_df,
                x='학년도',
                y='주문금액',
                color='담당자',
                markers=True,
                title="담당자별 연도별 주문 금액 추이"
            )
            st.plotly_chart(fig_year2, use_container_width=True)

else:
    st.error("본사담당자 정보가 없습니다. 학생수 데이터에 '본사담당자(2025.09)' 컬럼이 필요합니다.")
