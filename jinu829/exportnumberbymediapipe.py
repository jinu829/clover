import cv2
import mediapipe as mp
import numpy as np
import math
import json
import os

# Pose Landmarker 모델 파일 경로 (models/ 폴더에 다운로드된 .task 파일)
# https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "pose_landmarker_lite.task")

# 신체 부위별 정면 너비 -> 단면 타원 둘레 환산 시 사용하는 단반경(b) 비율.
# 실제 사람 몸은 정면에서 보이는 너비(a)보다 옆에서 본 두께(b)가 얇으므로,
# 부위별 통계적인 두께/너비 비율을 곱해 근사합니다.
DEPTH_RATIO = {
    "chest": 0.75,
    "waist": 0.80,
    "hip": 0.90,
    "thigh": 0.85,
}

# NOTE: Python 3.14 + mediapipe 조합에서는 세그멘테이션 마스크를
# result.segmentation_masks[0].numpy_view() 로 변환할 때 네이티브 크래시
# (STATUS_STACK_BUFFER_OVERRUN)가 발생했습니다 (mediapipe 네이티브 바인딩과
# 그 Python/numpy 조합 간의 ABI 비호환 문제로 추정). Python 3.13 가상환경
# (jinu829/.venv313)에서는 이 크래시가 재현되지 않아, 아래에서 세그멘테이션
# 마스크 기반 실루엣 스캔으로 폭을 측정합니다.
#
# 아래 상수들은 마스크에서 실루엣을 찾지 못했을 때(예: 랜드마크가 마스크
# 경계 밖으로 벗어난 경우)를 위한 폴백 근사에만 사용됩니다.
WAIST_INTERP_RATIO = 0.55        # 어깨~골반 사이 허리 위치 비율

# mediapipe의 LEFT_HIP/RIGHT_HIP 랜드마크는 골반 관절 중심에 찍혀
# 실제 골반 실루엣(엉덩이) 폭보다 좁게 측정됩니다. 정면 사진으로 재검증한
# 결과 보정 없이는 Hip 둘레가 Waist보다 작게 나오는 등 비현실적인 값이
# 나와, 아래 경험적 보정 계수로 실루엣 폭에 가깝게 근사합니다.
HIP_WIDTH_CORRECTION = 1.35      # 골반 랜드마크 간 거리 -> 실제 골반 실루엣 폭 보정 배수
THIGH_TO_HIP_WIDTH_RATIO = 0.58  # 한쪽 허벅지 폭 ≈ 보정된 골반 폭의 약 58% (통계적 근사치)

SEGMENTATION_THRESHOLD = 0.5     # 마스크 픽셀을 "몸"으로 간주하는 확률 임계값
SILHOUETTE_SEARCH_RADIUS = 14    # 랜드마크 지점이 마스크 밖일 때 실루엣을 찾기 위해 좌우로 탐색하는 최대 픽셀

# 랜드마크 근사 폭(expected_half_width) 대비 마스크 실루엣이 한쪽으로 이 배수
# 이상 벌어지는 것은 허용하지 않음. 팔을 몸통에서 떼어 옆으로 늘어뜨리거나
# 소품(의자 등)에 얹은 포즈에서는 그 높이의 마스크 행이 팔/손까지 몸통과
# 하나의 실루엣으로 이어져 폭이 실제보다 크게 잡히는데, 이 한도로 그런
# 오염된 확장을 차단하고 진짜 실루엣 경계(더 안쪽)만 반영한다.
SILHOUETTE_TOLERANCE = 1.4


