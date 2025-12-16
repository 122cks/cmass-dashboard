# CMASS 대시보드 배포 안내

이 프로젝트는 전체 시장 데이터(`2025년도_학년별·학급별 학생수(초중고)_전체.csv`)와 주문 데이터(`씨마스_22개정 주문현황_학교코드총판코드.csv`)를 이용해 교과/과목별, 지역별, 총판별 점유율을 보여주는 Streamlit 대시보드입니다.

## 로컬 실행 (권장 테스트 방법)
1. 이 repo 루트에서 가상환경을 생성하고 활성화하세요 (선택사항이지만 권장).

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2. 대시보드 실행 (수동):

```powershell
.\.venv\Scripts\python.exe -m streamlit run dashboard/app.py
```

3. 또는 파일에서 `run_dashboard.bat`을 더블클릭하면 자동으로 venv 내의 `python.exe`로 Streamlit을 실행합니다.

## 웹에 배포 (추천: Streamlit Community Cloud)
1. GitHub에 이 폴더(또는 repo)를 푸시합니다.
2. https://share.streamlit.io 에 접속하여 GitHub 계정으로 로그인 후 "New app"을 선택합니다.
3. 레포지토리, 브랜치, `dashboard/app.py` 경로를 선택하고 배포합니다.

Streamlit Cloud는 `requirements.txt`를 자동으로 읽어 필요한 패키지를 설치합니다.

## 로컬을 웹에 노출 (대체안, 임시 공유)
ngrok를 이용해 로컬 포트를 공개하면 브라우저에서 외부 접근이 가능합니다.

1) `pyngrok` 설치 (이미 requirements.txt에 포함됨):

```powershell
pip install pyngrok
```

2) 로컬에서 Streamlit을 실행한 뒤(예: 기본 포트 8501), ngrok로 터널을 엽니다:

```powershell
pyngrok http 8501
```

3) pyngrok이 제공하는 공개 URL을 복사하여 공유합니다.

주의: NGROK은 공개용으로는 임시이며 보안·지속성에 한계가 있습니다.

## 문제 해결 팁
- `streamlit` 명령이 인식되지 않으면 가상환경을 활성화했는지 확인하거나, `run_dashboard.bat`처럼 venv의 `python.exe`로 직접 호출하세요.
- 파일 인코딩 문제(CP949/UTF-8)가 발생하면 `dashboard/app.py`에서 이미 처리하도록 되어 있습니다.

원하시면 제가 GitHub에 푸시할 수 있게 도와드리거나, 배포 과정에서 생기는 오류를 직접 확인해 드리겠습니다.
