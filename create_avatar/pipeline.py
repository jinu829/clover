"""
exportnumberbymediapipe.py가 측정을 끝낸 뒤 나머지 단계를 차례로 실행하는 파이프라인.

사람(사진 이름)마다 아래 순서로 진행하고, 한 단계가 실패하면 그 사람만 멈추고 다음 사람으로 넘어간다.
  2. createHuman.py     : measurements/<이름>.json -> models_mhm/<이름>.mhm
  3. keentools_3d/main.py: 얼굴 사진 -> heads/<이름>.zip  (heads에 이미 있으면 건너뜀)
  4. importToBlender.py : models_mhm/<이름>.mhm -> avatars/<이름>.blend   (Blender 백그라운드)
  5. attachFace.py      : avatars/<이름>.blend + heads/<이름>.zip -> avatars/<이름>.blend (덮어씀)

createHuman.py는 MakeHuman 소스를 불러오면서 현재 폴더와 sys.path를 바꾸고,
4·5단계는 Blender 안에서만 돌기 때문에 모든 단계를 별도 프로세스로 실행한다.
"""

import glob
import os
import re
import shutil
import subprocess
import sys
import time

import createHuman  # MakeHuman 소스 위치 확인용 (createHuman 맨 위 import는 표준 라이브러리뿐)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)

MODELS_MHM_DIR = os.path.join(SCRIPT_DIR, "models_mhm")  # createHuman.py 결과 (.mhm)
AVATARS_DIR = os.path.join(SCRIPT_DIR, "avatars")        # importToBlender.py / attachFace.py 결과 (.blend)
HEADS_DIR = os.path.join(SCRIPT_DIR, "heads")            # FaceBuilder 머리 zip
KEENTOOLS_DIR = os.path.join(REPO_DIR, "keentools_3d")
DEFAULT_FACE_IMAGES_DIR = os.path.join(KEENTOOLS_DIR, "input_images")

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")  # KeenTools가 받는 형식


# --- 도구 찾기 ------------------------------------------------------------------

def find_blender(explicit=None):
    """Blender 실행 파일 경로. --blender > 환경변수 BLENDER > PATH > 기본 설치 위치 순서로 찾는다."""
    for candidate in (explicit, os.environ.get("BLENDER")):
        if candidate:
            return candidate if os.path.isfile(candidate) else shutil.which(candidate)
    found = shutil.which("blender")
    if found:
        return found
    patterns = [
        r"C:\Program Files\Blender Foundation\Blender*\blender.exe",
        os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Steam\steamapps\common\Blender\blender.exe"),
        "/Applications/Blender*.app/Contents/MacOS/Blender",
        "/snap/bin/blender",
    ]
    candidates = [path for pattern in patterns for path in glob.glob(pattern)]
    if not candidates:
        return None

    def version_key(path):  # "Blender 4.2" < "Blender 4.10" 이 되도록 숫자로 비교
        return [int(n) for n in re.findall(r"\d+", path)]

    return max(candidates, key=version_key)


def find_head_file(heads_dir, stem):
    """attachFace.py와 같은 규칙: heads/<이름>.zip, <이름>.obj, <이름>/ 폴더"""
    for candidate in (f"{stem}.zip", f"{stem}.obj", stem):
        path = os.path.join(heads_dir, candidate)
        if os.path.exists(path):
            return path
    return None


def _images_in(folder):
    if not os.path.isdir(folder):
        return []
    return [n for n in os.listdir(folder) if n.lower().endswith(IMAGE_EXTENSIONS)]


def find_face_images(face_dir, stem, single_person):
    """얼굴 사진 폴더. <face_dir>/<이름>/ 이 있으면 그것, 한 사람만 처리할 때는 <face_dir> 자체도 허용."""
    person_dir = os.path.join(face_dir, stem)
    if _images_in(person_dir):
        return person_dir
    if single_person and _images_in(face_dir):
        return face_dir
    return None


KEENTOOLS_KEY_HELP = ("KeenTools API 키가 없습니다. keentools_3d\\.env 파일에 KEENTOOLS_API_KEY=발급받은키 한 줄을 넣거나, "
                      "PowerShell에서 $env:KEENTOOLS_API_KEY = \"발급받은키\" 로 설정하세요")


