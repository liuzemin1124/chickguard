"""命令行入口：python -m chickguard.cli <video> [--config ...] [--out ...] [--no-video]"""
from __future__ import annotations

import argparse
import math
import os

from .config import load_config
from .service import analyze
from .storage import EventStore


def main() -> None:
    ap = argparse.ArgumentParser(description="ChickGuard 活鸡异常检测")
    ap.add_argument("video")
    ap.add_argument("--config", default="config/default.yaml")
    ap.add_argument("--out", default=None, help="标注视频输出路径，默认 output/<视频名>_annotated.mp4")
    ap.add_argument("--no-video", action="store_true", help="不输出标注视频")
    args = ap.parse_args()

    cfg = load_config(args.config)
    store = EventStore(cfg.get("storage", {}).get("db_path", ":memory:"))
    out = None
    if not args.no_video:
        out = args.out or os.path.join(
            "output", os.path.splitext(os.path.basename(args.video))[0] + "_annotated.mp4")

    r = analyze(args.video, cfg, out_path=out, store=store,
                progress=None)

    print(f"\n处理 {r.frames_processed} 帧，视频时长约 {r.duration_seconds:.1f}s，"
          f"产生 {len(r.events)} 条告警")
    print(f"耗时 {r.elapsed_seconds:.1f}s，处理速度 {r.proc_fps:.1f} 帧/秒 "
          f"(视频 {r.video_fps:.1f}fps，stride={r.stride})")
    if r.processed_size:
        w, h = r.processed_size
        print(f"原始分辨率 {r.source_size[0]}x{r.source_size[1]}，处理分辨率 {w}x{h}；"
              f"平均每帧检测到 {r.avg_detections:.1f} 只；"
              f"检测框平均对角线 {r.avg_diagonal:.0f}px（画面对角线 {math.hypot(w, h):.0f}px）")
    print(f"产生轨迹总数 {r.total_tracks}（远大于同时在场的鸡数，说明跟踪经常断裂）")
    try:
        import torch
        print(f"CUDA 可用: {torch.cuda.is_available()}")
    except ImportError:
        pass
    if r.video_path:
        print(f"标注视频: {r.video_path}")
    for e in r.events:
        print(f"[{e.timestamp:7.1f}s] {e.type:<10} {e.message}")


if __name__ == "__main__":
    main()
