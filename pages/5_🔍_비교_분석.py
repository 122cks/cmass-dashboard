import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="비교 분석", page_icon="🔍", layout="wide")

# Get data
if 'total_df' not in st.session_state or 'order_df' not in st.session_state:
    st.error("데이터를 불러올 수 없습니다. 메인 페이지로 돌아가주세요.")
    st.stop()

total_df = st.session_state['total_df']
order_df = st.session_state['order_df']

st.title("🔍 다차원 비교 분석")
st.markdown("---")

# Tab Layout
tab1, tab2, tab3, tab4 = st.tabs(["🆚 A/B 비교", "📊 크로스 분석", "🎯 벤치마크", "📈 트렌드 분석"])

with tab1:
    st.subheader("🆚 A/B 비교 분석")
    
    col1, col2 = st.columns(2)
    
    # Comparison dimension selection
    comparison_dim = st.radio(
        "비교 차원 선택",
        ["지역 비교", "총판 비교", "과목 비교", "교과군 비교"]
    )
    
    if comparison_dim == "지역 비교" and '시도교육청' in order_df.columns:
        regions = sorted(order_df['시도교육청'].dropna().unique().tolist())
        
        with col1:
            region_a = st.selectbox("지역 A", regions, index=0)
        with col2:
            region_b = st.selectbox("지역 B", regions, index=min(1, len(regions)-1))
        
        # Compare regions
        data_a = order_df[order_df['시도교육청'] == region_a]
        data_b = order_df[order_df['시도교육청'] == region_b]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            orders_a = data_a['부수'].sum()
            orders_b = data_b['부수'].sum()
            st.metric(f"{region_a} 주문량", f"{orders_a:,.0f}부", delta=f"{orders_a - orders_b:+,.0f}부")
            st.metric(f"{region_b} 주문량", f"{orders_b:,.0f}부")
        
        with col2:
            schools_a = data_a['학교코드'].nunique() if '학교코드' in data_a.columns else len(data_a)
            schools_b = data_b['학교코드'].nunique() if '학교코드' in data_b.columns else len(data_b)
            st.metric(f"{region_a} 학교 수", f"{schools_a}개교", delta=f"{schools_a - schools_b:+}개교")
            st.metric(f"{region_b} 학교 수", f"{schools_b}개교")
        
        with col3:
            avg_a = orders_a / schools_a if schools_a > 0 else 0
            avg_b = orders_b / schools_b if schools_b > 0 else 0
            st.metric(f"{region_a} 학교당 평균", f"{avg_a:.1f}부", delta=f"{avg_a - avg_b:+.1f}부")
            st.metric(f"{region_b} 학교당 평균", f"{avg_b:.1f}부")
        
        # Subject comparison
        st.markdown("---")
        st.subheader("과목별 비교")
        
        subject_a = data_a.groupby('과목명')['부수'].sum().reset_index()
        subject_a.columns = ['과목명', region_a]
        
        subject_b = data_b.groupby('과목명')['부수'].sum().reset_index()
        subject_b.columns = ['과목명', region_b]
        
        comparison_df = pd.merge(subject_a, subject_b, on='과목명', how='outer').fillna(0)
        comparison_df['차이'] = comparison_df[region_a] - comparison_df[region_b]
        comparison_df = comparison_df.sort_values('차이', key=abs, ascending=False).head(15)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(name=region_a, x=comparison_df['과목명'], y=comparison_df[region_a]))
        fig.add_trace(go.Bar(name=region_b, x=comparison_df['과목명'], y=comparison_df[region_b]))
        fig.update_layout(title="과목별 주문량 비교 TOP 15", barmode='group', height=400, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    
    elif comparison_dim == "총판 비교" and '총판' in order_df.columns:
        distributors = sorted(order_df['총판'].dropna().unique().tolist())
        
        with col1:
            dist_a = st.selectbox("총판 A", distributors, index=0)
        with col2:
            dist_b = st.selectbox("총판 B", distributors, index=min(1, len(distributors)-1))
        
        data_a = order_df[order_df['총판'] == dist_a]
        data_b = order_df[order_df['총판'] == dist_b]
        
        # Metrics comparison
        metrics = {
            '주문부수': data_a['부수'].sum(),
            '주문금액': data_a['금액'].sum() if '금액' in data_a.columns else 0,
            '거래학교': data_a['학교코드'].nunique() if '학교코드' in data_a.columns else len(data_a),
            '취급과목': data_a['과목명'].nunique() if '과목명' in data_a.columns else 0
        }
        
        metrics_b = {
            '주문부수': data_b['부수'].sum(),
            '주문금액': data_b['금액'].sum() if '금액' in data_b.columns else 0,
            '거래학교': data_b['학교코드'].nunique() if '학교코드' in data_b.columns else len(data_b),
            '취급과목': data_b['과목명'].nunique() if '과목명' in data_b.columns else 0
        }
        
        # Radar comparison
        categories = list(metrics.keys())
        
        fig = go.Figure()
        
        # Normalize for radar
        max_vals = [max(metrics[k], metrics_b[k]) for k in categories]
        normalized_a = [metrics[k]/max_vals[i]*100 if max_vals[i] > 0 else 0 for i, k in enumerate(categories)]
        normalized_b = [metrics_b[k]/max_vals[i]*100 if max_vals[i] > 0 else 0 for i, k in enumerate(categories)]
        
        fig.add_trace(go.Scatterpolar(
            r=normalized_a + [normalized_a[0]],
            theta=categories + [categories[0]],
            fill='toself',
            name=dist_a
        ))
        
        fig.add_trace(go.Scatterpolar(
            r=normalized_b + [normalized_b[0]],
            theta=categories + [categories[0]],
            fill='toself',
            name=dist_b
        ))
        
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            title=f"{dist_a} vs {dist_b} 종합 비교",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("📊 크로스 분석 (교차 분석)")
    
    # Select two dimensions for cross-analysis
    col1, col2 = st.columns(2)
    
    available_dims = []
    if '시도교육청' in order_df.columns:
        available_dims.append('시도교육청')
    if '총판' in order_df.columns:
        available_dims.append('총판')
    if '과목명' in order_df.columns:
        available_dims.append('과목명')
    if '교과군' in order_df.columns:
        available_dims.append('교과군')
    if '교지명' in order_df.columns:
        available_dims.append('교지명')
    
    with col1:
        dim1 = st.selectbox("차원 1 (행)", available_dims, index=0)
    with col2:
        dim2 = st.selectbox("차원 2 (열)", available_dims, index=min(1, len(available_dims)-1))
    
    if dim1 and dim2 and dim1 != dim2:
        # Create pivot table
        pivot = order_df.pivot_table(
            index=dim1,
            columns=dim2,
            values='부수',
            aggfunc='sum',
            fill_value=0
        )
        
        # Show top items for each dimension
        top_dim1 = order_df.groupby(dim1)['부수'].sum().nlargest(15).index.tolist()
        top_dim2 = order_df.groupby(dim2)['부수'].sum().nlargest(15).index.tolist()
        
        pivot_filtered = pivot.loc[top_dim1, top_dim2]
        
        # Heatmap
        fig_heatmap = px.imshow(
            pivot_filtered,
            title=f"{dim1} × {dim2} 크로스 분석 (주문량)",
            labels=dict(x=dim2, y=dim1, color="주문 부수"),
            aspect="auto",
            color_continuous_scale='RdYlGn'
        )
        fig_heatmap.update_layout(height=600)
        st.plotly_chart(fig_heatmap, use_container_width=True)
        
        # Summary statistics
        st.markdown("---")
        st.subheader("📈 요약 통계")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Top combinations
            st.markdown("#### 상위 조합 TOP 10")
            cross_sum = pivot_filtered.stack().reset_index()
            cross_sum.columns = [dim1, dim2, '주문량']
            cross_sum = cross_sum.sort_values('주문량', ascending=False).head(10)
            
            for idx, row in cross_sum.iterrows():
                st.write(f"{cross_sum.index.tolist().index(idx) + 1}. **{row[dim1]}** × **{row[dim2]}**: {row['주문량']:,.0f}부")
        
        with col2:
            # Dimension totals
            st.markdown(f"#### {dim1} 합계 TOP 10")
            dim1_totals = pivot_filtered.sum(axis=1).sort_values(ascending=False).head(10)
            
            for idx, val in dim1_totals.items():
                st.write(f"• **{idx}**: {val:,.0f}부")

with tab3:
    st.subheader("🎯 벤치마크 분석")
    
    # Select benchmark type
    benchmark_type = st.radio(
        "벤치마크 유형",
        ["지역별 벤치마크", "총판별 벤치마크", "과목별 벤치마크"]
    )
    
    if benchmark_type == "지역별 벤치마크" and '시도교육청' in order_df.columns:
        # Regional benchmark
        region_stats = order_df.groupby('시도교육청').agg({
            '부수': 'sum',
            '금액': 'sum' if '금액' in order_df.columns else 'count',
            '학교코드': 'nunique' if '학교코드' in order_df.columns else 'count'
        }).reset_index()
        
        region_stats.columns = ['지역', '주문량', '주문금액', '학교수']
        region_stats['학교당평균'] = region_stats['주문량'] / region_stats['학교수']
        
        # Calculate percentiles
        region_stats['주문량_백분위'] = region_stats['주문량'].rank(pct=True) * 100
        region_stats['학교당평균_백분위'] = region_stats['학교당평균'].rank(pct=True) * 100
        
        # Scatter plot with quadrants
        avg_orders = region_stats['주문량'].mean()
        avg_per_school = region_stats['학교당평균'].mean()
        
        fig = px.scatter(
            region_stats,
            x='주문량',
            y='학교당평균',
            size='학교수',
            color='주문량_백분위',
            hover_name='지역',
            title="지역별 벤치마크 (총 주문량 vs 학교당 평균)",
            labels={'주문량': '총 주문량', '학교당평균': '학교당 평균 주문량'},
            color_continuous_scale='RdYlGn'
        )
        
        # Add benchmark lines
        fig.add_hline(y=avg_per_school, line_dash="dash", line_color="gray", 
                      annotation_text=f"평균 학교당: {avg_per_school:.1f}")
        fig.add_vline(x=avg_orders, line_dash="dash", line_color="gray",
                      annotation_text=f"평균 주문량: {avg_orders:,.0f}")
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Quadrant analysis
        st.markdown("---")
        st.subheader("🔲 사분면 분석")
        
        region_stats['사분면'] = region_stats.apply(
            lambda row: '⭐ 고성과' if row['주문량'] >= avg_orders and row['학교당평균'] >= avg_per_school
            else '📈 성장형' if row['주문량'] < avg_orders and row['학교당평균'] >= avg_per_school
            else '🔄 확장형' if row['주문량'] >= avg_orders and row['학교당평균'] < avg_per_school
            else '⚠️ 개선필요',
            axis=1
        )
        
        cols = st.columns(4)
        quadrants = ['⭐ 고성과', '📈 성장형', '🔄 확장형', '⚠️ 개선필요']
        
        for idx, quad in enumerate(quadrants):
            with cols[idx]:
                quad_data = region_stats[region_stats['사분면'] == quad]
                st.markdown(f"### {quad}")
                st.markdown(f"**{len(quad_data)}개 지역**")
                for _, row in quad_data.iterrows():
                    st.write(f"• {row['지역']}")

with tab4:
    st.subheader("📈 패턴 및 트렌드 분석")
    
    # Distribution analysis
    st.markdown("#### 📊 주문량 분포 분석")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Order quantity distribution
        fig_hist = px.histogram(
            order_df,
            x='부수',
            nbins=50,
            title="주문 부수 분포",
            labels={'부수': '주문 부수', 'count': '빈도'}
        )
        fig_hist.update_layout(height=400)
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
        # Log scale distribution
        if '부수' in order_df.columns:
            order_df_temp = order_df[order_df['부수'] > 0].copy()
            fig_log = px.histogram(
                order_df_temp,
                x='부수',
                nbins=50,
                title="주문 부수 분포 (로그 스케일)",
                log_y=True,
                labels={'부수': '주문 부수', 'count': '빈도'}
            )
            fig_log.update_layout(height=400)
            st.plotly_chart(fig_log, use_container_width=True)
    
    # Pareto analysis
    st.markdown("---")
    st.subheader("📊 파레토 분석 (80/20 법칙)")
    
    analysis_dim = st.selectbox(
        "분석 차원 선택",
        ['시도교육청', '총판', '과목명', '학교코드'] if '학교코드' in order_df.columns else ['시도교육청', '총판', '과목명']
    )
    
    if analysis_dim in order_df.columns:
        pareto_data = order_df.groupby(analysis_dim)['부수'].sum().sort_values(ascending=False).reset_index()
        pareto_data['누적합'] = pareto_data['부수'].cumsum()
        pareto_data['누적비율(%)'] = (pareto_data['누적합'] / pareto_data['부수'].sum()) * 100
        
        # Find 80% point
        point_80 = pareto_data[pareto_data['누적비율(%)'] >= 80].index[0] if len(pareto_data[pareto_data['누적비율(%)'] >= 80]) > 0 else len(pareto_data)
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig.add_trace(
            go.Bar(name="주문량", x=pareto_data.head(30).index, y=pareto_data.head(30)['부수']),
            secondary_y=False
        )
        
        fig.add_trace(
            go.Scatter(name="누적비율", x=pareto_data.head(30).index, y=pareto_data.head(30)['누적비율(%)'],
                      mode='lines+markers', marker=dict(size=8)),
            secondary_y=True
        )
        
        fig.add_hline(y=80, line_dash="dash", line_color="red", secondary_y=True,
                      annotation_text="80% 지점")
        
        fig.update_xaxes(title_text=analysis_dim)
        fig.update_yaxes(title_text="주문 부수", secondary_y=False)
        fig.update_yaxes(title_text="누적 비율 (%)", secondary_y=True)
        fig.update_layout(title=f"{analysis_dim} 파레토 분석 (TOP 30)", height=500)
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.info(f"💡 상위 {point_80 + 1}개 {analysis_dim}이(가) 전체 주문량의 80%를 차지합니다.")

st.markdown("---")
st.caption("🔍 비교 분석 페이지")
