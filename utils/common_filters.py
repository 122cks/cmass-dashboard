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
        show_filters: List of filters to show. Options: ['교과군', '과목', '지역', '총판']
                     If None, shows all filters
    
    Returns:
        Filtered dataframe
    """
    if show_filters is None:
        show_filters = ['교과군', '과목', '지역', '총판']
    
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 공통 필터")
    
    filtered_df = order_df.copy()
    
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
