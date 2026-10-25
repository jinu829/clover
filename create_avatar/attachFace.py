"""
KeenTools(FaceBuilder) 머리를 importToBlender.py가 만든 MakeHuman 몸에 합치는 스크립트.

전체 흐름에서 이 스크립트가 맡는 부분 (3단계 = keentools_3d/main.py 결과물):
  4. 정렬      : FaceBuilder 머리를 MakeHuman 머리 위치·회전·크기에 자동으로 맞춤
                 (코끝·정수리로 대략 맞춘 뒤 얼굴 표면 ICP로 미세 조정)
  5. 가중치    : 몸에 face_fit 정점 그룹을 만듦 (얼굴 1 -> 턱 아래·귀·뒷머리 0)
  6~7. 변형    : 얼굴 정점을 FaceBuilder 표면에 투영해 "FaceFit" 셰이프키로 저장
                 (입속·눈구멍·눈알·이·관절 헬퍼는 주변 얼굴을 따라 이동)
  8. 눈·리그   : MPFB2 refit으로 눈알·눈썹·속눈썹과 뼈대를 새 얼굴에 다시 맞춤
  9. 텍스처    : FaceBuilder 텍스처를 몸 UV로 베이크하고 face_fit으로 피부와 섞음
  10. 저장     : <이름>.blend 저장 (FaceBuilder 머리는 숨겨서 같이 보관)

필요한 것
  - Blender 4.x 이상 + MPFB2 (importToBlender.py와 같음)
  - data/face_fit_hm08.json (tools/makeFaceFitData.py로 만든 것, 저장소에 포함)
  - 머리 파일: main.py가 받은 zip(OBJ+JPG) 또는 압축을 푼 .obj
    사람마다 heads/<이름>.zip (또는 heads/<이름>.obj, heads/<이름>/ 폴더)로 두면
    avatars/<이름>.blend 와 이름으로 짝지어진다.

실행 방법 1) 터미널에서 한 번에
  blender --background --python attachFace.py -- avatars --heads heads --out avatars
  blender --background --python attachFace.py -- avatars/sample_person.blend --head heads/sample_person.zip

실행 방법 2) Blender의 Scripting 탭
  몸이 들어 있는 .blend를 연 상태에서 아래 DEFAULT_HEAD를 바꾸고 실행하면
  현재 씬의 몸에 얼굴을 합친다 (저장은 하지 않음).
"""

import argparse
import importlib
import json
import os
import sys
import zipfile

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isdir(SCRIPT_DIR):  # Blender 텍스트 에디터에서 실행 시 경로가 가짜일 수 있음
        SCRIPT_DIR = os.getcwd()
except NameError:
    SCRIPT_DIR = os.getcwd()

# Scripting 탭에서 실행할 때 쓰는 기본값 (명령줄 인자가 있으면 무시됨)
DEFAULT_HEAD = os.path.join(SCRIPT_DIR, "heads", "keentools_head.zip")
FACE_FIT_DATA = os.path.join(SCRIPT_DIR, "data", "face_fit_hm08.json")

SHAPE_KEY = "FaceFit"           # 얼굴 변형 셰이프키 이름 (값 0~1로 닮은 정도 조절)
VERTEX_GROUP = "face_fit"       # 얼굴 가중치 정점 그룹
MASK_ATTRIBUTE = "face_fit_mask"  # 셰이더에서 쓰는 같은 가중치 (색 속성)
PROJECT_LIMIT_M = 0.02          # 얼굴 표면까지 이보다 멀면 투영하지 않음 (m)
SMOOTH_ITERATIONS = 8          # 이동량을 이웃과 평균내는 횟수 (클수록 매끈, 작을수록 FaceBuilder 디테일 유지)
MIN_NORMAL_DOT = 0.3            # 몸 정점 법선과 FaceBuilder 면 법선이 이만큼은 같은 쪽을 봐야 투영
TEXTURE_SIZE = 2048             # 베이크할 얼굴 텍스처 해상도
ICP_POINTS = 800                # 정렬에 쓰는 얼굴 정점 수 (많을수록 느리고 정확)


