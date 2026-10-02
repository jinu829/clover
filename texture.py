"""여러 장의 사진으로 머리 전체 텍스처(피부/머리카락 이미지)를 만듭니다.

텍스처 이미지의 각 칸마다
1. 그 칸이 머리 표면의 어느 3D 위치인지 계산하고
2. 그 위치를 각 사진에 투영해 색을 가져온 뒤
3. 그 위치를 정면으로 본 사진일수록 크게 섞습니다(가려진 사진은 제외).
어느 사진에도 안 보인 곳은 좌우 반대편 색, 그래도 없으면 주변 색을 섞어 채웁니다.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
from scipy.ndimage import gaussian_filter

from .geometry import View, sphere_uv

TEX_SIZE = 2048
DEPTH_SIZE = 512          # 가려짐 판정용 깊이 지도 크기
VISIBILITY_POWER = 4      # 클수록 '정면으로 본 사진'을 더 강하게 우선(덜 섞여서 선명)
MIN_VIEW_COS = 0.3        # 이보다 비스듬히(약 72도 이상) 보이는 곳은 그 사진에서 색을 안 가져옴
MIN_VIEW_COS_FACE = 0.1   # 얼굴 부분은 좀 더 비스듬해도(약 84도까지) 사진 색을 씀
VIEW_RAMP = 0.2           # 사진 색에서 추정 색으로 넘어가는 구간의 폭(클수록 더 부드럽게)
OCCLUSION_TOLERANCE = 0.05
FILL_BLUR = 6             # 추정으로 채운 부분을 부드럽게 하는 정도
CONF_BLUR = 12            # 사진 색과 추정 색의 경계를 부드럽게 하는 정도


def _tri_pixels(p: np.ndarray, h: int, w: int) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """2D 삼각형 p(3x2, 픽셀 단위) 안에 중심이 들어가는 픽셀들과 무게중심 좌표."""
    x0, x1 = max(int(np.floor(p[:, 0].min())), 0), min(int(np.ceil(p[:, 0].max())), w - 1)
    y0, y1 = max(int(np.floor(p[:, 1].min())), 0), min(int(np.ceil(p[:, 1].max())), h - 1)
    if x1 < x0 or y1 < y0:
        return None
    a, b, c = p
    den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    if abs(den) < 1e-12:
        return None
    xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    l0 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / den
    l1 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / den
    l2 = 1.0 - l0 - l1
    inside = (l0 >= -1e-4) & (l1 >= -1e-4) & (l2 >= -1e-4)
    if not inside.any():
        return None
    iy = (ys[inside] - 0.5).astype(int)
    ix = (xs[inside] - 0.5).astype(int)
    return iy, ix, np.stack([l0[inside], l1[inside], l2[inside]], axis=1)


def _depth_buffer(points_view: np.ndarray, faces: np.ndarray, h: int, w: int):
    """사진 속 각 위치에서 카메라에 가장 가까운 머리 표면의 깊이(가려짐 판정용)."""
    q = DEPTH_SIZE / max(h, w)
    dh, dw = int(np.ceil(h * q)), int(np.ceil(w * q))
    depth = np.full((dh, dw), -np.inf)
    p2 = np.stack([points_view[:, 0] * q, -points_view[:, 1] * q], axis=1)
    for f in faces:
        hit = _tri_pixels(p2[f], dh, dw)
        if hit is None:
            continue
        iy, ix, bary = hit
        depth[iy, ix] = np.maximum(depth[iy, ix], bary @ points_view[f, 2])
    return depth, q


def _sample(img: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """사진에서 (x, y) 위치 색을 부드럽게(쌍선형 보간) 가져옵니다."""
    h, w = img.shape[:2]
    x = np.clip(x - 0.5, 0, w - 1.001)
    y = np.clip(y - 0.5, 0, h - 1.001)
    x0, y0 = x.astype(int), y.astype(int)
    x1, y1 = np.minimum(x0 + 1, w - 1), np.minimum(y0 + 1, h - 1)
    fx, fy = (x - x0)[:, None], (y - y0)[:, None]

    def at(yy, xx):
        return img[yy, xx].astype(np.float32)

    return (at(y0, x0) * (1 - fx) * (1 - fy) + at(y0, x1) * fx * (1 - fy)
            + at(y1, x0) * (1 - fx) * fy + at(y1, x1) * fx * fy)


def bake_texture(vertices, faces, normals, uvs, face_uvs, views: List[View],
                 origin, basis, center, axes, width, face_mask: np.ndarray) -> np.ndarray:
    """vertices/normals/center/axes 는 머리 좌표, views 는 사진들. 결과는 (T, T, 3) uint8.

    face_mask: 삼각형마다 얼굴 부분이면 True, 머리 껍데기면 False
    """
    T = TEX_SIZE

    # 1. 텍스처 칸마다 3D 위치와 표면 방향 구하기
    pos = np.zeros((T, T, 3), np.float32)
    nrm = np.zeros((T, T, 3), np.float32)
    covered = np.zeros((T, T), bool)
    on_face = np.zeros((T, T), bool)
    front_z = np.full((T, T), -np.inf, np.float32)   # 입술 안쪽처럼 겹치는 곳은 앞쪽 면이 차지
    for fi, (f, fu) in enumerate(zip(faces, face_uvs)):
        p = np.stack([uvs[fu, 0] * T, (1.0 - uvs[fu, 1]) * T], axis=1)
        hit = _tri_pixels(p, T, T)
        if hit is None:
            continue
        iy, ix, bary = hit
        z = bary @ vertices[f, 2]
        nearer = z > front_z[iy, ix]
        iy, ix, bary = iy[nearer], ix[nearer], bary[nearer]
        front_z[iy, ix] = z[nearer]
        pos[iy, ix] = bary @ vertices[f]
        nrm[iy, ix] = bary @ normals[f]
        covered[iy, ix] = True
        on_face[iy, ix] = face_mask[fi]

    P = pos[covered].astype(np.float64)
    N = nrm[covered].astype(np.float64)
    face_cells = on_face[covered]
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)
    P_front = P @ basis.T + origin           # 머리 좌표 -> 정면 사진 좌표
    N_front = N @ basis.T
    verts_front = vertices @ basis.T + origin

    # 2. 사진마다 색 가져와서 섞기
    #    strict: 충분히 정면으로 본 사진만 / loose: 좀 비스듬해도 보이면
    #    얼굴 부분은 배경이 섞일 걱정이 없어서, strict 로 못 칠한 곳(콧볼 아래 등)은 loose 를 씁니다.
    #    conf: 사진 색을 얼마나 믿을지(0~1). 비스듬할수록 서서히 줄여서 경계가 부드럽게 넘어가게 합니다.
    color, wsum = np.zeros((len(P), 3)), np.zeros(len(P))
    color_loose, wsum_loose = np.zeros((len(P), 3)), np.zeros(len(P))
    conf = np.zeros(len(P))
    for v in views:
        h, w = v.rgb.shape[:2]
        X = v.project(P_front)
        x, y = X[:, 0], -X[:, 1]

        depth, q = _depth_buffer(v.project(verts_front), faces, h, w)
        dy = np.clip((y * q).astype(int), 0, depth.shape[0] - 1)
        dx = np.clip((x * q).astype(int), 0, depth.shape[1] - 1)
        visible = (x >= 0) & (x < w) & (y >= 0) & (y < h)
        visible &= X[:, 2] >= depth[dy, dx] - OCCLUSION_TOLERANCE * width * v.s

        cos = N_front @ v.camera_dir
        weight = np.clip(cos, 0, None) ** VISIBILITY_POWER * visible
        loose = np.where(cos > MIN_VIEW_COS_FACE, weight, 0.0)
        strict = np.where(cos > MIN_VIEW_COS, weight, 0.0)
        sample = _sample(v.rgb, x, y)
        color += strict[:, None] * sample
        wsum += strict
        color_loose += loose[:, None] * sample
        wsum_loose += loose
        conf = np.maximum(conf, np.clip((cos - MIN_VIEW_COS) / VIEW_RAMP, 0, 1) * visible)

    use_loose = (wsum <= 1e-4) & face_cells & (wsum_loose > 1e-6)
    color[use_loose], wsum[use_loose] = color_loose[use_loose], wsum_loose[use_loose]

    # 그래도 빈 얼굴 부분(입 안쪽, 콧구멍 아래 등)은 정면 사진에서 그 위치 색을 그대로 씁니다.
    front = views[0]
    rest = (wsum <= 1e-6) & face_cells
    if rest.any():
        X = front.project(P_front[rest])
        color[rest] = _sample(front.rgb, X[:, 0], -X[:, 1])
        wsum[rest] = 1.0
    conf[face_cells] = 1.0

    tex = np.zeros((T, T, 3), np.float32)
    conf_map = np.zeros((T, T), np.float32)
    tex[covered] = color / np.maximum(wsum, 1e-12)[:, None]
    conf_map[covered] = conf

    # 3. 덜 보인 곳: 좌우 반대편이 더 잘 보였으면 그 색을 가져오기
    weak = conf < 1.0
    if weak.any():
        cells = np.argwhere(covered)[weak]
        mirror_uv = sphere_uv(P[weak] * np.array([-1.0, 1.0, 1.0]), center, axes)
        mx = np.clip((mirror_uv[:, 0] * T).astype(int), 0, T - 1)
        my = np.clip(((1.0 - mirror_uv[:, 1]) * T).astype(int), 0, T - 1)
        better = conf_map[my, mx] > conf[weak]
        ys, xs = cells[better, 0], cells[better, 1]
        tex[ys, xs] = tex[my[better], mx[better]]
        conf_map[ys, xs] = conf_map[my[better], mx[better]]

    # 4. 안 보인 곳: 주변 색을 넓게 번지듯 섞어 채우고, 믿을 만한 정도(conf)에 따라 자연스럽게 섞기
    #    conf 를 흐리게 해서 '보임/안 보임' 경계가 얼룩이나 계단 없이 서서히 바뀌게 합니다(얼굴은 그대로).
    on_face_map = np.zeros((T, T), bool)
    on_face_map[covered] = face_cells
    soft = gaussian_filter(conf_map, CONF_BLUR)
    conf_map = np.where(on_face_map, conf_map, np.minimum(conf_map, soft))
    fill = _push_pull(tex, conf_map >= 0.5)
    fill = np.stack([gaussian_filter(fill[..., c], FILL_BLUR) for c in range(3)], axis=-1)
    alpha = conf_map[..., None]
    tex = alpha * tex + (1 - alpha) * fill

    return np.clip(tex, 0, 255).astype(np.uint8)


def _push_pull(tex: np.ndarray, known: np.ndarray) -> np.ndarray:
    """빈 칸을 주변 색의 평균으로 채웁니다. 가까운 색일수록 크게, 먼 곳은 넓은 평균으로."""
    levels = [(tex * known[..., None], known.astype(np.float32))]
    while levels[-1][1].shape[0] > 1:
        c, w = levels[-1]
        h2, w2 = (c.shape[0] + 1) // 2, (c.shape[1] + 1) // 2
        c = np.pad(c, ((0, h2 * 2 - c.shape[0]), (0, w2 * 2 - c.shape[1]), (0, 0)))
        w = np.pad(w, ((0, h2 * 2 - w.shape[0]), (0, w2 * 2 - w.shape[1])))
        levels.append((c.reshape(h2, 2, w2, 2, 3).sum(axis=(1, 3)),
                       w.reshape(h2, 2, w2, 2).sum(axis=(1, 3))))

    c, w = levels[-1]
    color = c / np.maximum(w, 1e-6)[..., None]
    for c, w in reversed(levels[:-1]):
        up = np.repeat(np.repeat(color, 2, axis=0), 2, axis=1)[: c.shape[0], : c.shape[1]]
        up = gaussian_filter(up, sigma=(1, 1, 0))   # 확대할 때 계단 무늬가 생기지 않게
        alpha = np.clip(w, 0, 1)[..., None]
        color = c / np.maximum(w, 1e-6)[..., None] * alpha + up * (1 - alpha)
    return color
