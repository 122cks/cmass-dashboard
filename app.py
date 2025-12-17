import streamlit as st
import pandas as pd
import os
import sys

# Add utils directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))
from market_size import calculate_market_size_by_subject
from market_size_v2 import calculate_market_size_by_subject_v2
from market_size_distributor import calculate_distributor_market_size, calculate_subject_market_by_distributor

# Grade sorting function for distributors
def get_grade_order(grade):
    """Convert grade to number for sorting (S=1, A=2, B=3, C=4, D=5, E=6, G=7, etc.)"""
    grade_map = {'S': 1, 'A': 2, 'B': 3, 'C': 4, 'D': 5, 'E': 6, 'G': 7}
    if pd.isna(grade):
        return 999
    return grade_map.get(str(grade).upper(), 99)

def sort_by_grade(df, grade_column='총판등급'):
    """Sort dataframe by distributor grade (S -> A -> B -> C -> D)"""
    if grade_column in df.columns:
        df['_grade_order'] = df[grade_column].apply(get_grade_order)
        df = df.sort_values('_grade_order').drop('_grade_order', axis=1)
    return df

# Set page config
st.set_page_config(
    page_title="CMASS 실적표 조회 시스템",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# File Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOTAL_FILE = os.path.join(BASE_DIR, "2025년도_학년별·학급별 학생수(초중고)_전체.csv")
ORDER_FILE = os.path.join(BASE_DIR, "씨마스_22개정 주문현황_학교코드총판코드.csv")
TARGET_FILE = os.path.join(BASE_DIR, "22개정 총판별 목표.csv")
PRODUCT_FILE = os.path.join(BASE_DIR, "제품정보.csv")
DISTRIBUTOR_FILE = os.path.join(BASE_DIR, "총판정보.csv")

@st.cache_data
def load_data():
    """Load and cache all data files"""
    # Load student data
    try:
        total_df = pd.read_csv(TOTAL_FILE, encoding='cp949')
    except UnicodeDecodeError:
        total_df = pd.read_csv(TOTAL_FILE, encoding='utf-8')
    
    # Load order data
    try:
        order_df = pd.read_csv(ORDER_FILE, encoding='cp949')
    except UnicodeDecodeError:
        order_df = pd.read_csv(ORDER_FILE, encoding='utf-8')
    
    # Load target data
    try:
        target_df = pd.read_csv(TARGET_FILE, encoding='cp949')
    except UnicodeDecodeError:
        try:
            target_df = pd.read_csv(TARGET_FILE, encoding='utf-8')
        except:
            target_df = pd.DataFrame()
    
    # Load product data
    try:
        product_df = pd.read_csv(PRODUCT_FILE, encoding='cp949')
    except UnicodeDecodeError:
        try:
            product_df = pd.read_csv(PRODUCT_FILE, encoding='utf-8')
        except:
            product_df = pd.DataFrame()
    
    # Load distributor data
    try:
        distributor_df = pd.read_csv(DISTRIBUTOR_FILE, encoding='cp949')
    except UnicodeDecodeError:
        try:
            distributor_df = pd.read_csv(DISTRIBUTOR_FILE, encoding='utf-8')
        except:
            distributor_df = pd.DataFrame()

    # Clean column names
    total_df.columns = total_df.columns.str.strip()
    order_df.columns = order_df.columns.str.strip()
    if not target_df.empty:
        target_df.columns = target_df.columns.str.strip()
    if not product_df.empty:
        product_df.columns = product_df.columns.str.strip()
    if not distributor_df.empty:
        distributor_df.columns = distributor_df.columns.str.strip()

    # Ensure School Codes are strings
    if '정보공시 학교코드' in total_df.columns:
        total_df['정보공시 학교코드'] = total_df['정보공시 학교코드'].astype(str)
    if '정보공시학교코드' in order_df.columns:
        order_df['정보공시학교코드'] = order_df['정보공시학교코드'].astype(str)
    
    # Map distributor official names from total_df to use 총판명(공식)
    # Create mapping: 담당총판 -> 총판명(공식) AND 숫자코드 -> 총판명(공식)
    if not distributor_df.empty and '총판명(공식)' in distributor_df.columns:
        # Create mapping from various distributor name formats to official name
        dist_official_map = {}
        dist_code_map = {}  # 숫자코드 -> 총판명(공식) 매핑
        
        for _, row in distributor_df.iterrows():
            official_name = row.get('총판명(공식)', '')
            if pd.notna(official_name):
                # Map from 총판명, 총판명1, etc.
                for col in ['총판명', '총판명1']:
                    if col in distributor_df.columns and pd.notna(row.get(col)):
                        dist_official_map[str(row[col])] = official_name
                
                # Map from 숫자코드 (총판코드)
                if '숫자코드' in distributor_df.columns and pd.notna(row.get('숫자코드')):
                    code = str(int(row['숫자코드'])) if isinstance(row['숫자코드'], (int, float)) else str(row['숫자코드'])
                    dist_code_map[code] = official_name
        
        # Update total_df's 담당총판 to use official names
        if '담당총판' in total_df.columns:
            total_df['담당총판_공식'] = total_df['담당총판'].map(lambda x: dist_official_map.get(str(x), x) if pd.notna(x) else x)
        
        # Update order_df's 총판 to use official names
        # 1. 먼저 총판코드로 매핑 시도
        # 2. 실패하면 총판명으로 매핑 시도
        if '총판' in order_df.columns:
            order_df['총판_원본'] = order_df['총판']
            
            # 총판코드가 있으면 코드로 먼저 매핑
            if '총판코드' in order_df.columns:
                order_df['총판코드_str'] = order_df['총판코드'].astype(str)
                order_df['총판_from_code'] = order_df['총판코드_str'].map(dist_code_map)
                # 코드 매핑 성공 시 사용, 실패 시 기존 총판명 유지
                order_df['총판'] = order_df['총판_from_code'].fillna(
                    order_df['총판'].map(lambda x: dist_official_map.get(str(x), x) if pd.notna(x) else x)
                )
                order_df.drop(columns=['총판코드_str', '총판_from_code'], inplace=True)
            else:
                # 총판코드가 없으면 총판명으로만 매핑
                order_df['총판'] = order_df['총판'].map(lambda x: dist_official_map.get(str(x), x) if pd.notna(x) else x)
    
    # Merge product info to add school level to subject names
    if (not product_df.empty and '코드' in product_df.columns and '학교급' in product_df.columns
            and '도서코드(교지명구분)' in order_df.columns):
        # Create mapping from product code to school level
        # 코드 컬럼을 정수로 변환 (NaN 제거 후) → 문자열로 변환
        product_df = product_df.dropna(subset=['코드'])
        product_df['코드'] = product_df['코드'].astype(int).astype(str)
        order_df['도서코드(교지명구분)'] = order_df['도서코드(교지명구분)'].astype(str)

        # Merge to get school level, subject name and target subject info (목표과목)
        # Include '교과서명' so we can build 교과서명_구분 = [중등]/[고등] + 교과서명
        merge_cols = ['코드', '학교급', '교과군', '교과서명']
        if '2026 목표과목' in product_df.columns:
            merge_cols.append('2026 목표과목')

        product_merge = product_df[merge_cols].rename(columns={'교과군': '교과군_제품'})

        order_df = pd.merge(
            order_df,
            product_merge,
            left_on='도서코드(교지명구분)',
            right_on='코드',
            how='left'
        )

        # Add school level to subject name for clarity (중등 정보 vs 고등 정보)
        def add_school_level_to_subject(row):
            if pd.notna(row.get('학교급')) and pd.notna(row.get('교과서명')):
                school_level = str(row['학교급'])
                subject = str(row['교과서명'])
                # 학교급에서 중등/고등 추출
                if '중학교' in school_level:
                    return f'[중등] {subject}'
                elif '고등학교' in school_level:
                    return f'[고등] {subject}'
            return row.get('교과서명', '')

        order_df['교과서명_구분'] = order_df.apply(add_school_level_to_subject, axis=1)
        
        # Add 학교급명 column (copy from 학교급) for consistency
        if '학교급' in order_df.columns:
            order_df['학교급명'] = order_df['학교급']
    else:
        # If product code missing in order data, fall back to original subject name
        order_df['교과서명_구분'] = order_df.get('교과서명', '')
    
    # Add distributor grade for sorting (using already mapped official names)
    if not distributor_df.empty and '총판명(공식)' in distributor_df.columns and '등급' in distributor_df.columns:
        grade_map = {}
        for _, row in distributor_df.iterrows():
            if pd.notna(row.get('총판명(공식)')) and pd.notna(row.get('등급')):
                grade_map[row['총판명(공식)']] = row['등급']
        if '총판' in order_df.columns:
            order_df['총판등급'] = order_df['총판'].map(grade_map)
    
    # Calculate accurate market size by subject (V2: 학교별 학년 추정)
    market_analysis = calculate_market_size_by_subject_v2(order_df, total_df, product_df)
    
    # Fallback to V1 if V2 fails
    if market_analysis.empty:
        market_analysis = calculate_market_size_by_subject(order_df, total_df, product_df)
    
    # Calculate distributor market size (총판별 담당 학교 기준)
    distributor_market = calculate_distributor_market_size(total_df, order_df, distributor_df)
    
    # Calculate subject market by distributor (총판별 과목별 시장 규모)
    subject_market_by_dist = calculate_subject_market_by_distributor(total_df, order_df, product_df)
    
    # Calculate total market size by school level for comparison analysis
    # 중등 = 중학교 1,2학년 / 고등 = 고등학교 1,2학년
    market_size_by_level = {}
    if not total_df.empty:
        # 중학교 (학교급코드 = 3)
        middle_schools = total_df[total_df['학교급코드'] == 3]
        market_size_by_level['중등'] = middle_schools['1학년 학생수'].sum() + middle_schools['2학년 학생수'].sum()
        
        # 고등학교 (학교급코드 = 4)
        high_schools = total_df[total_df['학교급코드'] == 4]
        market_size_by_level['고등'] = high_schools['1학년 학생수'].sum() + high_schools['2학년 학생수'].sum()
        
        # 전체
        market_size_by_level['전체'] = market_size_by_level['중등'] + market_size_by_level['고등']

    return total_df, order_df, target_df, product_df, distributor_df, market_analysis, market_size_by_level, distributor_market, subject_market_by_dist

# Load data
try:
    total_df, order_df, target_df, product_df, distributor_df, market_analysis, market_size_by_level, distributor_market, subject_market_by_dist = load_data()
    
    # Store in session state for access across pages
    st.session_state['total_df'] = total_df
    st.session_state['order_df'] = order_df
    st.session_state['target_df'] = target_df
    st.session_state['product_df'] = product_df
    st.session_state['distributor_df'] = distributor_df
    st.session_state['market_analysis'] = market_analysis
    st.session_state['market_size_by_level'] = market_size_by_level  # Store market size by school level
    st.session_state['distributor_market'] = distributor_market  # Store distributor market size
    st.session_state['subject_market_by_dist'] = subject_market_by_dist  # Store subject market by distributor
    st.session_state['sort_by_grade'] = sort_by_grade  # Store sorting function
except FileNotFoundError as e:
    st.error(f"파일을 찾을 수 없습니다: {e}")
    st.stop()
except Exception as e:
    st.error(f"데이터 로드 중 오류 발생: {e}")
    st.stop()

# Main Page - Dashboard
st.title("📊 22개정 자사 실적표 조회 시스템")
st.markdown("### 💼 Executive Dashboard")
st.markdown("---")

# 학년도 필터 (사이드바)
st.sidebar.header("📅 학년도 선택")
if '학년도' in order_df.columns:
    years = sorted(order_df['학년도'].dropna().unique().tolist(), reverse=True)
    # 2026년도가 있으면 기본값으로, 없으면 최신 학년도
    default_year = 2026 if 2026 in years else (years[0] if years else None)
    default_index = years.index(default_year) if default_year and default_year in years else 0
    
    selected_year = st.sidebar.selectbox(
        "기준 학년도", 
        years, 
        index=default_index,
        key='main_year_filter'
    )
    
    # 선택된 학년도 데이터 필터링
    filtered_order = order_df[order_df['학년도'] == selected_year].copy()
    
    # 학년도별 비교 옵션
    if len(years) > 1:
        show_year_comparison = st.sidebar.checkbox("📊 학년도별 비교 보기", key='main_year_comparison')
else:
    filtered_order = order_df.copy()
    selected_year = None
    show_year_comparison = False

st.sidebar.markdown("---")

# Key Performance Indicators - Enhanced
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    total_students = total_df['학생수(계)'].sum()
    st.metric("2025년 전체 학생수", f"{total_students:,.0f}명", 
             help="전국 중·고등학교 전체 학생수")

with col2:
    total_orders = filtered_order['부수'].sum()
    total_revenue = filtered_order['금액'].sum() if '금액' in filtered_order.columns else 0
    year_label = f"{selected_year}년용" if selected_year else "전체"
    st.metric(f"{year_label} 주문 부수", f"{total_orders:,.0f}부",
             delta=f"₩{total_revenue/100000000:.1f}억원",
             help="총 주문 부수 및 매출액")

with col3:
    # Calculate accurate overall share from market_analysis
    if not market_analysis.empty:
        # 선택된 학년도의 시장 규모 계산
        year_market_analysis = market_analysis.copy()
        if selected_year:
            # 학년도에 따라 시장 규모 재계산 필요 시 처리
            pass
        total_market = year_market_analysis['시장규모(학생수)'].sum()
        accurate_share = (total_orders / total_market * 100) if total_market > 0 else 0
        st.metric("정확 점유율", f"{accurate_share:.2f}%", 
                 help="각 과목의 대상 학년별 시장 규모를 기준으로 계산")
    else:
        overall_share = (total_orders / total_students) * 100
        st.metric("전체 점유율", f"{overall_share:.2f}%")

with col4:
    # Count unique schools by preferred school code column (prefer 정보공시학교코드)
    preferred_cols = ['정보공시학교코드', '정보공시 학교코드', '학교코드']
    total_schools = 0
    for col in preferred_cols:
        if col in filtered_order.columns:
            total_schools = filtered_order[col].dropna().nunique()
            break
    penetration_rate = (total_schools / total_df['학교명'].nunique() * 100) if not total_df.empty else 0
    st.metric("주문 학교 수", f"{total_schools:,}개교",
             delta=f"침투율 {penetration_rate:.1f}%",
             help="우리 교과서를 주문한 학교 수")

with col5:
    # Average order per school
    avg_per_school = total_orders / total_schools if total_schools > 0 else 0
    st.metric("학교당 평균", f"{avg_per_school:,.0f}부",
             help="주문 학교당 평균 주문 부수")

st.markdown("---")

# 학년도별 비교 섹션
if show_year_comparison and len(years) > 1:
    st.header(f"📊 학년도별 성과 비교")
    
    # 모든 학년도 데이터 비교
    comparison_data = []
    for year in years:
        year_data = order_df[order_df['학년도'] == year]
        
        # 학교 수 계산
        year_schools = 0
        for col in preferred_cols:
            if col in year_data.columns:
                year_schools = year_data[col].dropna().nunique()
                break
        
        comparison_data.append({
            '학년도': f"{year}년",
            '주문부수': year_data['부수'].sum(),
            '주문금액': year_data['금액'].sum() if '금액' in year_data.columns else 0,
            '주문학교수': year_schools,
            '학교당평균': year_data['부수'].sum() / year_schools if year_schools > 0 else 0
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    
    # 비교 차트
    col1, col2 = st.columns(2)
    
    with col1:
        import plotly.express as px
        fig1 = px.bar(
            comparison_df,
            x='학년도',
            y='주문부수',
            title="학년도별 주문 부수 비교",
            text='주문부수'
        )
        fig1.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        fig2 = px.bar(
            comparison_df,
            x='학년도',
            y='주문학교수',
            title="학년도별 주문 학교 수 비교",
            text='주문학교수'
        )
        fig2.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig2, use_container_width=True)
    
    # 상세 테이블
    st.dataframe(
        comparison_df.style.format({
            '주문부수': '{:,.0f}',
            '주문금액': '{:,.0f}',
            '주문학교수': '{:,.0f}',
            '학교당평균': '{:,.1f}'
        }),
        use_container_width=True
    )
    
    st.markdown("---")

# Performance Dashboard Cards
st.header("🎯 핵심 성과 지표 (KPI)")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 20px; border-radius: 10px; color: white;'>
        <h3 style='margin:0; color: white;'>📚 교과 다양성</h3>
        <p style='font-size: 2em; margin: 10px 0; font-weight: bold;'>
            {subjects}개
        </p>
        <p style='margin:0; opacity: 0.9;'>취급 과목 종류</p>
    </div>
    """.format(subjects=filtered_order['과목명'].nunique()), unsafe_allow_html=True)

with col2:
    num_distributors = filtered_order['총판'].nunique() if '총판' in filtered_order.columns else 0
    st.markdown("""
    <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                padding: 20px; border-radius: 10px; color: white;'>
        <h3 style='margin:0; color: white;'>🏢 유통 네트워크</h3>
        <p style='font-size: 2em; margin: 10px 0; font-weight: bold;'>
            {dist}개
        </p>
        <p style='margin:0; opacity: 0.9;'>협력 총판사</p>
    </div>
    """.format(dist=num_distributors), unsafe_allow_html=True)

with col3:
    num_regions = filtered_order['시도교육청'].nunique() if '시도교육청' in filtered_order.columns else 0
    st.markdown("""
    <div style='background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                padding: 20px; border-radius: 10px; color: white;'>
        <h3 style='margin:0; color: white;'>🗺️ 지역 커버리지</h3>
        <p style='font-size: 2em; margin: 10px 0; font-weight: bold;'>
            {regions}개
        </p>
        <p style='margin:0; opacity: 0.9;'>시도교육청</p>
    </div>
    """.format(regions=num_regions), unsafe_allow_html=True)

st.markdown("---")

# Display market analysis insights
year_text = f"{selected_year}년도" if selected_year else "전체"
st.header(f"📊 시장 규모 분석 ({year_text} 기준)")
if selected_year == 2025:
    st.caption("💡 2025년도 주문한 교과서는 2025년에 사용합니다.")
else:
    st.caption("💡 2025년 주문한 교과서는 2026년에 사용합니다. 현재 1학년 → 내년 2학년을 기준으로 정확한 시장 규모를 산정했습니다.")
st.info("⚠️ 과목명의 숫자(1, 2)는 학기를 의미합니다. 예: 한국사 1 = 1학기, 한국사 2 = 2학기 (학년 아님)")

if not market_analysis.empty:
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        # Top subjects by accurate market share - Enhanced visualization
        top_accurate = market_analysis.nlargest(15, '점유율(%)')
        
        import plotly.express as px
        import plotly.graph_objects as go
        
        fig = go.Figure()
        
        # Add bar for market share
        fig.add_trace(go.Bar(
            name='점유율',
            x=top_accurate['과목명'],
            y=top_accurate['점유율(%)'],
            marker_color='#667eea',
            text=top_accurate['점유율(%)'].apply(lambda x: f'{x:.1f}%'),
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>점유율: %{y:.2f}%<extra></extra>'
        ))
        
        fig.update_layout(
            title="📚 과목별 점유율 TOP 15 (정확 시장 규모 기준)",
            xaxis_title="",
            yaxis_title="점유율 (%)",
            height=400,
            showlegend=False,
            xaxis_tickangle=-45,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🎯 시장 분석 요약")
        avg_share = market_analysis['점유율(%)'].mean()
        st.metric("평균 점유율", f"{avg_share:.2f}%")
        
        high_share = len(market_analysis[market_analysis['점유율(%)'] > 50])
        st.metric("50% 이상 과목", f"{high_share}개")
        
        total_market_size = market_analysis['시장규모(학생수)'].sum()
        st.metric("전체 대상 시장", f"{total_market_size:,.0f}명")
        
        # Market concentration
        top5_share = market_analysis.nlargest(5, '주문부수')['주문부수'].sum()
        concentration = (top5_share / total_orders * 100) if total_orders > 0 else 0
        st.metric("TOP5 집중도", f"{concentration:.1f}%",
                 help="상위 5개 과목의 주문 비중")
    
    with col3:
        st.subheader("📈 점유율 분포")
        
        # Distribution analysis
        ranges = [
            ('80% 이상', len(market_analysis[market_analysis['점유율(%)'] >= 80])),
            ('60-80%', len(market_analysis[(market_analysis['점유율(%)'] >= 60) & (market_analysis['점유율(%)'] < 80)])),
            ('40-60%', len(market_analysis[(market_analysis['점유율(%)'] >= 40) & (market_analysis['점유율(%)'] < 60)])),
            ('20-40%', len(market_analysis[(market_analysis['점유율(%)'] >= 20) & (market_analysis['점유율(%)'] < 40)])),
            ('20% 미만', len(market_analysis[market_analysis['점유율(%)'] < 20]))
        ]
        
        for label, count in ranges:
            if count > 0:
                st.write(f"**{label}**: {count}개 과목")
else:
    st.info("시장 분석 데이터를 계산중입니다...")

st.markdown("---")

# Trend Analysis Section
st.header("📈 실적 분석 & 인사이트")

tab1, tab2, tab3 = st.tabs(["🏆 TOP 성과", "📊 학교급별 분석", "🎯 전략적 인사이트"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📚 교과/과목별 TOP 10")
        subject_col = '교과서명_구분' if '교과서명_구분' in order_df.columns else '과목명'
        subject_top = order_df.groupby(subject_col)['부수'].sum().sort_values(ascending=False).head(10)
        
        fig = px.bar(
            x=subject_top.values,
            y=subject_top.index,
            orientation='h',
            text=subject_top.values,
            color=subject_top.values,
            color_continuous_scale='Blues'
        )
        fig.update_traces(texttemplate='%{text:,.0f}부', textposition='outside')
        fig.update_layout(
            showlegend=False,
            height=400,
            xaxis_title="주문 부수",
            yaxis_title="",
            margin=dict(l=200)
        )
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.subheader("🗺️ 지역별 TOP 10")
        region_top = order_df.groupby('시도교육청')['부수'].sum().sort_values(ascending=False).head(10)
        
        fig = px.bar(
            x=region_top.values,
            y=region_top.index,
            orientation='h',
            text=region_top.values,
            color=region_top.values,
            color_continuous_scale='Greens'
        )
        fig.update_traces(texttemplate='%{text:,.0f}부', textposition='outside')
        fig.update_layout(
            showlegend=False,
            height=400,
            xaxis_title="주문 부수",
            yaxis_title=""
        )
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    if '학교급명' in order_df.columns:
        school_level_stats = order_df.groupby('학교급명').agg({
            '부수': 'sum',
            '금액': 'sum' if '금액' in order_df.columns else 'count',
            '정보공시학교코드': 'nunique' if '정보공시학교코드' in order_df.columns else 'count',
            '과목명': 'nunique'
        }).reset_index()
        school_level_stats.columns = ['학교급', '주문부수', '주문금액', '학교수', '과목수']
        school_level_stats['학교당평균'] = school_level_stats['주문부수'] / school_level_stats['학교수']
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.pie(
                school_level_stats,
                values='주문부수',
                names='학교급',
                title='학교급별 주문 부수 분포',
                hole=0.4
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.bar(
                school_level_stats,
                x='학교급',
                y='학교당평균',
                title='학교급별 학교당 평균 주문 부수',
                text='학교당평균',
                color='학교당평균',
                color_continuous_scale='Viridis'
            )
            fig.update_traces(texttemplate='%{text:,.0f}부', textposition='outside')
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # Detailed table
        st.subheader("📋 학교급별 상세 지표")
        st.dataframe(
            school_level_stats.style.format({
                '주문부수': '{:,.0f}',
                '주문금액': '{:,.0f}',
                '학교수': '{:,.0f}',
                '과목수': '{:,.0f}',
                '학교당평균': '{:,.1f}'
            }),
            use_container_width=True
        )

with tab3:
    st.subheader("💡 전략적 인사이트")
    
    # 총판별 시장 규모 정보 표시
    if 'distributor_market' in st.session_state and not st.session_state['distributor_market'].empty:
        st.markdown("#### 🏢 총판별 시장 현황 (담당 학교 기준)")
        
        dist_market_df = st.session_state['distributor_market']
        
        # TOP 10 총판 표시
        top_dists = dist_market_df.nlargest(10, '점유율(%)')
        
        col1, col2 = st.columns([3, 2])
        
        with col1:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name='점유율',
                x=top_dists['총판명'],
                y=top_dists['점유율(%)'],
                marker_color='#667eea',
                text=top_dists['점유율(%)'].apply(lambda x: f'{x:.1f}%'),
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>점유율: %{y:.2f}%<br>시장규모: %{customdata:,.0f}명<extra></extra>',
                customdata=top_dists['전체_시장규모']
            ))
            
            fig.update_layout(
                title="총판별 시장 점유율 TOP 10 (담당 학교 기준)",
                xaxis_title="",
                yaxis_title="점유율 (%)",
                height=400,
                showlegend=False,
                xaxis_tickangle=-45
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("**📊 총판별 시장 요약**")
            for idx, row in top_dists.head(5).iterrows():
                st.markdown(f"""
                **{row['총판명']}**
                - 시장규모: {row['전체_시장규모']:,.0f}명
                - 주문부수: {row['주문부수']:,.0f}부
                - 점유율: {row['점유율(%)']:.2f}%
                - 담당학교: {row['담당_전체학교수']}개교
                """)
        
        st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🎯 강점 분야")
        if not market_analysis.empty:
            strong_subjects = market_analysis[market_analysis['점유율(%)'] > 60].sort_values('점유율(%)', ascending=False)
            if len(strong_subjects) > 0:
                st.success(f"✅ **{len(strong_subjects)}개 과목**에서 60% 이상 점유율 달성")
                for idx, row in strong_subjects.head(5).iterrows():
                    st.write(f"• {row['과목명']}: **{row['점유율(%)']:.1f}%**")
            else:
                st.info("60% 이상 점유율 과목이 없습니다.")
        
        st.markdown("#### 📊 총판 효율성")
        if '총판' in order_df.columns:
            dist_efficiency = order_df.groupby('총판').agg({
                '부수': 'sum',
                '정보공시학교코드': 'nunique' if '정보공시학교코드' in order_df.columns else 'count'
            })
            dist_efficiency['효율성'] = dist_efficiency['부수'] / dist_efficiency['정보공시학교코드']
            top_efficient = dist_efficiency.nlargest(3, '효율성')
            st.info(f"📌 가장 효율적인 총판: **{top_efficient.index[0]}** (학교당 {top_efficient.iloc[0]['효율성']:.0f}부)")
    
    with col2:
        st.markdown("#### ⚠️ 개선 필요 분야")
        if not market_analysis.empty:
            weak_subjects = market_analysis[market_analysis['점유율(%)'] < 30].sort_values('주문부수', ascending=False)
            if len(weak_subjects) > 0:
                st.warning(f"⚡ **{len(weak_subjects)}개 과목**이 30% 미만 점유율")
                for idx, row in weak_subjects.head(5).iterrows():
                    st.write(f"• {row['과목명']}: {row['점유율(%)']:.1f}% (개선 여지)")
            else:
                st.success("모든 과목이 30% 이상 점유율을 기록했습니다!")
        
        st.markdown("#### 🎯 성장 기회")
        if '시도교육청' in order_df.columns:
            region_penetration = order_df.groupby('시도교육청')['정보공시학교코드'].nunique() if '정보공시학교코드' in order_df.columns else order_df.groupby('시도교육청')['학교코드'].nunique()
            low_penetration = region_penetration.nsmallest(3)
            st.info(f"📌 진출 확대 지역: {', '.join(low_penetration.index[:3].tolist())}")

st.markdown("---")

# Navigation Guide
st.header("🧭 페이지 안내")
st.markdown("""
<div style='background: linear-gradient(to right, #f8f9fa 0%, #e9ecef 100%); 
            padding: 20px; border-radius: 10px; border-left: 5px solid #667eea;'>
<p style='font-size: 1.1em; margin-bottom: 15px;'><b>왼쪽 사이드바에서 원하는 분석 페이지를 선택하세요:</b></p>

📚 <b>교과/과목별 분석</b><br>
&nbsp;&nbsp;&nbsp;&nbsp;→ 과목별 점유율 및 학교급별 상세 분석, 히트맵 시각화

🗺️ <b>지역별 분석</b><br>
&nbsp;&nbsp;&nbsp;&nbsp;→ 시도/교육청/시군구별 상세 분석, 지역 트렌드

🏢 <b>총판별 분석</b><br>
&nbsp;&nbsp;&nbsp;&nbsp;→ 총판별 판매 현황 및 성과 비교, 효율성 분석

📖 <b>교과서별 분석</b><br>
&nbsp;&nbsp;&nbsp;&nbsp;→ 개별 교과서 상세 분석 및 도서코드별 추적

🔍 <b>비교 분석</b><br>
&nbsp;&nbsp;&nbsp;&nbsp;→ A/B 비교 및 크로스 분석 (지역, 총판, 과목)

🔄 <b>총판 비교분석</b><br>
&nbsp;&nbsp;&nbsp;&nbsp;→ 2~6개 총판 동시 비교, 목표달성률, 시장 점유율

🏅 <b>등급별 분석</b><br>
&nbsp;&nbsp;&nbsp;&nbsp;→ S/A/B/C/D/E/G 등급별 총판 성과 분석
</div>
""", unsafe_allow_html=True)

st.markdown("---")
st.caption("© 2025 CMASS - 22개정 실적 분석 시스템 | 📊 Data-Driven Decision Making")
