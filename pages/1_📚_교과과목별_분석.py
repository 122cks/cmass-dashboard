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

st.set_page_config(page_title="교과/과목별 분석", page_icon="📚", layout="wide")
apply_custom_style()

# Get data from session state
if 'total_df' not in st.session_state or 'order_df' not in st.session_state:
    st.error("데이터를 불러올 수 없습니다. 메인 페이지로 돌아가주세요.")
    st.stop()

total_df = st.session_state['total_df']
order_df = st.session_state['order_df'].copy()
market_analysis = st.session_state.get('market_analysis', pd.DataFrame())  # 시장 분석 데이터

# 학년도 필터 추가 (기본값: 2026)
selected_years, comparison_mode = add_year_filter_sidebar(order_df, default_year='2026')
if selected_years:
    order_df = filter_by_years(order_df, selected_years)

st.title("📚 교과/과목별 상세 분석")
st.markdown("---")

# 연도별 비교 모드 안내
if comparison_mode:
    st.info("📊 **연도 비교 모드**: 2025년과 2026년 데이터를 비교하여 부수, 학교점유율, 학생수점유율의 증감을 확인할 수 있습니다.")

# Helper function to classify subject by school level
def get_school_level_from_subject(subject_name):
    """과목명으로 중학교/고등학교 구분"""
    if pd.isna(subject_name):
        return '미분류'
    
    subject_str = str(subject_name)
    
    # 고등학교 전용 과목 키워드
    high_keywords = ['Ⅰ', 'Ⅱ', 'I', 'II', '기하', '확률과 통계', '미적분', 
                     '물리학', '화학', '생명과학', '지구과학',
                     '한국지리', '세계지리', '동아시아사', '세계사',
                     '경제', '정치와 법', '사회·문화', '생활과 윤리', '윤리와 사상',
                     '실용', '심화', '진로']
    
    for keyword in high_keywords:
        if keyword in subject_str:
            return '고등학교'
    
    # 중학교 전용 과목 키워드
    middle_keywords = ['중학', '중등']
    for keyword in middle_keywords:
        if keyword in subject_str:
            return '중학교'
    
    # 기본 과목 (국어, 수학, 영어, 사회, 과학, 역사 등)은 문맥으로 판단 어려우므로
    # 학교급 정보가 있으면 그것을 사용하고, 없으면 미분류로 처리
    return '미분류'

