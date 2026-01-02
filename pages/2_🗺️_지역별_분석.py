import streamlit as st
from utils.style import apply_custom_style
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# Use utils package imports
from utils.common_filters import apply_common_filters, show_filter_summary
from utils.year_filter import add_year_filter_sidebar, filter_by_years, create_year_comparison_metrics
from utils.market_share_calculator import calculate_both_shares, compare_year_shares

st.set_page_config(page_title="지역별 분석", page_icon="🗺️", layout="wide")
apply_custom_style()

# Get data
if 'total_df' not in st.session_state or 'order_df' not in st.session_state:
    st.error("데이터를 불러올 수 없습니다. 메인 페이지로 돌아가주세요.")
    st.stop()

total_df = st.session_state['total_df']
order_df_orig = st.session_state['order_df'].copy()

# 학년도 필터 추가 (기본값: 2026)
selected_years, comparison_mode = add_year_filter_sidebar(order_df_orig, default_year='2026')
if selected_years:
    order_df = filter_by_years(order_df_orig, selected_years)
else:
    order_df = order_df_orig
distributor_df = st.session_state.get('distributor_df', pd.DataFrame())
market_analysis = st.session_state.get('market_analysis', pd.DataFrame())  # 시장 분석 데이터

# Add distributor info to order data (시군구 정보 추가)
if not distributor_df.empty and '총판명' in distributor_df.columns:
    # Create mapping from distributor name to region info
    dist_region_map = {}
    for _, row in distributor_df.iterrows():
        dist_name = str(row.get('총판명', ''))
        if dist_name:
            dist_region_map[dist_name] = {
                '지역': row.get('지 역', ''),
                '시도': row.get('시도', ''),
                '시군구': row.get('시군구', ''),
                '시군구2': row.get('시군구2', ''),
                '등급': row.get('등급', '')
            }
    
    # Match order data with distributor info
    def get_region_info(dist_name, info_type):
        if pd.isna(dist_name):
            return None
        for key, value in dist_region_map.items():
            if key in str(dist_name) or str(dist_name) in key:
                return value.get(info_type)
        return None
    
    order_df['시군구'] = order_df['총판'].apply(lambda x: get_region_info(x, '시군구'))
    order_df['시군구2'] = order_df['총판'].apply(lambda x: get_region_info(x, '시군구2'))
    order_df['총판지역'] = order_df['총판'].apply(lambda x: get_region_info(x, '지역'))

st.title("🗺️ 지역별 상세 분석")
st.markdown("---")

# 연도별 비교 모드 안내
if comparison_mode:
    st.info("📊 **연도 비교 모드**: 2025년과 2026년 데이터를 비교하여 부수, 학교점유율, 학생수점유율의 증감을 확인할 수 있습니다.")

