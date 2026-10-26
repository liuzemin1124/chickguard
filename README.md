# ChickGuard：活鸡异常检测原型系统

《软件工程基础》课程作业（方向 A：正向开发）。
模块化的活鸡异常检测系统：视频 → 检测 → 跟踪 → 规则判定 → 告警。
检测器与规则均为可替换接口，阈值与模型在 `config/default.yaml` 中配置。

## 快速开始（Windows / Linux / macOS）

```bash
pip install -r requirements.txt
pytest                                   # 运行全部测试（不需要模型和视频）
# Windows cmd:  set PYTHONPATH=src        PowerShell: $env:PYTHONPATH="src"
# Linux/macOS:  export PYTHONPATH=src
python -m chickguard.cli data/samples/your_video.mp4   # 命令行
streamlit run src/chickguard/app.py                    # 图形界面
```

## 结构

- `models.py` 数据结构；`detectors/` 检测器接口与实现；`tracker.py` 跟踪
- `rules/` 三条规则（不活动 / 扎堆 / 离群）；`alert_manager.py` 告警去重
- `service.py` 应用服务（命令行与界面共用）；`app.py` Streamlit 界面；`annotator.py` 标注视频
- `pipeline.py` 流水线；`config.py` 配置工厂；`storage.py` SQLite；`cli.py` 命令行
- `tests/` 单元、契约、端到端测试

## 说明

- 默认检测器为 Ultralytics YOLO 预训练模型（COCO 无 chicken 类，鸡多被识别为 bird）。
- 规则为基线实现，缺少带异常标注的公开数据，未做定量精度评估。
- 数据来源与许可见设计文档；请勿提交未授权的数据文件。
