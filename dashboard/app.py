import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- Simple admin PIN auth (direct input) ---
ADMIN_PIN = os.environ.get('ADMIN_PIN', '2274')
LOCKOUT_SECONDS = int(os.environ.get('PIN_LOCKOUT_SECONDS', 300))
MAX_ATTEMPTS = int(os.environ.get('PIN_MAX_ATTEMPTS', 3))

if 'auth_ok' not in st.session_state:
    st.session_state['auth_ok'] = False
if 'auth_attempts' not in st.session_state:
    st.session_state['auth_attempts'] = 0
if 'auth_lock_until' not in st.session_state:
    st.session_state['auth_lock_until'] = None

import time

def _is_locked():
    lock_until = st.session_state.get('auth_lock_until')
    if MAX_ATTEMPTS <= 0 or LOCKOUT_SECONDS <= 0:
        return False
    if lock_until and time.time() < lock_until:
        return True
    return False

if not st.session_state.get('auth_ok', False):
    if _is_locked():
        remaining = int(st.session_state['auth_lock_until'] - time.time())
        mins = remaining // 60
        secs = remaining % 60
        st.error(f"비밀번호 시도 횟수 초과: 잠금 상태입니다. 남은 시간 {mins}분 {secs}초")
        st.stop()

    st.markdown("""
    <div style='max-width:520px;margin:24px auto;padding:20px;background:#0b2b3a;border-radius:10px'>
    <h3 style='color:#fff;text-align:center;margin:0 0 12px 0'>관리자 PIN 입력</h3>
    </div>
    """, unsafe_allow_html=True)

    with st.form('pin_form'):
        entered = st.text_input('PIN', value='', type='password', placeholder='PIN을 입력하세요')
        submitted = st.form_submit_button('로그인')
        if submitted:
            if entered.strip() == ADMIN_PIN:
                st.session_state['auth_ok'] = True
                st.session_state['auth_attempts'] = 0
                st.session_state['auth_lock_until'] = None
                st.experimental_rerun()
            else:
                st.session_state['auth_attempts'] += 1
                if st.session_state['auth_attempts'] >= MAX_ATTEMPTS:
                    st.session_state['auth_lock_until'] = time.time() + LOCKOUT_SECONDS
                st.error('PIN이 올바르지 않습니다.')
                st.stop()


# Set page config
st.set_page_config(page_title="CMASS 실적표 조회", layout="wide")

# If this dashboard entrypoint is being used as the deployed main file,
# delegate execution to the root `app.py` so Streamlit's multi-page loader
# (pages/ folder) and the canonical app logic are used. This keeps behavior
# identical whether the Cloud entrypoint is `app.py` or `dashboard/app.py`.
try:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_app_path = os.path.join(BASE_DIR, 'app.py')
    if os.path.exists(root_app_path):
        with open(root_app_path, 'r', encoding='utf-8') as _f:
            code = _f.read()
        # Ensure root app resolves relative paths correctly
        g = globals()
        g['__file__'] = root_app_path
        exec(compile(code, root_app_path, 'exec'), g)
        st.stop()
except Exception:
    # If delegation fails, continue with this simplified dashboard as fallback
    pass

# File Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOTAL_FILE = os.path.join(BASE_DIR, "2025년도_학년별·학급별 학생수(초중고)_전체.csv")
ORDER_FILE = os.path.join(BASE_DIR, "씨마스_22개정 주문현황_학교코드총판코드.csv")

@st.cache_data
def load_data():
    # Try reading with different encodings
    try:
        total_df = pd.read_csv(TOTAL_FILE, encoding='cp949')
    except UnicodeDecodeError:
        total_df = pd.read_csv(TOTAL_FILE, encoding='utf-8')
    
    try:
        order_df = pd.read_csv(ORDER_FILE, encoding='cp949')
    except UnicodeDecodeError:
        order_df = pd.read_csv(ORDER_FILE, encoding='utf-8')

    # Clean column names (strip whitespace)
    total_df.columns = total_df.columns.str.strip()
    order_df.columns = order_df.columns.str.strip()

    # Ensure School Codes are strings for merging
    if '정보공시 학교코드' in total_df.columns:
        total_df['정보공시 학교코드'] = total_df['정보공시 학교코드'].astype(str)
    if '정보공시학교코드' in order_df.columns:
        order_df['정보공시학교코드'] = order_df['정보공시학교코드'].astype(str)

    return total_df, order_df

try:
    total_df, order_df = load_data()
except FileNotFoundError as e:
    st.error(f"파일을 찾을 수 없습니다: {e}")
    st.stop()

