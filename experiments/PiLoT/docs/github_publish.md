# 将复现资料发布到个人 GitHub

## 1. 推荐形式：一个仓库，按论文分目录

建议创建个人仓库 `paper-replication`，将不同论文放入 `experiments/<论文名>/`。本机导出目录仍叫 `paper-reproductions`，本地目录与 GitHub 仓库不必同名。这里所说的“项目”是 GitHub Repository，不是用来管理任务的 GitHub Projects 看板。普通仓库的 README 和 Markdown 就能在线阅读，不需要先配置 GitHub Pages 网站。

```text
paper-reproductions/
├── README.md                       # 各论文复现入口
├── .gitignore
├── EXPORT_MANIFEST.md               # 本次导出文件清单
└── experiments/
    ├── PiLoT/
    │   ├── README.md                 # 来源、范围与操作入口
    │   ├── LICENSE                   # 保留 PiLoT 原作者 MIT 声明
    │   ├── PiLoT_record.md
    │   ├── docs/
    │   │   └── media/               # 三组精选渲染图和可视化视频
    │   │       ├── feicuiwan_512/
    │   │       ├── feicuiwan_1024/
    │   │       └── smbu_seq2/
    │   ├── scripts/                  # 本次使用的辅助工具及修复
    │   ├── configs/demos/
    │   └── examples/                 # 少量点选坐标和预测 CSV（如已生成）
    └── OtherPaper/                   # 日后增加其他论文
```

这是一份“文档 + 辅助脚本 + 精选可视化”的轻量复现合集，不是 PiLoT 完整源码镜像。读者先独立克隆官方源码，再按 [PiLoT_record.md](../PiLoT_record.md) 复制辅助文件、配置环境和下载数据。不要把现有 PiLoT 的 `.git/` 直接放进这个合集：嵌套仓库会使文件管理和后续提交变得混乱，也会带入原仓库历史中的大文件。

若日后希望长期维护 PiLoT 算法源码、提交修改给作者，可以另外 fork 官方仓库，在合集里链接自己的 fork。对当前这种包含多篇论文的复现记录，轻量合集更便于浏览和维护。

## 2. 说明复现来源、范围和许可

每篇论文的入口至少写明：原论文、官方代码、数据来源、源码提交、环境、运行步骤、结果及未完成内容。不要把复现描述成自己提出的方法，也不要把公开 Demo 跑通等同于论文主实验完整复现。

本次 PiLoT 资料已经注明：

- 方法及原始实现来自 Cheng 等人的 PiLoT 论文和官方仓库，本资料不是作者官方教程。
- 已完成 Feicuiwan、SMBU 公开 Demo 的自定位推理与评估，以及 5 帧目标坐标投影展示；不等同于原论文表 2/表 3 的完整复现。
- SMBU 平移误差为归一化模型单位，不能直接当作米；目标演示没有独立真值，`5/5` 有效输出不是准确率。
- 环境排错、标注工具、离线投影工具和结果整理属于本次复现的补充工作。

应保留 PiLoT 的 [原始 MIT LICENSE](../LICENSE) 和版权声明。数据、图像、模型权重、第三方组件可能有各自的使用条款，不能仅凭 PiLoT 代码的 MIT 许可推定它们都允许转载。本次不复制原始数据集和模型，只从既有运行输出中选取下面三组展示媒体；渲染图来自官方 Demo 模型，视频还包含数据集查询画面，公开前仍应核查相应数据和模型的许可，并在展示位置保留来源说明。若许可不允许再分发，应移除对应媒体、保留复现步骤和数据来源链接，不要据此解除整个数据或输出目录的屏蔽规则。

合集根目录暂不替所有论文统一授予许可证；自己的新增文档或工具如需另行授权，可明确指定适用范围，保留各论文代码和数据已有的声明。GitHub 的[开源许可说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)可作参考。

## 3. 生成轻量发布目录

如果已经拿到准备好的轻量发布目录，其中的精选媒体可以直接随文档提交，不必再次准备或导出。下面的命令仅用于从本地运行结果新建资料包；两个工具都会拒绝覆盖已存在的目标。

在当前已经完成复现的 **PiLoT 源码工作目录** 中运行：

