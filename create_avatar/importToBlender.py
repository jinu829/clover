"""
createHuman.py가 만든 .mhm 아바타를 Blender로 자동으로 불러오는 스크립트.

불러오는 방법 (사람마다 자동 선택):
  1. MPFB2 (Blender용 MakeHuman 애드온)가 설치되어 있으면 .mhm을 직접 읽어
     몸체 메쉬 + 기본 뼈대(rig)를 만든다. MakeHuman 앱을 열 필요가 없다.
  2. MPFB2가 없거나 --source fbx 를 주면, MakeHuman에서 내보낸 같은 이름의
     .fbx(<이름>.mhm -> <이름>.fbx)를 찾아 불러온다.

불러온 뒤에는 measurements/<이름>.json 의 real_height_cm 으로 키를 맞춘다
(지금 .mhm에는 키 정보가 없어 모두 같은 키로 나오기 때문). 크기는 비율을
유지한 채 전체를 확대/축소한다.

실행 방법 1) 터미널에서 한 번에 (사람마다 <이름>.blend 저장)
  blender --background --python importToBlender.py -- avatars --out avatars
  blender --background --python importToBlender.py -- avatars/sample_person.mhm --out avatars --rig game_engine

실행 방법 2) Blender의 Scripting 탭에서 이 파일을 열고 실행
  아래 DEFAULT_* 값을 바꿔서 실행하면, 현재 씬에 사람마다 컬렉션을 만들어
  옆으로 나란히 불러온다 (저장은 하지 않음).
"""

import argparse
import importlib
import json
import os
import sys

import bpy
from mathutils import Vector

try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isdir(SCRIPT_DIR):  # Blender 텍스트 에디터에서 실행 시 경로가 가짜일 수 있음
        SCRIPT_DIR = os.getcwd()
except NameError:
    SCRIPT_DIR = os.getcwd()

# Scripting 탭에서 실행할 때 쓰는 기본값 (명령줄 인자가 있으면 무시됨)
DEFAULT_INPUT = os.path.join(SCRIPT_DIR, "avatars")             # .mhm 파일 또는 폴더 (createHuman.py가 저장하는 곳)
DEFAULT_MEASUREMENTS_DIR = os.path.join(SCRIPT_DIR, "measurements")  # 사진별 측정 JSON 폴더
DEFAULT_FBX_DIR = None                                          # None이면 .mhm과 같은 폴더에서 .fbx를 찾음

SPACING_M = 1.0  # 한 씬에 여러 명을 불러올 때 사람 사이 간격(m)


# ---------------------------------------------------------------------------
# MPFB2 연결
# ---------------------------------------------------------------------------

def _find_mpfb_human_service():
    """MPFB2의 HumanService 클래스를 찾는다. 없으면 None.

    Blender 4.2+ 확장(extension)은 bl_ext.<저장소>.mpfb 처럼 설치 위치에 따라
    모듈 이름이 달라지므로, MPFB 공식 예제(script_samples)와 같은 방식으로
    sys.modules에서 이름이 mpfb.services.humanservice 로 끝나는 모듈을 찾는다.
    아직 켜져 있지 않으면 한 번 켜 본다.
    """
    def lookup():
        for name in list(sys.modules):
            if name.endswith("mpfb.services.humanservice"):
                return getattr(importlib.import_module(name), "HumanService", None)
        return None

    service = lookup()
    if service is not None:
        return service

    import addon_utils
    for mod in addon_utils.modules():
        if mod.__name__ == "mpfb" or mod.__name__.endswith(".mpfb"):
            try:
                addon_utils.enable(mod.__name__, default_set=True)
            except Exception as e:  # 켜기 실패 시 FBX 방식으로 넘어감
                print(f"경고: MPFB2를 켜지 못했습니다 ({mod.__name__}): {e}")
            break
    return lookup()


def import_with_mpfb(human_service, mhm_path, rig):
    """MPFB2로 .mhm을 불러온다. rig: "PRESET"(기본 뼈대), "NONE", 또는 뼈대 이름"""
    settings = human_service.get_default_deserialization_settings()
    settings.update({
        "override_rig": rig,
        # .mhm에 눈/옷 등이 적혀 있지 않으므로 라이브러리 전체 탐색은 생략
        "bodypart_deep_search": False,
        "clothes_deep_search": False,
    })
    human_service.deserialize_from_mhm(mhm_path, settings)


# ---------------------------------------------------------------------------
# FBX 대체 경로
# ---------------------------------------------------------------------------

