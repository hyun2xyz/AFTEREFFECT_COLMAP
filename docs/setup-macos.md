# Mac 준비

에이전트는 이미 설치된 것을 먼저 확인하고 빠진 것만 준비합니다.
기본 과정은 Apple Silicon/Intel의 CPU 경로입니다. 학생의 영상·모델은
외부 서비스에 올릴 필요가 없습니다. 설치 시의 관리자/앱 권한은 학생이 확인합니다.

## 공식 다운로드

| 항목 | 준비할 곳 | 용도 |
| --- | --- | --- |
| Homebrew | https://brew.sh/ | 패키지 설치 |
| Python | https://www.python.org/downloads/macos/ 또는 Homebrew | 스크립트 실행 |
| COLMAP | https://colmap.github.io/install.html 또는 `brew install colmap` | CPU 카메라 복원 |
| FFmpeg | https://ffmpeg.org/download.html 또는 Homebrew | 영상·프레임 입출력 |
| After Effects | https://www.adobe.com/products/aftereffects.html | 학생의 라이선스로 별도 설치 |

Homebrew가 없다면 공식 사이트의 설치 명령을 확인해 실행하고, 설치 끝에
출력된 **Next steps**로 shellenv/PATH를 설정합니다. Apple Silicon의 기본
위치는 `/opt/homebrew`, Intel은 `/usr/local`입니다. 학생 컴퓨터의 실제 출력이 우선입니다.

```sh
brew install python@3.13 git colmap ffmpeg
git clone https://github.com/hyun2xyz/AFTEREFFECT_COLMAP.git
cd AFTEREFFECT_COLMAP
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -B scripts/colmap_ae.py doctor
```

이미 Python 3.12 이상이 있다면 그것으로 venv를 만들어도 됩니다.
문서의 이후 `python` 표기는 `.venv/bin/python`으로 바꿔 실행합니다.
시스템 Python에 패키지를 덮어쓰지 않습니다.

## CPU와 모델

COLMAP의 기본 SIFT 복원에는 가중치 다운로드가 없습니다. 스크립트가
설치된 CLI의 옵션을 확인해 CPU feature extraction/matching을 선택합니다.
이 Mac에서 실제 확인한 버전은 COLMAP 3.12.4(no CUDA), Python 3.13.7입니다.
최신 Homebrew 버전은 달라질 수 있으므로 `doctor`로 다시 확인합니다.

CUDA가 없는 빌드의 기본 고밀도 stereo 복원은 이 입문 과정에 포함하지 않습니다.
카메라·희소 RGB 점과 영상 undistortion에는 해당 단계가 필요 없습니다.
[COLMAP의 GPU 없는 환경 안내](https://colmap.github.io/legacy/3.12/faq.html#available-functionality-without-gpu-cuda).

Laya가 필요한 다음 단계에서만 [Laya 안내](laya.md)를 읽습니다.
일반 모델은 두 OS에서 같고, Mac 전용 MLX 가중치가 필수인 구조가 아닙니다.

## 애펙에서 마지막 한 번

생성된 `import_scene.jsx`를 검토하고 **File → Scripts → Run Script File**로 실행합니다.
Python을 애펙 내부에서 직접 실행하는 것은 아닙니다. 별도 MCP나 상주 패널을
설치하지 않습니다. 기본 JSX는 파일 쓰기/네트워크 권한을 켜라고 요구하지 않습니다.
학생의 프로젝트에 새 폴더·컴포지션을 추가하며 자동 저장하지 않습니다.

3D 파일을 쓸 때는 GLB가 가장 간단합니다. 애펙의 버전별
[지원 형식](https://helpx.adobe.com/after-effects/desktop/import-files/import-and-add-3d-models/import-3d-model.html)을 확인합니다.
모델의 축·피벗·크기는 실제 화면에서 확인하고 맞춥니다.
