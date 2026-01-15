# CRG – Coding Rules & Guidelines

## 1. 언어 및 환경
- Python 3.9 이상
- Windows 전용 스크립트

## 2. 라이브러리 사용 규칙
- GUI: tkinter (표준 라이브러리)
- Screen Capture: mss
- Image 처리: Pillow
- 빌드: pyinstaller

## 3. 코드 구조
- 단일 실행 스크립트 (`screen_region_capture.py`)
- UI 로직과 캡쳐 로직은 클래스 단위로 분리
- 전역 상태 최소화 (영역 정보는 App 인스턴스에 유지)

## 4. 명명 규칙
- 함수/변수: snake_case
- 클래스: PascalCase
- 파일명: 소문자 + 언더스코어

## 5. 예외 처리
- 폴더 선택 실패 시 프로그램 종료
- 캡쳐 실패 시 메시지 박스로 사용자에게 명시적 알림

## 6. 좌표 처리 규칙
- mss.monitors[0] 기준 가상 화면 좌표 사용
- 오버레이 좌표 → 실제 화면 좌표 오프셋 보정 필수

## 7. UI 규칙
- 모든 UI 문구는 한글
- 사용자 행동에 대한 상태 메시지 항상 표시