# ---------------------------------------------------------------------------
# 데이터 / 오브젝트 찾기
# ---------------------------------------------------------------------------

def load_face_fit_data(path=FACE_FIT_DATA):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["weights"] = {int(k): v for k, v in data["weights"].items()}
    return data


def find_body(data, objects=None):
    """MakeHuman 기본 메시(정점 수가 hm08과 같은 메시)를 찾는다"""
    candidates = [o for o in (objects or bpy.context.scene.objects)
                  if o.type == "MESH" and len(o.data.vertices) == data["vertex_count"]]
    if not candidates:
        return None
    named = [o for o in candidates if o.name.endswith(".body")]
    return (named or candidates)[0]


def person_stem(body):
    return body.name[:-len(".body")] if body.name.endswith(".body") else body.name


def _find_mpfb_human_service():
    """importToBlender.py와 같은 방식으로 MPFB2의 HumanService를 찾는다. 없으면 None"""
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
            except Exception as e:
                print(f"경고: MPFB2를 켜지 못했습니다 ({mod.__name__}): {e}")
            break
    return lookup()


# ---------------------------------------------------------------------------
# 3단계 결과물(머리) 불러오기
# ---------------------------------------------------------------------------

def find_head_file(heads_dir, stem):
    for candidate in (f"{stem}.zip", f"{stem}.obj", stem):
        path = os.path.join(heads_dir, candidate)
        if os.path.exists(path):
            return path
    return None


def _resolve_obj(head_path):
    """zip이면 같은 폴더의 <이름>_extracted/ 에 풀고, 그 안(또는 폴더 안)의 .obj 경로를 반환"""
    if os.path.isdir(head_path):
        folder = head_path
    elif head_path.lower().endswith(".zip"):
        folder = os.path.splitext(head_path)[0] + "_extracted"
        with zipfile.ZipFile(head_path) as z:
            z.extractall(folder)
    else:
        return head_path
    for root, _, files in os.walk(folder):
        for name in sorted(files):
            if name.lower().endswith(".obj"):
                return os.path.join(root, name)
    raise FileNotFoundError(f"{head_path} 안에서 .obj 파일을 찾지 못했습니다.")


def _find_texture_near(obj_path):
    folder = os.path.dirname(obj_path)
    for name in sorted(os.listdir(folder)):
        if name.lower().endswith((".jpg", ".jpeg", ".png")):
            return os.path.join(folder, name)
    return None


def import_head(head_path, name):
    obj_path = _resolve_obj(head_path)
    before = set(bpy.data.objects)
    if hasattr(bpy.ops.wm, "obj_import"):
        bpy.ops.wm.obj_import(filepath=obj_path)
    else:  # Blender 3.2 이하
        bpy.ops.import_scene.obj(filepath=obj_path)
    meshes = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if not meshes:
        raise RuntimeError(f"머리 메시를 불러오지 못했습니다: {obj_path}")
    if len(meshes) > 1:  # 여러 조각이면 하나로 합침
        with bpy.context.temp_override(active_object=meshes[0], selected_editable_objects=meshes):
            bpy.ops.object.join()
    head = meshes[0]
    head.name = name

    # OBJ에 재질이 없거나 텍스처가 안 붙었으면 옆의 jpg로 만든다
    texture = _find_texture_near(obj_path)
    has_image = any(m and m.use_nodes and any(n.type == "TEX_IMAGE" and n.image for n in m.node_tree.nodes)
                    for m in head.data.materials)
    if texture and not has_image:
        mat = bpy.data.materials.new(f"{name}.material")
        mat.use_nodes = True
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(texture, check_existing=True)
        links.new(tex.outputs["Color"], nodes["Principled BSDF"].inputs["Base Color"])
        head.data.materials.clear()
        head.data.materials.append(mat)
    print(f"  머리 불러옴: {obj_path} (정점 {len(head.data.vertices)}개, 텍스처 {'있음' if texture else '없음'})")
    return head