def _silhouette_width_at(mask, cx, cy, expected_half_width):
    """세그멘테이션 마스크에서 (cx, cy) 지점을 포함하는 실루엣 구간의 좌/우
    경계와 폭(px)을 반환. 각 방향으로는 배경 픽셀을 만나거나 중심(cx)에서
    expected_half_width * SILHOUETTE_TOLERANCE 만큼 벌어질 때까지만 확장한다
    (팔 등이 그 높이의 실루엣에 붙어 폭을 부풀리는 것을 방지).
    (cx, cy)가 실루엣 밖이면 근처 픽셀에서 다시 탐색하고, 그래도 찾지
    못하면 None을 반환한다(호출부에서 폴백 근사 사용).
    """
    h, w = mask.shape
    center_x = min(max(int(round(cx)), 0), w - 1)
    y = min(max(int(round(cy)), 0), h - 1)
    x0 = center_x
    row = mask[y] > SEGMENTATION_THRESHOLD

    if not row[x0]:
        for dx in range(1, SILHOUETTE_SEARCH_RADIUS + 1):
            if x0 - dx >= 0 and row[x0 - dx]:
                x0 -= dx
                break
            if x0 + dx < w and row[x0 + dx]:
                x0 += dx
                break
        else:
            return None

    max_reach = expected_half_width * SILHOUETTE_TOLERANCE

    left = x0
    while left > 0 and row[left - 1] and (center_x - (left - 1)) <= max_reach:
        left -= 1
    right = x0
    while right < w - 1 and row[right + 1] and ((right + 1) - center_x) <= max_reach:
        right += 1
    return left, right, right - left


def _ellipse_circumference_cm(width_px, scale, depth_ratio):
    """정면에서 측정한 폭(px)을 타원 단면 둘레(cm)로 환산 (라마누잔 근사식)"""
    a = (width_px * scale) / 2  # 장반경 (정면 너비의 절반)
    b = a * depth_ratio         # 단반경 (측면 두께 근사)
    return math.pi * (3 * (a + b) - math.sqrt((3 * a + b) * (a + 3 * b)))