def find_fbx_for(mhm_path, fbx_dir=None):
    stem = os.path.splitext(os.path.basename(mhm_path))[0]
    folder = fbx_dir or os.path.dirname(mhm_path)
    for ext in (".fbx", ".FBX"):
        candidate = os.path.join(folder, stem + ext)
        if os.path.isfile(candidate):
            return candidate
    return None


def import_with_fbx(fbx_path):
    bpy.ops.import_scene.fbx(filepath=fbx_path)


# ---------------------------------------------------------------------------
# 공통 처리
# ---------------------------------------------------------------------------

def load_real_height_cm(stem, measurements_dir):
    """measurements/<stem>.json 의 real_height_cm 을 읽는다. 없으면 None"""
    if not measurements_dir:
        return None
    path = os.path.join(measurements_dir, f"{stem}.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f).get("real_height_cm")


def _new_person_collection(name):
    """사람 한 명을 담을 컬렉션을 만들고, 새로 생기는 오브젝트가 들어가도록 활성화"""
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    layer_collection = bpy.context.view_layer.layer_collection.children[collection.name]
    bpy.context.view_layer.active_layer_collection = layer_collection
    return collection


def _move_into_collection(objects, collection):
    for obj in objects:
        if collection not in obj.users_collection:
            collection.objects.link(obj)
        for other in list(obj.users_collection):
            if other is not collection:
                other.objects.unlink(obj)


def _mesh_height_m(meshes):
    """보이는(평가된) 메쉬 정점 기준 전체 높이(m)와 바닥 z"""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    min_z, max_z = float("inf"), float("-inf")
    for obj in meshes:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            world = evaluated.matrix_world
            for v in mesh.vertices:
                z = (world @ v.co).z
                min_z, max_z = min(min_z, z), max(max_z, z)
        finally:
            evaluated.to_mesh_clear()
    if min_z == float("inf"):
        return None, None
    return max_z - min_z, min_z


def fit_height(new_objects, real_height_cm):
    """새로 불러온 오브젝트 전체를 비율 유지한 채 real_height_cm 키로 맞추고 발을 바닥(z=0)에 둔다"""
    meshes = [o for o in new_objects if o.type == "MESH"]
    height_m, _ = _mesh_height_m(meshes)
    if not height_m:
        print("  경고: 메쉬 높이를 계산할 수 없어 키 맞추기를 건너뜁니다.")
        return

    factor = (real_height_cm / 100.0) / height_m
    roots = [o for o in new_objects if o.parent is None or o.parent not in new_objects]
    for root in roots:
        root.scale = root.scale * factor
        root.location = root.location * factor  # 원점 기준으로 함께 확대/축소
    bpy.context.view_layer.update()

    _, floor_z = _mesh_height_m(meshes)
    for root in roots:
        root.location.z -= floor_z
    print(f"  키 맞춤: {height_m * 100:.1f}cm -> {real_height_cm:.1f}cm (x{factor:.3f})")


def import_person(mhm_path, *, human_service, source, rig, measurements_dir, fbx_dir):
    """사람 한 명을 불러와 컬렉션에 담고, 새로 생긴 오브젝트 목록을 반환. 실패 시 None"""
    stem = os.path.splitext(os.path.basename(mhm_path))[0]
    fbx_path = find_fbx_for(mhm_path, fbx_dir)

    use_mpfb = source in ("auto", "mpfb") and human_service is not None
    if source == "mpfb" and human_service is None:
        print(f"[{stem}] 실패: MPFB2 애드온을 찾을 수 없습니다.")
        return None
    if not use_mpfb and fbx_path is None:
        print(f"[{stem}] 건너뜀: MPFB2가 없고 {stem}.fbx 도 찾지 못했습니다.")
        return None

    before = set(bpy.data.objects)
    collection = _new_person_collection(stem)

    if use_mpfb:
        print(f"[{stem}] MPFB2로 불러오는 중: {mhm_path}")
        import_with_mpfb(human_service, os.path.abspath(mhm_path), rig)
    else:
        print(f"[{stem}] FBX로 불러오는 중: {fbx_path}")
        import_with_fbx(fbx_path)

    new_objects = [o for o in bpy.data.objects if o not in before]
    _move_into_collection(new_objects, collection)

    # MPFB/FBX가 붙이는 기본 이름 대신 사진 이름으로 정리 (정점이 가장 많은 메쉬 = 몸체)
    for obj in new_objects:
        if obj.type == "ARMATURE" and obj.parent is None:
            obj.name = stem
    meshes = [o for o in new_objects if o.type == "MESH"]
    if meshes:
        max(meshes, key=lambda o: len(o.data.vertices)).name = f"{stem}.body"

    real_height_cm = load_real_height_cm(stem, measurements_dir)
    if real_height_cm:
        fit_height(new_objects, real_height_cm)
    else:
        print(f"  measurements/{stem}.json 이 없어 키 맞추기를 건너뜁니다.")

    return new_objects


def collect_mhm_files(input_path):
    if os.path.isdir(input_path):
        return sorted(
            os.path.join(input_path, name)
            for name in os.listdir(input_path)
            if name.lower().endswith(".mhm")
        )
    return [input_path]


def run(input_path, *, out_dir=None, source="auto", rig="PRESET",
        measurements_dir=DEFAULT_MEASUREMENTS_DIR, fbx_dir=DEFAULT_FBX_DIR, export_fbx=False):
    mhm_files = collect_mhm_files(input_path)
    if not mhm_files:
        print(f".mhm 파일을 찾지 못했습니다: {input_path}")
        return

    human_service = _find_mpfb_human_service() if source != "fbx" else None
    if source != "fbx":
        print("MPFB2: " + ("사용 가능" if human_service else "찾을 수 없음 (FBX로 대체)"))

    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    succeeded = 0
    for index, mhm_path in enumerate(mhm_files):
        stem = os.path.splitext(os.path.basename(mhm_path))[0]
        if out_dir:
            # 사람마다 빈 파일에서 시작해 <이름>.blend 로 따로 저장
            bpy.ops.wm.read_homefile(use_empty=True)

        new_objects = import_person(
            mhm_path, human_service=human_service, source=source, rig=rig,
            measurements_dir=measurements_dir, fbx_dir=fbx_dir,
        )
        if new_objects is None:
            continue
        succeeded += 1

        if out_dir:
            blend_path = os.path.abspath(os.path.join(out_dir, f"{stem}.blend"))
            bpy.ops.wm.save_as_mainfile(filepath=blend_path)
            print(f"  저장: {blend_path}")
            if export_fbx:
                fbx_out = os.path.abspath(os.path.join(out_dir, f"{stem}.fbx"))
                bpy.ops.export_scene.fbx(filepath=fbx_out, add_leaf_bones=False)
                print(f"  FBX 내보내기: {fbx_out}")
        else:
            # 한 씬에 여러 명: 옆으로 나란히 배치
            for obj in new_objects:
                if obj.parent is None or obj.parent not in new_objects:
                    obj.location.x += index * SPACING_M

    print(f"완료: {succeeded}/{len(mhm_files)}명 불러옴")


def _parse_args():
    # blender ... --python importToBlender.py -- <인자들>  의 "--" 뒤만 읽는다
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=".mhm 아바타를 Blender로 불러옵니다.")
    parser.add_argument("input_path", nargs="?", default=DEFAULT_INPUT,
                        help=".mhm 파일 또는 .mhm이 들어있는 폴더 (기본값: 이 스크립트 옆 avatars 폴더)")
    parser.add_argument("--out", default=None,
                        help="사람마다 <이름>.blend 를 저장할 폴더. 생략하면 현재 씬에 모두 불러옴")
    parser.add_argument("--source", choices=["auto", "mpfb", "fbx"], default="auto",
                        help="auto: MPFB2 우선, 없으면 FBX / mpfb: MPFB2만 / fbx: FBX만")
    parser.add_argument("--rig", default="PRESET",
                        help="MPFB2 뼈대: PRESET(기본 뼈대), NONE(뼈대 없음), game_engine, mixamo 등")
    parser.add_argument("--measurements-dir", default=DEFAULT_MEASUREMENTS_DIR,
                        help="키 맞추기에 쓸 측정 JSON 폴더")
    parser.add_argument("--fbx-dir", default=DEFAULT_FBX_DIR,
                        help="FBX 대체 경로에서 <이름>.fbx 를 찾을 폴더 (기본값: .mhm과 같은 폴더)")
    parser.add_argument("--export-fbx", action="store_true",
                        help="--out 과 함께 쓰면 키를 맞춘 결과를 <이름>.fbx 로도 내보냄")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    run(
        args.input_path,
        out_dir=args.out,
        source=args.source,
        rig=args.rig,
        measurements_dir=args.measurements_dir,
        fbx_dir=args.fbx_dir,
        export_fbx=args.export_fbx,
    )
