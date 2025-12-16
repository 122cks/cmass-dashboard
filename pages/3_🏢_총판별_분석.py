import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'utils'))
from common_filters import apply_common_filters, show_filter_summary

st.set_page_config(page_title="총판별 분석", page_icon="🏢", layout="wide")

# Get data
if 'total_df' not in st.session_state or 'order_df' not in st.session_state:
    st.error("데이터를 불러올 수 없습니다. 메인 페이지로 돌아가주세요.")
    st.stop()

total_df = st.session_state['total_df']
order_df = st.session_state['order_df'].copy()

st.title("🏢 총판별 상세 분석")
st.markdown("---")

# Apply common filters
filtered_order_df = apply_common_filters(order_df)
show_filter_summary(filtered_order_df, st.session_state['order_df'])

st.sidebar.markdown("---")
st.sidebar.info(f"📊 필터링된 데이터: {len(filtered_order_df):,}건")

# Main Metrics
if '총판' in filtered_order_df.columns:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_orders = filtered_order_df['부수'].sum()
        st.metric("총 주문 부수", f"{total_orders:,.0f}부")
    
    with col2:
        total_amount = filtered_order_df['금액'].sum() if '금액' in filtered_order_df.columns else 0
        st.metric("총 주문 금액", f"{total_amount:,.0f}원")
    
    with col3:
        num_distributors = filtered_order_df['총판'].nunique()
        st.metric("총판 수", f"{num_distributors}개")
    
    with col4:
        avg_per_dist = total_orders / num_distributors if num_distributors > 0 else 0
        st.metric("총판당 평균", f"{avg_per_dist:,.0f}부")
    
    st.markdown("---")
    
    # Tab Layout
    tab1, tab2, tab3, tab4 = st.tabs(["📊 총판별 현황", "📈 실적 비교", "🎯 성과 분석", "📋 상세 테이블"])
    
    with tab1:
        st.subheader("총판별 판매 현황")
        
        # Distributor statistics
        dist_stats = filtered_order_df.groupby('총판').agg({
            '부수': 'sum',
            '금액': 'sum' if '금액' in filtered_order_df.columns else 'count',
            '학교코드': 'nunique' if '학교코드' in filtered_order_df.columns else 'count',
            '과목명': 'nunique' if '과목명' in filtered_order_df.columns else 'count'
        }).reset_index()
        
        dist_stats.columns = ['총판', '주문부수', '주문금액', '거래학교수', '취급과목수']
        dist_stats['판매비중(%)'] = (dist_stats['주문부수'] / dist_stats['주문부수'].sum()) * 100
        dist_stats['학교당평균'] = dist_stats['주문부수'] / dist_stats['거래학교수']
        dist_stats = dist_stats.sort_values('주문부수', ascending=False)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Bar chart
            fig = px.bar(
                dist_stats.head(20),
                x='총판',
                y='주문부수',
                title="총판별 주문 부수 TOP 20",
                text='주문부수',
                color='주문부수',
                color_continuous_scale='Greens'
            )
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig.update_layout(height=500, xaxis_tickangle=-45, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Pie chart
            fig_pie = px.pie(
                dist_stats.head(10),
                values='주문부수',
                names='총판',
                title="총판별 판매 비중 TOP 10"
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # Market share visualization
        st.markdown("---")
        st.subheader("📊 시장 점유율 분포")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Donut chart
            fig_donut = go.Figure(data=[go.Pie(
                labels=dist_stats['총판'],
                values=dist_stats['판매비중(%)'],
                hole=.4
            )])
            fig_donut.update_layout(title="총판별 시장 점유율")
            st.plotly_chart(fig_donut, use_container_width=True)
        
        with col2:
            # Waterfall chart for top distributors
            dist_waterfall = dist_stats.head(10).copy()
            fig_waterfall = go.Figure(go.Waterfall(
                name="주문량",
                orientation="v",
                x=dist_waterfall['총판'],
                y=dist_waterfall['주문부수'],
                text=dist_waterfall['주문부수'],
                textposition="outside",
                connector={"line": {"color": "rgb(63, 63, 63)"}},
            ))
            fig_waterfall.update_layout(title="TOP 10 총판 주문량 누적")
            st.plotly_chart(fig_waterfall, use_container_width=True)
    
    with tab2:
        st.subheader("📈 총판 실적 비교")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Scatter plot - Schools vs Orders
            fig_scatter = px.scatter(
                dist_stats,
                x='거래학교수',
                y='주문부수',
                size='주문금액',
                color='판매비중(%)',
                hover_name='총판',
                title="거래 학교 수 vs 주문량",
                labels={'거래학교수': '거래 학교 수', '주문부수': '주문 부수'},
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
        
        with col2:
            # Average per school
            fig_avg = px.bar(
                dist_stats.head(15),
                x='총판',
                y='학교당평균',
                title="총판별 학교당 평균 주문량 TOP 15",
                text='학교당평균',
                color='학교당평균',
                color_continuous_scale='Blues'
            )
            fig_avg.update_traces(texttemplate='%{text:.1f}', textposition='outside')
            fig_avg.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_avg, use_container_width=True)
        
        # Multi-metric comparison
        st.markdown("---")
        st.subheader("🔄 다차원 비교")
        
        # Radar chart for top 5 distributors
        top5_dists = dist_stats.head(5)
        
        # Normalize metrics for radar chart
        metrics_to_compare = ['주문부수', '주문금액', '거래학교수', '취급과목수', '학교당평균']
        normalized_data = top5_dists[metrics_to_compare].copy()
        for col in metrics_to_compare:
            max_val = normalized_data[col].max()
            normalized_data[col] = (normalized_data[col] / max_val) * 100 if max_val > 0 else 0
        
        fig_radar = go.Figure()
        
        for idx, row in top5_dists.iterrows():
            dist_name = row['총판']
            values = normalized_data.loc[idx].tolist()
            values.append(values[0])  # Close the radar
            
            fig_radar.add_trace(go.Scatterpolar(
                r=values,
                theta=metrics_to_compare + [metrics_to_compare[0]],
                name=dist_name,
                fill='toself'
            ))
        
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            title="TOP 5 총판 다차원 비교 (정규화)"
        )
        st.plotly_chart(fig_radar, use_container_width=True)
    
    with tab3:
        st.subheader("🎯 총판별 성과 심층 분석")
        
        # Performance ranking
        st.markdown("#### 🏆 종합 성과 순위")
        
        # Calculate composite score
        dist_stats['종합점수'] = (
            (dist_stats['주문부수'] / dist_stats['주문부수'].max() * 40) +
            (dist_stats['판매비중(%)'] / dist_stats['판매비중(%)'].max() * 30) +
            (dist_stats['거래학교수'] / dist_stats['거래학교수'].max() * 20) +
            (dist_stats['취급과목수'] / dist_stats['취급과목수'].max() * 10)
        )
        dist_stats = dist_stats.sort_values('종합점수', ascending=False)
        
        # Display top performers
        # Display top performers with school level breakdown
        st.markdown("👉 카드를 클릭하면 해당 총판의 세부 주문 내역과 지역별 학교급별 현황을 확인할 수 있습니다.")
        
        cols = st.columns(3)
        for idx, row in dist_stats.head(9).iterrows():
            col_idx = dist_stats.head(9).index.tolist().index(idx)
            with cols[col_idx % 3]:
                rank = col_idx + 1
                medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"
                dist_name = row['총판']
                
                # Card button
                if st.button(f"{medal} {dist_name}", key=f"dist_card_{idx}"):
                    st.session_state[f'show_dist_detail_{dist_name}'] = not st.session_state.get(f'show_dist_detail_{dist_name}', False)
                
                st.markdown(f"""
                <div style="border: 2px solid {'#FFD700' if rank == 1 else '#C0C0C0' if rank == 2 else '#CD7F32' if rank == 3 else '#4CAF50'}; 
                            border-radius: 10px; padding: 15px; margin: 10px 0;">
                    <h4>{medal} {dist_name}</h4>
                    <p><b>종합점수:</b> {row['종합점수']:.1f}</p>
                    <p><b>주문:</b> {row['주문부수']:,.0f}부 ({row['판매비중(%)']:.1f}%)</p>
                    <p><b>거래학교:</b> {row['거래학교수']}개교</p>
                    <p><b>평균/학교:</b> {row['학교당평균']:.1f}부</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Show detail when clicked
                if st.session_state.get(f'show_dist_detail_{dist_name}', False):
                    with st.expander(f"📊 {dist_name} 상세 정보", expanded=True):
                        dist_orders = filtered_order_df[filtered_order_df['총판'] == dist_name]
                        
                        # Subject breakdown
                        st.markdown("**📚 과목별 주문**")
                        subject_summary = dist_orders.groupby('과목명')['부수'].sum().reset_index()
                        subject_summary = subject_summary.sort_values('부수', ascending=False)
                        st.dataframe(
                            subject_summary.style.format({'부수': '{:,.0f}'}),
                            use_container_width=True,
                            height=150
                        )
                        
                        st.markdown("---")
                        
                        # Regional breakdown with school level
                        if '시도교육청' in dist_orders.columns:
                            st.markdown("**🗺️ 지역별 주문 현황**")
                            
                            # Get school codes from orders and merge with total data
                            if '정보공시학교코드' in dist_orders.columns:
                                # Merge to get school level info
                                dist_with_level = pd.merge(
                                    dist_orders,
                                    total_df[['정보공시 학교코드', '학교급코드', '학생수(계)']].drop_duplicates(),
                                    left_on='정보공시학교코드',
                                    right_on='정보공시 학교코드',
                                    how='left'
                                )
                                
                                school_level_names = {2: '초등학교', 3: '중학교', 4: '고등학교'}
                                dist_with_level['학교급'] = dist_with_level['학교급코드'].map(school_level_names)
                                
                                # Group by region and school level
                                region_school_summary = dist_with_level.groupby(['시도교육청', '학교급']).agg({
                                    '부수': 'sum',
                                    '학생수(계)': 'sum'
                                }).reset_index()
                                
                                # Display by region
                                for region in region_school_summary['시도교육청'].unique():
                                    region_data = region_school_summary[region_school_summary['시도교육청'] == region]
                                    st.write(f"**{region}**")
                                    for _, level_row in region_data.iterrows():
                                        if pd.notna(level_row['학교급']):
                                            st.write(f"  - {level_row['학교급']}: 주문 {level_row['부수']:,.0f}부 / 전체학생 {level_row['학생수(계)']:,.0f}명")
                            else:
                                # Simple regional breakdown
                                region_summary = dist_orders.groupby('시도교육청')['부수'].sum().reset_index()
                                region_summary = region_summary.sort_values('부수', ascending=False)
                                for _, reg_row in region_summary.iterrows():
                                    st.write(f"- {reg_row['시도교육청']}: {reg_row['부수']:,.0f}부")
        
        # Regional distribution by distributor
        st.markdown("---")
        st.subheader("📍 총판별 지역 분포")
        
        if '시도교육청' in filtered_order_df.columns:
            selected_dist = st.selectbox("총판 선택", dist_stats['총판'].tolist())
            
            dist_regional = filtered_order_df[filtered_order_df['총판'] == selected_dist].groupby('시도교육청')['부수'].sum().reset_index()
            dist_regional = dist_regional.sort_values('부수', ascending=False)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig = px.bar(
                    dist_regional,
                    x='시도교육청',
                    y='부수',
                    title=f"{selected_dist} - 지역별 주문 분포",
                    text='부수',
                    color='부수',
                    color_continuous_scale='Oranges'
                )
                fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
                fig.update_layout(xaxis_tickangle=-45, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig_pie = px.pie(
                    dist_regional.head(10),
                    values='부수',
                    names='시도교육청',
                    title=f"{selected_dist} 지역 비중"
                )
                st.plotly_chart(fig_pie, use_container_width=True)
    
    with tab4:
        st.subheader("📋 총판별 상세 데이터")
        
        # Search
        search_term = st.text_input("🔍 총판명 검색", "")
        
        if search_term:
            display_stats = dist_stats[dist_stats['총판'].str.contains(search_term, case=False, na=False)]
        else:
            display_stats = dist_stats
        
        # Display table
        st.dataframe(
            display_stats.style.format({
                '주문부수': '{:,.0f}',
                '주문금액': '{:,.0f}',
                '거래학교수': '{:,.0f}',
                '취급과목수': '{:,.0f}',
                '판매비중(%)': '{:.2f}%',
                '학교당평균': '{:.2f}',
                '종합점수': '{:.2f}'
            }),
            use_container_width=True,
            height=400
        )
        
        # Download
        csv = display_stats.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 CSV 다운로드",
            data=csv,
            file_name="총판별_분석_데이터.csv",
            mime="text/csv"
        )

else:
    st.warning("총판 정보가 없습니다.")

st.markdown("---")
st.caption("🏢 총판별 분석 페이지")
