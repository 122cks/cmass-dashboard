import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="목표 대비 달성률", page_icon="🎯", layout="wide")

# Get data
if 'order_df' not in st.session_state:
    st.error("데이터를 불러올 수 없습니다. 메인 페이지로 돌아가주세요.")
    st.stop()

order_df = st.session_state['order_df'].copy()
target_df = st.session_state.get('target_df', pd.DataFrame())
distributor_df = st.session_state.get('distributor_df', pd.DataFrame())

st.title("🎯 목표 대비 달성률 분석")
st.markdown("---")

# Check if target data exists
if target_df.empty or '총판명(공식)' not in target_df.columns:
    st.warning("⚠️ 목표 데이터가 없습니다. 메인 페이지에서 데이터를 확인해주세요.")
    st.stop()

# 목표 데이터 전처리
target_summary = target_df.copy()

# 쉼표 제거 및 숫자 변환
for col in ['목표과목1 부수', '목표과목2 부수', '전체목표 부수']:
    if col in target_summary.columns:
        target_summary[col] = target_summary[col].astype(str).str.replace(',', '').str.replace(' ', '')
        target_summary[col] = pd.to_numeric(target_summary[col], errors='coerce').fillna(0)

# 전체 목표 = 목표1 + 목표2
if '목표과목1 부수' in target_summary.columns and '목표과목2 부수' in target_summary.columns:
    target_summary['목표1'] = target_summary['목표과목1 부수']
    target_summary['목표2'] = target_summary['목표과목2 부수']
    target_summary['전체목표'] = target_summary['목표1'] + target_summary['목표2']
else:
    target_summary['전체목표'] = target_summary.get('전체목표 부수', 0)
    target_summary['목표1'] = target_summary['전체목표'] * 0.5
    target_summary['목표2'] = target_summary['전체목표'] * 0.5

# 총판별 실적 집계
school_code_col = '정보공시학교코드' if '정보공시학교코드' in order_df.columns else '학교코드'

actual_stats = order_df.groupby('총판').agg({
    '부수': 'sum',
    school_code_col: 'nunique',
    '금액': 'sum' if '금액' in order_df.columns else 'count'
}).reset_index()
actual_stats.columns = ['총판', '실적부수', '거래학교수', '주문금액']

# 목표와 실적 병합
target_map = target_summary.groupby('총판명(공식)').agg({
    '전체목표': 'sum',
    '목표1': 'sum',
    '목표2': 'sum'
}).reset_index()

achievement_df = pd.merge(
    target_map,
    actual_stats,
    left_on='총판명(공식)',
    right_on='총판',
    how='outer'
).fillna(0)

# 총판명 통일
achievement_df['총판'] = achievement_df['총판명(공식)'].fillna(achievement_df['총판'])

