"""
측정값 JSON(exportnumberbymediapipe.py 결과)으로 MakeHuman 아바타(.mhm)를 만든다.

모디파이어 값을 고정 공식으로 환산하지 않고, MakeHuman 메시에 직접 적용해 본 뒤
MakeHuman 자체 측정 기준(Measure 탭의 ruler, 키는 getHeightCm)으로 잰 cm가
목표 cm에 맞을 때까지 이분 탐색으로 맞춘다(피팅).

피팅 순서: 성별/나이/근육(입력값) -> 키 -> 체중 -> 부위별 둘레

실행 방법은 두 가지:
1) 일반 파이썬에서 (여러 장 일괄 처리용, MakeHuman 소스 필요)
   git clone https://github.com/makehumancommunity/makehuman.git
   pip install numpy PyQt5 PyOpenGL
   python createHuman.py measurements/A.json --out A.mhm --gender male --mh-src <clone경로>/makehuman

2) MakeHuman 프로그램 안에서 (Utilities > Shell 탭에 입력)
   import sys; sys.path.append(r"<createHuman.py가 있는 폴더>")
   import createHuman; createHuman.fit_in_makehuman(r"<경로>/A.json", gender="male")
   -> 화면의 아바타가 피팅되고 .mhm도 저장된다.
"""
import json
import os
import shutil
import sys

MAKEHUMAN_MODELS_DIR = r"C:\Users\enjoyer\Documents\makehuman\v1py3"
MAKEHUMAN_SRC_DIR = os.environ.get("MAKEHUMAN_SRC", "")  # MakeHuman 소스의 makehuman/ 폴더 (makehuman.py가 있는 곳)

# 측정 JSON 키 -> MakeHuman 둘레 모디파이어 (Measure 탭 ruler 이름과 동일)
CIRC_MODIFIERS = {
    "chest_circumference_cm": "measure/measure-bust-circ-decr|incr",
    "waist_circumference_cm": "measure/measure-waist-circ-decr|incr",
    "hip_circumference_cm": "measure/measure-hips-circ-decr|incr",
    "thigh_circumference_cm": "measure/measure-thigh-circ-decr|incr",
}

GENDER_VALUES = {"male": 1.0, "female": 0.0}

BISECT_STEPS = 18          # 이분 탐색 반복 횟수 (구간 1 기준 해상도 약 0.000004)
TOLERANCE_CM = 0.1         # 이 오차 안이면 맞춘 것으로 간주
CIRC_PASSES = 3            # 둘레 모디파이어끼리 서로 영향을 주므로 여러 바퀴 반복


def load_measurements(export_path="measurements.json"):
    """exportnumberbymediapipe.py가 저장한 측정값 JSON을 읽어옴"""
    with open(export_path, "r", encoding="utf-8") as f:
        return json.load(f)


# --- MakeHuman 메시에서 cm 재기 ---------------------------------------------

_RULER = None


def _ruler():
    """Measure 탭과 같은 ruler(부위별 정점 목록)를 가져온다"""
    global _RULER
    if _RULER is None:
        try:  # MakeHuman 프로그램 안: 이미 로드된 Measure 탭의 ruler 사용
            from core import G
            _RULER = G.app.getTask("Modelling", "Measure").ruler
        except Exception:  # 화면 없이 실행: 플러그인 모듈에서 직접 생성
            import importlib
            _RULER = importlib.import_module("0_modeling_a_measurement").Ruler()
    return _RULER


def measure_cm(human, modifier_name):
    """Measure 탭에 표시되는 값과 같은 방식으로 둘레/길이(cm)를 잰다"""
    return _ruler().getMeasure(human, modifier_name, "metric")


def _set(human, modifier_name, value):
    human.getModifier(modifier_name).setValue(value)
    human.applyAllTargets()


def _bisect(human, modifier_name, lo, hi, read_cm, target_cm, tol=TOLERANCE_CM / 10):
    """modifier 값을 [lo, hi]에서 이분 탐색해 read_cm()이 target_cm에 가장 가깝게 맞춘다.
    read_cm은 modifier 값에 대해 증가한다고 가정한다(키·체중·둘레 모두 해당).
    범위 끝에서도 목표에 못 미치면 끝값으로 두고 clipped=True를 반환한다."""
    _set(human, modifier_name, lo)
    lo_cm = read_cm()
    _set(human, modifier_name, hi)
    hi_cm = read_cm()
    if target_cm <= lo_cm:
        _set(human, modifier_name, lo)
        return lo, lo_cm, True
    if target_cm >= hi_cm:
        return hi, hi_cm, True

    for _ in range(BISECT_STEPS):
        mid = (lo + hi) / 2
        _set(human, modifier_name, mid)
        mid_cm = read_cm()
        if abs(mid_cm - target_cm) <= tol:
            return mid, mid_cm, False
        if mid_cm < target_cm:
            lo = mid
        else:
            hi = mid
    mid = (lo + hi) / 2
    _set(human, modifier_name, mid)
    return mid, read_cm(), False


