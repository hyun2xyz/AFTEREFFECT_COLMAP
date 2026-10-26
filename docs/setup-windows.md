# Windows 준비

Windows 10/11 **x64 CPU 경로**를 기준으로 시작합니다. NVIDIA GPU는 첫 COLMAP
계산의 필수가 아닙니다. [START-HERE](../START-HERE.md)대로 ZIP을 완전히 풀고
그 폴더를 에이전트와 PowerShell의 작업 폴더로 선택합니다. Git은 필수가 아닙니다.

## 1. Python부터

지원·테스트 버전은 **3.12 / 3.13**, 첫 설치 권장은 **3.13**입니다.
이미 있다면 추가 Python 패키지 없이 현재 상태부터 확인합니다.

```powershell
py -3.13 -B scripts/setup_environment.py --check
```

빠진 도구가 있으면 종료 코드 `1`과 실제 오류를 출력하며 아무것도 변경하지 않습니다.
Python이 없다면 [Python 공식 Windows 설치기](https://www.python.org/downloads/windows/)의
3.13 x64 전체 설치기를 사용합니다. embeddable ZIP이나 source ZIP을 고르지 않습니다.
WinGet이 있는 컴퓨터는 [Microsoft 설치 명령](https://learn.microsoft.com/en-us/windows/package-manager/winget/install)으로
패키지/설치 출처를 확인하고 사용자 범위로 설치할 수도 있습니다.

```powershell
winget show --id Python.Python.3.13 --exact --source winget
winget install --id Python.Python.3.13 --exact --source winget --scope user --architecture x64
```

설치 후 새 터미널에서 `py -3.13 --version`을 확인합니다. `py`가 보이지 않으면
설치한 `python.exe`의 실제 절대 경로로 대신 실행합니다. helper는 Python 자체나
WinGet·시스템 프로그램을 설치하지 않습니다.

## 2. COLMAP과 FFmpeg

[COLMAP 공식 Releases](https://github.com/colmap/colmap/releases)에서 **Windows x64 nocuda**
전체 ZIP을 받습니다. 확인한 재현용 버전은
[4.2.1 nocuda](https://github.com/colmap/colmap/releases/download/4.2.1/colmap-x64-windows-nocuda.zip)입니다.
[FFmpeg 공식 Windows 링크](https://ffmpeg.org/download.html#build-windows)가 연결하는
[Gyan release essentials ZIP](https://www.gyan.dev/ffmpeg/builds/)에는 `ffmpeg.exe`와
`ffprobe.exe`가 함께 있습니다. 앱·DLL·plugins를 따로 떼어 복사하지 않습니다.

새 컴퓨터의 다운로드/압축 해제 예시입니다. 기존 설치 폴더가 있다면 덮어쓰기 전에
먼저 `--check`로 확인합니다. 아래 다운로드는 저장소 밖의 사용자 로컬 폴더에 둡니다.

```powershell
$ToolRoot = Join-Path $env:LOCALAPPDATA 'AFTEREFFECT_COLMAP\tools'
$Downloads = Join-Path $ToolRoot 'downloads'
New-Item -ItemType Directory -Path $Downloads -Force | Out-Null
$ColmapZip = Join-Path $Downloads 'colmap-4.2.1-nocuda.zip'
Invoke-WebRequest 'https://github.com/colmap/colmap/releases/download/4.2.1/colmap-x64-windows-nocuda.zip' -OutFile $ColmapZip
if ((Get-FileHash $ColmapZip -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'c493d88cb4a43f21afba42cb55bf786e5434a0420e73db0ba1454c5d8b3686ae') { throw 'COLMAP SHA256 mismatch' }
Expand-Archive -Path $ColmapZip -DestinationPath (Join-Path $ToolRoot 'COLMAP')
$FfmpegZip = Join-Path $Downloads 'ffmpeg-release-essentials.zip'
Invoke-WebRequest 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile $FfmpegZip
Invoke-WebRequest 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip.sha256' -OutFile "$FfmpegZip.sha256"
$Expected = [regex]::Match((Get-Content "$FfmpegZip.sha256" -Raw), '\b[a-fA-F0-9]{64}\b').Value
if (-not $Expected -or (Get-FileHash $FfmpegZip -Algorithm SHA256).Hash -ne $Expected) { throw 'FFmpeg SHA256 mismatch' }
Expand-Archive -Path $FfmpegZip -DestinationPath (Join-Path $ToolRoot 'FFmpeg')
$ColmapExe = (Get-ChildItem (Join-Path $ToolRoot 'COLMAP') -Filter colmap.exe -Recurse | Select-Object -First 1).FullName
$FfmpegExe = (Get-ChildItem (Join-Path $ToolRoot 'FFmpeg') -Filter ffmpeg.exe -Recurse | Select-Object -First 1).FullName
$FfprobeExe = Join-Path (Split-Path $FfmpegExe) 'ffprobe.exe'
py -3.13 -B scripts/setup_environment.py --configure --colmap $ColmapExe --ffmpeg $FfmpegExe --ffprobe $FfprobeExe
py -3.13 -B scripts/setup_environment.py --install
.\.venv\Scripts\python.exe -B scripts/setup_environment.py --check
.\.venv\Scripts\python.exe -B scripts/colmap_ae.py doctor
```

다운로드 후 버전이나 해시가 달라졌다면 공식 release metadata를 확인하고 멈춥니다.
`--configure`는 실제로 실행된 파일의 절대 경로만 `tools.local.json`에 저장합니다.
`COLMAP.bat` 대신 **실제 `colmap.exe`**를 지정합니다. helper는 전체 ZIP의
DLL/plugins를 사용하며 시스템 PATH나 PowerShell 실행 정책을 변경하지 않습니다.
이후 실행 시 선택 순서는 **명령 인자 → 환경변수 → tools.local.json → PATH**입니다.
기존 `COLMAP_BINARY` 등이 오래된 경로를 가리키면 그 값을 먼저 고칩니다.

Microsoft runtime DLL 오류가 나면
[Microsoft 공식 x64 Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)를
확인합니다. 출처를 모르는 DLL을 복사하지 않고 `doctor`의 실제 오류를 보존합니다.

## 3. 프로젝트 패키지와 After Effects

이후 문서의 `python`은 `.\.venv\Scripts\python.exe`입니다. activation은 필요하지 않습니다.
`--install`은 이 프로젝트의 `.venv`와 `requirements.txt`만 사용합니다.
[선택 추적](temporal.md)이 필요해진 때만 다음을 실행합니다. 가중치는 필요하지 않습니다.

```powershell
.\.venv\Scripts\python.exe -B scripts/setup_environment.py --install --tracking
```

[Adobe 공식 설치 안내](https://helpx.adobe.com/download-install/using/download-install-new-computer.html)를
따라 학생 자신의 계정·라이선스로 After Effects를 준비합니다. 로그인·유료 계약·EULA 동의는
계정 소유자가 직접 처리합니다. 기본 전체 RGB cloud에는 **AE 24.1 이상 / Advanced 3D / GLB**가
필요합니다. [point-cloud](point-cloud.md)의 작은 RGB/단위 확인을 먼저 하고 생성된
`check_rgb.jsx` → `import_scene.jsx`를 **File → Scripts → Run Script File**에서 실행합니다.
영상 없이 `.\.venv\Scripts\python.exe -B scripts/pointcloud.py --rgb-check --out work/rgb-first`로
첫 검사 파일을 생성할 수 있습니다.
자동 저장·렌더나 MCP는 필요하지 않습니다.

Windows AE의 네이티브 표시가 이 배포물에서 확인되었다고 취급하지 않습니다.
해당 컴퓨터에서 색/단위와 첫·중간·끝의 실제 프레임을 검증합니다.
계산은 [workflow](workflow.md), 긴 계산과 일회성 재개는 [background](background.md),
실제 확인 범위는 [validation](validation.md)을 따릅니다.
