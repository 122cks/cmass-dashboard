"""
시장 규모 및 점유율 정확 계산 모듈

2025년 학생수 데이터 기준으로 2026년도 사용 교과서의 시장 규모를 계산합니다.
- 현재 1학년 → 내년 2학년
- 각 과목의 대상 학년별 학생수를 정확히 산출
"""

import pandas as pd
import re

# 과목명-학년 매핑 (기본 규칙)
SUBJECT_GRADE_MAPPING = {
    # 중학교
    '정보': {'학교급코드': 3, '학년': 1},  # 중1
    '보건': {'학교급코드': 3, '학년': 2},  # 중2
    '진로와 직업': {'학교급코드': 3, '학년': 1},  # 중1
    '미술 ①': {'학교급코드': 3, '학년': 1},  # 중1
    '미술 ②': {'학교급코드': 3, '학년': 2},  # 중2
    '체육 ①': {'학교급코드': 3, '학년': 1},  # 중1
    '체육 ②': {'학교급코드': 3, '학년': 2},  # 중2
    
    # 고등학교
    '한국사 1': {'학교급코드': 4, '학년': 1},  # 고1
    '한국사 2': {'학교급코드': 4, '학년': 2},  # 고2
    '체육 1': {'학교급코드': 4, '학년': 1},  # 고1
    '체육 2': {'학교급코드': 4, '학년': 2},  # 고2
    '인공지능 기초': {'학교급코드': 4, '학년': 1},  # 고1
}

def extract_grade_from_subject(subject_name, school_level_code=None):
    """
    과목명에서 학년 정보 추출
    
    Args:
        subject_name: 과목명
        school_level_code: 학교급 코드 (2: 초, 3: 중, 4: 고)
    
    Returns:
        학년 (1, 2, 3) 또는 None
    """
    if pd.isna(subject_name):
        return None
    
    subject_str = str(subject_name).strip()
    
    # 직접 매핑 확인
    if subject_str in SUBJECT_GRADE_MAPPING:
        mapping = SUBJECT_GRADE_MAPPING[subject_str]
        if school_level_code is None or mapping['학교급코드'] == school_level_code:
            return mapping['학년']
    
    # 숫자 패턴으로 학년 추출
    # 예: "한국사 1", "체육 2", "미술 ①"
    patterns = [
        r'(\d)\s*$',  # 끝에 숫자
        r'\s+(\d)$',  # 공백 후 숫자
        r'[①②③]',  # 한자 숫자
    ]
    
    for pattern in patterns:
        match = re.search(pattern, subject_str)
        if match:
            if '①' in subject_str:
                return 1
            elif '②' in subject_str:
                return 2
            elif '③' in subject_str:
                return 3
            else:
                try:
                    grade = int(match.group(1))
                    if 1 <= grade <= 3:
                        return grade
                except:
                    pass
    
    # 기본값: 교과목에 따라 추정
    if school_level_code == 3:  # 중학교
        # 일반적으로 중1 과목들
        if any(keyword in subject_str for keyword in ['정보', '진로']):
            return 1
        return 2  # 기본 중2
    elif school_level_code == 4:  # 고등학교
        # 선택과목은 대부분 2-3학년
        common_subjects = ['한국사', '체육', '인공지능']
        if any(keyword in subject_str for keyword in common_subjects):
            return 1
        return 2  # 기본 고2
    
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
    if pd.isna(current_grade):
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
        
        # 과목의 대상 학년 추출
        target_grade = extract_grade_from_subject(subject, school_code)
        
        if target_grade is None:
            # 학년 정보 없으면 전체 학생수 사용 (기존 방식)
            market_size = total_df[total_df['학교급코드'] == school_code]['학생수(계)'].sum()
        else:
            # 2026년도 해당 학년 컬럼
            grade_column = get_next_year_grade_column(target_grade, is_2026=True)
            
            if grade_column and grade_column in total_df.columns:
                # 해당 학년 학생수만 집계
                market_size = total_df[total_df['학교급코드'] == school_code][grade_column].sum()
            else:
                # 컬럼이 없으면 전체 사용
                market_size = total_df[total_df['학교급코드'] == school_code]['학생수(계)'].sum()
        
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
            market_size = region_schools['학생수(계)'].sum()
        else:
            grade_column = get_next_year_grade_column(target_grade, is_2026=True)
            if grade_column and grade_column in region_schools.columns:
                market_size = region_schools[grade_column].sum()
            else:
                market_size = region_schools['학생수(계)'].sum()
        
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
                market_size += total_df[total_df['학교급코드'] == school_code]['학생수(계)'].sum()
        elif school_code:
            market_size += total_df[total_df['학교급코드'] == school_code]['학생수(계)'].sum()
    
    share = (total_orders / market_size * 100) if market_size > 0 else 0
    
    return pd.Series({
        '주문부수': total_orders,
        '시장규모': market_size,
        '점유율(%)': share
    })