def has_keentools_key():
    if os.environ.get("KEENTOOLS_API_KEY"):
        return True
    env_path = os.path.join(KEENTOOLS_DIR, ".env")
    if os.path.isfile(env_path):
        with open(env_path, encoding="utf-8") as f:
            return any(line.strip().startswith("KEENTOOLS_API_KEY=") and line.split("=", 1)[1].strip()
                       for line in f)
    return False


# --- 단계 실행 ------------------------------------------------------------------

def _run(cmd, cwd=SCRIPT_DIR):
    print("  $ " + subprocess.list2cmdline(cmd))
    return subprocess.run(cmd, cwd=cwd).returncode == 0


def _made(path, started_at):
    """path가 이번 실행에서 새로 만들어졌거나 갱신됐는지"""
    return os.path.isfile(path) and os.path.getmtime(path) >= started_at - 1


def _blender_cmd(blender, script, args):
    # --python-exit-code 1: 스크립트 오류가 나면 Blender도 실패 코드로 끝나게 함 (--python보다 앞에 와야 함)
    return [blender, "--background", "--python-exit-code", "1",
            "--python", os.path.join(SCRIPT_DIR, script), "--"] + args


def make_mhm(json_path, stem, opts):
    mhm_path = os.path.join(MODELS_MHM_DIR, f"{stem}.mhm")
    cmd = [sys.executable, os.path.join(SCRIPT_DIR, "createHuman.py"), json_path,
           "--out-dir", MODELS_MHM_DIR, "--gender", opts.gender,
           "--age", str(opts.age), "--muscle", str(opts.muscle)]
    cmd += ["--mh-src", opts.mh_src]
    started_at = time.time()
    if _run(cmd) and _made(mhm_path, started_at):
        return mhm_path
    return None


def make_head(stem, opts, single_person):
    """heads/<이름>.zip을 찾거나 KeenTools로 만든다. 얼굴 단계를 못 하면 None과 이유를 돌려준다."""
    existing = find_head_file(opts.heads_dir, stem)
    if existing:
        print(f"  머리 파일 사용: {existing}")
        return existing, None
    face_dir = find_face_images(opts.face_images, stem, single_person)
    missing = []
    if not face_dir:
        hint = os.path.join(opts.face_images, stem) if not single_person else opts.face_images
        missing.append(f"얼굴 사진이 없습니다 ({hint}에 jpg/png를 넣으세요)")
    if not has_keentools_key():
        missing.append(KEENTOOLS_KEY_HELP)
    if missing:
        return None, f"{opts.heads_dir}에 {stem}.zip이 없고, KeenTools로 만들 준비도 안 됐습니다:\n    - " + "\n    - ".join(missing)
    os.makedirs(opts.heads_dir, exist_ok=True)
    head_path = os.path.join(opts.heads_dir, f"{stem}.zip")
    cmd = [sys.executable, os.path.join(KEENTOOLS_DIR, "main.py"), "--images", face_dir, "--out", head_path]
    started_at = time.time()
    if _run(cmd, cwd=KEENTOOLS_DIR) and _made(head_path, started_at):
        return head_path, None
    return None, "KeenTools 머리 생성에 실패했습니다"


def mpfb_install_help(blender, status):
    """MPFB2가 없을 때 보여 줄 안내"""
    if status.startswith("DISABLED"):
        first = f"MPFB2가 설치돼 있지만 켜지지 않았습니다 ({blender})."
    elif status == "MISSING":
        first = f"이 Blender에 MPFB2(Blender용 MakeHuman 애드온)가 설치돼 있지 않습니다 ({blender})."
    else:
        first = f"MPFB2 설치 여부를 확인하지 못했습니다 ({blender}): {status}"
    return (first + "\n"
            "4·5단계(Blender로 불러오기, 얼굴 합치기)는 MPFB2가 있어야 해서 건너뜁니다.\n"
            "  1) Blender를 열고 Edit > Preferences > Get Extensions\n"
            "     (처음이면 'Allow Online Access'를 켭니다)\n"
            "  2) 검색창에 MPFB 입력 -> Install\n"
            "     인터넷 없이 설치하려면 https://extensions.blender.org/add-ons/mpfb/ 에서 zip을 받아\n"
            "     Get Extensions 오른쪽 위 v 메뉴 > Install from Disk... 로 설치\n"
            "  3) Preferences > Add-ons에서 MPFB가 체크(켜짐)돼 있는지 확인\n"
            "  4) --blender로 실행하는 Blender와 같은 버전에 설치했는지 확인 (확장은 버전마다 따로 설치됨)\n"
            "설치 후 같은 명령을 다시 실행하세요. (.mhm은 models_mhm에 이미 만들어져 있습니다)")


