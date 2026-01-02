import streamlit as st
from utils.style import apply_custom_style
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from typing import cast
from utils.year_filter import add_year_filter_sidebar, filter_by_years, create_year_comparison_metrics
from utils.market_share_calculator import calculate_both_shares, compare_year_shares

st.set_page_config(page_title="수도권/지방 분석", page_icon="🗺️", layout="wide")
apply_custom_style()

# Get data
if 'order_df' not in st.session_state or 'total_df' not in st.session_state:
    st.error("데이터를 불러올 수 없습니다. 메인 페이지로 돌아가주세요.")
    st.stop()

order_df_orig = st.session_state.get('order_df', pd.DataFrame()).copy()
total_df = st.session_state.get('total_df', pd.DataFrame()).copy()

# 학년도 필터 추가
selected_years, comparison_mode = add_year_filter_sidebar(order_df_orig, default_year='2026')
if selected_years:
    order_df = filter_by_years(order_df_orig, selected_years)
else:
    order_df = order_df_orig

st.title("🗺️ 수도권/지방 분석")
st.markdown("---")

# 수도권 정의: 서울, 인천, 경기
METROPOLITAN_AREAS = ['서울특별시', '인천광역시', '경기도']

# 시도명 또는 시도교육청 컬럼으로 수도권/지방 구분 (양쪽 모두 대응)
region_col_order = None
if '시도명' in order_df.columns:
    region_col_order = '시도명'
elif '시도교육청' in order_df.columns:
    region_col_order = '시도교육청'

if region_col_order:
    order_df['지역구분'] = order_df[region_col_order].apply(
        lambda x: '수도권' if any(area in str(x) for area in METROPOLITAN_AREAS) else '지방'
    )

# total_df may use a different column name; prefer '시도명' then '시도교육청'
region_col_total = None
if '시도명' in total_df.columns:
    region_col_total = '시도명'
elif '시도교육청' in total_df.columns:
    region_col_total = '시도교육청'