```bash
cd ~/course/PiLoT
conda activate pilot
python scripts/prepare_visual_media.py --check
python scripts/prepare_visual_media.py
python scripts/export_reproduction_bundle.py --check
python scripts/export_reproduction_bundle.py
```

两个脚本的 `--check` 均只检查、列出计划，不写文件。媒体准备需要系统中有可用的 `ffmpeg`：先把三组前三帧图片整理到 `docs/media/`，并将原可视化视频转换为便于浏览器播放的 H.264 MP4，启用 faststart；保留原视频分辨率和 10 FPS，不改动 `outputs/` 中的原始结果。再运行导出工具，默认在旁边创建 `~/course/paper-reproductions/`，不会移动、删除或修改原始数据，不执行 Git 初始化、提交或上传。目标目录已存在时会拒绝覆盖，可以用 `--destination /absolute/path/to/new-directory` 指定另一个新目录。

H.264 也是 [GitHub 推荐的视频兼容格式](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files)。这里通过 Git 提交视频文件，不是向评论区上传附件；两种方式的大小限制不同，不应混淆。

导出采用文件白名单：文档、脚本和配置等普通文件限制为单文件不超过 5 MiB，精选媒体限制为单文件不超过 25 MiB。包含完整复现文档、必要辅助脚本、两个 Demo 的配置、原始 LICENSE，以及已存在时的少量标注 TXT 和目标预测 CSV。`EXPORT_MANIFEST.md` 记录上游基线提交、导出路径和大小。辅助文件含有本地复现修复，不能只看基线提交就认为这些修复已在上游提供。

精选媒体保存在 `experiments/PiLoT/docs/media/`，每组包含前三帧渲染图 `0_0.png`、`1_0.png`、`2_0.png` 和一条 `visualization.mp4`：

| 目录 | 运行配置 |
| --- | --- |
| `feicuiwan_512/` | Feicuiwan 默认 512 分辨率可视化运行 |
| `feicuiwan_1024/` | Feicuiwan 1024 分辨率展示运行 |
| `smbu_seq2/` | SMBU 可视化运行 |

媒体文件受单文件 25 MiB 上限检查，可随这份合集用普通 Git 发布，无需配置 Git LFS。它们是本次公开 Demo 复现的展示输出，不是原论文主实验的新结果；1024 分辨率的运行也不能据此声称精度更高。发布视频是编码格式转换后的展示副本，实验数值仍引用原始运行日志，不重新进行定位推理。

Markdown 中用缩略图和相对 MP4 链接展示，例如以下写法适用于 `docs/` 内的文档：

```markdown
[![Feicuiwan 512 首帧渲染图](media/feicuiwan_512/0_0.png)](media/feicuiwan_512/visualization.mp4)

[查看或下载可视化视频](media/feicuiwan_512/visualization.mp4)
```

若写在 `PiLoT_record.md` 中，路径前加 `docs/`。点击链接后可通过 GitHub 文件页查看或下载视频；相对 MP4 链接不保证在 README 中自动显示为内嵌播放器。图片和视频的说明仍需区分真实查询图与模型渲染图，定位精度以文档中的数值评估为准，不能只凭视频观感判断。

以下内容不会导出：

- `data_demo/`、训练数据、点云、模型 checkpoint 和 Hugging Face 下载缓存。
- `outputs/` 原始目录及其中的全部渲染图、深度、视频、运行日志，以及带本机绝对路径的 `summary.json`；只发布 `docs/media/` 中上述明确选取的 12 个媒体文件，其中视频为准备工具生成的 H.264 展示副本。
- `third_party/`、Conda 环境、`.git/` 历史、缓存、`.so` 和 `.pyc` 等平台相关编译产物。
- 本机恢复的 `DirectAbsoluteCost_cuda.cu`。编译所需的历史源码按指南在独立官方源码目录获取，不随此资料包再分发。

本机完整 Demo 数据约 13 GB，运行输出约 1.7 GB，没有必要全部上传到普通 Git 仓库；本次仅发布上述精选媒体。读者按指南从官方 Hugging Face 仓库下载所需数据即可。GitHub 普通 Git 对超过 50 MiB 的文件发出警告，超过 100 MiB 的单文件会被阻止；详见[大文件限制](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)。Git LFS 可用于确需版本化的大文件，但本次精选媒体受单文件 25 MiB 上限约束，完整数据又已有外部下载来源，因此无需为它们配置 LFS。

