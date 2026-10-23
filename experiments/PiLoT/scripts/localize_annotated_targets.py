#!/usr/bin/env python3
"""Project annotated Feicuiwan pixels using a completed run's cached depth.

Uses CPU only; does not rerun localization or load the Gaussian model.
The coordinates are predictions on the 3DGS map, not target ground truth.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pyproj
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.annotate_target_points import frame_key, load_points, read_query_image, resolve_path
from pixloc.utils.gs3d.pose_convert import dof6_to_matrix


def load_poses(path):
    poses = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 7 or fields[0] in poses:
            raise ValueError(f"{path}:{number}: expected unique name lon lat alt roll pitch yaw")
        pose = np.asarray(fields[1:], dtype=np.float64)
        if not np.isfinite(pose).all():
            raise ValueError(f"{path}:{number}: invalid pose")
        poses[fields[0]] = pose
    return poses


def render_intrinsics(config, width, height):
    camera = config["default_confs"]["cam_query"]
    native = config["render_config"].get("render_camera")
    if native:
        native_w, native_h, _, _, fx, fy = native
    else:
        native_w, native_h = camera["width"], camera["height"]
        fx = fy = camera["params"][0]
    scale = width / float(native_w)
    if abs(height - native_h * scale) > 1:
        raise ValueError("Cached depth aspect ratio disagrees with the render camera")
    # The stock Gaussian rasterizer uses ndc2Pix=((ndc+1)*size-1)/2.
    # GS3DRenderer uses a symmetric projection, ignoring configured cx/cy.
    return fx * scale, fy * scale, (width - 1) / 2, (height - 1) / 2


def bilinear_sample(array, x, y):
    height, width = array.shape[:2]
    if not (0 <= x <= width - 1 and 0 <= y <= height - 1):
        raise ValueError("Target ray falls outside the cached render")
    x0, y0 = int(np.floor(x)), int(np.floor(y))
    x1, y1 = min(x0 + 1, width - 1), min(y0 + 1, height - 1)
    tx, ty = x - x0, y - y0
    samples = [array[y0, x0], array[y0, x1], array[y1, x0], array[y1, x1]]
    weights = [(1-tx)*(1-ty), tx*(1-ty), (1-tx)*ty, tx*ty]
    active = [np.asarray(value, dtype=np.float64) for value, weight in zip(samples, weights) if weight > 0]
    if any(not np.isfinite(value).all() for value in active):
        raise ValueError("Nonfinite depth or render values at the target")
    return sum(float(weight) * value for value, weight in zip(samples, weights) if weight > 0), active


def backproject_to_geography(point, depth_z, pose, camera, offset):
    """Use the exact local camera frame used to render the Gaussian map."""
    fx, fy, cx, cy = camera["params"]
    ray = np.array([(point[0] - cx) / fx, (point[1] - cy) / fy, 1.0], dtype=np.float64)
    lon, lat, alt, roll, pitch, yaw = pose
    c2w = dof6_to_matrix(lat, lon, alt, roll, pitch, yaw, cgcs_offset=offset)
    local = c2w[:3, :3] @ (ray * depth_z) + c2w[:3, 3]
    projected = local + offset
    transformer = pyproj.Transformer.from_crs("EPSG:4547", "EPSG:4326", always_xy=True)
    target_lon, target_lat = transformer.transform(projected[0], projected[1])
    return float(target_lon), float(target_lat), float(projected[2])


def process_point(name, point, pose, config, render_dir, image_dir):
    camera = config["default_confs"]["cam_query"]
    image = read_query_image(image_dir / name, camera)
    if not (0 <= point[0] < image.shape[1] and 0 <= point[1] < image.shape[0]):
        raise ValueError("Annotation is outside the undistorted query image")
    depth = np.load(render_dir / Path(name).with_suffix(".npy"), allow_pickle=False)
    if depth.ndim != 2:
        raise ValueError("Cached depth must have shape (height, width)")
    rendered = cv2.imread(str(render_dir / name), cv2.IMREAD_COLOR)
    if rendered is None or rendered.shape[:2] != depth.shape:
        raise ValueError("Missing render image or color/depth size mismatch")
    height, width = depth.shape
    fx, fy, cx, cy = camera["params"]
    rfx, rfy, rcx, rcy = render_intrinsics(config, width, height)
    rx = rfx * (point[0] - cx) / fx + rcx
    ry = rfy * (point[1] - cy) / fy + rcy
    sampled, neighbors = bilinear_sample(depth, rx, ry)
    z = float(sampled)
    if any(float(value) <= 0 for value in neighbors) or not (1 <= z <= 5000):
        raise ValueError("Invalid or missing map depth; choose a covered ground/building point")
    color, _ = bilinear_sample(rendered, rx, ry)
    if float(np.mean(color)) <= 10:
        raise ValueError("The point hits a near-black map/background region; choose another point")
    offset = np.asarray(config["render_config"]["gs3d"].get("cgcs_offset", [401448, 3131258, 0]), dtype=np.float64)
    lon, lat, height_m = backproject_to_geography(point, z, pose, camera, offset)
    if not np.isfinite([lon, lat, height_m]).all():
        raise ValueError("Invalid geographic projection result")
    result = dict(frame=name, query_x=point[0], query_y=point[1], render_x=rx,
                  render_y=ry, depth_z_m=z, longitude=lon, latitude=lat,
                  model_height_m=height_m, status="ok", reason="")
    return result, image, rendered


def save_visualization(path, result, image, rendered):
    panel_width = 768
    panel_height = round(panel_width * image.shape[0] / image.shape[1])
    top, bottom = 34, 92
    canvas = np.zeros((panel_height + top + bottom, panel_width * 2, 3), dtype=np.uint8)
    canvas[top:top+panel_height, :panel_width] = cv2.resize(image, (panel_width, panel_height))
    canvas[top:top+panel_height, panel_width:] = cv2.resize(rendered, (panel_width, panel_height))
    points = [
        (round(result["query_x"] / image.shape[1] * panel_width),
         top + round(result["query_y"] / image.shape[0] * panel_height)),
        (panel_width + round(result["render_x"] / rendered.shape[1] * panel_width),
         top + round(result["render_y"] / rendered.shape[0] * panel_height)),
    ]
    for point in points:
        cv2.drawMarker(canvas, point, (0, 0, 255), cv2.MARKER_CROSS, 22, 2)
    messages = [
        (f'{result["frame"]} | undistorted query', 12, 24),
        ("3DGS render | mapped depth pixel", panel_width + 12, 24),
        (f'Predicted lon={result["longitude"]:.8f}, lat={result["latitude"]:.8f}, model height={result["model_height_m"]:.2f} m', 12, top + panel_height + 28),
        (f'Cached camera-Z depth estimate: {result["depth_z_m"]:.2f} m | No independent target ground truth', 12, top + panel_height + 57),
        ("Map-surface projection demo; depth is alpha weighted.", 12, top + panel_height + 81),
    ]
    for text, x, y in messages:
        cv2.putText(canvas, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, .56,
                    (235, 235, 235), 1, cv2.LINE_AA)
    if not cv2.imwrite(str(path), canvas):
        raise OSError(f"Could not save image: {path}")


def create_output(path):
    if path is not None:
        output = resolve_path(path)
        output.mkdir(parents=True, exist_ok=False)
        return output
    output = ROOT / "outputs" / "target_demo"
    number = 2
    while output.exists():
        output = ROOT / "outputs" / f"target_demo_{number}"
        number += 1
    output.mkdir(parents=True)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/demos/feicuiwan.yaml")
    parser.add_argument("--run", default="outputs/3dgs_test", help="Matched cached render directory and same-name .txt poses")
    parser.add_argument("--annotations", help="TXT from annotate_target_points.py")
    parser.add_argument("--output", help="New output directory; default creates outputs/target_demo[_N]")
    parser.add_argument("--check", action="store_true", help="Validate and compute without writing results")
    args = parser.parse_args()
    config_path = resolve_path(args.config)
    with config_path.open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    if config["render_config"].get("type") != "3dgs":
        parser.error("This script currently supports the georeferenced Feicuiwan 3DGS demo")
    dc = config["default_confs"]
    sequence = dc.get("sequence_name") or dc["dataset_name"]
    dataset = resolve_path(dc["dataset_path"])
    image_dir = resolve_path(dc["query_path"]) if dc.get("query_path") else dataset / "images" / sequence
    labels = resolve_path(args.annotations) if args.annotations else dataset / "bbox" / sequence / (sequence + "_xy.txt")
    points = load_points(labels)
    if not points:
        parser.error("No target annotations. First run scripts/annotate_target_points.py and click landmarks")
    render_dir = resolve_path(args.run)
    pose_path = render_dir.parent / (render_dir.name + ".txt")
    poses = load_poses(pose_path)
    output = None if args.check else create_output(args.output)
    rows = []
    for name in sorted(points, key=lambda item: frame_key(Path(item))):
        try:
            if Path(name).name != name or name not in poses:
                raise ValueError("No matching estimated pose for this image")
            result, image, rendered = process_point(name, points[name], poses[name], config, render_dir, image_dir)
            if output is not None:
                save_visualization(output / name, result, image, rendered)
            print(f'{name}: lon={result["longitude"]:.8f} lat={result["latitude"]:.8f} model_height={result["model_height_m"]:.2f}m depth_z={result["depth_z_m"]:.2f}m')
        except (OSError, ValueError) as error:
            result = dict(frame=name, query_x=points[name][0], query_y=points[name][1],
                          status="skipped", reason=str(error))
            print(f"SKIP {name}: {error}", file=sys.stderr)
        rows.append(result)
    valid = [row for row in rows if row["status"] == "ok"]
    if output is not None:
        fields = ["frame", "query_x", "query_y", "render_x", "render_y", "depth_z_m",
                  "longitude", "latitude", "model_height_m", "status", "reason"]
        with (output / "targets.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        (output / "targets_wgs84.txt").write_text(
            "".join(f'{row["frame"]} {row["longitude"]:.10f} {row["latitude"]:.10f} {row["model_height_m"]:.4f}\n' for row in valid), encoding="utf-8")
        manifest = dict(config=str(config_path), annotations=str(labels), poses=str(pose_path),
                        render_dir=str(render_dir), valid=len(valid), total=len(rows),
                        query_camera=dc["cam_query"], gs3d_config=config["render_config"]["gs3d"],
                        poses_used={row["frame"]: poses[row["frame"]].tolist() for row in valid},
                        coordinate_note="Longitude/latitude via EPSG:4547 -> 4326; height retains the model vertical datum.",
                        depth_note="Cached camera-Z depth is alpha weighted and may be biased in low-coverage regions.",
                        evaluation_note="Predictions only; no independent target ground truth or accuracy evaluation.", results=rows)
        (output / "summary.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"结果目录：{output}")
    print(f"有效目标：{len(valid)}/{len(rows)}；坐标为地图投影预测，未计算目标定位误差。")
    return 0 if valid else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, cv2.error) as error:
        raise SystemExit(f"目标投影无法继续：{error}")
