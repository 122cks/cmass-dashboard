import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="총판 비교분석", page_icon="🔄", layout="wide")

# Get data
if 'total_df' not in st.session_state or 'order_df' not in st.session_state:
    st.error("데이터를 불러올 수 없습니다. 메인 페이지로 돌아가주세요.")
    st.stop()

total_df = st.session_state['total_df']
order_df = st.session_state['order_df']
target_df = st.session_state.get('target_df', pd.DataFrame())
distributor_df = st.session_state.get('distributor_df', pd.DataFrame())

st.title("🔄 총판 비교 분석")
st.markdown("---")

# Sidebar - Distributor Selection
st.sidebar.header("🏢 비교할 총판 선택")

available_distributors = sorted(order_df['총판'].dropna().unique().tolist())

# Multi-select for distributors (2-6 distributors)
selected_distributors = st.sidebar.multiselect(
    "총판 선택 (2~6개)",
    available_distributors,
    default=available_distributors[:3] if len(available_distributors) >= 3 else available_distributors[:2]
)

if len(selected_distributors) < 2:
    st.warning("⚠️ 비교를 위해 최소 2개의 총판을 선택해주세요.")
    st.stop()
elif len(selected_distributors) > 6:
    st.warning("⚠️ 최대 6개까지 선택 가능합니다.")
    selected_distributors = selected_distributors[:6]

# Filter data
filtered_order = order_df[order_df['총판'].isin(selected_distributors)]

st.sidebar.markdown("---")
st.sidebar.info(f"📊 선택된 총판: {len(selected_distributors)}개")

# Main content tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 종합 비교", "📈 실적 대비", "🗺️ 지역별 분포", "📚 과목별 분석"])

