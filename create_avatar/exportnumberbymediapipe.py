import cv2
import mediapipe as mp
import numpy as np
import math
import json
import os

# Pose Landmarker 모델 파일 경로 (models/ 폴더에 다운로드된 .task 파일)
# https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "pose_landmarker_lite.task")

# 신체 부위별 "둘레 / 정면 폭" 비율. 정면 사진에서는 폭만 보이므로 이 비율을 곱해 둘레를 구한다.
# 타원 단면 가정은 실제 몸통(타원보다 각진 단면)보다 둘레를 9~13% 작게 내서, 대신
# MakeHuman 메시 72개(성별 2 x 체중 6 x 근육 3 x 키 2)에서 Measure 탭 ruler 둘레를
# 같은 높이의 정면 폭으로 나눈 평균값을 쓴다. createHuman.py의 피팅도 같은 ruler 기준이라
# 두 단계의 cm 정의가 일치한다. (체형 간 표준편차 2~3%, 남녀 차이 3% 이내)
CIRC_PER_WIDTH = {
    "chest": 3.14,
    "waist": 2.80,
    "hip": 2.76,
    "thigh": 3.39,
}

# 측정 높이는 MakeHuman Measure 탭 ruler 높이에 맞춘다 (렌더링한 MakeHuman 몸 8개에서
# mediapipe 랜드마크 대비 위치를 재 평균낸 값). 피팅이 같은 ruler로 재므로 같은 곳을 재야 한다.
WAIST_INTERP_RATIO = 0.69        # 어깨~골반 랜드마크 사이 허리 위치 비율 (편차 ±0.02)
HIP_BELOW_HIP_LANDMARK = 0.05    # 엉덩이 둘레 높이: 골반 랜드마크에서 (골반~무릎) x 이 비율 아래 (편차 ±0.03)
THIGH_INTERP_RATIO = 0.35        # 골반~무릎 사이 허벅지 위치 비율 (남 약 0.29, 여 약 0.42)

# 가슴 둘레(MakeHuman bust-circ)는 유두 높이에서 잰다. mediapipe 어깨 랜드마크는
# 어깨 관절 높이라 그대로 쓰면 삼각근까지 포함한 어깨 폭이 잡히므로, 어깨~골반
# 랜드마크 사이에서 이 비율만큼 내려간 곳을 가슴 높이로 쓴다 (편차 ±0.02).
CHEST_INTERP_RATIO = 0.28
CHEST_TO_SHOULDER_WIDTH_RATIO = 0.90  # 가슴 폭 ≈ 어깨 랜드마크 간 거리의 약 90% (마스크 실패 시 폴백)
ARM_HALF_WIDTH_RATIO = 0.15           # 위팔 반지름 ≈ 어깨 랜드마크 간 거리의 약 15%

# 마스크가 없거나 이상할 때 쓰는 정수리 근사: 눈에서 (어깨-눈 거리) x 이 비율만큼 위
HEAD_TOP_FROM_EYE_RATIO = 0.55
# 마스크로 잰 키가 랜드마크 근사와 이 비율 이상 차이 나면 마스크를 믿지 않음
MASK_HEIGHT_SANITY = 0.15

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
# 엉덩이는 골반 랜드마크 폭 대비 실제 폭의 개인차(특히 여성)가 커서 한도를 넓힌다.
# 팔/손은 arm_limits로 따로 잘라내므로 한도를 넓혀도 팔이 섞이지 않는다.
SILHOUETTE_TOLERANCE_BY_PART = {"hip": 1.8}


