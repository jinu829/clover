"""명령어 없이 실행했을 때, 파일 선택 창으로 사진을 고르게 해 줍니다."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

IMAGE_TYPES = [("이미지 파일", "*.jpg *.jpeg *.png *.bmp *.webp"), ("모든 파일", "*.*")]


def ask_images() -> Tuple[Optional[Path], List[Path]]:
    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)  # 선택 창이 다른 창 뒤에 숨지 않도록

    messagebox.showinfo("FaceBuilder", "1단계: 정면 사진 1장을 선택하세요.", parent=root)
    front = filedialog.askopenfilename(title="정면 사진 선택", filetypes=IMAGE_TYPES, parent=root)
    if not front:
        root.destroy()
        return None, []

    messagebox.showinfo(
        "FaceBuilder",
        "2단계: 측면 사진을 선택하세요.\n(Ctrl 을 누른 채 여러 장 선택 가능, 없으면 '취소')",
        parent=root,
    )
    sides = filedialog.askopenfilenames(title="측면 사진 선택 (여러 장 가능)", filetypes=IMAGE_TYPES, parent=root)
    root.destroy()
    return Path(front), [Path(s) for s in sides]
