#!/usr/bin/env python3
"""Generate size-specific GarmentCode T-shirt patterns from product references.

Product photos are style references only: they are never copied into a UV
texture or converted to mesh geometry.  The size-chart image is parsed into a
reviewable JSON file before GarmentCode is invoked.

The script deliberately does *not* call a pattern a "3D mesh".  Pass
``--simulate`` only on an installation with the official Warp simulator; a
mesh is then exported only if the simulator actually produces one.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parent
DEFAULT_BODY = ROOT / "assets" / "bodies" / "mean_all.yaml"
DEFAULT_DESIGN = ROOT / "assets" / "design_params" / "t-shirt.yaml"
DEFAULT_SIM_PROPS = ROOT / "assets" / "Sim_props" / "default_sim_props.yaml"
DEFAULT_CATALOG = ROOT / "assets" / "product_catalog.json"

MEASUREMENT_ALIASES = {
    "body_length": ["총장", "기장", "총길이", "body length", "length"],
    "shoulder_width": ["어깨너비", "어깨 너비", "어깨폭", "어깨", "shoulder width"],
    "chest_width": ["가슴단면", "가슴 단면", "가슴폭", "chest width"],
    "sleeve_length": ["소매길이", "소매 길이", "소매", "sleeve length"],
}
REQUIRED_MEASUREMENTS = tuple(MEASUREMENT_ALIASES)
SIZE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+\-/.]*$")
NUMBER_TOKEN = re.compile(r"(?<!\d)(\d{1,4}(?:[.,]\d+)?)")


class ProductInputError(ValueError):
    """A product input cannot be parsed safely enough to generate a pattern."""


def _require_file(path: Path, label: str) -> Path:
    path = path.resolve()
    if not path.is_file():
        raise ProductInputError(f"{label} does not exist or is not a file: {path}")
    return path


def _normalise_text(value: str) -> str:
    return re.sub(r"[\s_\-:|/]+", "", value.lower()).strip()


def _header_key(value: str) -> Optional[str]:
    normalised = _normalise_text(value)
    for key, aliases in MEASUREMENT_ALIASES.items():
        if any(_normalise_text(alias) in normalised for alias in aliases):
            return key
    return None


def _read_image_rgb(path: Path):
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required for reference-image analysis. Install the adapter "
            "requirements first."
        ) from exc
    with Image.open(path) as image:
        return image.convert("RGB")


def analyse_reference_images(front: Path, back: Path, catalog_entry: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Return conservative style evidence without treating photos as textures.

    GarmentCode contains a robust generic short-sleeve top template, but no
    trained image classifier.  Auto mode therefore records an explicit
    fallback rather than pretending that a photo uniquely determines pattern
    construction.
    """
    pixels: List[Tuple[int, int, int]] = []
    for image_path in (front, back):
        image = _read_image_rgb(image_path)
        width, height = image.size
        # The centre crop reduces white studio backgrounds and black borders.
        left, top, right, bottom = width // 5, height // 5, width * 4 // 5, height * 4 // 5
        pixels.extend(image.crop((left, top, right, bottom)).resize((64, 64)).getdata())

    non_background = [p for p in pixels if max(p) < 245 and max(p) - min(p) < 130]
    sample = non_background or pixels
    mean = tuple(round(sum(pixel[i] for pixel in sample) / len(sample)) for i in range(3))
    brightness = sum(mean) / 3
    if brightness < 60:
        colour = "black"
    elif brightness > 210:
        colour = "white"
    elif max(mean) - min(mean) < 25:
        colour = "gray"
    else:
        colour = "dominant_rgb_%02x%02x%02x" % mean

    fallback = {
        "category": "T-shirt",
        "sleeve": "short sleeve",
        "neck": "crew neck",
        "body": "straight body",
        "front": "unknown/plain assumed",
        "back": "unknown/plain assumed",
        "base_color": colour,
        "photo_role": "style reference only; not used as a texture",
        "classification_confidence": "fallback",
        "warnings": [
            "No trained garment classifier is bundled with GarmentCode. "
            "The documented safe fallback template (short-sleeve crew-neck T-shirt) was selected."
        ],
    }
    if not catalog_entry:
        return fallback
    # The catalog is an explicit visual review of the supplied product images.
    # It takes precedence over the generic fallback but remains separate from
    # the measurement table and never becomes a texture input.
    reviewed = dict(catalog_entry)
    reviewed.update({
        "base_color": catalog_entry.get("colour", colour),
        "photo_role": "style reference only; not used as a texture",
        "classification_confidence": "human-reviewed local catalog",
        "catalog_source": "assets/product_catalog.json",
    })
    return reviewed


