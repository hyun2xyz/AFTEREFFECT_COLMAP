# 선택 수업: Laya로 짧은 판단만 줄이기

기본 COLMAP→애펙 과정은 Laya 없이 완전히 실행됩니다. 가중치가 필요한 것은
COLMAP이 아니라 이 선택 기능입니다. Laya는 영상을 보거나 3D 공간을 복원하는
모델이 아니며, 짧은 텍스트에 대해 미리 정한 선택지를 평가합니다.

최적화의 순서는 **명확한 요청은 바로 Python → 상태는 짧은 JSON → 애매한
반복 판단에만 로컬 Laya → 긴 해석/코드 수정은 주 에이전트**입니다.
모든 명령 앞에 Laya를 호출하면 cold load와 설치 비용만 커질 수 있습니다.

## 공식 출처와 OS

- 코드: https://github.com/NandhaKishorM/laya (MIT)
- 모델: https://huggingface.co/convaiinnovations/laya (모델 카드의 Apache-2.0 확인)
- 한국어용: `multilingual` subfolder. Windows/macOS CPU에서 같은 가중치를 씁니다.
- 이 작은 adapter의 재현 기준은 `laya==0.3.4`, 모델 revision
  `1c5edc17a7acd8701df6fc341c0d179f1c62c982`입니다. 최신 버전을 섞으면 API/출력을 다시 확인합니다.

MLX는 Apple 전용 최적화 선택지이지 Windows 공통 필수 요소가 아닙니다.
초기 수업은 CPU 한 경로만 제공합니다. 원본 loader가 tokenizer config를
고칠 수 있어 다운로드 원본과 실행용 복사본을 분리합니다.

## 학생이 선택했을 때만 준비

기본 venv와 별도로 Python 3.12 venv를 만듭니다. Mac은 `python3.12 -m venv .venv-laya`,
Windows는 `py -3.12 -m venv .venv-laya`입니다. 이후 `LPY` 표기는 각각
`.venv-laya/bin/python` / `.venv-laya\Scripts\python.exe`로 바꿉니다.
PyTorch는 [공식 설치 선택기](https://pytorch.org/get-started/locally/)에서 해당 OS를 확인합니다.

```text
# Windows CPU (해당 venv Python 실행 파일로 LPY를 교체)
LPY -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
# Mac CPU: 위 명령 대신
LPY -m pip install torch==2.6.0
# 두 OS 공통
LPY -m pip install laya==0.3.4 transformers==5.0.0 safetensors==0.8.0 "huggingface-hub>=1,<2"
```

학생이 다운로드를 요청하면 에이전트가 아래 Python을 **별도 스크립트로 저장해**
실행할 수 있습니다. 외부 SSD 등 원하는 저장 위치를 먼저 정합니다. 가중치를
Git에 넣지 않습니다. 아래는 같은 revision의 tokenizer/config까지 받는 예시입니다.

```python
from pathlib import Path
import hashlib
import shutil
from huggingface_hub import snapshot_download

root = Path("models/laya").resolve()  # Git ignored; change to student's work volume if needed
snapshot_download(
    repo_id="convaiinnovations/laya",
    revision="1c5edc17a7acd8701df6fc341c0d179f1c62c982",
    local_dir=root / "pristine",
    allow_patterns=["README.md", "LICENSE*", "multilingual/*"],
)
weight = root / "pristine/multilingual/model.safetensors"
digest = hashlib.file_digest(weight.open("rb"), "sha256").hexdigest()
assert digest == "9d628fd971b700382ac6f65920a86f149777b2e748e0c955fb3b19695aa8f204"
shutil.copytree(root / "pristine/multilingual", root / "runtime")  # new destination only
```

공개 모델에 토큰이 필요하지 않은데도 토큰을 생성하거나 학생 자격 증명을
저장소에 넣지 않습니다. 다운로드 성공·완전한 파일·해시를 확인한 뒤에만 실행합니다.

```sh
LPY scripts/laya_suggest.py --model models/laya/runtime --request "복원은 끝났고 애펙으로 가져오는 방법이 궁금해요"
```

adapter는 두 짧은 질문을 한 번에 평가하고 `prepare/solve/export/anchor/ask_agent`
중 하나를 제안합니다. 실행은 하지 않습니다. 모델/패키지 누락·오류는
`abstain`으로 주 에이전트에 돌아갑니다. 확률 집중도를 정답률로 설명하지 않습니다.
장시간 로그, 영상, 학생의 비밀 정보는 입력하지 않습니다. Laya 결과로 자동
설치·재계산·앱 변경·수업 합격을 결정하지 않습니다.

새 저장소에서 실제 Laya 가중치 추론을 했는지는 [검증 기록](validation.md)과
구분합니다. 기존 vfx-workbench의 다른 환경에서 얻은 수치를 이번 실행 결과로 쓰지 않습니다.
