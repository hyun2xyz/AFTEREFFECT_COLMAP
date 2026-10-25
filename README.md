# AFTEREFFECT_COLMAP

**VFX 학생이 LLM 에이전트와 함께 시작하는 작은 COLMAP → After Effects 스킬.**
macOS·Windows에서 Python이 계산을 준비하고 애펙용 JSX를 만듭니다.
애펙 MCP, Blender, 별도 서버 없이 시작합니다.

## 학생은 이렇게 시작합니다

Codex 또는 Claude Code에 이 저장소를 열고 다음처럼 요청하세요.

> AGENTS.md와 공유 스킬을 읽고 제 컴퓨터부터 확인해 주세요.
> 필요한 것만 설치 안내하고, 제가 주는 짧은 영상으로 COLMAP 카메라와
> RGB 점 구름을 애펙에 가져오는 과정을 한 단계씩 진행해 주세요.
> 계산은 백그라운드에서 실행하고, 지원되는 일회성 예약으로 이 채팅을
> 다시 깨워 주세요. 아직 새 기능을 많이 추가하지는 마세요.

- [아무것도 없는 Mac 준비](docs/setup-macos.md)
- [아무것도 없는 Windows 준비](docs/setup-windows.md)
- [첫 영상부터 애펙까지](docs/workflow.md)
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

점은 원래3D 위치와 RGB를 유지하고, 화면에서 볼 수 있는 크기의 표식으로 표시합니다.
기본 표시 상한은2,000점이며 그보다 많은 원본 점도 `points.ply`에는 전부 보존합니다.
원본 영상 레이어는 처음에 꺼져 있습니다. 눈 아이콘을 켜면 영상과 겹쳐 볼 수 있습니다.
지금은 희소 점 구름입니다. 고밀도 복원, 자동 바닥 인식, 사람 가림,
그림자·조명 매칭, 자동 렌더는 다음 수업에서 필요할 때 확장합니다.
애펙에서 카메라를 바꿔도 원래 영상 배경은 2D입니다. 새로운 시점의
사실적인 배경까지 만들려면 별도의 3D 배경 표현이 필요합니다.

## 에이전트/개발자

공유 스킬은 [.agents/skills/aftereffect-colmap/SKILL.md](.agents/skills/aftereffect-colmap/SKILL.md)에 있습니다.
Codex는 저장소 스킬을 사용하고, Claude Code는 `CLAUDE.md`에서 같은 지침을 읽습니다.
전역 설정이나 개인 스킬을 바꾸는 설치기는 없습니다. 새로 연 세션에서 확인하세요.

```sh
python -m pip install -r requirements.txt
python -B scripts/colmap_ae.py doctor
python -B -m unittest discover -s tests -v
```

여기서 `python`은 프로젝트 venv의 Python입니다. 기본 명령은
`doctor`, `prepare`, `solve`, `export`, `anchor` 다섯 개뿐입니다.
긴 계산은 `scripts/jobs.py`로 실행합니다.
SIFT 실패 시에만 `requirements-tracking.txt`와 `scripts/temporal_solve.py`를
선택합니다. 검토한 정적 영역·초점거리 가정을 받고, 계산에 쓰지 않은 약20%의
관측점을 검사해 실패하면 내보내기를 막습니다. 특정 샷의 렌즈·마스크를 기본값으로 넣지 않습니다.

[검증 범위](docs/validation.md)와 [출처·라이선스](THIRD_PARTY_NOTICES.md)를 확인하세요.
실행 파일·Adobe 앱·가중치·학생 영상·AEP는 재배포하지 않습니다.
