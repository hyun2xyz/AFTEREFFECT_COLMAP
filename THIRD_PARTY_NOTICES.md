# 출처와 별도 라이선스

이 저장소의 새 starter 코드와 문서는 [MIT](LICENSE)입니다. 외부 실행 프로그램,
모델 가중치, 학생의 영상/3D 자산, Adobe 제품의 권리는 포함하지 않습니다.

## 참고·축약한 원본

사용자의 요청으로 [hyun2xyz/vfx-workbench](https://github.com/hyun2xyz/vfx-workbench)
commit `1211befad628e0b3856e50158b61be2f5d808723`의 다음 부분을 검토했습니다.

- `modules/camera_tracker/tools/run_colmap.py`: CPU COLMAP, world→camera 역변환,
  등록 프레임과 실패를 분리하는 개념.
- `modules/camera_tracker/integrations/canonical_exchange.py`, `generate_ae_jsx.py`:
  CV 카메라 좌표와 AE position/point-of-interest/roll 교환 개념.
- `modules/aftertracker/plugins/aftertracker-vfx/scripts/laya_recommend.py`,
  `bootstrap_laya.py`: 로컬 모델·고정 revision·기권·제안과 실행을 분리하는 개념.

과거 제작 데이터, 절대 경로, 녹화/배포/모델 설치 자동화는 복사하지 않았습니다.
코드는 이 입문 저장소의 CLI와 제한에 맞춰 새로 축약했습니다. 원본 전체에
하나의 라이선스가 있다고 추정해 통째로 재배포하지 않습니다.

AE pose convention은 [B2AC](https://github.com/hyun2xyz/b2ac/tree/a1e3c50ad4dddff8215ddb7e9eded078d639f4a5)
commit `a1e3c50ad4dddff8215ddb7e9eded078d639f4a5`의 MIT 관례를 참고합니다.
원본 notice는 vfx-workbench의 `integrations/third_party/B2AC_LICENSE.txt`에서
확인했고 copyright/permission/warranty 조항은 이 저장소 [LICENSE](LICENSE)에
동일하게 보존했습니다. B2AC 실행 코드나 Blender addon은 포함하지 않습니다.

## 외부 도구

| 도구 | 공식 출처 | 배포 범위 |
| --- | --- | --- |
| COLMAP | https://github.com/colmap/colmap | BSD-3-Clause 및 해당 릴리스 dependency notices; 바이너리 미포함 |
| FFmpeg | https://ffmpeg.org/legal.html | 빌드 옵션에 따라 LGPL/GPL 등 확인; 바이너리 미포함 |
| Pillow | https://pillow.readthedocs.io/en/stable/about.html#license | 별도 오픈소스 의존성; pip 설치 |
| NumPy | https://github.com/numpy/numpy/blob/main/LICENSE.txt | 연속 추적용 선택 의존성; pip 설치 |
| OpenCV | https://github.com/opencv/opencv/blob/4.x/LICENSE | 연속 추적용 선택 의존성; headless CPU 패키지 pip 설치 |
| Laya 코드 | https://github.com/NandhaKishorM/laya | MIT; 선택 설치 |
| Laya 가중치 | https://huggingface.co/convaiinnovations/laya | 해당 모델 카드 Apache-2.0; 다운로드 시 revision/notice 확인 |
| After Effects | https://www.adobe.com/products/aftereffects.html | 상용, 학생의 별도 라이선스 필요 |

코드와 모델 가중치의 라이선스는 서로 다를 수 있습니다. 공개/상용 사용 전에
사용 중인 실제 버전과 자산의 조건을 확인합니다. 합성 smoke의 텍스처는 난수로
생성하며 외부 사진이나 영상은 내려받지 않습니다.

전체 점 표시 파일은 [Khronos glTF2.0](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html)과
[KHR_materials_unlit](https://github.com/KhronosGroup/glTF/tree/main/extensions/2.0/Khronos/KHR_materials_unlit)
형식 규약을 따릅니다. 외부 GLB exporter 코드나 3D 자산을 복사하지 않습니다.