if region_col_total:
    total_df['지역구분'] = total_df[region_col_total].apply(
        lambda x: '수도권' if any(area in str(x) for area in METROPOLITAN_AREAS) else '지방'
    )
    
    # Sidebar - 지역 선택
    st.sidebar.header("🔍 지역 선택")
    region_options = ['전체', '수도권', '지방']
    selected_region = st.sidebar.radio("지역 구분", region_options)
    
    # 필터링
    if selected_region == '수도권':
        filtered_order = order_df[order_df['지역구분'] == '수도권'].copy()
        filtered_total = total_df[total_df['지역구분'] == '수도권'].copy() if '지역구분' in total_df.columns else total_df.copy()
    elif selected_region == '지방':
        filtered_order = order_df[order_df['지역구분'] == '지방'].copy()
        filtered_total = total_df[total_df['지역구분'] == '지방'].copy() if '지역구분' in total_df.columns else total_df.copy()
    else:
        filtered_order = order_df.copy()
        filtered_total = total_df.copy()
    
    school_code_col = '정보공시학교코드' if '정보공시학교코드' in filtered_order.columns else '학교코드'
    
    # ===== 전체 요약 통계 =====
    st.header(f"📊 {selected_region} 요약")
    
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
        total_market = filtered_total['학생수(계)'].sum() if '학생수(계)' in filtered_total.columns else 0
        st.metric("시장 규모", f"{total_market:,.0f}명")
    
    st.markdown("---")
    
    # ===== 수도권 vs 지방 비교 =====
    st.header("🔄 수도권 vs 지방 비교")
    
    # 비교 데이터 생성
    metro_order = order_df[order_df['지역구분'] == '수도권']
    local_order = order_df[order_df['지역구분'] == '지방']
    metro_total = total_df[total_df['지역구분'] == '수도권'] if '지역구분' in total_df.columns else pd.DataFrame()
    local_total = total_df[total_df['지역구분'] == '지방'] if '지역구분' in total_df.columns else pd.DataFrame()
    
    comparison_data = {
        '구분': ['수도권', '지방'],
        '주문부수': [metro_order['부수'].sum(), local_order['부수'].sum()],
        '주문금액': [
            metro_order['금액'].sum() if '금액' in metro_order.columns else 0,
            local_order['금액'].sum() if '금액' in local_order.columns else 0
        ],
        '학교수': [
            metro_order[school_code_col].nunique() if school_code_col in metro_order.columns else 0,
            local_order[school_code_col].nunique() if school_code_col in local_order.columns else 0
        ],
        '시장규모': [
            metro_total['학생수(계)'].sum() if not metro_total.empty and '학생수(계)' in metro_total.columns else 0,
            local_total['학생수(계)'].sum() if not local_total.empty and '학생수(계)' in local_total.columns else 0
        ],
        '과목수': [
            metro_order['과목명'].nunique() if '과목명' in metro_order.columns else 0,
            local_order['과목명'].nunique() if '과목명' in local_order.columns else 0
        ],
        '총판수': [
            metro_order['총판'].nunique() if '총판' in metro_order.columns else 0,
            local_order['총판'].nunique() if '총판' in local_order.columns else 0
        ]
    }
    
    comp_df = pd.DataFrame(comparison_data)
    # 숫자형 보장: Pylance와 런타임 오류 방지
    for col in ['주문부수', '주문금액', '학교수', '시장규모', '과목수', '총판수']:
        if col in comp_df.columns:
            comp_df[col] = pd.to_numeric(comp_df[col], errors='coerce').fillna(0).astype(float)
    
    # 비교 차트
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 기본 비교", "🎯 점유율 분석", "📈 효율성 지표", "🗺️ 상세 지역", "📚 과목 분석"])
    
    with tab1:
        st.subheader("📊 수도권 vs 지방 주요 지표")
        
        # 메트릭 비교
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🏙️ 수도권")
            metro_orders = cast(float, comp_df.loc[0, '주문부수'])
            metro_amount = cast(float, comp_df.loc[0, '주문금액'])
            metro_schools = cast(float, comp_df.loc[0, '학교수'])
            metro_market = cast(float, comp_df.loc[0, '시장규모'])
            st.metric("주문 부수", f"{metro_orders:,.0f}부")
            st.metric("주문 금액", f"{(metro_amount/1000000):.1f}백만원")
            st.metric("학교 수", f"{metro_schools:,.0f}개")
            st.metric("시장 규모", f"{metro_market:,.0f}명")
        
        with col2:
            st.markdown("### 🌄 지방")
            local_orders = cast(float, comp_df.loc[1, '주문부수'])
            local_amount = cast(float, comp_df.loc[1, '주문금액'])
            local_schools = cast(float, comp_df.loc[1, '학교수'])
            local_market = cast(float, comp_df.loc[1, '시장규모'])
            st.metric("주문 부수", f"{local_orders:,.0f}부")
            st.metric("주문 금액", f"{(local_amount/1000000):.1f}백만원")
            st.metric("학교 수", f"{local_schools:,.0f}개")
            st.metric("시장 규모", f"{local_market:,.0f}명")
        
        st.markdown("---")
        
        # 비교 차트
        col1, col2 = st.columns(2)
        
        with col1:
            fig1 = px.bar(
                comp_df,
                x='구분',
                y='주문부수',
                title="주문 부수 비교",
                color='구분',
                text='주문부수',
                color_discrete_map={'수도권': '#1f77b4', '지방': '#ff7f0e'}
            )
            fig1.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig1.update_layout(showlegend=False)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            fig2 = px.bar(
                comp_df,
                x='구분',
                y='학교수',
                title="학교 수 비교",
                color='구분',
                text='학교수',
                color_discrete_map={'수도권': '#1f77b4', '지방': '#ff7f0e'}
            )
            fig2.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig2.update_layout(showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)
        
        # 상세 테이블
        st.subheader("📋 비교 통계 테이블")
        st.dataframe(
            comp_df.style.format({
                '주문부수': '{:,.0f}',
                '주문금액': '{:,.0f}',
                '학교수': '{:,.0f}',
                '시장규모': '{:,.0f}',
                '과목수': '{:.0f}',
                '총판수': '{:.0f}'
            }).background_gradient(cmap='RdYlGn'),
            use_container_width=True
        )
    
    with tab2:
        st.subheader("🎯 점유율 및 비율 분석")
        
        # 파이 차트
        col1, col2 = st.columns(2)
        
        with col1:
            fig3 = px.pie(
                comp_df,
                values='주문부수',
                names='구분',
                title="주문 부수 점유율",
                hole=0.4,
                color='구분',
                color_discrete_map={'수도권': '#1f77b4', '지방': '#ff7f0e'}
            )
            fig3.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig3, use_container_width=True)
        
        with col2:
            fig4 = px.pie(
                comp_df,
                values='주문금액',
                names='구분',
                title="주문 금액 점유율",
                hole=0.4,
                color='구분',
                color_discrete_map={'수도권': '#1f77b4', '지방': '#ff7f0e'}
            )
            fig4.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig4, use_container_width=True)
        
        st.markdown("---")
        
        col3, col4 = st.columns(2)
        
        with col3:
            fig5 = px.pie(
                comp_df,
                values='시장규모',
                names='구분',
                title="시장 규모 비율",
                hole=0.4,
                color='구분',
                color_discrete_map={'수도권': '#1f77b4', '지방': '#ff7f0e'}
            )
            fig5.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig5, use_container_width=True)
        
        with col4:
            fig6 = px.pie(
                comp_df,
                values='학교수',
                names='구분',
                title="학교 수 비율",
                hole=0.4,
                color='구분',
                color_discrete_map={'수도권': '#1f77b4', '지방': '#ff7f0e'}
            )
            fig6.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig6, use_container_width=True)
    
    with tab3:
        st.subheader("📈 효율성 지표")
        
        # 효율성 계산
        comp_df['학교당평균부수'] = pd.to_numeric(comp_df['주문부수'], errors='coerce').fillna(0).astype(float) / pd.to_numeric(comp_df['학교수'].replace(0, 1), errors='coerce').fillna(0).astype(float)
        comp_df['학교당평균금액'] = pd.to_numeric(comp_df['주문금액'], errors='coerce').fillna(0).astype(float) / pd.to_numeric(comp_df['학교수'].replace(0, 1), errors='coerce').fillna(0).astype(float)
        comp_df['시장점유율(%)'] = (pd.to_numeric(comp_df['주문부수'], errors='coerce').fillna(0).astype(float) / pd.to_numeric(comp_df['시장규모'].replace(0, 1), errors='coerce').fillna(0).astype(float)) * 100
        comp_df['평균단가'] = pd.to_numeric(comp_df['주문금액'], errors='coerce').fillna(0).astype(float) / pd.to_numeric(comp_df['주문부수'].replace(0, 1), errors='coerce').fillna(0).astype(float)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            fig7 = px.bar(
                comp_df,
                x='구분',
                y='학교당평균부수',
                title="학교당 평균 주문 부수",
                color='구분',
                text='학교당평균부수',
                color_discrete_map={'수도권': '#1f77b4', '지방': '#ff7f0e'}
            )
            fig7.update_traces(texttemplate='%{text:.0f}', textposition='outside')
            fig7.update_layout(showlegend=False)
            st.plotly_chart(fig7, use_container_width=True)
        
        with col2:
            fig8 = px.bar(
                comp_df,
                x='구분',
                y='학교당평균금액',
                title="학교당 평균 주문 금액",
                color='구분',
                text='학교당평균금액',
                color_discrete_map={'수도권': '#1f77b4', '지방': '#ff7f0e'}
            )
            fig8.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig8.update_layout(showlegend=False)
            st.plotly_chart(fig8, use_container_width=True)
        
        with col3:
            fig9 = px.bar(
                comp_df,
                x='구분',
                y='시장점유율(%)',
                title="시장 점유율",
                color='구분',
                text='시장점유율(%)',
                color_discrete_map={'수도권': '#1f77b4', '지방': '#ff7f0e'}
            )
            fig9.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
            fig9.update_layout(showlegend=False)
            st.plotly_chart(fig9, use_container_width=True)
        
        st.markdown("---")
        
        # 효율성 테이블
        st.subheader("📊 효율성 지표 상세")
        efficiency_df = comp_df[['구분', '학교당평균부수', '학교당평균금액', '시장점유율(%)', '평균단가']].copy()
        st.dataframe(
            efficiency_df.style.format({
                '학교당평균부수': '{:.0f}',
                '학교당평균금액': '{:,.0f}',
                '시장점유율(%)': '{:.2f}',
                '평균단가': '{:,.0f}'
            }).background_gradient(cmap='YlGn'),
            use_container_width=True
        )
    
    with tab4:
        st.subheader("🗺️ 지역별 상세 분석")
        
        # 수도권 vs 지방의 시도별 상세
        region_detail = order_df.groupby(['지역구분', '시도명']).agg({
            '부수': 'sum',
            school_code_col: 'nunique' if school_code_col in order_df.columns else lambda x: 0,
            '금액': 'sum' if '금액' in order_df.columns else lambda x: 0
        }).reset_index()
        region_detail.columns = ['지역구분', '시도명', '주문부수', '학교수', '주문금액']
        region_detail = region_detail.sort_values(['지역구분', '주문부수'], ascending=[True, False])
        
        # 수도권 상세
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🏙️ 수도권 시도별")
            metro_detail = region_detail[region_detail['지역구분'] == '수도권']
            
            fig10 = px.bar(
                metro_detail,
                x='주문부수',
                y='시도명',
                orientation='h',
                title="수도권 시도별 주문 부수",
                color='주문부수',
                color_continuous_scale='Blues',
                text='주문부수'
            )
            fig10.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig10.update_layout(yaxis={'categoryorder': 'total ascending'}, height=300)
            st.plotly_chart(fig10, use_container_width=True)
            
            st.dataframe(
                metro_detail[['시도명', '주문부수', '학교수', '주문금액']].style.format({
                    '주문부수': '{:,.0f}',
                    '학교수': '{:,.0f}',
                    '주문금액': '{:,.0f}'
                }),
                use_container_width=True
            )
        
        with col2:
            st.markdown("### 🌄 지방 주요 시도")
            local_detail = region_detail[region_detail['지역구분'] == '지방'].head(10)
            
            fig11 = px.bar(
                local_detail,
                x='주문부수',
                y='시도명',
                orientation='h',
                title="지방 시도별 주문 부수 TOP 10",
                color='주문부수',
                color_continuous_scale='Oranges',
                text='주문부수'
            )
            fig11.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig11.update_layout(yaxis={'categoryorder': 'total ascending'}, height=300)
            st.plotly_chart(fig11, use_container_width=True)
            
            st.dataframe(
                local_detail[['시도명', '주문부수', '학교수', '주문금액']].style.format({
                    '주문부수': '{:,.0f}',
                    '학교수': '{:,.0f}',
                    '주문금액': '{:,.0f}'
                }),
                use_container_width=True
            )
        
        # 전체 시도별 맵
        st.markdown("---")
        st.subheader("📍 전국 시도별 분포")
        
        fig_map = px.bar(
            region_detail,
            x='시도명',
            y='주문부수',
            color='지역구분',
            title="시도별 주문 부수 (수도권 vs 지방)",
            color_discrete_map={'수도권': '#1f77b4', '지방': '#ff7f0e'},
            height=500
        )
        fig_map.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_map, use_container_width=True)
    
    with tab5:
        st.subheader("📚 과목별 분석")
        
        subject_col = '교과서명_구분' if '교과서명_구분' in order_df.columns else '과목명'
        if subject_col in order_df.columns:
            # 수도권 vs 지방 과목 비교
            subject_comparison = []
            
            # 상위 15개 과목 선정
            top_subjects = order_df.groupby(subject_col)['부수'].sum().nlargest(15).index
            
            for subject in top_subjects:
                metro_subj = metro_order[metro_order[subject_col] == subject]
                local_subj = local_order[local_order[subject_col] == subject]
                
                subject_comparison.append({
                    '과목명': subject,
                    '구분': '수도권',
                    '주문부수': metro_subj['부수'].sum(),
                    '학교수': metro_subj[school_code_col].nunique() if school_code_col in metro_subj.columns else 0
                })
                
                subject_comparison.append({
                    '과목명': subject,
                    '구분': '지방',
                    '주문부수': local_subj['부수'].sum(),
                    '학교수': local_subj[school_code_col].nunique() if school_code_col in local_subj.columns else 0
                })
            
            subject_comp_df = pd.DataFrame(subject_comparison)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig12 = px.bar(
                    subject_comp_df,
                    x='과목명',
                    y='주문부수',
                    color='구분',
                    barmode='group',
                    title="Top 15 과목: 수도권 vs 지방 주문 비교",
                    color_discrete_map={'수도권': '#1f77b4', '지방': '#ff7f0e'},
                    height=500
                )
                fig12.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig12, use_container_width=True)
            
            with col2:
                # 과목별 수도권 비율
                subject_ratio = subject_comp_df.pivot_table(
                    index='과목명',
                    columns='구분',
                    values='주문부수',
                    fill_value=0
                ).reset_index()
                
                if '수도권' in subject_ratio.columns and '지방' in subject_ratio.columns:
                    subject_ratio['수도권비율(%)'] = (
                        subject_ratio['수도권'] / (subject_ratio['수도권'] + subject_ratio['지방']).replace(0, 1)
                    ) * 100
                    subject_ratio = subject_ratio.sort_values('수도권비율(%)', ascending=False)
                    
                    st.dataframe(
                        subject_ratio[['과목명', '수도권비율(%)']].style.format({
                            '수도권비율(%)': '{:.1f}'
                        }).background_gradient(subset=['수도권비율(%)'], cmap='RdYlGn'),
                        use_container_width=True,
                        height=500
                    )
    
    # ===== 학교급별 비교 =====
    st.markdown("---")
    st.header("🏫 학교급별 수도권/지방 비교")
    
    if '학교급' in order_df.columns:
        school_level_comp = []
        
        for level in ['초등학교', '중학교', '고등학교']:
            metro_level = metro_order[metro_order['학교급'] == level]
            local_level = local_order[local_order['학교급'] == level]
            
            school_level_comp.append({
                '학교급': level,
                '구분': '수도권',
                '주문부수': metro_level['부수'].sum(),
                '학교수': metro_level[school_code_col].nunique() if school_code_col in metro_level.columns else 0
            })
            
            school_level_comp.append({
                '학교급': level,
                '구분': '지방',
                '주문부수': local_level['부수'].sum(),
                '학교수': local_level[school_code_col].nunique() if school_code_col in local_level.columns else 0
            })
        
        level_comp_df = pd.DataFrame(school_level_comp)
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig13 = px.bar(
                level_comp_df,
                x='학교급',
                y='주문부수',
                color='구분',
                barmode='group',
                title="학교급별 주문 부수: 수도권 vs 지방",
                color_discrete_map={'수도권': '#1f77b4', '지방': '#ff7f0e'},
                text='주문부수'
            )
            fig13.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            st.plotly_chart(fig13, use_container_width=True)
        
        with col2:
            fig14 = px.bar(
                level_comp_df,
                x='학교급',
                y='학교수',
                color='구분',
                barmode='group',
                title="학교급별 학교 수: 수도권 vs 지방",
                color_discrete_map={'수도권': '#1f77b4', '지방': '#ff7f0e'},
                text='학교수'
            )
            fig14.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            st.plotly_chart(fig14, use_container_width=True)
    
    # ===== 시계열 분석 =====
    if '학년도' in order_df.columns:
        st.markdown("---")
        st.header("📅 연도별 추이")
        
        year_trend = []
        for year in sorted(order_df['학년도'].unique()):
            metro_year = metro_order[metro_order['학년도'] == year]
            local_year = local_order[local_order['학년도'] == year]
            
            year_trend.append({
                '학년도': year,
                '구분': '수도권',
                '주문부수': metro_year['부수'].sum(),
                '주문금액': metro_year['금액'].sum() if '금액' in metro_year.columns else 0
            })
            
            year_trend.append({
                '학년도': year,
                '구분': '지방',
                '주문부수': local_year['부수'].sum(),
                '주문금액': local_year['금액'].sum() if '금액' in local_year.columns else 0
            })
        
        trend_df = pd.DataFrame(year_trend)
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig15 = px.line(
                trend_df,
                x='학년도',
                y='주문부수',
                color='구분',
                markers=True,
                title="연도별 주문 부수 추이",
                color_discrete_map={'수도권': '#1f77b4', '지방': '#ff7f0e'}
            )
            st.plotly_chart(fig15, use_container_width=True)
        
        with col2:
            fig16 = px.line(
                trend_df,
                x='학년도',
                y='주문금액',
                color='구분',
                markers=True,
                title="연도별 주문 금액 추이",
                color_discrete_map={'수도권': '#1f77b4', '지방': '#ff7f0e'}
            )
            st.plotly_chart(fig16, use_container_width=True)

else:
    st.error("시도명 정보가 없습니다. 데이터에 '시도명' 컬럼이 필요합니다.")
