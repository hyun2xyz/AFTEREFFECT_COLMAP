# 첫 영상 → 카메라 → 공간 기준 → 3D 파일

에이전트는 아래 전체를 한 번에 실행하지 않고, 학생과 현재 단계만 확인합니다.
`python`은 해당 프로젝트 venv의 실행 파일입니다. 출력 폴더는 매번 새로 만듭니다.
`work/`는 Git에서 제외됩니다. 큰 영상이라면 학생이 고른 다른 드라이브를 사용합니다.

## 1. 첫 샷 고르기

3~8초 정도의 정적인 실내/거리에서 카메라가 옆으로 조금 움직이는 샷으로 시작하세요.
텍스처가 있는 바닥·벽·가구와 시차가 도움이 됩니다. 순수 회전, 줌,
초광각, 롤링셔터 흔들림, 심한 모션블러, 화면 대부분을 차지하는 움직이는 사람은
첫 샷에 어렵습니다. 물리적인 초점거리/센서/미터 단위가 자동 복원되지는 않습니다.

```sh
python -B scripts/colmap_ae.py prepare --video /absolute/path/clip.mp4 --out work/shot01/prepared
```

기본 상한은 240프레임/긴 변 1600px입니다. 모든 프레임을 추출하며
상한 초과는 오류로 알려 줍니다. 에이전트가 임의로 영상을 자르거나 프레임을
줄이지 않습니다. 필요한 경우 학생과 상한/명시적 작업용 클립을 결정합니다.
가변 FPS·비정방 픽셀은 먼저 명시적인 작업용 변환이 필요합니다.

`manifest.json`에 원본 SHA256, 첫 원본 타임스탬프, 분수 FPS와 프레임 맵이
남습니다. 애펙 작업 컴프는 그 클립의 첫 프레임을 **0초로 재기준화**합니다.
원본 타임코드/오디오 편집을 자동 이식하지 않습니다.

## 2. CPU COLMAP을 백그라운드로

아래 명령은 구조 예시입니다. 에이전트가 학생 환경의 **실제 절대 경로**와
예상 시간/timeout을 채워 실행합니다. `--job` 폴더는 미리 만들지 않습니다.

```sh
python -B scripts/jobs.py start --job /absolute/work/shot01/job-solve-01 --estimate-minutes 10 --timeout-minutes 120 -- /absolute/venv/python -B /absolute/repo/scripts/colmap_ae.py solve --input /absolute/work/shot01/prepared --out /absolute/work/shot01/solve
```

Windows에서도 같은 Python 인자입니다. 예를 들어 실행 파일은
`C:\class\AFTEREFFECT_COLMAP\.venv\Scripts\python.exe`, 작업 폴더는
`D:\class-work\shot01\job-solve-01`처럼 실제 위치를 씁니다. 공백 경로는
셸에서 따옴표로 감싸며 스크립트 내부에서는 argv 배열로 전달합니다.

이 명령은 CPU 특징 추출/순차 매칭/복원 후 **이미지 undistortion**과 텍스트
모델까지 준비합니다. 고밀도 stereo 계산이나 학습 모델은 실행하지 않습니다.
여러 연결되지 않은 모델이 나오면 등록 프레임이 가장 많은 하나를 선택하고
`solution.json`에 모든 모델의 등록 수를 남깁니다. `--model-id`로 명시할 수도 있습니다.

[백그라운드 규칙](background.md)에 따라 일회성 예약 후 응답을 끝냅니다.

## 3. 재개해서 검사하고 내보내기

```sh
python -B scripts/jobs.py status --job /absolute/work/shot01/job-solve-01
python -B scripts/colmap_ae.py export --solution work/shot01/solve/solution.json --out work/shot01/ae01
```

`succeeded`는 Python 프로세스의 정상 종료입니다. 이어서 `solution.json`의
등록 비율, 실제 파일과 `report.json`을 확인해야 합니다. 미등록 프레임이
하나라도 있으면 JSX 내보내기를 막습니다. 상태를 완화하거나 보간으로 채우지
말고 샷·특징·매칭에서 원인을 찾는 다음 수업으로 갑니다.

