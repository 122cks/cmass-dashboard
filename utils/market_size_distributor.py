"""
총판별 시장 규모 계산 모듈

학생수 CSV의 담당총판 정보를 활용하여 총판별 정확한 시장 규모를 계산합니다.
"""

import pandas as pd
import numpy as np


def calculate_distributor_market_size(total_df, order_df, distributor_df):
    """
    총판별 시장 규모 계산
    
    Args:
        total_df: 학생수 데이터 (담당총판 정보 포함)
        order_df: 주문 데이터
        distributor_df: 총판 정보 (총판명(공식) 포함)
    
    Returns:
        총판별 시장 규모 DataFrame
    """
    results = []
    
    # 담당총판_공식 컬럼이 있는지 확인
    dist_col = '담당총판_공식' if '담당총판_공식' in total_df.columns else '담당총판'
    
    if dist_col not in total_df.columns:
        return pd.DataFrame()
    
    # 총판별로 담당 학교 정보 추출
    for dist_name, dist_schools in total_df.groupby(dist_col, dropna=False):
        if pd.isna(dist_name):
            continue
        
        # 중학교 시장 규모 (1, 2학년)
        middle_schools = dist_schools[dist_schools['학교급코드'] == 3]
        middle_market = middle_schools['1학년 학생수'].sum() + middle_schools['2학년 학생수'].sum()
        
        # 고등학교 시장 규모 (1, 2학년)
        high_schools = dist_schools[dist_schools['학교급코드'] == 4]
        high_market = high_schools['1학년 학생수'].sum() + high_schools['2학년 학생수'].sum()
        
        # 총 시장 규모
        total_market = middle_market + high_market
        
        # 주문 데이터에서 해당 총판의 주문량 계산
        if '총판' in order_df.columns:
            dist_orders = order_df[order_df['총판'] == dist_name]
            total_orders = dist_orders['부수'].sum() if not dist_orders.empty else 0
            total_amount = dist_orders['금액'].sum() if '금액' in dist_orders.columns and not dist_orders.empty else 0
            
            # 학교 수
            school_code_col = None
            for col in ['정보공시학교코드', '정보공시 학교코드', '학교코드']:
                if col in dist_orders.columns:
                    school_code_col = col
                    break
            
            num_schools = dist_orders[school_code_col].nunique() if school_code_col and not dist_orders.empty else 0
        else:
            total_orders = 0
            total_amount = 0
            num_schools = 0
        
        # 점유율 계산
        share_pct = (total_orders / total_market * 100) if total_market > 0 else 0
        
        results.append({
            '총판명': dist_name,
            '중학교_시장규모': middle_market,
            '고등학교_시장규모': high_market,
            '전체_시장규모': total_market,
            '주문부수': total_orders,
            '주문금액': total_amount,
            '주문학교수': num_schools,
            '점유율(%)': share_pct,
            '담당_중학교수': len(middle_schools),
            '담당_고등학교수': len(high_schools),
            '담당_전체학교수': len(dist_schools)
        })
    
    return pd.DataFrame(results)


def calculate_subject_market_by_distributor(total_df, order_df, product_df):
    """
    총판별 + 과목별 시장 규모 계산
    
    Args:
        total_df: 학생수 데이터 (담당총판 정보 포함)
        order_df: 주문 데이터 (제품정보와 병합되어 학교급 정보 포함)
        product_df: 제품 정보
    
    Returns:
        총판별 과목별 시장 규모 DataFrame
    """
    results = []
    
    # 담당총판_공식 컬럼 확인
    dist_col = '담당총판_공식' if '담당총판_공식' in total_df.columns else '담당총판'
    
    if dist_col not in total_df.columns or '총판' not in order_df.columns:
        return pd.DataFrame()
    
    # 과목명 컬럼
    subject_col = '교과서명_구분' if '교과서명_구분' in order_df.columns else '교과서명'
    
    if subject_col not in order_df.columns:
        return pd.DataFrame()
    
    # 총판별 + 과목별로 그룹화
    for (dist_name, subject), group in order_df.groupby(['총판', subject_col], dropna=False):
        if pd.isna(dist_name) or pd.isna(subject):
            continue
        
        # 해당 총판이 담당하는 학교들
        dist_schools = total_df[total_df[dist_col] == dist_name]
        
        if dist_schools.empty:
            continue
        
        # 과목의 학교급 확인 (중등 vs 고등)
        school_level = None
        if '학교급' in group.columns:
            # 가장 많은 주문이 발생한 학교급 사용
            school_level = group['학교급'].mode()[0] if not group['학교급'].mode().empty else None
        
        # 시장 규모 계산
        if school_level == '중학교' or '[중등]' in str(subject):
            # 중학교 1, 2학년 학생수
            middle_schools = dist_schools[dist_schools['학교급코드'] == 3]
            market_size = middle_schools['1학년 학생수'].sum() + middle_schools['2학년 학생수'].sum()
            school_level_text = '중등'
        elif school_level == '고등학교' or '[고등]' in str(subject):
            # 고등학교 1, 2학년 학생수
            high_schools = dist_schools[dist_schools['학교급코드'] == 4]
            market_size = high_schools['1학년 학생수'].sum() + high_schools['2학년 학생수'].sum()
            school_level_text = '고등'
        else:
            # 학교급을 알 수 없는 경우 중등+고등 전체
            middle_schools = dist_schools[dist_schools['학교급코드'] == 3]
            high_schools = dist_schools[dist_schools['학교급코드'] == 4]
            market_size = (middle_schools['1학년 학생수'].sum() + middle_schools['2학년 학생수'].sum() +
                          high_schools['1학년 학생수'].sum() + high_schools['2학년 학생수'].sum())
            school_level_text = '전체'
        
        # 주문 정보
        total_orders = group['부수'].sum()
        total_amount = group['금액'].sum() if '금액' in group.columns else 0
        
        # 학교 수
        school_code_col = None
        for col in ['정보공시학교코드', '정보공시 학교코드', '학교코드']:
            if col in group.columns:
                school_code_col = col
                break
        
        num_schools = group[school_code_col].nunique() if school_code_col else 0
        
        # 점유율
        share_pct = (total_orders / market_size * 100) if market_size > 0 else 0
        
        results.append({
            '총판명': dist_name,
            '과목명': subject,
            '학교급': school_level_text,
            '시장규모': market_size,
            '주문부수': total_orders,
            '주문금액': total_amount,
            '주문학교수': num_schools,
            '점유율(%)': share_pct
        })
    
    return pd.DataFrame(results)