st.title("📊 22개정 자사 실적표 조회화면")

# --- 주문 데이터 필터 (2026년도, 목표과목1/2만 사용) ---
if '학년도' in order_df.columns and '목표과목' in order_df.columns:
    order_filtered = order_df[(order_df['학년도'] == 2026) & (order_df['목표과목'].isin(['목표과목1', '목표과목2']))].copy()
else:
    order_filtered = order_df

# Sidebar Filters
st.sidebar.header("필터")
# Filter by School Level from Total Data if available
if '학교급코드' in total_df.columns:
    school_levels = sorted(total_df['학교급코드'].unique())
    selected_level = st.sidebar.multiselect("학교급코드 선택 (전체 데이터 기준)", school_levels, default=school_levels)
    if selected_level:
        filtered_total_df = total_df[total_df['학교급코드'].isin(selected_level)]
    else:
        filtered_total_df = total_df
else:
    filtered_total_df = total_df

# Calculate Total Market Size (Students)
total_students = filtered_total_df['학생수(계)'].sum()
st.sidebar.metric("전체 학생수 (Target Market)", f"{total_students:,.0f}명")

# Tabs
tab1, tab2, tab3 = st.tabs(["📚 교과/과목별 점유율", "🗺️ 지역별 점유율", "🏢 총판 점유율"])

# --- Tab 1: Subject Share ---
with tab1:
    st.header("교과/과목별 점유율")
    
    # Group orders by Subject (2026년도 + 목표과목1/2 필터 적용)
    subject_group = order_filtered.groupby('과목명')['부수'].sum().reset_index()
    subject_group = subject_group.sort_values(by='부수', ascending=False)
    
    # Calculate Share (Orders / Total Students in filtered market)
    # Note: This assumes 'Total Students' is the denominator for ALL subjects, which is a rough approximation.
    subject_group['점유율(%)'] = (subject_group['부수'] / total_students) * 100
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig_subj = px.bar(subject_group, x='과목명', y='부수', title="과목별 주문 부수", text_auto=True)
        st.plotly_chart(fig_subj, use_container_width=True)
        
    with col2:
        st.dataframe(subject_group.style.format({'부수': '{:,.0f}', '점유율(%)': '{:.2f}%'}))

# --- Tab 2: Regional Share ---
with tab2:
    st.header("지역별 점유율")
    
    # 1. Aggregate Total Students by Region (from Total File)
    # '지역' column exists in both, but we need to be careful about matching.
    # Let's use '시도교육청' as it's likely more standardized, or '지역' if it's consistent.
    # Let's check columns. Total: '시도교육청', '지역'. Order: '시도교육청', '지역'.
    
    region_col = '시도교육청' # Using Education Office as Region key
    
    market_by_region = filtered_total_df.groupby(region_col)['학생수(계)'].sum().reset_index()
    market_by_region.columns = [region_col, '전체학생수']
    
    orders_by_region = order_filtered.groupby(region_col)['부수'].sum().reset_index()
    orders_by_region.columns = [region_col, '주문부수']
    
    # Merge
    region_stats = pd.merge(market_by_region, orders_by_region, on=region_col, how='left').fillna(0)
    region_stats['점유율(%)'] = (region_stats['주문부수'] / region_stats['전체학생수']) * 100
    region_stats = region_stats.sort_values(by='점유율(%)', ascending=False)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig_region = px.bar(region_stats, x=region_col, y='점유율(%)', 
                            title="지역별 점유율 (%)", 
                            hover_data=['주문부수', '전체학생수'],
                            text_auto=True)
        st.plotly_chart(fig_region, use_container_width=True)
        
    with col2:
        st.dataframe(region_stats.style.format({'전체학생수': '{:,.0f}', '주문부수': '{:,.0f}', '점유율(%)': '{:.2f}%'}))

# --- Tab 3: Distributor Share ---
with tab3:
    st.header("총판 점유율")
    
    # Group by Distributor (2026년도 + 목표과목1/2 필터 적용)
    dist_group = order_filtered.groupby('총판')['부수'].sum().reset_index()
    dist_group = dist_group.sort_values(by='부수', ascending=False)
    
    # Calculate Share of CMASS Sales
    total_orders = dist_group['부수'].sum()
    dist_group['판매비중(%)'] = (dist_group['부수'] / total_orders) * 100
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig_dist = px.pie(dist_group, values='부수', names='총판', title="총판별 판매 비중")
        st.plotly_chart(fig_dist, use_container_width=True)
        
    with col2:
        st.dataframe(dist_group.style.format({'부수': '{:,.0f}', '판매비중(%)': '{:.2f}%'}))

