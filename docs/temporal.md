# 순차 측정 추적이 필요한 짧은 샷

일반 `solve`의 SIFT가 끊겼고, 같은 정적인 무늬가 모든 프레임에 계속 보일 때만
`scripts/temporal_solve.py`를 다음 선택지로 사용합니다. 먼저 실제 영상을 보고
움직이는 물체·구름·반사·가림을 피할 수 있는지 판단합니다. 모든 프레임에서
살아남은 코너만 사용하므로 큰 이동, 블러, 반복 무늬, 가림에는 실패할 수 있습니다.
실패하면 촬영/마스크/렌즈 가정을 검토합니다. 프레임 보간이나 자동 재실행은 없습니다.

## 필요한 입력

- `prepare`가 만든 **전체** `manifest.json`과 이미지. 일부 프레임만 고르지 않습니다.
- 준비된 이미지 해상도 기준의 고정 `--focal-px`. 초점거리를 임의로 고정해 얻은
  결과는 캘리브레이션이 아닙니다. 원본 해상도의 픽셀 초점거리를 알고 있다면
  준비본의 리사이즈 비율을 적용합니다. 줌 변화나 강한 렌즈 왜곡은 이 방법에 맞지 않습니다.
- 학생과 에이전트가 실제 첫 프레임에 대조해 검토한 `--mask`.
  마스크는 **첫 프레임에서 추적을 시작할 영역**이며 매 프레임 같은 화면 좌표에
  다시 적용하지 않습니다. 전체 샷에서 정적인 표면에 남는 영역을 고릅니다.

프로젝트 venv에 선택 의존성만 추가합니다. 기존 `requirements.txt`도 설치되어 있어야 합니다.

```sh
python -m pip install -r requirements-tracking.txt
```

NumPy와 OpenCV CPU 추적을 사용하며 ML 모델이나 가중치를 다운로드하지 않습니다.

## 마스크

PNG는 준비본과 정확히 같은 크기의 흑백 grayscale 이미지입니다. 흰색 `255`는 허용,
검은색 `0`은 제외이며 알파·중간 회색은 받지 않습니다. 자동 리사이즈하지 않습니다.

JSON은 다음 형식입니다. 아래 좌표는 형식 예시이며 **학생 영상에 맞게 다시 그립니다**.

```json
{
  "width": 640,
  "height": 480,
  "polygons": [[[30, 120], [290, 90], [300, 450], [30, 450]]],
  "exclude_polygons": [[[100, 200], [150, 200], [150, 270], [100, 270]]]
}
```

좌표는 준비본의 왼쪽 위 픽셀 중심 `(0,0)`부터 `[x,y]`, 오른쪽·아래가 양수입니다.
범위는 `0..width-1`, `0..height-1`입니다. `polygons`의 합집합에서 선택적인
`exclude_polygons`를 뺍니다. 건물·전경·배경·구름을 자동 분류하지 않으며,
구름과 움직이는 전경의 제외는 검토한 마스크에 명시해야 합니다.

## 실행

긴 계산은 [background.md](background.md)의 jobs/일회성 재개 절차를 따릅니다.
`FOCAL_PX` / `$FocalPx`에는 해당 준비본에서 확인한 숫자를 먼저 넣습니다.
아래 10분은 학생이 정하는 거친 예상치이며 실제 ETA가 아닙니다.

macOS, 저장소 루트의 zsh/bash:

```sh
.venv/bin/python -B scripts/jobs.py start \
  --job "$PWD/work/shot/temporal-job01" --estimate-minutes 10 --timeout-minutes 60 -- \
  "$PWD/.venv/bin/python" -B "$PWD/scripts/temporal_solve.py" \
  --manifest "$PWD/work/shot/prepared/manifest.json" \
  --mask "$PWD/work/shot/static-mask.json" --focal-px "$FOCAL_PX" \
  --min-angle 1.5 --out "$PWD/work/shot/solve-temporal01"
```

Windows, 저장소 루트의 PowerShell:

