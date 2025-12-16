import streamlit as st
import pandas as pd
import os
import sys

# Add utils directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))
from market_size import calculate_market_size_by_subject

# Grade sorting function for distributors
def get_grade_order(grade):
    """Convert grade to number for sorting (S=1, A=2, B=3, C=4, D=5, E=6, etc.)"""
    grade_map = {'S': 1, 'A': 2, 'B': 3, 'C': 4, 'D': 5, 'E': 6}
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
    
    # Merge product info to add school level to subject names
    if not product_df.empty and '코드' in product_df.columns and '학교급' in product_df.columns:
        # Create mapping from product code to school level
        product_df['코드'] = product_df['코드'].astype(str)
        order_df['코드'] = order_df['코드'].astype(str)
        
        # Merge to get school level
        order_df = pd.merge(
            order_df, 
            product_df[['코드', '학교급', '교과군']].rename(columns={'교과군': '교과군_제품'}),
            on='코드',
            how='left'
        )
        
        # Add school level to subject name for clarity (중등 정보 vs 고등 정보)
        def add_school_level_to_subject(row):
            if pd.notna(row.get('학교급')) and pd.notna(row.get('교과서명')):
                school_level = row['학교급']
                subject = str(row['교과서명'])
                # Add prefix based on school level
                if school_level == '중학교':
                    return f"[중등] {subject}"
                elif school_level == '고등학교':
                    return f"[고등] {subject}"
            return row.get('교과서명', '')
        
        order_df['교과서명_구분'] = order_df.apply(add_school_level_to_subject, axis=1)
    else:
        order_df['교과서명_구분'] = order_df.get('교과서명', '')
    
    # Map official distributor names (총판명(공식))
    if not distributor_df.empty and '총판명(공식)' in distributor_df.columns:
        # Create mapping from original name to official name
        dist_map = {}
        for _, row in distributor_df.iterrows():
            for col in ['총판명', '총판명1']:
                if col in distributor_df.columns and pd.notna(row.get(col)):
                    dist_map[row[col]] = row['총판명(공식)']
        
        # Apply mapping to order data
        if '총판' in order_df.columns:
            order_df['총판_원본'] = order_df['총판']
            order_df['총판'] = order_df['총판'].map(lambda x: dist_map.get(x, x) if pd.notna(x) else x)
        
        # Add distributor grade for sorting
        grade_map = {}
        for _, row in distributor_df.iterrows():
            if pd.notna(row.get('총판명(공식)')) and pd.notna(row.get('등급')):
                grade_map[row['총판명(공식)']] = row['등급']
        order_df['총판등급'] = order_df['총판'].map(grade_map)
    
    # Calculate accurate market size by subject
    market_analysis = calculate_market_size_by_subject(order_df, total_df, product_df)

    return total_df, order_df, target_df, product_df, distributor_df, market_analysis

# Load data
try:
    total_df, order_df, target_df, product_df, distributor_df, market_analysis = load_data()
    
    # Store in session state for access across pages
    st.session_state['total_df'] = total_df
    st.session_state['order_df'] = order_df
    st.session_state['target_df'] = target_df
    st.session_state['product_df'] = product_df
    st.session_state['distributor_df'] = distributor_df
    st.session_state['market_analysis'] = market_analysis
    st.session_state['sort_by_grade'] = sort_by_grade  # Store sorting function
except FileNotFoundError as e:
    st.error(f"파일을 찾을 수 없습니다: {e}")
    st.stop()
except Exception as e:
    st.error(f"데이터 로드 중 오류 발생: {e}")
    st.stop()

# Main Page - Dashboard
st.title("📊 22개정 자사 실적표 조회 시스템")
st.markdown("---")

# Create metrics row
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_students = total_df['학생수(계)'].sum()
    st.metric("2025년 전체 학생수", f"{total_students:,.0f}명")

with col2:
    total_orders = order_df['부수'].sum()
    st.metric("2026년용 주문 부수", f"{total_orders:,.0f}부")

