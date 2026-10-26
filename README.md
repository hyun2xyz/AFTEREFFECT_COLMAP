# AFTEREFFECT_COLMAP

**VFX 학생이 LLM 에이전트와 함께 시작하는 작은 COLMAP → After Effects 스킬.**
macOS·Windows에서 Python이 계산을 준비하고 애펙용 JSX를 만듭니다.
애펙 MCP, Blender, 별도 서버 없이 시작합니다.

## 학생은 이렇게 시작합니다

공통강의의 Git 세팅을 마친 컴퓨터에서, 이 저장소를 내 GitHub 계정에 **포크**해서 시작합니다.

1. Codex 또는 Claude Code에 붙여 넣습니다.

   > https://github.com/hyun2xyz/AFTEREFFECT_COLMAP 를 제 GitHub 계정으로 포크해서 문서(Documents) 폴더에
   > 받아 주세요. 끝나면 origin과 upstream 주소를 보여 주세요.

2. 받은 `AFTEREFFECT_COLMAP` 폴더를 Codex에서 다시 열고 [START-HERE.md](START-HERE.md)의 문장이나
   다음처럼 요청합니다.

> START-HERE.md, AGENTS.md와 공유 스킬을 읽고 제 컴퓨터부터 확인해 주세요.
> 필요한 것만 설치 안내하고, 제가 주는 짧은 영상으로 COLMAP 카메라와
> RGB 점 구름을 애펙에 가져오는 과정을 한 단계씩 진행해 주세요.
> 계산은 백그라운드에서 실행하고, 지원되는 일회성 예약으로 이 채팅을
> 다시 깨워 주세요. 아직 새 기능을 많이 추가하지는 마세요.

- [포크로 시작하고 업데이트 받기](docs/fork-and-update.md)
- [아무것도 없는 Mac 준비](docs/setup-macos.md)
- [아무것도 없는 Windows 준비](docs/setup-windows.md)
- [첫 영상부터 애펙까지](docs/workflow.md)
- [COLMAP 전체 RGB 점·한 레이어 표시·실제 점 추가](docs/point-cloud.md)
- [SIFT가 끊기는 짧은 샷: 선택형 연속 측정 추적](docs/temporal.md)
- [백그라운드 계산·한 번만 재개·예약 정리](docs/background.md)
- [선택: Laya로 작은 판단 줄이기](docs/laya.md)

## 첫 버전의 범위

1. 짧은 영상의 모든 프레임과 정확한 FPS를 준비합니다.
2. CPU COLMAP으로 카메라와 색이 있는 희소 3D 점을 복원합니다.
3. 카메라와 RGB 점 구름을 가져오는 JSX를 만듭니다. 메인 컴프는 카메라·점 구름 그룹·원본 영상·검은 배경의 4개 레이어입니다.
4. 학생이 고른 세 점으로 바닥/벽 기준을 잡고, 제공한 3D 모델을 그 위치에 놓습니다.

**COLMAP은 학습 가중치가 필요 없습니다.** 기본 Python 의존성은 Pillow 하나입니다.
COLMAP·FFmpeg·After Effects는 각 공식 경로에서 별도로 준비합니다.
Laya 가중치는 선택 사항이며 Git에 포함하지 않습니다.

점은 원래 3D 중심과 RGB를 유지하며 **전체 점**을 GLB 모델 레이어 하나로 표시합니다.
기본 크기는 첫 카메라에서 3px입니다. 전체 원본 좌표/RGB는 `points.ply`에도 보존합니다.
AE24.1+의 Advanced3D가 필요하며 첫 호스트에서 `check_rgb.jsx`로 색과 단위를 확인합니다.
구형 AE용 `--cloud-renderer shapes`는 명시적인 제한 표시 옵션입니다.
원본 영상 레이어는 처음에 꺼져 있습니다. 눈 아이콘을 켜면 영상과 겹쳐 볼 수 있습니다.
지금은 희소 점 구름입니다. 고밀도 복원, 자동 바닥 인식, 사람 가림,
그림자·조명 매칭, 자동 렌더는 다음 수업에서 필요할 때 확장합니다.
애펙에서 카메라를 바꿔도 원래 영상 배경은 2D입니다. 새로운 시점의
사실적인 배경까지 만들려면 별도의 3D 배경 표현이 필요합니다.

## 에이전트/개발자

공유 스킬은 [.agents/skills/aftereffect-colmap/SKILL.md](.agents/skills/aftereffect-colmap/SKILL.md)에 있습니다.
Codex는 저장소 스킬을 사용하고, Claude Code는 `CLAUDE.md`에서 같은 지침을 읽습니다.
전역 설정이나 개인 스킬을 바꾸는 설치기는 없습니다. 새로 연 세션에서 확인하세요.

아래는 **OS 준비와 setup helper의 프로젝트 venv 설치가 끝난 뒤** 실행합니다.

macOS:

```sh
.venv/bin/python -B scripts/colmap_ae.py doctor
.venv/bin/python -B -m unittest discover -s tests -v
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -B scripts/colmap_ae.py doctor
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

다른 문서의 `python`도 이 프로젝트 venv 실행 파일을 뜻합니다. 기본 명령은
`doctor`, `prepare`, `solve`, `export`, `anchor` 다섯 개뿐입니다.
긴 계산은 `scripts/jobs.py`로 실행합니다.
SIFT 실패 시에만 `requirements-tracking.txt`와 `scripts/temporal_solve.py`를
선택합니다. 검토한 정적 영역·초점거리 가정을 받고, 계산에 쓰지 않은 약20%의
관측점을 검사해 실패하면 내보내기를 막습니다. 특정 샷의 렌즈·마스크를 기본값으로 넣지 않습니다.
점이 더 필요할 때만 `enrich_cloud.py`로 검증된 카메라를 고정하고 실제 COLMAP 점을
추가합니다. 새 SIFT가 기본이며, 기존 DB 재사용은 모든 입력 픽셀이 같은 경우만 허용합니다.

설치 경로는 `scripts/setup_environment.py --configure`가 개인 `tools.local.json`에
기록합니다. 패키지는 실행 파일·venv·개인 설정을 포함하지 않습니다. Adobe 설치와
라이선스/약관 단계는 학생이 공식 앱에서 진행하며, 에이전트가 완료 여부를 확인합니다.

[검증 범위](docs/validation.md)와 [출처·라이선스](THIRD_PARTY_NOTICES.md)를 확인하세요.
실행 파일·Adobe 앱·가중치·학생 영상·AEP는 재배포하지 않습니다.
