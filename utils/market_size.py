"""
시장 규모 및 점유율 정확 계산 모듈

2025년 학생수 데이터 기준으로 2026년도 사용 교과서의 시장 규모를 계산합니다.
- 현재 1학년 → 내년 2학년
- 각 과목의 대상 학년별 학생수를 정확히 산출

주의: 과목명의 숫자(1, 2 등)는 학년이 아니라 학기를 의미함
- 한국사 1, 한국사 2 → 1학기, 2학기
- 체육 1, 체육 2 → 1학기, 2학기
- 미술 ①, 미술 ② → 1학기, 2학기
"""

import pandas as pd
import re

# 과목명-학년 매핑 (실제 대상 학년 기준)
SUBJECT_GRADE_MAPPING = {
    # 중학교 - 학년 기준으로 정확히 매핑
    '정보': {'학교급코드': 3, '학년': 1},  # 중1
    '보건': {'학교급코드': 3, '학년': 2},  # 중2
    '진로와 직업': {'학교급코드': 3, '학년': 1},  # 중1
    # 미술 ①② 는 학기이므로 학년 구분 없음
    '미술': {'학교급코드': 3, '학년': None},  # 전 학년
    '체육': {'학교급코드': 3, '학년': None},  # 전 학년
    
    # 고등학교 - 한국사는 공통과목이므로 학년 특정
    '한국사': {'학교급코드': 4, '학년': 1},  # 고1 (1, 2학기 모두)
    '인공지능 기초': {'학교급코드': 4, '학년': 1},  # 고1
    # 기타 선택과목은 2-3학년
}

def extract_grade_from_subject(subject_name, school_level_code=None):
    """
    과목명에서 학년 정보 추출
    
    주의: 과목명의 숫자는 학기(1학기, 2학기)를 의미하므로 학년과 무관
    
    Args:
        subject_name: 과목명
        school_level_code: 학교급 코드 (2: 초, 3: 중, 4: 고)
    
    Returns:
        학년 (1, 2, 3) 또는 None (전 학년 대상)
    """
    if pd.isna(subject_name):
        return None
    
    subject_str = str(subject_name).strip()
    
    # 기본 과목명에서 숫자/기호 제거 (학기 표시 제거)
    # "한국사 1" → "한국사", "미술 ①" → "미술"
    base_subject = re.sub(r'\s*[①②③④⑤⑥\d]+\s*$', '', subject_str).strip()
    
    # 직접 매핑 확인 (기본 과목명으로)
    if base_subject in SUBJECT_GRADE_MAPPING:
        mapping = SUBJECT_GRADE_MAPPING[base_subject]
        if school_level_code is None or mapping['학교급코드'] == school_level_code:
            return mapping['학년']
    
    # 원래 과목명으로도 확인 (완전 일치)
    if subject_str in SUBJECT_GRADE_MAPPING:
        mapping = SUBJECT_GRADE_MAPPING[subject_str]
        if school_level_code is None or mapping['학교급코드'] == school_level_code:
            return mapping['학년']
    
    # 과목 키워드로 추정
    if school_level_code == 3:  # 중학교
        # 중1 과목들
        if any(keyword in base_subject for keyword in ['정보', '진로']):
            return 1
        # 중2 과목들
        elif any(keyword in base_subject for keyword in ['보건']):
            return 2
        # 미술, 체육 등은 전 학년 대상
        elif any(keyword in base_subject for keyword in ['미술', '체육', '음악']):
            return None  # 전 학년
        return None  # 기본: 전 학년
        
    elif school_level_code == 4:  # 고등학교
        # 고1 필수과목
        if any(keyword in base_subject for keyword in ['한국사', '인공지능']):
            return 1
        # 선택과목은 대부분 2-3학년이지만 특정 어려움
        return None  # 전 학년 또는 선택 과목
    
    return None

