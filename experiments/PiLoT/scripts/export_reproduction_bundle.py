#!/usr/bin/env python3
"""Export a small, independent collection of reproduction notes and helpers.

Only the explicit allowlist below is exported, including optional, curated
visualization samples. The original repository, datasets, models, complete
outputs, binaries and Git history are never copied. This tool does not
initialize Git, stage changes, make commits or contact GitHub.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
from typing import List


ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_MEDIA_BYTES = 25 * 1024 * 1024
EXPERIMENT = Path("experiments/PiLoT")
REQUIRED = (
    "PiLoT_record.md",
    "LICENSE",
    "docs/github_publish.md",
    "docs/coordinate_systems.md",
    "docs/custom_data.md",
    "scripts/annotate_target_points.py",
    "scripts/localize_annotated_targets.py",
    "scripts/download_data_demo.sh",
    "scripts/_common.sh",
    "scripts/verify_pilot_2frames.py",
    "scripts/verify_pilot_nframes.py",
    "scripts/prepare_citygaussian_py38.py",
    "scripts/prepare_visual_media.py",
    "scripts/export_reproduction_bundle.py",
    "configs/demos/feicuiwan.yaml",
    "configs/demos/smbu_seq2.yaml",
)
MEDIA_FILENAMES = ("0_0.png", "1_0.png", "2_0.png", "visualization.mp4")
# Read prepared publication copies only; never recurse through outputs/.
# prepare_visual_media.py preserves the original runs and creates H.264 MP4s.
MEDIA_GROUPS = (
    (("docs/media/feicuiwan_512",), "feicuiwan_512", "Feicuiwan · 512 分辨率"),
    (("docs/media/feicuiwan_1024",), "feicuiwan_1024", "Feicuiwan · 1024 分辨率展示"),
    (("docs/media/smbu_seq2",), "smbu_seq2", "SMBU · seq2"),
)
MEDIA_DESTINATIONS = frozenset(
    EXPERIMENT / "docs/media" / name / filename
    for _, name, _ in MEDIA_GROUPS
    for filename in MEDIA_FILENAMES
)

COLLECTION_IGNORE = """# Download large data and model files separately.
data_demo/
/data/
/datasets/
experiments/*/data/
experiments/*/datasets/
outputs/
/models/
/checkpoints/
/weights/
experiments/*/models/
experiments/*/checkpoints/
experiments/*/weights/
third_party/
workdirs/
*.ckpt
*.pt
*.pth
*.pth.tar
*.safetensors
*.onnx
*.npy
*.npz
*.ply
*.bin

# Local environments, caches and compiled products.
.venv/
venv/
env/
__pycache__/
*.py[cod]
.cache/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.ipynb_checkpoints/
build/
dist/
*.egg-info/
*.egg
*.so
*.dylib
*.dll
*.o
*.obj
.vscode/
.idea/
.DS_Store
Thumbs.db

# Ignore arbitrary videos; only the three curated result videos are public.
*.mp4
!/experiments/PiLoT/docs/media/feicuiwan_512/visualization.mp4
!/experiments/PiLoT/docs/media/feicuiwan_1024/visualization.mp4
!/experiments/PiLoT/docs/media/smbu_seq2/visualization.mp4
*.avi
*.mov
*.mkv
*.webm
*.zip
*.tar
*.tar.gz
*.tgz
*.7z
*.log
*.log.*
events.out.tfevents*
wandb/
mlruns/

# Credentials. Keep actual tokens outside the repository.
.env
.env.*
!.env.example
*.pem
*.key
id_rsa
id_ed25519
.aws/
.ssh/
credentials.json
token.json
"""


@dataclass(frozen=True)
class ExportFile:
    path: Path
    content: bytes
    mode: int = 0o644


def read_source(
    root: Path,
    relative: str,
    destination: Path,
    max_file_bytes: int = MAX_FILE_BYTES,
) -> ExportFile:
    """Read one allowlisted regular file, enforcing a bounded snapshot."""
    source = root / relative
    if source.is_symlink() or not source.is_file():
        raise ValueError("Required source is not a regular file: " + relative)
    try:
        source.resolve().relative_to(root.resolve())
    except ValueError:
        raise ValueError("Source points outside the PiLoT directory: " + relative)
    with source.open("rb") as stream:
        content = stream.read(max_file_bytes + 1)
    if len(content) > max_file_bytes:
        raise ValueError("File exceeds the {} MiB export limit: {}".format(
            max_file_bytes // (1024 * 1024), relative,
        ))
    mode = 0o755 if source.stat().st_mode & 0o111 else 0o644
    return ExportFile(destination, content, mode)


def source_commit(root: Path) -> str:
    # The exported collection also includes this helper. It must not mistake
    # that collection's Git HEAD for the original PiLoT source revision.
    source_error = (
        "Run the exporter from an independent PiLoT source checkout with "
        "main.py, pixloc/ and its own Git repository, not from the lightweight "
        "reproduction collection."
    )
    if not (root / "main.py").is_file() or not (root / "pixloc").is_dir():
        raise ValueError(source_error)
    try:
        toplevel = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=10,
        )
        if Path(toplevel.stdout.strip()).resolve() != root.resolve():
            raise ValueError(source_error)
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError(source_error + " Cannot read source Git metadata: " + str(error))
    commit = result.stdout.strip()
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        raise ValueError("Unexpected source Git commit")
    return commit


def text_file(path: str, content: str) -> ExportFile:
    return ExportFile(Path(path), content.encode("utf-8"))


def build_plan(root: Path, commit: str) -> List[ExportFile]:
    """Read all inputs before creating an export directory."""
    files = [read_source(root, name, EXPERIMENT / name) for name in REQUIRED]
    optional = (
        (
            ("data_demo/query/bbox/3dgs_test/3dgs_test_xy.txt",),
            "examples/target_points_3dgs_test.txt",
        ),
        (
            ("outputs/target_demo_2/targets.csv", "outputs/target_demo/targets.csv"),
            "examples/target_demo.csv",
        ),
    )
    for candidates, destination in optional:
        for name in candidates:
            if (root / name).exists():
                files.append(read_source(root, name, EXPERIMENT / destination))
                break

    media_rows = []
    for candidates, name, label in MEDIA_GROUPS:
        for source_directory in candidates:
            directory = root / source_directory
            if not directory.exists() and not directory.is_symlink():
                continue
            if directory.is_symlink() or not directory.is_dir():
                raise ValueError("Visualization group is not a regular directory: " + source_directory)
            sources = [root / source_directory / filename for filename in MEDIA_FILENAMES]
            present = [source.exists() or source.is_symlink() for source in sources]
            if not all(present):
                missing = [filename for filename, found in zip(MEDIA_FILENAMES, present) if not found]
                raise ValueError("Incomplete visualization group {}: missing {}".format(
                    source_directory, ", ".join(missing),
                ))
            for filename in MEDIA_FILENAMES:
                files.append(read_source(
                    root, source_directory + "/" + filename,
                    EXPERIMENT / "docs/media" / name / filename,
                    max_file_bytes=MAX_MEDIA_BYTES,
                ))
            media_rows.append("| " + label + " | " + " | ".join(
                "[第 {} 帧](docs/media/{}/{})".format(index, name, filename)
                for index, filename in enumerate(MEDIA_FILENAMES[:3])
            ) + " | [MP4 视频](docs/media/" + name + "/visualization.mp4) |")
            break
    if media_rows:
        media_section = """## 精选可视化结果

每组保留前三帧渲染图（帧号 0、1、2）和一次完整可视化视频，方便浏览复现效果。
图片为模型渲染结果，不是另行上传的完整查询图像集；视频为便于浏览器播放的
H.264 发布副本，保留原分辨率和 10 FPS，原 `outputs/` 中的运行结果未更改。
视频可点击链接下载后播放，GitHub 文档页面不一定直接内嵌播放。

| 场景 / 设置 | 第 0 帧 | 第 1 帧 | 第 2 帧 | 可视化视频 |
| --- | --- | --- | --- | --- |
""" + "\n".join(media_rows) + "\n\n"
    else:
        media_section = ""

    files.append(text_file(".gitignore", COLLECTION_IGNORE))
    files.append(text_file("README.md", """# Paper Reproductions / 论文实验复现记录

这里收集个人对他人论文及公开代码的实验复现、环境配置和操作说明。
原方法、预训练模型和数据集归原作者所有；每个实验分别注明来源和复现范围。

| 实验 | 内容 | 指南 |
| --- | --- | --- |
| PiLoT | Feicuiwan、SMBU 公开 Demo 与少量帧的目标地理定位功能展示 | [实验入口](experiments/PiLoT/README.md) |

后续可以在 `experiments/OtherPaper/` 增加其他论文的复现记录，并更新上表。
每个实验应包含论文与官方代码链接、适用版本、操作步骤、结果和局限说明。

本仓库保存文档、辅助脚本、配置、少量文本结果及可选的精选渲染图和视频；数据、模型权重、
编译产物及完整运行输出按各实验指南单独获取。发布前请阅读
[GitHub 上传指南](experiments/PiLoT/docs/github_publish.md)。
"""))
    files.append(text_file(str(EXPERIMENT / "README.md"), """# PiLoT 公开 Demo 复现

这是对他人论文及其公开实现的个人实验复现资料，不是论文官方仓库。

- 论文：[PiLoT: Neural Pixel-to-3D Registration for UAV-based Ego and Target Geo-localization](https://arxiv.org/abs/2603.20778)
- 官方代码：[nudt-sawlab/PiLoT](https://github.com/nudt-sawlab/PiLoT)
- [完整复现指南及结果](PiLoT_record.md)
- [发布说明](docs/github_publish.md)

已完成 Feicuiwan 和 SMBU 两个官方公开 Demo 的自定位推理、误差评估及
可视化，并完成 Feicuiwan 少量人工点选帧的目标坐标投影演示。
这些结果不等同于原论文主实验表的完整复现；目标演示没有独立真值，
不能用有效坐标输出比例代替定位准确率。

## 如何使用本资料

这个目录只含补充文档和辅助文件，不包含 `main.py`、`pixloc/`、数据或权重，
不能直接在本目录运行 PiLoT。先独立克隆官方源码，再将本目录中的辅助文件
复制到该源码目录，按完整指南配置环境和下载数据。例如：

```bash
git clone https://github.com/nudt-sawlab/PiLoT.git ~/course/PiLoT
cd ~/course/PiLoT
git checkout COMMIT_PLACEHOLDER

# 修改为你克隆的复现合集的实际绝对路径。
bundle_dir=/absolute/path/paper-reproductions/experiments/PiLoT
cp -a "$bundle_dir/scripts/." scripts/
cp -a "$bundle_dir/configs/." configs/
cp -a "$bundle_dir/docs/." docs/
cp "$bundle_dir/PiLoT_record.md" PiLoT_record.md
```

复制后，按 `PiLoT_record.md` 中的环境、数据和实验步骤继续。
本次记录的上游提交为 `COMMIT_PLACEHOLDER`；辅助文件包含本次复现的本地修复。
CUDA 源码恢复应在这个保留了官方 Git 历史的源码目录执行，不能在轻量合集执行。
CityGaussian 需要按指南单独克隆并应用 Python 3.8 兼容修复。

若存在 `examples/target_points_3dgs_test.txt`，可使用它复核相同点选输入：

```bash
python scripts/localize_annotated_targets.py \\
  --annotations "$bundle_dir/examples/target_points_3dgs_test.txt" \\
  --run outputs/3dgs_test
```

上面的命令要求已完成对应的可视化运行，并保留同一次运行的估计位姿和渲染深度。
可选的 `examples/target_demo.csv` 为本次人工点选目标的预测坐标，不是真值。
数据、权重和完整输出不随本仓库分发。可选的 `docs/media/` 只包含白名单中的
精选结果，不要解除整个 `data_demo/` 或 `outputs/` 的忽略规则。

MEDIA_SECTION_PLACEHOLDER
## 归属与许可

PiLoT 方法及原始实现属于论文作者。本目录保留上游的 [MIT LICENSE](LICENSE)
和版权声明；这份许可证不表示本合集作者是 PiLoT 原作者，也不替代数据集、
预训练模型或其他第三方组件各自的使用条款。论文引用信息见完整指南。
""".replace("COMMIT_PLACEHOLDER", commit).replace("MEDIA_SECTION_PLACEHOLDER\n", media_section)))

    files.sort(key=lambda item: item.path.as_posix())
    manifest_lines = [
        "# Export manifest", "",
        "Upstream repository: https://github.com/nudt-sawlab/PiLoT",
        "Upstream base commit: `" + commit + "`", "",
        "Includes allowlisted local reproduction changes; the base commit alone does not include those changes.",
        "No datasets, model weights, binaries, complete output directories or Git history were exported.",
        "Optional curated media are limited to three render samples and one video per allowlisted run.", "",
        "| Exported relative path | Bytes |", "| --- | ---: |",
    ]
    manifest_lines.extend("| `" + item.path.as_posix() + "` | " + str(len(item.content)) + " |" for item in files)
    total = sum(len(item.content) for item in files)
    manifest_lines.extend([
        "", "Payload: " + str(len(files)) + " files, " + str(total) + " bytes.",
        "`EXPORT_MANIFEST.md` is generated metadata and is excluded from the payload total.",
    ])
    files.append(text_file("EXPORT_MANIFEST.md", "\n".join(manifest_lines) + "\n"))
    paths = [item.path for item in files]
    if len(paths) != len(set(paths)):
        raise ValueError("Duplicate export destination")
    for item in files:
        if item.path.is_absolute() or ".." in item.path.parts:
            raise ValueError("Invalid export destination: " + str(item.path))
        limit = MAX_MEDIA_BYTES if item.path in MEDIA_DESTINATIONS else MAX_FILE_BYTES
        if len(item.content) > limit:
            raise ValueError("Exported file exceeds its {} MiB limit: {}".format(
                limit // (1024 * 1024), item.path,
            ))
    return sorted(files, key=lambda item: item.path.as_posix())


def write_plan(destination: Path, files: List[ExportFile]) -> None:
    """Create a fresh directory, never replace an existing destination."""
    if destination.exists() or destination.is_symlink():
        raise ValueError("Destination already exists; choose a new directory: " + str(destination))
    destination.mkdir(parents=True, exist_ok=False)
    for item in files:
        target = destination / item.path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(item.content)
        target.chmod(item.mode)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination", type=Path, default=ROOT.parent / "paper-reproductions",
        help="New collection directory (default: a sibling paper-reproductions directory)",
    )
    parser.add_argument("--check", action="store_true", help="Print the complete plan without writing files")
    args = parser.parse_args()
    destination = args.destination.expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        parser.error("Destination already exists; choose a new directory: " + str(destination))
    try:
        commit = source_commit(ROOT)
        files = build_plan(ROOT, commit)
        print("Upstream base commit: " + commit)
        print("Destination: " + str(destination))
        for item in files:
            print("{:>8} B  {}".format(len(item.content), item.path.as_posix()))
        print("Total: {} files, {} bytes".format(len(files), sum(len(item.content) for item in files)))
        if args.check:
            print("CHECK OK: no files written.")
        else:
            write_plan(destination, files)
            print("Export complete. Review the files before initializing or publishing a Git repository.")
    except (OSError, ValueError) as error:
        print("Export failed: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
