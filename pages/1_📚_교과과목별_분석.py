import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="교과/과목별 분석", page_icon="📚", layout="wide")

# Get data from session state
if 'total_df' not in st.session_state or 'order_df' not in st.session_state:
    st.error("데이터를 불러올 수 없습니다. 메인 페이지로 돌아가주세요.")
    st.stop()

total_df = st.session_state['total_df']
order_df = st.session_state['order_df']

st.title("📚 교과/과목별 상세 분석")
st.markdown("---")

# Sidebar Filters
st.sidebar.header("🔍 필터 옵션")

# School Level Filter
if '학교급명' in order_df.columns:
    school_levels = ['전체'] + sorted(order_df['학교급명'].dropna().unique().tolist())
    selected_school_level = st.sidebar.selectbox("학교급 선택", school_levels)
    
    if selected_school_level != '전체':
        filtered_order_df = order_df[order_df['학교급명'] == selected_school_level].copy()
    else:
        filtered_order_df = order_df.copy()
else:
    filtered_order_df = order_df.copy()

# Subject Group Filter
if '교과군' in filtered_order_df.columns:
    subject_groups = ['전체'] + sorted(filtered_order_df['교과군'].dropna().unique().tolist())
    selected_subject_group = st.sidebar.selectbox("교과군 선택", subject_groups)
    
    if selected_subject_group != '전체':
        filtered_order_df = filtered_order_df[filtered_order_df['교과군'] == selected_subject_group]

# Region Filter
if '시도교육청' in filtered_order_df.columns:
    regions = ['전체'] + sorted(filtered_order_df['시도교육청'].dropna().unique().tolist())
    selected_region = st.sidebar.selectbox("지역 선택", regions)
    
    if selected_region != '전체':
        filtered_order_df = filtered_order_df[filtered_order_df['시도교육청'] == selected_region]

st.sidebar.markdown("---")
st.sidebar.info(f"📊 필터링된 데이터: {len(filtered_order_df):,}건")

# Main Analysis
col1, col2, col3 = st.columns(3)

with col1:
    total_orders = filtered_order_df['부수'].sum()
    st.metric("총 주문 부수", f"{total_orders:,.0f}부")

with col2:
    total_amount = filtered_order_df['금액'].sum() if '금액' in filtered_order_df.columns else 0
    st.metric("총 주문 금액", f"{total_amount:,.0f}원")

with col3:
    unique_subjects = filtered_order_df['과목명'].nunique()
    st.metric("과목 종류", f"{unique_subjects}개")

st.markdown("---")

# Tab Layout
tab1, tab2, tab3, tab4 = st.tabs(["📊 과목별 현황", "📈 교과군 분석", "🎯 상세 분석", "📋 데이터 테이블"])

with tab1:
    st.subheader("과목별 주문 현황")
    
    # Group by subject
    subject_stats = filtered_order_df.groupby('과목명').agg({
        '부수': 'sum',
        '금액': 'sum' if '금액' in filtered_order_df.columns else 'count',
        '학교코드': 'nunique' if '학교코드' in filtered_order_df.columns else 'count'
    }).reset_index()
    
    subject_stats.columns = ['과목명', '주문부수', '주문금액', '학교수']
    subject_stats = subject_stats.sort_values('주문부수', ascending=False)
    
    # Calculate market share
    total_students_filtered = total_df['학생수(계)'].sum()
    subject_stats['점유율(%)'] = (subject_stats['주문부수'] / total_students_filtered) * 100
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Bar chart
        fig = px.bar(
            subject_stats.head(20),
            x='과목명',
            y='주문부수',
            title="과목별 주문 부수 TOP 20",
            text='주문부수',
            color='주문부수',
            color_continuous_scale='Blues'
        )
        fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
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
                subject_breakdown = group_data.groupby('과목명')['부수'].sum().sort_values(ascending=False)
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    for subject, count in subject_breakdown.items():
                        st.write(f"• **{subject}**: {count:,}부")
                
                with col2:
                    fig = px.bar(
                        x=subject_breakdown.values,
                        y=subject_breakdown.index,
                        orientation='h',
                        title=f"{group} - 과목별 분포"
                    )
                    fig.update_layout(height=max(300, len(subject_breakdown) * 30))
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("교과군 정보가 없습니다.")

with tab3:
    st.subheader("🎯 심화 분석")
    
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
                st.progress(min(row['점유율(%)'] / 100, 1.0))
    
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
            color='점유율(%)',
            hover_name='과목명',
            title="과목별 효율성 분석 (학교수 vs 학교당 평균)",
            labels={'학교수': '주문 학교 수', '학교당평균': '학교당 평균 주문량'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Heatmap if region and subject data available
    st.markdown("---")
    st.markdown("#### 🗺️ 지역 × 과목 히트맵")
    
    if '시도교육청' in filtered_order_df.columns:
        # Create pivot table for heatmap
        pivot_data = filtered_order_df.pivot_table(
            index='시도교육청',
            columns='과목명',
            values='부수',
            aggfunc='sum',
            fill_value=0
        )
        
        # Select top subjects and regions
        top_subjects_list = subject_stats.head(10)['과목명'].tolist()
        pivot_data_filtered = pivot_data[top_subjects_list]
        
        fig_heatmap = px.imshow(
            pivot_data_filtered,
            title="지역별 × 과목별 주문 분포 (TOP 10 과목)",
            labels=dict(x="과목", y="지역", color="주문 부수"),
            aspect="auto",
            color_continuous_scale='YlOrRd'
        )
        fig_heatmap.update_layout(height=600)
        st.plotly_chart(fig_heatmap, use_container_width=True)

with tab4:
    st.subheader("📋 상세 데이터 테이블")
    
    # Search functionality
    search_term = st.text_input("🔍 과목명 검색", "")
    
    if search_term:
        display_stats = subject_stats[subject_stats['과목명'].str.contains(search_term, case=False, na=False)]
    else:
        display_stats = subject_stats
    
    # Display dataframe
    st.dataframe(
        display_stats.style.format({
            '주문부수': '{:,.0f}',
            '주문금액': '{:,.0f}',
            '학교수': '{:,.0f}',
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