def get_next_year_grade_column(current_grade, is_2026=True):
    """
    2025년 학년별 학생수 데이터에서 2026년도에 해당하는 컬럼명 반환
    
    Args:
        current_grade: 2025년 기준 학년 (1, 2, 3)
        is_2026: 2026년도 사용 여부 (True면 +1 학년)
    
    Returns:
        학생수 컬럼명 (예: '2학년 학생수')
    """
    if pd.isna(current_grade) or current_grade is None:
        return None
    
    if is_2026:
        # 2025년 1학년 → 2026년 2학년
        next_grade = int(current_grade) + 1
    else:
        next_grade = int(current_grade)
    
    # 초등학교는 6학년까지, 중고등학교는 3학년까지
    if next_grade > 6:
        return None
    
    return f'{next_grade}학년 학생수'

def get_all_grades_for_school_level(school_level_code, total_df):
    """
    특정 학교급의 모든 학년 학생수 합계 반환 (학년 특정 불가능한 과목용)
    
    Args:
        school_level_code: 학교급 코드
        total_df: 학생수 데이터
    
    Returns:
        전체 학생수
    """
    if school_level_code == 2:  # 초등학교
        grade_columns = [f'{i}학년 학생수' for i in range(1, 7)]
    else:  # 중·고등학교
        grade_columns = [f'{i}학년 학생수' for i in range(1, 4)]
    
    # 2026년도 기준으로 +1학년 (현재 1학년 → 내년 2학년)
    next_year_columns = [f'{i+1}학년 학생수' for i in range(1, 3 if school_level_code != 2 else 6)]
    
    total = 0
    filtered = total_df[total_df['학교급코드'] == school_level_code]
    
    for col in next_year_columns:
        if col in filtered.columns:
            total += filtered[col].sum()
    
    return total

def calculate_market_size_by_subject(order_df, total_df, product_df=None):
    """
    과목별 정확한 시장 규모 계산
    
    Args:
        order_df: 주문 데이터
        total_df: 학교별 학년별 학생수 데이터
        product_df: 제품 정보 (선택)
    
    Returns:
        DataFrame with columns: [과목명, 학교급, 대상학년, 시장규모(학생수), 주문부수, 점유율(%)]
    """
    results = []
    
    # 주문 데이터에서 과목별 집계
    subject_orders = order_df.groupby(['과목명', '학교급명']).agg({
        '부수': 'sum',
        '정보공시학교코드': lambda x: list(x.unique())
    }).reset_index()
    
    for _, row in subject_orders.iterrows():
        subject = row['과목명']
        school_level = row['학교급명']
        order_count = row['부수']
        schools = row['정보공시학교코드']
        
        # 학교급 코드 결정
        if '중학교' in str(school_level):
            school_code = 3
        elif '고등' in str(school_level):
            school_code = 4
        elif '초등' in str(school_level):
            school_code = 2
        else:
            school_code = None
        
        # 대상 학년 추출
        target_grade = extract_grade_from_subject(subject, school_code)
        
        if target_grade is None:
            # 학년 정보 없으면 해당 학교급 전체 학생수 사용
            market_size = get_all_grades_for_school_level(school_code, total_df)
        else:
            # 2026년도 해당 학년 컬럼
            grade_column = get_next_year_grade_column(target_grade, is_2026=True)
            
            if grade_column and grade_column in total_df.columns:
                # 해당 학년 학생수만 집계
                market_size = total_df[total_df['학교급코드'] == school_code][grade_column].sum()
            else:
                # 컬럼이 없으면 전체 사용
                market_size = get_all_grades_for_school_level(school_code, total_df)
        
        # 점유율 계산
        if market_size > 0:
            share = (order_count / market_size) * 100
        else:
            share = 0
        
        results.append({
            '과목명': subject,
            '학교급': school_level,
            '대상학년': f'{target_grade}학년→{target_grade+1}학년' if target_grade else '전체',
            '2026학년': target_grade + 1 if target_grade else None,
            '시장규모(학생수)': market_size,
            '주문부수': order_count,
            '점유율(%)': share,
            '주문학교수': len(schools)
        })
    
    return pd.DataFrame(results)

