# 검증 기록

기준일: 2026-10-25 (KST). 아래는 이 저장소에서 직접 확인한 범위입니다.
다른 프로젝트의 성공 기록을 이번 starter의 결과로 옮기지 않습니다.

## 로컬 Python / 실제 COLMAP

- macOS arm64, Python 3.13.7, Pillow 12.3.0, COLMAP 3.12.4(no CUDA), FFmpeg 7.1.1.
- 회귀 검증: 좌표계·평면 정렬·주점 보정·프레임 누락 거부·RGB 보존·출력 보호,
  독립 프로세스 생존·동시 중복 거부·timeout과 자손 정리·Unicode 경로·예약 ID 분리.
  Python unittest 21개 통과.
- 실제 COLMAP: 난수 텍스처의 여러 깊이 평면을 카메라 이동/회전으로 만든
  12프레임 합성 영상. `prepare → CPU solve → undistort → export` 완료.
  12/12프레임 등록, 희소 점 9,701개, 가이드 80개.
  COLMAP 내부 점 오차 중앙값 약 0.092px, 계산 약 19초.
- 첫 두 합성 장면은 시차/자가 보정 조건이 부족해 복원이 실패하거나 불완전했고
  내보내기를 차단했습니다. 최종 fixture의 카메라 기하를 바꿨으며 solver의
  품질 문턱을 낮춰 통과시키지 않았습니다. 실패 작업도 로컬에 보존했습니다.

숫자는 작은 합성 입력의 측정치입니다. 실제 학생 영상의 시간·등록률·물리 정확도를
보장하지 않습니다. `review.jpg`의 수치 오버레이는 AE 내 실제 attachment 검증과 다릅니다.

재현하려면 COLMAP/FFmpeg를 준비한 뒤 새 절대 경로로 실행합니다.

```sh
python -B scripts/jobs.py start --job /absolute/work/job-smoke --estimate-minutes 3 --timeout-minutes 15 -- /absolute/venv/python -B /absolute/repo/tests/smoke_colmap.py --out /absolute/work/smoke
```

## OS / 앱 / 예약 / 선택 모델

| 항목 | 상태 |
| --- | --- |
| Mac CPU COLMAP 전체 경로 | 위 합성 입력에서 실제 통과 |
| macOS/Windows Python 회귀 | Python 3.12/3.13 네 조합에서 21개씩 통과 ([코드 커밋 877d334 CI](https://github.com/hyun2xyz/AFTEREFFECT_COLMAP/actions/runs/40113353777)) |
| Windows COLMAP 바이너리 | 공식 x64 nocuda 설치 경로 안내; 이 Mac에서 실행한 것으로 보고하지 않음 |
| 실제 After Effects JSX | Mac AE 26.3x87에서 Run Script File로 실제 가져오기 완료(MCP 미사용) |
| 실제 AE 카메라 투영 | 3개 프레임 × 80개 점 = 240개 toComp 비교, max 0.000147px / p95 0.000121px 통과 |
| 벽 기준 + 3D 파일 가져오기 | 생성한 cube OBJ로 anchor→JSX 실행; USER_MODEL과 Advanced 3D 전환 확인 |
| 평면 정렬 후 Advanced 3D 투영 | 같은 240개 비교, max 0.000596px / p95 0.000448px 통과 |
| 실제 학생 영상 합성/3D 모델 축·피벗·접지 | 학생 입력으로 별도 검수 필요 |
| 일회성 예약으로 종료된 채팅 재개→자기 삭제 | 스킬/도구별 계약 작성; 이번 실행에서 실제 예약을 생성하지 않음 |
| Laya 모델 | 고정 revision/파일 목록/Apache-2.0 모델 카드 확인, 가중치 미다운로드·실제 추론 미실행 |

백그라운드 작업은 문서 작성 중 실제 독립 프로세스로 진행했습니다.
스케줄러가 아닌 `jobs.py wakeup`을 실제 예약 생성으로 표현하지 않습니다.
COLMAP 계산 동안 독립적인 문서/코드 작업이 남아 있어 이번에는 그 일을 계속했습니다.

## 선택: 애펙 안에서 좌표 전달 검사

```sh
python -B tests/generate_ae_check.py --scene /absolute/export/scene.json --out /absolute/export/check_projection.jsx
```

먼저 같은 scene의 `import_scene.jsx`를 애펙에서 실행한 뒤, 해당 컴프를 선택하고
검사용 JSX를 Run Script File로 실행합니다. Python의 예상 화면 좌표와 AE 자체
`toComp` 결과를 비교하고 결과를 guide text layer/컴프 comment에 남깁니다.
측정용 임시 null은 제거하며 프로젝트 저장/파일 쓰기 권한 변경은 하지 않습니다.
이것은 좌표 전달 검사이며 원본 영상의 실제 매칭 정확도/색 일치/모델 접지 검사가 아닙니다.