with tab1:
    st.subheader("총판별 종합 성과 비교")
    
    # Get market size by level from session
    market_size_by_level = st.session_state.get('market_size_by_level', {})
    
    # For now, use '전체' market size (중등 1,2학년 + 고등 1,2학년)
    # TODO: In future, could filter by school level if needed
    total_market_size = market_size_by_level.get('전체', 0)
    
    # Calculate comprehensive statistics with market share
    comparison_stats = []
    for dist in selected_distributors:
        dist_data = filtered_order[filtered_order['총판'] == dist]
        
        # Determine school code column
        school_code_col = '정보공시학교코드' if '정보공시학교코드' in dist_data.columns else '학교코드'
        subject_col = '교과서명_구분' if '교과서명_구분' in dist_data.columns else '교과서명'
        
        # Use total national market size (중등 1,2학년 + 고등 1,2학년)
        market_size = total_market_size
        
        stats = {
            '총판': dist,
            '주문부수': dist_data['부수'].sum(),
            '시장규모': market_size,
            '점유율(%)': (dist_data['부수'].sum() / market_size * 100) if market_size > 0 else 0,
            '주문금액': dist_data['금액'].sum() if '금액' in dist_data.columns else 0,
            '거래학교수': dist_data[school_code_col].nunique() if school_code_col in dist_data.columns else 0,
            '취급과목수': dist_data[subject_col].nunique() if subject_col in dist_data.columns else 0,
            '학교당평균': 0
        }
        stats['학교당평균'] = stats['주문부수'] / stats['거래학교수'] if stats['거래학교수'] > 0 else 0
        
        # Get target and grade info from distributor_df
        if not distributor_df.empty and '총판명(공식)' in distributor_df.columns:
            # Match by official name
            dist_info = distributor_df[distributor_df['총판명(공식)'] == dist]
            if dist_info.empty:
                # Try partial match
                dist_info = distributor_df[distributor_df['총판명(공식)'].str.contains(dist.split(')')[-1], na=False)]
            if not dist_info.empty:
                stats['등급'] = dist_info.iloc[0].get('등급', '-')
            else:
                stats['등급'] = '-'
        else:
            stats['등급'] = '-'
        
        # Get target from target_df
        if not target_df.empty and '총판명' in target_df.columns:
            # Try matching with official name
            target_info = target_df[target_df['총판명'] == dist]
            if target_info.empty:
                # Try partial match
                dist_name = dist.split(')')[-1] if ')' in dist else dist
                target_info = target_df[target_df['총판명'].str.contains(dist_name, na=False)]
            if not target_info.empty:
                target_str = str(target_info.iloc[0].get('전체목표 부수', '0'))
                stats['목표부수'] = pd.to_numeric(target_str.replace(',', '').strip(), errors='coerce')
                if pd.notna(stats['목표부수']) and stats['목표부수'] > 0:
                    stats['목표달성률'] = (stats['주문부수'] / stats['목표부수']) * 100
                else:
                    stats['목표달성률'] = 0
            else:
                stats['목표부수'] = 0
                stats['목표달성률'] = 0
        else:
            stats['목표부수'] = 0
            stats['목표달성률'] = 0
        
        comparison_stats.append(stats)
    
    comparison_df = pd.DataFrame(comparison_stats)
    
    # Display metrics cards with market share
    cols = st.columns(len(selected_distributors))
    for idx, (_, row) in enumerate(comparison_df.iterrows()):
        with cols[idx]:
            grade_color = {'S': '🥇', 'A': '🥈', 'B': '🥉', 'C': '⭐'}.get(row['등급'], '📍')
            st.markdown(f"""
            <div style="border: 2px solid #4CAF50; border-radius: 10px; padding: 15px; margin: 5px;">
                <h4>{grade_color} {row['총판']}</h4>
                <p><b>등급:</b> {row['등급']}</p>
                <p><b>주문:</b> {row['주문부수']:,.0f}부</p>
                <p><b>점유율:</b> {row['점유율(%)']:.2f}%</p>
                <p><b>시장규모:</b> {row['시장규모']:,.0f}명</p>
                <p><b>학교:</b> {row['거래학교수']}개교</p>
                {f"<p><b>목표달성:</b> {row['목표달성률']:.1f}%</p>" if row['목표달성률'] > 0 else ""}
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Comparative charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Bar chart - Market Share (점유율)
        fig1 = px.bar(
            comparison_df,
            x='총판',
            y='점유율(%)',
            title="총판별 시장 점유율 비교",
            text='점유율(%)',
            color='점유율(%)',
            color_continuous_scale='Greens'
        )
        fig1.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
        fig1.update_layout(yaxis_title="점유율 (%)")
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # Bar chart - Order volume
        fig2 = px.bar(
            comparison_df,
            x='총판',
            y='주문부수',
            title="총판별 주문 부수 비교",
            text='주문부수',
            color='주문부수',
            color_continuous_scale='Blues'
        )
        fig2.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig2, use_container_width=True)
            y='거래학교수',
            title="총판별 거래 학교 수 비교",
            text='거래학교수',
            color='거래학교수',
            color_continuous_scale='Greens'
        )
        fig2.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig2, use_container_width=True)
    
    # Multi-metric comparison
    st.markdown("---")
    st.subheader("📊 다차원 비교")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Radar chart
        metrics = ['주문부수', '거래학교수', '취급과목수', '학교당평균']
        normalized_data = comparison_df[metrics].copy()
        for col in metrics:
            max_val = normalized_data[col].max()
            normalized_data[col] = (normalized_data[col] / max_val) * 100 if max_val > 0 else 0
        
        fig_radar = go.Figure()
        for idx, row in comparison_df.iterrows():
            values = normalized_data.iloc[idx].tolist()
            values.append(values[0])
            
            fig_radar.add_trace(go.Scatterpolar(
                r=values,
                theta=metrics + [metrics[0]],
                name=row['총판'],
                fill='toself'
            ))
        
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            title="총판별 다차원 성과 비교 (정규화)"
        )
        st.plotly_chart(fig_radar, use_container_width=True)
    
    with col2:
        # Summary table
        st.markdown("#### 📋 비교 요약")
        display_df = comparison_df[['총판', '등급', '주문부수', '거래학교수', '학교당평균']].copy()
        st.dataframe(
            display_df.style.format({
                '주문부수': '{:,.0f}',
                '거래학교수': '{:,.0f}',
                '학교당평균': '{:.1f}'
            }),
            use_container_width=True,
            height=300
        )

with tab2:
    st.subheader("📈 목표 대비 실적 분석")
    
    if not target_df.empty:
        # Goal achievement comparison
        goal_data = comparison_df[comparison_df['목표부수'] > 0].copy()
        
        if not goal_data.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                # Achievement rate bar chart
                fig = px.bar(
                    goal_data,
                    x='총판',
                    y='목표달성률',
                    title="총판별 목표 달성률 (%)",
                    text='목표달성률',
                    color='목표달성률',
                    color_continuous_scale='RdYlGn'
                )
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="목표")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Goal vs Actual
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(
                    name='목표',
                    x=goal_data['총판'],
                    y=goal_data['목표부수'],
                    text=goal_data['목표부수'],
                    texttemplate='%{text:,.0f}'
                ))
                fig2.add_trace(go.Bar(
                    name='실적',
                    x=goal_data['총판'],
                    y=goal_data['주문부수'],
                    text=goal_data['주문부수'],
                    texttemplate='%{text:,.0f}'
                ))
                fig2.update_layout(title="목표 vs 실적 비교", barmode='group')
                st.plotly_chart(fig2, use_container_width=True)
            
            # Gap analysis
            st.markdown("---")
            st.subheader("📊 목표 대비 차이 분석")
            
            goal_data['차이'] = goal_data['주문부수'] - goal_data['목표부수']
            
            fig3 = px.bar(
                goal_data,
                x='총판',
                y='차이',
                title="목표 대비 실적 차이",
                text='차이',
                color='차이',
                color_continuous_scale='RdYlGn'
            )
            fig3.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig3.add_hline(y=0, line_dash="solid", line_color="black")
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("목표 데이터가 설정된 총판이 없습니다.")
    else:
        st.info("목표 데이터가 없습니다.")

with tab3:
    st.subheader("🗺️ 지역별 활동 비교")
    
    # Regional distribution for each distributor
    regional_comparison = []
    for dist in selected_distributors:
        dist_orders = filtered_order[filtered_order['총판'] == dist]
        if '시도교육청' in dist_orders.columns:
            regional = dist_orders.groupby('시도교육청')['부수'].sum().reset_index()
            regional['총판'] = dist
            regional_comparison.append(regional)
    
    if regional_comparison:
        regional_df = pd.concat(regional_comparison, ignore_index=True)
        
        # Grouped bar chart
        fig = px.bar(
            regional_df,
            x='시도교육청',
            y='부수',
            color='총판',
            title="총판별 지역 분포 비교",
            text='부수',
            barmode='group'
        )
        fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig.update_layout(height=500, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
        
        # Heatmap
        st.markdown("---")
        pivot_regional = regional_df.pivot(index='시도교육청', columns='총판', values='부수').fillna(0)
        
        fig_heatmap = px.imshow(
            pivot_regional,
            title="총판 × 지역 주문량 히트맵",
            labels=dict(x="총판", y="지역", color="주문량"),
            aspect="auto",
            color_continuous_scale='YlOrRd'
        )
        fig_heatmap.update_layout(height=600)
        st.plotly_chart(fig_heatmap, use_container_width=True)
        
        # Market share by region
        st.markdown("---")
        st.subheader("지역별 총판 점유율")
        
        # Calculate share within selected distributors per region
        pivot_pct = pivot_regional.div(pivot_regional.sum(axis=1), axis=0) * 100
        
        fig_share = px.bar(
            pivot_pct.reset_index().melt(id_vars='시도교육청', var_name='총판', value_name='점유율'),
            x='시도교육청',
            y='점유율',
            color='총판',
            title="지역별 총판 점유율 (%)",
            barmode='stack',
            text='점유율'
        )
        fig_share.update_traces(texttemplate='%{text:.1f}%', textposition='inside')
        fig_share.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_share, use_container_width=True)

with tab4:
    st.subheader("📚 과목별 판매 비교")
    
    # Subject distribution for each distributor
    subject_comparison = []
    for dist in selected_distributors:
        dist_orders = filtered_order[filtered_order['총판'] == dist]
        subject = dist_orders.groupby('과목명')['부수'].sum().reset_index()
        subject['총판'] = dist
        subject_comparison.append(subject)
    
    if subject_comparison:
        subject_df = pd.concat(subject_comparison, ignore_index=True)
        
        # Get top subjects
        top_subjects = subject_df.groupby('과목명')['부수'].sum().sort_values(ascending=False).head(10).index
        subject_df_top = subject_df[subject_df['과목명'].isin(top_subjects)]
        
        # Grouped bar chart
        fig = px.bar(
            subject_df_top,
            x='과목명',
            y='부수',
            color='총판',
            title="총판별 주요 과목 판매량 비교 (TOP 10)",
            text='부수',
            barmode='group'
        )
        fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig.update_layout(height=500, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
        
        # Stacked area chart
        st.markdown("---")
        
        pivot_subject = subject_df_top.pivot(index='과목명', columns='총판', values='부수').fillna(0)
        
        fig_area = go.Figure()
        for col in pivot_subject.columns:
            fig_area.add_trace(go.Bar(
                name=col,
                x=pivot_subject.index,
                y=pivot_subject[col],
                text=pivot_subject[col],
                texttemplate='%{text:,.0f}'
            ))
        
        fig_area.update_layout(
            title="과목별 총판 판매량 누적",
            barmode='stack',
            xaxis_tickangle=-45
        )
        st.plotly_chart(fig_area, use_container_width=True)
        
        # Detailed table
        st.markdown("---")
        st.subheader("📋 과목별 상세 비교")
        
        pivot_display = subject_df.pivot(index='과목명', columns='총판', values='부수').fillna(0)
        pivot_display['합계'] = pivot_display.sum(axis=1)
        pivot_display = pivot_display.sort_values('합계', ascending=False)
        
        st.dataframe(
            pivot_display.style.format('{:,.0f}'),
            use_container_width=True,
            height=400
        )
        
        # Download button
        csv = pivot_display.to_csv(encoding='utf-8-sig')
        st.download_button(
            label="📥 CSV 다운로드",
            data=csv,
            file_name="총판비교_과목별_분석.csv",
            mime="text/csv"
        )

st.markdown("---")
st.caption("🔄 총판 비교 분석 페이지")