with col3:
    # Calculate accurate overall share from market_analysis
    if not market_analysis.empty:
        total_market = market_analysis['시장규모(학생수)'].sum()
        accurate_share = (total_orders / total_market * 100) if total_market > 0 else 0
        st.metric("정확 점유율", f"{accurate_share:.2f}%", 
                 help="각 과목의 대상 학년별 시장 규모를 기준으로 계산")
    else:
        overall_share = (total_orders / total_students) * 100
        st.metric("전체 점유율", f"{overall_share:.2f}%")

with col4:
    # Count unique schools by school code
    school_code_cols = ['학교코드', '정보공시학교코드', '정보공시 학교코드']
    total_schools = 0
    for col in school_code_cols:
        if col in order_df.columns:
            total_schools = order_df[col].dropna().nunique()
            break
    st.metric("주문 학교 수", f"{total_schools:,}개교")

st.markdown("---")

# Display market analysis insights
st.header("📊 시장 규모 분석 (2026년도 기준)")
st.caption("💡 2025년 주문한 교과서는 2026년에 사용합니다. 현재 1학년 → 내년 2학년을 기준으로 정확한 시장 규모를 산정했습니다.")
st.info("⚠️ 과목명의 숫자(1, 2)는 학기를 의미합니다. 예: 한국사 1 = 1학기, 한국사 2 = 2학기 (학년 아님)")

if not market_analysis.empty:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Top subjects by accurate market share
        top_accurate = market_analysis.nlargest(10, '점유율(%)')
        st.subheader("📚 과목별 정확 점유율 TOP 10")
        for idx, row in top_accurate.iterrows():
            grade_info = f" ({row['대상학년']})" if row['대상학년'] != '전체' else " (전 학년)"
            st.write(f"{top_accurate.index.tolist().index(idx) + 1}. **{row['과목명']}**{grade_info}: "
                    f"{row['점유율(%)']:.2f}% | 시장: {row['시장규모(학생수)']:,.0f}명 | 주문: {row['주문부수']:,.0f}부")
    
    with col2:
        st.subheader("🎯 시장 분석 요약")
        avg_share = market_analysis['점유율(%)'].mean()
        st.metric("평균 점유율", f"{avg_share:.2f}%")
        
        high_share = len(market_analysis[market_analysis['점유율(%)'] > 50])
        st.metric("50% 이상 과목", f"{high_share}개")
        
        total_market_size = market_analysis['시장규모(학생수)'].sum()
        st.metric("전체 대상 시장", f"{total_market_size:,.0f}명")
else:
    st.info("시장 분석 데이터를 계산중입니다...")

st.markdown("---")

# Quick Overview Section
st.header("📈 주요 지표 개요")

col1, col2 = st.columns(2)

with col1:
    st.subheader("교과/과목별 TOP 5")
    subject_top = order_df.groupby('과목명')['부수'].sum().sort_values(ascending=False).head(5)
    for idx, (subject, count) in enumerate(subject_top.items(), 1):
        st.write(f"{idx}. **{subject}**: {count:,}부")

with col2:
    st.subheader("지역별 TOP 5")
    region_top = order_df.groupby('시도교육청')['부수'].sum().sort_values(ascending=False).head(5)
    for idx, (region, count) in enumerate(region_top.items(), 1):
        st.write(f"{idx}. **{region}**: {count:,}부")

st.markdown("---")

# Navigation Guide
st.header("🧭 페이지 안내")
st.info("""
왼쪽 사이드바에서 원하는 분석 페이지를 선택하세요:
- **📚 교과/과목별 분석**: 과목별 점유율 및 상세 분석
- **🗺️ 지역별 분석**: 시도/교육청/학교급별 상세 분석
- **🏢 총판별 분석**: 총판별 판매 현황 및 비교
- **📖 교과서별 분석**: 개별 교과서 상세 분석 및 도서코드별 추적
- **🔍 비교 분석**: 다차원 비교 및 크로스 분석
""")

st.markdown("---")
st.caption("© 2025 CMASS - 22개정 실적 분석 시스템")
