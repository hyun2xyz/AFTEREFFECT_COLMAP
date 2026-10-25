# 검증 범위

2026-10-25 KST 기준. 저장소 코드와 실제 호스트에서 확인한 범위입니다.
다른 프로젝트의 성공을 가져오거나, 등록률을 실제 영상 고정으로 해석하지 않습니다.

## Python와 실제 계산

- 선택 추적 의존성을 설치한 Mac Python 3.13.7에서 unittest 33개 통과.
  좌표·렌즈·주점·RGB·전체 PLY 보존·멀리 있는 점의 가시 크기·heldout 실패 거부,
  마스크/Unicode·관측점 분리·독립 job/timeout/예약 ID를 검사합니다.
- Mac COLMAP 3.12.4 CPU의 기본 SIFT 경로는 12프레임 합성 샷에서 실제 복원했습니다.
  Windows 4.2.1 CPU도 같은 합성 경로를 실제 실행한 기록이 있습니다.
- 새 연속 추적: Mac COLMAP 3.12.4에서 새 DB/importer부터 12/12프레임까지 실제 확인.
  train 452 / unused 113점, unused median 0.0676px·p95 0.2446px, 양의 깊이 100%.
- 실제 96프레임 정적 건물 샷을 **재사용 코드**로 다시 실행: 96/96, 246점, 약 14.6초.
  unused 62점 median 0.1305px·p95 0.5661px, 양의 깊이 100%. 준비 해상도 1600×900,
  f=1920 고정과 작은 각도는 이 샷의 가정이며 다른 영상의 기본값이 아닙니다.
- 이전 SIFT 결과는 96개 카메라가 나왔어도 독립 영상 검사에서 크게 미끄러져
  거부했습니다. 통과하지 못한 결과를 보여주려고 export 문턱을 낮추지 않았습니다.

[CI](https://github.com/hyun2xyz/AFTEREFFECT_COLMAP/actions)는 macOS/Windows ×
Python 3.12/3.13 회귀와 Windows 공식 COLMAP 4.2.1 nocuda의 기본/연속 추적
native smoke를 실행합니다. 학생은 사용하는 커밋의 결과를 확인합니다.
CI에서 실제 Windows Adobe 앱을 실행한 것은 아닙니다.

## 실제 After Effects

Mac AE 26.3x87에서 Python 생성 JSX를 File→Scripts→Run Script File로 실행했습니다.
AE MCP나 별도 서버를 사용하지 않았습니다.

- 전체 246개 RGB 점이 한 collapsed 3D precomp에 들어갑니다. 메인 레이어 4개:
  카메라 / 점 구름 / 원본 영상(처음 off) / 검은 배경.
- 원래 3D 중심과 RGB는 유지하고 표식 크기만 첫 카메라에서 6px가 되게 조정합니다.
  고정 5월드 단위로는 1픽셀 미만이던 먼 점이 실제 렌더에서 보임을 확인했습니다.
  첫 프레임의 점 중심 246개에서 원본 RGB와 native PNG의 채널 값이 일치했습니다.
- nested 점 80개 × 첫/중간/끝 = 240개 native toComp 검사:
  max 0.000355px / p95 0.000332px. 검수용 텍스트 레이어를 남기지 않았습니다.
- 처음/중간/끝 실제 native PNG와 검은 배경의 점 표시를 확인했습니다.
  전체 실시간 재생이나 Windows AE 실행을 확인했다는 뜻은 아닙니다.
- 이전 컴프/사용자 변경을 보존하고 별도 AEP로 저장했습니다. 일반 importer는
  학생 프로젝트에 새 항목만 추가하며 자동 저장/닫기를 하지 않습니다.
- 초기 anchor+cube OBJ의 Advanced 3D 가져오기/좌표 전달도 확인했습니다.
  학생이 주는 새 모델의 피벗·크기·접지는 그 모델로 별도 검수합니다.

## 백그라운드와 선택 모델

실제 분리 계산→응답 종료→같은 채팅의 native 일회성 예약 재개→자기 예약 삭제
확인→같은 ID의 로컬 binding 정리까지 실행했습니다. `jobs.py wakeup` 자체를
예약기라고 표현하지 않습니다. 앱/OS별 실제 scheduler가 없으면 자동 재개는 보장하지 않습니다.

COLMAP/LK에는 학습 가중치가 없습니다. 선택 Laya는 고정 revision/라이선스 안내와
missing-model 거부를 확인했고, 이 저장소에서 실제 가중치를 받아 추론하지는 않았습니다.

## 학생의 다음 검수

```sh
python -B tests/generate_ae_check.py --scene /absolute/export/scene.json --out /absolute/export/check_projection.jsx
```

같은 scene의 importer 실행 후 해당 메인 컴프를 선택해 검수 JSX를 실행합니다.
실제 자식 점 중심을 상위 collapsed precomp를 통해 비교하고 alert/comment에 결과를
남깁니다. 임시 null과 새로 만든 미사용 source를 제거하며 텍스트 레이어를 추가하지 않습니다.

좌표 전달·unused 영상 적합성 통과는 물리 렌즈, 미터 단위 깊이, 자동 바닥/벽 의미,
고밀도 표면, 새 시점 배경 생성이나 물체 가림·조명·접지의 증명이 아닙니다.
