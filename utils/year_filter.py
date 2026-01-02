"""
학년도 필터 및 비교 유틸리티
모든 페이지에서 공통으로 사용
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def add_year_filter_sidebar(order_df, default_year='2026'):
    """
    사이드바에 학년도 필터 추가
    
    Args:
        order_df: 주문 데이터프레임
        default_year: 기본 선택 연도 (기본값: '2026')
    
    Returns:
        tuple: (선택된 연도 리스트, 비교 모드 활성화 여부)
    """
    st.sidebar.markdown("---")
    st.sidebar.header("📅 학년도 선택")
    
    if '학년도' not in order_df.columns:
        st.sidebar.warning("학년도 정보가 없습니다.")
        return None, False
    
    # 사용 가능한 학년도 추출
    available_years = sorted([str(y) for y in order_df['학년도'].dropna().unique()], reverse=True)
    
    if not available_years:
        st.sidebar.warning("학년도 데이터가 없습니다.")
        return None, False
    
    # 기본 연도가 없으면 최신 연도 사용
    if default_year not in available_years:
        default_year = available_years[0]
    
    # 비교 모드 선택
    comparison_mode = st.sidebar.checkbox("📊 연도 비교 모드", value=False, help="2025년과 2026년을 비교합니다")
    
    if comparison_mode:
        # 비교 모드: 2025와 2026 자동 선택
        if '2025' in available_years and '2026' in available_years:
            selected_years = ['2025', '2026']
            st.sidebar.info("🔄 2025년 vs 2026년 비교 모드")
        else:
            st.sidebar.warning("2025년 또는 2026년 데이터가 없어 비교가 불가능합니다.")
            selected_years = [default_year]
            comparison_mode = False
    else:
        # 단일 연도 선택
        selected_year = st.sidebar.selectbox(
            "분석 학년도",
            options=available_years,
            index=available_years.index(default_year) if default_year in available_years else 0
        )
        selected_years = [selected_year]
        st.sidebar.success(f"✅ {selected_year}년 데이터 분석")
    
    return selected_years, comparison_mode


def filter_by_years(df, years, year_column='학년도'):
    """
    학년도로 데이터 필터링
    
    Args:
        df: 필터링할 데이터프레임
        years: 선택된 학년도 리스트
        year_column: 학년도 컬럼명 (기본값: '학년도')
    
    Returns:
        필터링된 데이터프레임
    """
    if year_column not in df.columns or years is None:
        return df
    
    return df[df[year_column].astype(str).isin(years)].copy()


def create_year_comparison_chart(df, metric_col, group_col, title, year_column='학년도'):
    """
    연도별 비교 차트 생성
    
    Args:
        df: 데이터프레임
        metric_col: 비교할 메트릭 컬럼
        group_col: 그룹화 컬럼
        title: 차트 제목
        year_column: 학년도 컬럼명
    
    Returns:
        plotly figure
    """
    if year_column not in df.columns:
        return None
    
    # 연도별 집계
    comparison_data = df.groupby([year_column, group_col])[metric_col].sum().reset_index()
    comparison_data[year_column] = comparison_data[year_column].astype(str)
    
    fig = px.bar(
        comparison_data,
        x=group_col,
        y=metric_col,
        color=year_column,
        barmode='group',
        title=title,
        text=metric_col
    )
    fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
    fig.update_layout(xaxis_tickangle=-45, height=500)
    
    return fig


def create_year_comparison_metrics(df_2025, df_2026, metric_cols):
    """
    연도별 주요 지표 비교 메트릭 표시
    
    Args:
        df_2025: 2025년 데이터
        df_2026: 2026년 데이터
        metric_cols: 비교할 메트릭 컬럼 딕셔너리 {컬럼명: 표시명}
    """
    st.markdown("### 📊 2025년 vs 2026년 주요 지표 비교")
    
    cols = st.columns(len(metric_cols))
    
    for idx, (col_name, display_name) in enumerate(metric_cols.items()):
        with cols[idx]:
            if col_name in df_2026.columns and col_name in df_2025.columns:
                val_2026 = df_2026[col_name].sum() if col_name != 'count' else len(df_2026)
                val_2025 = df_2025[col_name].sum() if col_name != 'count' else len(df_2025)
                delta = val_2026 - val_2025
                delta_pct = (delta / val_2025 * 100) if val_2025 > 0 else 0
                
                st.metric(
                    display_name,
                    f"{val_2026:,.0f}",
                    delta=f"{delta:+,.0f} ({delta_pct:+.1f}%)",
                    help=f"2025년: {val_2025:,.0f}"
                )


def show_year_comparison_table(df, group_col, metric_cols, year_column='학년도'):
    """
    연도별 비교 테이블 표시
    
    Args:
        df: 데이터프레임
        group_col: 그룹화 컬럼
        metric_cols: 집계할 메트릭 컬럼 리스트
        year_column: 학년도 컬럼명
    """
    if year_column not in df.columns:
        st.warning("학년도 정보가 없습니다.")
        return
    
    # Pivot 테이블 생성
    agg_dict = {col: 'sum' for col in metric_cols if col in df.columns}
    
    if not agg_dict:
        st.warning("비교할 메트릭이 없습니다.")
        return
    
    pivot_data = df.groupby([group_col, year_column]).agg(agg_dict).reset_index()
    pivot_data[year_column] = pivot_data[year_column].astype(str)
    
    # 2025와 2026으로 분리
    df_2025 = pivot_data[pivot_data[year_column] == '2025'].copy()
    df_2026 = pivot_data[pivot_data[year_column] == '2026'].copy()
    
    if df_2025.empty or df_2026.empty:
        st.info("2025년 또는 2026년 데이터가 부족하여 비교표를 생성할 수 없습니다.")
        return
    
    # 병합하여 비교
    comparison = pd.merge(
        df_2026,
        df_2025,
        on=group_col,
        how='outer',
        suffixes=('_2026', '_2025')
    ).fillna(0)
    
    # 증감률 계산
    for col in metric_cols:
        if col in df.columns:
            col_2026 = f"{col}_2026"
            col_2025 = f"{col}_2025"
            if col_2026 in comparison.columns and col_2025 in comparison.columns:
                comparison[f"{col}_증감"] = comparison[col_2026] - comparison[col_2025]
                comparison[f"{col}_증감률(%)"] = (
                    (comparison[col_2026] - comparison[col_2025]) / 
                    comparison[col_2025].replace(0, 1) * 100
                )
    
    st.dataframe(comparison, use_container_width=True, height=400)
    
    return comparison
