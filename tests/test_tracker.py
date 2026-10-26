from chickguard.models import Detection
from chickguard.tracker import CentroidTracker


def det(x, y, s=40):
    return Detection((x, y, x + s, y + s))


def test_tracker_keeps_identity_across_frames():
    t = CentroidTracker(max_distance=50)
    t.update(0, [det(0, 0), det(300, 300)], fps=10)
    tracks = t.update(1, [det(5, 5), det(305, 300)], fps=10)
    assert sorted(x.track_id for x in tracks) == [1, 2]
    assert all(len(x.history) == 2 for x in tracks)


def test_tracker_tolerates_short_loss_then_drops():
    t = CentroidTracker(max_distance=50, max_lost_seconds=1.0)
    t.update(0, [det(0, 0)], fps=10)
    assert len(t.update(5, [], fps=10)) == 1     # 丢失 0.5s，仍保留
    assert len(t.update(30, [], fps=10)) == 0    # 丢失 3s，移除


def test_tracker_creates_new_track_for_far_detection():
    t = CentroidTracker(max_distance=50)
    t.update(0, [det(0, 0)], fps=10)
    tracks = t.update(1, [det(500, 500)], fps=10)
    assert len(tracks) == 2


def test_ratio_based_distance_scales_with_body_size():
    # 同样 100px 的位移：大个体（体长≈283）仍是同一只，小个体（体长≈28）则不是
    big = CentroidTracker(max_distance_ratio=0.8)
    big.update(0, [det(0, 0, s=200)], fps=10)
    assert len(big.update(1, [det(100, 0, s=200)], fps=10)) == 1

    small = CentroidTracker(max_distance_ratio=0.8)
    small.update(0, [det(0, 0, s=20)], fps=10)
    assert len(small.update(1, [det(100, 0, s=20)], fps=10)) == 2


def test_total_tracks_counts_every_created_track():
    t = CentroidTracker(max_distance=50)
    t.update(0, [det(0, 0)], fps=10)
    t.update(1, [det(500, 500)], fps=10)
    assert t.total_tracks == 2
