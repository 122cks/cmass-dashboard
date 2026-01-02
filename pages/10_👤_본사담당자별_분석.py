import streamlit as st
from utils.style import apply_custom_style
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from utils.year_filter import add_year_filter_sidebar, filter_by_years, create_year_comparison_metrics

st.set_page_config(page_title="본사담당자별 분석", page_icon="👤", layout="wide")
apply_custom_style()

# Get data
if 'order_df' not in st.session_state or 'total_df' not in st.session_state:
    st.error("데이터를 불러올 수 없습니다. 메인 페이지로 돌아가주세요.")
    st.stop()

order_df_orig = st.session_state.get('order_df', pd.DataFrame()).copy()
total_df = st.session_state.get('total_df', pd.DataFrame()).copy()
product_df = st.session_state.get('product_df', pd.DataFrame()).copy()

# 학년도 필터 추가
selected_years, comparison_mode = add_year_filter_sidebar(order_df_orig, default_year='2026')
if selected_years:
    order_df = filter_by_years(order_df_orig, selected_years)
else:
    order_df = order_df_orig

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
    # 회사 전체(선택된 연도 기준) 주문/금액 합계 (비교용)
    total_orders_all = order_df['부수'].sum() if '부수' in order_df.columns else 0
    total_amount_all = order_df['금액'].sum() if '금액' in order_df.columns else 0
    
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
        
        # 주문한 학교들의 코드 추출
        ordered_schools = mgr_order[school_code_col].unique() if school_code_col in mgr_order.columns else []
        
        # 주문한 학교들의 학생수 합계 (total_df에서 해당 학교들의 학생수 추출)
        ordered_schools_student_count = 0
        if len(ordered_schools) > 0 and '학생수(계)' in mgr_total.columns:
            ordered_schools_student_count = mgr_total[
                mgr_total['정보공시 학교코드'].isin(ordered_schools)
            ]['학생수(계)'].sum()
        
        summary = {
            '담당자': manager,
            '담당학교수': mgr_total['정보공시 학교코드'].nunique(),
            '채택학교수': len(ordered_schools),
            '담당학생수': mgr_total['학생수(계)'].sum() if '학생수(계)' in mgr_total.columns else 0,
            '채택학교학생수': ordered_schools_student_count,
            '총주문부수': mgr_order['부수'].sum(),
            '총주문금액': mgr_order['금액'].sum() if '금액' in mgr_order.columns else 0,
            '과목수': mgr_order['과목명'].nunique() if '과목명' in mgr_order.columns else 0,
            '총판수': mgr_order['총판'].nunique() if '총판' in mgr_order.columns else 0
        }
        
        # 학교 점유율 = 채택 학교수 / 담당 학교수
        if summary['담당학교수'] > 0:
            summary['학교점유율(%)'] = (summary['채택학교수'] / summary['담당학교수']) * 100
        else:
            summary['학교점유율(%)'] = 0
        
        # 학생수 점유율 = 채택 학교의 학생수 / 담당 지역 전체 학생수
        if summary['담당학생수'] > 0:
            summary['학생수점유율(%)'] = (summary['채택학교학생수'] / summary['담당학생수']) * 100
        else:
            summary['학생수점유율(%)'] = 0

        # 주문부수 기반: 학생수 대비 점유율 및 학생당 주문부수
        if summary['담당학생수'] > 0:
            summary['학생당부수'] = summary['총주문부수'] / summary['담당학생수']
            # 학생수 대비 점유율(%) = (총주문부수 / 담당학생수) * 100
            summary['학생수대비부수점유율(%)'] = (summary['총주문부수'] / summary['담당학생수']) * 100
        else:
            summary['학생당부수'] = 0
            summary['학생수대비부수점유율(%)'] = 0

        # 회사 전체 대비 점유율 (선택된 연도 기준 전체 주문 대비)
        if total_orders_all > 0:
            summary['회사주문점유율(%)'] = (summary['총주문부수'] / total_orders_all) * 100
        else:
            summary['회사주문점유율(%)'] = 0

        if total_amount_all > 0:
            summary['회사금액점유율(%)'] = (summary['총주문금액'] / total_amount_all) * 100
        else:
            summary['회사금액점유율(%)'] = 0

        manager_summary.append(summary)
    
    summary_df = pd.DataFrame(manager_summary)
    
    # 평균 계산 (전체 담당자 기준)
    avg_metrics = {
        '평균_총주문부수': summary_df['총주문부수'].mean(),
        '평균_학생수점유율': summary_df['학생수점유율(%)'].mean(),
        '평균_학교점유율': summary_df['학교점유율(%)'].mean(),
        '평균_학생당부수': summary_df['학생당부수'].mean(),
        '평균_채택학교수': summary_df['채택학교수'].mean()
    }
    
    # 담당자별 평균 대비 증감률 계산
    summary_df['주문부수_평균대비(%)'] = ((summary_df['총주문부수'] - avg_metrics['평균_총주문부수']) / avg_metrics['평균_총주문부수'] * 100).round(1)
    summary_df['학생수점유율_평균대비(%)'] = ((summary_df['학생수점유율(%)'] - avg_metrics['평균_학생수점유율']) / avg_metrics['평균_학생수점유율'] * 100).round(1)
    summary_df['학교점유율_평균대비(%)'] = ((summary_df['학교점유율(%)'] - avg_metrics['평균_학교점유율']) / avg_metrics['평균_학교점유율'] * 100).round(1)
    
    # 랭킹 계산
    summary_df['주문부수_순위'] = summary_df['총주문부수'].rank(ascending=False, method='min').astype(int)
    summary_df['학생수점유율_순위'] = summary_df['학생수점유율(%)'].rank(ascending=False, method='min').astype(int)
    summary_df['학교점유율_순위'] = summary_df['학교점유율(%)'].rank(ascending=False, method='min').astype(int)
    summary_df['학생당부수_순위'] = summary_df['학생당부수'].rank(ascending=False, method='min').astype(int)
    
    # 담당자 비교 차트
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 주요 지표 비교", "🎯 성과 분석", "🗺️ 지역별 인사이트", "📚 과목별 인사이트", "💡 액션 추천"])
    
    with tab1:
        st.subheader("📊 담당자별 주요 지표")
        
        # 메트릭 카드 - 학교/학생수 점유율 중심
        cols = st.columns(len(selected_managers))
        for idx_val, row in summary_df.iterrows():
            idx = int(idx_val) if isinstance(idx_val, (int, np.integer)) else 0
            with cols[idx]:
                st.markdown(f"### {row['담당자']}")
                
                # 핵심 KPI with 랭킹 배지
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.metric("🎯 학생수 점유율", f"{row['학생수점유율(%)']:.1f}%", 
                             delta=f"평균대비 {row['학생수점유율_평균대비(%)']:+.1f}%",
                             help=f"담당학생 {row['담당학생수']:,}명 중 채택학교 학생 {row['채택학교학생수']:,}명")
                with col_b:
                    rank = int(row['학생수점유율_순위'])
                    st.markdown(f"<div style='text-align:center; font-size:24px; font-weight:bold; color:{'#FF6B6B' if rank <= 3 else '#4ECDC4'};'>#{rank}</div>", unsafe_allow_html=True)
                
                col_c, col_d = st.columns([3, 1])
                with col_c:
                    st.metric("📚 주문 부수", f"{row['총주문부수']:,.0f}부",
                             delta=f"평균대비 {row['주문부수_평균대비(%)']:+.1f}%")
                with col_d:
                    rank = int(row['주문부수_순위'])
                    st.markdown(f"<div style='text-align:center; font-size:24px; font-weight:bold; color:{'#FF6B6B' if rank <= 3 else '#4ECDC4'};'>#{rank}</div>", unsafe_allow_html=True)
                
                st.metric("🏫 학교 점유율", f"{row['학교점유율(%)']:.1f}%", 
                         delta=f"평균대비 {row['학교점유율_평균대비(%)']:+.1f}%",
                         help=f"담당학교 {row['담당학교수']:,}개 중 채택학교 {row['채택학교수']:,}개")
                st.metric("👤 학생당 주문부수", f"{row.get('학생당부수', 0):.3f}부/명", 
                         help=f"순위: #{int(row['학생당부수_순위'])}")
                st.metric("📊 담당 학생수", f"{row['담당학생수']:,.0f}명", help="담당 지역 총 학생수")
        
        st.markdown("---")
        
        # 비교 차트 - 학생수/학교 점유율 중심
        col1, col2 = st.columns(2)
        
        with col1:
            fig1 = px.bar(
                summary_df,
                x='담당자',
                y='학생수점유율(%)',
                title="⭐ 담당자별 학생수 점유율 (채택학교 학생수 기준)",
                color='학생수점유율(%)',
                color_continuous_scale='RdYlGn',
                text='학생수점유율(%)'
            )
            fig1.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig1.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig1, use_container_width=True)
            st.caption("📌 담당 지역 전체 학생수 대비 채택한 학교들의 학생수 비율")
        
        with col2:
            fig2 = px.bar(
                summary_df,
                x='담당자',
                y='학교점유율(%)',
                title="담당자별 학교 점유율 (채택학교수 기준)",
                color='학교점유율(%)',
                color_continuous_scale='Blues',
                text='학교점유율(%)'
            )
            fig2.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig2.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("📌 담당 학교수 대비 채택한 학교수 비율")
        
        # 상세 테이블
        st.subheader("📋 담당자별 상세 통계 (학생수 점유율 기준 정렬)")
        display_df = summary_df.copy()
        display_df = display_df.sort_values('학생수점유율(%)', ascending=False)
        
        # 컬럼 순서 재배열 - 중요한 지표를 앞으로
        column_order = ['담당자', '학생수점유율(%)', '학생수대비부수점유율(%)', '학생당부수', '학교점유율(%)', '채택학교학생수', '담당학생수', 
                   '채택학교수', '담당학교수', '총주문부수', '회사주문점유율(%)', '총주문금액', '회사금액점유율(%)', '과목수', '총판수']
        display_df = display_df[column_order]
        
        st.dataframe(
            display_df.style.format({
                '담당학교수': '{:,.0f}',
                '채택학교수': '{:,.0f}',
                '담당학생수': '{:,.0f}',
                '채택학교학생수': '{:,.0f}',
                '총주문부수': '{:,.0f}',
                '총주문금액': '{:,.0f}',
                '과목수': '{:.0f}',
                '총판수': '{:.0f}',
                '학교점유율(%)': '{:.1f}',
                '학생수점유율(%)': '{:.2f}',
                '학생수대비부수점유율(%)': '{:.2f}',
                '학생당부수': '{:.3f}',
                '회사주문점유율(%)': '{:.2f}',
                '회사금액점유율(%)': '{:.2f}'
            }).background_gradient(subset=['학생수점유율(%)', '학교점유율(%)'], cmap='RdYlGn'),
            use_container_width=True,
            height=200
        )
        st.info("💡 **학생수점유율**은 담당 지역 전체 학생수 대비 채택한 학교들의 학생수 비율입니다. **학교점유율**은 담당 학교수 대비 채택한 학교수 비율입니다.")
    
    with tab2:
        st.subheader("🎯 성과 분석")
        
        st.info("""💡 **성과 평가 기준**
        - **학생수 점유율**: 담당 지역 학생수 대비 채택학교 학생수 비율 (공정한 비교 지표)
        - **학교 점유율**: 담당 학교수 대비 채택 학교수 비율
        - **절대 주문량**: 전체 매출 기여도 파악
        """)
        
        # 학생수 점유율 비교 - 가장 중요한 지표
        st.markdown("#### ⭐ 학생수 점유율 비교 (채택학교 학생수 기준)")
        fig_student = px.bar(
            summary_df.sort_values('학생수점유율(%)', ascending=True),
            y='담당자',
            x='학생수점유율(%)',
            orientation='h',
            title="담당자별 학생수 점유율 (담당 학생수 대비 채택학교 학생수)",
            color='학생수점유율(%)',
            color_continuous_scale='RdYlGn',
            text='학생수점유율(%)'
        )
        fig_student.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
        fig_student.update_layout(height=400)
        st.plotly_chart(fig_student, use_container_width=True)
        st.caption("📌 담당 지역 전체 학생수 대비 채택한 학교들의 학생수 비율 - 담당 규모가 달라도 공정한 비교")
        
        # 학교 점유율 비교
        st.markdown("#### 🏫 학교 점유율 비교 (채택 학교수 기준)")
        fig_school = px.bar(
            summary_df.sort_values('학교점유율(%)', ascending=True),
            y='담당자',
            x='학교점유율(%)',
            orientation='h',
            title="담당자별 학교 점유율 (담당 학교수 대비 채택 학교수)",
            color='학교점유율(%)',
            color_continuous_scale='Blues',
            text='학교점유율(%)'
        )
        fig_school.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
        fig_school.update_layout(height=400)
        st.plotly_chart(fig_school, use_container_width=True)
        st.caption("📌 담당 학교수 대비 채택한 학교수 비율 - 영업 커버리지 지표")
        
        st.markdown("---")
        
        # 파이 차트 - 절대 주문량
        st.markdown("#### 📊 절대 주문량 비교 (전체 매출 기여도)")
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
            st.caption("전체 매출 중 각 담당자의 기여도")
        
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
            st.caption("전체 매출액 중 각 담당자의 기여도")
        
        # 효율성 분석
        st.markdown("---")
        st.subheader("📊 효율성 지표 (학교당 평균)")
        st.caption("주문 받은 학교들의 평균적인 주문량 - 영업 집중도를 나타냄")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # 학교당 평균 주문 부수 (채택된 학교 기준)
            summary_df['학교당평균부수'] = summary_df['총주문부수'] / summary_df['채택학교수'].replace(0, 1)
            fig5 = px.bar(
                summary_df,
                x='담당자',
                y='학교당평균부수',
                title="학교당 평균 주문 부수",
                color='학교당평균부수',
                color_continuous_scale='Viridis',
                text='학교당평균부수'
            )
            fig5.update_traces(texttemplate='%{text:.0f}', textposition='outside')
            fig5.update_layout(showlegend=False)
            st.plotly_chart(fig5, use_container_width=True)
            st.caption("주문 받은 학교당 평균 부수")
        
        with col2:
            # 학교당 평균 금액 (채택된 학교 기준)
            summary_df['학교당평균금액'] = summary_df['총주문금액'] / summary_df['채택학교수'].replace(0, 1)
            fig6 = px.bar(
                summary_df,
                x='담당자',
                y='학교당평균금액',
                title="학교당 평균 주문 금액",
                color='학교당평균금액',
                color_continuous_scale='Oranges',
                text='학교당평균금액'
            )
            fig6.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig6.update_layout(showlegend=False)
            st.plotly_chart(fig6, use_container_width=True)
            st.caption("주문 받은 학교당 평균 금액")
        
        with col3:
            # 담당학교당 주문부수 (전체 담당 학교 기준)
            summary_df['담당학교당부수'] = summary_df['총주문부수'] / summary_df['담당학교수'].replace(0, 1)
            fig7 = px.bar(
                summary_df,
                x='담당자',
                y='담당학교당부수',
                title="담당 학교당 주문 부수",
                color='담당학교당부수',
                color_continuous_scale='Blues',
                text='담당학교당부수'
            )
            fig7.update_traces(texttemplate='%{text:.1f}', textposition='outside')
            fig7.update_layout(showlegend=False)
            st.plotly_chart(fig7, use_container_width=True)
            st.caption("전체 담당 학교 기준 평균 (미주문 학교 포함)")
    
    with tab3:
        st.subheader("🗺️ 지역별 인사이트 (담당자별 강점/약점 지역)")
        
        # 수도권 정의
        metro_regions = ['서울특별시', '인천광역시', '경기도']
        
        # 전체 지역별 점유율 계산
        if '시도명' in filtered_order.columns and '시도명' in filtered_total.columns:
            region_analysis = []
            
            for manager in selected_managers:
                mgr_total = filtered_total[filtered_total['본사담당자(2025.09)'] == manager]
                mgr_order = filtered_order[filtered_order['본사담당자(2025.09)'] == manager]
                
                for region in mgr_total['시도명'].unique():
                    region_total = mgr_total[mgr_total['시도명'] == region]
                    region_order = mgr_order[mgr_order['시도명'] == region]
                    
                    # 해당 지역의 담당 학생수
                    region_students = region_total['학생수(계)'].sum() if '학생수(계)' in region_total.columns else 0
                    # 해당 지역의 주문부수
                    region_orders = region_order['부수'].sum() if '부수' in region_order.columns else 0
                    # 해당 지역의 채택학교수
                    region_schools = region_order[school_code_col].nunique() if school_code_col in region_order.columns else 0
                    # 담당학교수
                    region_total_schools = region_total['정보공시 학교코드'].nunique()
                    
                    # 점유율 계산
                    school_share = (region_schools / region_total_schools * 100) if region_total_schools > 0 else 0
                    student_share = (region_orders / region_students * 100) if region_students > 0 else 0
                    
                    region_analysis.append({
                        '담당자': manager,
                        '지역': region,
                        '수도권여부': '수도권' if region in metro_regions else '지방',
                        '담당학생수': region_students,
                        '주문부수': region_orders,
                        '채택학교수': region_schools,
                        '담당학교수': region_total_schools,
                        '학교점유율(%)': school_share,
                        '학생대비주문율(%)': student_share
                    })
            
            region_df = pd.DataFrame(region_analysis)
            
            # 수도권 최고/최저 점유율
            st.markdown("#### 🏙️ 수도권 지역 점유율 분석")
            metro_df = region_df[region_df['수도권여부'] == '수도권'].copy()
            
            if not metro_df.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("##### 🔴 점유율 낮은 지역 TOP 5")
                    low_metro = metro_df.nsmallest(5, '학교점유율(%)')[['담당자', '지역', '학교점유율(%)', '학생대비주문율(%)', '채택학교수', '담당학교수']]
                    st.dataframe(
                        low_metro.style.format({
                            '학교점유율(%)': '{:.1f}',
                            '학생대비주문율(%)': '{:.2f}',
                            '채택학교수': '{:,.0f}',
                            '담당학교수': '{:,.0f}'
                        }).background_gradient(subset=['학교점유율(%)'], cmap='Reds_r'),
                        use_container_width=True
                    )
                    st.caption("⚠️ 집중 영업 필요 지역")
                
                with col2:
                    st.markdown("##### 🟢 점유율 높은 지역 TOP 5")
                    high_metro = metro_df.nlargest(5, '학교점유율(%)')[['담당자', '지역', '학교점유율(%)', '학생대비주문율(%)', '채택학교수', '담당학교수']]
                    st.dataframe(
                        high_metro.style.format({
                            '학교점유율(%)': '{:.1f}',
                            '학생대비주문율(%)': '{:.2f}',
                            '채택학교수': '{:,.0f}',
                            '담당학교수': '{:,.0f}'
                        }).background_gradient(subset=['학교점유율(%)'], cmap='Greens'),
                        use_container_width=True
                    )
                    st.caption("✅ 강점 지역 - 성공 전략 벤치마킹")
            
            # 담당자별 지역 히트맵
            st.markdown("---")
            st.markdown("#### 📊 담당자 × 지역 점유율 히트맵")
            
            pivot_region = region_df.pivot_table(
                index='담당자',
                columns='지역',
                values='학교점유율(%)',
                aggfunc='mean'
            ).fillna(0)
            
            fig_heatmap = px.imshow(
                pivot_region,
                labels=dict(x="지역", y="담당자", color="학교점유율(%)"),
                x=pivot_region.columns,
                y=pivot_region.index,
                color_continuous_scale='RdYlGn',
                aspect='auto',
                title="담당자별 지역 학교 점유율 히트맵"
            )
            fig_heatmap.update_layout(height=400)
            st.plotly_chart(fig_heatmap, use_container_width=True)
            st.caption("💡 진한 녹색: 높은 점유율 | 진한 빨강: 낮은 점유율 (집중 영업 필요)")
        
        # 담당자별 시도 분포 (기존 코드)
        st.markdown("---")
        st.markdown("#### 📍 담당자별 지역 상세 분포")
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
        st.subheader("📚 과목별 인사이트 (담당자별 강점/약점 과목)")
        
        if '과목명' in filtered_order.columns:
            # 전체 과목별 점유율 분석
            subject_analysis = []
            
            for manager in selected_managers:
                mgr_order = filtered_order[filtered_order['본사담당자(2025.09)'] == manager]
                
                for subject in mgr_order['과목명'].unique():
                    subj_data = mgr_order[mgr_order['과목명'] == subject]
                    subject_orders = subj_data['부수'].sum()
                    subject_schools = subj_data[school_code_col].nunique() if school_code_col in subj_data.columns else 0
                    
                    subject_analysis.append({
                        '담당자': manager,
                        '과목명': subject,
                        '주문부수': subject_orders,
                        '학교수': subject_schools
                    })
            
            subject_df = pd.DataFrame(subject_analysis)
            
            # 전체 과목별 평균 계산
            subject_avg = subject_df.groupby('과목명')['주문부수'].mean().reset_index()
            subject_avg.columns = ['과목명', '평균주문부수']
            
            subject_df = subject_df.merge(subject_avg, on='과목명', how='left')
            subject_df['평균대비(%)'] = ((subject_df['주문부수'] - subject_df['평균주문부수']) / subject_df['평균주문부수'] * 100).round(1)
            
            # 주요 과목 (전체 주문 기준 TOP 10)
            top_subjects = subject_df.groupby('과목명')['주문부수'].sum().nlargest(10).index
            top_subject_df = subject_df[subject_df['과목명'].isin(top_subjects)]
            
            st.markdown("#### 📖 주요 과목별 담당자 점유율 비교")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("##### 🔴 과목별 점유율 낮은 케이스 TOP 10")
                low_subject = top_subject_df.nsmallest(10, '주문부수')[['담당자', '과목명', '주문부수', '평균대비(%)', '학교수']]
                st.dataframe(
                    low_subject.style.format({
                        '주문부수': '{:,.0f}',
                        '평균대비(%)': '{:+.1f}',
                        '학교수': '{:,.0f}'
                    }).background_gradient(subset=['평균대비(%)'], cmap='Reds_r'),
                    use_container_width=True
                )
                st.caption("⚠️ 해당 과목 집중 영업 필요")
            
            with col2:
                st.markdown("##### 🟢 과목별 점유율 높은 케이스 TOP 10")
                high_subject = top_subject_df.nlargest(10, '주문부수')[['담당자', '과목명', '주문부수', '평균대비(%)', '학교수']]
                st.dataframe(
                    high_subject.style.format({
                        '주문부수': '{:,.0f}',
                        '평균대비(%)': '{:+.1f}',
                        '학교수': '{:,.0f}'
                    }).background_gradient(subset=['평균대비(%)'], cmap='Greens'),
                    use_container_width=True
                )
                st.caption("✅ 강점 과목 - 노하우 공유 필요")
            
            # 담당자별 과목 점유율 히트맵
            st.markdown("---")
            st.markdown("#### 📊 담당자 × 과목 주문부수 히트맵 (TOP 15 과목)")
            
            top15_subjects = subject_df.groupby('과목명')['주문부수'].sum().nlargest(15).index
            top15_df = subject_df[subject_df['과목명'].isin(top15_subjects)]
            
            pivot_subject = top15_df.pivot_table(
                index='담당자',
                columns='과목명',
                values='주문부수',
                aggfunc='sum'
            ).fillna(0)
            
            fig_subject_heatmap = px.imshow(
                pivot_subject,
                labels=dict(x="과목명", y="담당자", color="주문부수"),
                x=pivot_subject.columns,
                y=pivot_subject.index,
                color_continuous_scale='YlOrRd',
                aspect='auto',
                title="담당자별 과목 주문부수 히트맵"
            )
            fig_subject_heatmap.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig_subject_heatmap, use_container_width=True)
            st.caption("💡 진한 색: 높은 주문부수 | 옅은 색: 낮은 주문부수")
            
            # 담당자별 Top 과목 (기존 코드)
            st.markdown("---")
            st.markdown("#### 📖 담당자별 과목 주문 현황")
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
    
    with tab5:
        st.subheader("💡 액션 추천 (관리자용)")
        
        st.info("📌 **담당자별 성과 분석 기반 액션 포인트**")
        
        # 3가지 카테고리로 담당자 분류
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### 🔴 집중 관리 필요")
            st.caption("학생수 점유율 하위 30%")
            
            threshold_low = summary_df['학생수점유율(%)'].quantile(0.3)
            low_performers = summary_df[summary_df['학생수점유율(%)'] <= threshold_low].sort_values('학생수점유율(%)')
            
            for _, row in low_performers.iterrows():
                with st.expander(f"👤 {row['담당자']} - 점유율 {row['학생수점유율(%)']:.1f}%"):
                    st.write(f"**현황:**")
                    st.write(f"- 학생수 점유율: {row['학생수점유율(%)']:.1f}% (#{int(row['학생수점유율_순위'])})")
                    st.write(f"- 학교 점유율: {row['학교점유율(%)']:.1f}%")
                    st.write(f"- 주문부수: {row['총주문부수']:,.0f}부")
                    st.write(f"\n**제안 액션:**")
                    st.write("✓ 미채택 학교 리스트 검토 및 집중 영업")
                    st.write("✓ 상위 담당자와 전략 미팅 (노하우 전수)")
                    if row['학교점유율(%)'] < summary_df['학교점유율(%)'].mean():
                        st.write("✓ 학교 침투율 개선 우선")
        
        with col2:
            st.markdown("### 🟢 확장 추천")
            st.caption("점유율 상위 30% (추가 성장 가능)")
            
            threshold_high = summary_df['학생수점유율(%)'].quantile(0.7)
            high_performers = summary_df[summary_df['학생수점유율(%)'] >= threshold_high].sort_values('학생수점유율(%)', ascending=False)
            
            for _, row in high_performers.iterrows():
                with st.expander(f"⭐ {row['담당자']} - 점유율 {row['학생수점유율(%)']:.1f}%"):
                    st.write(f"**현황:**")
                    st.write(f"- 학생수 점유율: {row['학생수점유율(%)']:.1f}% (#{int(row['학생수점유율_순위'])})")
                    st.write(f"- 학교당 평균: {(row['총주문부수'] / row['채택학교수']):.0f}부" if row['채택학교수'] > 0 else "N/A")
                    st.write(f"- 담당 학생수: {row['담당학생수']:,.0f}명")
                    st.write(f"\n**제안 액션:**")
                    st.write("✓ 성공 사례 공유 (전사 세미나)")
                    st.write("✓ 인접 지역 확장 검토")
                    st.write("✓ 대형 학교 추가 공략")
        
        with col3:
            st.markdown("### 🟡 효율성 개선")
            st.caption("학교수 많지만 학교당 평균 낮음")
            
            summary_df['학교당평균부수_temp'] = summary_df['총주문부수'] / summary_df['채택학교수'].replace(0, 1)
            avg_per_school = summary_df['학교당평균부수_temp'].mean()
            
            inefficient = summary_df[
                (summary_df['채택학교수'] >= summary_df['채택학교수'].median()) & 
                (summary_df['학교당평균부수_temp'] < avg_per_school)
            ].sort_values('학교당평균부수_temp')
            
            for _, row in inefficient.iterrows():
                with st.expander(f"📊 {row['담당자']} - 학교당 {row['학교당평균부수_temp']:.0f}부"):
                    st.write(f"**현황:**")
                    st.write(f"- 채택 학교수: {row['채택학교수']:,.0f}개 (많음)")
                    st.write(f"- 학교당 평균: {row['학교당평균부수_temp']:.0f}부 (평균 이하)")
                    st.write(f"- 총 주문부수: {row['총주문부수']:,.0f}부")
                    st.write(f"\n**제안 액션:**")
                    st.write("✓ 기존 거래처 심화 영업 (추가 과목)")
                    st.write("✓ 학교당 주문량 증대 전략")
                    st.write("✓ Cross-selling 기회 탐색")
        
        # 전체 요약 통계
        st.markdown("---")
        st.markdown("### 📊 전체 담당자 요약 통계")
        
        summary_stats_col1, summary_stats_col2, summary_stats_col3, summary_stats_col4 = st.columns(4)
        
        with summary_stats_col1:
            st.metric("평균 학생수 점유율", f"{summary_df['학생수점유율(%)'].mean():.2f}%",
                     help="전체 담당자 평균")
        
        with summary_stats_col2:
            st.metric("평균 주문부수", f"{summary_df['총주문부수'].mean():,.0f}부")
        
        with summary_stats_col3:
            st.metric("평균 채택학교수", f"{summary_df['채택학교수'].mean():.1f}개")
        
        with summary_stats_col4:
            st.metric("평균 학교당 주문", f"{(summary_df['총주문부수'].sum() / summary_df['채택학교수'].sum()):.0f}부")
    
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
