import streamlit as st
from utils.style import apply_custom_style
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.year_filter import add_year_filter_sidebar, filter_by_years, create_year_comparison_metrics
from utils.market_share_calculator import calculate_both_shares, compare_year_shares

st.set_page_config(page_title="비교 분석", page_icon="🔍", layout="wide")
apply_custom_style()

# Get data
if 'total_df' not in st.session_state or 'order_df' not in st.session_state:
    st.error("데이터를 불러올 수 없습니다. 메인 페이지로 돌아가주세요.")
    st.stop()

total_df = st.session_state['total_df']
order_df_orig = st.session_state['order_df'].copy()
market_analysis = st.session_state.get('market_analysis', pd.DataFrame())  # 시장 분석 데이터

# 학년도 필터 추가
selected_years, comparison_mode = add_year_filter_sidebar(order_df_orig, default_year='2026')
if selected_years:
    order_df = filter_by_years(order_df_orig, selected_years)
else:
    order_df = order_df_orig

st.title("🔍 다차원 비교 분석")
st.markdown("---")

# Tab Layout
tab1, tab2, tab3, tab4 = st.tabs(["🆚 A/B 비교", "📊 크로스 분석", "🎯 벤치마크", "📈 트렌드 분석"])

with tab1:
    st.subheader("🆚 A/B 비교 분석 (점유율 기준)")
    
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
        
        # Calculate market size for each region
        school_code_col = '정보공시학교코드' if '정보공시학교코드' in data_a.columns else '학교코드'
        schools_a_codes = data_a[school_code_col].unique() if school_code_col in data_a.columns else []
        schools_b_codes = data_b[school_code_col].unique() if school_code_col in data_b.columns else []
        
        # Calculate market size (중등/고등 1,2학년 학생수)
        if not total_df.empty:
            schools_a_df = total_df[total_df['정보공시 학교코드'].isin(pd.Series(schools_a_codes).astype(str))]
            market_a = 0
            for _, school in schools_a_df.iterrows():
                grade_code = school.get('학교급코드', 0)
                if grade_code == 3:  # 중학교
                    market_a += school.get('1학년 학생수', 0) + school.get('2학년 학생수', 0)
                elif grade_code == 4:  # 고등학교
                    market_a += school.get('1학년 학생수', 0) + school.get('2학년 학생수', 0)
            
            schools_b_df = total_df[total_df['정보공시 학교코드'].isin(pd.Series(schools_b_codes).astype(str))]
            market_b = 0
            for _, school in schools_b_df.iterrows():
                grade_code = school.get('학교급코드', 0)
                if grade_code == 3:  # 중학교
                    market_b += school.get('1학년 학생수', 0) + school.get('2학년 학생수', 0)
                elif grade_code == 4:  # 고등학교
                    market_b += school.get('1학년 학생수', 0) + school.get('2학년 학생수', 0)
        else:
            market_a = market_b = 0
        
        orders_a = data_a['부수'].sum()
        orders_b = data_b['부수'].sum()
        share_a = (orders_a / market_a * 100) if market_a > 0 else 0
        share_b = (orders_b / market_b * 100) if market_b > 0 else 0
        
        # Summary cards with visual comparison
        st.markdown("### 📊 종합 비교")
        cols = st.columns(2)
        
        with cols[0]:
            color_a = '#4CAF50' if share_a >= share_b else '#FF9800'
            st.markdown(f"""
            <div style="border: 3px solid {color_a}; border-radius: 15px; padding: 25px; background: linear-gradient(135deg, {color_a}22 0%, {color_a}11 100%);">
                <h2 style="margin:0; color:{color_a};">📍 {region_a}</h2>
                <hr style="border-color:{color_a};">
                <h1 style="margin:10px 0; color:{color_a}; font-size:3em;">{share_a:.2f}%</h1>
                <p style="font-size:1.2em; margin:5px 0;"><b>시장 점유율</b></p>
                <p style="margin:5px 0;">주문량: {orders_a:,.0f}부</p>
                <p style="margin:5px 0;">시장규모: {market_a:,.0f}명</p>
                <p style="margin:5px 0;">학교수: {len(schools_a_codes)}개교</p>
            </div>
            """, unsafe_allow_html=True)
        
        with cols[1]:
            color_b = '#4CAF50' if share_b >= share_a else '#FF9800'
            st.markdown(f"""
            <div style="border: 3px solid {color_b}; border-radius: 15px; padding: 25px; background: linear-gradient(135deg, {color_b}22 0%, {color_b}11 100%);">
                <h2 style="margin:0; color:{color_b};">📍 {region_b}</h2>
                <hr style="border-color:{color_b};">
                <h1 style="margin:10px 0; color:{color_b}; font-size:3em;">{share_b:.2f}%</h1>
                <p style="font-size:1.2em; margin:5px 0;"><b>시장 점유율</b></p>
                <p style="margin:5px 0;">주문량: {orders_b:,.0f}부</p>
                <p style="margin:5px 0;">시장규모: {market_b:,.0f}명</p>
                <p style="margin:5px 0;">학교수: {len(schools_b_codes)}개교</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Comparison chart - Market Share
        st.markdown("---")
        st.markdown("### 📈 점유율 비교")
        
        fig_share = go.Figure()
        fig_share.add_trace(go.Bar(
            name='점유율 (%)',
            x=[region_a, region_b],
            y=[share_a, share_b],
            text=[f'{share_a:.2f}%', f'{share_b:.2f}%'],
            textposition='outside',
            marker_color=['#4CAF50' if share_a >= share_b else '#FF9800', '#4CAF50' if share_b >= share_a else '#FF9800']
        ))
        fig_share.update_layout(
            title="지역별 시장 점유율 비교",
            yaxis_title="점유율 (%)",
            height=400,
            showlegend=False
        )
        st.plotly_chart(fig_share, use_container_width=True)
        
        # Subject comparison
        st.markdown("---")
        st.subheader("과목별 비교")
        
        subject_col = '교과서명_구분' if '교과서명_구분' in data_a.columns else '과목명'
        subject_a = data_a.groupby(subject_col)['부수'].sum().reset_index()
        subject_a.columns = [subject_col, region_a]
        
        subject_b = data_b.groupby(subject_col)['부수'].sum().reset_index()
        subject_b.columns = [subject_col, region_b]
        
        comparison_df = pd.merge(subject_a, subject_b, on=subject_col, how='outer').fillna(0)
        comparison_df['차이'] = comparison_df[region_a] - comparison_df[region_b]
        comparison_df = comparison_df.sort_values('차이', key=abs, ascending=False).head(15)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(name=region_a, x=comparison_df[subject_col], y=comparison_df[region_a]))
        fig.add_trace(go.Bar(name=region_b, x=comparison_df[subject_col], y=comparison_df[region_b]))
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
        
        # Calculate market size for each distributor
        school_code_col = '정보공시학교코드' if '정보공시학교코드' in data_a.columns else '학교코드'
        schools_a_codes = data_a[school_code_col].unique() if school_code_col in data_a.columns else []
        schools_b_codes = data_b[school_code_col].unique() if school_code_col in data_b.columns else []
        
        # Calculate market size
        if not total_df.empty:
            schools_a_df = total_df[total_df['정보공시 학교코드'].isin(pd.Series(schools_a_codes).astype(str))]
            market_a = 0
            for _, school in schools_a_df.iterrows():
                grade_code = school.get('학교급코드', 0)
                if grade_code == 3:  # 중학교
                    market_a += school.get('1학년 학생수', 0) + school.get('2학년 학생수', 0)
                elif grade_code == 4:  # 고등학교
                    market_a += school.get('1학년 학생수', 0) + school.get('2학년 학생수', 0)
            
            schools_b_df = total_df[total_df['정보공시 학교코드'].isin(pd.Series(schools_b_codes).astype(str))]
            market_b = 0
            for _, school in schools_b_df.iterrows():
                grade_code = school.get('학교급코드', 0)
                if grade_code == 3:  # 중학교
                    market_b += school.get('1학년 학생수', 0) + school.get('2학년 학생수', 0)
                elif grade_code == 4:  # 고등학교
                    market_b += school.get('1학년 학생수', 0) + school.get('2학년 학생수', 0)
        else:
            market_a = market_b = 0
        
        # Metrics comparison
        orders_a = data_a['부수'].sum()
        orders_b = data_b['부수'].sum()
        share_a = (orders_a / market_a * 100) if market_a > 0 else 0
        share_b = (orders_b / market_b * 100) if market_b > 0 else 0
        
        amount_a = data_a['금액'].sum() if '금액' in data_a.columns else 0
        amount_b = data_b['금액'].sum() if '금액' in data_b.columns else 0
        
        # Summary cards
        st.markdown("### 📊 종합 비교")
        cols = st.columns(2)
        
        with cols[0]:
            color_a = '#4CAF50' if share_a >= share_b else '#FF9800'
            st.markdown(f"""
            <div style="border: 3px solid {color_a}; border-radius: 15px; padding: 25px; background: linear-gradient(135deg, {color_a}22 0%, {color_a}11 100%);">
                <h2 style="margin:0; color:{color_a};">🏢 {dist_a}</h2>
                <hr style="border-color:{color_a};">
                <h1 style="margin:10px 0; color:{color_a}; font-size:3em;">{share_a:.2f}%</h1>
                <p style="font-size:1.2em; margin:5px 0;"><b>시장 점유율</b></p>
                <p style="margin:5px 0;">주문량: {orders_a:,.0f}부</p>
                <p style="margin:5px 0;">주문금액: {amount_a:,.0f}원</p>
                <p style="margin:5px 0;">시장규모: {market_a:,.0f}명</p>
                <p style="margin:5px 0;">학교수: {len(schools_a_codes)}개교</p>
            </div>
            """, unsafe_allow_html=True)
        
        with cols[1]:
            color_b = '#4CAF50' if share_b >= share_a else '#FF9800'
            st.markdown(f"""
            <div style="border: 3px solid {color_b}; border-radius: 15px; padding: 25px; background: linear-gradient(135deg, {color_b}22 0%, {color_b}11 100%);">
                <h2 style="margin:0; color:{color_b};">🏢 {dist_b}</h2>
                <hr style="border-color:{color_b};">
                <h1 style="margin:10px 0; color:{color_b}; font-size:3em;">{share_b:.2f}%</h1>
                <p style="font-size:1.2em; margin:5px 0;"><b>시장 점유율</b></p>
                <p style="margin:5px 0;">주문량: {orders_b:,.0f}부</p>
                <p style="margin:5px 0;">주문금액: {amount_b:,.0f}원</p>
                <p style="margin:5px 0;">시장규모: {market_b:,.0f}명</p>
                <p style="margin:5px 0;">학교수: {len(schools_b_codes)}개교</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Comparison visualization
        st.markdown("---")
        st.markdown("### 📈 종합 비교 차트")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Market share comparison
            fig_share = go.Figure()
            fig_share.add_trace(go.Bar(
                name='점유율 (%)',
                x=[dist_a, dist_b],
                y=[share_a, share_b],
                text=[f'{share_a:.2f}%', f'{share_b:.2f}%'],
                textposition='outside',
                marker_color=['#4CAF50' if share_a >= share_b else '#FF9800', '#4CAF50' if share_b >= share_a else '#FF9800']
            ))
            fig_share.update_layout(
                title="시장 점유율 비교",
                yaxis_title="점유율 (%)",
                height=400,
                showlegend=False
            )
            st.plotly_chart(fig_share, use_container_width=True)
        
        with col2:
            # Radar chart for normalized comparison
            categories = ['점유율', '주문량', '주문금액', '학교수']
            
            # Normalize values
            max_share = max(share_a, share_b) if max(share_a, share_b) > 0 else 1
            max_orders = max(orders_a, orders_b) if max(orders_a, orders_b) > 0 else 1
            max_amount = max(amount_a, amount_b) if max(amount_a, amount_b) > 0 else 1
            max_schools = max(len(schools_a_codes), len(schools_b_codes)) if max(len(schools_a_codes), len(schools_b_codes)) > 0 else 1
            
            normalized_a = [
                share_a / max_share * 100,
                orders_a / max_orders * 100,
                amount_a / max_amount * 100,
                len(schools_a_codes) / max_schools * 100
            ]
            
            normalized_b = [
                share_b / max_share * 100,
                orders_b / max_orders * 100,
                amount_b / max_amount * 100,
                len(schools_b_codes) / max_schools * 100
            ]
            
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=normalized_a + [normalized_a[0]],
                theta=categories + [categories[0]],
                fill='toself',
                name=dist_a
            ))
            fig_radar.add_trace(go.Scatterpolar(
                r=normalized_b + [normalized_b[0]],
                theta=categories + [categories[0]],
                fill='toself',
                name=dist_b
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                title="다차원 비교 (정규화)",
                height=400
            )
            st.plotly_chart(fig_radar, use_container_width=True)

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
        school_code_col = '정보공시학교코드' if '정보공시학교코드' in order_df.columns else '학교코드'
        
        region_stats = order_df.groupby('시도교육청').agg({
            '부수': 'sum',
            '금액': 'sum' if '금액' in order_df.columns else 'count',
            school_code_col: 'nunique'
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
    
    school_code_col = '정보공시학교코드' if '정보공시학교코드' in order_df.columns else '학교코드'
    
    analysis_dim = st.selectbox(
        "분석 차원 선택",
        ['시도교육청', '총판', '과목명', school_code_col]
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