```powershell
$Root = (Get-Location).Path
$Python = Join-Path $Root '.venv\Scripts\python.exe'
& $Python -B scripts/jobs.py start `
  --job "$Root\work\shot\temporal-job01" --estimate-minutes 10 --timeout-minutes 60 -- `
  $Python -B "$Root\scripts\temporal_solve.py" `
  --manifest "$Root\work\shot\prepared\manifest.json" `
  --mask "$Root\work\shot\static-mask.json" --focal-px $FocalPx `
  --min-angle 1.5 --out "$Root\work\shot\solve-temporal01"
```

COLMAP 위치는 기존 `COLMAP_BINARY` 또는 `--colmap`으로 실제 실행 파일을 지정합니다.
job과 출력 폴더는 매번 새 경로입니다. 결과를 읽기 전 외부 예약 정리를 확인하고
status를 한 번 읽습니다. 진행 중이면 같은 계산을 유지하고 한 번만 나중에 재개합니다.

`--min-angle`은 삼각측량·점 필터·local BA의 최소 각도(도)이며 반드시 지정합니다.
기본 초기 쌍 각도는 COLMAP의 `16`도(`--init-min-angle`)입니다. 거리가 멀고
실제 시차가 작은 샷은 검토 후 두 값을 명시적으로 낮출 수 있습니다. 예를 들어
`--min-angle 0.1 --init-min-angle 0.25`는 먼 장면 한 건에서 성공한 **약한 깊이 가정**이며
다른 샷의 기본값이 아닙니다. 낮춘 각도는 `solution.json`의 `weak_depth:true`로 남습니다.
삼각측량 각도를 낮춰도 재투영 오차 기준은 완화하지 않습니다.

## 통과 기준과 결과

첫 프레임의 코너를 순차 LK로 추적하고 매 프레임 역방향 추적 오차 `<0.75px`,
LK 오차 `<15`와 이미지 경계를 확인합니다. 중간에 사라진 코너는 다시 심지 않습니다.
모든 프레임을 살아남은 코너 중 매 다섯 번째(약 20%)를 **feature/match 입력 전에**
분리합니다. solve/heldout 전체 경로는 `measured-tracks.npz`에 보존합니다.

공식 `database_creator`와 `feature_importer`가 현재 설치된 COLMAP 버전의 DB·카메라·
rig/frame을 만듭니다. 이전 샷의 DB는 필요하지 않습니다. 텍스트 importer에 필요한
0 descriptor는 위치 운반용이며 매칭에는 쓰지 않습니다. LK의 같은 점 인덱스만 raw로
import하고 COLMAP geometry verification을 거칩니다. 렌즈는 공유 `SIMPLE_PINHOLE`로
고정하며 초점거리·주점·왜곡을 BA에서 수정하지 않습니다.

OpenCV 위치에는 COLMAP의 픽셀 중심 규약에 맞춰 `+0.5px`를 적용합니다. 이 정리는
이전 샷 전용 실험보다 명시적이며 heldout 위치에도 똑같이 적용됩니다.
[COLMAP DB 규약](https://colmap.github.io/database.html).

통과하려면 모든 준비 프레임의 실제 등록과 최소 100개 train / 20개 heldout track이
필요합니다. heldout 점은 처음/끝 관측으로 한 번 삼각측량한 뒤 모든 카메라에 재투영합니다.
유한한 오차, median `≤1.5px`, p95 `≤3px`, **모든 카메라에서 앞쪽인 점 `≥95%`**를
만족해야 `ready_for_export:true`가 됩니다. 실패하면 출력·로그를 남기고 비정상 종료하며
export를 막습니다. `heldout-report.json`은 영상상 적합성 검사이고 실제 깊이·치수·
AE 네이티브 부착 검증이 아닙니다. 같은 heldout을 보고 수치를 반복 조정한 결과를
새로운 독립 검증이라고 부르지 않습니다.

`tracking-report.json`, `heldout-report.json`, `solution.json`, 단계별 로그를 확인한 뒤
기존 `colmap_ae.py export --solution ...`로 이어갑니다. 첫/중간/끝 overlay와 실제
AE 카메라/포인트 움직임을 검토해야 합니다. 원거리 샷은 마스크 안 정적 표면의
추적 가이드로 사용하고, 임의의 전경/배경 깊이 분리나 실제 축척으로 확대 해석하지 않습니다.
