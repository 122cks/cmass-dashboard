import ast
import sys

files_to_test = [
    'pages/1_📚_교과과목별_분석.py',
    'pages/2_🗺️_지역별_분석.py',
    'pages/8_🎯_목표_대비_달성률.py',
    'pages/9_📅_연도별_분석.py'
]

all_ok = True
for filepath in files_to_test:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            ast.parse(f.read())
        print(f"✅ {filepath} - OK")
    except SyntaxError as e:
        print(f"❌ {filepath} - SyntaxError at line {e.lineno}: {e.msg}")
        all_ok = False
    except Exception as e:
        print(f"❌ {filepath} - Error: {e}")
        all_ok = False

if all_ok:
    print("\n✅ 모든 파일 구문 검사 통과!")
else:
    print("\n❌ 일부 파일에 오류가 있습니다.")
    sys.exit(1)