def calculate_body_measurements(image_path, real_height_cm=175.0, export_path="measurements.json",
                                 show_window=True, save_visualization_path=None):
    # 1. MediaPipe Tasks API - Pose Landmarker 초기화
    BaseOptions = mp.tasks.BaseOptions
    PoseLandmarker = mp.tasks.vision.PoseLandmarker
    PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode
    PoseLandmark = mp.tasks.vision.PoseLandmark

    image = cv2.imread(image_path)
    if image is None:
        print("이미지를 불러올 수 없습니다.")
        return
    h, w, _ = image.shape

    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=VisionRunningMode.IMAGE,
        output_segmentation_masks=True,
    )

    with PoseLandmarker.create_from_options(options) as landmarker:
        mp_image = mp.Image.create_from_file(image_path)
        result = landmarker.detect(mp_image)

    if not result.pose_landmarks:
        print("사람을 인식하지 못했습니다.")
        return

    landmarks = result.pose_landmarks[0]

    mask = None
    if result.segmentation_masks:
        mask = result.segmentation_masks[0].numpy_view()
        if mask.ndim == 3:  # (h, w, 1) -> (h, w)
            mask = mask[:, :, 0]

    def px(landmark_id):
        lm = landmarks[landmark_id]
        return lm.x * w, lm.y * h

    # 2. 픽셀-cm 환산 비율 (Scale) 계산
    # 정수리 추정(코에서 눈 높이만큼 위로 연장)부터 발뒤꿈치까지의 픽셀 높이 계산
    _, nose_y = px(PoseLandmark.NOSE.value)
    _, eye_y = px(PoseLandmark.LEFT_EYE.value)
    top_head_y = nose_y - (nose_y - eye_y) * 2  # 대략적인 정수리 위치
    _, left_heel_y = px(PoseLandmark.LEFT_HEEL.value)
    _, right_heel_y = px(PoseLandmark.RIGHT_HEEL.value)
    heel_y = max(left_heel_y, right_heel_y)

    pixel_height = heel_y - top_head_y
    scale = real_height_cm / pixel_height  # 픽셀당 cm

    # 3. 어깨/골반 좌우 랜드마크로 각 부위의 폭(px)과 중심 좌표 추정
    l_sh_x, l_sh_y = px(PoseLandmark.LEFT_SHOULDER.value)
    r_sh_x, r_sh_y = px(PoseLandmark.RIGHT_SHOULDER.value)
    shoulder_width_px = abs(l_sh_x - r_sh_x)
    shoulder_cx, shoulder_cy = (l_sh_x + r_sh_x) / 2, (l_sh_y + r_sh_y) / 2

    l_hip_x, l_hip_y = px(PoseLandmark.LEFT_HIP.value)
    r_hip_x, r_hip_y = px(PoseLandmark.RIGHT_HIP.value)
    hip_width_px = abs(l_hip_x - r_hip_x)  # 랜드마크 간 원거리 (허리 보간에는 이 값을 그대로 사용)
    hip_width_corrected_px = hip_width_px * HIP_WIDTH_CORRECTION  # 실루엣 폭 근사치 (Hip/Thigh 계산에 사용)
    hip_cx, hip_cy = (l_hip_x + r_hip_x) / 2, (l_hip_y + r_hip_y) / 2

    waist_width_px = shoulder_width_px + (hip_width_px - shoulder_width_px) * WAIST_INTERP_RATIO
    waist_cx = shoulder_cx + (hip_cx - shoulder_cx) * WAIST_INTERP_RATIO
    waist_cy = shoulder_cy + (hip_cy - shoulder_cy) * WAIST_INTERP_RATIO

    # 오른쪽 허벅지 (골반 ~ 무릎 사이 상위 20% 지점), 폭은 보정된 골반 폭 비례로 근사
    r_knee_x, r_knee_y = px(PoseLandmark.RIGHT_KNEE.value)
    thigh_cx = r_hip_x + (r_knee_x - r_hip_x) * 0.2
    thigh_cy = r_hip_y + (r_knee_y - r_hip_y) * 0.2
    thigh_width_px = hip_width_corrected_px * THIGH_TO_HIP_WIDTH_RATIO

    regions = {
        "chest": (shoulder_cx, shoulder_cy, shoulder_width_px),
        "waist": (waist_cx, waist_cy, waist_width_px),
        "hip": (hip_cx, hip_cy, hip_width_corrected_px),
        "thigh": (thigh_cx, thigh_cy, thigh_width_px),
    }

    # 4. 부위별 둘레 계산 (마스크 실루엣 스캔 우선, 실패 시 랜드마크 근사로 폴백)
    circumferences = {}
    measured_lines = {}
    for name, (cx, cy, fallback_width_px) in regions.items():
        silhouette = (
            _silhouette_width_at(mask, cx, cy, fallback_width_px / 2)
            if mask is not None else None
        )
        if silhouette is not None:
            left_x, right_x, width_px = silhouette
        else:
            width_px = fallback_width_px
            left_x, right_x = int(cx - width_px / 2), int(cx + width_px / 2)

        circumferences[name] = _ellipse_circumference_cm(width_px, scale, DEPTH_RATIO[name])
        measured_lines[name] = (int(cy), left_x, right_x)

    # --- 시각화 (이미지에 랜드마크, 측정선, 텍스트 그리기) ---
    draw_img = image.copy()

    for lm in landmarks:
        cx_px, cy_px = int(lm.x * w), int(lm.y * h)
        cv2.circle(draw_img, (cx_px, cy_px), 3, (0, 200, 0), -1)

    line_colors = {
        "chest": (255, 0, 0),    # 파란색
        "waist": (0, 255, 255),  # 노란색
        "hip": (0, 255, 0),      # 초록색
        "thigh": (255, 0, 255),  # 보라색
    }

    cv2.putText(draw_img, f"Scale: {scale:.3f} cm/px", (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    text_y = 60
    for name, (line_y, left_x, right_x) in measured_lines.items():
        cv2.line(draw_img, (left_x, line_y), (right_x, line_y), line_colors[name], 3)
        text = f"{name.capitalize()} Circ: {circumferences[name]:.1f} cm"
        cv2.putText(draw_img, text, (20, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, line_colors[name], 2)
        text_y += 30

    if show_window:
        cv2.imshow("Body Measurement", draw_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    if save_visualization_path:
        cv2.imwrite(save_visualization_path, draw_img)
        print(f"시각화 이미지를 저장했습니다: {save_visualization_path}")

    # 5. 측정값 JSON으로 export (createHuman.py에서 읽어서 사용)
    measurements = {
        "real_height_cm": real_height_cm,
        "scale_cm_per_px": scale,
        "chest_circumference_cm": circumferences.get("chest"),
        "waist_circumference_cm": circumferences.get("waist"),
        "hip_circumference_cm": circumferences.get("hip"),
        "thigh_circumference_cm": circumferences.get("thigh"),
    }
    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(measurements, f, ensure_ascii=False, indent=2)
    print(f"측정값을 저장했습니다: {export_path}")

    return measurements


IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def process_images(input_path, real_height_cm=175.0, out_dir="measurements", save_visualizations=True):
    """
    input_path가 폴더면 그 안의 모든 이미지 파일을, 단일 파일이면 그 파일 하나를
    측정합니다. 사진별로 <파일명>.json (+ <파일명>_viz.jpg)을 out_dir에 저장합니다.
    """
    if os.path.isdir(input_path):
        image_paths = sorted(
            os.path.join(input_path, name)
            for name in os.listdir(input_path)
            if name.lower().endswith(IMAGE_EXTENSIONS)
        )
    else:
        image_paths = [input_path]

    os.makedirs(out_dir, exist_ok=True)

    results = {}
    for image_path in image_paths:
        stem = os.path.splitext(os.path.basename(image_path))[0]
        export_path = os.path.join(out_dir, f"{stem}.json")
        viz_path = os.path.join(out_dir, f"{stem}_viz.jpg") if save_visualizations else None

        print(f"[{stem}] 측정 중: {image_path}")
        measurements = calculate_body_measurements(
            image_path,
            real_height_cm=real_height_cm,
            export_path=export_path,
            show_window=False,
            save_visualization_path=viz_path,
        )
        results[image_path] = measurements

    succeeded = sum(1 for v in results.values() if v)
    print(f"완료: {succeeded}/{len(results)}장 측정 성공 (결과: {out_dir}/)")
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="사진(들)에서 신체 치수를 측정해 JSON으로 저장합니다.")
    parser.add_argument("input_path", help="이미지 파일 경로 또는 이미지가 들어있는 폴더 경로")
    parser.add_argument("--height", type=float, default=175.0, help="실제 키(cm), 기본값 175.0")
    parser.add_argument("--out-dir", default="measurements", help="측정 결과(JSON/시각화) 저장 폴더")
    parser.add_argument("--no-viz", action="store_true", help="시각화 이미지 저장 생략")
    args = parser.parse_args()

    process_images(
        args.input_path,
        real_height_cm=args.height,
        out_dir=args.out_dir,
        save_visualizations=not args.no_viz,
    )

# 실행 방법(터미널에 해당 코드 순차적으로 입력)
#py -3.13 -m venv .venv313
#.venv313\Scripts\activate
#pip install opencv-python mediapipe numpy
#python exportnumberbymediapipe.py testdata/sample_person.jpg

#여러 사진을 한꺼번에 돌리고 싶다면
#python exportnumberbymediapipe.py testdata폴더경로 --out-dir measurements : 모든 사진에 대해 측정 결과 measurement생성
"""Get-ChildItem measurements\*.json | ForEach-Object { #모든 measurement내의 사진에 대해서 createHuman파일을 돌림.
    python createHuman.py $_.FullName --out "$($_.BaseName).mhm"
}"""