def load_catalog_entry(catalog_path: Path, item_id: str, catalog_root: Path) -> Tuple[Dict[str, Any], Path, Path, Path]:
    with catalog_path.open(encoding="utf-8") as handle:
        catalog = json.load(handle)
    try:
        entry = dict(catalog["items"][item_id.upper()])
    except KeyError as exc:
        raise ProductInputError(f"Catalog item '{item_id}' was not found in {catalog_path}.") from exc
    item_dir = catalog_root / entry["folder"]
    front = _require_file(item_dir / entry["front"], f"catalog {item_id} front image")
    back = _require_file(item_dir / entry["back"], f"catalog {item_id} back image")
    chart = _require_file(item_dir / entry["size_chart"], f"catalog {item_id} size chart")
    return entry, front, back, chart


def infer_catalog_entry_from_front_filename(catalog_path: Path, front_path: Path, catalog_root: Optional[Path]) -> Optional[Tuple[Dict[str, Any], Path, Path, Path]]:
    """Resolve ``A1.png``-style local inputs without requiring a long path.

    This is intentionally limited to a filename uniquely listed in the
    reviewed catalog. Arbitrary missing input paths still fail normally.
    """
    if not catalog_path.is_file():
        return None
    with catalog_path.open(encoding="utf-8") as handle:
        catalog = json.load(handle)
    matches = [item_id for item_id, entry in catalog["items"].items() if entry["front"].lower() == front_path.name.lower()]
    if len(matches) != 1:
        return None
    root = catalog_root or (ROOT.parent / catalog["source_root_hint"])
    return load_catalog_entry(catalog_path, matches[0], root.resolve())


