"""
MakeHuman 기본 메시(base.obj, hm08)에서 attachFace.py가 쓰는 데이터를 만든다.

  python tools/makeFaceFitData.py <base.obj 경로> --out data/face_fit_hm08.json

base.obj는 MPFB2(mpfb/data/3dobjs/base.obj)나 MakeHuman(data/3dobjs/base.obj)에
들어 있다. 사람마다 모양은 달라도 정점 순서(토폴로지)는 같으므로, 한 번 만든
JSON을 모든 아바타에 그대로 쓴다. 결과 JSON은 저장소에 커밋되어 있어 보통은
다시 만들 필요가 없다.

만드는 것
  landmarks : 정렬 초기값에 쓰는 정점 번호 (코끝, 턱끝, 정수리, 양쪽 눈 중심)
  weights   : face_fit 가중치 (정점 번호 -> 0~1)
              얼굴 앞면 1, 턱 아래·귀·뒷머리·정수리 쪽으로 갈수록 0,
              입속과 눈구멍 안쪽은 0
  head      : 머리 전체(턱 위, 입속·눈구멍 제외) 정점. FaceBuilder 머리의 방향을 고를 때 사용
  carry     : 투영하지 않고 주변 얼굴이 움직인 만큼 따라 움직일 정점
              (입속, 눈구멍 안쪽, 눈알·속눈썹·이·혀 헬퍼, 눈·턱·혀 관절 큐브)
"""

import argparse
import json

import numpy as np

# base.obj 좌표계: Y 위, +Z 앞, 단위 dm (1 = 10cm)
UNDER_CHIN = (6.00, 6.35)   # 이 높이(y) 구간에서 턱 아래 -> 얼굴로 0 -> 1
FRONT = (0.35, 0.85)        # 이 깊이(z) 구간에서 귀 -> 볼로 0 -> 1
HAIRLINE = (7.90, 8.25)     # 이 높이(y) 구간에서 이마 -> 정수리로 1 -> 0
HEAD_BOTTOM = 6.25          # 이 높이(y) 위를 머리 전체로 봄 (턱끝 높이)
EYE_SOCKET_RADIUS = 0.32    # 눈 중심에서 이 거리 안의 안쪽을 향한 면 = 눈구멍
MOUTH_CENTER = (0.0, 6.72, 1.05)
MOUTH_RADIUS = 0.50         # 입 중심에서 이 거리 안의 안쪽을 향한 면 = 입속

# 얼굴을 따라 움직여야 하는 헬퍼/관절 그룹 (MPFB2가 눈·리그를 다시 맞출 때 기준이 됨)
CARRY_GROUPS = (
    "helper-l-eye", "helper-r-eye",
    "helper-l-eyelashes-1", "helper-l-eyelashes-2", "helper-r-eyelashes-1", "helper-r-eyelashes-2",
    "helper-upper-teeth", "helper-lower-teeth", "helper-tongue",
    "joint-l-eye", "joint-r-eye", "joint-l-eye-target", "joint-r-eye-target",
    "joint-l-upperlid", "joint-l-lowerlid", "joint-r-upperlid", "joint-r-lowerlid",
    "joint-jaw", "joint-mouth", "joint-tongue-1", "joint-tongue-2", "joint-tongue-3", "joint-tongue-4",
)


def load_obj(path):
    verts, faces, groups, group = [], [], [], None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("v "):
                verts.append([float(x) for x in line.split()[1:4]])
            elif line.startswith("g "):
                group = line.split()[1]
            elif line.startswith("f "):
                faces.append([int(p.split("/")[0]) - 1 for p in line.split()[1:]])
                groups.append(group)
    return np.array(verts), faces, groups


def vertex_normals(verts, faces):
    normals = np.zeros_like(verts)
    for face in faces:
        p = verts[face]
        n = np.zeros(3)
        for i in range(len(face)):  # Newell 방식 (사각형/삼각형 모두)
            a, b = p[i], p[(i + 1) % len(face)]
            n += [(a[1] - b[1]) * (a[2] + b[2]), (a[2] - b[2]) * (a[0] + b[0]), (a[0] - b[0]) * (a[1] + b[1])]
        normals[face] += n
    length = np.linalg.norm(normals, axis=1, keepdims=True)
    return normals / np.maximum(length, 1e-12)


def smoothstep(lo, hi, x):
    t = np.clip((x - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def facing_inward(points, normals, center, radius):
    """center 근처에서 면이 center 쪽(안쪽)을 향하는 정점 = 구멍 안쪽 면"""
    to_center = np.asarray(center) - points
    dist = np.linalg.norm(to_center, axis=1)
    cos = (normals * to_center).sum(1) / np.maximum(dist, 1e-12)
    return (dist < radius) & (cos > 0.2)


def build(base_obj):
    verts, faces, groups = load_obj(base_obj)
    body_faces = [f for f, g in zip(faces, groups) if g == "body"]
    body = np.array(sorted({i for f in body_faces for i in f}))
    normals = vertex_normals(verts, body_faces)

    def group_verts(name):
        return sorted({i for f, g in zip(faces, groups) if g == name for i in f})

    p = verts[body]
    x, y, z = p.T
    mid = np.abs(x) < 0.02
    nose = body[mid & (y > 6.6) & (y < 7.2)][np.argmax(z[mid & (y > 6.6) & (y < 7.2)])]
    chin = body[mid & (y > 6.15) & (y < 6.45)][np.argmax(z[mid & (y > 6.15) & (y < 6.45)])]
    top = body[np.argmax(y)]
    eye_l, eye_r = group_verts("helper-l-eye"), group_verts("helper-r-eye")

    w = smoothstep(*UNDER_CHIN, y) * smoothstep(*FRONT, z) * (1 - smoothstep(*HAIRLINE, y))
    n = normals[body]
    cavity = facing_inward(p, n, MOUTH_CENTER, MOUTH_RADIUS)
    for eye in (eye_l, eye_r):
        cavity |= facing_inward(p, n, verts[eye].mean(0), EYE_SOCKET_RADIUS)
    w[cavity] = 0.0

    carry = set(int(i) for i in body[cavity])
    for name in CARRY_GROUPS:
        carry.update(group_verts(name))

    head = body[(y > HEAD_BOTTOM) & ~cavity]

    keep = w > 1e-3
    return {
        "source": "MakeHuman hm08 base.obj",
        "vertex_count": len(verts),
        "landmarks": {
            "nose_tip": int(nose),
            "chin": int(chin),
            "head_top": int(top),
            "eye_l": [int(i) for i in eye_l],
            "eye_r": [int(i) for i in eye_r],
        },
        "head": [int(i) for i in head],
        "carry": sorted(carry),
        "weights": {str(int(i)): round(float(v), 3) for i, v in zip(body[keep], w[keep])},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="attachFace.py용 MakeHuman 얼굴 가중치/기준점 데이터를 만듭니다.")
    parser.add_argument("base_obj", help="MakeHuman/MPFB2의 base.obj 경로")
    parser.add_argument("--out", default="data/face_fit_hm08.json")
    args = parser.parse_args()

    data = build(args.base_obj)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    full = sum(1 for v in data["weights"].values() if v >= 0.99)
    print(f"저장: {args.out} (가중치 정점 {len(data['weights'])}개, 그중 1.0 {full}개, 따라 움직일 정점 {len(data['carry'])}개)")
