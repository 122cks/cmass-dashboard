import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Mapping, Any, cast

st.set_page_config(page_title="총판 비교분석", page_icon="🔄", layout="wide")

# Get data
if 'total_df' not in st.session_state or 'order_df' not in st.session_state:
    st.error("데이터를 불러올 수 없습니다. 메인 페이지로 돌아가주세요.")
    st.stop()

total_df = st.session_state['total_df']
order_df = st.session_state['order_df']
target_df = st.session_state.get('target_df', pd.DataFrame())
distributor_df = st.session_state.get('distributor_df', pd.DataFrame())
market_analysis = st.session_state.get('market_analysis', pd.DataFrame())  # 시장 분석 데이터
subject_market_by_dist = st.session_state.get('subject_market_by_dist', pd.DataFrame())  # 총판별 과목 시장

st.title("🔄 총판 비교 분석")
st.markdown("---")

# Modal for detailed comparison
@st.dialog("📊 총판 상세 비교", width="large")
def show_comparison_detail(dist1, dist2):
    """두 총판 상세 비교 모달"""
    st.subheader(f"🔄 {dist1} vs {dist2}")
    
    order_df = st.session_state['order_df']
    dist1_orders = order_df[order_df['총판'] == dist1]
    dist2_orders = order_df[order_df['총판'] == dist2]
    
    # 기본 비교
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"### 📌 {dist1}")
        st.metric("주문 부수", f"{dist1_orders['부수'].sum():,.0f}부")
        school_col = '정보공시학교코드' if '정보공시학교코드' in dist1_orders.columns else '학교코드'
        st.metric("학교 수", f"{dist1_orders[school_col].nunique():,}개")
    
    with col2:
        st.markdown(f"### 📌 {dist2}")
        st.metric("주문 부수", f"{dist2_orders['부수'].sum():,.0f}부")
        st.metric("학교 수", f"{dist2_orders[school_col].nunique():,}개")
    
    st.markdown("---")
    
    # 과목별 비교
    if '과목명' in dist1_orders.columns:
        st.subheader("📚 과목별 비교")
        
        subject1 = dist1_orders.groupby('과목명')['부수'].sum().reset_index()
        subject1.columns = ['과목명', dist1]
        
        subject2 = dist2_orders.groupby('과목명')['부수'].sum().reset_index()
        subject2.columns = ['과목명', dist2]
        
        subject_comp = pd.merge(subject1, subject2, on='과목명', how='outer').fillna(0)
        subject_comp = subject_comp.sort_values(dist1, ascending=False).head(15)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(name=dist1, x=subject_comp['과목명'], y=subject_comp[dist1]))
        fig.add_trace(go.Bar(name=dist2, x=subject_comp['과목명'], y=subject_comp[dist2]))
        fig.update_layout(barmode='group', height=400, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(subject_comp, use_container_width=True)

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
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 종합 비교", "📈 실적 대비", "🗺️ 지역별 분포", "📚 과목별 분석", "⚖️ 점유율 유사 총판", "👥 학생수 유사 총판"])

with tab1:
    st.subheader("총판별 종합 성과 비교")
    
    # Get total_df for market size calculation
    total_df = st.session_state.get('total_df', pd.DataFrame())
    
    # Calculate comprehensive statistics with market share
    comparison_stats = []
    
    # 2026년도 목표과목1, 목표과목2만 필터링 (목표 달성률 계산용, 컬럼명 방어적 처리)
    target_col = None
    if '목표과목' in filtered_order.columns:
        target_col = '목표과목'
    elif '2026 목표과목' in filtered_order.columns:
        target_col = '2026 목표과목'

    if '학년도' in filtered_order.columns and target_col is not None:
        filtered_order_2026 = filtered_order[
            (filtered_order['학년도'] == 2026) & 
            (filtered_order[target_col].isin(['목표과목1', '목표과목2']))
        ]
    else:
        filtered_order_2026 = filtered_order
    
    for dist in selected_distributors:
        # 전체 데이터 (참고용)
        dist_data = filtered_order[filtered_order['총판'] == dist]
        
        # 2026년도 데이터 (달성률 계산용)
        dist_data_2026 = filtered_order_2026[filtered_order_2026['총판'] == dist]
        
        # Determine school code column
        school_code_col = '정보공시학교코드' if '정보공시학교코드' in dist_data.columns else '학교코드'
        subject_col = '교과서명_구분' if '교과서명_구분' in dist_data.columns else '교과서명'
        
        # Calculate market size for this distributor's schools (담당 학교의 중등/고등 1,2학년 학생수)
        school_codes = dist_data[school_code_col].unique() if school_code_col in dist_data.columns else []
        
        if not total_df.empty and len(school_codes) > 0:
            dist_schools = total_df[total_df['정보공시 학교코드'].isin(pd.Series(school_codes).astype(str))]
            if not dist_schools.empty:
                # Calculate market size based on school level (중등=3, 고등=4)
                # 중등 1,2학년 + 고등 1,2학년 학생수 합계
                market_size = 0
                for _, school in dist_schools.iterrows():
                    grade_code = school.get('학교급코드', 0)
                    if grade_code == 3:  # 중학교
                        market_size += school.get('1학년 학생수', 0) + school.get('2학년 학생수', 0)
                    elif grade_code == 4:  # 고등학교
                        market_size += school.get('1학년 학생수', 0) + school.get('2학년 학생수', 0)
            else:
                market_size = 0
        else:
            market_size = 0
        
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
        
        # Get target and grade info from distributor_df (코드 기반 매칭)
        if not distributor_df.empty:
            dist_rows = order_df[order_df['총판'] == dist]
            dist_code = None
            if '총판코드_정규화' in dist_rows.columns and not dist_rows.empty:
                codes = dist_rows['총판코드_정규화'].dropna().astype(str)
                dist_code = codes.mode().iloc[0] if not codes.empty else None
            # distributor_df에서 코드 정규화 후 매칭
            code_col = '총판코드' if '총판코드' in distributor_df.columns else ('숫자코드' if '숫자코드' in distributor_df.columns else None)
            if code_col and dist_code is not None:
                df_tmp = distributor_df.copy()
                try:
                    df_tmp['__code_norm'] = df_tmp[code_col].apply(lambda x: str(int(x)) if isinstance(x, (int,float)) and not pd.isna(x) and float(x).is_integer() else str(x).strip() if pd.notna(x) else '')
                except Exception:
                    df_tmp['__code_norm'] = df_tmp[code_col].astype(str).str.strip()
                dist_info = df_tmp[df_tmp['__code_norm'] == dist_code]
                if not dist_info.empty:
                    stats['등급'] = dist_info.iloc[0].get('등급', '-')
                else:
                    stats['등급'] = '-'
            else:
                stats['등급'] = '-'
        else:
            stats['등급'] = '-'
        
        # Get target from target_df and calculate achievement by target subject
        if not target_df.empty:
            # 코드 기준 매칭
            dist_rows = order_df[order_df['총판'] == dist]
            dist_code = None
            if '총판코드_정규화' in dist_rows.columns and not dist_rows.empty:
                codes = dist_rows['총판코드_정규화'].dropna().astype(str)
                dist_code = codes.mode().iloc[0] if not codes.empty else None
            code_col = '총판코드' if '총판코드' in target_df.columns else None
            if code_col and dist_code is not None:
                tmp = target_df.copy()
                try:
                    tmp['__code_norm'] = tmp[code_col].apply(lambda x: str(int(x)) if isinstance(x, (int,float)) and not pd.isna(x) and float(x).is_integer() else str(x).strip() if pd.notna(x) else '')
                except Exception:
                    tmp['__code_norm'] = tmp[code_col].astype(str).str.strip()
                target_info = tmp[tmp['__code_norm'] == dist_code]
            else:
                target_info = pd.DataFrame()
            
            if not target_info.empty:
                target_row = target_info.iloc[0]
                
                # 목표과목1 부수
                target1_str = str(target_row.get('목표과목1 부수', '0'))
                target1 = pd.to_numeric(target1_str.replace(',', '').strip(), errors='coerce')
                if pd.isna(target1):
                    target1 = 0
                
                # 목표과목2 부수
                target2_str = str(target_row.get('목표과목2 부수', '0'))
                target2 = pd.to_numeric(target2_str.replace(',', '').strip(), errors='coerce')
                if pd.isna(target2):
                    target2 = 0
                
                # 전체 목표 = 목표과목1 + 목표과목2
                stats['목표부수'] = target1 + target2
                
                # Calculate actual orders by target subject (목표과목1, 목표과목2) - 2026년도만
                if '2026 목표과목' in dist_data_2026.columns:
                    # 목표과목1 달성률 (2026년도)
                    subject1_orders = dist_data_2026[dist_data_2026['2026 목표과목'] == '목표과목1']['부수'].sum()
                    stats['목표과목1_주문'] = subject1_orders
                    stats['목표과목1_목표'] = target1
                    stats['목표과목1_달성률'] = (subject1_orders / target1 * 100) if target1 > 0 else 0
                    
                    # 목표과목2 달성률 (2026년도)
                    subject2_orders = dist_data_2026[dist_data_2026['2026 목표과목'] == '목표과목2']['부수'].sum()
                    stats['목표과목2_주문'] = subject2_orders
                    stats['목표과목2_목표'] = target2
                    stats['목표과목2_달성률'] = (subject2_orders / target2 * 100) if target2 > 0 else 0
                    
                    # 전체 실적 (2026년도)
                    stats['실적2026'] = subject1_orders + subject2_orders
                else:
                    stats['목표과목1_주문'] = 0
                    stats['목표과목1_목표'] = target1
                    stats['목표과목1_달성률'] = 0
                    stats['목표과목2_주문'] = 0
                    stats['목표과목2_목표'] = target2
                    stats['목표과목2_달성률'] = 0
                    stats['실적2026'] = dist_data_2026['부수'].sum()
                
                # 전체 목표달성률 (2026년도 실적 사용)
                if stats['목표부수'] > 0:
                    stats['목표달성률'] = (stats['실적2026'] / stats['목표부수']) * 100
                else:
                    stats['목표달성률'] = 0
            else:
                stats['목표부수'] = 0
                stats['목표달성률'] = 0
                stats['목표과목1_주문'] = 0
                stats['목표과목1_목표'] = 0
                stats['목표과목1_달성률'] = 0
                stats['목표과목2_주문'] = 0
                stats['목표과목2_목표'] = 0
                stats['목표과목2_달성률'] = 0
        else:
            stats['목표부수'] = 0
            stats['목표달성률'] = 0
            stats['목표과목1_주문'] = 0
            stats['목표과목1_목표'] = 0
            stats['목표과목1_달성률'] = 0
            stats['목표과목2_주문'] = 0
            stats['목표과목2_목표'] = 0
            stats['목표과목2_달성률'] = 0
        
        comparison_stats.append(stats)
    
    comparison_df = pd.DataFrame(comparison_stats)
    
    # Display metrics cards with market share
    cols = st.columns(len(selected_distributors))
    for idx, (_, row) in enumerate(comparison_df.iterrows()):
        with cols[idx]:
            grade_color = {'S': '🥇', 'A': '🥈', 'B': '🥉', 'C': '⭐'}.get(row['등급'], '📍')
            
            # 목표달성률 표시 (색상)
            achievement_color = '#4CAF50' if row.get('목표달성률', 0) >= 100 else '#FF9800' if row.get('목표달성률', 0) >= 80 else '#F44336'
            
            st.markdown(f"""
            <div style="border: 2px solid {achievement_color}; border-radius: 10px; padding: 15px; margin: 5px;">
                <h4>{grade_color} {row['총판']}</h4>
                <p><b>등급:</b> {row['등급']}</p>
                <p><b>주문:</b> {row['주문부수']:,.0f}부</p>
                <p><b>점유율:</b> {row['점유율(%)']:.2f}%</p>
                <p><b>시장규모:</b> {row['시장규모']:,.0f}명</p>
                <p><b>학교:</b> {row['거래학교수']}개교</p>
                <hr>
                {f"<p><b>전체 목표달성:</b> {row['목표달성률']:.1f}%</p>" if row['목표달성률'] > 0 else ""}
                {f"<p style='font-size:0.9em;'><b>목표1:</b> {row['목표과목1_주문']:,.0f}/{row['목표과목1_목표']:,.0f}부 ({row['목표과목1_달성률']:.1f}%)</p>" if row.get('목표과목1_목표', 0) > 0 else ""}
                {f"<p style='font-size:0.9em;'><b>목표2:</b> {row['목표과목2_주문']:,.0f}/{row['목표과목2_목표']:,.0f}부 ({row['목표과목2_달성률']:.1f}%)</p>" if row.get('목표과목2_목표', 0) > 0 else ""}
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
        # Calculate relative share (전체 대비 상대적 비중)
        comparison_df['상대비중(%)'] = (comparison_df['주문부수'] / comparison_df['주문부수'].sum()) * 100
        
        # Percentage composition
        fig2 = go.Figure()
        fig2.add_trace(go.Pie(
            labels=comparison_df['총판'],
            values=comparison_df['상대비중(%)'],
            text=comparison_df['상대비중(%)'].apply(lambda x: f'{x:.1f}%'),
            textposition='inside',
            hole=0.3
        ))
        fig2.update_layout(
            title="총판별 상대적 주문 비중 (%)",
            showlegend=True
        )
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
            values = normalized_data.iloc[idx].tolist()  # type: ignore
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
    st.subheader("📈 총판 간 목표 달성률 비교")
    
    if not target_df.empty:
        # Goal achievement comparison
        goal_data = comparison_df[comparison_df['목표부수'] > 0].copy()
        
        if not goal_data.empty:
            st.info("💡 선택한 총판들의 목표 대비 달성률을 비교합니다. (목표과목1 + 목표과목2 = 전체 목표)")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # 전체 목표 달성률 비교
                fig_achievement = px.bar(
                    goal_data,
                    x='총판',
                    y='목표달성률',
                    title="총판별 전체 목표 달성률 비교",
                    text='목표달성률',
                    color='목표달성률',
                    color_continuous_scale='RdYlGn',
                    range_color=[0, 200]
                )
                fig_achievement.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig_achievement.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="목표선 (100%)")
                fig_achievement.update_layout(xaxis_tickangle=-45, height=500, yaxis_title="달성률 (%)")
                st.plotly_chart(fig_achievement, use_container_width=True)
            
            with col2:
                # 목표 vs 실적 비교
                fig_target = go.Figure()
                
                fig_target.add_trace(go.Bar(
                    name='목표',
                    x=goal_data['총판'],
                    y=goal_data['목표부수'],
                    marker_color='lightblue',
                    text=goal_data['목표부수'],
                    texttemplate='%{text:,.0f}',
                    textposition='outside'
                ))
                
                fig_target.add_trace(go.Bar(
                    name='실적',
                    x=goal_data['총판'],
                    y=goal_data['주문부수'],
                    marker_color='darkblue',
                    text=goal_data['주문부수'],
                    texttemplate='%{text:,.0f}',
                    textposition='outside'
                ))
                
                fig_target.update_layout(
                    title="목표 vs 실적 비교",
                    barmode='group',
                    xaxis_tickangle=-45,
                    height=500,
                    yaxis_title="부수"
                )
                st.plotly_chart(fig_target, use_container_width=True)
            
            # 목표과목별 달성률 비교
            st.markdown("---")
            st.subheader("📚 목표과목별 달성률 상세 비교")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # 목표과목1 달성률
                goal_subject1 = goal_data[goal_data['목표과목1_목표'] > 0]
                if len(goal_subject1) > 0:
                    fig1 = px.bar(
                        goal_subject1,
                        x='총판',
                        y='목표과목1_달성률',
                        title="목표과목1 달성률 비교",
                        text='목표과목1_달성률',
                        color='목표과목1_달성률',
                        color_continuous_scale='Blues'
                    )
                    fig1.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                    fig1.add_hline(y=100, line_dash="dash", line_color="red")
                    fig1.update_layout(xaxis_tickangle=-45, yaxis_title="달성률 (%)")
                    st.plotly_chart(fig1, use_container_width=True)
                else:
                    st.info("목표과목1 데이터가 없습니다.")
            
            with col2:
                # 목표과목2 달성률
                goal_subject2 = goal_data[goal_data['목표과목2_목표'] > 0]
                if len(goal_subject2) > 0:
                    fig2 = px.bar(
                        goal_subject2,
                        x='총판',
                        y='목표과목2_달성률',
                        title="목표과목2 달성률 비교",
                        text='목표과목2_달성률',
                        color='목표과목2_달성률',
                        color_continuous_scale='Greens'
                    )
                    fig2.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                    fig2.add_hline(y=100, line_dash="dash", line_color="red")
                    fig2.update_layout(xaxis_tickangle=-45, yaxis_title="달성률 (%)")
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info("목표과목2 데이터가 없습니다.")
            
            # 달성률 상세 테이블
            st.markdown("---")
            st.subheader("📊 달성률 상세 데이터")
            
            detail_cols = ['총판', '등급', '목표부수', '주문부수', '목표달성률']
            if goal_data['목표과목1_목표'].sum() > 0:
                detail_cols.extend(['목표과목1_목표', '목표과목1_주문', '목표과목1_달성률'])
            if goal_data['목표과목2_목표'].sum() > 0:
                detail_cols.extend(['목표과목2_목표', '목표과목2_주문', '목표과목2_달성률'])
            
            format_dict = {
                '목표부수': '{:,.0f}',
                '주문부수': '{:,.0f}',
                '목표달성률': '{:.1f}',
                '목표과목1_목표': '{:,.0f}',
                '목표과목1_주문': '{:,.0f}',
                '목표과목1_달성률': '{:.1f}',
                '목표과목2_목표': '{:,.0f}',
                '목표과목2_주문': '{:,.0f}',
                '목표과목2_달성률': '{:.1f}'
            }
            
            # Format using compatible method
            formatted_df = goal_data[detail_cols].copy()
            st.dataframe(
                formatted_df.style.format(cast(Mapping[str, Any], format_dict), na_rep='-')  # type: ignore[arg-type]
                .background_gradient(
                    subset=['목표달성률'], cmap='RdYlGn', vmin=0, vmax=200
                ),
                use_container_width=True
            )
        else:
            st.warning("선택한 총판 중 목표 데이터가 있는 총판이 없습니다.")
    else:
        st.warning("목표 데이터가 없습니다.")

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
    
    # Subject distribution for each distributor (도서코드 기준)
    subject_comparison = []
    for dist in selected_distributors:
        dist_orders = filtered_order[filtered_order['총판'] == dist]
        
        book_code_col = '도서코드(교지명구분)' if '도서코드(교지명구분)' in dist_orders.columns else '도서코드'
        subject_col = '교과서명_구분' if '교과서명_구분' in dist_orders.columns else '과목명'
        
        if book_code_col in dist_orders.columns:
            subject = dist_orders.groupby(book_code_col).agg({
                '부수': 'sum',
                subject_col: 'first'
            }).reset_index()
            subject.columns = [book_code_col, '부수', '과목명']
        else:
            subject = dist_orders.groupby(subject_col)['부수'].sum().reset_index()
            subject.columns = ['과목명', '부수']
        
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
        
        # 중복 제거 후 pivot (과목명 + 총판 조합이 중복되면 합산)
        subject_df_agg = subject_df_top.groupby(['과목명', '총판'])['부수'].sum().reset_index()
        pivot_subject = subject_df_agg.pivot(index='과목명', columns='총판', values='부수').fillna(0)
        
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
        
        # 중복 제거 후 pivot
        subject_df_agg = subject_df.groupby(['과목명', '총판'])['부수'].sum().reset_index()
        pivot_display = subject_df_agg.pivot(index='과목명', columns='총판', values='부수').fillna(0)
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

with tab5:
    st.subheader("⚖️ 점유율이 유사한 총판 분석")
    
    # Get all distributor stats with market share
    distributor_market = st.session_state.get('distributor_market', pd.DataFrame())
    
    if not distributor_market.empty and '점유율(%)' in distributor_market.columns:
        # Select a reference distributor from selected ones
        ref_dist = st.selectbox("기준 총판 선택", selected_distributors, key="ref_share")
        
        # Get reference market share
        ref_row = comparison_df[comparison_df['총판'] == ref_dist]
        if not ref_row.empty:
            ref_share = ref_row.iloc[0]['점유율(%)']
            
            # Find similar distributors (within ±20% range)
            all_dist_stats = []
            for dist in order_df['총판'].unique():
                dist_data = order_df[order_df['총판'] == dist]
                school_code_col = '정보공시학교코드' if '정보공시학교코드' in dist_data.columns else '학교코드'
                
                # Get market size from distributor_market
                # 코드 기반으로 distributor_market 매칭 (세션의 code_to_official 사용)
                dist_rows2 = order_df[order_df['총판'] == dist]
                dist_code2 = None
                if '총판코드_정규화' in dist_rows2.columns and not dist_rows2.empty:
                    codes2 = dist_rows2['총판코드_정규화'].dropna().astype(str)
                    dist_code2 = codes2.mode().iloc[0] if not codes2.empty else None
                official = st.session_state.get('code_to_official', {}).get(dist_code2)
                if official:
                    dist_market_row = distributor_market[distributor_market['총판명(공식)'] == official]
                else:
                    dist_market_row = pd.DataFrame()
                if not dist_market_row.empty:
                    market_size = dist_market_row.iloc[0]['시장규모']
                else:
                    market_size = 0
                
                orders = dist_data['부수'].sum()
                share = (orders / market_size * 100) if market_size > 0 else 0
                
                all_dist_stats.append({
                    '총판': dist,
                    '주문부수': orders,
                    '시장규모': market_size,
                    '점유율(%)': share,
                    '거래학교수': dist_data[school_code_col].nunique() if school_code_col in dist_data.columns else 0
                })
            
            all_dist_df = pd.DataFrame(all_dist_stats)
            
            # Filter similar (within ±2% range)
            similar_range = 2.0
            similar_dists = all_dist_df[
                (all_dist_df['점유율(%)'] >= ref_share - similar_range) & 
                (all_dist_df['점유율(%)'] <= ref_share + similar_range) &
                (all_dist_df['총판'] != ref_dist)
            ].sort_values('점유율(%)', ascending=False).head(10)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("기준 총판", ref_dist)
            with col2:
                st.metric("기준 점유율", f"{ref_share:.2f}%")
            with col3:
                st.metric("유사 총판 수", f"{len(similar_dists)}개")
            
            st.markdown("---")
            
            if not similar_dists.empty:
                # Comparison chart
                compare_df = pd.concat([
                    ref_row[['총판', '주문부수', '점유율(%)', '거래학교수']],
                    similar_dists[['총판', '주문부수', '점유율(%)', '거래학교수']]
                ]).head(11)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig1 = px.bar(
                        compare_df,
                        x='총판',
                        y='점유율(%)',
                        title=f"점유율 비교 (기준: {ref_dist})",
                        text='점유율(%)',
                        color='점유율(%)',
                        color_continuous_scale='Blues'
                    )
                    fig1.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
                    fig1.update_layout(xaxis_tickangle=-45, showlegend=False)
                    fig1.add_hline(y=ref_share, line_dash="dash", line_color="red", 
                                  annotation_text=f"{ref_dist} 기준")
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    fig2 = px.scatter(
                        compare_df,
                        x='거래학교수',
                        y='주문부수',
                        size='점유율(%)',
                        color='점유율(%)',
                        hover_name='총판',
                        title="학교수 vs 주문부수 (크기=점유율)",
                        labels={'거래학교수': '거래 학교 수', '주문부수': '주문 부수'}
                    )
                    st.plotly_chart(fig2, use_container_width=True)
                
                st.markdown("---")
                st.subheader("📊 유사 총판 상세 비교")
                
                st.dataframe(
                    compare_df.style.format({
                        '주문부수': '{:,.0f}',
                        '시장규모': '{:,.0f}',
                        '점유율(%)': '{:.2f}',
                        '거래학교수': '{:,.0f}'
                    }).background_gradient(subset=['점유율(%)'], cmap='RdYlGn'),
                    use_container_width=True
                )
                
                st.info(f"💡 **분석 인사이트**: 점유율이 유사한 총판들을 비교하여 효율성과 전략을 벤치마킹할 수 있습니다.")
            else:
                st.warning(f"⚠️ {ref_dist}와 점유율이 유사한 총판이 없습니다. (±{similar_range}% 범위)")
    else:
        st.warning("⚠️ 점유율 데이터가 없습니다. 시장규모 정보를 확인해주세요.")

with tab6:
    st.subheader("👥 학생수(시장규모)가 유사한 총판 분석")
    
    distributor_market = st.session_state.get('distributor_market', pd.DataFrame())
    
    if not distributor_market.empty and '시장규모' in distributor_market.columns:
        # Select a reference distributor
        ref_dist2 = st.selectbox("기준 총판 선택", selected_distributors, key="ref_market")
        
        # Get reference market size
        ref_row2 = comparison_df[comparison_df['총판'] == ref_dist2]
        if not ref_row2.empty:
            ref_market = ref_row2.iloc[0]['시장규모']
            
            # Find similar distributors by market size (within ±20%)
            all_dist_stats2 = []
            for dist in order_df['총판'].unique():
                dist_data = order_df[order_df['총판'] == dist]
                school_code_col = '정보공시학교코드' if '정보공시학교코드' in dist_data.columns else '학교코드'
                
                # Get market size
                dist_rows3 = order_df[order_df['총판'] == dist]
                dist_code3 = None
                if '총판코드_정규화' in dist_rows3.columns and not dist_rows3.empty:
                    codes3 = dist_rows3['총판코드_정규화'].dropna().astype(str)
                    dist_code3 = codes3.mode().iloc[0] if not codes3.empty else None
                official = st.session_state.get('code_to_official', {}).get(dist_code3)
                if official:
                    dist_market_row = distributor_market[distributor_market['총판명(공식)'] == official]
                else:
                    dist_market_row = pd.DataFrame()
                if not dist_market_row.empty:
                    market_size = dist_market_row.iloc[0]['시장규모']
                else:
                    market_size = 0
                
                orders = dist_data['부수'].sum()
                share = (orders / market_size * 100) if market_size > 0 else 0
                
                all_dist_stats2.append({
                    '총판': dist,
                    '주문부수': orders,
                    '시장규모': market_size,
                    '점유율(%)': share,
                    '거래학교수': dist_data[school_code_col].nunique() if school_code_col in dist_data.columns else 0
                })
            
            all_dist_df2 = pd.DataFrame(all_dist_stats2)
            
            # Filter similar market size (within ±20%)
            similar_market = all_dist_df2[
                (all_dist_df2['시장규모'] >= ref_market * 0.8) & 
                (all_dist_df2['시장규모'] <= ref_market * 1.2) &
                (all_dist_df2['총판'] != ref_dist2) &
                (all_dist_df2['시장규모'] > 0)
            ].sort_values('시장규모', ascending=False).head(10)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("기준 총판", ref_dist2)
            with col2:
                st.metric("기준 시장규모", f"{ref_market:,.0f}명")
            with col3:
                st.metric("유사 총판 수", f"{len(similar_market)}개")
            
            st.markdown("---")
            
            if not similar_market.empty:
                # Comparison
                compare_df2 = pd.concat([
                    ref_row2[['총판', '주문부수', '시장규모', '점유율(%)', '거래학교수']],
                    similar_market[['총판', '주문부수', '시장규모', '점유율(%)', '거래학교수']]
                ]).head(11)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig1 = px.bar(
                        compare_df2,
                        x='총판',
                        y='시장규모',
                        title=f"시장규모 비교 (기준: {ref_dist2})",
                        text='시장규모',
                        color='시장규모',
                        color_continuous_scale='Greens'
                    )
                    fig1.update_traces(texttemplate='%{text:,.0f}명', textposition='outside')
                    fig1.update_layout(xaxis_tickangle=-45, showlegend=False)
                    fig1.add_hline(y=ref_market, line_dash="dash", line_color="red",
                                  annotation_text=f"{ref_dist2} 기준")
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    # Market size가 비슷한 경우, 점유율 차이가 핵심 지표
                    fig2 = px.bar(
                        compare_df2.sort_values('점유율(%)', ascending=False),
                        x='총판',
                        y='점유율(%)',
                        title="유사 시장규모 총판의 점유율 비교",
                        text='점유율(%)',
                        color='점유율(%)',
                        color_continuous_scale='RdYlGn'
                    )
                    fig2.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
                    fig2.update_layout(xaxis_tickangle=-45, showlegend=False)
                    st.plotly_chart(fig2, use_container_width=True)
                
                st.markdown("---")
                st.subheader("📊 시장규모 유사 총판 상세 비교")
                
                # Add efficiency metric
                compare_df2['학교당평균'] = compare_df2['주문부수'] / compare_df2['거래학교수']
                
                st.dataframe(
                    compare_df2[['총판', '시장규모', '주문부수', '점유율(%)', '거래학교수', '학교당평균']].style.format({
                        '시장규모': '{:,.0f}',
                        '주문부수': '{:,.0f}',
                        '점유율(%)': '{:.2f}',
                        '거래학교수': '{:,.0f}',
                        '학교당평균': '{:.1f}'
                    }).background_gradient(subset=['점유율(%)'], cmap='RdYlGn'),
                    use_container_width=True
                )
                
                st.success(f"💡 **분석 인사이트**: 시장규모가 비슷한 총판 간 점유율 차이는 영업 효율성과 전략의 차이를 나타냅니다.")
                
                # Performance gap analysis
                if len(compare_df2) > 1:
                    max_share = compare_df2['점유율(%)'].max()
                    min_share = compare_df2['점유율(%)'].min()
                    gap = max_share - min_share
                    
                    st.info(f"📈 **점유율 격차**: 최고 {max_share:.2f}% vs 최저 {min_share:.2f}% = {gap:.2f}%p 차이")
            else:
                st.warning(f"⚠️ {ref_dist2}와 시장규모가 유사한 총판이 없습니다. (±20% 범위)")
    else:
        st.warning("⚠️ 시장규모 데이터가 없습니다.")

st.markdown("---")
st.caption("🔄 총판 비교 분석 페이지")
