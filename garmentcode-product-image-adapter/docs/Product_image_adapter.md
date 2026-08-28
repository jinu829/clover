# Product-image size adapter

`generate_from_product_images.py` is an adapter around GarmentCode; it does
not alter the GarmentCode core or paste product photos onto a garment texture.
The front and back files are copied as reference evidence and are used only for
a conservative colour estimate and documented T-shirt-template fallback.

The size chart is the source of measurement values. The adapter preprocesses
the image, removes detected table rules, runs Tesseract (`kor+eng`), maps the
headers below, applies a clearly recorded lost-decimal repair when appropriate,
then writes `parsed_size_table.json` before any patterns are generated.

| Canonical field | Accepted headers |
| --- | --- |
| `body_length` | 총장, 기장, 총길이, body length, length |
| `shoulder_width` | 어깨너비, 어깨 너비, 어깨폭, 어깨, shoulder width |
| `chest_width` | 가슴단면, 가슴 단면, 가슴폭, chest width |
| `sleeve_length` | 소매길이, 소매 길이, 소매, sleeve length |

`chest_width` is explicitly treated as a flat garment width, not a full chest
circumference. The adapter maps it to twice that value for the four torso panel
widths, then records the mapping and measured generated value in
`validation.json`.

## Setup

Use a Python environment compatible with the repository (the project documents
Python 3.9), install GarmentCode, then the adapter extras. Tesseract itself and
its Korean language data are system packages and are not installed by pip.

```powershell
cd GarmentCode-main
python -m pip install -e .
python -m pip install -r requirements-product-adapter.txt
```

## Run

```powershell
python generate_from_product_images.py `
  --front inputs/garment_001/front.png `
  --back inputs/garment_001/back.png `
  --size-chart inputs/garment_001/size_chart.png `
  --output outputs/garment_001
```

If OCR needs a human correction, edit a reviewed JSON file in the same schema
as `parsed_size_table.json` and pass it explicitly. This keeps the image as the
original source while preventing an unverified OCR result from producing a
garment.

```powershell
python generate_from_product_images.py ... `
  --size-table-json reviewed_size_table.json
```

Each valid size row produces a separate directory with `pattern_<SIZE>.json`,
GarmentCode's native pattern exports, the precise design/body inputs, and
`measurements.json`/`validation.json`. The count is determined from valid rows,
not a hard-coded list of sizes.

## Reviewed local catalog

`assets/product_catalog.json` records a visual classification of the supplied
`옷 파일/옷 파일` data. It identifies A--E as short-sleeve tops, F--J as
long-sleeve tops (F/G/J are raglan), K--O as shorts, and P--T as denim pants.
The catalog records unsupported construction honestly: a raglan sleeve is not a
set-in sleeve, and the current adapter does not map pants measurements. Those
items stop with an explanatory error instead of being turned into a T-shirt.

For a reviewed compatible item, the three paths and its style metadata can be
loaded directly:

```powershell
python generate_from_product_images.py `
  --catalog-id A `
  --catalog-root "../옷 파일/옷 파일" `
  --output outputs/A
```

When launched from `GarmentCode-main`, the bundled catalog also resolves a
missing short front filename such as `--front A1.png` to its local A1/A2/A3
triplet. For unambiguous and portable runs, prefer `--catalog-id`.

## About 3D meshes

GarmentCode's regular command-line pattern generation creates sewing-pattern
JSON and 3D panel placement, not a physically draped mesh. The repository's
actual mesh path is `test_garment_sim.py`, which depends on the separately
installed NVIDIA Warp GarmentCode simulator. After that dependency is working,
add `--simulate`; only then will the adapter copy a simulator-produced mesh as
`garment_<SIZE>.<extension>`. Without the flag it intentionally produces no
fake mesh and states that fact in the console.
