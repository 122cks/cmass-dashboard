import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="지역별 분석", page_icon="🗺️", layout="wide")

# Get data
if 'total_df' not in st.session_state or 'order_df' not in st.session_state:
    st.error("데이터를 불러올 수 없습니다. 메인 페이지로 돌아가주세요.")
    st.stop()

total_df = st.session_state['total_df']
order_df = st.session_state['order_df']

st.title("🗺️ 지역별 상세 분석")
st.markdown("---")

# Sidebar Filters
st.sidebar.header("🔍 필터 옵션")

# School Level Filter
if '학교급코드' in total_df.columns:
    school_levels_code = sorted(total_df['학교급코드'].dropna().unique().tolist())
    school_level_names = {2: '초등학교', 3: '중학교', 4: '고등학교'}
    school_options = ['전체'] + [school_level_names.get(code, f'학교급{code}') for code in school_levels_code]
    selected_school = st.sidebar.selectbox("학교급 선택", school_options)
    
    if selected_school != '전체':
        selected_code = [k for k, v in school_level_names.items() if v == selected_school][0]
        filtered_total_df = total_df[total_df['학교급코드'] == selected_code].copy()
    else:
        filtered_total_df = total_df.copy()
else:
    filtered_total_df = total_df.copy()

# Subject Filter
if '과목명' in order_df.columns:
    subjects = ['전체'] + sorted(order_df['과목명'].dropna().unique().tolist())
    selected_subject = st.sidebar.selectbox("과목 선택", subjects)
    
    if selected_subject != '전체':
        filtered_order_df = order_df[order_df['과목명'] == selected_subject].copy()
    else:
        filtered_order_df = order_df.copy()
else:
    filtered_order_df = order_df.copy()

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
tab1, tab2, tab3, tab4 = st.tabs(["🗺️ 시도별 분석", "🏫 교육청별 분석", "📊 학교급별 분석", "📋 상세 테이블"])

with tab1:
    st.subheader("시도교육청별 점유율 분석")
    
    if '시도교육청' in filtered_total_df.columns and '시도교육청' in filtered_order_df.columns:
        # Calculate regional statistics
        region_students = filtered_total_df.groupby('시도교육청')['학생수(계)'].sum().reset_index()
        region_students.columns = ['시도교육청', '전체학생수']
        
        region_orders = filtered_order_df.groupby('시도교육청')['부수'].sum().reset_index()
        region_orders.columns = ['시도교육청', '주문부수']
        
        region_stats = pd.merge(region_students, region_orders, on='시도교육청', how='left').fillna(0)
        region_stats['점유율(%)'] = (region_stats['주문부수'] / region_stats['전체학생수']) * 100
        region_stats['미점유학생'] = region_stats['전체학생수'] - region_stats['주문부수']
        region_stats = region_stats.sort_values('점유율(%)', ascending=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Bar chart
            fig = px.bar(
                region_stats,
                x='시도교육청',
                y='점유율(%)',
                title="시도별 점유율",
                text='점유율(%)',
                color='점유율(%)',
                color_continuous_scale='RdYlGn'
            )
            fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
            fig.update_layout(height=500, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Pie chart
            fig_pie = px.pie(
                region_stats.head(10),
                values='주문부수',
                names='시도교육청',
                title="지역별 주문 비중 TOP 10"
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        
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
                            # Aggregate by subject
                            subject_summary = region_orders.groupby('과목명')['부수'].sum().reset_index()
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
