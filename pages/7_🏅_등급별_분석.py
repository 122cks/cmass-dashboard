import streamlit as st
from utils.style import apply_custom_style
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.year_filter import add_year_filter_sidebar, filter_by_years, create_year_comparison_metrics

st.set_page_config(page_title="등급별 분석", page_icon="🏅", layout="wide")
apply_custom_style()

# Get data
if 'order_df' not in st.session_state:
    st.error("데이터를 불러올 수 없습니다. 메인 페이지로 돌아가주세요.")
    st.stop()

# 🚨 등급별 분석은 목표과목 필터된 데이터 사용
order_df_orig = st.session_state.get('order_df_target_filtered', st.session_state['order_df']).copy()
distributor_df = st.session_state.get('distributor_df', pd.DataFrame())
target_df = st.session_state.get('target_df', pd.DataFrame())
sort_by_grade = st.session_state.get('sort_by_grade', None)

# 학년도 필터 추가
selected_years, comparison_mode = add_year_filter_sidebar(order_df_orig, default_year='2026')
if selected_years:
    order_df = filter_by_years(order_df_orig, selected_years)
else:
    order_df = order_df_orig
total_df = st.session_state.get('total_df', pd.DataFrame())
market_analysis = st.session_state.get('market_analysis', pd.DataFrame())  # 시장 분석 데이터

st.title("🏅 등급별 총판 분석")
st.markdown("---")

# Modal for grade detail
@st.dialog("🏅 등급 상세 정보", width="large")
def show_grade_detail(grade):
    """등급별 상세 정보 모달"""
    st.subheader(f"🏅 등급: {grade}")
    
    order_df = st.session_state.get('order_df_target_filtered', st.session_state['order_df'])
    grade_col = '총판등급' if '총판등급' in order_df.columns else '등급'
    grade_orders = order_df[order_df[grade_col] == grade].copy()
    
    # 기본 통계
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 주문 부수", f"{grade_orders['부수'].sum():,.0f}부")
    with col2:
        st.metric("총판 수", f"{grade_orders['총판'].nunique():,}개")
    with col3:
        school_col = '정보공시학교코드' if '정보공시학교코드' in grade_orders.columns else '학교코드'
        st.metric("학교 수", f"{grade_orders[school_col].nunique():,}개")
    with col4:
        st.metric("과목 수", f"{grade_orders['과목명'].nunique():,}개" if '과목명' in grade_orders.columns else "N/A")
    
    st.markdown("---")
    
    # 탭으로 구분
    detail_tab1, detail_tab2, detail_tab3 = st.tabs(["🏢 총판별 현황", "📚 과목별 분석", "🗺️ 지역별 분포"])
    
    with detail_tab1:
        st.subheader("총판별 주문 현황")
        dist_orders = grade_orders.groupby('총판').agg({
            '부수': 'sum',
            school_col: 'nunique'
        }).reset_index()
        dist_orders.columns = ['총판', '주문부수', '학교수']
        dist_orders = dist_orders.sort_values('주문부수', ascending=False)
        
        fig = px.bar(
            dist_orders.head(20),
            x='주문부수',
            y='총판',
            orientation='h',
            title="총판별 주문 TOP 20",
            color='학교수',
            color_continuous_scale='Plasma'
        )
        fig.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(
            dist_orders.style.format({
                '주문부수': '{:,.0f}',
                '학교수': '{:,.0f}'
            }),
            use_container_width=True,
            height=300
        )
    
    with detail_tab2:
        st.subheader("과목별 주문 현황")
        if '과목명' in grade_orders.columns:
            subject_orders = grade_orders.groupby('과목명').agg({
                '부수': 'sum',
                school_col: 'nunique'
            }).reset_index()
            subject_orders.columns = ['과목명', '주문부수', '학교수']
            subject_orders = subject_orders.sort_values('주문부수', ascending=False)
            
            fig = px.treemap(
                subject_orders.head(20),
                path=['과목명'],
                values='주문부수',
                title="과목별 주문 비중 (Tree Map)"
            )
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
    
    with detail_tab3:
        st.subheader("지역별 분포")
        if '시도' in grade_orders.columns:
            region_orders = grade_orders.groupby('시도').agg({
                '부수': 'sum',
                '총판': 'nunique'
            }).reset_index()
            region_orders.columns = ['지역', '주문부수', '총판수']
            region_orders = region_orders.sort_values('주문부수', ascending=False)
            
            fig = px.bar(
                region_orders,
                x='지역',
                y='주문부수',
                title="지역별 주문 현황",
                color='총판수',
                color_continuous_scale='Blues'
            )
            fig.update_layout(xaxis={'tickangle': -45})
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(
                region_orders.style.format({
                    '주문부수': '{:,.0f}',
                    '총판수': '{:,.0f}'
                }),
                use_container_width=True
            )
        else:
            st.info("지역 정보가 없습니다.")

