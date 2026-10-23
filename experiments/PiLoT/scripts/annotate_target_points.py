#!/usr/bin/env python3
"""Click one target point per query image; save undistorted full-size pixels.

Example: python scripts/annotate_target_points.py --frames 0 75 150 225 298
This prepares pixel annotations only; it does not estimate target locations.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, Tuple

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
HEADER = 78
WINDOW = "PiLoT - click a landmark"
Points = Dict[str, Tuple[float, float]]


def resolve_path(value: str) -> Path:
    path = Path(os.path.expandvars(os.path.expanduser(value)))
    return path if path.is_absolute() else ROOT / path


def frame_key(path: Path):
    try:
        return int(path.stem.split("_")[0]), path.name
    except ValueError:
        return float("inf"), path.name


def load_points(path: Path) -> Points:
    points = {}
    if path.exists():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            fields = line.split()
            if len(fields) != 3:
                raise ValueError(f"{path}:{number}: expected 'filename x y'")
            name, x, y = fields
            point = float(x), float(y)
            if not np.isfinite(point).all() or name in points:
                raise ValueError(f"{path}:{number}: invalid or duplicate point")
            points[name] = point
    return points


def save_points(path: Path, points: Points) -> None:
    """Keep other frames and replace the file only after writing succeeds."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=str(path.parent),
            prefix=path.name + ".", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            for name in sorted(points, key=lambda item: frame_key(Path(item))):
                x, y = points[name]
                stream.write(f"{name} {x:.3f} {y:.3f}\n")
        os.replace(str(temporary), str(path))
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def read_query_image(path: Path, camera: dict) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read image: {path}")
    expected = int(camera["height"]), int(camera["width"])
    if image.shape[:2] != expected:
        raise ValueError(f"{path}: image size {image.shape[:2]} != config {expected}")
    distortion = camera.get("distortion")
    if distortion:
        fx, fy, cx, cy = camera["params"]
        matrix = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], dtype=np.float64)
        # Match view.read_image: same intrinsic matrix, no crop or recentering.
        image = cv2.undistort(image, matrix, np.asarray(distortion, dtype=np.float32))
    return image


def make_preview(image: np.ndarray, max_width: int, max_height: int):
    height, width = image.shape[:2]
    scale = min(max_width / width, (max_height - HEADER) / height, 1.0)
    out_width = max(1, round(width * scale))
    out_height = max(1, round(height * scale))
    preview = cv2.resize(image, (out_width, out_height), interpolation=cv2.INTER_AREA)
    return preview, out_width / width, out_height / height