def _circ_log_error(human, targets):
    """측정 둘레들이 목표보다 평균적으로 얼마나 큰지(로그 비율 평균). 0이면 평균적으로 일치"""
    import math
    errs = [math.log(measure_cm(human, mod) / cm) for mod, cm in targets.items()]
    return sum(errs) / len(errs)


def fit_human(human, measured, gender="male", age_years=25.0, muscle=0.5, log=print):
    """human(MakeHuman Human 객체)을 측정값에 맞게 피팅하고 결과 요약을 반환한다."""
    height_cm = measured.get("real_height_cm")
    targets = {mod: measured[key] for key, mod in CIRC_MODIFIERS.items() if measured.get(key)}

    # 0. 이전 값 초기화 후 입력값으로 정하는 매크로
    for mod in CIRC_MODIFIERS.values():
        human.getModifier(mod).setValue(0.0)
    human.getModifier("macrodetails/Gender").setValue(GENDER_VALUES[gender])
    human.setAgeYears(age_years)
    human.getModifier("macrodetails-universal/Muscle").setValue(muscle)
    human.getModifier("macrodetails-universal/Weight").setValue(0.5)
    human.applyAllTargets()

    report = {}
    clipped = []

    # 1~2. 키와 체중은 서로 조금씩 영향을 주므로 두 번 번갈아 맞춘다
    for _ in range(2):
        if height_cm:
            v, cm, c = _bisect(human, "macrodetails-height/Height", 0.0, 1.0, human.getHeightCm, height_cm)
            report["height"] = (v, cm, height_cm)
            if c:
                clipped.append("height")
        if targets:
            # 체중은 전체 볼륨을 정하므로, 둘레들의 평균 오차가 0이 되도록 맞춘다
            v, err, c = _bisect(human, "macrodetails-universal/Weight", 0.0, 1.0,
                                lambda: _circ_log_error(human, targets), 0.0, tol=0.001)
            report["weight"] = (v, err)
            if c:
                clipped.append("weight")

    # 3. 남은 차이는 부위별 둘레 모디파이어로 맞춘다
    for _ in range(CIRC_PASSES):
        for mod, cm in targets.items():
            v, got, c = _bisect(human, mod, -1.0, 1.0, lambda m=mod: measure_cm(human, m), cm)
            report[mod] = (v, got, cm)
        if all(abs(measure_cm(human, mod) - cm) <= TOLERANCE_CM for mod, cm in targets.items()):
            break

    # 최종 결과(둘레 모디파이어가 키를 바꿨을 수 있으니 실제 값으로 다시 읽음)
    final = {"height_cm": (human.getHeightCm(), height_cm)}
    for mod, cm in targets.items():
        got = measure_cm(human, mod)
        final[mod] = (got, cm)
        if abs(got - cm) > 1.0:
            clipped.append(mod)

    log("피팅 결과 (MakeHuman 측정값 / 목표값):")
    log(f"  키: {final['height_cm'][0]:.1f} / {height_cm:.1f} cm" if height_cm else "  키: 목표값 없음")
    for mod, (got, cm) in final.items():
        if mod != "height_cm":
            log(f"  {mod.split('/')[1].replace('measure-', '').replace('-decr|incr', '')}: "
                f"{got:.1f} / {cm:.1f} cm (모디파이어 {human.getModifier(mod).getValue():+.3f})")
    log(f"  체중 매크로: {human.getModifier('macrodetails-universal/Weight').getValue():.3f}")
    if clipped:
        log(f"경고: 모디파이어 범위 안에서 목표에 도달하지 못한 항목: {sorted(set(clipped))}")
    return {"final": final, "clipped": sorted(set(clipped))}


# --- .mhm 저장 ----------------------------------------------------------------

