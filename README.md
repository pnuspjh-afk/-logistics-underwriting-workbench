# Logistics Underwriting Workbench

물류센터 대체투자 언더라이팅 워크벤치

## 개요
이 프로젝트는 물류센터 딜의 임대수익·공실·금리·Capex 가정을 자유롭게 변경하며 NOI, DSCR, LTV, IRR 등을 계산하고, 투자 포인트와 실사(DD) 체크리스트까지 자동 생성해주는 심사역용 분석 툴입니다.

## 주요 기능
- **Underwriting Engine**: 한국 물류센터 실무 로직 기반의 수지 분석 (NOI, DSCR, IRR 등)
- **Scenario Analysis**: Base / Downside / Upside 시나리오별 민감도 분석 및 시각화
- **Investment Memo Engine**: 분석 결과를 바탕으로 투자 심의용 국문 요약문 자동 생성
- **DD Checklist Engine**: 자산 특성 및 리스크 지표에 따른 맞춤형 실사 체크리스트 제공

## 설치 및 실행 방법
1. 필수 패키지 설치:
   ```bash
   pip install -r requirements.txt
   ```
2. 앱 실행:
   ```bash
   streamlit run app.py
   ```

## 파일 구조
- `app.py`: Streamlit 메인 앱 (UI)
- `calculator.py`: 수지 분석 및 IRR 계산 엔진
- `memo_engine.py`: 투자 메모 생성 엔진
- `dd_engine.py`: 실사 체크리스트 생성 엔진
- `sample_assets.csv`: 샘플 물류센터 데이터
- `requirements.txt`: 의존성 라이브러리 목록
