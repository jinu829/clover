import os
import shutil

MAKEHUMAN_MODELS_DIR = r"C:\Users\enjoyer\Documents\makehuman\v1py3"


def generate_mhm_file(output_path, params):
    """
    측정된 MakeHuman 파라미터 딕셔너리를 입력받아 .mhm 파일을 생성하는 함수
    """
    # 기본 MHM 헤더 설정
    mhm_content = [
        "version v1.2.0",   # MakeHuman은 "v" 접두사가 있는 버전만 파싱 가능
        "tags body",
    ]

    # 매개변수 작성 (modifier_name value 형식)
    for key, val in params.items():
        mhm_content.append(f"modifier {key} {val:.4f}")

    # 파일 저장
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(mhm_content))

    print(f"MHM 설정 파일이 생성되었습니다: {output_path}")

    # MakeHuman 모델 폴더로 자동 복사
    if os.path.isdir(MAKEHUMAN_MODELS_DIR):
        dest = os.path.join(MAKEHUMAN_MODELS_DIR, os.path.basename(output_path))
        shutil.copy2(output_path, dest)
        print(f"MakeHuman 모델 폴더로 복사되었습니다: {dest}")
    else:
        print(f"경고: MakeHuman 모델 폴더를 찾을 수 없습니다: {MAKEHUMAN_MODELS_DIR}")


def normalize(value, min_value, max_value):
    """실측 cm 값을 MakeHuman TwoSidedModifier 범위(-1.0~1.0)로 정규화.
    범위 중간값 → 0 (기본 체형), 최솟값 → -1, 최댓값 → 1."""
    mid = (min_value + max_value) / 2
    half = (max_value - min_value) / 2
    return max(-1.0, min(1.0, (value - mid) / half))


def load_measurements(export_path="measurements.json"):
    """exportnumberbymediapipe.py가 저장한 측정값 JSON을 읽어옴"""
    import json
    with open(export_path, "r", encoding="utf-8") as f:
        return json.load(f)


# 둘레(cm)별 통계적 최소/최대 범위 (정규화 기준)
CIRC_RANGE_CM = {
    "chest": (70.0, 120.0),
    "waist": (60.0, 110.0),
    "hip": (75.0, 120.0),
    "thigh": (40.0, 70.0),
}


def build_avatar(measurements_path="measurements.json", output_path="my_custom_avatar.mhm"):
    """measurements_path의 측정값(JSON)을 읽어 output_path에 .mhm 아바타를 생성.

    exportnumberbymediapipe.py를 여러 사진에 대해 실행하면 사진별로
    <이름>.json 파일이 생기는데, measurements_path에 원하는 사진의 JSON을
    지정하는 것만으로 그 인물의 아바타를 만들 수 있습니다 (A.json -> B.json
    으로 바꾸면 B 사진 속 인물 기준 아바타가 생성됨).
    """
    measured = load_measurements(measurements_path)

    custom_body_params = {
        # 1. 기본 글로벌 파라미터 (성별, 나이, 근육, 체중)
        "macrodetails/Gender": 1.0,         # 남성
        "macrodetails/Age": 0.5,            # 성인
        "macrodetails-universal/Muscle": 0.6,
        "macrodetails-universal/Weight": 0.4,

        # 2. 세부 측정 치수 파라미터 (Modifiers)
        # MakeHuman 실제 modifier 이름: measure/<target>-decr|incr
        # 값 범위: -1.0(최소) ~ 0.0(기본 체형) ~ 1.0(최대)
        "measure/measure-bust-circ-decr|incr": normalize(
            measured["chest_circumference_cm"], *CIRC_RANGE_CM["chest"]
        ),
        "measure/measure-waist-circ-decr|incr": normalize(
            measured["waist_circumference_cm"], *CIRC_RANGE_CM["waist"]
        ),
        "measure/measure-hips-circ-decr|incr": normalize(
            measured["hip_circumference_cm"], *CIRC_RANGE_CM["hip"]
        ),
        "measure/measure-thigh-circ-decr|incr": normalize(
            measured["thigh_circumference_cm"], *CIRC_RANGE_CM["thigh"]
        ),
    }

    generate_mhm_file(output_path, custom_body_params)
    return custom_body_params


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="측정값 JSON으로부터 MakeHuman 아바타(.mhm)를 생성합니다.")
    parser.add_argument("measurements_path", nargs="?", default="measurements.json",
                         help="exportnumberbymediapipe.py가 생성한 측정값 JSON 경로 (기본값: measurements.json)")
    parser.add_argument("--out", default="my_custom_avatar.mhm", help="출력 .mhm 파일 경로")
    args = parser.parse_args()

    build_avatar(args.measurements_path, args.out)