def generate_mhm_file(output_path, human):
    """피팅된 human의 모디파이어 값으로 .mhm 파일을 생성 (MakeHuman 저장 형식과 동일)"""
    mhm_content = [
        "version v1.2.0",   # MakeHuman은 "v" 접두사가 있는 버전만 파싱 가능
        "tags body",
    ]
    for modifier in human.modifiers:
        if modifier.getValue() or modifier.isMacro():
            mhm_content.append(f"modifier {modifier.fullName} {modifier.getValue():.6f}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(mhm_content) + "\n")

    print(f"MHM 설정 파일이 생성되었습니다: {output_path}")

    # MakeHuman 모델 폴더로 자동 복사
    if os.path.isdir(MAKEHUMAN_MODELS_DIR):
        dest = os.path.join(MAKEHUMAN_MODELS_DIR, os.path.basename(output_path))
        if os.path.abspath(dest) != os.path.abspath(output_path):
            shutil.copy2(output_path, dest)
            print(f"MakeHuman 모델 폴더로 복사되었습니다: {dest}")
    else:
        print(f"경고: MakeHuman 모델 폴더를 찾을 수 없습니다: {MAKEHUMAN_MODELS_DIR}")


# --- 실행 진입점 --------------------------------------------------------------

def _load_headless_human(mh_src):
    """MakeHuman 소스(makehuman/ 폴더)로 화면 없이 Human 객체를 만든다"""
    mh_src = os.path.abspath(mh_src)
    if not os.path.isfile(os.path.join(mh_src, "makehuman.py")):
        sys.exit(f"MakeHuman 소스 폴더가 아닙니다(makehuman.py 없음): {mh_src}\n"
                 "--mh-src 또는 환경변수 MAKEHUMAN_SRC로 소스의 makehuman/ 폴더를 지정하세요.")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.chdir(mh_src)  # MakeHuman은 data/ 경로를 현재 폴더 기준으로 찾음
    sys.path[:0] = [mh_src] + [os.path.join(mh_src, p) for p in ("lib", "apps", "shared", "apps/gui", "core", "plugins")]

    import logging
    logging.disable(logging.WARNING)  # 컴파일된 npz가 없다는 경고 등 생략
    import makehuman  # noqa: F401  (경로/버전 초기화)
    import files3d, human, humanmodifier, getpath
    from core import G

    class _HeadlessApp:
        """GUI 없이 Human이 호출하는 G.app 메서드만 흉내냄"""
        def progress(self, *args, **kwargs):
            pass

        def getSetting(self, name):
            return {"units": "metric", "realtimeNormalUpdates": False}.get(name)

        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    G.app = _HeadlessApp()
    mesh = files3d.loadMesh(getpath.getSysDataPath("3dobjs/base.obj"), maxFaces=5)
    h = human.Human(mesh)
    humanmodifier.loadModifiers(getpath.getSysDataPath("modifiers/modeling_modifiers.json"), h)
    humanmodifier.loadModifiers(getpath.getSysDataPath("modifiers/measurement_modifiers.json"), h)
    h.applyAllTargets()
    return h


def build_avatar(measurements_path="measurements.json", output_path="my_custom_avatar.mhm",
                 gender="male", age_years=25.0, muscle=0.5, mh_src=MAKEHUMAN_SRC_DIR):
    """measurements_path의 측정값(JSON)으로 아바타를 피팅해 output_path에 .mhm을 생성.

    exportnumberbymediapipe.py를 여러 사진에 대해 실행하면 사진별로
    <이름>.json 파일이 생기는데, measurements_path에 원하는 사진의 JSON을
    지정하는 것만으로 그 인물의 아바타를 만들 수 있습니다.
    """
    measurements_path = os.path.abspath(measurements_path)
    output_path = os.path.abspath(output_path)
    measured = load_measurements(measurements_path)
    h = _load_headless_human(mh_src)
    result = fit_human(h, measured, gender=gender, age_years=age_years, muscle=muscle)
    generate_mhm_file(output_path, h)
    return result


def fit_in_makehuman(measurements_path, output_path=None, gender="male", age_years=25.0, muscle=0.5):
    """MakeHuman 프로그램의 Shell 탭에서 호출: 화면의 아바타를 피팅하고 .mhm으로 저장"""
    from core import G
    import getpath
    h = G.app.selectedHuman
    result = fit_human(h, load_measurements(measurements_path), gender=gender, age_years=age_years, muscle=muscle)
    if output_path is None:
        stem = os.path.splitext(os.path.basename(measurements_path))[0]
        output_path = os.path.join(getpath.getPath("models"), f"{stem}.mhm")
    generate_mhm_file(output_path, h)
    G.app.redraw()
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="측정값 JSON으로부터 MakeHuman 아바타(.mhm)를 피팅해 생성합니다.")
    parser.add_argument("measurements_path", nargs="?", default="measurements.json",
                        help="exportnumberbymediapipe.py가 생성한 측정값 JSON 경로 (기본값: measurements.json)")
    parser.add_argument("--out", default="my_custom_avatar.mhm", help="출력 .mhm 파일 경로")
    parser.add_argument("--gender", choices=sorted(GENDER_VALUES), default="male", help="성별 (기본값: male)")
    parser.add_argument("--age", type=float, default=25.0, help="나이(세), 기본값 25")
    parser.add_argument("--muscle", type=float, default=0.5, help="근육 매크로 0~1, 기본값 0.5(보통)")
    parser.add_argument("--mh-src", default=MAKEHUMAN_SRC_DIR,
                        help="MakeHuman 소스의 makehuman/ 폴더 (환경변수 MAKEHUMAN_SRC로도 지정 가능)")
    args = parser.parse_args()

    build_avatar(args.measurements_path, args.out, gender=args.gender, age_years=args.age,
                 muscle=args.muscle, mh_src=args.mh_src)