class Annotator:
    def __init__(self, files, camera, output, points, max_width, max_height):
        self.files, self.camera, self.output, self.points = files, camera, output, points
        self.max_width, self.max_height = max_width, max_height
        self.index = 0
        self.status = "Click a ground landmark, such as a road corner."

    def show_frame(self):
        self.image = read_query_image(self.files[self.index], self.camera)
        self.preview, self.scale_x, self.scale_y = make_preview(
            self.image, self.max_width, self.max_height,
        )
        point = self.points.get(self.files[self.index].name)
        self.status = f"Existing point: {point}" if point else "Click a ground landmark, such as a road corner."
        self.redraw()

    def redraw(self):
        height, width = self.preview.shape[:2]
        canvas = np.zeros((height + HEADER, width, 3), dtype=np.uint8)
        canvas[HEADER:] = self.preview
        name = self.files[self.index].name
        messages = [
            f"{name} | image {self.index + 1}/{len(self.files)} | marked: {len(self.points)}",
            "Left click: save | N/Space: next | P: previous | C/Right click: clear | Q/Esc: quit",
            self.status,
        ]
        for row, message in enumerate(messages):
            cv2.putText(canvas, message, (10, 20 + 24 * row),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, (235, 235, 235), 1, cv2.LINE_AA)
        if name in self.points:
            x, y = self.points[name]
            center = round(x * self.scale_x), HEADER + round(y * self.scale_y)
            cv2.drawMarker(canvas, center, (0, 0, 255), cv2.MARKER_CROSS, 20, 2)
            cv2.putText(canvas, f"({x:.1f}, {y:.1f})", (center[0] + 10, center[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2, cv2.LINE_AA)
        cv2.imshow(WINDOW, canvas)

    def update_point(self, point):
        name = self.files[self.index].name
        updated = dict(self.points)
        if point is None:
            updated.pop(name, None)
        else:
            updated[name] = point
        save_points(self.output, updated)
        self.points = updated
        self.status = f"Saved: {name} {point}" if point is not None else f"Cleared: {name}"
        print(self.status, flush=True)

    def mouse(self, event, x, y, flags, parameter):
        height, width = self.preview.shape[:2]
        if not (0 <= x < width and HEADER <= y < HEADER + height):
            return
        try:
            if event == cv2.EVENT_LBUTTONDOWN:
                point = (min(x / self.scale_x, self.image.shape[1] - 1),
                         min((y - HEADER) / self.scale_y, self.image.shape[0] - 1))
                self.update_point(point)
            elif event == cv2.EVENT_RBUTTONDOWN:
                self.update_point(None)
            else:
                return
        except OSError as error:
            self.status = "SAVE FAILED - see terminal"
            print(f"保存失败，原标注保留：{error}", file=sys.stderr)
        self.redraw()

    def run(self):
        try:
            cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)
            self.show_frame()
            cv2.setMouseCallback(WINDOW, self.mouse)
            while True:
                try:
                    if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                        break
                except cv2.error:
                    # Some backends destroy the window before this query.
                    break
                key = cv2.waitKeyEx(50)
                if key in (27, ord("q"), ord("Q")):
                    break
                if key in (ord("n"), ord("N"), 32, 65363, 2555904):
                    self.index = min(self.index + 1, len(self.files) - 1)
                    self.show_frame()
                elif key in (ord("p"), ord("P"), 65361, 2424832):
                    self.index = max(self.index - 1, 0)
                    self.show_frame()
                elif key in (ord("c"), ord("C")):
                    self.update_point(None)
                    self.redraw()
        finally:
            try:
                cv2.destroyAllWindows()
            except cv2.error:
                pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/demos/feicuiwan.yaml")
    parser.add_argument("--frames", nargs="+", type=int, help="Frame IDs from image filenames")
    parser.add_argument("--output", help="Annotation TXT (default: query/bbox/<sequence>/<sequence>_xy.txt)")
    parser.add_argument("--max-width", type=int, default=1280)
    parser.add_argument("--max-height", type=int, default=800)
    parser.add_argument("--check", action="store_true", help="Check inputs without opening GUI or writing files")
    args = parser.parse_args()
    if args.max_width < 320 or args.max_height < HEADER + 100:
        parser.error("Preview size is too small")

    with resolve_path(args.config).open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)["default_confs"]
    sequence = config.get("sequence_name") or config["dataset_name"]
    dataset = resolve_path(config["dataset_path"])
    image_dir = resolve_path(config["query_path"]) if config.get("query_path") else dataset / "images" / sequence
    files = sorted((path for path in image_dir.iterdir() if path.suffix.lower() in (".png", ".jpg", ".jpeg")), key=frame_key)
    if args.frames is not None:
        requested = set(args.frames)
        available = {frame_key(path)[0] for path in files}
        if requested - available:
            parser.error(f"Frame IDs not found: {sorted(requested - available)}")
        files = [path for path in files if frame_key(path)[0] in requested]
    if not files:
        parser.error(f"No query images in {image_dir}")
    output = resolve_path(args.output) if args.output else dataset / "bbox" / sequence / (sequence + "_xy.txt")
    points = load_points(output)
    print(f"本次图片：{len(files)} 张；已有标注：{len(points)} 条")
    print(f"保存路径：{output}")
    print("坐标：去畸变后的原始分辨率像素 (x, y)，每张图片一个点。")
    if args.check:
        for path in files:
            image = read_query_image(path, config["cam_query"])
            if path.name in points:
                x, y = points[path.name]
                if not (0 <= x < image.shape[1] and 0 <= y < image.shape[0]):
                    raise ValueError(f"Point outside image: {path.name}")
        print("CHECK OK：所选图片和已有坐标有效；未写入任何标注。")
        return
    if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        parser.error("没有图形显示环境，请在 Ubuntu 桌面的终端运行此命令。")
    if "NONE" in next((line for line in cv2.getBuildInformation().splitlines() if "GUI:" in line), "NONE"):
        parser.error("当前 OpenCV 未启用 GUI，请使用已有图形版 OpenCV 的 pilot 环境。")
    print("鼠标左键：保存/更换点；N/空格：下一张；P：上一张；C/右键：清除；Q/Esc：退出。")
    Annotator(files, config["cam_query"], output, points, args.max_width, args.max_height).run()
    print(f"已保留标注：{output}" if output.exists() else "尚未点击标注，未创建输出文件。")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, cv2.error) as error:
        raise SystemExit(f"标注工具无法继续：{error}")