源工作目录的 `.gitignore` 和合集的 `.gitignore` 均已屏蔽大数据、权重、运行输出、缓存、编译文件、常见视频/压缩包及凭据，不会全局屏蔽 PNG、CSV、TXT 等适合精选发布的小文件。仅对 `docs/media/feicuiwan_512/visualization.mp4`、`docs/media/feicuiwan_1024/visualization.mp4`、`docs/media/smbu_seq2/visualization.mp4` 三条视频设置精确白名单，合集中的规则使用对应的 `experiments/PiLoT/` 前缀；其他 MP4 和整个 `outputs/` 仍然屏蔽。根级 `/models/`、`/datasets/` 规则不会误伤 `pixloc/pixlib/models/` 等源码目录。

注意：`.gitignore` 只阻止尚未跟踪的文件被意外加入，不能自动移除已经跟踪的文件，更不能清理已有 Git 历史。本地官方仓库已经跟踪过一些二进制和缓存，所以本次使用独立白名单导出，而不是直接在原仓库 `git add .`。相关机制见 GitHub 的[忽略文件说明](https://docs.github.com/en/get-started/git-basics/ignoring-files)。

## 4. 检查后上传到自己的新仓库

以下命令是供仓库所有者手工执行的发布步骤；导出工具不会执行它们。

1. 登录 GitHub，创建属于自己账号的 `paper-replication` 仓库，可以选择 Public 或 Private。
2. 创建时先不要勾选自动生成 README、`.gitignore` 或 LICENSE，使远端保持为空，避免首次推送发生历史冲突。
3. 在本机进入新导出的轻量目录，而不是原始 PiLoT 源码目录。将下面的 `YOUR_USERNAME` 替换为自己的账号名。

```bash
cd ~/course/paper-reproductions
git init
git add README.md .gitignore EXPORT_MANIFEST.md experiments/
git status --short
git diff --cached --stat
```

确认暂存区只有文档、脚本、配置、少量文本结果和上述精选媒体，没有完整数据集、权重、未选取的运行输出、密钥或个人 Token 后再提交：

```bash
git commit -m "docs: add PiLoT reproduction guide and helpers"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/paper-replication.git
git remote -v
git push -u origin main
```

这里先执行 `git init`，首次提交后再将分支改名为 `main`，兼容不支持 `git init -b main` 的 Git 2.25.1。若轻量目录已经初始化并配置好自己的远端，就不必重复初始化或添加同名 `origin`；先用 `git status` 和 `git remote -v` 检查，再仅暂存本次增加的媒体和更新的文档、清单，提交后执行 `git push`。

以上 HTTPS 推送需要配置 GitHub 支持的身份验证，也可换成已配置密钥的 SSH 地址。若 Git 提示未设置提交身份，先在这个新仓库用 `git config user.name "你的名字"` 和 `git config user.email "你的提交邮箱"` 设置；不要将 Token 写到 Markdown、脚本、远端 URL 或配置样例中。官方流程见[从本机添加代码到 GitHub](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github)。

当前原始 PiLoT 工作目录的 `origin` 指向作者仓库 `nudt-sawlab/PiLoT`。不要在那个目录直接执行上面的推送命令，也不必修改它的 remote；新合集使用自己的独立仓库和 remote。

如果误暂存了不应公开的文件，应先停止提交，检查 `git status` 并撤出对应文件；如果文件已被跟踪，需要有针对性地停止跟踪，单纯增加 ignore 规则无效。若已提交大文件或凭据，后续删除一份工作区文件也不能从历史中清除；尤其凭据需要立即撤销并另行处理历史，不要继续盲目推送。

## 5. 以后增加其他论文

在 `experiments/NewPaper/` 中保存该论文的来源、环境、步骤、结果和必要脚本，并更新根 README 的索引。大数据继续使用外部下载链接。检查后，仅添加这次更新的文件，再提交和推送到同一个个人仓库即可。

尽量记录固定源码版本、运行参数、随机性说明、结果单位和复现边界。对于失败尝试也可保留原因和解决方式，让后来读者能区分“论文原方法”“复现中的环境修复”和“为了展示增加的功能”。