# Modal for detailed region info
@st.dialog("🗺️ 지역 상세 정보", width="large")
def show_region_detail(region_name):
    """지역별 상세 정보 모달"""
    st.subheader(f"📍 {region_name}")
    
    # 해당 지역의 모든 주문 데이터
    region_col = '시도' if '시도' in st.session_state['order_df'].columns else '시도교육청'
    region_orders = st.session_state['order_df'][
        st.session_state['order_df'][region_col] == region_name
    ].copy()
    
    # 기본 통계
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 주문 부수", f"{region_orders['부수'].sum():,.0f}부")
    with col2:
        school_col = '정보공시학교코드' if '정보공시학교코드' in region_orders.columns else '학교코드'
        st.metric("주문 학교 수", f"{region_orders[school_col].nunique():,}개")
    with col3:
        st.metric("총판 수", f"{region_orders['총판'].nunique():,}개" if '총판' in region_orders.columns else "N/A")
    with col4:
        st.metric("과목 수", f"{region_orders['과목명'].nunique():,}개" if '과목명' in region_orders.columns else "N/A")
    
    st.markdown("---")
    
    # 탭으로 구분
    detail_tab1, detail_tab2, detail_tab3 = st.tabs(["🏫 학교별 주문", "📚 과목별 분석", "🏢 총판별 분포"])
    
    with detail_tab1:
        st.subheader("학교별 주문 현황")
        school_orders = region_orders.groupby('학교명').agg({
            '부수': 'sum',
            '금액': 'sum' if '금액' in region_orders.columns else 'count',
            '과목명': 'nunique' if '과목명' in region_orders.columns else 'count'
        }).reset_index()
        school_orders.columns = ['학교명', '주문부수', '주문금액', '과목수']
        school_orders = school_orders.sort_values('주문부수', ascending=False)
        
        # 차트
        fig = px.bar(
            school_orders.head(30),
            x='주문부수',
            y='학교명',
            orientation='h',
            title="상위 30개 학교 주문 현황",
            color='과목수'
        )
        fig.update_layout(height=700, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
        
        # 테이블
        st.dataframe(
            school_orders.style.format({
                '주문부수': '{:,.0f}',
                '주문금액': '{:,.0f}',
                '과목수': '{:.0f}'
            }),
            use_container_width=True,
            height=400
        )
    
    with detail_tab2:
        st.subheader("과목별 주문 현황")
        if '과목명' in region_orders.columns:
            subject_orders = region_orders.groupby('과목명').agg({
                '부수': 'sum',
                school_col: 'nunique'
            }).reset_index()
            subject_orders.columns = ['과목명', '주문부수', '학교수']
            subject_orders = subject_orders.sort_values('주문부수', ascending=False)
            
            fig = px.bar(
                subject_orders.head(20),
                x='과목명',
                y='주문부수',
                title="과목별 주문 현황 TOP 20",
                color='학교수',
                color_continuous_scale='Viridis'
            )
            fig.update_layout(xaxis={'tickangle': -45})
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
        st.subheader("총판별 분포")
        if '총판' in region_orders.columns:
            dist_orders = region_orders.groupby('총판').agg({
                '부수': 'sum',
                school_col: 'nunique'
            }).reset_index()
            dist_orders.columns = ['총판', '주문부수', '학교수']
            dist_orders = dist_orders.sort_values('주문부수', ascending=False)
            
            fig = px.pie(
                dist_orders,
                values='주문부수',
                names='총판',
                title="총판별 주문 비중"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(
                dist_orders.style.format({
                    '주문부수': '{:,.0f}',
                    '학교수': '{:,.0f}'
                }),
                use_container_width=True
            )
        else:
            st.info("총판 정보가 없습니다.")

# Add region classification helper function
def classify_region_direction(region_name):
    """Classify region into North/South based on name"""
    if pd.isna(region_name):
        return '미분류'
    
    region_str = str(region_name)
    
    # Northern regions
    northern = ['서울', '인천', '경기', '강원', '대전', '세종', '충청북도', '충청남도', '충북', '충남']
    # Southern regions  
    southern = ['부산', '대구', '울산', '광주', '전라북도', '전라남도', '경상북도', '경상남도', '제주', '전북', '전남', '경북', '경남']
    
    for n in northern:
        if n in region_str:
            return '북도'
    for s in southern:
        if s in region_str:
            return '남도'
    
    return '미분류'

# Add region classification to dataframes
if '시도교육청' in total_df.columns:
    total_df['지역구분'] = total_df['시도교육청'].apply(classify_region_direction)
if '시도교육청' in order_df.columns:
    order_df['지역구분'] = order_df['시도교육청'].apply(classify_region_direction)

# Sidebar Filters
st.sidebar.header("🔍 필터 옵션")

# Region Direction Filter (North/South)
if '지역구분' in total_df.columns:
    region_directions = ['전체'] + sorted(total_df['지역구분'].dropna().unique().tolist())
    selected_direction = st.sidebar.selectbox("지역 구분", region_directions)
    
    if selected_direction != '전체':
        filtered_total_df = total_df[total_df['지역구분'] == selected_direction].copy()
        filtered_order_df = order_df[order_df['지역구분'] == selected_direction].copy()
    else:
        filtered_total_df = total_df.copy()
        filtered_order_df = order_df.copy()
else:
    filtered_total_df = total_df.copy()
    filtered_order_df = order_df.copy()

# School Level Filter
if '학교급명' in filtered_order_df.columns:
    # 학교급명 고유값 확인 및 정렬
    unique_levels = filtered_order_df['학교급명'].dropna().unique().tolist()
    # 중학교, 고등학교 순으로 정렬
    sorted_levels = []
    for level in ['중학교', '고등학교']:
        matching = [l for l in unique_levels if level in str(l)]
        sorted_levels.extend(sorted(matching))
    # 남은 것들 추가
    remaining = [l for l in unique_levels if l not in sorted_levels]
    sorted_levels.extend(sorted(remaining))
    
    school_levels = ['전체'] + sorted_levels
    selected_school_level = st.sidebar.selectbox("학교급 선택", school_levels)
    
    if selected_school_level != '전체':
        filtered_order_df = filtered_order_df[filtered_order_df['학교급명'] == selected_school_level]
        st.sidebar.info(f"선택된 학교급: {selected_school_level}")
        filtered_total_df = filtered_total_df[filtered_total_df.get('학교급명', filtered_total_df['학교급코드'].map({2: '초등학교', 3: '중학교', 4: '고등학교'})) == selected_school_level]

# Apply common filters
original_len = len(filtered_order_df)
filtered_order_df = apply_common_filters(filtered_order_df, show_filters=['교과군', '과목'])
show_filter_summary(filtered_order_df, order_df)

st.sidebar.markdown("---")
st.sidebar.info(f"📊 필터링된 데이터: {len(filtered_order_df):,}건")
if '학교급코드' in filtered_total_df.columns:
    school_levels_code = sorted(filtered_total_df['학교급코드'].dropna().unique().tolist())
    school_level_names = {2: '초등학교', 3: '중학교', 4: '고등학교'}
    school_options = ['전체'] + [school_level_names.get(code, f'학교급{code}') for code in school_levels_code]
    selected_school = st.sidebar.selectbox("학교급 선택", school_options)
    
    if selected_school != '전체':
        selected_code = [k for k, v in school_level_names.items() if v == selected_school][0]
        filtered_total_df = filtered_total_df[filtered_total_df['학교급코드'] == selected_code].copy()
    
# Subject Filter
if '과목명' in filtered_order_df.columns:
    subjects = ['전체'] + sorted(filtered_order_df['과목명'].dropna().unique().tolist())
    selected_subject = st.sidebar.selectbox("과목 선택", subjects)
    
    if selected_subject != '전체':
        filtered_order_df = filtered_order_df[filtered_order_df['과목명'] == selected_subject].copy()

st.sidebar.markdown("---")
st.sidebar.info(f"📊 필터링된 학생: {filtered_total_df['학생수(계)'].sum():,.0f}명")
st.sidebar.info(f"📊 필터링된 주문: {filtered_order_df['부수'].sum():,.0f}부")

# Main Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_students = filtered_total_df['학생수(계)'].sum()
    st.metric("전체 학생 수", f"{total_students:,.0f}명")

with col2:
    total_orders = filtered_order_df['부수'].sum()
    st.metric("총 주문 부수", f"{total_orders:,.0f}부")

with col3:
    overall_share = (total_orders / total_students * 100) if total_students > 0 else 0
    st.metric("전체 점유율", f"{overall_share:.2f}%")

with col4:
    num_regions = filtered_order_df['시도교육청'].nunique() if '시도교육청' in filtered_order_df.columns else 0
    st.metric("지역 수", f"{num_regions}개")

st.markdown("---")

# Tab Layout
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🗺️ 시도별 분석", "🏫 교육청별 분석", "🏘️ 시군구별 분석", "📊 학교급별 분석", "🧭 남도/북도 비교", "📋 상세 테이블"])

with tab1:
    st.subheader("시도교육청별 점유율 분석")
    
    if '시도교육청' in filtered_total_df.columns and '시도교육청' in filtered_order_df.columns:
        # Calculate regional statistics
        region_students = filtered_total_df.groupby('시도교육청')['학생수(계)'].sum().reset_index()
        region_students.columns = ['시도교육청', '전체학생수']
        
        # 지역별 전체 학교 수 계산
        region_schools_total = filtered_total_df.groupby('시도교육청')['정보공시 학교코드'].nunique().reset_index()
        region_schools_total.columns = ['시도교육청', '전체학교수']
        
        region_orders = filtered_order_df.groupby('시도교육청')['부수'].sum().reset_index()
        region_orders.columns = ['시도교육청', '주문부수']
        
        # 지역별 채택 학교 수 계산
        school_code_col = '정보공시학교코드' if '정보공시학교코드' in filtered_order_df.columns else '학교코드'
        region_schools_adopted = filtered_order_df.groupby('시도교육청')[school_code_col].nunique().reset_index()
        region_schools_adopted.columns = ['시도교육청', '채택학교수']
        
        # 모든 통계 병합
        region_stats = pd.merge(region_students, region_schools_total, on='시도교육청', how='left')
        region_stats = pd.merge(region_stats, region_orders, on='시도교육청', how='left')
        region_stats = pd.merge(region_stats, region_schools_adopted, on='시도교육청', how='left')
        region_stats = region_stats.fillna(0)
        
        # 채택학교 학생수 계산 (채택한 학교들의 학생수 합계)
        if school_code_col in filtered_order_df.columns:
            # 채택 학교 목록
            adopted_schools_by_region = filtered_order_df.groupby('시도교육청')[school_code_col].unique()
            
            # 각 지역의 채택학교 학생수 계산
            채택학교학생수_list = []
            for region in region_stats['시도교육청']:
                if region in adopted_schools_by_region.index:
                    adopted_schools = adopted_schools_by_region[region]
                    # 해당 학교들의 학생수 합계
                    school_code_col_total = '정보공시 학교코드' if '정보공시 학교코드' in filtered_total_df.columns else '학교코드'
                    students = filtered_total_df[filtered_total_df[school_code_col_total].isin(adopted_schools)]['학생수(계)'].sum()
                    채택학교학생수_list.append(students)
                else:
                    채택학교학생수_list.append(0)
            
            region_stats['채택학교학생수'] = 채택학교학생수_list
        else:
            region_stats['채택학교학생수'] = 0
        
        # 점유율 계산
        region_stats['학교점유율(%)'] = (region_stats['채택학교수'] / region_stats['전체학교수'] * 100).fillna(0)
        region_stats['학생수점유율(%)'] = (region_stats['채택학교학생수'] / region_stats['전체학생수'] * 100).fillna(0)
        region_stats['미점유학생'] = region_stats['전체학생수'] - region_stats['채택학교학생수']
        region_stats['미채택학교'] = region_stats['전체학교수'] - region_stats['채택학교수']
        region_stats = region_stats.sort_values('학생수점유율(%)', ascending=False)
        
        # 지역 클릭 안내
        st.info("💡 **아래 차트에서** 학교점유율(채택학교수/전체학교수)과 학생수점유율(채택학교학생수/전체학생수)을 함께 확인할 수 있습니다.")
        
        # 3열 차트로 변경
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Bar chart - 학교점유율
            fig = px.bar(
                region_stats,
                x='시도교육청',
                y='학교점유율(%)',
                title="시도별 학교점유율 (채택학교수/전체학교수)",
                text='학교점유율(%)',
                color='학교점유율(%)',
                color_continuous_scale='Blues'
            )
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig.update_layout(height=500, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Bar chart - 학생수점유율
            fig2 = px.bar(
                region_stats,
                x='시도교육청',
                y='학생수점유율(%)',
                title="시도별 학생수점유율 (채택학교학생수/전체학생수)",
                text='학생수점유율(%)',
                color='학생수점유율(%)',
                color_continuous_scale='RdYlGn'
            )
            fig2.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
            fig2.update_layout(height=500, xaxis_tickangle=-45)
            st.plotly_chart(fig2, use_container_width=True)
        
        with col3:
            # Calculate relative share (전체 대비 상대적 비중)
            region_stats['상대비중(%)'] = (region_stats['주문부수'] / region_stats['주문부수'].sum()) * 100
            
            # Stacked percentage bar chart
            fig_relative = go.Figure()
            fig_relative.add_trace(go.Bar(
                x=region_stats['시도교육청'],
                y=region_stats['상대비중(%)'],
                text=region_stats['상대비중(%)'].apply(lambda x: f'{x:.1f}%'),
                textposition='auto',
                marker_color='lightcoral',
                name='상대 비중'
            ))
            fig_relative.update_layout(
                title="지역별 상대적 주문 비중 (%)",
                yaxis_title="전체 대비 비중 (%)",
                xaxis_tickangle=-45,
                height=500,
                showlegend=False
            )
            st.plotly_chart(fig_relative, use_container_width=True)
        
        # 클릭 가능한 지역 테이블
        st.markdown("### 📋 지역별 종합 데이터 (클릭하여 상세보기)")
        
        # Display top regions with click buttons
        for idx, row in region_stats.head(20).iterrows():
            cols = st.columns([1, 3, 2, 2, 2, 2, 2, 2])
            
            with cols[0]:
                if st.button("📍", key=f"region_btn_{idx}", help="상세 정보 보기"):
                    show_region_detail(row['시도교육청'])
            
            with cols[1]:
                st.write(f"**{row['시도교육청']}**")
            with cols[2]:
                st.write(f"{row['주문부수']:,.0f}부")
            with cols[3]:
                st.write(f"{row['점유율(%)']:.1f}%")
            with cols[4]:
                st.write(f"{row['채택학교수']:,.0f}/{row['전체학교수']:,.0f}개교")
            with cols[5]:
                st.write(f"{row['학교채택률(%)']:.1f}%")
            with cols[6]:
                st.write(f"{row['전체학생수']:,.0f}명")
            with cols[7]:
                st.write(f"{row['상대비중(%)']:.1f}%")
        
        # Detailed comparison
        st.markdown("---")
        st.subheader("📊 지역별 상세 비교")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Scatter plot - Market size vs Share
            fig_scatter = px.scatter(
                region_stats,
                x='전체학생수',
                y='점유율(%)',
                size='주문부수',
                color='점유율(%)',
                hover_name='시도교육청',
                title="시장 규모 vs 점유율",
                labels={'전체학생수': '전체 학생 수', '점유율(%)': '점유율 (%)'},
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
        
        with col2:
            # Funnel chart for top regions
            fig_funnel = go.Figure(go.Funnel(
                y=region_stats.head(10)['시도교육청'],
                x=region_stats.head(10)['주문부수'],
                textinfo="value+percent initial"
            ))
            fig_funnel.update_layout(title="지역별 주문량 TOP 10 (Funnel)")
            st.plotly_chart(fig_funnel, use_container_width=True)
        
        # Regional performance cards with school level breakdown
        st.markdown("---")
        st.subheader("🏆 지역별 성과 카드")
        st.caption("카드를 클릭하면 학교급별 학생수와 세부 주문 내역을 확인할 수 있습니다.")
        
        # Calculate school level breakdown by region
        school_level_names = {2: '초등학교', 3: '중학교', 4: '고등학교'}
        if '학교급코드' in filtered_total_df.columns:
            region_school_breakdown = filtered_total_df.groupby(['시도교육청', '학교급코드'])['학생수(계)'].sum().reset_index()
            region_school_breakdown['학교급'] = region_school_breakdown['학교급코드'].map(school_level_names)
        
        cols = st.columns(3)
        for idx, (_, row) in enumerate(region_stats.head(6).iterrows()):
            with cols[idx % 3]:
                region_name = row['시도교육청']
                
                # Card button
                if st.button(f"📍 {region_name}", key=f"region_card_{idx}"):
                    st.session_state[f'show_detail_{region_name}'] = not st.session_state.get(f'show_detail_{region_name}', False)
                
                st.markdown(f"""
                <div style="border: 2px solid #4CAF50; border-radius: 10px; padding: 15px; margin: 10px 0;">
                    <h4>{region_name}</h4>
                    <p><b>점유율:</b> {row['점유율(%)']:.2f}%</p>
                    <p><b>주문:</b> {row['주문부수']:,.0f}부</p>
                    <p><b>전체학생:</b> {row['전체학생수']:,.0f}명</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Show detail when clicked
                if st.session_state.get(f'show_detail_{region_name}', False):
                    with st.expander(f"📊 {region_name} 상세 정보", expanded=True):
                        # School level breakdown
                        if '학교급코드' in filtered_total_df.columns:
                            st.markdown("**📚 학교급별 전체 학생수**")
                            region_breakdown = region_school_breakdown[region_school_breakdown['시도교육청'] == region_name]
                            for _, level_row in region_breakdown.iterrows():
                                st.write(f"- {level_row['학교급']}: {level_row['학생수(계)']:,.0f}명")
                        
                        st.markdown("---")
                        
                        # Order details
                        st.markdown("**📦 세부 주문 내역**")
                        region_orders = filtered_order_df[filtered_order_df['시도교육청'] == region_name]
                        
                        if len(region_orders) > 0:
                            # Aggregate by book code (도서코드)
                            book_code_col = '도서코드(교지명구분)' if '도서코드(교지명구분)' in region_orders.columns else '도서코드'
                            subject_col = '교과서명_구분' if '교과서명_구분' in region_orders.columns else '과목명'
                            
                            if book_code_col in region_orders.columns:
                                subject_summary = region_orders.groupby(book_code_col).agg({
                                    '부수': 'sum',
                                    subject_col: 'first'
                                }).reset_index()
                                subject_summary.columns = [book_code_col, '부수', '과목명']
                            else:
                                subject_summary = region_orders.groupby(subject_col)['부수'].sum().reset_index()
                                subject_summary.columns = ['과목명', '부수']
                            
                            subject_summary = subject_summary.sort_values('부수', ascending=False)
                            
                            st.dataframe(
                                subject_summary.style.format({'부수': '{:,.0f}'}),
                                use_container_width=True,
                                height=200
                            )
                            
                            # Distributor breakdown
                            if '총판' in region_orders.columns:
                                st.markdown("**🏢 총판별 주문**")
                                dist_summary = region_orders.groupby('총판')['부수'].sum().reset_index()
                                dist_summary = dist_summary.sort_values('부수', ascending=False).head(5)
                                for _, dist_row in dist_summary.iterrows():
                                    st.write(f"- {dist_row['총판']}: {dist_row['부수']:,.0f}부")
                        else:
                            st.info("주문 내역이 없습니다.")

with tab2:
    st.subheader("교육지원청별 상세 분석")
    
    if '교육지원청' in filtered_total_df.columns and '교육지원청' in filtered_order_df.columns:
        # Education office statistics
        office_students = filtered_total_df.groupby(['시도교육청', '교육지원청'])['학생수(계)'].sum().reset_index()
        office_orders = filtered_order_df.groupby(['시도교육청', '교육지원청'])['부수'].sum().reset_index()
        
        office_stats = pd.merge(
            office_students,
            office_orders,
            on=['시도교육청', '교육지원청'],
            how='left'
        ).fillna(0)
        
        office_stats['점유율(%)'] = (office_stats['부수'] / office_stats['학생수(계)']) * 100
        office_stats = office_stats.sort_values('점유율(%)', ascending=False)
        
        # Select region for detailed view
        selected_region_detail = st.selectbox(
            "상세 조회할 지역 선택",
            ['전체'] + sorted(office_stats['시도교육청'].unique().tolist())
        )
        
        if selected_region_detail != '전체':
            office_stats_filtered = office_stats[office_stats['시도교육청'] == selected_region_detail]
        else:
            office_stats_filtered = office_stats.head(20)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig = px.bar(
                office_stats_filtered,
                x='교육지원청',
                y='점유율(%)',
                color='시도교육청',
                title=f"{'전체 TOP 20' if selected_region_detail == '전체' else selected_region_detail} - 교육청별 점유율",
                text='점유율(%)',
                barmode='group'
            )
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig.update_layout(height=500, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Top 10 education offices
            st.markdown("#### 🥇 TOP 10 교육청")
            for idx, row in office_stats.head(10).iterrows():
                st.write(f"{office_stats.head(10).index.tolist().index(idx) + 1}. **{row['교육지원청']}** ({row['시도교육청']})")
                st.write(f"   📊 {row['점유율(%)']:.2f}% | 📦 {row['부수']:,.0f}부")
                st.progress(min(row['점유율(%)'] / 100, 1.0))
    else:
        st.info("교육지원청 정보가 없습니다.")

with tab3:
    st.subheader("🏘️ 시군구별 분석")
    st.caption("총판 정보의 시군구 데이터를 기반으로 더 넓은 범위의 지역 분석을 제공합니다.")
    
    # Check if we have city/county data
    if '시군구2' in order_df.columns and not order_df['시군구2'].isna().all():
        # Get orders with city/county info
        city_orders = filtered_order_df[filtered_order_df['시군구2'].notna()].copy()
        
        if not city_orders.empty:
            # Aggregate by city/county
            city_stats = city_orders.groupby('시군구2').agg({
                '부수': 'sum',
                '총판': 'nunique'
            }).reset_index()
            city_stats.columns = ['시군구', '주문부수', '총판수']
            city_stats = city_stats.sort_values('주문부수', ascending=False)
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("총 시군구 수", f"{len(city_stats)}개")
            with col2:
                st.metric("총 주문부수", f"{city_stats['주문부수'].sum():,.0f}부")
            with col3:
                avg_per_city = city_stats['주문부수'].mean()
                st.metric("시군구당 평균", f"{avg_per_city:,.0f}부")
            with col4:
                top_city = city_stats.iloc[0]
                st.metric("최다 주문", f"{top_city['시군구']}", f"{top_city['주문부수']:,.0f}부")
            
            st.markdown("---")
            
            # Charts
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Bar chart - Top cities
                fig_bar = px.bar(
                    city_stats.head(15),
                    x='시군구',
                    y='주문부수',
                    title="시군구별 주문 현황 TOP 15",
                    text='주문부수',
                    color='주문부수',
                    color_continuous_scale='Blues'
                )
                fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                fig_bar.update_layout(height=400, xaxis_tickangle=-45)
                st.plotly_chart(fig_bar, use_container_width=True)
            
            with col2:
                # Pie chart - Distribution
                fig_pie = px.pie(
                    city_stats.head(10),
                    values='주문부수',
                    names='시군구',
                    title="TOP 10 시군구 점유 비율"
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)
            
            # Subject distribution by city
            st.markdown("---")
            st.subheader("📚 시군구별 과목 분포")
            
            subject_col = '교과서명_구분' if '교과서명_구분' in city_orders.columns else '교과서명'
            if subject_col in city_orders.columns:
                city_subject = city_orders.groupby(['시군구2', subject_col])['부수'].sum().reset_index()
                
                # Select city for detailed view
                selected_city = st.selectbox(
                    "상세 조회할 시군구 선택",
                    ['전체'] + sorted(city_stats['시군구'].unique().tolist())
                )
                
                if selected_city != '전체':
                    city_subject_filtered = city_subject[city_subject['시군구2'] == selected_city]
                    city_subject_filtered = city_subject_filtered.sort_values('부수', ascending=False)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig = px.bar(
                            city_subject_filtered.head(10),
                            x=subject_col,
                            y='부수',
                            title=f"{selected_city} - 과목별 주문 현황",
                            text='부수',
                            color='부수',
                            color_continuous_scale='Viridis'
                        )
                        fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                        fig.update_layout(height=400, xaxis_tickangle=-45)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        # Pie chart for selected city
                        fig_pie = px.pie(
                            city_subject_filtered.head(8),
                            values='부수',
                            names=subject_col,
                            title=f"{selected_city} - 과목 구성"
                        )
                        st.plotly_chart(fig_pie, use_container_width=True)
                    
                    # Detailed table
                    st.markdown("#### 📋 상세 데이터")
                    st.dataframe(
                        city_subject_filtered.style.format({'부수': '{:,.0f}'}),
                        use_container_width=True
                    )
                else:
                    # Heatmap - Top cities vs Top subjects
                    top_cities = city_stats.head(10)['시군구'].tolist()
                    top_subjects = city_orders.groupby(subject_col)['부수'].sum().nlargest(10).index.tolist()
                    
                    heatmap_data = city_subject[
                        (city_subject['시군구2'].isin(top_cities)) &
                        (city_subject[subject_col].isin(top_subjects))
                    ].pivot_table(
                        index='시군구2',
                        columns=subject_col,
                        values='부수',
                        fill_value=0
                    )
                    
                    fig_heatmap = px.imshow(
                        heatmap_data,
                        labels=dict(x="과목", y="시군구", color="주문부수"),
                        title="시군구 × 과목 주문 히트맵 (TOP 10)",
                        color_continuous_scale='YlOrRd',
                        aspect='auto'
                    )
                    fig_heatmap.update_layout(height=500)
                    st.plotly_chart(fig_heatmap, use_container_width=True)
            
            # Distributor distribution by city
            st.markdown("---")
            st.subheader("🏢 시군구별 총판 분포")
            
            if '총판' in city_orders.columns:
                city_dist = city_orders.groupby('시군구2')['총판'].apply(lambda x: ', '.join(sorted(set(x.dropna())))).reset_index()
                # city_stats의 시군구 컴럼 확인 후 병합
                if '총판수' in city_stats.columns and '주문부수' in city_stats.columns:
                    merge_cols = []
                    if '총판수' in city_stats.columns:
                        merge_cols.append('총판수')
                    if '주문부수' in city_stats.columns:
                        merge_cols.append('주문부수')
                    
                    if merge_cols and '시군구2' in city_stats.columns:
                        city_dist = pd.merge(city_dist, city_stats[['시군구2'] + merge_cols], on='시군구2', how='left')
            
            st.dataframe(
                city_dist.rename(columns={
                    '시군구': '시군구',
                    '총판': '담당 총판',
                    '총판수': '총판 수',
                    '주문부수': '총 주문부수'
                }).style.format({'총 주문부수': '{:,.0f}'}),
                use_container_width=True,
                height=400
            )
            
        else:
            st.warning("시군구 정보가 매핑된 주문 데이터가 없습니다.")
    else:
        st.info("시군구 정보가 없습니다. 총판정보 파일에 시군구 데이터가 있는지 확인해주세요.")

with tab4:
    st.subheader("학교급별 지역 분석")
    
    if '학교급코드' in filtered_total_df.columns:
        school_level_names = {2: '초등학교', 3: '중학교', 4: '고등학교'}
        
        # Multi-level analysis
        multi_stats = filtered_total_df.groupby(['시도교육청', '학교급코드'])['학생수(계)'].sum().reset_index()
        multi_stats['학교급'] = multi_stats['학교급코드'].map(school_level_names)
        
        # Pivot for heatmap
        pivot_data = multi_stats.pivot(index='시도교육청', columns='학교급', values='학생수(계)').fillna(0)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Stacked bar chart
            fig = px.bar(
                multi_stats,
                x='시도교육청',
                y='학생수(계)',
                color='학교급',
                title="지역별 × 학교급별 학생 분포",
                barmode='stack',
                text='학생수(계)'
            )
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='inside')
            fig.update_layout(height=500, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Summary by school level
            school_summary = multi_stats.groupby('학교급')['학생수(계)'].sum().reset_index()
            fig_pie = px.pie(
                school_summary,
                values='학생수(계)',
                names='학교급',
                title="학교급별 학생 비율"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # Heatmap
        st.markdown("---")
        fig_heatmap = px.imshow(
            pivot_data,
            title="지역 × 학교급 학생 분포 히트맵",
            labels=dict(x="학교급", y="지역", color="학생 수"),
            aspect="auto",
            color_continuous_scale='Blues'
        )
        fig_heatmap.update_layout(height=600)
        st.plotly_chart(fig_heatmap, use_container_width=True)

with tab4:
    st.subheader("🧭 남도/북도 지역 비교")
    
    if '지역구분' in total_df.columns:
        # Calculate statistics by region direction
        direction_total = total_df.groupby('지역구분')['학생수(계)'].sum().reset_index()
        direction_total.columns = ['지역구분', '전체학생수']
        
        direction_orders = order_df.groupby('지역구분')['부수'].sum().reset_index()
        direction_orders.columns = ['지역구분', '주문부수']
        
        direction_stats = pd.merge(direction_total, direction_orders, on='지역구분', how='left').fillna(0)
        direction_stats['점유율(%)'] = (direction_stats['주문부수'] / direction_stats['전체학생수']) * 100
        direction_stats = direction_stats[direction_stats['지역구분'] != '미분류']
        
        # Metrics
        col1, col2 = st.columns(2)
        
        for idx, row in direction_stats.iterrows():
            with col1 if row['지역구분'] == '남도' else col2:
                direction_emoji = '🌊' if row['지역구분'] == '남도' else '⛰️'
                st.markdown(f"""
                <div style="border: 3px solid {'#FF6B6B' if row['지역구분'] == '남도' else '#4ECDC4'}; 
                            border-radius: 15px; padding: 20px; margin: 10px 0;">
                    <h2 style="text-align: center;">{direction_emoji} {row['지역구분']}</h2>
                    <p><b>전체 학생:</b> {row['전체학생수']:,.0f}명</p>
                    <p><b>주문:</b> {row['주문부수']:,.0f}부</p>
                    <p><b>점유율:</b> {row['점유율(%)']:.2f}%</p>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Comparison charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Bar chart - Orders
            fig1 = px.bar(
                direction_stats,
                x='지역구분',
                y='주문부수',
                title="남도/북도 주문량 비교",
                text='주문부수',
                color='지역구분',
                color_discrete_map={'남도': '#FF6B6B', '북도': '#4ECDC4'}
            )
            fig1.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Pie chart
            fig2 = px.pie(
                direction_stats,
                values='주문부수',
                names='지역구분',
                title="남도/북도 주문 비중",
                color='지역구분',
                color_discrete_map={'남도': '#FF6B6B', '북도': '#4ECDC4'}
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        # Regional breakdown within north/south
        st.markdown("---")
        st.subheader("📍 남도/북도 내 시도별 분포")
        
        regional_direction = total_df.groupby(['지역구분', '시도교육청'])['학생수(계)'].sum().reset_index()
        regional_direction_orders = order_df.groupby(['지역구분', '시도교육청'])['부수'].sum().reset_index()
        
        regional_direction = pd.merge(
            regional_direction,
            regional_direction_orders,
            on=['지역구분', '시도교육청'],
            how='left'
        ).fillna(0)
        regional_direction['점유율(%)'] = (regional_direction['부수'] / regional_direction['학생수(계)']) * 100
        regional_direction = regional_direction[regional_direction['지역구분'] != '미분류']
        
        col1, col2 = st.columns(2)
        
        with col1:
            # South region breakdown
            south_data = regional_direction[regional_direction['지역구분'] == '남도'].sort_values('부수', ascending=False)
            fig_south = px.bar(
                south_data,
                x='시도교육청',
                y='부수',
                title="🌊 남도 지역 시도별 주문량",
                text='부수',
                color='점유율(%)',
                color_continuous_scale='Reds'
            )
            fig_south.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig_south.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_south, use_container_width=True)
        
        with col2:
            # North region breakdown
            north_data = regional_direction[regional_direction['지역구분'] == '북도'].sort_values('부수', ascending=False)
            fig_north = px.bar(
                north_data,
                x='시도교육청',
                y='부수',
                title="⛰️ 북도 지역 시도별 주문량",
                text='부수',
                color='점유율(%)',
                color_continuous_scale='Blues'
            )
            fig_north.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig_north.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_north, use_container_width=True)
        
        # School level comparison
        st.markdown("---")
        st.subheader("📚 남도/북도 학교급별 비교")
        
        if '학교급코드' in total_df.columns:
            school_level_names = {2: '초등학교', 3: '중학교', 4: '고등학교'}
            
            direction_school = total_df.groupby(['지역구분', '학교급코드'])['학생수(계)'].sum().reset_index()
            direction_school['학교급'] = direction_school['학교급코드'].map(school_level_names)
            direction_school = direction_school[direction_school['지역구분'] != '미분류']
            
            fig_school = px.bar(
                direction_school,
                x='학교급',
                y='학생수(계)',
                color='지역구분',
                title="남도/북도 학교급별 학생 분포",
                barmode='group',
                text='학생수(계)',
                color_discrete_map={'남도': '#FF6B6B', '북도': '#4ECDC4'}
            )
            fig_school.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            st.plotly_chart(fig_school, use_container_width=True)
    else:
        st.info("지역 구분 데이터가 없습니다.")

with tab5:
    st.subheader("📋 지역별 상세 데이터")
    
    # Display regional statistics table
    if 'region_stats' in locals():
        st.dataframe(
            region_stats.style.format({
                '전체학생수': '{:,.0f}',
                '주문부수': '{:,.0f}',
                '점유율(%)': '{:.2f}%',
                '미점유학생': '{:,.0f}'
            }),
            use_container_width=True,
            height=400
        )
        
        # Download button
        csv = region_stats.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 CSV 다운로드",
            data=csv,
            file_name="지역별_분석_데이터.csv",
            mime="text/csv"
        )

st.markdown("---")
st.caption("🗺️ 지역별 분석 페이지")
