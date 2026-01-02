"""
시장 점유율 계산 유틸리티
학교수 대비 점유율 및 학생수 대비 점유율 계산
"""
import pandas as pd
import streamlit as st


def calculate_school_share(order_df, total_df, group_cols):
    """
    학교수 대비 점유율 계산
    
    Args:
        order_df: 주문 데이터프레임
        total_df: 전체 학교/학생 데이터프레임
        group_cols: 그룹화할 컬럼 리스트 (예: ['교과서명_구분'], ['시도명'], ['총판명'])
    
    Returns:
        점유율이 포함된 데이터프레임
    """
    if order_df.empty or total_df.empty:
        return pd.DataFrame()
    
    # 그룹별 채택학교수 계산
    adopted_schools = order_df.groupby(group_cols)['학교코드'].nunique().reset_index()
    adopted_schools.columns = list(group_cols) + ['채택학교수']
    
    # 그룹별 전체 학교수 계산
    if '시도명' in group_cols:
        # 지역별 분석인 경우
        total_schools = total_df.groupby(['시도명'])['학교코드'].nunique().reset_index()
        total_schools.columns = ['시도명', '전체학교수']
        result = adopted_schools.merge(total_schools, on='시도명', how='left')
    elif '교과서명_구분' in group_cols or '과목명' in group_cols:
        # 과목별 분석인 경우 - 전체 학교수 사용
        total_school_count = total_df['학교코드'].nunique()
        result = adopted_schools.copy()
        result['전체학교수'] = total_school_count
    else:
        # 기타 분석 (총판별 등) - 전체 학교수 사용
        total_school_count = total_df['학교코드'].nunique()
        result = adopted_schools.copy()
        result['전체학교수'] = total_school_count
    
    # 학교점유율(%) 계산
    result['학교점유율(%)'] = (result['채택학교수'] / result['전체학교수'] * 100).round(2)
    
    # 부수 정보 추가
    volume_data = order_df.groupby(group_cols)['부수'].sum().reset_index()
    result = result.merge(volume_data, on=group_cols, how='left')
    
    return result


def calculate_student_share(order_df, total_df, group_cols):
    """
    학생수 대비 점유율 계산
    
    Args:
        order_df: 주문 데이터프레임 (학교코드별 학생수 정보 포함)
        total_df: 전체 학교/학생 데이터프레임
        group_cols: 그룹화할 컬럼 리스트
    
    Returns:
        학생수 점유율이 포함된 데이터프레임
    """
    if order_df.empty or total_df.empty:
        return pd.DataFrame()
    
    # order_df에 학생수 정보 추가
    if '학생수' not in order_df.columns:
        order_df = order_df.merge(
            total_df[['학교코드', '학생수']],
            on='학교코드',
            how='left'
        )
    
    # 그룹별 채택학교 학생수 계산
    adopted_students = order_df.groupby(group_cols).agg({
        '학교코드': 'nunique',
        '학생수': 'sum',
        '부수': 'sum'
    }).reset_index()
    adopted_students.columns = list(group_cols) + ['채택학교수', '채택학교학생수', '부수']
    
    # 그룹별 전체 학생수 계산
    if '시도명' in group_cols:
        # 지역별 분석인 경우
        total_students = total_df.groupby(['시도명'])['학생수'].sum().reset_index()
        total_students.columns = ['시도명', '전체학생수']
        result = adopted_students.merge(total_students, on='시도명', how='left')
    elif '교과서명_구분' in group_cols or '과목명' in group_cols:
        # 과목별 분석인 경우 - 전체 학생수 사용
        total_student_count = total_df['학생수'].sum()
        result = adopted_students.copy()
        result['전체학생수'] = total_student_count
    else:
        # 기타 분석 - 전체 학생수 사용
        total_student_count = total_df['학생수'].sum()
        result = adopted_students.copy()
        result['전체학생수'] = total_student_count
    
    # 학생수점유율(%) 계산
    result['학생수점유율(%)'] = (result['채택학교학생수'] / result['전체학생수'] * 100).round(2)
    
    return result


def calculate_both_shares(order_df, total_df, group_cols):
    """
    학교수 대비 점유율과 학생수 대비 점유율 모두 계산
    
    Args:
        order_df: 주문 데이터프레임
        total_df: 전체 학교/학생 데이터프레임
        group_cols: 그룹화할 컬럼 리스트
    
    Returns:
        모든 점유율 정보가 포함된 데이터프레임
    """
    if order_df.empty or total_df.empty:
        return pd.DataFrame()
    
    # 학생수 정보 병합
    if '학생수' not in order_df.columns:
        order_with_students = order_df.merge(
            total_df[['학교코드', '학생수']],
            on='학교코드',
            how='left'
        )
    else:
        order_with_students = order_df.copy()
    
    # 그룹별 집계
    result = order_with_students.groupby(group_cols).agg({
        '학교코드': 'nunique',
        '학생수': 'sum',
        '부수': 'sum'
    }).reset_index()
    result.columns = list(group_cols) + ['채택학교수', '채택학교학생수', '부수']
    
    # 전체 학교수/학생수 계산
    if '시도명' in group_cols:
        # 지역별 전체 수 계산
        total_by_region = total_df.groupby(['시도명']).agg({
            '학교코드': 'nunique',
            '학생수': 'sum'
        }).reset_index()
        total_by_region.columns = ['시도명', '전체학교수', '전체학생수']
        result = result.merge(total_by_region, on='시도명', how='left')
    else:
        # 전체 수 사용
        total_school_count = total_df['학교코드'].nunique()
        total_student_count = total_df['학생수'].sum()
        result['전체학교수'] = total_school_count
        result['전체학생수'] = total_student_count
    
    # 점유율 계산
    result['학교점유율(%)'] = (result['채택학교수'] / result['전체학교수'] * 100).round(2)
    result['학생수점유율(%)'] = (result['채택학교학생수'] / result['전체학생수'] * 100).round(2)
    
    return result


