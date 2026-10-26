# 처음 시작하기

이 폴더는 **Codex 또는 Claude Code와 함께** 내 영상의 COLMAP 카메라와 원본 RGB
포인트 클라우드를 After Effects로 가져오는 수업용 starter입니다. Python·COLMAP·
FFmpeg가 없는 컴퓨터도 설치 단계부터 시작할 수 있습니다. After Effects는 Adobe
라이선스로 별도 준비하며 앱·모델 가중치는 이 저장소에 포함하지 않습니다.

## 포크해서 받기

공통강의의 Git 세팅(Git·GitHub CLI 설치와 `gh` 인증)을 마친 컴퓨터에서 시작합니다.
[포크로 시작하고 업데이트 받기](docs/fork-and-update.md) 1번의 문장으로 이 저장소를 내 GitHub
계정에 포크해서 받고, 받은 폴더를 Codex에서 다시 엽니다. 전역 스킬 설치는 필요하지 않습니다.

## 폴더를 연 뒤 이 문장을 붙여 넣기

> 이 폴더의 AGENTS.md와 .agents/skills/aftereffect-colmap/SKILL.md를 읽고 시작해 주세요.
> 실제 OS와 설치된 도구를 확인하고, OS setup 문서의 공식 출처로 빠진 것만 준비해 주세요.
> Python 3.13(또는 3.12), 프로젝트 .venv와 tools.local.json을 사용해 주세요.
> 제가 주는 짧은 영상의 모든 프레임에서 카메라와 실제 COLMAP 원본 RGB 점을 복원하고,
> 전체 GLB cloud를 AE로 가져오는 과정까지 한 단계씩 진행해 주세요.
> Adobe 계정 로그인·결제·약관 동의는 제가 직접 하겠습니다. 원본 영상과 기존 프로젝트는
> 보존하고 설치 완료, 계산 완료, 실제 AE 색·단위·부착 확인을 구분해 알려 주세요.
> 긴 계산과 재개는 docs/background.md를 따르고, 실패를 성공으로 보고하지 마세요.

## 진행 순서

1. 현재 OS의 [Mac setup](docs/setup-macos.md) 또는 [Windows setup](docs/setup-windows.md)만
   읽고 도구를 준비합니다. `setup_environment.py --check`는 Python 표준 라이브러리만으로
   검사하며, `--configure`는 로컬 경로만 저장합니다. `--install`을 요청한 때만 `.venv`에
   기본 패키지를 설치합니다.
2. `doctor`가 통과하면 내 영상과 새 `work/<shot>` 폴더를 정해
   [workflow](docs/workflow.md)대로 준비·계산·검증합니다. 아무 영상이나 성공하는 것은
   아닙니다. 고정 줌, 적은 블러, 정적인 질감이 보이는 짧은 샷부터 시작합니다.
3. [point-cloud](docs/point-cloud.md)대로 AE 24.1 이상 / Advanced 3D에서 작은 RGB·단위
   확인을 먼저 합니다. 영상 없이도 `pointcloud.py --rgb-check`로 이 검사를 준비할 수
   있습니다. 그다음 전체 cloud를 가져와 첫·중간·끝 프레임을 실제로 검토합니다.
   `doctor` 통과나 JSX 생성만으로 AE 확인이 끝난 것은 아닙니다.

기본 과정에는 학습 가중치나 외부 영상 업로드가 필요하지 않습니다. 추가 점 복원이나
선택 추적은 현재 샷에서 필요할 때만 읽습니다. 재구성되지 않은 표면의 깊이·실제 치수는
추정하지 않으며, 컴퓨터별 실제 검증 범위는 [validation](docs/validation.md)에 구분합니다.

수업을 마치면 내 작업을 내 포크에 push하고, 강사가 업데이트를 알리면 upstream에서 pull합니다.
방법은 [포크로 시작하고 업데이트 받기](docs/fork-and-update.md)의 2·3번에 있습니다.