# ---------------------------------------------------------------------------
# 메시 좌표 읽기
# ---------------------------------------------------------------------------

def body_current_shape(body):
    """모디파이어(뼈대·헬퍼 숨김·서브디비전)를 끈 상태의 현재 모양 (셰이프키 반영, 로컬 좌표)"""
    saved = [(m, m.show_viewport) for m in body.modifiers]
    for m, _ in saved:
        m.show_viewport = False
    try:
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = body.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        n = len(mesh.vertices)
        co = np.empty(n * 3)
        mesh.vertices.foreach_get("co", co)
        normals = np.empty(n * 3)
        if hasattr(mesh, "vertex_normals"):
            mesh.vertex_normals.foreach_get("vector", normals)
        else:
            mesh.vertices.foreach_get("normal", normals)
        edges = np.empty(len(mesh.edges) * 2, dtype=np.int64)
        mesh.edges.foreach_get("vertices", edges)
        evaluated.to_mesh_clear()
    finally:
        for m, shown in saved:
            m.show_viewport = shown
    return co.reshape(-1, 3), normals.reshape(-1, 3), edges.reshape(-1, 2)


def _to_world(matrix, points):
    m = np.array(matrix)
    return points @ m[:3, :3].T + m[:3, 3]


def head_bvh(head):
    """머리 메시의 로컬 좌표 BVH와 정점 배열"""
    mesh = head.data
    verts = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", verts)
    verts = verts.reshape(-1, 3)
    polygons = [tuple(p.vertices) for p in mesh.polygons]
    return BVHTree.FromPolygons([Vector(v) for v in verts], polygons), verts


# ---------------------------------------------------------------------------
# 4. 정렬
# ---------------------------------------------------------------------------

def similarity(src, dst):
    """Umeyama: dst ≈ s * R @ src + t 를 만족하는 4x4 행렬"""
    mu_s, mu_d = src.mean(0), dst.mean(0)
    a, b = src - mu_s, dst - mu_d
    U, S, Vt = np.linalg.svd(b.T @ a / len(src))
    D = np.eye(3)
    D[2, 2] = np.sign(np.linalg.det(U @ Vt))
    R = U @ D @ Vt
    s = np.trace(np.diag(S) @ D) / (a ** 2).sum(1).mean()
    M = np.eye(4)
    M[:3, :3] = s * R
    M[:3, 3] = mu_d - s * R @ mu_s
    return M


def _icp(points, bvh, head_matrix, iterations, trim=0.9):
    """points(몸 얼굴 정점, 월드)에 머리 표면이 겹치도록 head_matrix(4x4 numpy)를 다듬는다.
    반환: (새 행렬, 잘라낸 평균 거리 m)"""
    H = head_matrix.copy()
    error = float("inf")
    for _ in range(iterations):
        inv = np.linalg.inv(H)
        local = _to_world(inv, points)
        pairs_src, pairs_dst, dists = [], [], []
        for p_world, p_local in zip(points, local):
            hit = bvh.find_nearest(Vector(p_local))
            if hit[0] is None:
                continue
            q = _to_world(H, np.array([hit[0]]))[0]
            pairs_src.append(q)
            pairs_dst.append(p_world)
            dists.append(np.linalg.norm(q - p_world))
        if len(dists) < 10:
            return H, float("inf")
        dists = np.array(dists)
        keep = dists <= np.quantile(dists, trim)
        error = float(dists[keep].mean())
        H = similarity(np.array(pairs_src)[keep], np.array(pairs_dst)[keep]) @ H
    return H, error