def _preprocess_for_ocr(image_path: Path, debug_dir: Path):
    """Upscale, normalise contrast, and remove table rules when OpenCV exists."""
    image = _read_image_rgb(image_path)
    debug_dir.mkdir(parents=True, exist_ok=True)
    try:
        import cv2
        import numpy as np
        from PIL import Image
    except ImportError:
        debug_path = debug_dir / "size_chart_preprocessed.png"
        image.save(debug_path)
        return image, ["OpenCV unavailable: OCR used the original image without table-line removal."], debug_path

    rgb = np.asarray(image)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    scale = max(1.0, 1800.0 / max(gray.shape))
    if scale != 1.0:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 9
    )
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(20, gray.shape[1] // 20), 1)))
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(20, gray.shape[0] // 20))))
    text_mask = cv2.bitwise_not(cv2.bitwise_or(horizontal, vertical))
    cleaned = cv2.bitwise_and(gray, gray, mask=text_mask)
    # Tesseract expects dark text on a light background.
    cleaned = cv2.bitwise_not(cleaned)
    debug_path = debug_dir / "size_chart_preprocessed.png"
    Image.fromarray(cleaned).save(debug_path)
    return Image.fromarray(cleaned), [], debug_path


def _ocr_tokens(image) -> List[Dict[str, Any]]:
    try:
        import pytesseract
        from pytesseract import Output
    except ImportError as exc:
        raise RuntimeError(
            "OCR requires pytesseract and a system Tesseract installation (kor+eng "
            "language data for Korean tables). See requirements-product-adapter.txt."
        ) from exc

    try:
        data = pytesseract.image_to_data(image, lang="kor+eng", config="--psm 6", output_type=Output.DICT)
    except pytesseract.TesseractError as exc:
        raise ProductInputError(
            "Tesseract could not load kor+eng. Install the Korean language data or "
            "supply an OCR sidecar with --size-table-json."
        ) from exc

    tokens = []
    for index, raw_text in enumerate(data["text"]):
        text = raw_text.strip()
        try:
            confidence = float(data["conf"][index])
        except (ValueError, TypeError):
            confidence = -1
        if text and confidence >= 20:
            tokens.append({
                "text": text,
                "x": int(data["left"][index]),
                "y": int(data["top"][index]),
                "w": int(data["width"][index]),
                "h": int(data["height"][index]),
                "confidence": confidence,
            })
    if not tokens:
        raise ProductInputError("No readable text was found in the size-chart image.")
    return tokens


def _group_rows(tokens: Sequence[Mapping[str, Any]]) -> List[List[Mapping[str, Any]]]:
    ordered = sorted(tokens, key=lambda item: (item["y"] + item["h"] / 2, item["x"]))
    median_height = sorted(item["h"] for item in ordered)[len(ordered) // 2]
    tolerance = max(10, median_height * 0.8)
    rows: List[List[Mapping[str, Any]]] = []
    centres: List[float] = []
    for token in ordered:
        centre = token["y"] + token["h"] / 2
        if rows and abs(centre - centres[-1]) <= tolerance:
            rows[-1].append(token)
            centres[-1] = sum(item["y"] + item["h"] / 2 for item in rows[-1]) / len(rows[-1])
        else:
            rows.append([token])
            centres.append(centre)
    return [sorted(row, key=lambda item: item["x"]) for row in rows]


def _find_header_row(rows: Sequence[Sequence[Mapping[str, Any]]]) -> Tuple[int, Dict[str, float]]:
    best: Optional[Tuple[int, Dict[str, float]]] = None
    for index, row in enumerate(rows):
        by_key: Dict[str, float] = {}
        for token in row:
            key = _header_key(str(token["text"]))
            if key:
                by_key[key] = token["x"] + token["w"] / 2
        if best is None or len(by_key) > len(best[1]):
            best = (index, by_key)
    if best is None or len(best[1]) < len(REQUIRED_MEASUREMENTS):
        found = [] if best is None else list(best[1])
        raise ProductInputError(
            "Could not identify all required size-chart headers. Found %s; required %s. "
            "Inspect outputs/.../ocr_debug/size_chart_preprocessed.png or correct the OCR sidecar."
            % (found, list(REQUIRED_MEASUREMENTS))
        )
    return best


def _parse_number(text: str, field: str, warnings: List[str]) -> Optional[float]:
    match = NUMBER_TOKEN.search(text.replace("O", "0").replace("o", "0"))
    if not match:
        return None
    raw = match.group(1).replace(",", ".")
    value = float(raw)
    # Typical apparel measures are in cm. A three-digit OCR token such as 395
    # is commonly a lost decimal from 39.5. Never silently apply this repair.
    if value > 150 and raw.isdigit() and len(raw) in (3, 4):
        repaired = value / 10
        if 5 <= repaired <= 150:
            warnings.append(
                f"Possible OCR decimal repair for {field}: '{raw}' -> {repaired:.1f} cm. Verify the source cell."
            )
            value = repaired
    if not 1 <= value <= 300:
        warnings.append(f"Implausible {field} value {value:g} cm; row was rejected.")
        return None
    return value


def _nearest_token(row: Sequence[Mapping[str, Any]], target_x: float) -> Mapping[str, Any]:
    return min(row, key=lambda item: abs((item["x"] + item["w"] / 2) - target_x))


def parse_size_chart_image(image_path: Path, debug_dir: Path) -> Dict[str, Any]:
    image, preprocessing_warnings, _ = _preprocess_for_ocr(image_path, debug_dir)
    tokens = _ocr_tokens(image)
    rows = _group_rows(tokens)
    header_index, columns = _find_header_row(rows)
    size_x = min(token["x"] + token["w"] / 2 for token in rows[header_index])
    sizes: Dict[str, Dict[str, float]] = {}
    warnings = list(preprocessing_warnings)
    diagnostics = []
    for row in rows[header_index + 1:]:
        first = _nearest_token(row, size_x)
        name = str(first["text"]).strip().upper()
        if not SIZE_TOKEN.fullmatch(name) or _parse_number(name, "size", []) is not None:
            continue
        measurements: Dict[str, float] = {}
        row_warnings: List[str] = []
        for field, column_x in columns.items():
            token = _nearest_token(row, column_x)
            # A distant nearest token indicates a partial/misaligned OCR row.
            if abs((token["x"] + token["w"] / 2) - column_x) > max(80, token["w"] * 3):
                continue
            value = _parse_number(str(token["text"]), field, row_warnings)
            if value is not None:
                measurements[field] = value
        diagnostics.append({"row": [str(token["text"]) for token in row], "size_candidate": name, "measurements": measurements})
        if set(measurements) == set(REQUIRED_MEASUREMENTS):
            if name in sizes:
                warnings.append(f"Duplicate size row '{name}' ignored after the first valid row.")
            else:
                sizes[name] = measurements
                warnings.extend(f"{name}: {warning}" for warning in row_warnings)

    if not sizes:
        raise ProductInputError(
            "No complete size rows were parsed. A pattern was not generated; inspect OCR diagnostics and correct the table."
        )
    return {"unit": "cm", "sizes": sizes, "warnings": warnings, "ocr_rows": diagnostics}


def load_size_table_sidecar(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        parsed = json.load(handle)
    if parsed.get("unit") != "cm" or not isinstance(parsed.get("sizes"), dict):
        raise ProductInputError("The OCR sidecar must contain unit='cm' and a sizes object.")
    valid: Dict[str, Dict[str, float]] = {}
    for size, values in parsed["sizes"].items():
        missing = set(REQUIRED_MEASUREMENTS) - set(values)
        if missing:
            raise ProductInputError(f"Size {size} is missing required measurements: {sorted(missing)}")
        valid[str(size)] = {key: float(values[key]) for key in REQUIRED_MEASUREMENTS}
    return {"unit": "cm", "sizes": valid, "warnings": ["Used user-supplied parsed size table; image OCR was bypassed."]}


def _load_yaml(path: Path) -> Dict[str, Any]:
    import yaml
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _copy_reference_images(front: Path, back: Path, output: Path) -> None:
    target = output / "reference"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(front, target / "front.png")
    shutil.copy2(back, target / "back.png")


def make_body_for_measurements(body_file: Path, values: Mapping[str, float]):
    """Map flat chest width and shoulder span to the non-fitted Shirt panels.

    ``chest_width`` is a *flat garment width*, so its GarmentCode panel
    circumference is twice that value.  This mapping is intentionally kept
    here (outside GarmentCode core) and recorded per output size.
    """
    from assets.bodies.body_params import BodyParameters

    body = BodyParameters(str(body_file))
    chest_circumference = values["chest_width"] * 2.0
    shoulder = values["shoulder_width"]
    if shoulder >= chest_circumference:
        raise ProductInputError(
            f"Shoulder width ({shoulder:g} cm) must be smaller than chest circumference "
            f"({chest_circumference:g} cm) for the straight T-shirt template."
        )
    # In tee.TorsoFrontHalfPanel, 2 * front_width is the front shoulder span.
    # Solving its fraction gives this body back-width proxy while preserving
    # the original body bust circumference for armhole calculations.
    body["back_width"] = body["bust"] * (1.0 - shoulder / chest_circumference)
    return body


def design_for_measurements(design_file: Path, body, values: Mapping[str, float]) -> Dict[str, Any]:
    design = _load_yaml(design_file)["design"]
    design = copy.deepcopy(design)
    chest_circumference = values["chest_width"] * 2.0
    design["meta"]["upper"]["v"] = "Shirt"
    design["meta"]["bottom"]["v"] = None
    design["meta"]["wb"]["v"] = None
    design["shirt"]["width"]["v"] = chest_circumference / body["bust"]
    design["shirt"]["flare"]["v"] = 1.0
    design["sleeve"]["sleeveless"]["v"] = False
    design["sleeve"]["cuff"]["type"]["v"] = None
    design["collar"]["f_collar"]["v"] = "CircleNeckHalf"
    design["collar"]["b_collar"]["v"] = "CircleNeckHalf"
    design["collar"]["component"]["style"]["v"] = None

    # The highest front shoulder point is length + shoulder inclination in
    # tee.py.  Set its vertical 2D panel span to the supplied total length.
    front_half_width = values["shoulder_width"] / 2.0
    shoulder_rise = __import__("math").tan(__import__("math").radians(body["_shoulder_incl"])) * front_half_width
    core_length = values["body_length"] - shoulder_rise
    if core_length <= 5:
        raise ProductInputError("Body length is too short for the selected template and shoulder slope.")
    design["shirt"]["length"]["v"] = core_length / body["waist_line"]
    return design


def _upper_from_piece(piece):
    if not piece.subs:
        raise RuntimeError("GarmentCode returned a MetaGarment with no upper component.")
    return piece.subs[0]


def _measure_generated(piece) -> Dict[str, float]:
    upper = _upper_from_piece(piece)
    right = upper.right
    left = upper.left
    # Actual panel dimensions, measured from the generated component objects.
    chest_circumference = right.ftorso.width + right.btorso.width + left.ftorso.width + left.btorso.width
    body_length = max(right.ftorso.length(), left.ftorso.length())
    shoulder_width = right.ftorso.width + left.ftorso.width
    sleeve_length = max(right.sleeve.f_sleeve.length(), left.sleeve.f_sleeve.length())
    return {
        "body_length": float(body_length),
        "shoulder_width": float(shoulder_width),
        "chest_width": float(chest_circumference / 2.0),
        "sleeve_length": float(sleeve_length),
    }


def _build_piece(body, design, name: str):
    from assets.garment_programs.meta_garment import MetaGarment
    return MetaGarment(name, body, copy.deepcopy(design))


def _calibrate_sleeve(body, design: Dict[str, Any], desired_cm: float) -> None:
    """Solve the monotonic GarmentCode sleeve ratio against generated geometry."""
    low, high = 0.02, 1.5
    best_ratio = design["sleeve"]["length"]["v"]
    best_error = float("inf")
    for _ in range(22):
        ratio = (low + high) / 2.0
        candidate = copy.deepcopy(design)
        candidate["sleeve"]["length"]["v"] = ratio
        generated = _measure_generated(_build_piece(body, candidate, "sleeve_calibration"))["sleeve_length"]
        error = abs(generated - desired_cm)
        if error < best_error:
            best_ratio, best_error = ratio, error
        if generated < desired_cm:
            low = ratio
        else:
            high = ratio
    design["sleeve"]["length"]["v"] = best_ratio


def _write_json(path: Path, content: Mapping[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(content, handle, ensure_ascii=False, indent=2)


def generate_size(size: str, values: Mapping[str, float], output: Path, body_file: Path, design_file: Path, tolerance: float) -> Tuple[Path, Path]:
    body = make_body_for_measurements(body_file, values)
    design = design_for_measurements(design_file, body, values)
    _calibrate_sleeve(body, design, values["sleeve_length"])
    piece = _build_piece(body, design, f"Tshirt_{size}")
    if piece.is_self_intersecting():
        raise ProductInputError(f"Generated {size} template is self-intersecting; no output was exported.")
    pattern = piece.assembly()
    size_dir = output / size
    size_dir.mkdir(parents=True, exist_ok=True)
    # GarmentCode serialization is the source-of-truth pattern export.
    pattern.serialize(size_dir, to_subfolder=False, tag=size, with_3d=True, with_text=True, view_ids=False, with_printable=True)
    _write_json(size_dir / f"pattern_{size}.json", pattern.spec)
    body.save(size_dir, name="body_measurements")
    with (size_dir / f"design_{size}.yaml").open("w", encoding="utf-8") as handle:
        import yaml
        yaml.safe_dump({"design": design}, handle, allow_unicode=True, sort_keys=False)

    actual = _measure_generated(piece)
    errors = {key: round(actual[key] - float(values[key]), 3) for key in REQUIRED_MEASUREMENTS}
    validation = {
        "unit": "cm",
        "input_measurements": {key: float(values[key]) for key in REQUIRED_MEASUREMENTS},
        "generated_measurements": {key: round(actual[key], 3) for key in REQUIRED_MEASUREMENTS},
        "error_cm": errors,
        "tolerance_cm": tolerance,
        "passed": all(abs(error) <= tolerance for error in errors.values()),
        "measurement_notes": {
            "chest_width": "Generated panel circumference divided by 2; input is a flat garment chest width.",
            "body_length": "Vertical front torso-panel span from hem to highest shoulder point.",
            "shoulder_width": "Distance between front left/right shoulder endpoints in the 2D panel construction.",
            "sleeve_length": "Generated sleeve panel longitudinal length.",
        },
    }
    _write_json(size_dir / "measurements.json", {"unit": "cm", "measurements": validation["input_measurements"]})
    _write_json(size_dir / "validation.json", validation)
    return size_dir, next(size_dir.glob(f"*{size}_specification.json"))


def _collect_new_meshes(root: Path, before: Iterable[Path]) -> List[Path]:
    before_set = {path.resolve() for path in before}
    suffixes = {".obj", ".ply", ".glb", ".gltf", ".usd", ".usda", ".usdc"}
    return [path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in suffixes and path.resolve() not in before_set]


def simulate_mesh(specification: Path, size_dir: Path, sim_props: Path) -> Path:
    """Invoke the official simulator and copy a genuinely created mesh artifact."""
    before = list(ROOT.rglob("*.obj")) + list(ROOT.rglob("*.ply")) + list(ROOT.rglob("*.glb")) + list(ROOT.rglob("*.usd"))
    command = [sys.executable, str(ROOT / "test_garment_sim.py"), "--pattern_spec", str(specification), "--sim_config", str(sim_props)]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    (size_dir / "simulation.log").write_text(completed.stdout + "\n" + completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"Warp simulation failed for {size_dir.name}; inspect {size_dir / 'simulation.log'}")
    meshes = _collect_new_meshes(ROOT, before)
    if not meshes:
        raise RuntimeError("Warp simulation reported success but no mesh artifact was produced; no garment file was created.")
    mesh = max(meshes, key=lambda path: path.stat().st_mtime)
    destination = size_dir / f"garment_{size_dir.name}{mesh.suffix.lower()}"
    shutil.copy2(mesh, destination)
    return destination


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--front", type=Path, help="Product front reference PNG")
    parser.add_argument("--back", type=Path, help="Product back reference PNG")
    parser.add_argument("--size-chart", type=Path, help="Size-chart PNG")
    parser.add_argument("--output", required=True, type=Path, help="Output garment directory")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG, help="Reviewed local product catalog JSON")
    parser.add_argument("--catalog-id", help="Catalog item ID (A through T); resolves the three image paths")
    parser.add_argument("--catalog-root", type=Path, help="Directory containing catalog folders 상의 and 하의")
    parser.add_argument("--size-table-json", type=Path, help="Optional reviewed parsed_size_table.json; bypasses OCR")
    parser.add_argument("--body", type=Path, default=DEFAULT_BODY, help="GarmentCode body YAML")
    parser.add_argument("--design", type=Path, default=DEFAULT_DESIGN, help="GarmentCode T-shirt design YAML")
    parser.add_argument("--tolerance-cm", type=float, default=0.5, help="Validation tolerance in centimetres")
    parser.add_argument("--simulate", action="store_true", help="Run the separately installed official Warp draping simulator")
    parser.add_argument("--sim-props", type=Path, default=DEFAULT_SIM_PROPS, help="Official Warp simulation properties YAML")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        catalog_entry = None
        if args.catalog_id:
            catalog_path = _require_file(args.catalog, "product catalog")
            if not args.catalog_root:
                raise ProductInputError("--catalog-id requires --catalog-root (the directory containing 상의 and 하의).")
            catalog_entry, front, back, chart = load_catalog_entry(
                catalog_path, args.catalog_id, args.catalog_root.resolve()
            )
            if catalog_entry.get("generation_status", "supported").startswith("blocked"):
                raise ProductInputError(
                    f"Catalog item {args.catalog_id.upper()} is classified as {catalog_entry['category']} and is not sent "
                    f"to the T-shirt adapter: {catalog_entry.get('blocking_reason', 'no compatible adapter') }"
                )
        else:
            if not (args.front and args.back and args.size_chart):
                raise ProductInputError("Provide --front, --back, and --size-chart, or use --catalog-id with --catalog-root.")
            # Convenience for the bundled data: running from GarmentCode-main
            # with --front A1.png now resolves its reviewed A1/A2/A3 triplet.
            inferred = infer_catalog_entry_from_front_filename(
                args.catalog, args.front, args.catalog_root
            ) if not args.front.is_file() else None
            if inferred:
                catalog_entry, front, back, chart = inferred
                print(f"Resolved {args.front.name} through local catalog to {front.parent}")
            else:
                front = _require_file(args.front, "front image")
                back = _require_file(args.back, "back image")
                chart = _require_file(args.size_chart, "size chart")
        body_file = _require_file(args.body, "body YAML")
        design_file = _require_file(args.design, "design YAML")
        if args.size_table_json:
            _require_file(args.size_table_json, "size-table JSON")
        if args.simulate:
            _require_file(args.sim_props, "simulation properties")
        output = args.output.resolve()
        output.mkdir(parents=True, exist_ok=True)

        print("[1/8] Loading reference images")
        style = analyse_reference_images(front, back, catalog_entry)
        print("[2/8] Detecting garment type")
        print(f"Detected garment: {style['category']} ({style['classification_confidence']} template selection)")
        print("[3/8] Reading size chart image")
        parsed = load_size_table_sidecar(args.size_table_json) if args.size_table_json else parse_size_chart_image(chart, output / "ocr_debug")
        _write_json(output / "parsed_size_table.json", parsed)
        _write_json(output / "reference_analysis.json", style)
        _copy_reference_images(front, back, output)

        print("[4/8] Detected measurements")
        print("SIZE | LENGTH | SHOULDER | CHEST | SLEEVE")
        for size, values in parsed["sizes"].items():
            print(f"{size:4} | {values['body_length']:6g} | {values['shoulder_width']:8g} | {values['chest_width']:5g} | {values['sleeve_length']:6g}")
        print("[5/8] Selecting GarmentCode template")
        print("Selected template: MetaGarment / Shirt (non-fitted T-shirt panels)")
        print("[6/8] Generating garments")
        generated: List[Tuple[str, Path, Path]] = []
        for size, values in parsed["sizes"].items():
            print(f"Generating {size}...", end=" ", flush=True)
            size_dir, spec = generate_size(size, values, output, body_file, design_file, args.tolerance_cm)
            generated.append((size, size_dir, spec))
            print("SUCCESS")

        print("[7/8] Validating measurements")
        failures = []
        for size, size_dir, _ in generated:
            validation = json.loads((size_dir / "validation.json").read_text(encoding="utf-8"))
            if not validation["passed"]:
                failures.append(size)
                print(f"WARNING: {size} exceeds {args.tolerance_cm:g} cm tolerance; inspect validation.json")
        print("[8/8] Exporting models")
        if args.simulate:
            for size, size_dir, spec in generated:
                mesh = simulate_mesh(spec, size_dir, args.sim_props)
                print(f"Exported actual simulated mesh: {mesh.name}")
        else:
            print("2D patterns exported. No 3D mesh was claimed or created; rerun with --simulate after installing Warp.")
        if failures:
            print("Completed with validation warnings: " + ", ".join(failures))
            return 2
        print("Completed.")
        return 0
    except (ProductInputError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