def _silhouette_width_at(mask, cx, cy, expected_half_width, max_left=None, max_right=None,
                         tolerance=SILHOUETTE_TOLERANCE):
    """세그멘테이션 마스크에서 (cx, cy) 지점을 포함하는 실루엣 구간의 좌/우
    경계와 폭(px)을 반환. 각 방향으로는 배경 픽셀을 만나거나 중심(cx)에서
    expected_half_width * SILHOUETTE_TOLERANCE 만큼 벌어질 때까지만 확장한다
    (팔 등이 그 높이의 실루엣에 붙어 폭을 부풀리는 것을 방지).
    max_left/max_right를 주면 그 방향의 확장 한도를 더 좁힌다(팔 영역 제외용).
    (cx, cy)가 실루엣 밖이면 근처 픽셀에서 다시 탐색하고, 그래도 찾지
    못하면 None을 반환한다(호출부에서 폴백 근사 사용).
    """
    h, w = mask.shape #마스크 배열의 높이와 너비 가져오기
    center_x = min(max(int(round(cx)), 0), w - 1) #부동소수점 형식인 cx를 정수 형식으로 반올림. 이때 올림을 하면서 너비보다 커지면 안되기에 w-1 보다 작을 경우에만 선택
    y = min(max(int(round(cy)), 0), h - 1)
    x0 = center_x #가로 탐색을 시작할 중심 지점.
    row = mask[y] > SEGMENTATION_THRESHOLD #가로로 넓힐 해당 높이의 가로 행 데이터를 담기. 이때 사람이라고 확실한 데이터만 담음.

    #관절 중심점이 마스크 경계 바로 바깥에 찍히더라도 반경 내에서 가장 가까운 신체 영역을 자동으로 찾아내어, 세그멘테이션 마스크 스캔 실패로 인한 치수 측정 누락 오류를 방지하고 파이프라인의 안정성을 높이는 역할을 함.
    if not row[x0]:
        for dx in range(1, SILHOUETTE_SEARCH_RADIUS + 1): #dx를 1픽셀부터 허용한 최댓값까지 천천히 올림.
            if x0 - dx >= 0 and row[x0 - dx]: #만약 dx만큼 줄인 게 0보다 크고(이미지 내) dx만큼 줄인 게 실루엣 마스크 세그멘테이션 마스크 안이 있다 -> 중심점으로 적합.
                x0 -= dx
                break
            if x0 + dx < w and row[x0 + dx]:
                x0 += dx
                break
        else: #두 경우 모두 안될 경우 적당한 지점이 없기에 None반환.
            return None

        
    #탐색을 허용할 수 있는 최대 범위(옷 같은 걸로 인하여 세그멘테이션 마스크가 좌우로 비정상적으로 길어지는 걸 방지한다.)
    max_reach = expected_half_width * tolerance
    reach_left = max_reach if max_left is None else min(max_reach, max_left)
    reach_right = max_reach if max_right is None else min(max_reach, max_right)

    #기준점 x0를 중심으로 좌우 방향으로 폭을 넓혀가며 세그멘테이션 마스크 끝 지점을 파악하고, 좌우 좌표 위치와 폭을 반환하는 코드
    left = x0
    while left > 0 and row[left - 1] and (center_x - (left - 1)) <= reach_left:
        left -= 1
    right = x0
    while right < w - 1 and row[right + 1] and ((right + 1) - center_x) <= reach_right:
        right += 1
    return left, right, right - left    


def _circumference_cm(width_px, scale, part):
    """정면에서 측정한 폭(px)을 둘레(cm)로 환산 (CIRC_PER_WIDTH 설명 참고)"""
    return width_px * scale * CIRC_PER_WIDTH[part]


