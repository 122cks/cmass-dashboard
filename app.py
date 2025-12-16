import streamlit as st
import pandas as pd
import os

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

    return total_df, order_df, target_df, product_df, distributor_df

# Load data
try:
    total_df, order_df, target_df, product_df, distributor_df = load_data()
    
    # Store in session state for access across pages
    st.session_state['total_df'] = total_df
    st.session_state['order_df'] = order_df
    st.session_state['target_df'] = target_df
    st.session_state['product_df'] = product_df
    st.session_state['distributor_df'] = distributor_df
except FileNotFoundError as e:
    st.error(f"파일을 찾을 수 없습니다: {e}")
    st.stop()

# Main Page - Dashboard
st.title("📊 22개정 자사 실적표 조회 시스템")
st.markdown("---")

# Create metrics row
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_students = total_df['학생수(계)'].sum()
    st.metric("전체 학생수", f"{total_students:,.0f}명")

with col2:
    total_orders = order_df['부수'].sum()
    st.metric("총 주문 부수", f"{total_orders:,.0f}부")

with col3:
    overall_share = (total_orders / total_students) * 100
    st.metric("전체 점유율", f"{overall_share:.2f}%")

with col4:
    total_schools = order_df['학교코드'].nunique() if '학교코드' in order_df.columns else order_df['정보공시학교코드'].nunique()
    st.metric("주문 학교 수", f"{total_schools:,}개교")

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
