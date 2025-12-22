import os
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ORDER_FILE = os.path.join(BASE_DIR, '씨마스_22개정 주문현황_학교코드총판코드.csv')
DISTRIBUTOR_FILE = os.path.join(BASE_DIR, '총판정보.csv')
TARGET_FILE = os.path.join(BASE_DIR, '22개정 총판별 목표.csv')


def _normalize_code(code_val) -> str:
    if pd.isna(code_val):
        return ''
    s = str(code_val).strip().replace(',', '').strip()
    if s.endswith('.0'):
        s = s[:-2]
    try:
        f = float(s)
        if f.is_integer():
            s = str(int(f))
    except Exception:
        pass

    # 핵심: 4자리 코드 유지 (선행 0 보호)
    if s.isdigit() and 0 < len(s) < 4:
        s = s.zfill(4)
    return s


def _read_csv_auto(path: str, *, dtype=None):
    try:
        return pd.read_csv(path, encoding='cp949', low_memory=False, dtype=dtype)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding='utf-8', low_memory=False, dtype=dtype)


def build_map(dist: pd.DataFrame):
    if dist.empty:
        return {}
    code_col = '숫자코드' if '숫자코드' in dist.columns else ('총판코드' if '총판코드' in dist.columns else None)
    if not code_col or '총판명(공식)' not in dist.columns:
        return {}

    m = {}
    for _, r in dist.iterrows():
        code = _normalize_code(r.get(code_col))
        name = r.get('총판명(공식)')
        if pd.isna(name) or code == '':
            continue
        m[code] = str(name).strip()
    return m


def check(label: str, orders: pd.DataFrame, dist: pd.DataFrame):
    if '총판코드' not in orders.columns:
        print(f'[{label}] ERROR: orders has no 총판코드')
        return

    m = build_map(dist)
    orders_norm = orders['총판코드'].apply(_normalize_code)
    unique_codes = sorted([c for c in orders_norm.unique() if c != ''])
    mapped = set(m.keys())
    unmapped = [c for c in unique_codes if c not in mapped]

    print(f'\n[{label}]')
    print(' orders unique codes:', len(unique_codes))
    print(' dist map size     :', len(mapped))
    print(' unmapped unique   :', len(unmapped))
    print(' sample unmapped   :', unmapped[:30])

    # leading zero diagnostics
    raw_series = orders['총판코드'].astype(str)
    leading_zero = raw_series.str.match(r'^0\d{3}$', na=False).sum()
    dot_zero = raw_series.str.contains(r'\.0$', na=False).sum()
    print(r' raw leading-zero count (^0\d{3}$):', int(leading_zero))
    print(' raw endswith .0 count           :', int(dot_zero))


def main():
    print('Files:')
    print('-', ORDER_FILE)
    print('-', DISTRIBUTOR_FILE)

    # (A) app.py처럼 dtype 없이 읽기 (배포 환경에서 흔한 문제: 추론으로 숫자화)
    orders_a = _read_csv_auto(ORDER_FILE, dtype=None)
    dist_a = _read_csv_auto(DISTRIBUTOR_FILE, dtype=None)
    check('A:infer-types', orders_a, dist_a)

    # (B) 코드 컬럼만 str로 고정해서 읽기 (해결안)
    orders_dtype = {'총판코드': str, '정보공시학교코드': str}
    dist_dtype = {'숫자코드': str, '총판코드': str}
    orders_b = _read_csv_auto(ORDER_FILE, dtype=orders_dtype)
    dist_b = _read_csv_auto(DISTRIBUTOR_FILE, dtype=dist_dtype)
    check('B:dtype-code-cols', orders_b, dist_b)


if __name__ == '__main__':
    main()

