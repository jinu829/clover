# 사용 방법

이 프로젝트는 상품의 앞면 사진, 뒷면 사진, 사이즈표 이미지를 받아
GarmentCode의 티셔츠 패턴을 사이즈별로 생성하는 **어댑터**입니다.

> 사진 전체를 texture로 붙이거나, 사진만으로 실제 봉제 패턴을 복원하지
> 않습니다. 사진은 티셔츠 형태와 기본 색을 판단하는 참고 자료이고, 실제
> 치수는 반드시 사이즈표에서 가져옵니다.

## 1. 필요한 준비물

- Python 3.9 (64-bit 권장)
- 원본 [GarmentCode](https://github.com/maria-korosteleva/GarmentCode) 저장소
- 상품별 앞면·뒷면·사이즈표 이미지
- 한글 사이즈표를 OCR로 읽을 경우 Tesseract OCR 및 한국어(`kor`) 언어 데이터

Python 설치 시 **Add Python to PATH**를 선택한 뒤, 새 PowerShell에서 아래
명령이 동작하는지 확인합니다.

```powershell
python --version
```

## 2. GarmentCode에 어댑터 설치

먼저 GarmentCode를 별도로 내려받습니다. 이 저장소에는 GarmentCode 본체를
포함하지 않습니다.

```powershell
git clone https://github.com/maria-korosteleva/GarmentCode.git GarmentCode-main
```

그 다음 이 저장소의 설치 스크립트를 실행합니다. 경로는 자신의 폴더 위치에
맞게 바꿉니다.

```powershell
& ".\install_into_garmentcode.ps1" `
  -GarmentCodeRoot "C:\path\to\GarmentCode-main"
```

GarmentCode 폴더에서 Python 의존성을 설치합니다.

```powershell
cd "C:\path\to\GarmentCode-main"
python -m pip install -e .
python -m pip install -r "C:\path\to\garmentcode-product-image-adapter\requirements.txt"
```

## 3. 새 상품 실행하기

상품 하나당 아래처럼 세 파일을 준비합니다.

```text
inputs/
└─ new_product/
   ├─ front.png       # 상품 앞면 사진
   ├─ back.png        # 상품 뒷면 사진
   └─ size_chart.png  # 상품 치수표 이미지
```

현재 지원하는 치수표 헤더는 다음 네 가지입니다. 한글·영문 별칭도 인식합니다.

```text
총장 / body length
어깨너비 / shoulder width
가슴단면 / chest width
소매길이 / sleeve length
```

GarmentCode 폴더에서 실행합니다.

```powershell
python generate_from_product_images.py `
  --front "inputs/new_product/front.png" `
  --back "inputs/new_product/back.png" `
  --size-chart "inputs/new_product/size_chart.png" `
  --output "outputs/new_product"
```

`가슴단면`은 옷을 평평하게 놓고 측정한 폭으로 해석합니다. 코드에서 이를
두 배로 계산해 GarmentCode 패널 둘레에 연결합니다.

## 4. 포함된 A--T 예제 실행하기

검토가 끝난 로컬 상품 세트는 `assets/product_catalog.json`에 등록되어 있습니다.
예를 들어 A 세트는 A1(앞면), A2(뒷면), A3(사이즈표)를 자동으로 찾습니다.

```powershell
python generate_from_product_images.py `
  --catalog-id A `
  --catalog-root "C:\path\to\옷 파일\옷 파일" `
  --output "outputs/A"
```

### GitHub에 포함된 즉시 실행 예제

저장소의 `examples/A/`에는 실행 가능한 검은색 기본 반소매 티셔츠 예제
(`front.png`, `back.png`, `size_chart.png`)가 포함되어 있습니다. GarmentCode와
이 저장소를 나란히 clone한 경우 GarmentCode 폴더에서 아래처럼 실행합니다.

```powershell
python generate_from_product_images.py `
  --front "..\garmentcode-product-image-adapter\examples\A\front.png" `
  --back "..\garmentcode-product-image-adapter\examples\A\back.png" `
  --size-chart "..\garmentcode-product-image-adapter\examples\A\size_chart.png" `
  --output "outputs\example_A"
```

이 예제 이미지는 저장소 작성자가 재배포해도 된다고 판단한 경우에만 포함해야
합니다. 권한이 없다면 `examples/A/`를 삭제하고, 자신의 입력 이미지로 3절의
명령을 사용합니다.

## 5. 결과 확인하기

성공하면 다음과 같은 결과가 생성됩니다.

```text
outputs/new_product/
├─ parsed_size_table.json      # OCR로 읽고 검증한 치수표
├─ reference_analysis.json     # 사진 분류 결과와 경고
├─ reference/
│  ├─ front.png
│  └─ back.png
├─ XS/
│  ├─ pattern_XS.json
│  ├─ measurements.json
│  └─ validation.json
└─ ...                         # 실제로 발견한 모든 size row마다 생성
```

반드시 `parsed_size_table.json`과 각 사이즈의 `validation.json`을 확인합니다.
OCR이 `39.5`를 `395`처럼 읽으면 코드가 가능한 소수점 복구를 시도하지만,
경고를 남깁니다. 경고가 있으면 원본 표와 대조해야 합니다.

## 6. OCR이 틀릴 때

OCR 결과를 확인·수정한 뒤 아래 형식으로 JSON 파일을 만듭니다.

```json
{
  "unit": "cm",
  "sizes": {
    "S": {
      "body_length": 65.0,
      "shoulder_width": 46.4,
      "chest_width": 53.0,
      "sleeve_length": 22.6
    },
    "M": {
      "body_length": 67.5,
      "shoulder_width": 48.4,
      "chest_width": 55.5,
      "sleeve_length": 23.3
    }
  }
}
```

그리고 `--size-table-json` 옵션으로 사용합니다.

```powershell
python generate_from_product_images.py `
  --front "inputs/new_product/front.png" `
  --back "inputs/new_product/back.png" `
  --size-chart "inputs/new_product/size_chart.png" `
  --size-table-json "reviewed_size_table.json" `
  --output "outputs/new_product"
```

## 7. 지원 범위와 한계

현재 어댑터가 안전하게 처리하는 대상은 기본적인 크루넥, set-in 소매 방식의
티셔츠 계열입니다.

- 라글란 소매, 후드, 복잡한 절개, 포켓: 기본 템플릿으로 정확히 재현되지 않음
- 바지·반바지: 하의 전용 치수 매핑이 아직 구현되지 않음
- 프린트·로고: 사진을 texture로 사용하지 않으므로 3D 패턴에 복사되지 않음
- 기본 실행 결과: 2D 봉제 패턴과 3D 패널 배치

실제 물리 드레이프 3D mesh는 GarmentCode의 별도 NVIDIA Warp 시뮬레이터를
설치한 경우에만 `--simulate` 옵션으로 생성할 수 있습니다. 시뮬레이터 없이
생긴 패턴 결과를 완성된 3D mesh라고 부르면 안 됩니다.

## 8. 자주 발생하는 오류

| 오류 | 원인 및 해결 |
| --- | --- |
| `python is not recognized` | Python을 설치하고 PATH를 적용한 새 터미널을 엽니다. |
| `front image does not exist` | 현재 폴더 기준 경로가 틀렸습니다. 절대 경로를 쓰거나 `--catalog-id`를 사용합니다. |
| `Tesseract could not load kor+eng` | Tesseract 및 Korean language data를 설치하거나 `--size-table-json`으로 검토한 치수표를 제공합니다. |
| 헤더를 찾지 못함 | 네 필수 치수 열이 보이도록 표를 잘라내거나, 검토한 JSON을 사용합니다. |
| 라글란/하의 카탈로그 항목 오류 | 의도된 차단입니다. 현재 티셔츠 어댑터에 맞지 않는 구조입니다. |
