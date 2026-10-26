"""Streamlit 界面：上传视频 → 调参数 → 分析 → 看标注视频、告警与历史。
界面层不含业务逻辑，只调用 service.analyze。
启动：streamlit run src/chickguard/app.py"""
import copy
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from chickguard.config import load_config  # noqa: E402
from chickguard.service import analyze  # noqa: E402
from chickguard.storage import EventStore  # noqa: E402

TYPE_CN = {"inactivity": "不活动", "huddling": "扎堆", "outlier": "离群"}
OUT_DIR = ROOT / "output"
DB_PATH = OUT_DIR / "app_events.db"

st.set_page_config(page_title="ChickGuard 活鸡异常检测", layout="wide")


@st.cache_resource(show_spinner="正在加载检测模型……")
def get_detector(model_path: str, confidence: float, classes: tuple):
    from chickguard.detectors.yolo_detector import YoloDetector
    return YoloDetector(model_path=model_path, confidence=confidence, classes=list(classes))


def build_cfg() -> dict:
    cfg = copy.deepcopy(load_config(str(ROOT / "config" / "default.yaml")))
    sb = st.sidebar
    sb.header("检测")
    model = sb.selectbox("模型", ["yolov8n.pt", "yolov8s.pt", "yolov8m.pt"],
                         help="越大检出越多但越慢；首次使用会自动下载")
    custom = sb.text_input("自定义权重路径（可选）", "")
    conf = sb.slider("置信度阈值", 0.05, 0.90, 0.30, 0.05)
    sb.header("视频处理")
    stride = sb.slider("每 N 帧处理 1 帧", 1, 10, cfg["pipeline"].get("stride", 2))
    width = sb.selectbox("处理宽度(px)", [640, 960, 1280, 1920],
                         index=2, help="大画面会先缩小再检测，速度更快")
    sb.header("规则")
    rules = []
    if sb.checkbox("不活动", True):
        rules.append({"name": "inactivity", "params": {
            "window_seconds": sb.slider("观察窗口(秒)", 2, 30, 10),
            "move_ratio": sb.slider("位移阈值(体长倍数)", 0.1, 1.0, 0.3, 0.05)}})
    if sb.checkbox("扎堆", True):
        rules.append({"name": "huddling", "params": {
            "min_members": sb.slider("扎堆最少只数", 3, 20, 6),
            "radius_ratio": sb.slider("聚集半径(体长倍数)", 0.5, 3.0, 1.5, 0.1)}})
    if sb.checkbox("离群", True):
        rules.append({"name": "outlier", "params": {
            "outlier_ratio": sb.slider("离群倍数", 2.0, 10.0, 4.0, 0.5),
            "min_tracks": 5}})
    cooldown = sb.slider("同一目标告警冷却(秒)", 5, 120, 30)
    overlap = sb.slider("告警合并：成员重叠度", 0.3, 1.0, 0.5, 0.05,
                        help="冷却期内同类告警的成员重叠超过该比例，视为同一事件")

    cfg["detector"]["params"].update(
        model_path=custom.strip() or model, confidence=conf)
    cfg["pipeline"].update(stride=stride, max_width=width)
    cfg["rules"] = rules
    cfg["alert"] = {"cooldown_seconds": cooldown, "overlap_threshold": overlap}
    return cfg


