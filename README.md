# ChickGuard：活鸡异常检测原型系统

《软件工程基础》课程作业（方向 A：正向开发）。

模块化的活鸡异常检测系统：视频 → 检测 → 跟踪 → 规则判定 → 告警。
检测器与规则都是可替换的接口，模型和阈值在 `config/default.yaml` 中配置。

> 告警由规则基线产生，不代表真实的异常或疾病；系统没有做检测精度评估。

## 环境要求

- Python 3.10 或更高
- Windows、Linux、macOS 均可（作者在 Windows 上开发和测试）
- 首次运行检测需要联网下载约 6 MB 的模型文件 `yolov8n.pt`（见下文）

## 安装

```bash
python -m venv venv
# Windows PowerShell:  .\venv\Scripts\Activate.ps1
# Windows cmd:         venv\Scripts\activate.bat
# Linux / macOS:       source venv/bin/activate

pip install -r requirements.txt
```

`requirements.txt` 中的 torch 等依赖较大，安装需要一些时间。国内网络可以加镜像：
`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

## 1. 运行自动化测试（不需要模型和视频）

```bash
pytest
```

预期结果：32 个测试全部通过。

## 2. 准备视频和模型

- **视频**：仓库不包含视频文件。请自备一段 mp4，放进 `data/samples/`。
- **模型**：第一次运行时 Ultralytics 会自动下载 `yolov8n.pt` 到当前目录。
  如果下载失败，可手动下载后放到项目根目录，或在 `config/default.yaml` 中把
  `model_path` 改成本地权重的路径。

## 3. 运行

### 图形界面（推荐）

```bash
streamlit run src/chickguard/app.py
```

在浏览器里选择视频（上传，或选 `data/samples` 中的文件），调整左侧参数，点击“开始分析”。
结果页显示标注视频、告警列表、统计和告警截图；“历史记录”页可筛选和导出 CSV。

### 命令行

在项目根目录运行（先设置 `PYTHONPATH`）：

```bash
# Windows PowerShell:  $env:PYTHONPATH="src"
# Windows cmd:         set PYTHONPATH=src
# Linux / macOS:       export PYTHONPATH=src

python -m chickguard.cli data/samples/你的视频.mp4
```

输出内容包括处理帧数、耗时、处理速度、检测统计、告警列表，标注视频保存在 `output/` 目录。
可选参数：`--config 配置文件路径`、`--out 输出视频路径`、`--no-video`。

## 配置

`config/default.yaml` 中可以修改：检测模型与置信度、抽帧间隔、处理宽度、
三条规则的阈值、告警冷却时间与合并阈值。界面侧栏的参数与之对应。

## 项目结构

```
config/default.yaml          默认配置
src/chickguard/
  models.py                  Detection / Track / Event
  detectors/                 检测器接口、YOLO 实现、测试用假检测器
  tracker.py                 质心跟踪器
  rules/                     不活动 / 扎堆 / 离群 三条规则
  alert_manager.py           告警合并（冷却 + 成员重叠）
  storage.py                 SQLite 事件存储
  video_source.py            视频读取、抽帧、缩放
  annotator.py               标注视频、告警截图、H.264 转码
  pipeline.py                流水线
  service.py                 一次完整分析（命令行与界面共用）
  config.py                  读取配置并构造对象
  cli.py / app.py            命令行 / Streamlit 界面
tests/                       单元、契约、端到端与界面冒烟测试
```

## 已知局限

- 默认使用 COCO 预训练的 YOLOv8n，没有 chicken 类，鸡通常被识别为 bird，鸭、鹅也会被检出。
- 规则只基于位移和位置，近景、手持镜头、高密度场景下会失效。
- CPU 模式下处理速度低于视频帧率，只适合离线分析。
- 演示使用的是公开视频素材，不是真实鸡舍监控。
