import streamlit as st
from utils.style import apply_custom_style
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.year_filter import add_year_filter_sidebar, filter_by_years, create_year_comparison_metrics
from utils.market_share_calculator import calculate_both_shares, compare_year_shares

st.set_page_config(page_title="교과서별 분석", page_icon="📖", layout="wide")
apply_custom_style()

# Get data
if 'order_df' not in st.session_state:
    st.error("데이터를 불러올 수 없습니다. 메인 페이지로 돌아가주세요.")
    st.stop()

order_df_orig = st.session_state['order_df'].copy()
selected_years, comparison_mode = add_year_filter_sidebar(order_df_orig, default_year='2026')
if selected_years:
    order_df = filter_by_years(order_df_orig, selected_years)
else:
    order_df = order_df_orig

st.title("📖 교과서별 상세 분석")
st.markdown("---")

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
    
    return '미분류'

# Sidebar Filters
st.sidebar.header("🔍 필터 옵션")

# Book Type Filter
if '교지명' in order_df.columns:
    book_types = ['전체'] + sorted(order_df['교지명'].dropna().unique().tolist())
    selected_book_type = st.sidebar.selectbox("도서 유형", book_types)
    
    if selected_book_type != '전체':
        filtered_df = order_df[order_df['교지명'] == selected_book_type].copy()
    else:
        filtered_df = order_df.copy()
else:
    filtered_df = order_df.copy()

# Subject Filter
subject_col_filter = '교과서명_구분' if '교과서명_구분' in filtered_df.columns else '과목명'
if subject_col_filter in filtered_df.columns:
    subjects = ['전체'] + sorted(filtered_df[subject_col_filter].dropna().unique().tolist())
    selected_subject = st.sidebar.selectbox("과목 선택", subjects)
    
    if selected_subject != '전체':
        filtered_df = filtered_df[filtered_df[subject_col_filter] == selected_subject]

# Region Filter
if '시도교육청' in filtered_df.columns:
    regions = ['전체'] + sorted(filtered_df['시도교육청'].dropna().unique().tolist())
    selected_region = st.sidebar.selectbox("지역 선택", regions)
    
    if selected_region != '전체':
        filtered_df = filtered_df[filtered_df['시도교육청'] == selected_region]

st.sidebar.markdown("---")
st.sidebar.info(f"📊 필터링된 데이터: {len(filtered_df):,}건")

# Main Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_books = filtered_df['도서코드'].nunique() if '도서코드' in filtered_df.columns else len(filtered_df)
    st.metric("교과서 종류", f"{total_books:,}개")

with col2:
    total_orders = filtered_df['부수'].sum()
    st.metric("총 주문 부수", f"{total_orders:,.0f}부")

with col3:
    total_amount = filtered_df['금액'].sum() if '금액' in filtered_df.columns else 0
    st.metric("총 주문 금액", f"{total_amount:,.0f}원")

with col4:
    avg_price = filtered_df['정가'].mean() if '정가' in filtered_df.columns else 0
    st.metric("평균 정가", f"{avg_price:,.0f}원")

st.markdown("---")

# Tab Layout
tab1, tab2, tab3, tab4 = st.tabs(["📚 교과서 목록", "💰 가격 분석", "🎯 도서코드별 분석", "📋 상세 테이블"])