내보내기는 왜곡 없는 PINHOLE을 사용합니다. 주점이 영상 중앙과 다르면
**이미지의 padding/평행 이동과 카메라 주점을 함께** 바꿉니다. 소수 픽셀 이동은
Pillow bicubic으로 작업용 복사본에만 적용하고 원본 intrinsics/이동량을 기록합니다.
Anamorphic/non-square fx/fy와 거의 수직인 AE POI 카메라는 이 starter에서 거부합니다.

만들어지는 핵심 파일:

| 파일 | 확인할 내용 |
| --- | --- |
| `review.jpg` | 처음·중간·끝 이미지 위 기준점 ID, 눈에 띄는 미끄러짐/잘못된 매칭 |
| `scene.json` | 카메라·점·RGB·렌즈·시간·좌표변환; 에이전트가 짧게 요약해 사용 |
| `report.json` | 등록 수와 내부 오차, AE/시각 검수의 미확인 상태 |
| `plates/` | 애펙 카메라와 정확히 같은 렌즈/크기의 작업용 이미지 |
| `import_scene.jsx` | 검토 후 실행할 애펙 스크립트 |

`review.jpg`는 수치 투영을 그린 진단입니다. 이것만으로 실제 AE에서 점이 붙는다고
확정할 수 없습니다. 애펙에서 중간 프레임과 가장자리까지 직접 확인합니다.

## 4. 애펙으로 가져오기

**File → Scripts → Run Script File**에서 생성된 JSX를 실행합니다.
새 폴더/컴프, 2D 작업용 이미지 시퀀스, 카메라, 기본 80개 RGB 가이드 도형,
`WORLD_ORIGIN`이 생깁니다. 이전 프로젝트는 저장/종료하지 않습니다.
가이드 도형은 배달 렌더에서 제외되는 guide layer입니다. 무거운 전체 점 구름이 아닙니다.
RGB 값은 보존하지만 프로젝트 색 관리/노출에 따른 화면 차이는 별도 확인합니다.

모든 소스 프레임에 측정한 카메라 키를 넣고 HOLD로 설정합니다.
서브프레임 모션블러나 슬로모션에 필요한 연속 카메라 추정은 다음 단계입니다.
원본 카메라를 유지하면 제공한 모델을 영상 위에 합성할 수 있습니다.
애펙 카메라를 새 경로로 바꿔도 2D 배경 영상이 3D로 재생성되는 것은 아닙니다.

## 5. 바닥/벽과 모델을 한 번에 하나씩

에이전트는 실제 프레임과 ID 오버레이를 보고 학생과 같은 평면의 세 점을
고릅니다. 점만 보고 바닥/벽을 자동 단정하지 않습니다. 서로 멀고 일직선이
아닌 삼각형이 좋습니다. 세 점은 이 작은 가이드 세트의 ID입니다.

```sh
python -B scripts/colmap_ae.py anchor --scene work/shot01/ae01/scene.json --points 17,42,91 --plane floor --model /absolute/path/object.glb --model-scale 25 --out work/shot01/ae02-floor
```

`17,42,91`은 예시이므로 실제 `review.jpg`/`scene.json`의 ID로 바꿉니다.
첫 점은 원점, 두 번째 점은 X 방향, 세 번째 점은 평면의 안쪽 방향입니다.
바닥은 XZ, 벽은 XY 평면이 됩니다. 세 점의 순서를 바꾸면 위/아래가 뒤집힐
수 있으므로 카메라와 실제 화면을 보고 확인합니다. 변환은 점과 카메라에
함께 적용되므로 원래 화면 투영은 유지됩니다.

알고 있는 길이를 쓰려면 `--baseline-units 100`처럼 첫째→둘째 점 사이를
100 작업 단위로 정합니다. 이것이 자동 미터 복원이라는 뜻은 아닙니다.
모델은 원점에 배치하는 출발점이며 모델 자체 피벗·축·스케일·회전과 지면
접촉은 학생이 화면에서 맞춥니다. 자동 occlusion/그림자/조명은 만들지 않습니다.

새 JSX는 새 컴프를 만들므로 이전 결과를 비교하며 남길 수 있습니다.
수업 후 에이전트는 `work/shot01/next.md`에 검증한 것, 남은 문제, 다음 한
단계만 기록합니다. 전역 스킬을 스스로 늘리거나 전체 기능을 미리 구현하지 않습니다.