def _orientation_candidates():
    """KeenTools OBJ의 좌표계를 모르므로, 축을 90도 단위로 돌린 24가지 방향을 모두 시도"""
    import itertools
    candidates = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            R = np.zeros((3, 3))
            for row, (col, sign) in enumerate(zip(perm, signs)):
                R[row, col] = sign
            if np.linalg.det(R) > 0:
                M = np.eye(4)
                M[:3, :3] = R
                candidates.append(M)
    return candidates


def align_head(head, body, body_co, data, face_idx, orient="auto"):
    """머리를 몸 얼굴에 맞춘다. 반환: 잘라낸 평균 거리(m)

    얼굴 앞면만으로는 머리가 앞뒤 축으로 돌아간 상태(roll)를 구별하기 어려워서,
    방향 고르기와 1차 정렬은 머리 전체(정수리·귀·뒷머리 포함)로 하고
    마지막 미세 조정만 얼굴 앞면으로 한다."""
    bvh, head_verts = head_bvh(head)
    body_world = _to_world(body.matrix_world, body_co)
    lm = data["landmarks"]
    mh_nose, mh_top = body_world[lm["nose_tip"]], body_world[lm["head_top"]]
    points = body_world[face_idx]
    whole = body_world[data["head"]]
    whole = whole[:: max(1, len(whole) // 300)]

    base = np.array(head.matrix_world)
    center = _to_world(base, head_verts).mean(0)
    to_center, from_center = np.eye(4), np.eye(4)
    to_center[:3, 3], from_center[:3, 3] = center, -center
    candidates = _orientation_candidates() if orient == "auto" else [np.eye(4)]

    best = None
    for rotation in candidates:
        H = to_center @ rotation @ from_center @ base
        world = _to_world(H, head_verts)
        z_lo, z_hi = world[:, 2].min(), world[:, 2].max()
        upper = world[world[:, 2] > z_lo + 0.25 * (z_hi - z_lo)]
        nose = upper[np.argmin(upper[:, 1])]  # 정면(-Y)으로 가장 튀어나온 점 = 코끝
        span = z_hi - nose[2]
        if span <= 0:
            continue
        s = (mh_top[2] - mh_nose[2]) / span
        init = np.eye(4)
        init[:3, :3] *= s
        init[:3, 3] = mh_nose - s * nose
        H, error = _icp(whole, bvh, init @ H, iterations=12, trim=0.8)
        if best is None or error < best[1]:
            best = (H, error)

    H, _ = _icp(whole, bvh, best[0], iterations=10, trim=0.8)
    H, error = _icp(points, bvh, H, iterations=30)
    head.matrix_world = Matrix(H.tolist())
    bpy.context.view_layer.update()
    print(f"  정렬: 얼굴 표면 평균 거리 {error * 1000:.1f}mm")
    return error


# ---------------------------------------------------------------------------
# 5~7. 가중치 + 투영 -> 셰이프키
# ---------------------------------------------------------------------------

def write_weights(body, weights):
    group = body.vertex_groups.get(VERTEX_GROUP) or body.vertex_groups.new(name=VERTEX_GROUP)
    group.remove(list(range(len(body.data.vertices))))
    for index, weight in weights.items():
        group.add([index], weight, "REPLACE")

    # 셰이더에서 쓰도록 같은 값을 색 속성으로도 저장 (회색 = 가중치)
    attrs = body.data.color_attributes
    if MASK_ATTRIBUTE in attrs:
        attrs.remove(attrs[MASK_ATTRIBUTE])
    attr = attrs.new(MASK_ATTRIBUTE, "FLOAT_COLOR", "POINT")
    colors = np.zeros((len(body.data.vertices), 4))
    colors[:, 3] = 1.0
    for index, weight in weights.items():
        colors[index, :3] = weight
    attr.data.foreach_set("color", colors.ravel())


def project_face(body, head, co, normals, edges, weights, carry):
    """얼굴 정점마다 FaceBuilder 표면까지의 이동량(로컬 좌표)을 구한다"""
    bvh, _ = head_bvh(head)
    body_m = np.array(body.matrix_world)
    head_inv = np.linalg.inv(np.array(head.matrix_world))
    to_head = head_inv @ body_m                 # 몸 로컬 -> 머리 로컬
    to_body = np.linalg.inv(to_head)
    head_scale = np.cbrt(abs(np.linalg.det(to_head[:3, :3])))
    body_scale = np.cbrt(abs(np.linalg.det(body_m[:3, :3])))
    limit = PROJECT_LIMIT_M / body_scale * head_scale  # 머리 로컬 단위의 최대 거리

    indices = np.array(sorted(weights))
    neighbors = [[] for _ in range(len(co))]
    for a, b in edges:
        neighbors[a].append(b)
        neighbors[b].append(a)

    def cast(index, position):
        """position(몸 로컬)에서 법선 앞뒤로 쏴서 가장 가까운 머리 표면 점(몸 로컬)을 찾는다.
        면 방향이 반대인 곳(콧구멍·눈꺼풀 안쪽이 바깥 피부에 붙는 경우)은 받지 않는다."""
        origin = Vector(_to_world(to_head, position[None])[0])
        direction = Vector(normals[index] @ to_head[:3, :3].T).normalized()
        best = None
        for sign in (1.0, -1.0):
            hit, normal, _, dist = bvh.ray_cast(origin, direction * sign, limit)
            if hit is not None and normal.dot(direction) > MIN_NORMAL_DOT and (best is None or dist < best[1]):
                best = (hit, dist)
        if best is None:
            hit, normal, _, dist = bvh.find_nearest(origin, limit)
            if hit is not None and normal.dot(direction) > MIN_NORMAL_DOT:
                best = (hit, dist)
        return None if best is None else _to_world(to_body, np.array([best[0]]))[0]

    displacement = np.zeros_like(co)
    hit_mask = np.zeros(len(co), dtype=bool)
    pending = list(indices)
    for _ in range(4):
        # 표면을 찾은 점은 확정. 못 찾은 점은 이웃이 움직인 만큼 옮긴 위치에서 다시 쏜다
        # (몸과 FaceBuilder 얼굴 차이가 PROJECT_LIMIT_M보다 큰 곳도 단계적으로 따라감)
        for i in pending:
            target = cast(i, co[i] + displacement[i])
            if target is not None:
                displacement[i] = target - co[i]
                hit_mask[i] = True
        pending = [i for i in pending if not hit_mask[i]]
        if not pending:
            break
        for _ in range(10):
            fill = [i for i in pending if any(hit_mask[j] or np.any(displacement[j]) for j in neighbors[i])]
            if not fill:
                break
            for i in fill:
                known = [displacement[j] for j in neighbors[i] if hit_mask[j] or np.any(displacement[j])]
                displacement[i] = np.mean(known, axis=0)
    missed = len(pending)

    # 이동량을 이웃끼리 부드럽게 만든다. 이웃한 점이 서로 다른 면(콧방울 주름, 눈꺼풀 안팎)에
    # 붙으면서 생기는 접힘·찢어짐을 없애고, MakeHuman의 잔주름(콧구멍·눈꺼풀)은 그대로 남긴다
    region = np.zeros(len(co), dtype=bool)
    region[indices] = True
    pairs = edges[region[edges[:, 0]] & region[edges[:, 1]]]
    degree = np.bincount(pairs.ravel(), minlength=len(co))[:, None]
    smooth = indices[degree[indices, 0] > 0]
    for _ in range(SMOOTH_ITERATIONS):
        total = np.zeros_like(displacement)
        np.add.at(total, pairs[:, 0], displacement[pairs[:, 1]])
        np.add.at(total, pairs[:, 1], displacement[pairs[:, 0]])
        displacement[smooth] = 0.5 * displacement[smooth] + 0.5 * total[smooth] / degree[smooth]

    w = np.zeros(len(co))
    w[indices] = [weights[i] for i in indices]
    displacement *= w[:, None]

    # 입속·눈구멍·헬퍼·관절은 가까운 얼굴 정점들의 이동량 평균을 따라감
    solid = [i for i in indices if weights[i] >= 0.5]
    tree = KDTree(len(solid))
    for i in solid:
        tree.insert(Vector(co[i]), i)
    tree.balance()
    for i in carry:
        found = tree.find_n(Vector(co[i]), 12)
        inv = np.array([1.0 / max(d, 1e-6) for _, _, d in found])
        displacement[i] = (np.array([displacement[j] for _, j, _ in found]) * inv[:, None]).sum(0) / inv.sum()

    print(f"  투영: 얼굴 정점 {len(indices)}개 (표면을 못 찾아 이웃으로 채운 점 {missed}개), "
          f"최대 이동 {np.linalg.norm(displacement, axis=1).max() * body_scale * 1000:.1f}mm")
    return displacement


def write_shape_key(body, displacement):
    if body.data.shape_keys is None:
        body.shape_key_add(name="Basis", from_mix=False)
    keys = body.data.shape_keys.key_blocks
    basis = body.data.shape_keys.reference_key
    key = keys.get(SHAPE_KEY) or body.shape_key_add(name=SHAPE_KEY, from_mix=False)
    co = np.empty(len(basis.data) * 3)
    basis.data.foreach_get("co", co)
    key.data.foreach_set("co", (co.reshape(-1, 3) + displacement).ravel())
    key.value = 1.0
    body.data.update()


# ---------------------------------------------------------------------------
# 8. 눈·눈썹·리그 다시 맞추기
# ---------------------------------------------------------------------------

def refit_with_mpfb(body):
    service = _find_mpfb_human_service()
    if service is None:
        print("  경고: MPFB2가 없어 눈·리그 재피팅을 건너뜁니다. 눈알 위치를 직접 확인하세요.")
        return False
    try:
        service.refit(body)
    except Exception as e:
        print(f"  경고: MPFB2 refit 실패 ({e}). 눈·리그 위치를 직접 확인하세요.")
        return False
    print("  MPFB2 refit: 눈·눈썹·속눈썹·뼈대를 새 얼굴에 맞춤")
    return True


# ---------------------------------------------------------------------------
# 9. 텍스처
# ---------------------------------------------------------------------------

def _body_materials(body):
    if not body.data.materials or all(m is None for m in body.data.materials):
        mat = bpy.data.materials.new(f"{body.name}.skin")
        mat.use_nodes = True
        mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.80, 0.60, 0.50, 1.0)
        body.data.materials.clear()
        body.data.materials.append(mat)
    return [m for m in body.data.materials if m is not None]


def _insert_face_mix(mat, image_node):
    """Principled BSDF의 Base Color 앞에 (원래 피부색, 얼굴 텍스처)를 face_fit_mask로 섞는 노드를 넣는다"""
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        return False
    base = bsdf.inputs["Base Color"]
    old = nodes.get("FaceFit Mix")
    if old is not None:  # 다시 실행할 때는 이전 노드를 걷어내고 원래 연결을 되살림
        skin_link = old.inputs[6].links[0].from_socket if old.inputs[6].is_linked else None
        nodes.remove(old)
        for name in ("FaceFit Mask", "FaceFit Alpha"):
            if nodes.get(name):
                nodes.remove(nodes[name])
        if skin_link is not None:
            links.new(skin_link, base)

    mix = nodes.new("ShaderNodeMix")
    mix.name = "FaceFit Mix"
    mix.data_type = "RGBA"
    mask = nodes.new("ShaderNodeAttribute")
    mask.name = "FaceFit Mask"
    mask.attribute_name = MASK_ATTRIBUTE
    alpha = nodes.new("ShaderNodeMath")
    alpha.name = "FaceFit Alpha"
    alpha.operation = "MULTIPLY"
    if base.is_linked:
        links.new(base.links[0].from_socket, mix.inputs[6])
    else:
        mix.inputs[6].default_value = base.default_value
    links.new(image_node.outputs["Color"], mix.inputs[7])
    links.new(mask.outputs["Fac"], alpha.inputs[0])
    links.new(image_node.outputs["Alpha"], alpha.inputs[1])  # 베이크가 안 된 곳은 원래 피부
    links.new(alpha.outputs[0], mix.inputs[0])
    links.new(mix.outputs[2], base)
    mix.location = bsdf.location + Vector((-250, 0))
    mask.location = alpha.location = image_node.location = bsdf.location + Vector((-550, 0))
    alpha.location.y += 250
    image_node.location.y -= 300
    return True


def bake_face_texture(body, head, out_dir, stem, size=TEXTURE_SIZE):
    scene = bpy.context.scene
    image = bpy.data.images.get(f"{stem}_face") or bpy.data.images.new(f"{stem}_face", size, size, alpha=True)
    image.generated_color = (0, 0, 0, 0)

    image_nodes = []
    for mat in _body_materials(body):
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        node = nodes.get("FaceFit Texture") or nodes.new("ShaderNodeTexImage")
        node.name = "FaceFit Texture"
        node.image = image
        node.interpolation = "Linear"
        nodes.active = node  # 베이크 대상
        image_nodes.append((mat, node))

    previous = (scene.render.engine, head.hide_get(), head.hide_render)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 1
    head.hide_set(False)
    head.hide_render = False
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    head.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    try:
        bpy.ops.object.bake(
            type="DIFFUSE", pass_filter={"COLOR"}, use_selected_to_active=True,
            cage_extrusion=0.005, max_ray_distance=0.03, margin=8, use_clear=True,
            target="IMAGE_TEXTURES",
        )
    finally:
        scene.render.engine = previous[0]
        head.hide_set(previous[1])
        head.hide_render = previous[2]

    if out_dir:
        path = os.path.abspath(os.path.join(out_dir, f"{stem}_face.png"))
        image.filepath_raw = path
        image.file_format = "PNG"
        image.save()
        image.filepath = path
        print(f"  얼굴 텍스처 저장: {path}")

    for mat, node in image_nodes:
        if not _insert_face_mix(mat, node):
            print(f"  경고: {mat.name} 재질에 Principled BSDF가 없어 얼굴 텍스처를 직접 연결해야 합니다.")
    return image


# ---------------------------------------------------------------------------
# 전체 실행
# ---------------------------------------------------------------------------

def attach_face(body, head_path, *, data, out_dir=None, texture=True, orient="auto"):
    stem = person_stem(body)
    head_name = f"{stem}.facebuilder"
    if head_name in bpy.data.objects:  # 다시 실행할 때 이전 머리 제거
        bpy.data.objects.remove(bpy.data.objects[head_name], do_unlink=True)
    if body.data.shape_keys and SHAPE_KEY in body.data.shape_keys.key_blocks:
        body.data.shape_keys.key_blocks[SHAPE_KEY].value = 0.0  # 변형 전 모양 기준으로 다시 계산

    head = import_head(head_path, head_name)
    for collection in list(head.users_collection):  # 몸과 같은 컬렉션에 둔다
        collection.objects.unlink(head)
    body.users_collection[0].objects.link(head)

    co, normals, edges = body_current_shape(body)
    weights, carry = data["weights"], data["carry"]
    face = sorted(i for i, w in weights.items() if w >= 0.95)
    face = face[:: max(1, len(face) // ICP_POINTS)]

    error = align_head(head, body, co, data, face, orient=orient)
    if error > 0.01:
        print("  경고: 정렬 오차가 1cm보다 큽니다. 결과를 눈으로 확인하세요 (--orient none 으로 다시 시도 가능).")

    write_weights(body, weights)
    displacement = project_face(body, head, co, normals, edges, weights, carry)
    write_shape_key(body, displacement)
    refit_with_mpfb(body)

    if texture:
        bake_face_texture(body, head, out_dir, stem)

    head.hide_set(True)
    head.hide_render = True
    return head


def collect_blend_files(input_path):
    if os.path.isdir(input_path):
        return sorted(os.path.join(input_path, n) for n in os.listdir(input_path) if n.lower().endswith(".blend"))
    return [input_path]


def run(input_path, *, head=None, heads_dir=None, out_dir=None, texture=True, orient="auto"):
    data = load_face_fit_data()
    blend_files = collect_blend_files(input_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    succeeded = 0
    for blend_path in blend_files:
        stem = os.path.splitext(os.path.basename(blend_path))[0]
        head_path = head or (heads_dir and find_head_file(heads_dir, stem))
        if not head_path:
            print(f"[{stem}] 건너뜀: {heads_dir}에서 {stem}.zip / {stem}.obj 를 찾지 못했습니다.")
            continue

        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend_path))
        body = find_body(data)
        if body is None:
            print(f"[{stem}] 건너뜀: MakeHuman 몸 메시(정점 {data['vertex_count']}개)를 찾지 못했습니다.")
            continue
        print(f"[{stem}] 얼굴 합치는 중: {head_path}")
        attach_face(body, os.path.abspath(head_path), data=data,
                    out_dir=out_dir or os.path.dirname(blend_path), texture=texture, orient=orient)

        save_path = os.path.abspath(os.path.join(out_dir or os.path.dirname(blend_path), f"{stem}.blend"))
        bpy.ops.wm.save_as_mainfile(filepath=save_path)
        print(f"  저장: {save_path}")
        succeeded += 1

    print(f"완료: {succeeded}/{len(blend_files)}명 얼굴 합침")


def run_in_current_scene(head_path=DEFAULT_HEAD):
    """Scripting 탭용: 현재 씬의 몸에 얼굴을 합친다 (저장하지 않음)"""
    data = load_face_fit_data()
    body = find_body(data)
    if body is None:
        print(f"MakeHuman 몸 메시(정점 {data['vertex_count']}개)를 찾지 못했습니다.")
        return
    attach_face(body, head_path, data=data, out_dir=bpy.path.abspath("//") or None)


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="FaceBuilder 머리를 MakeHuman 몸(.blend)에 합칩니다.")
    parser.add_argument("input_path", help="importToBlender.py가 만든 <이름>.blend 또는 그 폴더")
    parser.add_argument("--head", default=None, help="머리 파일(zip/obj) 하나. .blend가 하나일 때 사용")
    parser.add_argument("--heads", default=None, help="<이름>.zip / <이름>.obj 가 모여 있는 폴더")
    parser.add_argument("--out", default=None, help="결과 .blend와 얼굴 텍스처를 저장할 폴더 (기본: 입력과 같은 폴더)")
    parser.add_argument("--no-texture", action="store_true", help="텍스처 베이크 생략")
    parser.add_argument("--orient", choices=["auto", "none"], default="auto",
                        help="auto: 머리 OBJ의 방향을 자동으로 찾음 / none: 불러온 방향 그대로 사용")
    args = parser.parse_args(argv)
    if not args.head and not args.heads:
        parser.error("--head 또는 --heads 중 하나가 필요합니다.")
    return args


if __name__ == "__main__":
    if "--" in sys.argv:
        args = _parse_args(sys.argv[sys.argv.index("--") + 1:])
        run(args.input_path, head=args.head, heads_dir=args.heads, out_dir=args.out,
            texture=not args.no_texture, orient=args.orient)
    else:
        run_in_current_scene()