# Use existing grade column from order_df
if '총판등급' not in order_df.columns:
    st.warning("총판 등급 정보가 없습니다. 기본 분석만 제공됩니다.")
    order_df['등급'] = '미분류'
else:
    order_df['등급'] = order_df['총판등급'].fillna('미분류')

# Sidebar filters
st.sidebar.header("🔍 필터 옵션")

# Sort grades: S, A, B, C, D, E, G, then others
grade_order = ['S', 'A', 'B', 'C', 'D', 'E', 'G']
all_grades = order_df['등급'].unique().tolist()
available_grades = [g for g in grade_order if g in all_grades]
available_grades += sorted([g for g in all_grades if g not in grade_order and g != '미분류'])
if '미분류' in all_grades:
    available_grades.append('미분류')

selected_grades = st.sidebar.multiselect(
    "등급 선택",
    available_grades,
    default=available_grades if len(available_grades) <= 4 else available_grades[:4]
)

if not selected_grades:
    st.warning("⚠️ 분석할 등급을 선택해주세요.")
    st.stop()

# Filter data
filtered_order = order_df[order_df['등급'].isin(selected_grades)]

st.sidebar.markdown("---")
st.sidebar.info(f"📊 선택된 등급: {len(selected_grades)}개")

# Main metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_orders = filtered_order['부수'].sum()
    st.metric("총 주문 부수", f"{total_orders:,.0f}부")

with col2:
    total_distributors = filtered_order['총판'].nunique()
    st.metric("총판 수", f"{total_distributors}개")

with col3:
    avg_per_dist = total_orders / total_distributors if total_distributors > 0 else 0
    st.metric("총판당 평균", f"{avg_per_dist:,.0f}부")

with col4:
    total_schools = filtered_order['정보공시학교코드'].nunique() if '정보공시학교코드' in filtered_order.columns else filtered_order['학교코드'].nunique()
    st.metric("거래 학교", f"{total_schools:,}개교")

st.markdown("---")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 등급별 현황", "📈 성과 비교", "🗺️ 지역 분포", "📚 과목별 분석"])