with tab1:
    st.subheader("교과서별 주문 현황")
    
    # Aggregate by book
    subject_col = '교과서명_구분' if '교과서명_구분' in filtered_df.columns else '과목명'
    school_code_col = '정보공시학교코드' if '정보공시학교코드' in filtered_df.columns else '학교코드'
    
    if '도서코드' in filtered_df.columns and subject_col in filtered_df.columns:
        book_stats = filtered_df.groupby(['도서코드', subject_col, '교지명']).agg({
            '부수': 'sum',
            '금액': 'sum' if '금액' in filtered_df.columns else 'count',
            '정가': 'first' if '정가' in filtered_df.columns else 'count',
            school_code_col: 'nunique'
        }).reset_index()
        
        book_stats.columns = ['도서코드', '과목명', '교지명', '주문부수', '주문금액', '정가', '주문학교수']
        book_stats['시장점유율(%)'] = (book_stats['주문부수'] / book_stats['주문부수'].sum()) * 100
        
        # 학교급 구분 추가 (학교급 또는 학교급명 컬럼 사용)
        school_level_col = '학교급' if '학교급' in filtered_df.columns else ('학교급명' if '학교급명' in filtered_df.columns else None)
        
        if school_level_col:
            book_school_level = filtered_df.groupby('과목명')[school_level_col].first().to_dict()
            book_stats['학교급'] = book_stats['과목명'].map(book_school_level).fillna('미분류')
        else:
            book_stats['학교급'] = book_stats['과목명'].apply(get_school_level_from_subject)
        
        book_stats = book_stats.sort_values('주문부수', ascending=False)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Top textbooks with school level color coding
            fig = px.bar(
                book_stats.head(20),
                x='과목명',
                y='주문부수',
                color='학교급',
                title="TOP 20 교과서 주문 현황 (🔵중학교 / 🔴고등학교)",
                text='주문부수',
                color_discrete_map={
                    '중학교': '#4A90E2',  # 파란색
                    '고등학교': '#E94B3C',  # 빨간색
                    '미분류': '#9E9E9E'  # 회색
                },
                barmode='group'
            )
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig.update_layout(height=500, xaxis_tickangle=-45, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Book type distribution
            type_dist = book_stats.groupby('교지명')['주문부수'].sum().reset_index()
            fig_pie = px.pie(
                type_dist,
                values='주문부수',
                names='교지명',
                title="도서 유형별 비중"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # Detailed book cards
        st.markdown("---")
        st.subheader("🏆 인기 교과서 TOP 10")
        
        cols = st.columns(2)
        for idx, row in book_stats.head(10).iterrows():
            col_idx = book_stats.head(10).index.tolist().index(idx)
            with cols[col_idx % 2]:
                rank = col_idx + 1
                st.markdown(f"""
                <div style="border: 2px solid #2196F3; border-radius: 10px; padding: 15px; margin: 10px 0;">
                    <h4>#{rank} {row['과목명']}</h4>
                    <p><b>도서코드:</b> {row['도서코드']}</p>
                    <p><b>유형:</b> {row['교지명']}</p>
                    <p><b>주문:</b> {row['주문부수']:,.0f}부 ({row['시장점유율(%)']:.2f}%)</p>
                    <p><b>정가:</b> {row['정가']:,.0f}원</p>
                    <p><b>주문학교:</b> {row['주문학교수']}개교</p>
                </div>
                """, unsafe_allow_html=True)

with tab2:
    st.subheader("💰 가격대별 분석")
    
    if '정가' in filtered_df.columns:
        # Price distribution
        col1, col2 = st.columns(2)
        
        with col1:
            # Histogram
            fig_hist = px.histogram(
                filtered_df,
                x='정가',
                nbins=30,
                title="교과서 가격 분포",
                labels={'정가': '가격 (원)', 'count': '빈도'}
            )
            fig_hist.update_layout(height=400)
            st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            # Box plot by subject
            if '과목명' in filtered_df.columns:
                top_subjects = filtered_df['과목명'].value_counts().head(10).index.tolist()
                price_by_subject = filtered_df[filtered_df['과목명'].isin(top_subjects)]
                
                fig_box = px.box(
                    price_by_subject,
                    y='과목명',
                    x='정가',
                    title="과목별 가격 분포 (TOP 10)",
                    orientation='h'
                )
                fig_box.update_layout(height=400)
                st.plotly_chart(fig_box, use_container_width=True)
        
        # Price range analysis
        st.markdown("---")
        st.subheader("📊 가격대별 주문 분석")
        
        # Create price ranges
        filtered_df['가격대'] = pd.cut(
            filtered_df['정가'],
            bins=[0, 10000, 15000, 20000, 25000, float('inf')],
            labels=['1만원 미만', '1~1.5만원', '1.5~2만원', '2~2.5만원', '2.5만원 이상']
        )
        
        price_range_stats = filtered_df.groupby('가격대').agg({
            '부수': 'sum',
            '금액': 'sum' if '금액' in filtered_df.columns else 'count',
            '도서코드': 'nunique' if '도서코드' in filtered_df.columns else 'count'
        }).reset_index()
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.bar(
                price_range_stats,
                x='가격대',
                y='부수',
                title="가격대별 주문량",
                text='부수',
                color='부수',
                color_continuous_scale='Greens'
            )
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig_funnel = go.Figure(go.Funnel(
                y=price_range_stats['가격대'],
                x=price_range_stats['부수'],
                textinfo="value+percent initial"
            ))
            fig_funnel.update_layout(title="가격대별 주문 비율")
            st.plotly_chart(fig_funnel, use_container_width=True)

with tab3:
    st.subheader("🔍 도서코드별 상세 추적")
    
    if '도서코드' in filtered_df.columns:
        # Search by book code
        search_code = st.text_input("🔍 도서코드 검색", "")
        
        if search_code:
            code_data = filtered_df[filtered_df['도서코드'].str.contains(search_code, case=False, na=False, regex=False)]
            
            if len(code_data) > 0:
                st.success(f"검색 결과: {len(code_data)}건")
                
                # Display detailed info
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    total_qty = code_data['부수'].sum()
                    st.metric("총 주문량", f"{total_qty:,.0f}부")
                
                with col2:
                    total_amt = code_data['금액'].sum() if '금액' in code_data.columns else 0
                    st.metric("총 금액", f"{total_amt:,.0f}원")
                
                with col3:
                    school_code_col = '정보공시학교코드' if '정보공시학교코드' in code_data.columns else '학교코드'
                    school_count = code_data[school_code_col].nunique()
                    st.metric("주문 학교", f"{school_count}개교")
                
                # Regional distribution
                if '시도교육청' in code_data.columns:
                    st.markdown("---")
                    st.subheader("📍 지역별 주문 분포")
                    
                    regional_dist = code_data.groupby('시도교육청')['부수'].sum().reset_index()
                    regional_dist = regional_dist.sort_values('부수', ascending=False)
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        fig = px.bar(
                            regional_dist,
                            x='시도교육청',
                            y='부수',
                            title=f"도서코드 '{search_code}' 지역별 분포",
                            text='부수'
                        )
                        fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                        fig.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        fig_pie = px.pie(
                            regional_dist.head(10),
                            values='부수',
                            names='시도교육청',
                            title="지역 비중"
                        )
                        st.plotly_chart(fig_pie, use_container_width=True)
                
                # Detailed table
                st.markdown("---")
                st.dataframe(code_data, use_container_width=True, height=300)
            else:
                st.warning("검색 결과가 없습니다.")
        else:
            # Show book code frequency
            code_freq = filtered_df['도서코드'].value_counts().reset_index()
            code_freq.columns = ['도서코드', '빈도']
            
            st.markdown("#### 📊 도서코드별 주문 빈도 TOP 20")
            
            fig = px.bar(
                code_freq.head(20),
                x='도서코드',
                y='빈도',
                title="도서코드별 주문 빈도",
                text='빈도'
            )
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("📋 전체 교과서 데이터")
    
    # Search functionality
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_term = st.text_input("🔍 검색 (과목명, 도서코드)", "")
    
    with col2:
        sort_by = st.selectbox("정렬 기준", ['주문부수', '주문금액', '정가', '주문학교수'])
    
    if 'book_stats' in locals():
        display_data = book_stats.copy()
        
        if search_term:
            display_data = display_data[
                display_data['과목명'].str.contains(search_term, case=False, na=False, regex=False) |
                display_data['도서코드'].astype(str).str.contains(search_term, case=False, na=False, regex=False)
            ]
        
        display_data = display_data.sort_values(sort_by, ascending=False)
        
        st.dataframe(
            display_data.style.format({
                '주문부수': '{:,.0f}',
                '주문금액': '{:,.0f}',
                '정가': '{:,.0f}',
                '주문학교수': '{:,.0f}',
                '시장점유율(%)': '{:.2f}%'
            }),
            use_container_width=True,
            height=400
        )
        
        # Download
        csv = display_data.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 CSV 다운로드",
            data=csv,
            file_name="교과서별_분석_데이터.csv",
            mime="text/csv"
        )

st.markdown("---")
st.caption("📖 교과서별 분석 페이지")
