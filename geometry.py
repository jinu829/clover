"""3D 모양 계산.

좌표 약속
- '사진 좌표': 각 사진의 픽셀 단위. x 오른쪽, y 위쪽, z 카메라 쪽이 + 입니다.
  (사진 픽셀 위치는 (x, -y))
- '머리 좌표': 두 볼 사이 가운데가 원점. x 는 사진 기준 오른쪽, y 는 이마 쪽, z 는 코 쪽.
  고개가 살짝 기울어진 사진이어도 머리 기준으로 반듯하게 맞춘 좌표입니다.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np

from .engines.base import face_normals, vertex_normals

# MediaPipe 얼굴 점 번호
RIGHT_CHEEK = 234   # 사진에서 왼쪽 끝 볼(본인 기준 오른쪽)
LEFT_CHEEK = 454    # 사진에서 오른쪽 끝 볼
FOREHEAD = 10       # 이마 위쪽 가운데
CHIN = 152          # 턱 끝

# 머리(두개골)를 타원체로 근사할 때의 비율. 단위는 두 볼 사이 거리(W).
HEAD_CENTER = (0.0, 0.10, -0.20)   # 볼 가운데 기준 타원체 중심 위치
HEAD_HALF_WIDTH = 0.55
HEAD_HALF_HEIGHT = 0.85
HEAD_HALF_DEPTH = 0.70
CROWN_ABOVE_FOREHEAD = 0.30        # 이마 점 위로 정수리까지 최소 높이
MOUTH_RECESS = 0.04                # 입을 메운 면을 안쪽으로 넣는 깊이

SHELL_RINGS = 14       # 얼굴 테두리에서 뒤통수까지 고리 개수(많을수록 매끈)
SHELL_BLEND_RINGS = 4  # 얼굴 테두리 모양에서 타원체 모양으로 바뀌는 데 쓰는 고리 수
UV_RADIUS = 0.49       # 텍스처 이미지 안에서 머리 전체가 차지하는 원의 반지름
UV_FACE_EMPHASIS = 3   # 클수록 텍스처에서 얼굴이 크게(선명하게), 뒤통수가 작게 배치됨. 1 이면 균등


@dataclass
class View:
    """사진 한 장과, 정면 사진 대비 이 사진이 얼마나 돌아가 있는지(s, R, t).

    정면 사진 좌표의 점 X 는 이 사진에서 s * R @ X + t 위치에 보입니다.
    """
    name: str
    rgb: np.ndarray
    points: np.ndarray                  # (468, 3) 이 사진에서 찾은 얼굴 점 (사진 좌표)
    s: float = 1.0
    R: np.ndarray = field(default_factory=lambda: np.eye(3))
    t: np.ndarray = field(default_factory=lambda: np.zeros(3))

    @property
    def camera_dir(self) -> np.ndarray:
        """정면 사진 좌표에서 본, 이 사진의 카메라 쪽 방향."""
        return self.R[2]

    @property
    def yaw_degrees(self) -> float:
        return float(np.degrees(np.arctan2(self.R[0, 2], self.R[2, 2])))

    def project(self, points_front: np.ndarray) -> np.ndarray:
        """정면 사진 좌표의 점들을 이 사진 좌표로 옮깁니다."""
        return self.s * points_front @ self.R.T + self.t


# ---------------------------------------------------------------- 얼굴 삼각형 구조

def face_topology() -> Tuple[np.ndarray, np.ndarray, List[np.ndarray]]:
    """MediaPipe 가 정의한 얼굴 삼각형 852개, 얼굴 테두리 순서, 눈/입 구멍 테두리들."""
    from mediapipe.tasks.python.vision import FaceLandmarksConnections as C

    t = C.FACE_LANDMARKS_TESSELATION   # 삼각형마다 변 3개씩 순서대로 들어 있음
    tris = np.array([[t[i].start, t[i + 1].start, t[i + 2].start] for i in range(0, len(t), 3)])
    oval = np.array([c.start for c in C.FACE_LANDMARKS_FACE_OVAL])
    holes = _boundary_loops(tris, exclude=set(oval.tolist()))
    return tris, oval, holes


def _boundary_loops(tris: np.ndarray, exclude: set) -> List[np.ndarray]:
    """삼각형 하나에만 속한 변(=구멍 테두리)을 이어 고리 목록으로 만듭니다."""
    count = defaultdict(int)
    for a, b, c in tris:
        for e in ((a, b), (b, c), (c, a)):
            count[tuple(sorted(e))] += 1

    nbr = defaultdict(list)
    for (a, b), n in count.items():
        if n == 1 and not (a in exclude and b in exclude):
            nbr[a].append(b)
            nbr[b].append(a)

    loops, seen = [], set()
    for start in nbr:
        if start in seen:
            continue
        loop = [start]
        seen.add(start)
        prev, cur = start, nbr[start][0]
        while cur != start:
            loop.append(cur)
            seen.add(cur)
            a, b = nbr[cur]
            prev, cur = cur, (b if a == prev else a)
        loops.append(np.array(loop))
    return loops


def orient_faces(points: np.ndarray, faces: np.ndarray, outward: np.ndarray) -> np.ndarray:
    """삼각형 묶음의 감는 순서를 바깥(outward)을 보도록 통일합니다(다수결)."""
    n = face_normals(points, faces)
    wrong = np.einsum("ij,ij->i", n, np.broadcast_to(outward, n.shape)) < 0
    return faces[:, ::-1].copy() if wrong.sum() > len(faces) / 2 else faces


def fill_holes(points: np.ndarray, tris: np.ndarray, holes: List[np.ndarray], width: float):
    """눈, 입 구멍을 가운데 점 하나와 부채꼴 삼각형으로 막습니다.

    입은 다물고 있으면 위아래 입술 테두리가 겹쳐서, 가운데 점을 안쪽으로 살짝 넣어야
    메운 면이 입술과 겹쳐 얼룩지지 않습니다.
    반환: (점들, 삼각형들, 텍스처 좌표 계산용 점들) - 마지막은 입 가운데 점을 넣기 전 위치.
    (넣은 위치로 텍스처 좌표를 계산하면 아랫입술과 텍스처 자리가 겹쳐 얼룩이 생깁니다)
    """
    centers = np.array([points[loop].mean(axis=0) for loop in holes])
    uv_points = np.vstack([points, centers])
    mouth = int(np.argmin(centers[:, 1]))          # 가장 아래쪽 구멍이 입
    centers[mouth, 2] -= MOUTH_RECESS * width
    all_points = np.vstack([points, centers])
    all_tris = [tris]
    for k, loop in enumerate(holes):
        c = len(points) + k
        fan = np.array([[loop[j], loop[(j + 1) % len(loop)], c] for j in range(len(loop))])
        all_tris.append(orient_faces(uv_points, fan, np.array([0.0, 0.0, 1.0])))
    return all_points, np.vstack(all_tris), uv_points


# ---------------------------------------------------------------- 여러 사진 합치기

def similarity(src: np.ndarray, dst: np.ndarray) -> Tuple[float, np.ndarray, np.ndarray]:
    """dst ≈ s * R @ src + t 가 되는 크기 s, 회전 R, 이동 t 를 구합니다(Umeyama 방법)."""
    mu_s, mu_d = src.mean(axis=0), dst.mean(axis=0)
    xs, xd = src - mu_s, dst - mu_d
    U, S, Vt = np.linalg.svd(xd.T @ xs / len(src))
    D = np.eye(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        D[2, 2] = -1
    R = U @ D @ Vt
    s = float(np.trace(np.diag(S) @ D) / ((xs ** 2).sum() / len(src)))
    t = mu_d - s * R @ mu_s
    return s, R, t


def fuse_views(views: List[View], tris: np.ndarray) -> np.ndarray:
    """사진마다 추정한 얼굴 모양을, 각 부분을 정면으로 잘 본 사진일수록 크게 반영해 합칩니다.

    예) 볼 옆면은 측면 사진이, 코와 입은 정면 사진이 더 많이 반영됩니다.
    """
    front = views[0].points
    normals = vertex_normals(front, tris)
    acc = np.zeros_like(front)
    wsum = np.zeros(len(front))
    for i, v in enumerate(views):
        estimate = (v.points - v.t) @ v.R / v.s        # 이 사진의 점들을 정면 사진 좌표로
        w = np.clip(normals @ v.camera_dir, 0, None) ** 2
        if i == 0:
            w += 1e-3                                   # 어떤 사진에도 안 보이는 점 대비
        acc += w[:, None] * estimate
        wsum += w
    return acc / wsum[:, None]


# ---------------------------------------------------------------- 머리 전체 만들기

def head_frame(points: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
    """얼굴 점으로 '머리 좌표'의 원점, 축(열 벡터 3개), 두 볼 사이 거리 W 를 구합니다."""
    x = points[LEFT_CHEEK] - points[RIGHT_CHEEK]
    width = float(np.linalg.norm(x))
    x /= width
    y = points[FOREHEAD] - points[CHIN]
    y -= x * (y @ x)
    y /= np.linalg.norm(y)
    z = np.cross(x, y)
    origin = (points[LEFT_CHEEK] + points[RIGHT_CHEEK]) / 2
    return origin, np.stack([x, y, z], axis=1), width


def head_ellipsoid(points: np.ndarray, width: float) -> Tuple[np.ndarray, np.ndarray]:
    """머리 좌표 기준, 두개골을 근사하는 타원체의 중심과 반지름(x, y, z)."""
    center = np.array(HEAD_CENTER) * width
    half_height = max(HEAD_HALF_HEIGHT * width,
                      points[FOREHEAD, 1] - center[1] + CROWN_ABOVE_FOREHEAD * width)
    axes = np.array([HEAD_HALF_WIDTH * width, half_height, HEAD_HALF_DEPTH * width])
    return center, axes


def _slerp(a: np.ndarray, b: np.ndarray, t: float) -> np.ndarray:
    omega = np.arccos(np.clip(a @ b, -1.0, 1.0))[:, None]
    return (np.sin((1 - t) * omega) * a + np.sin(t * omega) * b) / np.sin(omega)


def build_shell(points: np.ndarray, oval: np.ndarray, center: np.ndarray, axes: np.ndarray):
    """얼굴 테두리에서 시작해 정수리, 옆머리, 턱 아래를 지나 뒤통수 한 점으로 모이는 껍데기.

    반환: (새 점들, 삼각형들) - 삼각형 번호는 points 뒤에 새 점들을 이어 붙인 기준
    """
    n_oval, base = len(oval), len(points)
    d0 = (points[oval] - center) / axes
    r0 = np.linalg.norm(d0, axis=1)
    d0 /= r0[:, None]
    back = np.array([0.0, 0.0, -1.0])

    rings = []
    for k in range(1, SHELL_RINGS):
        d = _slerp(d0, back, k / SHELL_RINGS)
        blend = min(1.0, k / SHELL_BLEND_RINGS)
        blend = blend * blend * (3 - 2 * blend)          # 부드럽게 바뀌도록
        r = r0 + (1.0 - r0) * blend
        rings.append(center + axes * d * r[:, None])
    pole = len(rings) * n_oval + base
    new_points = np.vstack(rings + [center + axes * back])

    def idx(k, i):
        i %= n_oval
        return oval[i] if k == 0 else base + (k - 1) * n_oval + i

    faces = []
    for k in range(SHELL_RINGS - 1):
        for i in range(n_oval):
            a, b, c, d = idx(k, i), idx(k, i + 1), idx(k + 1, i + 1), idx(k + 1, i)
            faces += [[a, b, c], [a, c, d]]
    last = SHELL_RINGS - 1
    for i in range(n_oval):
        faces.append([idx(last, i), idx(last, i + 1), pole])
    faces = np.array(faces)

    all_points = np.vstack([points, new_points])
    centroids = all_points[faces].mean(axis=1)
    faces = orient_faces(all_points, faces, centroids - center)
    return new_points, faces, pole


# ---------------------------------------------------------------- 매끈하게 만들기

def subdivide(vertices: np.ndarray, faces: np.ndarray, crease: np.ndarray, movable: np.ndarray):
    """삼각형 하나를 4개로 나누고 표면을 매끈하게 다듬습니다(Loop 방식).

    crease: 점마다 '꺾이는 경계선(얼굴 테두리, 눈/입 구멍) 위의 점'이면 True. 경계선 위의 변은
        볼록하게 하지 않고 정확히 가운데에 점을 둬서, 얼굴 테두리가 사진 밖으로 삐져나가지 않게 합니다.
    movable: 기존 점도 주변 평균 쪽으로 옮겨 다듬을 점(머리 껍데기)이면 True.
        얼굴 점은 MediaPipe 가 찾은 위치를 지키도록 움직이지 않습니다.
    새 삼각형 j 는 원래 삼각형 j % len(faces) 에서 나온 것입니다.
    반환: (점들, 삼각형들, 새 crease, 새 movable)
    """
    n, m = len(vertices), len(faces)
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    opposite = np.concatenate([faces[:, 2], faces[:, 0], faces[:, 1]])
    unique, inverse = np.unique(np.sort(edges, axis=1), axis=0, return_inverse=True)
    inverse = inverse.ravel()

    on_crease = crease[unique].all(axis=1)
    smooth = (np.bincount(inverse, minlength=len(unique)) == 2) & ~on_crease
    opposite_sum = np.zeros((len(unique), 3))
    np.add.at(opposite_sum, inverse, vertices[opposite])
    ends = vertices[unique].sum(axis=1)
    edge_points = np.where(smooth[:, None], 3 / 8 * ends + 1 / 8 * opposite_sum, ends / 2)

    # 기존 점 다듬기: 이웃 점 평균 쪽으로 이동(Loop 규칙의 꼭짓점 가중치)
    neighbor_sum = np.zeros_like(vertices)
    np.add.at(neighbor_sum, unique[:, 0], vertices[unique[:, 1]])
    np.add.at(neighbor_sum, unique[:, 1], vertices[unique[:, 0]])
    valence = np.bincount(unique.ravel(), minlength=n)[:, None]
    beta = np.where(valence > 3, 3 / (8 * np.maximum(valence, 1)), 3 / 16)
    smoothed = (1 - valence * beta) * vertices + beta * neighbor_sum
    move = movable & ~crease
    vertices = np.where(move[:, None], smoothed, vertices)
    edge_movable = movable[unique].any(axis=1) & ~on_crease

    a, b, c = faces.T
    ab, bc, ca = (inverse[k * m:(k + 1) * m] + n for k in range(3))
    new_faces = np.concatenate([
        np.stack([a, ab, ca], axis=1),
        np.stack([ab, b, bc], axis=1),
        np.stack([ca, bc, c], axis=1),
        np.stack([ab, bc, ca], axis=1),
    ])
    return (np.vstack([vertices, edge_points]), new_faces,
            np.r_[crease, on_crease], np.r_[movable, edge_movable])


# ---------------------------------------------------------------- 텍스처 좌표(UV)

def sphere_uv(points: np.ndarray, center: np.ndarray, axes: np.ndarray) -> np.ndarray:
    """머리를 앞에서 펼친 원형 지도 좌표. 얼굴 가운데가 원 중심, 뒤통수가 원 테두리.

    얼굴(앞쪽)에 텍스처 공간을 많이 주고, 사진에 안 보이는 뒤통수는 좁게 줍니다.
    """
    d = (points - center) / axes
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    theta = np.arccos(np.clip(d[:, 2], -1.0, 1.0))
    phi = np.arctan2(d[:, 1], d[:, 0])
    r = UV_RADIUS * (1.0 - (1.0 - theta / np.pi) ** UV_FACE_EMPHASIS)
    return np.stack([0.5 + r * np.cos(phi), 0.5 + r * np.sin(phi)], axis=1)


def make_uvs(points, faces, center, axes, pole):
    """점마다 UV 를 주고, 뒤통수 꼭짓점만 삼각형마다 따로 UV 를 줍니다(한 점이 원 테두리 전체이므로)."""
    uvs = sphere_uv(points, center, axes)
    face_uvs = faces.copy()
    extra = []
    for fi in np.where((faces == pole).any(axis=1))[0]:
        others = faces[fi][faces[fi] != pole]
        direction = (uvs[others] - 0.5).mean(axis=0)
        extra.append(0.5 + UV_RADIUS * direction / np.linalg.norm(direction))
        face_uvs[fi][faces[fi] == pole] = len(uvs) + len(extra) - 1
    return np.vstack([uvs, np.array(extra)]), face_uvs
