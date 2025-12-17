"""
개선된 시장 규모 및 점유율 계산 모듈

학교별로 과목의 실제 배정 학년을 추정하여 정확한 시장 규모를 계산합니다.

핵심 개선사항:
1. 학년도 구분: 2025년도 주문 vs 2026년도 주문
2. 학교별 과목 배정 학년 자동 추정 (주문 부수와 학년별 학생수 비교)
3. 정보, 체육 등 학년이 가변적인 과목 정확 처리
"""

import pandas as pd
import numpy as np
import re


def infer_subject_grade_for_school(order_quantity, grade_students):
    """
    주문 부수와 학년별 학생수를 비교하여 해당 과목이 몇 학년에 배정되었는지 추정
    
    Args:
        order_quantity: 주문 부수
        grade_students: dict {1: 학생수, 2: 학생수, 3: 학생수}
    
    Returns:
        추정 학년 (1, 2, 3) 또는 None (여러 학년 또는 특정 불가)
    """
    if not grade_students or order_quantity <= 0:
        return None
    
    # 각 학년 학생수와의 차이 계산
    differences = {}
    for grade, students in grade_students.items():
        if students > 0:
            # 오차율 계산 (주문부수가 학생수와 얼마나 가까운지)
            error_rate = abs(order_quantity - students) / students
            differences[grade] = error_rate
    
    if not differences:
        return None
    
    # 가장 오차가 적은 학년 선택 (15% 이내 오차만 허용)
    min_grade = min(differences, key=differences.get)
    if differences[min_grade] < 0.15:  # 15% 이내 오차
        return min_grade
    
    # 여러 학년 합과 비교 (2개 학년 대상일 수도 있음)
    for grade_combo in [(1, 2), (2, 3), (1, 2, 3)]:
        combo_students = sum(grade_students.get(g, 0) for g in grade_combo)
        if combo_students > 0:
            error_rate = abs(order_quantity - combo_students) / combo_students
            if error_rate < 0.15:
                # 여러 학년 대상 → None 반환 (전체 학년으로 처리)
                return None
    
    return None  # 특정 불가능