def calculate_body_measurements(image_path, real_height_cm=175.0, export_path="measurements.json",
                                 show_window=True, save_visualization_path=None):
    # 1. MediaPipe Tasks API - Pose Landmarker 초기화
    BaseOptions = mp.tasks.BaseOptions #AI 모델 파일(.task)의 경로를 지정하거나 실행 디바이스(CPU/GPU) 등의 기본 설정을 정의하는 클래스
    PoseLandmarker = mp.tasks.vision.PoseLandmarker #각 관절점(Landmark)를 찾아주는 AI엔진
    PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions #모델 경로(BaseOptions), 실행 모드(VisionRunningMode), 세그멘테이션 마스크 사용 여부 등을 결정함.
    VisionRunningMode = mp.tasks.vision.RunningMode #이미지, 동영상 등 어떤 파일을 기준으로 작업할지 모드를 정함.
    PoseLandmark = mp.tasks.vision.PoseLandmark #추출된 Landmark

    image = cv2.imread(image_path) #이미지 읽어오기
    if image is None:
        print("이미지를 불러올 수 없습니다.")
        return
    h, w, _ = image.shape

    # mediapipe는 너비/높이가 4의 배수가 아닌 이미지에서 세그멘테이션 마스크를
    # 생성할 때 내부 stride 정렬이 깨져 네이티브 크래시
    # (Check failed: 1 == ChannelSize())가 발생합니다. 오른쪽/아래쪽 가장자리를
    # 복제해 4의 배수로 패딩하여 이를 피합니다.
    pad_bottom, pad_right = (-h) % 4, (-w) % 4
    if pad_bottom or pad_right:
        image = cv2.copyMakeBorder(image, 0, pad_bottom, 0, pad_right, cv2.BORDER_REPLICATE)
        h, w, _ = image.shape

    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=VisionRunningMode.IMAGE,
        output_segmentation_masks=True,
    )

    with PoseLandmarker.create_from_options(options) as landmarker:
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        result = landmarker.detect(mp_image)

    if not result.pose_landmarks:
        print("사람을 인식하지 못했습니다.")
        return

    landmarks = result.pose_landmarks[0]

    mask = None
    if result.segmentation_masks:
        mask = result.segmentation_masks[0].numpy_view() #[0]번째 감지 대상(사람)의 마스크 데이터를 Numpy배열 형태로 변환
        if mask.ndim == 3:  # (h, w, 1) -> (h, w) #만약 추출된 데이터가 3차원이면 z값을 0으로 만들어서 평탄화
            mask = mask[:, :, 0]

    def px(landmark_id): #mediaPipe에서 반환한 Landmark의 좌표는 0.0~1.0사이의 값으로 추출됨. 따라서 이 값을 실제 사진의 비율에 맞게 수정해주어야 함.
        lm = landmarks[landmark_id]
        return lm.x * w, lm.y * h

    # 2. 픽셀-cm 환산 비율 (Scale) 계산
    # 랜드마크 근사: 정수리는 눈에서 (어깨-눈 거리)의 일정 비율 위, 바닥은 발뒤꿈치/발끝 중 낮은 쪽
    eye_y = (px(PoseLandmark.LEFT_EYE.value)[1] + px(PoseLandmark.RIGHT_EYE.value)[1]) / 2
    sh_y = (px(PoseLandmark.LEFT_SHOULDER.value)[1] + px(PoseLandmark.RIGHT_SHOULDER.value)[1]) / 2
    top_head_y = eye_y - (sh_y - eye_y) * HEAD_TOP_FROM_EYE_RATIO
    floor_y = max(px(lm_id.value)[1] for lm_id in (PoseLandmark.LEFT_HEEL, PoseLandmark.RIGHT_HEEL,
                                                    PoseLandmark.LEFT_FOOT_INDEX, PoseLandmark.RIGHT_FOOT_INDEX))
    landmark_pixel_height = floor_y - top_head_y

    # 마스크 우선: 몸 실루엣의 맨 위(머리카락 포함)~맨 아래(발바닥) 행. 랜드마크 근사보다 훨씬 정확하다.
    # (신발/높은 머리 모양은 그만큼 키에 더해지므로 맨발·평소 머리로 찍은 사진이 가장 정확)
    pixel_height = landmark_pixel_height
    scale_source = "landmarks"
    if mask is not None:
        body_rows = np.where((mask > SEGMENTATION_THRESHOLD).sum(axis=1) >= 3)[0]
        if body_rows.size:
            mask_pixel_height = body_rows[-1] - body_rows[0] + 1
            if abs(mask_pixel_height / landmark_pixel_height - 1) <= MASK_HEIGHT_SANITY:
                pixel_height = mask_pixel_height
                scale_source = "mask"
    if scale_source == "landmarks":
        print("경고: 마스크로 키를 잴 수 없어 랜드마크 근사를 사용합니다 (스케일 오차가 커질 수 있음)")
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

    # 가슴: 어깨 관절이 아니라 유두 높이 (CHEST_INTERP_RATIO 설명 참고)
    chest_cx = shoulder_cx + (hip_cx - shoulder_cx) * CHEST_INTERP_RATIO
    chest_cy = shoulder_cy + (hip_cy - shoulder_cy) * CHEST_INTERP_RATIO
    chest_width_px = shoulder_width_px * CHEST_TO_SHOULDER_WIDTH_RATIO

    # 팔이 몸통 옆에 붙어 있으면 그 높이의 마스크가 팔/손까지 이어지므로,
    # 어깨-팔꿈치-손목 선 위의 팔 중심에서 팔 반지름만큼 안쪽까지만 몸통으로 인정한다.
    arm_half_px = shoulder_width_px * ARM_HALF_WIDTH_RATIO
    arms = {}
    for side, (sh, el, wr) in {
        "left": (PoseLandmark.LEFT_SHOULDER, PoseLandmark.LEFT_ELBOW, PoseLandmark.LEFT_WRIST),
        "right": (PoseLandmark.RIGHT_SHOULDER, PoseLandmark.RIGHT_ELBOW, PoseLandmark.RIGHT_WRIST),
    }.items():
        arms[side] = [px(sh.value), px(el.value), px(wr.value)]

    def arm_x_at(points, y):
        """팔 꺾은선(어깨-팔꿈치-손목)이 높이 y를 지나는 x. 손목보다 아래면 손목 x(손)"""
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            if min(y0, y1) <= y <= max(y0, y1) and y1 != y0:
                return x0 + (x1 - x0) * (y - y0) / (y1 - y0)
        return points[-1][0] if y > points[-1][1] else points[0][0]

    def arm_limits(cx, cy, min_reach):
        """(cx, cy)에서 좌/우로 몸통으로 인정할 최대 거리(px)"""
        reach = {side: max(abs(arm_x_at(points, cy) - cx) - arm_half_px, min_reach)
                 for side, points in arms.items()}
        # 이미지 좌표에서 왼쪽(x 작은 쪽)이 어느 팔인지 판정
        if arms["left"][0][0] < arms["right"][0][0]:
            return {"max_left": reach["left"], "max_right": reach["right"]}
        return {"max_left": reach["right"], "max_right": reach["left"]}

    # 오른쪽 허벅지 (골반 ~ 무릎 사이 THIGH_INTERP_RATIO 지점), 폭은 보정된 골반 폭 비례로 근사
    r_knee_x, r_knee_y = px(PoseLandmark.RIGHT_KNEE.value)
    thigh_cx = r_hip_x + (r_knee_x - r_hip_x) * THIGH_INTERP_RATIO
    thigh_cy = r_hip_y + (r_knee_y - r_hip_y) * THIGH_INTERP_RATIO

    # 엉덩이: 골반 랜드마크보다 약간 아래(엉덩이가 가장 튀어나온 높이)
    l_knee_y = px(PoseLandmark.LEFT_KNEE.value)[1]
    hip_measure_cy = hip_cy + ((l_knee_y + r_knee_y) / 2 - hip_cy) * HIP_BELOW_HIP_LANDMARK
    thigh_width_px = hip_width_corrected_px * THIGH_TO_HIP_WIDTH_RATIO

    regions = {
        "chest": (chest_cx, chest_cy, chest_width_px),
        "waist": (waist_cx, waist_cy, waist_width_px),
        "hip": (hip_cx, hip_measure_cy, hip_width_corrected_px),
        "thigh": (thigh_cx, thigh_cy, thigh_width_px),
    }

    # 4. 부위별 둘레 계산 (마스크 실루엣 스캔 우선, 실패 시 랜드마크 근사로 폴백)
    circumferences = {}
    measured_lines = {}
    for name, (cx, cy, fallback_width_px) in regions.items():
        # 팔 영역 제외 (허벅지는 팔과 겹치지 않으므로 제외)
        limits = arm_limits(cx, cy, fallback_width_px * 0.25) if name != "thigh" else {}
        silhouette = (
            _silhouette_width_at(mask, cx, cy, fallback_width_px / 2,
                                 tolerance=SILHOUETTE_TOLERANCE_BY_PART.get(name, SILHOUETTE_TOLERANCE), **limits)
            if mask is not None else None
        )
        if silhouette is not None:
            left_x, right_x, width_px = silhouette
        else:
            width_px = fallback_width_px
            left_x, right_x = int(cx - width_px / 2), int(cx + width_px / 2)

        circumferences[name] = _circumference_cm(width_px, scale, name) #둘레 길이 저장
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

    cv2.putText(draw_img, f"Scale: {scale:.3f} cm/px ({scale_source})", (20, 30),
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
        "scale_source": scale_source,
        "chest_circumference_cm": circumferences.get("chest"),
        "waist_circumference_cm": circumferences.get("waist"),
        "hip_circumference_cm": circumferences.get("hip"),
        "thigh_circumference_cm": circumferences.get("thigh"),
    }
    # numpy 숫자형은 json으로 저장할 수 없으므로 파이썬 float로 변환
    measurements = {k: (float(v) if isinstance(v, (int, float, np.floating)) else v) for k, v in measurements.items()}
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