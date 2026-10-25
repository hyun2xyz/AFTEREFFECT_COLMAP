# Windows 준비

Windows 10/11 x64의 CPU 경로부터 시작합니다. NVIDIA GPU가 없어도 첫 수업을
진행할 수 있습니다. 아래 파일들은 OS에 맞는 실행 프로그램이며 학습 가중치가 아닙니다.

## 준비 순서

1. [Git for Windows](https://git-scm.com/downloads/win)와
   [Python](https://www.python.org/downloads/windows/) 3.12 이상을 준비합니다.
   첫 과정의 기준은 Python 3.13입니다. 터미널을 다시 열어 `git --version`,
   `py -3.13 --version`을 확인합니다.
2. [COLMAP 공식 Releases](https://github.com/colmap/colmap/releases)에서
   **Windows x64 nocuda** ZIP을 받습니다. 2026-10-25 확인 예시는
   [4.2.1 nocuda](https://github.com/colmap/colmap/releases/download/4.2.1/colmap-x64-windows-nocuda.zip)입니다.
   **Source code ZIP이 아닙니다.** 전체를 `C:\Tools\COLMAP` 등에 풀고
   DLL·plugins 폴더를 함께 보존합니다. NVIDIA CUDA 빌드는 나중에 필요할 때 선택합니다.
3. [FFmpeg 공식 다운로드 페이지의 Windows 링크](https://ffmpeg.org/download.html#build-windows)에서
   빌드를 받아 압축을 풀고 `ffmpeg.exe`, `ffprobe.exe`가 든 `bin`을 PATH에
   추가하거나 아래 환경변수로 정확한 경로를 지정합니다.
4. [After Effects](https://www.adobe.com/products/aftereffects.html)는 학생의
   Adobe 라이선스로 별도 설치합니다. 공개 저장소에 앱/SDK/키를 담지 않습니다.

COLMAP 배포본의 `COLMAP.bat -h`로 먼저 설치를 확인해도 됩니다.
Python 실행기는 셸을 거치지 않으므로 **실제 `colmap.exe` 경로**를 사용합니다.
설치 경로는 압축을 푼 실제 구조로 바꾸세요.

```powershell
$env:COLMAP_BINARY = 'C:\Tools\COLMAP\bin\colmap.exe'
$env:FFMPEG_BINARY = 'C:\Tools\ffmpeg\bin\ffmpeg.exe'
$env:FFPROBE_BINARY = 'C:\Tools\ffmpeg\bin\ffprobe.exe'
git clone https://github.com/hyun2xyz/AFTEREFFECT_COLMAP.git
cd AFTEREFFECT_COLMAP
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -B scripts/colmap_ae.py doctor
```

이후 문서의 `python`은 `.\.venv\Scripts\python.exe`입니다. PowerShell
실행 정책을 바꾸거나 venv activation을 켤 필요가 없습니다.
위 환경변수는 현재 터미널에만 적용됩니다. 새로 연 에이전트에도 같은 설정을
전달하거나 `COLMAP_BINARY`/FFmpeg PATH를 그 프로세스에서 설정해야 합니다.
실행기는 `colmap.exe` 옆의 DLL 경로와 상위 `plugins`를 연결합니다.
`doctor`가 실패하면 전체 ZIP 구조·버전·로그를 먼저 확인합니다.
배포본 실행 시 Microsoft C/C++ runtime DLL 오류가 나면
[Microsoft 공식 Visual C++ Redistributable 안내](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)
에서 x64용 runtime을 확인합니다. 출처를 모르는 DLL 파일을 따로 복사하지 않습니다.

COLMAP은 별도 모델 가중치가 필요 없습니다. [선택 Laya](laya.md)는 같은
다국어 가중치를 CPU로 사용하므로 Windows에 MLX를 설치하지 않습니다.
SIFT가 끊기는 짧은 샷은 [선택형 연속 추적](temporal.md)을 검토하고,
그때만 `.\.venv\Scripts\python.exe -m pip install -r requirements-tracking.txt`로
NumPy/OpenCV를 프로젝트 venv에 추가합니다. 가중치는 필요하지 않습니다.

## 애펙

생성된 JSX를 **File → Scripts → Run Script File**로 실행합니다.
이 한 단계는 Mac과 같습니다. Windows의 `AfterFX.exe -r` 자동 실행은 필요해진
다음 수업에서 추가할 수 있으며 이 starter는 앱을 강제 실행하거나 저장하지 않습니다.
GLTF의 외부 BIN/텍스처가 빠졌다면 단일 GLB를 요청하는 것이 편합니다.

Windows 전용 코드의 실제 확인 상태는 [검증 기록](validation.md)에 표시합니다.
Mac에서의 성공을 Windows 애펙 실행 성공으로 해석하지 않습니다.