def show_result(r) -> None:
    c = st.columns(5)
    c[0].metric("告警数", len(r.events))
    c[1].metric("处理帧数", r.frames_processed)
    c[2].metric("耗时(秒)", f"{r.elapsed_seconds:.1f}")
    c[3].metric("处理速度(帧/秒)", f"{r.proc_fps:.1f}")
    c[4].metric("产生轨迹总数", r.total_tracks)
    if r.processed_size:
        st.caption(
            f"原始分辨率 {r.source_size[0]}x{r.source_size[1]} → 处理分辨率 "
            f"{r.processed_size[0]}x{r.processed_size[1]}；平均每帧检测到 {r.avg_detections:.1f} 只。"
            "告警由规则基线产生，不代表真实的异常或疾病。")

    left, right = st.columns([3, 2])
    with left:
        st.subheader("标注视频")
        if r.video_path and r.playable:
            st.video(r.video_path)
        elif r.video_path:
            st.info("未安装 imageio-ffmpeg，浏览器无法直接播放，请下载后用本地播放器查看。")
        if r.video_path:
            with open(r.video_path, "rb") as f:
                st.download_button("下载标注视频", f, file_name=os.path.basename(r.video_path))
    with right:
        st.subheader("告警列表")
        if r.events:
            df = pd.DataFrame([{
                "时间(秒)": round(e.timestamp, 1), "类型": TYPE_CN.get(e.type, e.type),
                "说明": e.message} for e in r.events])
            st.dataframe(df, use_container_width=True, hide_index=True)
            counts = Counter(TYPE_CN.get(e.type, e.type) for e in r.events)
            st.bar_chart(pd.Series(counts, name="数量"))
        else:
            st.write("没有产生告警。")

    if r.snapshots:
        st.subheader("告警截图")

        def gallery(items):
            cols = st.columns(3)
            for i, (evs, img) in enumerate(items):
                kinds = "/".join(sorted({TYPE_CN.get(e.type, e.type) for e in evs}))
                cols[i % 3].image(img[:, :, ::-1], caption=f"{evs[0].timestamp:.1f}s {kinds}")

        gallery(r.snapshots[:12])
        if len(r.snapshots) > 12:
            with st.expander(f"更多截图（共 {len(r.snapshots)} 张）"):
                gallery(r.snapshots[12:])


def tab_analyze(cfg: dict) -> None:
    mode = st.radio("视频来源", ["上传文件", "data/samples 目录"], horizontal=True)
    video_path = None
    if mode == "上传文件":
        up = st.file_uploader("选择视频", type=["mp4", "avi", "mov", "mkv"])
        if up is not None:
            tmp = Path(tempfile.gettempdir()) / f"chickguard_{up.name}"
            tmp.write_bytes(up.getbuffer())
            video_path = str(tmp)
            name = Path(up.name).stem
    else:
        files = sorted(p for p in (ROOT / "data" / "samples").glob("*")
                       if p.suffix.lower() in {".mp4", ".avi", ".mov", ".mkv"})
        if files:
            pick = st.selectbox("样例视频", files, format_func=lambda p: p.name)
            video_path, name = str(pick), pick.stem
        else:
            st.info("data/samples 目录里还没有视频。")

    if video_path and st.button("开始分析", type="primary"):
        OUT_DIR.mkdir(exist_ok=True)
        bar = st.progress(0.0, text="分析中……")
        detector = get_detector(cfg["detector"]["params"]["model_path"],
                                cfg["detector"]["params"]["confidence"],
                                tuple(cfg["detector"]["params"].get("classes", ["bird"])))
        store = EventStore(str(DB_PATH))
        try:
            st.session_state["result"] = analyze(
                video_path, cfg, out_path=str(OUT_DIR / f"{name}_annotated.mp4"),
                detector=detector, store=store,
                progress=lambda p: bar.progress(p, text=f"分析中……{p:.0%}"))
        finally:
            store.close()
        bar.empty()

    if "result" in st.session_state:
        show_result(st.session_state["result"])


def tab_history() -> None:
    if not DB_PATH.exists():
        st.info("还没有历史记录，先去分析一段视频。")
        return
    store = EventStore(str(DB_PATH))
    events = store.list_events()
    if not events:
        st.info("历史记录为空。")
    else:
        kind = st.multiselect("按类型筛选", list(TYPE_CN.values()), default=list(TYPE_CN.values()))
        rows = [{"视频时间(秒)": round(e.timestamp, 1), "类型": TYPE_CN.get(e.type, e.type),
                 "说明": e.message} for e in events if TYPE_CN.get(e.type, e.type) in kind]
        st.write(f"共 {len(rows)} 条")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.download_button("导出 CSV", pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig"),
                           file_name="events.csv")
    if st.button("清空历史记录"):
        store.clear()
        st.rerun()
    store.close()


st.title("ChickGuard 活鸡异常检测系统")
cfg = build_cfg()
t1, t2 = st.tabs(["分析视频", "历史记录"])
with t1:
    tab_analyze(cfg)
with t2:
    tab_history()
