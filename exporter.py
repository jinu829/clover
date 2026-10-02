"""만든 3D 얼굴을 파일로 저장합니다.

- face.obj / face.mtl : Blender, Windows '3D 뷰어' 등에서 여는 표준 3D 파일
- viewer.html         : 더블클릭하면 웹브라우저에서 바로 돌려볼 수 있는 뷰어
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Dict

from .engines.base import FaceMesh, vertex_normals


def _normals(mesh: FaceMesh):
    return mesh.normals if mesh.normals is not None else vertex_normals(mesh.vertices, mesh.faces)


def _face_uvs(mesh: FaceMesh):
    return mesh.face_uvs if mesh.face_uvs is not None else mesh.faces


def write_obj(mesh: FaceMesh, out_dir: Path) -> Path:
    obj_path = out_dir / "face.obj"
    has_tex = mesh.uvs is not None and mesh.texture_path is not None

    lines = ["# FaceBuilder 결과물"]
    if has_tex:
        (out_dir / "face.mtl").write_text(
            "newmtl face\nKd 1 1 1\n" f"map_Kd {mesh.texture_path.name}\n", encoding="utf-8"
        )
        lines += ["mtllib face.mtl", "usemtl face"]

    lines += [f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in mesh.vertices]
    if has_tex:
        lines += [f"vt {u:.6f} {v:.6f}" for u, v in mesh.uvs]
    lines += [f"vn {x:.5f} {y:.5f} {z:.5f}" for x, y, z in _normals(mesh)]
    # OBJ 파일은 번호가 1부터 시작합니다. 형식: f 점/텍스처좌표/방향
    for (a, b, c), (ta, tb, tc) in zip(mesh.faces + 1, _face_uvs(mesh) + 1):
        if has_tex:
            lines.append(f"f {a}/{ta}/{a} {b}/{tb}/{b} {c}/{tc}/{c}")
        else:
            lines.append(f"f {a}//{a} {b}//{b} {c}//{c}")

    obj_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return obj_path


def write_viewer(mesh: FaceMesh, out_dir: Path) -> Path:
    texture = None
    if mesh.texture_path is not None and mesh.uvs is not None:
        mime = "image/png" if mesh.texture_path.suffix.lower() == ".png" else "image/jpeg"
        b64 = base64.b64encode(mesh.texture_path.read_bytes()).decode("ascii")
        texture = f"data:{mime};base64,{b64}"

    data = {
        "positions": mesh.vertices.astype(float).round(5).ravel().tolist(),
        "normals": _normals(mesh).astype(float).round(4).ravel().tolist(),
        "faces": mesh.faces.astype(int).ravel().tolist(),
        "uvs": None if mesh.uvs is None else mesh.uvs.astype(float).round(5).ravel().tolist(),
        "faceUvs": _face_uvs(mesh).astype(int).ravel().tolist(),
        "texture": texture,
    }
    html_path = out_dir / "viewer.html"
    html_path.write_text(_VIEWER_TEMPLATE.replace("__DATA__", json.dumps(data)), encoding="utf-8")
    return html_path


def export_all(mesh: FaceMesh, out_dir: Path) -> Dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    return {"obj": write_obj(mesh, out_dir), "viewer": write_viewer(mesh, out_dir)}


_VIEWER_TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>3D 얼굴 뷰어</title>
<style>
  html, body { margin: 0; height: 100%; overflow: hidden; background: #1e1f22; color: #e8e8e8;
               font-family: "Malgun Gothic", sans-serif; }
  #info { position: absolute; top: 12px; left: 12px; font-size: 14px; line-height: 1.6;
          background: rgba(0,0,0,.45); padding: 8px 12px; border-radius: 6px; }
</style>
<script type="importmap">
{ "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/" } }
</script>
</head>
<body>
<div id="info">
  왼쪽 드래그: 회전 · 휠: 확대/축소 · 오른쪽 드래그: 이동<br>
  T 키: 사진 입히기 켜기/끄기 · W 키: 와이어프레임
</div>
<script type="module">
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const DATA = __DATA__;

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(innerWidth, innerHeight);
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1e1f22);
const camera = new THREE.PerspectiveCamera(35, innerWidth / innerHeight, 0.01, 100);
camera.position.set(0, 0, 4);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

scene.add(new THREE.AmbientLight(0xffffff, 1.2));
const light = new THREE.DirectionalLight(0xffffff, 1.6);
light.position.set(1, 1, 2);
scene.add(light);

// 삼각형 꼭짓점마다 점/방향/텍스처좌표를 풀어서 넣습니다(꼭짓점마다 UV 가 다를 수 있음).
const n = DATA.faces.length;
const pos = new Float32Array(n * 3), nrm = new Float32Array(n * 3);
const uv = DATA.uvs ? new Float32Array(n * 2) : null;
for (let i = 0; i < n; i++) {
  const v = DATA.faces[i];
  for (let k = 0; k < 3; k++) {
    pos[i * 3 + k] = DATA.positions[v * 3 + k];
    nrm[i * 3 + k] = DATA.normals[v * 3 + k];
  }
  if (uv) {
    const t = DATA.faceUvs[i];
    uv[i * 2] = DATA.uvs[t * 2];
    uv[i * 2 + 1] = DATA.uvs[t * 2 + 1];
  }
}
const geometry = new THREE.BufferGeometry();
geometry.setAttribute("position", new THREE.BufferAttribute(pos, 3));
geometry.setAttribute("normal", new THREE.BufferAttribute(nrm, 3));
if (uv) geometry.setAttribute("uv", new THREE.BufferAttribute(uv, 2));

const plain = new THREE.MeshStandardMaterial({ color: 0xd9b8a3, roughness: 0.8, side: THREE.DoubleSide });
let textured = null;
if (DATA.texture) {
  const tex = new THREE.TextureLoader().load(DATA.texture);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = renderer.capabilities.getMaxAnisotropy();   // 비스듬히 볼 때도 선명하게
  textured = new THREE.MeshStandardMaterial({ map: tex, roughness: 0.9, side: THREE.DoubleSide });
}
const mesh = new THREE.Mesh(geometry, textured || plain);
scene.add(mesh);

addEventListener("keydown", (e) => {
  const key = e.key.toLowerCase();
  if (key === "t" && textured) mesh.material = mesh.material === textured ? plain : textured;
  if (key === "w") { plain.wireframe = !plain.wireframe; if (textured) textured.wireframe = plain.wireframe; }
});
addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});
renderer.setAnimationLoop(() => { controls.update(); renderer.render(scene, camera); });
</script>
</body>
</html>
"""
