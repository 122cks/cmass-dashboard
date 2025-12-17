import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="등급별 분석", page_icon="🏅", layout="wide")

# Get data
if 'order_df' not in st.session_state:
    st.error("데이터를 불러올 수 없습니다. 메인 페이지로 돌아가주세요.")
    st.stop()

order_df = st.session_state['order_df'].copy()
distributor_df = st.session_state.get('distributor_df', pd.DataFrame())
target_df = st.session_state.get('target_df', pd.DataFrame())
sort_by_grade = st.session_state.get('sort_by_grade', None)
total_df = st.session_state.get('total_df', pd.DataFrame())
market_analysis = st.session_state.get('market_analysis', pd.DataFrame())  # 시장 분석 데이터

st.title("🏅 등급별 총판 분석")
st.markdown("---")

# Use existing grade column from order_df
if '총판등급' not in order_df.columns:
    st.warning("총판 등급 정보가 없습니다. 기본 분석만 제공됩니다.")
    order_df['등급'] = '미분류'
else:
    order_df['등급'] = order_df['총판등급'].fillna('미분류')

# Sidebar filters
st.sidebar.header("🔍 필터 옵션")

# Sort grades: S, A, B, C, D, E, G, then others
grade_order = ['S', 'A', 'B', 'C', 'D', 'E', 'G']
all_grades = order_df['등급'].unique().tolist()
available_grades = [g for g in grade_order if g in all_grades]
available_grades += sorted([g for g in all_grades if g not in grade_order and g != '미분류'])
if '미분류' in all_grades:
    available_grades.append('미분류')

selected_grades = st.sidebar.multiselect(
    "등급 선택",
    available_grades,
    default=available_grades if len(available_grades) <= 4 else available_grades[:4]
)

if not selected_grades:
    st.warning("⚠️ 분석할 등급을 선택해주세요.")
    st.stop()

# Filter data
filtered_order = order_df[order_df['등급'].isin(selected_grades)]

st.sidebar.markdown("---")
st.sidebar.info(f"📊 선택된 등급: {len(selected_grades)}개")

# Main metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_orders = filtered_order['부수'].sum()
    st.metric("총 주문 부수", f"{total_orders:,.0f}부")

with col2:
    total_distributors = filtered_order['총판'].nunique()
    st.metric("총판 수", f"{total_distributors}개")

with col3:
    avg_per_dist = total_orders / total_distributors if total_distributors > 0 else 0
    st.metric("총판당 평균", f"{avg_per_dist:,.0f}부")

with col4:
    total_schools = filtered_order['정보공시학교코드'].nunique() if '정보공시학교코드' in filtered_order.columns else filtered_order['학교코드'].nunique()
    st.metric("거래 학교", f"{total_schools:,}개교")

st.markdown("---")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 등급별 현황", "📈 성과 비교", "🗺️ 지역 분포", "📚 과목별 분석"])

