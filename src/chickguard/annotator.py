"""把检测框、跟踪 ID 和告警画到视频上并写出文件（cv2 仅在实例化时导入）。"""
from __future__ import annotations

import os
import subprocess
from typing import Dict, List, Optional, Tuple

from .models import Detection, Event, Track


def to_browser_mp4(src: str, dst: str) -> bool:
    """把 OpenCV 写出的 mp4v 转成浏览器可播放的 H.264。需要 imageio-ffmpeg；失败返回 False。"""
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run(
            [exe, "-y", "-loglevel", "error", "-i", src,
             "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
             "-vcodec", "libx264", "-pix_fmt", "yuv420p", "-crf", "23",
             "-preset", "veryfast", "-movflags", "+faststart", dst],
            check=True, capture_output=True)
        return os.path.exists(dst)
    except Exception:
        return False


class VideoAnnotator:
    GREEN = (0, 200, 0)
    RED = (0, 0, 255)

    def __init__(self, out_path: str, src_fps: float, stride: int = 1,
                 max_width: int = 1280, hold_seconds: float = 3.0,
                 max_snapshots: int = 24):
        try:
            import cv2
        except ImportError as e:  # pragma: no cover
            raise ImportError("输出标注视频需要先安装 opencv-python") from e
        self._cv2 = cv2
        self.out_path = out_path
        self.src_fps = src_fps
        self.out_fps = max(1.0, src_fps / max(1, stride))  # 保持真实播放速度
        self.max_width = max_width
        self.hold_seconds = hold_seconds
        self._writer = None
        self._scale = 1.0
        self._flagged: Dict[int, Tuple[float, str]] = {}   # track_id -> (截止时间, 类型)
        self._banner: Optional[Tuple[float, str]] = None   # (截止时间, 文本)
        self.max_snapshots = max_snapshots
        self.snapshots: List[Tuple[List[Event], object]] = []  # (该帧的事件列表, 标注后的画面)
        self._pending: List[Event] = []

    def on_event(self, events: List[Event]) -> None:
        for e in events:
            until = e.timestamp + self.hold_seconds
            for tid in e.track_ids:
                self._flagged[tid] = (until, e.type)
            ids = ",".join(f"#{i}" for i in e.track_ids[:4])
            self._banner = (until, f"ALERT {e.type} {ids}")
            if len(self.snapshots) < self.max_snapshots:
                self._pending.append(e)  # 在下一帧（已标红）截图，同一帧的事件共用一张

    def on_frame(self, frame_idx: int, frame, detections: List[Detection],
                 tracks: List[Track]) -> None:
        cv2 = self._cv2
        if self._writer is None:
            h, w = frame.shape[:2]
            self._scale = min(1.0, self.max_width / w)
            size = (int(w * self._scale), int(h * self._scale))
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self._writer = cv2.VideoWriter(self.out_path, fourcc, self.out_fps, size)
            if not self._writer.isOpened():
                raise RuntimeError(f"无法创建输出视频: {self.out_path}")
        now = frame_idx / self.src_fps
        img = frame.copy()
        s = self._scale
        ids = {t.position: t.track_id for t in tracks if t.last_seen == frame_idx}
        for d in detections:
            tid = ids.get(d.center)
            flagged = tid in self._flagged and self._flagged[tid][0] >= now
            color = self.RED if flagged else self.GREEN
            x1, y1, x2, y2 = [int(v) for v in d.bbox]
            cv2.rectangle(img, (x1, y1), (x2, y2), color, max(2, int(3 / s)))
            if tid is not None:
                cv2.putText(img, f"#{tid}", (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX,
                            0.9 / s, color, max(2, int(2 / s)))
        if self._banner and self._banner[0] >= now:
            cv2.putText(img, self._banner[1], (20, int(50 / s)), cv2.FONT_HERSHEY_SIMPLEX,
                        1.2 / s, self.RED, max(2, int(3 / s)))
        if s < 1.0:
            img = cv2.resize(img, None, fx=s, fy=s)
        self._writer.write(img)
        if self._pending:
            small = img
            if img.shape[1] > 800:
                f = 800 / img.shape[1]
                small = cv2.resize(img, None, fx=f, fy=f)
            self.snapshots.append((self._pending, small.copy()))
            self._pending = []

    def close(self) -> None:
        if self._writer is not None:
            self._writer.release()
            self._writer = None
