# Mac 준비

먼저 [START-HERE](../START-HERE.md)대로 **압축을 푼 저장소 폴더**를 에이전트에 엽니다.
Git은 필수가 아닙니다. 설치된 도구를 먼저 확인하고 빠진 것만 준비합니다.
이 문서의 명령은 그 폴더를 현재 작업 폴더로 삼습니다.

## 1. Python과 실행 프로그램

지원·테스트하는 Python은 **3.12 / 3.13**, 첫 설치 권장은 **3.13**입니다.
이미 있다면 다음 검사는 추가 Python 패키지 없이 실행됩니다.

```sh
python3.13 -B scripts/setup_environment.py --check
```

빠진 항목이 있으면 종료 코드 `1`과 경로/오류를 출력합니다. 이 검사는 설치하거나
설정을 쓰지 않습니다. Python이 없으면 아래 공식 경로부터 준비합니다.

[Homebrew 공식 설치 안내](https://brew.sh/)의 현재 OS/CPU 지원 조건과 설치 내용을
확인합니다. Homebrew도 없는 컴퓨터의 공식 설치 명령은 다음과 같습니다.
설치기의 OS 권한/Command Line Tools 안내는 현재 컴퓨터에서 처리합니다.

```sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

아래 예시는 PATH의 실제 `brew`부터 찾고 Apple Silicon·Intel 기본 경로의 실행 가능
여부를 확인합니다. 이미 있는 항목은 설치 목록에서 뺍니다.
[Python 3.13](https://formulae.brew.sh/formula/python@3.13),
[COLMAP](https://colmap.github.io/install.html),
[FFmpeg](https://formulae.brew.sh/formula/ffmpeg)의 공식 배포 안내를 따릅니다.

```sh
TASK_BREW="$(command -v brew 2>/dev/null || true)"
if [ ! -x "$TASK_BREW" ]; then
  if [ -x /opt/homebrew/bin/brew ]; then
    TASK_BREW=/opt/homebrew/bin/brew
  elif [ -x /usr/local/bin/brew ]; then
    TASK_BREW=/usr/local/bin/brew
  else
    printf '%s\n' 'Homebrew를 찾지 못했습니다. 위 공식 설치 안내를 완료하고 다시 실행하세요.' >&2
    exit 1
  fi
fi
"$TASK_BREW" install python@3.13 colmap ffmpeg
TASK_PYTHON="$("$TASK_BREW" --prefix python@3.13)/bin/python3.13"
"$TASK_PYTHON" -B scripts/setup_environment.py --configure
"$TASK_PYTHON" -B scripts/setup_environment.py --install
.venv/bin/python -B scripts/setup_environment.py --check
.venv/bin/python -B scripts/colmap_ae.py doctor
```

`--configure`는 확인한 `colmap`·`ffmpeg`·`ffprobe`의 절대 경로만
`tools.local.json`에 씁니다. PATH와 Homebrew 기본 위치를 찾으며 전역 PATH를
고치지 않습니다. 경로가 다르면 다음처럼 실제 파일을 명시합니다.

```sh
python3.13 -B scripts/setup_environment.py --configure \
  --colmap /actual/path/colmap --ffmpeg /actual/path/ffmpeg --ffprobe /actual/path/ffprobe
```

실행 시 선택 순서는 **명령 인자 → 환경변수 → tools.local.json → PATH**입니다.
기존 환경변수가 잘못된 경로를 가리키면 그 값을 먼저 수정합니다.
Homebrew를 사용할 수 없다면 [Python macOS 설치기](https://www.python.org/downloads/macos/)와
COLMAP의 현재 공식 설치 방법을 검토합니다. 지원하지 않는 OS에서 준비가 끝났다고
가정하지 않습니다.

## 2. 프로젝트 패키지만 설치

`--install`은 이 폴더의 `.venv`만 만들거나 재사용하고 `requirements.txt`를 설치합니다.
시스템 Python 패키지는 변경하지 않습니다. 다른 컴퓨터에서 복사한 `.venv`는 재사용하지
말고 원본을 보존한 뒤 이 컴퓨터에서 새로 준비합니다.
[Python의 venv 안내](https://docs.python.org/3.13/library/venv.html).

기본 Python 의존성은 Pillow입니다. COLMAP의 CPU SIFT 과정에는 학습 가중치가
필요하지 않습니다. SIFT가 끊긴 샷에서 [선택 추적](temporal.md)이 필요해졌을 때만
다음 명령을 실행합니다.

```sh
.venv/bin/python -B scripts/setup_environment.py --install --tracking
```

이후 문서의 `python`은 `.venv/bin/python`입니다. 설치 완료 여부는 `--check`와
`doctor`의 실제 출력으로 확인합니다. 설치기는 카메라 계산이나 AE 검증을 대신하지 않습니다.

## 3. After Effects와 첫 네이티브 확인

[Adobe 공식 설치 안내](https://helpx.adobe.com/download-install/using/download-install-new-computer.html)에
따라 학생의 계정·라이선스로 After Effects를 준비합니다. 로그인·유료 계약·약관 동의는
계정 소유자가 직접 처리하며 이 저장소는 앱이나 키를 배포하지 않습니다.

기본 전체 RGB cloud는 **AE 24.1 이상 / Advanced 3D / GLB** 경로를 사용합니다.
컴퓨터의 [3D 모델 지원](https://helpx.adobe.com/after-effects/desktop/import-files/import-and-add-3d-models/import-3d-model.html)을
확인하고 [point-cloud 안내](point-cloud.md)대로 작은 RGB/단위 확인부터 실행합니다.
영상 없이 `.venv/bin/python -B scripts/pointcloud.py --rgb-check --out work/rgb-first`로
검사 파일을 생성할 수 있습니다. `work/rgb-first/check_rgb.jsx`를 먼저 실행합니다.
실제 export가 만든 `check_rgb.jsx`, 이어서 `import_scene.jsx`를 검토한 뒤
**File → Scripts → Run Script File**에서 실행합니다. 앱을 자동 저장하거나 렌더하지 않습니다.

설치/파일 생성과 실제 화면 검증을 구분합니다. 첫·중간·끝 프레임에서 원본 영상과
카메라·RGB cloud의 색과 부착을 확인한 뒤 완료로 기록합니다.
계산 명령은 [workflow](workflow.md), 긴 계산과 일회성 재개는
[background](background.md), 실제 확인 범위는 [validation](validation.md)을 따릅니다.