with tab1:
    st.subheader("등급별 총판 현황")
    
    # Get total_df for market size calculation
    total_df = st.session_state.get('total_df', pd.DataFrame())
    
    # Calculate statistics by grade with market share
    grade_stats = []
    for grade in selected_grades:
        grade_data = filtered_order[filtered_order['등급'] == grade]
        
        # Calculate school code column
        school_code_col = '정보공시학교코드' if '정보공시학교코드' in grade_data.columns else '학교코드'
        
        # Calculate market size for this grade's schools (담당 학교의 중등/고등 1,2학년 학생수)
        school_codes = grade_data[school_code_col].unique() if school_code_col in grade_data.columns else []
        
        if not total_df.empty and len(school_codes) > 0:
            grade_schools = total_df[total_df['정보공시 학교코드'].isin(pd.Series(school_codes).astype(str))]
            if not grade_schools.empty:
                # Calculate market size based on school level (중등=3, 고등=4)
                # 중등 1,2학년 + 고등 1,2학년 학생수 합계
                market_size = 0
                for _, school in grade_schools.iterrows():
                    grade_code = school.get('학교급코드', 0)
                    if grade_code == 3:  # 중학교
                        market_size += school.get('1학년 학생수', 0) + school.get('2학년 학생수', 0)
                    elif grade_code == 4:  # 고등학교
                        market_size += school.get('1학년 학생수', 0) + school.get('2학년 학생수', 0)
            else:
                market_size = 0
        else:
            market_size = 0
        
        stats = {
            '등급': grade,
            '총판수': grade_data['총판'].nunique(),
            '주문부수': grade_data['부수'].sum(),
            '시장규모': market_size,
            '점유율(%)': (grade_data['부수'].sum() / market_size * 100) if market_size > 0 else 0,
            '주문금액': grade_data['금액'].sum() if '금액' in grade_data.columns else 0,
            '거래학교수': grade_data[school_code_col].nunique() if school_code_col in grade_data.columns else 0,
            '취급과목수': grade_data['과목명'].nunique() if '과목명' in grade_data.columns else grade_data.get('교과서명_구분', grade_data.get('교과서명', pd.Series())).nunique(),
            '총판당평균': 0,
            '학교당평균': 0
        }
        stats['총판당평균'] = stats['주문부수'] / stats['총판수'] if stats['총판수'] > 0 else 0
        stats['학교당평균'] = stats['주문부수'] / stats['거래학교수'] if stats['거래학교수'] > 0 else 0
        
        grade_stats.append(stats)
    
    grade_df = pd.DataFrame(grade_stats)
    
    # Display grade cards with market share
    cols = st.columns(len(selected_grades))
    for idx, (_, row) in enumerate(grade_df.iterrows()):
        with cols[idx]:
            grade_emoji = {'S': '🥇', 'A': '🥈', 'B': '🥉', 'C': '⭐', 'D': '📌', 'E': '🔵', 'G': '⚪', '미분류': '📍'}.get(row['등급'], '📌')
            grade_color = {'S': '#FFD700', 'A': '#C0C0C0', 'B': '#CD7F32', 'C': '#4CAF50', 'D': '#2196F3', 'E': '#9C27B0', 'G': '#607D8B', '미분류': '#9E9E9E'}.get(row['등급'], '#4CAF50')
            
            st.markdown(f"""
            <div style="border: 3px solid {grade_color}; border-radius: 15px; padding: 20px; margin: 10px 0;">
                <h2 style="text-align: center;">{grade_emoji} {row['등급']}</h2>
                <p><b>총판 수:</b> {row['총판수']}개</p>
                <p><b>주문:</b> {row['주문부수']:,.0f}부</p>
                <p><b>점유율:</b> {row['점유율(%)']:.2f}%</p>
                <p><b>시장규모:</b> {row['시장규모']:,.0f}명</p>
                <p><b>학교:</b> {row['거래학교수']}개교</p>
                <p><b>과목:</b> {row['취급과목수']}개</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Comparative charts with market share
    col1, col2 = st.columns(2)
    
    with col1:
        # Bar chart - Market Share by grade
        fig1 = px.bar(
            grade_df,
            x='등급',
            y='점유율(%)',
            title="등급별 시장 점유율",
            text='점유율(%)',
            color='등급',
            color_discrete_map={'S': '#FFD700', 'A': '#C0C0C0', 'B': '#CD7F32', 'C': '#4CAF50', 'D': '#2196F3', '미분류': '#9E9E9E'}
        )
        fig1.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
        fig1.update_layout(yaxis_title="점유율 (%)")
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # Calculate relative share (전체 대비 상대적 비중)
        grade_df['상대비중(%)'] = (grade_df['주문부수'] / grade_df['주문부수'].sum()) * 100
        
        # Percentage composition with donut chart
        fig2 = go.Figure()
        fig2.add_trace(go.Pie(
            labels=grade_df['등급'],
            values=grade_df['상대비중(%)'],
            text=grade_df['상대비중(%)'].apply(lambda x: f'{x:.1f}%'),
            textposition='inside',
            marker=dict(colors=['#FFD700', '#C0C0C0', '#CD7F32', '#4CAF50', '#2196F3', '#9E9E9E']),
            hole=0.4
        ))
        fig2.update_layout(
            title="등급별 상대적 주문 비중 (%)",
            showlegend=True
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    # Detailed metrics table
    st.markdown("---")
    st.subheader("📋 등급별 상세 지표")
    
    st.dataframe(
        grade_df.style.format({
            '총판수': '{:,.0f}',
            '주문부수': '{:,.0f}',
            '점유율(%)': '{:.2f}',
            '시장규모': '{:,.0f}',
            '주문금액': '{:,.0f}',
            '거래학교수': '{:,.0f}',
            '취급과목수': '{:,.0f}',
            '총판당평균': '{:.1f}',
            '학교당평균': '{:.1f}'
        }),
        use_container_width=True
    )

with tab2:
    st.subheader("📈 등급 내 총판별 점유율 및 순위")
    
    # 등급별로 탭 생성
    grade_tabs = st.tabs([f"{grade}등급" for grade in selected_grades])
    
    for grade_idx, grade in enumerate(selected_grades):
        with grade_tabs[grade_idx]:
            st.markdown(f"### 🏅 {grade}등급 총판 순위")
            
            # 해당 등급의 총판 데이터
            grade_data = filtered_order[filtered_order['등급'] == grade]
            
            # 2026년도 목표과목1, 목표과목2만 필터링 (목표 달성률 계산용, 컬럼명 방어적 처리)
            target_col = None
            if '목표과목' in grade_data.columns:
                target_col = '목표과목'
            elif '2026 목표과목' in grade_data.columns:
                target_col = '2026 목표과목'

            if '학년도' in grade_data.columns and target_col is not None:
                grade_data_2026 = grade_data[
                    (grade_data['학년도'] == 2026) & 
                    (grade_data[target_col].isin(['목표과목1', '목표과목2']))
                ]
            else:
                grade_data_2026 = grade_data
            
            school_code_col = '정보공시학교코드' if '정보공시학교코드' in grade_data.columns else '학교코드'
            
            # 총판별 집계 (전체)
            dist_in_grade = grade_data.groupby('총판').agg({
                '부수': 'sum',
                school_code_col: 'nunique',
                '금액': 'sum' if '금액' in grade_data.columns else 'count'
            }).reset_index()
            dist_in_grade.columns = ['총판', '주문부수', '학교수', '주문금액']
            
            # 2026년도 실적 집계
            dist_2026_actual = grade_data_2026.groupby('총판')['부수'].sum().to_dict()
            dist_in_grade['실적2026'] = dist_in_grade['총판'].map(dist_2026_actual).fillna(0)
            
            # 등급 내 점유율 계산
            total_in_grade = dist_in_grade['주문부수'].sum()
            dist_in_grade['등급내점유율(%)'] = (dist_in_grade['주문부수'] / total_in_grade * 100) if total_in_grade > 0 else 0
            
            # 목표 데이터 병합
            target_df = st.session_state.get('target_df', pd.DataFrame())
            if not target_df.empty and '총판명(공식)' in target_df.columns:
                # 목표 계산
                target_summary = target_df.copy()
                for col in ['목표과목1 부수', '목표과목2 부수', '전체목표 부수']:
                    if col in target_summary.columns:
                        target_summary[col] = target_summary[col].astype(str).str.replace(',', '').str.replace(' ', '')
                        target_summary[col] = pd.to_numeric(target_summary[col], errors='coerce').fillna(0)
                
                if '목표과목1 부수' in target_summary.columns and '목표과목2 부수' in target_summary.columns:
                    target_summary['전체목표'] = target_summary['목표과목1 부수'] + target_summary['목표과목2 부수']
                else:
                    target_summary['전체목표'] = target_summary.get('전체목표 부수', 0)
                
                target_map = target_summary.groupby('총판명(공식)')['전체목표'].sum().to_dict()
                dist_in_grade['목표부수'] = dist_in_grade['총판'].map(target_map).fillna(0)
                dist_in_grade['달성률(%)'] = (dist_in_grade['주문부수'] / dist_in_grade['목표부수'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
                
                # 순위 계산 (달성률 기준)
                dist_in_grade = dist_in_grade.sort_values('달성률(%)', ascending=False)
                dist_in_grade['달성률순위'] = range(1, len(dist_in_grade) + 1)
            else:
                dist_in_grade['목표부수'] = 0
                dist_in_grade['달성률(%)'] = 0
                dist_in_grade['달성률순위'] = 0
            
            # 점유율 순위 계산
            dist_in_grade = dist_in_grade.sort_values('등급내점유율(%)', ascending=False)
            dist_in_grade['점유율순위'] = range(1, len(dist_in_grade) + 1)
            
            # 차트 표시
            col1, col2 = st.columns(2)
            
            with col1:
                # 등급 내 점유율 차트
                fig1 = px.bar(
                    dist_in_grade.head(15),
                    x='총판',
                    y='등급내점유율(%)',
                    title=f"{grade}등급 내 점유율 TOP 15",
                    text='등급내점유율(%)',
                    color='등급내점유율(%)',
                    color_continuous_scale='Blues'
                )
                fig1.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
                fig1.update_layout(xaxis_tickangle=-45, height=400)
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                # 목표 달성률 차트
                if dist_in_grade['목표부수'].sum() > 0:
                    fig2 = px.bar(
                        dist_in_grade[dist_in_grade['목표부수'] > 0].head(15),
                        x='총판',
                        y='달성률(%)',
                        title=f"{grade}등급 목표 달성률 TOP 15",
                        text='달성률(%)',
                        color='달성률(%)',
                        color_continuous_scale='RdYlGn'
                    )
                    fig2.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                    fig2.update_layout(xaxis_tickangle=-45, height=400)
                    fig2.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="목표선")
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info("목표 데이터가 없습니다.")
            
            # 순위 테이블
            st.markdown("#### 📊 종합 순위표")
            
            display_cols = ['점유율순위', '총판', '주문부수', '등급내점유율(%)', '학교수']
            if dist_in_grade['목표부수'].sum() > 0:
                display_cols.extend(['목표부수', '달성률(%)', '달성률순위'])
            
            st.dataframe(
                dist_in_grade[display_cols].head(20).style.format({
                    '주문부수': '{:,.0f}',
                    '등급내점유율(%)': '{:.2f}',
                    '학교수': '{:,.0f}',
                    '목표부수': '{:,.0f}',
                    '달성률(%)': '{:.1f}'
                }),
                use_container_width=True
            )

with tab3:
    st.subheader("🗺️ 등급별 지역 분포")
    
    if '시도교육청' in filtered_order.columns:
        # Regional distribution by grade
        regional_by_grade = filtered_order.groupby(['등급', '시도교육청'])['부수'].sum().reset_index()
        
        # Grouped bar chart
        fig = px.bar(
            regional_by_grade,
            x='시도교육청',
            y='부수',
            color='등급',
            title="등급별 지역 분포",
            text='부수',
            barmode='group',
            color_discrete_map={'S': '#FFD700', 'A': '#C0C0C0', 'B': '#CD7F32', 'C': '#4CAF50', '미분류': '#9E9E9E'}
        )
        fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig.update_layout(height=500, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
        
        # Stacked percentage view
        st.markdown("---")
        
        pivot_regional = regional_by_grade.pivot(index='시도교육청', columns='등급', values='부수').fillna(0)
        pivot_pct = pivot_regional.div(pivot_regional.sum(axis=1), axis=0) * 100
        
        fig_pct = px.bar(
            pivot_pct.reset_index().melt(id_vars='시도교육청', var_name='등급', value_name='비율'),
            x='시도교육청',
            y='비율',
            color='등급',
            title="지역별 등급 구성비 (%)",
            barmode='stack',
            text='비율',
            color_discrete_map={'S': '#FFD700', 'A': '#C0C0C0', 'B': '#CD7F32', 'C': '#4CAF50', '미분류': '#9E9E9E'}
        )
        fig_pct.update_traces(texttemplate='%{text:.1f}%', textposition='inside')
        fig_pct.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_pct, use_container_width=True)
        
        # Heatmap
        st.markdown("---")
        
        fig_heatmap = px.imshow(
            pivot_regional,
            title="등급 × 지역 주문량 히트맵",
            labels=dict(x="등급", y="지역", color="주문량"),
            aspect="auto",
            color_continuous_scale='YlOrRd'
        )
        fig_heatmap.update_layout(height=600)
        st.plotly_chart(fig_heatmap, use_container_width=True)

with tab4:
    st.subheader("📚 등급별 과목 분석")
    
    # Subject distribution by grade (도서코드 기준)
    book_code_col = '도서코드(교지명구분)' if '도서코드(교지명구분)' in filtered_order.columns else '도서코드'
    subject_col = '교과서명_구분' if '교과서명_구분' in filtered_order.columns else '과목명'
    
    if book_code_col in filtered_order.columns:
        subject_by_grade = filtered_order.groupby(['등급', book_code_col]).agg({
            '부수': 'sum',
            subject_col: 'first'
        }).reset_index()
        subject_by_grade.columns = ['등급', book_code_col, '부수', '과목명']
    else:
        subject_by_grade = filtered_order.groupby(['등급', subject_col])['부수'].sum().reset_index()
        subject_by_grade.columns = ['등급', '과목명', '부수']
    
    # Get top subjects overall
    top_subjects = subject_by_grade.groupby('과목명')['부수'].sum().sort_values(ascending=False).head(15).index
    subject_by_grade_top = subject_by_grade[subject_by_grade['과목명'].isin(top_subjects)]
    
    # Grouped bar chart
    fig = px.bar(
        subject_by_grade_top,
        x='과목명',
        y='부수',
        color='등급',
        title="등급별 주요 과목 판매량 (TOP 15)",
        text='부수',
        barmode='group',
        color_discrete_map={'S': '#FFD700', 'A': '#C0C0C0', 'B': '#CD7F32', 'C': '#4CAF50', '미분류': '#9E9E9E'}
    )
    fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
    fig.update_layout(height=500, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)
    
    # Subject diversity by grade
    st.markdown("---")
    st.subheader("📊 등급별 과목 다양성")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Number of subjects by grade
        fig_diversity = px.bar(
            grade_df,
            x='등급',
            y='취급과목수',
            title="등급별 취급 과목 수",
            text='취급과목수',
            color='등급',
            color_discrete_map={'S': '#FFD700', 'A': '#C0C0C0', 'B': '#CD7F32', 'C': '#4CAF50', '미분류': '#9E9E9E'}
        )
        fig_diversity.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig_diversity, use_container_width=True)
    
    with col2:
        # Top subject for each grade
        st.markdown("#### 등급별 TOP 과목")
        for grade in selected_grades:
            grade_subjects = subject_by_grade[subject_by_grade['등급'] == grade].sort_values('부수', ascending=False)
            if not grade_subjects.empty:
                top_subject = grade_subjects.iloc[0]
                grade_emoji = {'S': '🥇', 'A': '🥈', 'B': '🥉', 'C': '⭐', '미분류': '📍'}.get(grade, '📌')
                st.write(f"{grade_emoji} **{grade}등급**: {top_subject['과목명']} ({top_subject['부수']:,.0f}부)")
    
    # Detailed table
    st.markdown("---")
    st.subheader("📋 등급별 과목 상세")
    
    # 중복 제거 후 pivot (과목명 + 등급 조합이 중복되면 합산)
    subject_agg = subject_by_grade.groupby(['과목명', '등급'])['부수'].sum().reset_index()
    pivot_subject = subject_agg.pivot(index='과목명', columns='등급', values='부수').fillna(0)
    pivot_subject['합계'] = pivot_subject.sum(axis=1)
    pivot_subject = pivot_subject.sort_values('합계', ascending=False).head(20)
    
    st.dataframe(
        pivot_subject.style.format('{:,.0f}'),
        use_container_width=True,
        height=400
    )
    
    # Download button
    csv = pivot_subject.to_csv(encoding='utf-8-sig')
    st.download_button(
        label="📥 CSV 다운로드",
        data=csv,
        file_name="등급별_과목_분석.csv",
        mime="text/csv"
    )

st.markdown("---")
st.caption("🏅 등급별 총판 분석 페이지")
