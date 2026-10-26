import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

from chickguard.video_source import OpenCVVideoSource


def test_opencv_source_reads_frames_with_stride(tmp_path):
    path = str(tmp_path / "t.avi")
    w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (64, 48))
    for i in range(20):
        w.write(np.full((48, 64, 3), i * 10, dtype=np.uint8))
    w.release()
    src = OpenCVVideoSource(path, stride=5)
    assert abs(src.fps - 10.0) < 0.5
    assert [i for i, _ in src] == [0, 5, 10, 15]


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        OpenCVVideoSource(str(tmp_path / "nope.mp4"))