# Modal for detailed subject info
@st.dialog("📖 과목 상세 정보", width="large")
def show_subject_detail(subject_name, book_code):
    """과목별 상세 정보 모달"""
    st.subheader(f"📚 {subject_name}")
    
    # 해당 과목의 모든 주문 데이터
    book_code_col = '도서코드(교지명구분)' if '도서코드(교지명구분)' in st.session_state['order_df'].columns else '도서코드'
    subject_orders = st.session_state['order_df'][st.session_state['order_df'][book_code_col] == book_code].copy()
    
    # 기본 통계
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 주문 부수", f"{subject_orders['부수'].sum():,.0f}부")
    with col2:
        school_col = '정보공시학교코드' if '정보공시학교코드' in subject_orders.columns else '학교코드'
        st.metric("주문 학교 수", f"{subject_orders[school_col].nunique():,}개")
    with col3:
        st.metric("총 주문 금액", f"{subject_orders['금액'].sum():,.0f}원" if '금액' in subject_orders.columns else "N/A")
    with col4:
        st.metric("학교당 평균", f"{subject_orders['부수'].sum() / subject_orders[school_col].nunique():.1f}부")
    
    st.markdown("---")
    
    # 탭으로 구분
    detail_tab1, detail_tab2, detail_tab3 = st.tabs(["🏫 학교별 주문", "📅 학년도별 분석", "🗺️ 지역별 분포"])
    
    with detail_tab1:
        st.subheader("학교별 주문 현황")
        
        agg_dict = {'부수': 'sum'}
        col_names = ['학교명', '주문부수']
        
        if '금액' in subject_orders.columns:
            agg_dict['금액'] = 'sum'
            col_names.append('주문금액')
        
        if '시도' in subject_orders.columns:
            agg_dict['시도'] = 'first'
            col_names.append('지역')
        
        school_orders = subject_orders.groupby('학교명').agg(agg_dict).reset_index()
        school_orders.columns = col_names
        school_orders = school_orders.sort_values('주문부수', ascending=False)
        
        # 차트
        fig = px.bar(
            school_orders.head(20),
            x='주문부수',
            y='학교명',
            orientation='h',
            title="상위 20개 학교 주문 현황",
            color='지역' if '지역' in school_orders.columns else None
        )
        fig.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
        
        # 테이블
        st.dataframe(
            school_orders.style.format({
                '주문부수': '{:,.0f}',
                '주문금액': '{:,.0f}'
            }),
            use_container_width=True,
            height=300
        )
    
    with detail_tab2:
        st.subheader("학년도별 주문 추이")
        if '학년도' in subject_orders.columns:
            year_orders = subject_orders.groupby('학년도')['부수'].sum().reset_index()
            year_orders.columns = ['학년도', '주문부수']
            
            fig = px.line(
                year_orders,
                x='학년도',
                y='주문부수',
                markers=True,
                title="학년도별 주문 추이"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # 학년도별 상세
            st.dataframe(
                year_orders.style.format({'주문부수': '{:,.0f}'}),
                use_container_width=True
            )
        else:
            st.info("학년도 정보가 없습니다.")
    
    with detail_tab3:
        st.subheader("지역별 분포")
        if '시도' in subject_orders.columns:
            region_orders = subject_orders.groupby('시도').agg({
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

# Sidebar Filters
st.sidebar.header("🔍 필터 옵션")

# School Level Filter
if '학교급명' in order_df.columns:
    # 학교급명 고유값 확인 및 정렬
    unique_levels = order_df['학교급명'].dropna().unique().tolist()
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
        order_df = order_df[order_df['학교급명'] == selected_school_level].copy()
        st.sidebar.info(f"선택된 학교급: {selected_school_level}")

# Apply common filters
filtered_order_df = apply_common_filters(order_df)

# Show filter summary
show_filter_summary(filtered_order_df, st.session_state['order_df'])

st.sidebar.markdown("---")
st.sidebar.info(f"📊 필터링된 데이터: {len(filtered_order_df):,}건")

# 성과 알림 설정
st.sidebar.markdown("---")
st.sidebar.header("🔔 성과 알림 설정")
has_year = '학년도' in filtered_order_df.columns
compare_options = ['없음']
if has_year:
    compare_options.append('전년(학년도)')
compare_by = st.sidebar.selectbox("비교 기준", compare_options)
up_threshold = st.sidebar.number_input("상승 임계값 (퍼센트포인트)", min_value=0.0, value=10.0, step=1.0)
down_threshold = st.sidebar.number_input("감소 임계값 (퍼센트포인트)", min_value=0.0, value=10.0, step=1.0)

# Main Analysis
col1, col2, col3 = st.columns(3)

with col1:
    total_orders = filtered_order_df['부수'].sum()
    st.metric("총 주문 부수", f"{total_orders:,.0f}부")

with col2:
    total_amount = filtered_order_df['금액'].sum() if '금액' in filtered_order_df.columns else 0
    st.metric("총 주문 금액", f"{total_amount:,.0f}원")

with col3:
    subject_col = '교과서명_구분' if '교과서명_구분' in filtered_order_df.columns else '교과서명'
    unique_subjects = filtered_order_df[subject_col].nunique() if subject_col in filtered_order_df.columns else 0
    st.metric("과목 종류", f"{unique_subjects}개")

# 연도 비교 모드일 경우 비교 메트릭 표시
if comparison_mode and '학년도' in filtered_order_df.columns:
    df_2025 = filtered_order_df[filtered_order_df['학년도'].astype(str) == '2025']
    df_2026 = filtered_order_df[filtered_order_df['학년도'].astype(str) == '2026']
    if not df_2025.empty and not df_2026.empty:
        create_year_comparison_metrics(df_2025, df_2026, {'부수': '주문 부수', '금액': '주문 금액'})

st.markdown("---")
# Tab Layout
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 과목별 현황", "📈 교과군 분석", "🏫 중등/고등 분석", "🎯 상세 분석", "💡 성과 인사이트", "📋 데이터 테이블"])

with tab1:
    st.subheader("과목별 주문 현황")
    
    # Group by BOOK CODE first (도서코드로 먼저 구분!)
    book_code_col = '도서코드(교지명구분)' if '도서코드(교지명구분)' in filtered_order_df.columns else '도서코드'
    school_code_col = '정보공시학교코드' if '정보공시학교코드' in filtered_order_df.columns else '학교코드'
    
    if book_code_col in filtered_order_df.columns:
        subject_stats = filtered_order_df.groupby(book_code_col).agg({
            '부수': 'sum',
            '금액': 'sum' if '금액' in filtered_order_df.columns else 'count',
            school_code_col: 'nunique',
            '교과서명_구분': 'first' if '교과서명_구분' in filtered_order_df.columns else 'count'
        }).reset_index()
        
        subject_stats.columns = ['도서코드', '주문부수', '주문금액', '학교수', '과목명']
    else:
        # Fallback: 교과서명_구분으로 그룹화
        subject_col = '교과서명_구분' if '교과서명_구분' in filtered_order_df.columns else '과목명'
        subject_stats = filtered_order_df.groupby(subject_col).agg({
            '부수': 'sum',
            '금액': 'sum' if '금액' in filtered_order_df.columns else 'count',
            school_code_col: 'nunique'
        }).reset_index()
        
        subject_stats.columns = ['과목명', '주문부수', '주문금액', '학교수']
    
    subject_stats = subject_stats.sort_values('주문부수', ascending=False)
    # ----------------------------
    # 채택(주문) 학교수 및 학생수 기반 점유율 계산
    # ----------------------------
    # 학교 코드 컬럼 이름 확인 (order vs total df 차이 처리)
    total_school_code_col = None
    for c in total_df.columns:
        if '학교코드' in c:
            total_school_code_col = c
            break

    student_col = '학생수(계)' if '학생수(계)' in total_df.columns else None

    # 학교 -> 학생수 매핑 생성
    school_student_map = {}
    if total_school_code_col and student_col:
        school_student_map = total_df.dropna(subset=[total_school_code_col]).set_index(total_school_code_col)[student_col].to_dict()

    # 과목 기준 컬럼 결정 (도서코드 우선)
    subject_group_col = '도서코드' if '도서코드' in subject_stats.columns else '과목명'

    # 채택 학교수 및 채택 학교 학생수 계산
    adopted_school_counts = []
    adopted_school_students = []
    for _, r in subject_stats.iterrows():
        key = r[subject_group_col]
        if subject_group_col == '도서코드':
            sel = filtered_order_df[filtered_order_df[book_code_col].astype(str) == str(key)]
        else:
            sel = filtered_order_df[filtered_order_df[subject_col] == key] if 'subject_col' in locals() else filtered_order_df[filtered_order_df['과목명'] == key]

        adopted_schools = sel[school_code_col].dropna().unique().tolist() if school_code_col in sel.columns else []
        adopted_school_counts.append(len(adopted_schools))

        # 해당 채택 학교들의 학생수 합
        adopted_students = 0
        if school_student_map and len(adopted_schools) > 0:
            for sc in adopted_schools:
                # 매핑 키 유형 일관화: 문자열/숫자
                adopted_students += float(school_student_map.get(sc, school_student_map.get(str(sc), 0)))
        adopted_school_students.append(adopted_students)

    subject_stats['채택학교수'] = adopted_school_counts
    subject_stats['채택학교학생수'] = adopted_school_students

    # 전체 담당(분석) 기준 학생수 및 학교수(전체 시장규모) 사용
    total_students_filtered = total_df['학생수(계)'].sum() if '학생수(계)' in total_df.columns else 0
    total_school_count = total_df[total_school_code_col].nunique() if total_school_code_col else 0

    # 학교 점유율 및 학생수 점유율
    subject_stats['학교점유율(%)'] = (subject_stats['채택학교수'] / subject_stats.get('학교수', total_school_count).replace(0, total_school_count) * 100).fillna(0)
    subject_stats['학생수점유율(%)'] = (subject_stats['채택학교학생수'] / total_students_filtered * 100).fillna(0)

    # 이전 기간(전년) 대비 학생수 점유율 계산 및 알림 생성
    prev_shares = {}
    if compare_by == '전년(학년도)' and '학년도' in filtered_order_df.columns:
        try:
            # current year determined from filtered data
            current_year_vals = pd.to_numeric(filtered_order_df['학년도'], errors='coerce').dropna().astype(int)
            if not current_year_vals.empty:
                current_year = int(current_year_vals.max())
                prev_year = current_year - 1
                prev_df = filtered_order_df[filtered_order_df['학년도'].astype(str) == str(prev_year)]

                # compute prev adopted students per subject
                for _, r in subject_stats.iterrows():
                    key = r[subject_group_col]
                    if subject_group_col == '도서코드':
                        sel_prev = prev_df[prev_df[book_code_col].astype(str) == str(key)]
                    else:
                        sel_prev = prev_df[prev_df[subject_col] == key] if 'subject_col' in locals() else prev_df[prev_df['과목명'] == key]

                    prev_adopted_schools = sel_prev[school_code_col].dropna().unique().tolist() if school_code_col in sel_prev.columns else []
                    prev_adopted_students = 0
                    if school_student_map and len(prev_adopted_schools) > 0:
                        for sc in prev_adopted_schools:
                            prev_adopted_students += float(school_student_map.get(sc, school_student_map.get(str(sc), 0)))

                    prev_share = (prev_adopted_students / total_students_filtered * 100) if total_students_filtered > 0 else 0
                    prev_shares[key] = prev_share
        except Exception:
            prev_shares = {}

    # 알림 리스트 생성
    alerts_up = []
    alerts_down = []
    if prev_shares:
        for _, r in subject_stats.iterrows():
            key = r[subject_group_col]
            cur_share = r.get('학생수점유율(%)', 0)
            prev_share = prev_shares.get(key, None)
            if prev_share is None:
                continue
            diff = cur_share - prev_share
            if diff >= up_threshold:
                alerts_up.append((r.get('과목명', key), cur_share, prev_share, diff))
            if diff <= -down_threshold:
                alerts_down.append((r.get('과목명', key), cur_share, prev_share, diff))
    
    # 정확한 시장점유율 계산 (market_analysis 데이터 활용)
    if not market_analysis.empty and '도서코드' in market_analysis.columns:
        # 필요한 컬럼이 모두 있는지 확인
        required_cols = ['도서코드', '주문부수', '시장규모', '과목명']
        if all(col in market_analysis.columns for col in required_cols):
            # 도서코드별 시장 규모 및 점유율 계산
            market_summary = market_analysis.groupby('도서코드').agg({
                '주문부수': 'sum',
                '시장규모': 'sum',
                '과목명': 'first'
            }).reset_index()
            market_summary['점유율(%)'] = (market_summary['주문부수'] / market_summary['시장규모'] * 100).fillna(0)
            
            # subject_stats에 병합
            if '도서코드' in subject_stats.columns:
                subject_stats = pd.merge(
                    subject_stats,
                    market_summary[['도서코드', '시장규모', '점유율(%)']],
                    on='도서코드',
                    how='left'
                )
            else:
                subject_stats['시장규모'] = 0
                subject_stats['점유율(%)'] = 0
        else:
            # Fallback: 기존 방식
            total_students_filtered = total_df['학생수(계)'].sum()
            subject_stats['시장규모'] = total_students_filtered
            subject_stats['점유율(%)'] = (subject_stats['주문부수'] / total_students_filtered * 100).fillna(0)
    else:
        # Fallback: 기존 방식 (전체 학생수 기준)
        total_students_filtered = total_df['학생수(계)'].sum()
        subject_stats['시장규모'] = total_students_filtered
        subject_stats['점유율(%)'] = (subject_stats['주문부수'] / total_students_filtered * 100).fillna(0)
    
    # 과목 클릭 안내
    st.info("💡 **아래 테이블에서 과목을 클릭**하면 해당 과목의 상세 정보를 확인할 수 있습니다.")
    
    # 학교급 구분 추가 (학교급 또는 학교급명 컬럼 사용, 없으면 과목명으로 추정)
    school_level_col = '학교급' if '학교급' in filtered_order_df.columns else ('학교급명' if '학교급명' in filtered_order_df.columns else None)
    
    if school_level_col:
        # 도서코드별로 학교급 매핑
        book_school_level = filtered_order_df.groupby('과목명')[school_level_col].first().to_dict()
        subject_stats['학교급'] = subject_stats['과목명'].map(book_school_level).fillna('미분류')
    else:
        subject_stats['학교급'] = subject_stats['과목명'].apply(get_school_level_from_subject)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Bar chart with school level color coding
        fig = px.bar(
            subject_stats.head(20),
            x='과목명',
            y='주문부수',
            title="과목별 주문 부수 TOP 20 (🔵중학교 / 🔴고등학교)",
            text='주문부수',
            color='학교급',
            color_discrete_map={
                '중학교': '#4A90E2',  # 파란색
                '고등학교': '#E94B3C',  # 빨간색
                '미분류': '#9E9E9E'  # 회색
            }
        )
        fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig.update_layout(height=500, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
        
        # 추가: 학생수 기준 점유율 막대 차트 (TOP 20)
        if '학생수점유율(%)' in subject_stats.columns:
            fig_share = px.bar(
                subject_stats.sort_values('학생수점유율(%)', ascending=False).head(20),
                x='과목명',
                y='학생수점유율(%)',
                title='과목별 학생수 점유율 TOP 20',
                text='학생수점유율(%)',
                color='학교급',
                color_discrete_map={'중학교': '#4A90E2', '고등학교': '#E94B3C', '미분류': '#9E9E9E'}
            )
            fig_share.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
            fig_share.update_layout(height=400)
            # hover에 채택학교수/채택학교학생수 노출
            if '채택학교수' in subject_stats.columns and '채택학교학생수' in subject_stats.columns:
                fig_share.update_traces(hovertemplate='%{x}<br>학생수점유율: %{y:.2f}%<br>채택학교수: %{customdata[0]}<br>채택학교학생수: %{customdata[1]:,.0f}')
                fig_share.update_traces(customdata=subject_stats.sort_values('학생수점유율(%)').head(20)[['채택학교수','채택학교학생수']].values)
            st.plotly_chart(fig_share, use_container_width=True)

            # 성과 알림 표시
            if compare_by != '없음':
                with st.expander('🔔 과목별 성과 알림 (학생수 점유율 변화)', expanded=True):
                    if not prev_shares:
                        st.info('비교 대상 기간의 데이터가 충분하지 않습니다.')
                    else:
                        if alerts_up:
                            st.success(f"상승 알림: {len(alerts_up)}개 과목")
                            for name, cur, prev, diff in alerts_up:
                                st.write(f"▲ {name}: 현재 {cur:.2f}% (이전 {prev:.2f}%), 차이 +{diff:.2f}pp")
                        else:
                            st.write('상승 알림 없음')
                        if alerts_down:
                            st.error(f"감소 알림: {len(alerts_down)}개 과목")
                            for name, cur, prev, diff in alerts_down:
                                st.write(f"▼ {name}: 현재 {cur:.2f}% (이전 {prev:.2f}%), 차이 {diff:.2f}pp")
                        else:
                            st.write('감소 알림 없음')
    
    with col2:
        # Pie chart for top subjects
        fig_pie = px.pie(
            subject_stats.head(10),
            values='주문부수',
            names='과목명',
            title="과목별 비중 TOP 10"
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
    
    # 클릭 가능한 과목 테이블
    st.markdown("### 📋 과목별 상세 데이터 (클릭하여 상세보기)")
    
    # 도서코드 컬럼이 있는지 확인
    has_book_code = '도서코드' in subject_stats.columns
    
    # Display top 20 subjects with click buttons
    for idx, row in subject_stats.head(20).iterrows():
        col_btn, col_name, col_orders, col_schools, col_share = st.columns([1, 3, 2, 2, 2])
        
        with col_btn:
            book_code = row['도서코드'] if has_book_code else None
            if st.button("📖", key=f"detail_btn_{idx}", help="상세 정보 보기"):
                show_subject_detail(row['과목명'], book_code)
        
        with col_name:
            st.write(f"**{row['과목명']}**")
        with col_orders:
            st.write(f"{row['주문부수']:,.0f}부")
        with col_schools:
            st.write(f"{row['학교수']:,.0f}개교")
        with col_share:
            st.write(f"{row.get('학생수점유율(%)', row.get('점유율(%)', 0)):.1f}%")

with tab2:
    st.subheader("교과군별 분석")
    
    if '교과군' in filtered_order_df.columns:
        # Group by subject group
        group_stats = filtered_order_df.groupby('교과군').agg({
            '부수': 'sum',
            '금액': 'sum' if '금액' in filtered_order_df.columns else 'count',
            '과목명': 'nunique'
        }).reset_index()
        
        group_stats.columns = ['교과군', '주문부수', '주문금액', '과목수']
        group_stats = group_stats.sort_values('주문부수', ascending=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Horizontal bar chart
            fig = px.bar(
                group_stats,
                y='교과군',
                x='주문부수',
                title="교과군별 주문 부수",
                orientation='h',
                text='주문부수',
                color='주문부수',
                color_continuous_scale='Viridis'
            )
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Treemap
            fig_tree = px.treemap(
                group_stats,
                path=['교과군'],
                values='주문부수',
                title="교과군별 점유 비율 (Treemap)",
                color='주문부수',
                color_continuous_scale='RdYlGn'
            )
            fig_tree.update_layout(height=400)
            st.plotly_chart(fig_tree, use_container_width=True)
        
        # Detailed breakdown by subject group
        st.markdown("---")
        st.subheader("교과군별 상세 내역")
        
        for group in group_stats['교과군'].head(5):
            with st.expander(f"📖 {group}"):
                group_data = filtered_order_df[filtered_order_df['교과군'] == group]
                
                # 도서코드 기준으로 그룹화
                book_code_col = '도서코드(교지명구분)' if '도서코드(교지명구분)' in group_data.columns else '도서코드'
                if book_code_col in group_data.columns:
                    subject_breakdown = group_data.groupby(book_code_col).agg({
                        '부수': 'sum',
                        '교과서명_구분': 'first' if '교과서명_구분' in group_data.columns else 'count'
                    })
                    subject_breakdown.columns = ['주문부수', '과목명']
                    subject_breakdown = subject_breakdown.sort_values('주문부수', ascending=False)
                else:
                    subject_col = '교과서명_구분' if '교과서명_구분' in group_data.columns else '과목명'
                    subject_breakdown = group_data.groupby(subject_col)['부수'].sum().sort_values(ascending=False)
                    subject_breakdown = pd.DataFrame({'과목명': subject_breakdown.index, '주문부수': subject_breakdown.values})
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    for _, row in subject_breakdown.iterrows():
                        st.write(f"• **{row['과목명']}**: {row['주문부수']:,}부")
                
                with col2:
                    fig = px.bar(
                        subject_breakdown,
                        x='주문부수',
                        y='과목명',
                        orientation='h',
                        title=f"{group} - 과목별 분포"
                    )
                    fig.update_layout(height=max(300, len(subject_breakdown) * 30))
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("교과군 정보가 없습니다.")

with tab3:
    st.subheader("� 중등/고등학교 상세 분석")
    
    # Get product info if available
    product_df = st.session_state.get('product_df', pd.DataFrame())
    
    # Merge order data with product info to get school level
    if not product_df.empty and '학교급' in product_df.columns and '코드' in product_df.columns:
        # 도서코드 컬럼 찾기
        book_code_col = None
        for col in ['도서코드(교지명구분)', '도서코드', '과목코드']:
            if col in filtered_order_df.columns:
                book_code_col = col
                break
        
        if book_code_col:
            # 타입 통일 (문자열로 변환)
            product_merge = product_df[['코드', '학교급', '교과군', '교과서명']].drop_duplicates().copy()
            product_merge['코드'] = product_merge['코드'].astype(str)
            
            filtered_order_copy = filtered_order_df.copy()
            filtered_order_copy[book_code_col] = filtered_order_copy[book_code_col].astype(str)
            
            # Merge with product data
            order_with_level = pd.merge(
                filtered_order_copy,
                product_merge,
                left_on=book_code_col,
                right_on='코드',
                how='left'
            )
        else:
            order_with_level = filtered_order_df.copy()
    else:
        order_with_level = filtered_order_df.copy()
    
    # School level comparison
    if '학교급명' in filtered_order_df.columns:
        school_levels = filtered_order_df['학교급명'].unique()
        middle_high = [s for s in school_levels if '중학교' in str(s) or '고등학교' in str(s)]
        
        if middle_high:
            # Statistics by school level
            school_code_col = '정보공시학교코드' if '정보공시학교코드' in filtered_order_df.columns else '학교코드'
            
            level_stats = filtered_order_df[filtered_order_df['학교급명'].isin(middle_high)].groupby('학교급명').agg({
                '부수': 'sum',
                '금액': 'sum' if '금액' in filtered_order_df.columns else 'count',
                '과목명': 'nunique',
                school_code_col: 'nunique'
            }).reset_index()
            level_stats.columns = ['학교급', '주문부수', '주문금액', '과목수', '학교수']
            
            # Display metrics
            cols = st.columns(len(middle_high))
            for idx, (_, row) in enumerate(level_stats.iterrows()):
                with cols[idx]:
                    level_emoji = '🎓' if '중학교' in row['학교급'] else '🏫'
                    st.markdown(f"""
                    <div style="border: 2px solid {'#4A90E2' if '중학교' in row['학교급'] else '#E94B3C'}; 
                                border-radius: 15px; padding: 20px; margin: 10px 0;">
                        <h3 style="text-align: center;">{level_emoji} {row['학교급']}</h3>
                        <p><b>주문:</b> {row['주문부수']:,.0f}부</p>
                        <p><b>금액:</b> {row['주문금액']:,.0f}원</p>
                        <p><b>과목:</b> {row['과목수']}개</p>
                        <p><b>학교:</b> {row['학교수']}개교</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Comparison charts
            col1, col2 = st.columns(2)
            
            with col1:
                # Orders comparison
                fig1 = px.bar(
                    level_stats,
                    x='학교급',
                    y='주문부수',
                    title="중등/고등 주문량 비교",
                    text='주문부수',
                    color='학교급',
                    color_discrete_map={'중학교': '#4A90E2', '고등학교': '#E94B3C'}
                )
                fig1.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                # Pie chart
                fig2 = px.pie(
                    level_stats,
                    values='주문부수',
                    names='학교급',
                    title="중등/고등 주문 비중",
                    color='학교급',
                    color_discrete_map={'중학교': '#4A90E2', '고등학교': '#E94B3C'}
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            # Subject comparison by school level
            st.markdown("---")
            st.subheader("📚 학교급별 과목 분석")
            
            subject_by_level = filtered_order_df[filtered_order_df['학교급명'].isin(middle_high)].groupby(['학교급명', '과목명'])['부수'].sum().reset_index()
            
            # Get top subjects for each level
            col1, col2 = st.columns(2)
            
            with col1:
                # Middle school subjects
                middle_subjects = subject_by_level[subject_by_level['학교급명'].str.contains('중학교', na=False, regex=False)].sort_values('부수', ascending=False).head(10)
                
                if not middle_subjects.empty:
                    fig_middle = px.bar(
                        middle_subjects,
                        x='과목명',
                        y='부수',
                        title="🎓 중학교 주요 과목 TOP 10",
                        text='부수',
                        color='부수',
                        color_continuous_scale='Blues'
                    )
                    fig_middle.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                    fig_middle.update_layout(xaxis_tickangle=-45, showlegend=False)
                    st.plotly_chart(fig_middle, use_container_width=True)
                else:
                    st.info("중학교 데이터가 없습니다.")
            
            with col2:
                # High school subjects
                high_subjects = subject_by_level[subject_by_level['학교급명'].str.contains('고등학교', na=False, regex=False)].sort_values('부수', ascending=False).head(10)
                
                if not high_subjects.empty:
                    fig_high = px.bar(
                        high_subjects,
                        x='과목명',
                        y='부수',
                        title="🏫 고등학교 주요 과목 TOP 10",
                        text='부수',
                        color='부수',
                        color_continuous_scale='Reds'
                    )
                    fig_high.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                    fig_high.update_layout(xaxis_tickangle=-45, showlegend=False)
                    st.plotly_chart(fig_high, use_container_width=True)
                else:
                    st.info("고등학교 데이터가 없습니다.")
            
            # Regional distribution by school level
            st.markdown("---")
            st.subheader("🗺️ 학교급별 지역 분포")
            
            if '시도교육청' in filtered_order_df.columns:
                regional_level = filtered_order_df[filtered_order_df['학교급명'].isin(middle_high)].groupby(['시도교육청', '학교급명'])['부수'].sum().reset_index()
                
                fig_regional = px.bar(
                    regional_level,
                    x='시도교육청',
                    y='부수',
                    color='학교급명',
                    title="중등/고등 지역별 분포",
                    barmode='group',
                    text='부수',
                    color_discrete_map={'중학교': '#4A90E2', '고등학교': '#E94B3C'}
                )
                fig_regional.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                fig_regional.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_regional, use_container_width=True)
            
            # Subject group comparison
            st.markdown("---")
            st.subheader("📖 학교급별 교과군 비교")
            
            if '교과군' in filtered_order_df.columns:
                group_level = filtered_order_df[filtered_order_df['학교급명'].isin(middle_high)].groupby(['교과군', '학교급명'])['부수'].sum().reset_index()
                
                # Heatmap
                pivot_group_level = group_level.pivot(index='교과군', columns='학교급명', values='부수').fillna(0)
                
                fig_heatmap = px.imshow(
                    pivot_group_level,
                    title="교과군 × 학교급 주문량 히트맵",
                    labels=dict(x="학교급", y="교과군", color="주문량"),
                    aspect="auto",
                    color_continuous_scale='YlOrRd'
                )
                fig_heatmap.update_layout(height=500)
                st.plotly_chart(fig_heatmap, use_container_width=True)
        else:
            st.info("중학교/고등학교 데이터가 없습니다.")
    else:
        st.info("학교급 정보가 없습니다.")

with tab4:
    st.subheader("�🎯 심화 분석")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Top performing subjects
        st.markdown("#### 📈 최고 실적 과목")
        top_subjects = subject_stats.head(10)
        
        for idx, row in top_subjects.iterrows():
            with st.container():
                st.markdown(f"""
                **{row['과목명']}**  
                📦 주문: {row['주문부수']:,.0f}부 | 💰 금액: {row['주문금액']:,.0f}원  
                🏫 학교수: {row['학교수']}개 | 📊 점유율: {row['점유율(%)']:.2f}%
                """)
                st.progress(min(row.get('학생수점유율(%)', row.get('점유율(%)', 0)) / 100, 1.0))
    
    with col2:
        # Subject performance ranking
        st.markdown("#### 🏆 과목별 성과 순위")
        
        # Calculate average order per school
        subject_stats['학교당평균'] = subject_stats['주문부수'] / subject_stats['학교수']
        subject_stats_ranked = subject_stats.sort_values('학교당평균', ascending=False).head(10)
        
        fig = px.scatter(
            subject_stats_ranked,
            x='학교수',
            y='학교당평균',
            size='주문부수',
            color='학생수점유율(%)' if '학생수점유율(%)' in subject_stats_ranked.columns else '점유율(%)',
            hover_name='과목명',
            title="과목별 효율성 분석 (학교수 vs 학교당 평균)",
            labels={'학교수': '주문 학교 수', '학교당평균': '학교당 평균 주문량'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Heatmap if region and subject data available
    st.markdown("---")
    st.markdown("#### 🗺️ 지역 × 과목 히트맵")
    
    if '시도교육청' in filtered_order_df.columns:
        # Use the same subject column as in subject_stats
        subject_col = '교과서명_구분' if '교과서명_구분' in filtered_order_df.columns else '과목명'
        
        # Create pivot table for heatmap
        pivot_data = filtered_order_df.pivot_table(
            index='시도교육청',
            columns=subject_col,
            values='부수',
            aggfunc='sum',
            fill_value=0
        )
        
        # Select top subjects and regions (using the same column names from subject_stats)
        top_subjects_list = subject_stats.head(10)['과목명'].tolist()
        
        # Filter only the columns that exist in pivot_data
        top_subjects_list = [s for s in top_subjects_list if s in pivot_data.columns]
        
        if top_subjects_list:
            # 중복 컬럼 제거 (unique 적용)
            unique_subjects = list(dict.fromkeys(top_subjects_list))
            pivot_data_filtered = pivot_data[unique_subjects].copy()
            
            fig_heatmap = px.imshow(
                pivot_data_filtered,
                title="지역별 × 과목별 주문 분포 (TOP 10 과목)",
                labels=dict(x="과목", y="지역", color="주문 부수"),
                aspect="auto",
                color_continuous_scale='YlOrRd'
            )
            fig_heatmap.update_layout(height=600)
            st.plotly_chart(fig_heatmap, use_container_width=True)
        else:
            st.info("히트맵을 표시할 데이터가 충분하지 않습니다.")

with tab5:
    st.subheader("💡 성과 인사이트 및 분석")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🏆 상위 성과 과목 (TOP 5)")
        top5 = subject_stats.head(5)
        
        for idx, row in top5.iterrows():
            # Performance card with gradient
            efficiency_score = row['학교당평균'] if '학교당평균' in row else 0
            pct = row.get('학생수점유율(%)', row.get('점유율(%)', 0))
            color = "#28a745" if pct > 50 else "#ffc107" if pct > 30 else "#dc3545"
            
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, {color}20 0%, {color}40 100%); 
                        padding: 15px; border-radius: 8px; margin-bottom: 10px;
                        border-left: 4px solid {color};'>
                <h4 style='margin:0; color: {color};'>{row['과목명']}</h4>
                <p style='margin: 5px 0;'>
                    <b>주문 부수:</b> {row['주문부수']:,.0f}부 | 
                    <b>점유율:</b> {row.get('학생수점유율(%)', row.get('점유율(%)', 0)):.1f}%
                </p>
                <p style='margin: 5px 0;'>
                    <b>학교 수:</b> {row['학교수']:,.0f}개 | 
                    <b>학교당 평균:</b> {efficiency_score:.1f}부
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("#### 📊 성과 분석 지표")
        
        # Performance metrics
        if '학생수점유율(%)' in subject_stats.columns:
            high_performers = len(subject_stats[subject_stats['학생수점유율(%)'] > 50])
            mid_performers = len(subject_stats[(subject_stats['학생수점유율(%)'] >= 30) & (subject_stats['학생수점유율(%)'] <= 50)])
            low_performers = len(subject_stats[subject_stats['학생수점유율(%)'] < 30])
        else:
            high_performers = len(subject_stats[subject_stats['점유율(%)'] > 50])
            mid_performers = len(subject_stats[(subject_stats['점유율(%)'] >= 30) & (subject_stats['점유율(%)'] <= 50)])
            low_performers = len(subject_stats[subject_stats['점유율(%)'] < 30])
        
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric("우수 (50%↑)", f"{high_performers}개", help="점유율 50% 이상")
        metric_col2.metric("보통 (30~50%)", f"{mid_performers}개", help="점유율 30~50%")
        metric_col3.metric("개선 필요 (30%↓)", f"{low_performers}개", help="점유율 30% 미만")
    
    with col2:
        st.markdown("#### ⚠️ 개선 필요 과목 (하위 5)")
        bottom5 = subject_stats.tail(5).sort_values('주문부수', ascending=True)
        
        for idx, row in bottom5.iterrows():
            st.markdown(f"""
            <div style='background: #fff3cd; padding: 12px; border-radius: 8px; 
                        margin-bottom: 10px; border-left: 4px solid #ffc107;'>
                <p style='margin:0;'><b>{row['과목명']}</b></p>
                <p style='margin: 5px 0; font-size: 0.9em;'>
                    주문: {row['주문부수']:,.0f}부 | 점유율: {row.get('학생수점유율(%)', row.get('점유율(%)', 0)):.1f}% | 
                    학교: {row['학교수']:,.0f}개
                </p>
                <p style='margin: 0; font-size: 0.85em; color: #856404;'>
                    💡 개선 포인트: 학교 침투율 제고 필요
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("#### 🎯 전략적 제안")
        
        # Strategic recommendations
        avg_share = subject_stats['학생수점유율(%)'].mean() if '학생수점유율(%)' in subject_stats.columns else subject_stats['점유율(%)'].mean()
        avg_schools = subject_stats['학교수'].mean()
        
        st.info(f"""
        **평균 점유율**: {avg_share:.1f}%  
        **평균 주문 학교 수**: {avg_schools:.0f}개
        
        **권장 액션**:
        - 상위 과목: 시장 선도 지위 유지 및 확대
        - 중위 과목: 경쟁력 강화 및 차별화 전략
        - 하위 과목: 침투율 개선 및 마케팅 강화
        """)
        
        # Competition intensity
        st.markdown("#### 🔥 경쟁 강도 분석")
        subject_stats_sorted = subject_stats.copy()
        subject_stats_sorted['경쟁강도'] = subject_stats_sorted['학교수'] / subject_stats_sorted['주문부수'] * 10000
        high_competition = subject_stats_sorted.nsmallest(5, '경쟁강도')
        
        st.warning(f"🔥 **고강도 경쟁 과목**: {', '.join(high_competition['과목명'].head(3).tolist())}")

with tab6:
    st.subheader("📋 상세 데이터 테이블")
    
    # Search functionality
    search_term = st.text_input("🔍 과목명 검색", "")
    
    if search_term:
        display_stats = subject_stats[subject_stats['과목명'].str.contains(search_term, case=False, na=False, regex=False)]
    else:
        display_stats = subject_stats
    
    # Display dataframe
    st.dataframe(
        display_stats.style.format({
            '주문부수': '{:,.0f}',
            '주문금액': '{:,.0f}',
            '학교수': '{:,.0f}',
            '채택학교수': '{:,.0f}',
            '채택학교학생수': '{:,.0f}',
            '학생수점유율(%)': '{:.2f}%',
            '점유율(%)': '{:.2f}%',
            '학교당평균': '{:.2f}'
        }),
        use_container_width=True,
        height=400
    )
    
    # Download button
    csv = display_stats.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 CSV 다운로드",
        data=csv,
        file_name="과목별_분석_데이터.csv",
        mime="text/csv"
    )

st.markdown("---")
st.caption("📊 교과/과목별 분석 페이지")