def compare_year_shares(order_df, total_df, group_cols, year_col='학년도'):
    """
    연도별 점유율 비교 (증감 계산)
    
    Args:
        order_df: 주문 데이터프레임 (여러 연도 포함)
        total_df: 전체 학교/학생 데이터프레임
        group_cols: 그룹화할 컬럼 리스트
        year_col: 학년도 컬럼명
    
    Returns:
        연도별 점유율 및 증감이 포함된 데이터프레임
    """
    if order_df.empty or year_col not in order_df.columns:
        return pd.DataFrame()
    
    years = sorted(order_df[year_col].unique())
    if len(years) < 2:
        # 단일 연도만 있으면 증감 계산 불가
        return calculate_both_shares(order_df, total_df, group_cols)
    
    # 각 연도별 점유율 계산
    year_data = {}
    for year in years:
        year_df = order_df[order_df[year_col] == year]
        year_shares = calculate_both_shares(year_df, total_df, group_cols)
        year_data[str(year)] = year_shares
    
    # 최신 2개 연도 비교 (보통 2025 vs 2026)
    if len(years) >= 2:
        prev_year = str(years[-2])
        curr_year = str(years[-1])
        
        prev_data = year_data[prev_year]
        curr_data = year_data[curr_year]
        
        # 병합
        comparison = curr_data.merge(
            prev_data[group_cols + ['부수', '학교점유율(%)', '학생수점유율(%)']],
            on=group_cols,
            how='outer',
            suffixes=('', f'_{prev_year}')
        )
        
        # 증감 계산
        comparison['부수증감'] = comparison['부수'] - comparison[f'부수_{prev_year}']
        comparison['부수증감률(%)'] = (
            (comparison['부수'] - comparison[f'부수_{prev_year}']) / 
            comparison[f'부수_{prev_year}'] * 100
        ).round(1)
        
        comparison['학교점유율증감(%p)'] = (
            comparison['학교점유율(%)'] - comparison[f'학교점유율(%)_{prev_year}']
        ).round(2)
        
        comparison['학생수점유율증감(%p)'] = (
            comparison['학생수점유율(%)'] - comparison[f'학생수점유율(%)_{prev_year}']
        ).round(2)
        
        # 컬럼명 정리
        comparison.rename(columns={
            '부수': f'부수({curr_year})',
            f'부수_{prev_year}': f'부수({prev_year})',
            '학교점유율(%)': f'학교점유율(%)({curr_year})',
            f'학교점유율(%)_{prev_year}': f'학교점유율(%)({prev_year})',
            '학생수점유율(%)': f'학생수점유율(%)({curr_year})',
            f'학생수점유율(%)_{prev_year}': f'학생수점유율(%)({prev_year})'
        }, inplace=True)
        
        return comparison
    
    return year_data[str(years[-1])]


def display_share_metrics(data, group_name, show_volume=True):
    """
    점유율 메트릭을 화면에 표시
    
    Args:
        data: 점유율 데이터 (Series 또는 단일 행)
        group_name: 그룹명 (표시용)
        show_volume: 부수 표시 여부
    """
    cols = st.columns(4 if show_volume else 3)
    
    col_idx = 0
    if show_volume and '부수' in data:
        cols[col_idx].metric("📦 부수", f"{data['부수']:,.0f}권")
        col_idx += 1
    
    if '채택학교수' in data:
        cols[col_idx].metric("🏫 채택학교수", f"{data['채택학교수']:,.0f}개")
        col_idx += 1
    
    if '학교점유율(%)' in data:
        cols[col_idx].metric("📊 학교점유율", f"{data['학교점유율(%)']:.2f}%")
        col_idx += 1
    
    if '학생수점유율(%)' in data:
        cols[col_idx].metric("👥 학생수점유율", f"{data['학생수점유율(%)']:.2f}%")


def display_share_comparison(data_2025, data_2026, group_name):
    """
    연도별 점유율 비교 표시 (증감 포함)
    
    Args:
        data_2025: 2025년 데이터 (Series)
        data_2026: 2026년 데이터 (Series)
        group_name: 그룹명
    """
    st.subheader(f"📊 {group_name} - 연도별 비교")
    
    # 부수 비교
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📦 부수 (2026)", 
                 f"{data_2026.get('부수', 0):,.0f}권",
                 delta=f"{data_2026.get('부수', 0) - data_2025.get('부수', 0):,.0f}권")
    
    # 학교점유율 비교
    with col2:
        share_2025 = data_2025.get('학교점유율(%)', 0)
        share_2026 = data_2026.get('학교점유율(%)', 0)
        st.metric("🏫 학교점유율 (2026)",
                 f"{share_2026:.2f}%",
                 delta=f"{share_2026 - share_2025:.2f}%p")
    
    # 학생수점유율 비교
    with col3:
        student_share_2025 = data_2025.get('학생수점유율(%)', 0)
        student_share_2026 = data_2026.get('학생수점유율(%)', 0)
        st.metric("👥 학생수점유율 (2026)",
                 f"{student_share_2026:.2f}%",
                 delta=f"{student_share_2026 - student_share_2025:.2f}%p")
