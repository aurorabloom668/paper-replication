# PiLoT 公开 Demo 复现

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
git checkout a27028fd22be1de5d6f13c8a1b35ea63dbbfb86a

# 修改为你克隆的复现合集的实际绝对路径。
bundle_dir=/absolute/path/paper-reproductions/experiments/PiLoT
cp -a "$bundle_dir/scripts/." scripts/
cp -a "$bundle_dir/configs/." configs/
cp -a "$bundle_dir/docs/." docs/
cp "$bundle_dir/PiLoT_record.md" PiLoT_record.md
```

复制后，按 `PiLoT_record.md` 中的环境、数据和实验步骤继续。
本次记录的上游提交为 `a27028fd22be1de5d6f13c8a1b35ea63dbbfb86a`；辅助文件包含本次复现的本地修复。
CUDA 源码恢复应在这个保留了官方 Git 历史的源码目录执行，不能在轻量合集执行。
CityGaussian 需要按指南单独克隆并应用 Python 3.8 兼容修复。

若存在 `examples/target_points_3dgs_test.txt`，可使用它复核相同点选输入：

```bash
python scripts/localize_annotated_targets.py \
  --annotations "$bundle_dir/examples/target_points_3dgs_test.txt" \
  --run outputs/3dgs_test
```

上面的命令要求已完成对应的可视化运行，并保留同一次运行的估计位姿和渲染深度。
可选的 `examples/target_demo.csv` 为本次人工点选目标的预测坐标，不是真值。
数据、权重和完整输出不随本仓库分发。可选的 `docs/media/` 只包含白名单中的
精选结果，不要解除整个 `data_demo/` 或 `outputs/` 的忽略规则。

## 精选可视化结果

每组保留前三帧渲染图（帧号 0、1、2）和一次完整可视化视频，方便浏览复现效果。
图片为模型渲染结果，不是另行上传的完整查询图像集；视频为便于浏览器播放的
H.264 发布副本，保留原分辨率和 10 FPS，原 `outputs/` 中的运行结果未更改。
视频可点击链接下载后播放，GitHub 文档页面不一定直接内嵌播放。

| 场景 / 设置 | 第 0 帧 | 第 1 帧 | 第 2 帧 | 可视化视频 |
| --- | --- | --- | --- | --- |
| Feicuiwan · 512 分辨率 | [第 0 帧](docs/media/feicuiwan_512/0_0.png) | [第 1 帧](docs/media/feicuiwan_512/1_0.png) | [第 2 帧](docs/media/feicuiwan_512/2_0.png) | [MP4 视频](docs/media/feicuiwan_512/visualization.mp4) |
| Feicuiwan · 1024 分辨率展示 | [第 0 帧](docs/media/feicuiwan_1024/0_0.png) | [第 1 帧](docs/media/feicuiwan_1024/1_0.png) | [第 2 帧](docs/media/feicuiwan_1024/2_0.png) | [MP4 视频](docs/media/feicuiwan_1024/visualization.mp4) |
| SMBU · seq2 | [第 0 帧](docs/media/smbu_seq2/0_0.png) | [第 1 帧](docs/media/smbu_seq2/1_0.png) | [第 2 帧](docs/media/smbu_seq2/2_0.png) | [MP4 视频](docs/media/smbu_seq2/visualization.mp4) |

## 归属与许可

PiLoT 方法及原始实现属于论文作者。本目录保留上游的 [MIT LICENSE](LICENSE)
和版权声明；这份许可证不表示本合集作者是 PiLoT 原作者，也不替代数据集、
预训练模型或其他第三方组件各自的使用条款。论文引用信息见完整指南。