# 달성률 계산
achievement_df['전체달성률(%)'] = (achievement_df['실적부수'] / achievement_df['전체목표'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
achievement_df['목표1달성률(%)'] = (achievement_df['실적부수'] / achievement_df['목표1'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
achievement_df['목표2달성률(%)'] = (achievement_df['실적부수'] / achievement_df['목표2'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
achievement_df['차이'] = achievement_df['실적부수'] - achievement_df['전체목표']

# 등급 정보 추가
if not distributor_df.empty and '총판명(공식)' in distributor_df.columns and '등급' in distributor_df.columns:
    grade_map = distributor_df.set_index('총판명(공식)')['등급'].to_dict()
    achievement_df['등급'] = achievement_df['총판'].map(grade_map).fillna('미분류')
else:
    achievement_df['등급'] = '미분류'

# 목표가 있는 총판만 필터링
achievement_df = achievement_df[achievement_df['전체목표'] > 0]

# Sidebar Filters
st.sidebar.header("🔍 필터 옵션")

# Grade Filter
if '등급' in achievement_df.columns:
    grade_order = ['S', 'A', 'B', 'C', 'D', 'E', 'G', '미분류']
    available_grades = [g for g in grade_order if g in achievement_df['등급'].unique()]
    selected_grades = st.sidebar.multiselect(
        "등급 선택",
        available_grades,
        default=available_grades
    )
    if selected_grades:
        achievement_df = achievement_df[achievement_df['등급'].isin(selected_grades)]

# Achievement Filter
achievement_filter = st.sidebar.radio(
    "달성률 필터",
    ["전체", "달성 (≥100%)", "미달성 (<100%)", "우수 (≥120%)", "부진 (<80%)"]
)

if achievement_filter == "달성 (≥100%)":
    achievement_df = achievement_df[achievement_df['전체달성률(%)'] >= 100]
elif achievement_filter == "미달성 (<100%)":
    achievement_df = achievement_df[achievement_df['전체달성률(%)'] < 100]
elif achievement_filter == "우수 (≥120%)":
    achievement_df = achievement_df[achievement_df['전체달성률(%)'] >= 120]
elif achievement_filter == "부진 (<80%)":
    achievement_df = achievement_df[achievement_df['전체달성률(%)'] < 80]

achievement_df = achievement_df.sort_values('전체달성률(%)', ascending=False)

st.sidebar.markdown("---")
st.sidebar.info(f"📊 분석 대상 총판: {len(achievement_df)}개")

# Main Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_target = achievement_df['전체목표'].sum()
    st.metric("전체 목표", f"{total_target:,.0f}부")

with col2:
    total_actual = achievement_df['실적부수'].sum()
    st.metric("전체 실적", f"{total_actual:,.0f}부")

with col3:
    overall_rate = (total_actual / total_target * 100) if total_target > 0 else 0
    st.metric("전체 달성률", f"{overall_rate:.1f}%", 
             delta=f"{total_actual - total_target:,.0f}부")

with col4:
    achieved_count = len(achievement_df[achievement_df['전체달성률(%)'] >= 100])
    st.metric("목표 달성 총판", f"{achieved_count}/{len(achievement_df)}개")

st.markdown("---")

# Tab Layout
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 전체 현황", "🏆 TOP/BOTTOM", "📈 등급별 분석", "📋 상세 테이블", "📉 갭 분석"])

with tab1:
    st.subheader("📊 목표 대비 달성률 전체 현황")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 목표 vs 실적 비교 차트
        fig1 = go.Figure()
        
        top_20 = achievement_df.head(20)
        
        fig1.add_trace(go.Bar(
            name='목표',
            x=top_20['총판'],
            y=top_20['전체목표'],
            marker_color='lightblue',
            text=top_20['전체목표'],
            texttemplate='%{text:,.0f}',
            textposition='outside'
        ))
        
        fig1.add_trace(go.Bar(
            name='실적',
            x=top_20['총판'],
            y=top_20['실적부수'],
            marker_color='green',
            text=top_20['실적부수'],
            texttemplate='%{text:,.0f}',
            textposition='outside'
        ))
        
        fig1.update_layout(
            title="목표 vs 실적 비교 TOP 20",
            barmode='group',
            xaxis_tickangle=-45,
            height=500
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # 달성률 차트
        fig2 = px.bar(
            achievement_df.head(20),
            x='총판',
            y='전체달성률(%)',
            title="목표 달성률 TOP 20",
            text='전체달성률(%)',
            color='전체달성률(%)',
            color_continuous_scale='RdYlGn'
        )
        fig2.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig2.update_layout(xaxis_tickangle=-45, height=500)
        fig2.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="목표선")
        st.plotly_chart(fig2, use_container_width=True)
    
    # 달성률 분포
    st.markdown("---")
    st.subheader("📊 달성률 분포")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 히스토그램
        fig_hist = px.histogram(
            achievement_df,
            x='전체달성률(%)',
            nbins=20,
            title="달성률 분포",
            labels={'전체달성률(%)': '달성률 (%)', 'count': '총판 수'}
        )
        fig_hist.add_vline(x=100, line_dash="dash", line_color="red", annotation_text="목표선")
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
        # 달성률 구간별 총판 수
        achievement_df['달성구간'] = pd.cut(
            achievement_df['전체달성률(%)'],
            bins=[0, 50, 80, 100, 120, float('inf')],
            labels=['50% 미만', '50-80%', '80-100%', '100-120%', '120% 이상']
        )
        
        interval_dist = achievement_df['달성구간'].value_counts().reset_index()
        interval_dist.columns = ['달성구간', '총판수']
        
        fig_pie = px.pie(
            interval_dist,
            values='총판수',
            names='달성구간',
            title="달성률 구간별 총판 분포",
            color_discrete_sequence=px.colors.sequential.RdYlGn
        )
        st.plotly_chart(fig_pie, use_container_width=True)

with tab2:
    st.subheader("🏆 TOP/BOTTOM 달성 총판")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🥇 TOP 10 (달성률 기준)")
        top10 = achievement_df.head(10)
        
        for idx, row in top10.iterrows():
            rank = top10.index.tolist().index(idx) + 1
            emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "⭐"
            
            st.markdown(f"""
            <div style="border: 2px solid #4CAF50; border-radius: 10px; padding: 15px; margin: 10px 0;">
                <h4>{emoji} #{rank} {row['총판']} ({row['등급']}등급)</h4>
                <p><b>달성률:</b> {row['전체달성률(%)']:.1f}%</p>
                <p><b>목표:</b> {row['전체목표']:,.0f}부 → <b>실적:</b> {row['실적부수']:,.0f}부</p>
                <p><b>초과:</b> <span style="color: green;">{row['차이']:,.0f}부</span></p>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 📉 BOTTOM 10 (달성률 기준)")
        bottom10 = achievement_df.tail(10).iloc[::-1]
        
        for idx, row in bottom10.iterrows():
            rank = len(achievement_df) - achievement_df.index.tolist().index(idx)
            
            st.markdown(f"""
            <div style="border: 2px solid #E94B3C; border-radius: 10px; padding: 15px; margin: 10px 0;">
                <h4>#{rank} {row['총판']} ({row['등급']}등급)</h4>
                <p><b>달성률:</b> {row['전체달성률(%)']:.1f}%</p>
                <p><b>목표:</b> {row['전체목표']:,.0f}부 → <b>실적:</b> {row['실적부수']:,.0f}부</p>
                <p><b>부족:</b> <span style="color: red;">{row['차이']:,.0f}부</span></p>
            </div>
            """, unsafe_allow_html=True)

with tab3:
    st.subheader("📈 등급별 달성률 분석")
    
    # 등급별 집계
    grade_achievement = achievement_df.groupby('등급').agg({
        '전체목표': 'sum',
        '실적부수': 'sum',
        '총판': 'count'
    }).reset_index()
    grade_achievement.columns = ['등급', '목표합계', '실적합계', '총판수']
    grade_achievement['평균달성률(%)'] = (grade_achievement['실적합계'] / grade_achievement['목표합계'] * 100).fillna(0)
    
    # 등급 순서 정렬
    grade_order = ['S', 'A', 'B', 'C', 'D', 'E', 'G', '미분류']
    grade_achievement['등급_order'] = grade_achievement['등급'].apply(lambda x: grade_order.index(x) if x in grade_order else 99)
    grade_achievement = grade_achievement.sort_values('등급_order')
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 등급별 평균 달성률
        fig = px.bar(
            grade_achievement,
            x='등급',
            y='평균달성률(%)',
            title="등급별 평균 달성률",
            text='평균달성률(%)',
            color='등급',
            color_discrete_map={'S': '#FFD700', 'A': '#C0C0C0', 'B': '#CD7F32', 'C': '#4CAF50', 'D': '#2196F3', '미분류': '#9E9E9E'}
        )
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="목표선")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # 등급별 목표/실적 비교
        fig2 = go.Figure()
        
        fig2.add_trace(go.Bar(
            name='목표',
            x=grade_achievement['등급'],
            y=grade_achievement['목표합계'],
            marker_color='lightblue'
        ))
        
        fig2.add_trace(go.Bar(
            name='실적',
            x=grade_achievement['등급'],
            y=grade_achievement['실적합계'],
            marker_color='green'
        ))
        
        fig2.update_layout(
            title="등급별 목표 vs 실적",
            barmode='group'
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    # 등급별 상세 테이블
    st.dataframe(
        grade_achievement[['등급', '총판수', '목표합계', '실적합계', '평균달성률(%)']].style.format({
            '총판수': '{:,.0f}',
            '목표합계': '{:,.0f}',
            '실적합계': '{:,.0f}',
            '평균달성률(%)': '{:.1f}'
        }),
        use_container_width=True
    )

with tab4:
    st.subheader("📋 총판별 상세 달성률 데이터")
    
    # 순위 추가
    achievement_df['순위'] = range(1, len(achievement_df) + 1)
    
    display_df = achievement_df[[
        '순위', '총판', '등급', '전체목표', '실적부수', '전체달성률(%)', 
        '차이', '거래학교수', '주문금액'
    ]].copy()
    
    st.dataframe(
        display_df.style.format({
            '전체목표': '{:,.0f}',
            '실적부수': '{:,.0f}',
            '전체달성률(%)': '{:.1f}',
            '차이': '{:,.0f}',
            '거래학교수': '{:,.0f}',
            '주문금액': '{:,.0f}'
        }).applymap(
            lambda x: 'color: green' if isinstance(x, (int, float)) and x >= 100 else ('color: red' if isinstance(x, (int, float)) and 0 <= x < 100 else ''),
            subset=['전체달성률(%)']
        ),
        use_container_width=True,
        height=600
    )
    
    # CSV 다운로드
    csv = display_df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 CSV 다운로드",
        data=csv,
        file_name="목표_대비_달성률.csv",
        mime="text/csv"
    )

with tab5:
    st.subheader("📉 목표 갭 분석")
    
    # 갭이 큰 순서대로 정렬
    gap_df = achievement_df.copy()
    gap_df['절대갭'] = abs(gap_df['차이'])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔼 초과 달성 TOP 10")
        over_achievement = gap_df[gap_df['차이'] > 0].sort_values('차이', ascending=False).head(10)
        
        if len(over_achievement) > 0:
            fig = px.bar(
                over_achievement,
                x='총판',
                y='차이',
                title="목표 초과 달성 TOP 10",
                text='차이',
                color='차이',
                color_continuous_scale='Greens'
            )
            fig.update_traces(texttemplate='%{text:+,.0f}', textposition='outside')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("초과 달성 총판이 없습니다.")
    
    with col2:
        st.markdown("### 🔽 미달성 TOP 10")
        under_achievement = gap_df[gap_df['차이'] < 0].sort_values('차이').head(10)
        
        if len(under_achievement) > 0:
            fig = px.bar(
                under_achievement,
                x='총판',
                y='차이',
                title="목표 미달성 TOP 10",
                text='차이',
                color='차이',
                color_continuous_scale='Reds_r'
            )
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("미달성 총판이 없습니다.")
    
    # 갭 분포
    st.markdown("---")
    st.subheader("📊 목표 갭 분포")
    
    fig_scatter = px.scatter(
        gap_df,
        x='전체목표',
        y='실적부수',
        size='절대갭',
        color='등급',
        hover_data=['총판', '전체달성률(%)'],
        title="목표 vs 실적 분포 (점 크기 = 갭)",
        labels={'전체목표': '목표 부수', '실적부수': '실적 부수'}
    )
    
    # 대각선 (목표=실적 기준선)
    max_val = max(gap_df['전체목표'].max(), gap_df['실적부수'].max())
    fig_scatter.add_trace(go.Scatter(
        x=[0, max_val],
        y=[0, max_val],
        mode='lines',
        line=dict(dash='dash', color='red'),
        name='목표선 (100%)',
        showlegend=True
    ))
    
    st.plotly_chart(fig_scatter, use_container_width=True)
