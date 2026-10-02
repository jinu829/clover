"""FaceBuilder 실행 파일.

사용법
    python main.py                                 
    python main.py --front 정면.jpg --side 왼쪽.jpg 오른쪽.jpg
    python main.py --front 정면.jpg --engine keentools
"""
from __future__ import annotations

import argparse
import os
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

# MediaPipe 가 출력하는 기술적인 경고 메시지를 줄입니다.
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

from facebuilder.engines import ENGINE_NAMES, FaceBuilderError, get_engine
from facebuilder.exporter import export_all


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="정면/측면 사진으로 3D 얼굴을 만듭니다.")
    parser.add_argument("--front", type=Path, help="정면 사진 경로 (생략하면 선택 창이 뜹니다)")
    parser.add_argument("--side", type=Path, nargs="*", default=[], help="측면 사진 경로들 (여러 개 가능)")
    parser.add_argument("--engine", choices=ENGINE_NAMES, default="mediapipe", help="사용할 3D 엔진")
    parser.add_argument("--out", type=Path, default=Path("output"), help="결과를 저장할 폴더")
    parser.add_argument("--no-open", action="store_true", help="끝난 뒤 뷰어를 자동으로 열지 않음")
    return parser.parse_args()


def run(args: argparse.Namespace) -> int:
    front, sides = args.front, list(args.side)
    if front is None:
        from facebuilder.picker import ask_images
        front, sides = ask_images()
        if front is None:
            print("정면 사진을 선택하지 않아 종료합니다.")
            return 1

    for path in [front, *sides]:
        if not path.is_file():
            raise FaceBuilderError(f"파일을 찾을 수 없습니다: {path}")

    out_dir = args.out / datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"엔진: {args.engine} / 정면 1장, 측면 {len(sides)}장")
    engine = get_engine(args.engine)
    mesh = engine.build(front, sides, out_dir)
    files = export_all(mesh, out_dir)

    print("\n완료! 결과 파일:")
    print(f"  3D 파일 : {files['obj'].resolve()}")
    print(f"  뷰어    : {files['viewer'].resolve()}")
    print(f"  점 {len(mesh.vertices)}개, 삼각형 {len(mesh.faces)}개")

    if not args.no_open:
        webbrowser.open(files["viewer"].resolve().as_uri())
    return 0


def main() -> int:
    try:
        return run(parse_args())
    except FaceBuilderError as e:
        print(f"\n[오류] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