with tab1:
    st.subheader("등급별 총판 현황")
    
    # Get total_df for market size calculation
    total_df = st.session_state.get('total_df', pd.DataFrame())
    
    # Calculate statistics by grade with market share
    grade_stats = []
    for grade in selected_grades:
        grade_data = filtered_order[filtered_order['등급'] == grade]
        
        # Calculate school code column
        school_code_col = '정보공시학교코드' if '정보공시학교코드' in grade_data.columns else '학교코드'
        
        # Calculate market size for this grade's schools (담당 학교의 중등/고등 1,2학년 학생수)
        school_codes = grade_data[school_code_col].unique() if school_code_col in grade_data.columns else []
        
        if not total_df.empty and len(school_codes) > 0:
            grade_schools = total_df[total_df['정보공시 학교코드'].isin(pd.Series(school_codes).astype(str))]
            if not grade_schools.empty:
                # Calculate market size based on school level (중등=3, 고등=4)
                # 중등 1,2학년 + 고등 1,2학년 학생수 합계
                market_size = 0
                for _, school in grade_schools.iterrows():
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
            '등급': grade,
            '총판수': grade_data['총판'].nunique(),
            '주문부수': grade_data['부수'].sum(),
            '시장규모': market_size,
            '점유율(%)': (grade_data['부수'].sum() / market_size * 100) if market_size > 0 else 0,
            '주문금액': grade_data['금액'].sum() if '금액' in grade_data.columns else 0,
            '거래학교수': grade_data[school_code_col].nunique() if school_code_col in grade_data.columns else 0,
            '취급과목수': grade_data['과목명'].nunique() if '과목명' in grade_data.columns else grade_data.get('교과서명_구분', grade_data.get('교과서명', pd.Series())).nunique(),
            '총판당평균': 0,
            '학교당평균': 0
        }
        stats['총판당평균'] = stats['주문부수'] / stats['총판수'] if stats['총판수'] > 0 else 0
        stats['학교당평균'] = stats['주문부수'] / stats['거래학교수'] if stats['거래학교수'] > 0 else 0
        
        grade_stats.append(stats)
    
    grade_df = pd.DataFrame(grade_stats)
    
    # Display grade cards with market share
    cols = st.columns(len(selected_grades))
    for idx, (_, row) in enumerate(grade_df.iterrows()):
        with cols[idx]:
            grade_emoji = {'S': '🥇', 'A': '🥈', 'B': '🥉', 'C': '⭐', 'D': '📌', 'E': '🔵', 'G': '⚪', '미분류': '📍'}.get(row['등급'], '📌')
            grade_color = {'S': '#FFD700', 'A': '#C0C0C0', 'B': '#CD7F32', 'C': '#4CAF50', 'D': '#2196F3', 'E': '#9C27B0', 'G': '#607D8B', '미분류': '#9E9E9E'}.get(row['등급'], '#4CAF50')
            
            st.markdown(f"""
            <div style="border: 3px solid {grade_color}; border-radius: 15px; padding: 20px; margin: 10px 0;">
                <h2 style="text-align: center;">{grade_emoji} {row['등급']}</h2>
                <p><b>총판 수:</b> {row['총판수']}개</p>
                <p><b>주문:</b> {row['주문부수']:,.0f}부</p>
                <p><b>점유율:</b> {row['점유율(%)']:.2f}%</p>
                <p><b>시장규모:</b> {row['시장규모']:,.0f}명</p>
                <p><b>학교:</b> {row['거래학교수']}개교</p>
                <p><b>과목:</b> {row['취급과목수']}개</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Comparative charts with market share
    col1, col2 = st.columns(2)
    
    with col1:
        # Bar chart - Market Share by grade
        fig1 = px.bar(
            grade_df,
            x='등급',
            y='점유율(%)',
            title="등급별 시장 점유율",
            text='점유율(%)',
            color='등급',
            color_discrete_map={'S': '#FFD700', 'A': '#C0C0C0', 'B': '#CD7F32', 'C': '#4CAF50', 'D': '#2196F3', '미분류': '#9E9E9E'}
        )
        fig1.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
        fig1.update_layout(yaxis_title="점유율 (%)")
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # Bar chart - Total orders by grade
        fig2 = px.bar(
            grade_df,
            x='등급',
            y='주문부수',
            title="등급별 총 주문 부수",
            text='주문부수',
            color='등급',
            color_discrete_map={'S': '#FFD700', 'A': '#C0C0C0', 'B': '#CD7F32', 'C': '#4CAF50', 'D': '#2196F3', '미분류': '#9E9E9E'}
        )
        fig2.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig2, use_container_width=True)
    
    # Detailed metrics table
    st.markdown("---")
    st.subheader("📋 등급별 상세 지표")
    
    st.dataframe(
        grade_df.style.format({
            '총판수': '{:,.0f}',
            '주문부수': '{:,.0f}',
            '점유율(%)': '{:.2f}',
            '시장규모': '{:,.0f}',
            '주문금액': '{:,.0f}',
            '거래학교수': '{:,.0f}',
            '취급과목수': '{:,.0f}',
            '총판당평균': '{:.1f}',
            '학교당평균': '{:.1f}'
        }),
        use_container_width=True
    )

with tab2:
    st.subheader("📈 등급별 성과 심층 비교")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Average per distributor
        fig = px.bar(
            grade_df,
            x='등급',
            y='총판당평균',
            title="등급별 총판당 평균 주문",
            text='총판당평균',
            color='등급',
            color_discrete_map={'S': '#FFD700', 'A': '#C0C0C0', 'B': '#CD7F32', 'C': '#4CAF50', '미분류': '#9E9E9E'}
        )
        fig.update_traces(texttemplate='%{text:,.1f}', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Average per school
        fig2 = px.bar(
            grade_df,
            x='등급',
            y='학교당평균',
            title="등급별 학교당 평균 주문",
            text='학교당평균',
            color='등급',
            color_discrete_map={'S': '#FFD700', 'A': '#C0C0C0', 'B': '#CD7F32', 'C': '#4CAF50', '미분류': '#9E9E9E'}
        )
        fig2.update_traces(texttemplate='%{text:,.1f}', textposition='outside')
        st.plotly_chart(fig2, use_container_width=True)
    
    # Multi-dimensional comparison
    st.markdown("---")
    st.subheader("🔄 다차원 성과 비교")
    
    # Radar chart
    metrics = ['주문부수', '거래학교수', '취급과목수', '총판당평균', '학교당평균']
    normalized_data = grade_df[metrics].copy()
    for col in metrics:
        max_val = normalized_data[col].max()
        normalized_data[col] = (normalized_data[col] / max_val) * 100 if max_val > 0 else 0
    
    fig_radar = go.Figure()
    color_map = {'S': '#FFD700', 'A': '#C0C0C0', 'B': '#CD7F32', 'C': '#4CAF50', '미분류': '#9E9E9E'}
    
    for idx, row in grade_df.iterrows():
        values = normalized_data.iloc[idx].tolist()  # type: ignore
        values.append(values[0])
        
        fig_radar.add_trace(go.Scatterpolar(
            r=values,
            theta=metrics + [metrics[0]],
            name=row['등급'],
            fill='toself',
            line_color=color_map.get(row['등급'], '#4CAF50')
        ))
    
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        title="등급별 다차원 성과 비교 (정규화)"
    )
    st.plotly_chart(fig_radar, use_container_width=True)
    
    # Individual distributor performance within grades
    st.markdown("---")
    st.subheader("🏢 등급 내 총판별 성과")
    
    selected_grade = st.selectbox("상세 조회할 등급 선택", selected_grades)
    
    school_code_col = '정보공시학교코드' if '정보공시학교코드' in filtered_order.columns else '학교코드'
    
    grade_distributors = filtered_order[filtered_order['등급'] == selected_grade].groupby('총판').agg({
        '부수': 'sum',
        school_code_col: 'nunique',
        '과목명': 'nunique'
    }).reset_index()
    grade_distributors.columns = ['총판', '주문부수', '거래학교수', '취급과목수']
    grade_distributors['학교당평균'] = grade_distributors['주문부수'] / grade_distributors['거래학교수']
    grade_distributors = grade_distributors.sort_values('주문부수', ascending=False)
    
    fig_dist = px.bar(
        grade_distributors,
        x='총판',
        y='주문부수',
        title=f"{selected_grade}등급 총판별 주문량",
        text='주문부수',
        color='주문부수',
        color_continuous_scale='Blues'
    )
    fig_dist.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
    fig_dist.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_dist, use_container_width=True)

with tab3:
    st.subheader("🗺️ 등급별 지역 분포")
    
    if '시도교육청' in filtered_order.columns:
        # Regional distribution by grade
        regional_by_grade = filtered_order.groupby(['등급', '시도교육청'])['부수'].sum().reset_index()
        
        # Grouped bar chart
        fig = px.bar(
            regional_by_grade,
            x='시도교육청',
            y='부수',
            color='등급',
            title="등급별 지역 분포",
            text='부수',
            barmode='group',
            color_discrete_map={'S': '#FFD700', 'A': '#C0C0C0', 'B': '#CD7F32', 'C': '#4CAF50', '미분류': '#9E9E9E'}
        )
        fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig.update_layout(height=500, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
        
        # Stacked percentage view
        st.markdown("---")
        
        pivot_regional = regional_by_grade.pivot(index='시도교육청', columns='등급', values='부수').fillna(0)
        pivot_pct = pivot_regional.div(pivot_regional.sum(axis=1), axis=0) * 100
        
        fig_pct = px.bar(
            pivot_pct.reset_index().melt(id_vars='시도교육청', var_name='등급', value_name='비율'),
            x='시도교육청',
            y='비율',
            color='등급',
            title="지역별 등급 구성비 (%)",
            barmode='stack',
            text='비율',
            color_discrete_map={'S': '#FFD700', 'A': '#C0C0C0', 'B': '#CD7F32', 'C': '#4CAF50', '미분류': '#9E9E9E'}
        )
        fig_pct.update_traces(texttemplate='%{text:.1f}%', textposition='inside')
        fig_pct.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_pct, use_container_width=True)
        
        # Heatmap
        st.markdown("---")
        
        fig_heatmap = px.imshow(
            pivot_regional,
            title="등급 × 지역 주문량 히트맵",
            labels=dict(x="등급", y="지역", color="주문량"),
            aspect="auto",
            color_continuous_scale='YlOrRd'
        )
        fig_heatmap.update_layout(height=600)
        st.plotly_chart(fig_heatmap, use_container_width=True)

with tab4:
    st.subheader("📚 등급별 과목 분석")
    
    # Subject distribution by grade (도서코드 기준)
    book_code_col = '도서코드(교지명구분)' if '도서코드(교지명구분)' in filtered_order.columns else '도서코드'
    subject_col = '교과서명_구분' if '교과서명_구분' in filtered_order.columns else '과목명'
    
    if book_code_col in filtered_order.columns:
        subject_by_grade = filtered_order.groupby(['등급', book_code_col]).agg({
            '부수': 'sum',
            subject_col: 'first'
        }).reset_index()
        subject_by_grade.columns = ['등급', book_code_col, '부수', '과목명']
    else:
        subject_by_grade = filtered_order.groupby(['등급', subject_col])['부수'].sum().reset_index()
        subject_by_grade.columns = ['등급', '과목명', '부수']
    
    # Get top subjects overall
    top_subjects = subject_by_grade.groupby('과목명')['부수'].sum().sort_values(ascending=False).head(15).index
    subject_by_grade_top = subject_by_grade[subject_by_grade['과목명'].isin(top_subjects)]
    
    # Grouped bar chart
    fig = px.bar(
        subject_by_grade_top,
        x='과목명',
        y='부수',
        color='등급',
        title="등급별 주요 과목 판매량 (TOP 15)",
        text='부수',
        barmode='group',
        color_discrete_map={'S': '#FFD700', 'A': '#C0C0C0', 'B': '#CD7F32', 'C': '#4CAF50', '미분류': '#9E9E9E'}
    )
    fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
    fig.update_layout(height=500, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)
    
    # Subject diversity by grade
    st.markdown("---")
    st.subheader("📊 등급별 과목 다양성")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Number of subjects by grade
        fig_diversity = px.bar(
            grade_df,
            x='등급',
            y='취급과목수',
            title="등급별 취급 과목 수",
            text='취급과목수',
            color='등급',
            color_discrete_map={'S': '#FFD700', 'A': '#C0C0C0', 'B': '#CD7F32', 'C': '#4CAF50', '미분류': '#9E9E9E'}
        )
        fig_diversity.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig_diversity, use_container_width=True)
    
    with col2:
        # Top subject for each grade
        st.markdown("#### 등급별 TOP 과목")
        for grade in selected_grades:
            grade_subjects = subject_by_grade[subject_by_grade['등급'] == grade].sort_values('부수', ascending=False)
            if not grade_subjects.empty:
                top_subject = grade_subjects.iloc[0]
                grade_emoji = {'S': '🥇', 'A': '🥈', 'B': '🥉', 'C': '⭐', '미분류': '📍'}.get(grade, '📌')
                st.write(f"{grade_emoji} **{grade}등급**: {top_subject['과목명']} ({top_subject['부수']:,.0f}부)")
    
    # Detailed table
    st.markdown("---")
    st.subheader("📋 등급별 과목 상세")
    
    pivot_subject = subject_by_grade.pivot(index='과목명', columns='등급', values='부수').fillna(0)
    pivot_subject['합계'] = pivot_subject.sum(axis=1)
    pivot_subject = pivot_subject.sort_values('합계', ascending=False).head(20)
    
    st.dataframe(
        pivot_subject.style.format('{:,.0f}'),
        use_container_width=True,
        height=400
    )
    
    # Download button
    csv = pivot_subject.to_csv(encoding='utf-8-sig')
    st.download_button(
        label="📥 CSV 다운로드",
        data=csv,
        file_name="등급별_과목_분석.csv",
        mime="text/csv"
    )

st.markdown("---")
st.caption("🏅 등급별 총판 분석 페이지")
