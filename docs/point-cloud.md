# 전체 RGB 점을 그대로 가져오기

기본 `export`는 COLMAP 모델의 **모든 점**을 `pointcloud.glb` 하나에 담습니다.
원래 좌표와 RGB는 `points.ply`에도 전부 보존합니다. 80개 ID의 `review.jpg`는
작은 검수 표본이며 실제 표시 점 수가 아닙니다. `report.json`의 `total_points`,
`display_cloud_points`, `full_cloud_display`를 함께 확인합니다.

## 첫 AE 호스트

영상이나 COLMAP 계산 전에도 작은 검사를 만들 수 있습니다. 이 단계는 Pillow만 필요합니다.

```sh
python -B scripts/pointcloud.py --rgb-check --out work/rgb-first
```

AE24.1+에서 생성된 **`check_rgb.jsx`**를 Run Script File로 먼저 실행합니다.
다섯 쌍에서 왼쪽은 원래 RGB 기준, 오른쪽은 3D 표식입니다. 위치·크기·색을
비교합니다. 다른 색이면 프로젝트 색 관리·작업 색공간·노출과 AE 버전을 확인합니다.
전역 설정이나 학생의 다른 프로젝트를 자동으로 바꾸지 않습니다.

그 다음 `import_scene.jsx`를 실행합니다. 기본 메인은 카메라 / 전체 RGB 모델 /
영상(처음 off) / 검은 배경의 4레이어입니다. GLB 단위는 실제 AE에서 측정해 보정하고,
점구름의 **Accepts Lights/Accepts Shadows/Casts Shadows**를 꺼서 원래 색을 유지합니다.
GLB·plates·JSX를 함께 보관합니다. 자동 저장·닫기·렌더나 AE MCP는 없습니다.

점마다 작은 팔면체 표식이 있지만 중심·깊이·RGB를 변경하거나 점 사이를 면으로
잇지 않습니다. GLB의 float32 표시 정밀도와 원본 PLY 좌표는 구분합니다.
`--point-size 2`로 표식 지름만 줄일 수 있습니다. 희소 점 구름이며 dense stereo로
표면을 복원하거나 새 시점의 영상·실제 미터 깊이를 만든 것은 아닙니다.

첫/중간/끝의 실제 AE 투영 검수는 다음 JSX로 확인합니다. 파일 쓰기 권한은 필요하지 않습니다.

```sh
python -B tests/generate_ae_check.py --scene work/shot/ae01/scene.json --out work/shot/ae01/check_projection.jsx
```

같은 컴프를 선택하고 실행합니다. GLB의 실제 인코딩 중심과 native 모델 단위/카메라를
검사합니다. RGB 기준 비교와 영상 위 고정 검수는 별도로 필요합니다.

## 실제 점이 더 필요할 때

이미 COLMAP 점이 충분하다면 추가 계산하지 않습니다. 적은 점만 나온 유효한
카메라에서 더 복원하려면 **그 카메라를 고정한 채** `enrich_cloud.py`를 실행합니다.
기본은 검증된 undistorted 이미지에서 새 CPU SIFT를 추출하고 매칭한 뒤 공식
`point_triangulator`로 삼각측량하고 색을 추출합니다. 학습 가중치는 없습니다.

아래 경로는 에이전트가 실제 절대 경로로 채우는 구조 예시입니다.
Mac의 venv Python은 `.venv/bin/python`, Windows는 `.venv\Scripts\python.exe`입니다.

```sh
python -B scripts/jobs.py start --job /absolute/work/shot/job-enrich-01 --estimate-minutes 10 --timeout-minutes 120 -- /absolute/venv/python -B /absolute/repo/scripts/enrich_cloud.py --solution /absolute/work/shot/solve/solution.json --out /absolute/work/shot/enriched
```

예상 시간은 첫 실행이면 미확인으로 알리고 보수적인 첫 확인을 고릅니다.
[백그라운드/일회성 재개](background.md)를 사용해 LLM이 대기 조회를 반복하지 않습니다.
완료 후 새 `solution.json`으로 일반 `export`를 실행합니다.

```sh
python -B scripts/colmap_ae.py export --solution work/shot/enriched/solution.json --out work/shot/ae-full
```

기존 SIFT를 재사용하려면 `--database /absolute/old/database.db`와
`--database-images /absolute/old/images`를 함께 지정합니다. 모든 프레임이 현재
카메라의 undistorted 이미지와 **실제 RGB 픽셀까지 같은지** 검사합니다. 렌즈 보정으로
이미지가 달라졌다면 DB를 억지로 쓰지 않고 기본 새 SIFT 경로를 택합니다.
원본 DB는 수정하지 않고 백업 복사본만 사용합니다.

모든 카메라/렌즈가 유지됐는지 검사하고, 기존 temporal heldout은 카메라에 관한
검증으로 계승합니다. 추가된 모든 SIFT 점을 새 독립 heldout으로 검증했다는 뜻은
아닙니다. 기본 최소 삼각측량 각도는 1.5°이며, 이미 검토한 temporal 결과의 각도가
있으면 그 값을 계승합니다. 샷 근거 없이 더 낮추거나 오차 기준을 완화하지 않습니다.
어떤 영상에서나 점 수가 늘어난다고 보장하지 않으며 실제 결과 수를 보고합니다.

이 경로는 CPU sparse triangulation입니다. 기본 COLMAP dense stereo는 CUDA가
필요하므로 Mac/Windows nocuda에서 같은 단계라고 설명하지 않습니다.
[COLMAP known-camera 절차](https://colmap.github.io/faq.html#reconstruct-sparse-dense-model-from-known-camera-poses).

## 구형 AE의 명시적 대안

```sh
python -B scripts/colmap_ae.py export --solution work/shot/solve/solution.json --out work/shot/ae-shapes --cloud-renderer shapes --cloud-limit 2000
```

이 모드만 collapsed3D shape precomp로 제한 표시합니다. 전체 PLY는 그대로 남지만,
학생에게 모든 점이 표시된다고 말하지 않습니다. 모드를 바꾸어 실패를 숨기지 않습니다.
