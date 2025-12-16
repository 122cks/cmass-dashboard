"""
Common filter components for all analysis pages
"""
import streamlit as st
import pandas as pd


def apply_common_filters(order_df, show_filters=None):
    """
    Apply common filters to order data
    
    Args:
        order_df: Order dataframe
        show_filters: List of filters to show. Options: ['학년도', '교과군', '과목', '지역', '총판']
                     If None, shows all filters
    
    Returns:
        Filtered dataframe
    """
    if show_filters is None:
        show_filters = ['학년도', '교과군', '과목', '지역', '총판']
    
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 공통 필터")
    
    filtered_df = order_df.copy()
    
    # 0. 학년도 필터 (2026년도 기본값)
    if '학년도' in show_filters and '학년도' in order_df.columns:
        years = sorted(order_df['학년도'].dropna().unique().tolist(), reverse=True)
        # 2026년도가 있으면 기본값으로, 없으면 최신 학년도
        default_year = 2026 if 2026 in years else (years[0] if years else None)
        default_index = years.index(default_year) if default_year in years else 0
        
        selected_year = st.sidebar.selectbox(
            "📅 학년도 선택", 
            years, 
            index=default_index,
            key='common_filter_year'
        )
        
        filtered_df = filtered_df[filtered_df['학년도'] == selected_year]
        
        # 학년도별 비교 옵션
        if len(years) > 1:
            show_comparison = st.sidebar.checkbox("📊 학년도별 비교 보기", key='common_filter_year_comparison')
            if show_comparison and 'year_comparison_enabled' not in st.session_state:
                st.session_state['year_comparison_enabled'] = True
                st.session_state['selected_year'] = selected_year
            elif not show_comparison and 'year_comparison_enabled' in st.session_state:
                del st.session_state['year_comparison_enabled']
    
    # 1. 교과군 필터
    if '교과군' in show_filters:
        subject_col = '교과군_제품' if '교과군_제품' in order_df.columns else '교과군'
        if subject_col in order_df.columns:
            subject_groups = ['전체'] + sorted(order_df[subject_col].dropna().unique().tolist())
            selected_group = st.sidebar.selectbox("📚 교과군 선택", subject_groups, key='common_filter_subject_group')
            
            if selected_group != '전체':
                filtered_df = filtered_df[filtered_df[subject_col] == selected_group]
    
    # 2. 과목 필터
    if '과목' in show_filters:
        subject_col = '교과서명_구분' if '교과서명_구분' in filtered_df.columns else '교과서명'
        if subject_col in filtered_df.columns:
            subjects = ['전체'] + sorted(filtered_df[subject_col].dropna().unique().tolist())
            selected_subject = st.sidebar.selectbox("📖 과목 선택", subjects, key='common_filter_subject')
            
            if selected_subject != '전체':
                filtered_df = filtered_df[filtered_df[subject_col] == selected_subject]
    
    # 3. 지역 필터
    if '지역' in show_filters:
        if '시도교육청' in filtered_df.columns:
            regions = ['전체'] + sorted(filtered_df['시도교육청'].dropna().unique().tolist())
            selected_region = st.sidebar.selectbox("🗺️ 지역 선택", regions, key='common_filter_region')
            
            if selected_region != '전체':
                filtered_df = filtered_df[filtered_df['시도교육청'] == selected_region]
    
    # 4. 총판 필터
    if '총판' in show_filters:
        if '총판' in filtered_df.columns:
            distributors = ['전체'] + sorted(filtered_df['총판'].dropna().unique().tolist())
            selected_dist = st.sidebar.selectbox("🏢 총판 선택", distributors, key='common_filter_distributor')
            
            if selected_dist != '전체':
                filtered_df = filtered_df[filtered_df['총판'] == selected_dist]
    
    return filtered_df


def show_filter_summary(filtered_df, original_df):
    """Show summary of applied filters"""
    if len(filtered_df) < len(original_df):
        st.info(f"🔍 필터 적용: 전체 {len(original_df):,}건 중 {len(filtered_df):,}건 표시")