def calculate_market_size_by_region_subject(order_df, total_df):
    """
    지역별 × 과목별 정확한 시장 규모 및 점유율 계산
    
    Returns:
        DataFrame with columns: [시도교육청, 과목명, 학교급, 대상학년, 시장규모, 주문부수, 점유율(%)]
    """
    results = []
    
    # 지역별 × 과목별 주문 집계
    regional_subject_orders = order_df.groupby(['시도교육청', '과목명', '학교급명'])['부수'].sum().reset_index()
    
    for _, row in regional_subject_orders.iterrows():
        region = row['시도교육청']
        subject = row['과목명']
        school_level = row['학교급명']
        order_count = row['부수']
        
        # 학교급 코드
        if '중학교' in str(school_level):
            school_code = 3
        elif '고등' in str(school_level):
            school_code = 4
        elif '초등' in str(school_level):
            school_code = 2
        else:
            school_code = None
        
        # 대상 학년
        target_grade = extract_grade_from_subject(subject, school_code)
        
        # 해당 지역의 시장 규모
        region_schools = total_df[(total_df['시도교육청'] == region) & 
                                  (total_df['학교급코드'] == school_code)]
        
        if target_grade is None:
            market_size = get_all_grades_for_school_level(school_code, region_schools)
        else:
            grade_column = get_next_year_grade_column(target_grade, is_2026=True)
            if grade_column and grade_column in region_schools.columns:
                market_size = region_schools[grade_column].sum()
            else:
                market_size = get_all_grades_for_school_level(school_code, region_schools)
        
        # 점유율
        share = (order_count / market_size * 100) if market_size > 0 else 0
        
        results.append({
            '시도교육청': region,
            '과목명': subject,
            '학교급': school_level,
            '대상학년': target_grade + 1 if target_grade else None,
            '시장규모': market_size,
            '주문부수': order_count,
            '점유율(%)': share
        })
    
    return pd.DataFrame(results)

def calculate_accurate_market_share(order_df, total_df, group_by_columns):
    """
    일반적인 그룹별 정확한 점유율 계산
    
    Args:
        order_df: 주문 데이터
        total_df: 학생수 데이터
        group_by_columns: 그룹화할 컬럼 리스트
    
    Returns:
        DataFrame with accurate market share
    """
    # 각 주문 건에 대상 학년 정보 추가
    order_with_grade = order_df.copy()
    
    # 학교급 코드 추가
    def get_school_code(school_level):
        if pd.isna(school_level):
            return None
        if '중학교' in str(school_level):
            return 3
        elif '고등' in str(school_level):
            return 4
        elif '초등' in str(school_level):
            return 2
        return None
    
    order_with_grade['학교급코드'] = order_with_grade['학교급명'].apply(get_school_code)
    order_with_grade['대상학년'] = order_with_grade.apply(
        lambda row: extract_grade_from_subject(row['과목명'], row['학교급코드']),
        axis=1
    )
    
    # 그룹별 집계
    result = order_with_grade.groupby(group_by_columns).apply(
        lambda group: calculate_group_market_share(group, total_df)
    ).reset_index()
    
    return result

def calculate_group_market_share(group_df, total_df):
    """
    그룹에 대한 시장 규모 및 점유율 계산
    """
    total_orders = group_df['부수'].sum()
    
    # 시장 규모 계산 (학년 고려)
    market_size = 0
    
    for _, row in group_df.iterrows():
        school_code = row.get('학교급코드')
        target_grade = row.get('대상학년')
        
        if target_grade and school_code:
            grade_column = get_next_year_grade_column(target_grade, is_2026=True)
            if grade_column and grade_column in total_df.columns:
                grade_market = total_df[total_df['학교급코드'] == school_code][grade_column].sum()
                market_size += grade_market
            else:
                market_size += get_all_grades_for_school_level(school_code, total_df)
        elif school_code:
            market_size += get_all_grades_for_school_level(school_code, total_df)
    
    share = (total_orders / market_size * 100) if market_size > 0 else 0
    
    return pd.Series({
        '주문부수': total_orders,
        '시장규모': market_size,
        '점유율(%)': share
    })