def check_mpfb(blender):
    """Blender를 한 번 띄워 MPFB2가 쓸 수 있는지 확인. "OK", "MISSING", "DISABLED ..." 또는 오류 설명을 돌려준다."""
    cmd = _blender_cmd(blender, "importToBlender.py", ["--check-mpfb"])
    try:
        result = subprocess.run(cmd, cwd=SCRIPT_DIR, capture_output=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"Blender 실행 실패: {e}"
    output = result.stdout.decode("utf-8", errors="replace")
    for line in output.splitlines():
        if line.startswith("MPFB2_CHECK "):
            return line[len("MPFB2_CHECK "):].strip()
    return f"점검 결과 없음 (종료 코드 {result.returncode})"


def import_to_blender(blender, mhm_path, stem, measurements_dir):
    blend_path = os.path.join(AVATARS_DIR, f"{stem}.blend")
    cmd = _blender_cmd(blender, "importToBlender.py",
                       [mhm_path, "--out", AVATARS_DIR, "--measurements-dir", measurements_dir])
    started_at = time.time()
    if _run(cmd) and _made(blend_path, started_at):
        return blend_path
    return None


def attach_face(blender, blend_path, head_path):
    cmd = _blender_cmd(blender, "attachFace.py", [blend_path, "--head", head_path, "--out", AVATARS_DIR])
    started_at = time.time()
    return _run(cmd) and _made(blend_path, started_at)


# --- 전체 실행 ------------------------------------------------------------------

def run_pipeline(measured, measurements_dir, opts):
    """measured: {사진 경로: 측정 결과 dict 또는 None}. 측정에 성공한 사람만 다음 단계로 보낸다."""
    measurements_dir = os.path.abspath(measurements_dir)
    opts.heads_dir = os.path.abspath(opts.heads_dir)
    opts.face_images = os.path.abspath(opts.face_images)
    stems = [os.path.splitext(os.path.basename(p))[0] for p, m in measured.items() if m]
    if not stems:
        print("측정에 성공한 사진이 없어 파이프라인을 멈춥니다.")
        return {}
    single_person = len(measured) == 1

    mh_src = createHuman.find_makehuman_src(opts.mh_src)
    if not mh_src:
        print("\n" + createHuman.makehuman_src_help(opts.mh_src))
        print("\n측정 결과는 저장돼 있으니, 위처럼 준비한 뒤 같은 명령을 다시 실행하면 됩니다.")
        return {stem: "중단: MakeHuman 소스 없음" for stem in stems}
    opts.mh_src = mh_src
    print(f"MakeHuman 소스: {mh_src}")

    blender = find_blender(opts.blender)
    if not blender:
        print("경고: Blender를 찾지 못했습니다. .mhm까지만 만들고 4·5단계는 건너뜁니다.\n"
              "      --blender \"C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe\" 처럼 지정하거나 "
              "환경변수 BLENDER를 설정하세요.")
    else:
        print(f"Blender: {blender}")

    # 4·5단계는 MPFB2가 있어야 함 (4단계는 같은 이름의 .fbx가 있으면 대신 쓸 수 있음)
    mpfb_status = check_mpfb(blender) if blender else None
    mpfb_ok = mpfb_status == "OK"
    if blender:
        print("MPFB2: " + ("사용 가능" if mpfb_ok else "없음"))
        if not mpfb_ok:
            print("\n경고: " + mpfb_install_help(blender, mpfb_status))

    os.makedirs(MODELS_MHM_DIR, exist_ok=True)
    os.makedirs(AVATARS_DIR, exist_ok=True)

    summary = {}
    for stem in stems:
        print(f"\n===== [{stem}] =====")
        json_path = os.path.join(measurements_dir, f"{stem}.json")

        print("[2/5] 몸 만들기 (createHuman.py)")
        mhm_path = make_mhm(json_path, stem, opts)
        if not mhm_path:
            summary[stem] = "실패: createHuman.py (.mhm 생성)"
            continue

        head_path, why_no_face = None, "--skip-face"
        if not opts.skip_face:
            print("[3/5] 얼굴 준비 (heads 폴더 / keentools_3d/main.py)")
            head_path, why_no_face = make_head(stem, opts, single_person)
            if not head_path:
                print(f"  경고: {why_no_face}. 얼굴 합치기를 건너뜁니다.")

        if not blender:
            summary[stem] = f"부분 완료: {mhm_path} (Blender 없음)"
            continue

        if not mpfb_ok and not os.path.isfile(os.path.splitext(mhm_path)[0] + ".fbx"):
            summary[stem] = f"부분 완료: {mhm_path} (MPFB2 없음, 4·5단계 건너뜀)"
            continue

        print("[4/5] Blender로 불러오기 (importToBlender.py)")
        blend_path = import_to_blender(blender, mhm_path, stem, measurements_dir)
        if not blend_path:
            summary[stem] = "실패: importToBlender.py (.blend 생성)"
            continue

        if not head_path:
            summary[stem] = f"부분 완료: {blend_path} (얼굴 없음: {why_no_face})"
            continue

        print("[5/5] 얼굴 합치기 (attachFace.py)")
        if not mpfb_ok:
            print("  경고: MPFB2가 없어 눈·눈썹·뼈대를 새 얼굴에 다시 맞추는 단계는 빠집니다.")
        if attach_face(blender, blend_path, head_path):
            summary[stem] = f"완료: {blend_path}"
        else:
            summary[stem] = f"실패: attachFace.py (얼굴 없는 몸은 {blend_path}에 남아 있음)"

    print("\n===== 결과 =====")
    for stem, result in summary.items():
        print(f"  {stem}: {result}")
    if blender and not mpfb_ok:
        print("\n" + mpfb_install_help(blender, mpfb_status))
    return summary


def add_pipeline_arguments(parser):
    group = parser.add_argument_group("파이프라인 (측정 뒤 .mhm -> .blend -> 얼굴 합치기까지 자동 실행)")
    group.add_argument("--measure-only", action="store_true", help="측정(JSON)만 하고 다음 단계는 실행하지 않음")
    group.add_argument("--gender", choices=["male", "female"], default="male", help="createHuman.py 성별 (기본 male)")
    group.add_argument("--age", type=float, default=25.0, help="createHuman.py 나이 (기본 25)")
    group.add_argument("--muscle", type=float, default=0.5, help="createHuman.py 근육 0~1 (기본 0.5)")
    group.add_argument("--mh-src", default=os.environ.get("MAKEHUMAN_SRC", ""),
                       help="MakeHuman 소스의 makehuman/ 폴더 (기본: 환경변수 MAKEHUMAN_SRC, 없으면 C:\\makehuman-src 등에서 자동 탐색)")
    group.add_argument("--blender", default=None,
                       help="blender 실행 파일 경로 (기본: 환경변수 BLENDER, PATH, 기본 설치 위치 순서로 찾음)")
    group.add_argument("--heads-dir", default=HEADS_DIR,
                       help="<이름>.zip 머리 파일 폴더 (기본: create_avatar/heads)")
    group.add_argument("--face-images", default=DEFAULT_FACE_IMAGES_DIR,
                       help="머리가 없을 때 KeenTools에 보낼 얼굴 사진 폴더. 사람마다 <폴더>/<이름>/, "
                            "한 명만 처리할 때는 폴더에 바로 넣어도 됨 (기본: keentools_3d/input_images)")
    group.add_argument("--skip-face", action="store_true", help="얼굴 단계(3·5단계)를 건너뜀")
    return parser
