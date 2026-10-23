#!/usr/bin/env python3
"""Apply the annotation-only Python 3.8 compatibility changes used for SMBU.

Target CityGaussian commit: 3c1e93b38712334877ff3cfdf724e4ec7ee3e65b.
The script is idempotent and does not change rendering/optimization algorithms.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "dataset.py",
    "internal/cameras/cameras.py",
    "internal/configs/dataset.py",
    "internal/dataparsers/colmap_block_dataparser.py",
    "internal/dataparsers/matrix_city_dataparser.py",
    "internal/dataset.py",
    "internal/renderers/partition_lod_renderer.py",
    "internal/utils/network_factory.py",
    "internal/viewer/client.py",
    "internal/viewer/ui/render_panel.py",
    "internal/viewer/viewer.py",
    "render.py",
    "utils/auto_hyper_parameter.py",
    "utils/common.py",
    "utils/finetune_pruned_partitions_v2.py",
    "utils/matrix_city_depth_to_point_cloud.py",
    "utils/merge_partitions_v2.py",
    "utils/train_colmap_partitions_v2.py",
    "utils/train_matrix_city_partitions_v2.py",
    "utils/train_partitions.py",
    "utils/trained_partition_utils.py",
)


def postpone_annotations(source: str, filename: str) -> str:
    tree = ast.parse(source, filename=filename)
    futures = [node for node in tree.body
               if isinstance(node, ast.ImportFrom) and node.module == "__future__"]
    if any(name.name == "annotations" for node in futures for name in node.names):
        return source
    lines = source.splitlines(keepends=True)
    position = 0
    while position < len(lines) and (not lines[position].strip() or lines[position].lstrip().startswith("#")):
        position += 1
    if tree.body and isinstance(tree.body[0], ast.Expr):
        value = tree.body[0].value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            position = tree.body[0].end_lineno
    for node in futures:
        position = max(position, node.end_lineno)
    if position and not lines[position - 1].endswith("\n"):
        lines[position - 1] += "\n"
    lines.insert(position, "from __future__ import annotations\n")
    result = "".join(lines)
    compile(result, filename, "exec")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "third_party/CityGaussian")
    parser.add_argument("--check", action="store_true", help="Report pending edits without changing files")
    args = parser.parse_args()
    changes = []
    # Validate all inputs before applying any change.
    for relative in FILES:
        path = args.root / relative
        source = path.read_text(encoding="utf-8")
        updated = postpone_annotations(source, str(path))
        if source != updated:
            changes.append((path, updated))
    for path, updated in changes:
        if not args.check:
            path.write_text(updated, encoding="utf-8")
        print(f"{'NEEDS FIX' if args.check else 'UPDATED'}: {path}")
    print(f"Checked {len(FILES)} files; {'pending' if args.check else 'updated'}: {len(changes)}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, SyntaxError) as error:
        raise SystemExit(f"CityGaussian compatibility setup failed: {error}")