def match_orders_with_student_data(order_df, total_df, year_offset=1):
    """
    주문 데이터와 학생수 데이터를 학교별로 매칭하고, 
    학년도별 주문 패턴으로 배정 학년을 판단하여 시장 규모 계산
    
    비즈니스 로직:
    - 2025년, 2026년 둘 다 주문 → 1학년 편성
    - 2026년만 주문 → 2학년 편성
    - 2025년만 주문 → 1학년 편성
    
    Args:
        order_df: 주문 데이터
        total_df: 학생수 데이터 (2025년 기준)
        year_offset: 학년 오프셋 (사용 안 함, 학년도 패턴으로 판단)
    
    Returns:
        학교별 + 도서코드별 시장 규모 데이터프레임
    """
    results = []
    
    # 학교 코드 컬럼 찾기
    school_code_col = None
    for col in ['정보공시학교코드', '정보공시 학교코드', '학교코드']:
        if col in order_df.columns:
            school_code_col = col
            break
    
    if not school_code_col:
        return pd.DataFrame()
    
    # 도서코드별 학년도 패턴 분석 (전체 데이터에서)
    book_code_col = '도서코드(교지명구분)' if '도서코드(교지명구분)' in order_df.columns else '도서코드'
    if book_code_col not in order_df.columns:
        return pd.DataFrame()
    
    # 도서코드별로 학년도 주문 패턴 파악
    book_grade_map = {}
    if '학년도' in order_df.columns:
        for book_code, book_group in order_df.groupby(book_code_col, dropna=False):
            if pd.isna(book_code):
                continue
            years = book_group['학년도'].unique()
            has_2025 = 2025 in years
            has_2026 = 2026 in years
            
            # 배정 학년 결정
            if has_2025 and has_2026:
                book_grade_map[book_code] = (1, "2025+2026년 주문")
            elif has_2026 and not has_2025:
                book_grade_map[book_code] = (2, "2026년만 주문")
            elif has_2025 and not has_2026:
                book_grade_map[book_code] = (1, "2025년만 주문")
            else:
                book_grade_map[book_code] = (None, "학년도 정보 없음")
    
    # 학교별 + 도서코드별로 그룹화
    groupby_cols = [school_code_col, book_code_col]
    if '학교급명' in order_df.columns:
        groupby_cols.append('학교급명')
    
    for group_keys, group_data in order_df.groupby(groupby_cols, dropna=False):
        if not isinstance(group_keys, tuple):
            group_keys = (group_keys,)
        
        school_code = group_keys[0]
        book_code = group_keys[1] if len(group_keys) > 1 else '미상'
        school_level = group_keys[2] if len(group_keys) > 2 else '미상'
        
        # 도서코드에 해당하는 과목명 가져오기
        subject_name = group_data['교과서명_구분'].iloc[0] if '교과서명_구분' in group_data.columns and not group_data['교과서명_구분'].isna().all() else str(book_code)
        
        # 해당 학교의 학생수 데이터 찾기
        school_total = total_df[total_df.get('정보공시 학교코드', '') == str(school_code)]
        
        if school_total.empty:
            continue
        
        # 학교급 코드 확인
        school_level_code = school_total.iloc[0].get('학교급코드', 0)
        
        # 현재 학년별 학생수 추출 (2025년 기준)
        grade_students = {}
        for grade in [1, 2, 3]:
            col_name = f'{grade}학년 학생수'
            if col_name in school_total.columns:
                students = school_total.iloc[0].get(col_name, 0)
                grade_students[grade] = int(students) if pd.notna(students) else 0
        
        # 주문 부수 합계
        total_orders = group_data['부수'].sum()
        
        # 도서코드별 배정 학년 가져오기
        if book_code in book_grade_map:
            target_grade, grade_logic = book_grade_map[book_code]
        else:
            target_grade = None
            grade_logic = "학년도 정보 없음"
        
        # 시장 규모 계산 (배정 학년의 학생수만)
        if target_grade and target_grade in grade_students:
            market_size = grade_students[target_grade]
        elif not target_grade:
            # 학년 정보 없으면 전체 학년 합계
            market_size = sum(grade_students.values())
        else:
            market_size = sum(grade_students.values())
        
        results.append({
            '학교코드': school_code,
            '도서코드': book_code,
            '과목명': subject_name,
            '학교급': school_level,
            '주문부수': total_orders,
            '배정학년': target_grade,
            '배정로직': grade_logic,
            '시장규모': market_size,
            '1학년학생수': grade_students.get(1, 0),
            '2학년학생수': grade_students.get(2, 0),
            '3학년학생수': grade_students.get(3, 0),
        })
    
    return pd.DataFrame(results)


def calculate_market_size_by_subject_v2(order_df, total_df, product_df=None):
    """
    과목별 시장 규모 및 점유율 계산 (개선 버전)
    
    학년도별 주문 패턴으로 배정 학년을 판단하여 정확한 시장 규모 산출
    
    비즈니스 로직:
    - 2025년, 2026년 둘 다 주문 → 1학년 편성
    - 2026년만 주문 → 2학년 편성
    - 2025년만 주문 → 1학년 편성
    
    Args:
        order_df: 주문 데이터프레임
        total_df: 학생수 데이터프레임 (2025년 기준)
        product_df: 제품 정보 데이터프레임 (옵션)
    
    Returns:
        과목별 시장 규모 및 점유율 데이터프레임
    """
    # 학교별 데이터 매칭 (학년도 패턴으로 배정 학년 판단)
    school_subject = match_orders_with_student_data(order_df, total_df, year_offset=0)
    
    if school_subject.empty:
        return pd.DataFrame()
    
    # 도서코드별 집계 (과목명이 아닌 도서코드로!)
    book_code_col = '도서코드' if '도서코드' in school_subject.columns else '과목명'
    
    subject_summary = school_subject.groupby(book_code_col).agg({
        '주문부수': 'sum',
        '시장규모': 'sum',
        '학교코드': 'count',  # 학교 수
        '과목명': 'first',  # 과목명 가져오기
        '배정학년': 'first',  # 배정 학년 가져오기
        '배정로직': 'first'  # 배정 로직 가져오기
    }).reset_index()
    
    subject_summary.columns = ['도서코드', '주문부수', '시장규모(학생수)', '학교수', '과목명', '대상학년', '배정로직']
    
    # 점유율 계산
    subject_summary['점유율(%)'] = (
        subject_summary['주문부수'] / subject_summary['시장규모(학생수)'] * 100
    ).fillna(0)
    

    # 정렬
    subject_summary = subject_summary.sort_values('주문부수', ascending=False)
    
    return subject_summary
