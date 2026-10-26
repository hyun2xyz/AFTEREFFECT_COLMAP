# 검증 범위

2026-10-26 KST 기준. 소스 검사, 실제 계산, 실제 Adobe 호스트 확인을 구분합니다.
Mac 성공을 Windows AE 성공으로 해석하지 않습니다.

## 새 컴퓨터 준비

- Python 표준 라이브러리만으로 setup helper를 실행했고, helper 검사 10개를 포함한
  회귀 검사 49개가 Mac Python 3.13.7에서 통과했습니다.
- Git 없는 별도 폴더에 helper/requirements만 복사해 실제 configure → 새 `.venv`와
  Pillow 설치 → check를 실행했습니다. NumPy/OpenCV와 전역 설정 없이 통과했습니다.
  완전히 빈 OS에서 Homebrew/Windows 설치기의 모든 화면을 실행한 검증은 아닙니다.
- 소스 ZIP은 실행 파일·개인 `tools.local.json`·venv·학생 영상·AEP·가중치를 포함하지
  않습니다. Adobe 설치·로그인·라이선스와 실제 호스트 확인은 별도 단계입니다.

## Python와 native COLMAP

- Mac COLMAP 3.12.4 CPU의 기본 SIFT와 연속 LK 경로를 실제 합성 샷에서 실행했습니다.
  연속 추적은 12/12, train452 / unused113점, median0.0676px·p950.2446px였습니다.
- 공용 `enrich_cloud.py`의 **새 CPU SIFT** 경로: 합성12/12, native9,740점,
  카메라 변화0, native PLY 그대로 복사, 표시 샘플링 없이 전체 GLB export 통과.
- 실제96프레임 샷에서 **공용 DB 재사용 경로**를 다시 실행했습니다. 모든 입력 RGB
  픽셀이 같은지 먼저 확인하고 21.618초에 native55,368점을 얻었습니다.
  기존 카메라/렌즈를 유지했고 원래 DB는 수정하지 않았습니다.
- 이 카메라의 별도 unused62점 검수는 median0.1305px / p950.5661px, 양의 깊이100%.
  f=1920과 작은 삼각측량 각도는 그 샷의 가정이며 다른 영상의 기본값이 아닙니다.
  카메라 검증을 계승한 것이며 새 SIFT 점 전부를 독립 heldout으로 검사한 것은 아닙니다.
- 이전 SIFT 모델은96카메라여도 실제 부착이 크게 미끄러져 거부했습니다.
  등록 수나 내부 오차만으로 샷 성공을 판정하지 않습니다.

[커밋별 CI](https://github.com/hyun2xyz/AFTEREFFECT_COLMAP/actions)는 macOS/Windows ×
Python3.12/3.13 검사를 실행합니다. Windows native job은 공식 COLMAP4.2.1 nocuda와
FFmpeg 준비 → setup helper의 로컬 venv/Pillow 설치 → 개인 경로 config → RGB 검사 파일
생성 → 기본 SIFT → 선택 tracking 설치/연속 추적 → 고정 카메라 점 추가/전체 GLB를
실행합니다. 해당 커밋의 실제 통과 여부를 확인하며, Windows Adobe 앱은 실행하지 않습니다.

## 실제 After Effects

Python이 생성한 공용 JSX를 Mac AE26.3x87의 **File → Scripts → Run Script File**로
직접 실행했습니다. AE MCP/별도 서버는 사용하지 않았습니다.

- 공용 전체 GLB importer: native55,368점,96프레임 카메라, 메인4레이어.
  원래 중심/RGB를 가진 작은 표식이며 점 사이에 표면을 만들지 않았습니다.
- 공용 RGB check의 중간 RGB5색을 native PNG에서 원래 채널 값과 정확히 대조했습니다.
  importer는 실제 모델 단위를 측정하고 cloud의 조명 영향을 끕니다.
- 공용 native QA240샘플: max0.000435px / p950.000345px, PASS.
  GLB의 실제 float32 인코딩 중심과 카메라를 비교합니다.
- 처음/중간/끝 native PNG와 실제 전체 점 표시를 확인했습니다. 전체 실시간 재생이나
  Windows AE 실행을 확인했다는 뜻은 아닙니다. 새 컴퓨터에서 RGB/단위 검사를 합니다.
- 이전 collapsed shape246점 경로도 native 투영/RGB를 확인한 기록이 있습니다.
  현재는 구형 AE용 명시적 제한 표시이며 기본 전체 표시와 구분합니다.
- 일반 importer/checker는 새 항목만 추가하고 저장·닫기·자동 렌더를 하지 않습니다.
  진단 PNG는 검수용 별도 로컬 스크립트로 저장했으며 기본 패키지 흐름에 넣지 않았습니다.

## 백그라운드와 선택 모델

실제 분리 계산 → 응답 종료 → 같은 채팅의 native 일회성 재개 → 정확한 자기 예약
삭제 확인 → 같은 ID의 로컬 binding 정리까지 실행한 기록이 있습니다. `jobs.py wakeup`
자체가 예약기는 아닙니다. 네이티브 예약 도구가 없으면 자동 재개를 보장하지 않습니다.

COLMAP/SIFT/LK에는 학습 가중치가 없습니다. 선택 Laya는 고정 revision/라이선스 안내와
missing-model 거부를 확인했지만 이 저장소에서 실제 가중치를 받아 추론하지 않았습니다.

좌표 전달·영상상 적합성 통과는 물리 렌즈, 미터 단위 깊이, 자동 바닥/벽 의미,
고밀도 표면, 새로운 시점의 배경 생성이나 물체 가림·조명·접지의 증명이 아닙니다.
