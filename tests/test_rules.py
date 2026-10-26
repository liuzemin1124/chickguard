from conftest import make_track

from chickguard.rules import HuddlingRule, InactivityRule, OutlierRule

FPS = 10.0


def test_inactivity_triggers_for_static_chicken():
    pts = [(f, 100 + (f % 2), 100) for f in range(0, 101)]  # 10 秒内几乎不动
    events = InactivityRule(window_seconds=10).evaluate([make_track(1, pts)], 100, FPS)
    assert len(events) == 1 and events[0].type == "inactivity"


def test_inactivity_not_triggered_for_moving_chicken():
    pts = [(f, 100 + f * 2, 100) for f in range(0, 101)]
    assert InactivityRule(window_seconds=10).evaluate([make_track(1, pts)], 100, FPS) == []


def test_inactivity_needs_full_window():
    pts = [(f, 100, 100) for f in range(0, 50)]  # 只观察了 5 秒
    assert InactivityRule(window_seconds=10).evaluate([make_track(1, pts)], 49, FPS) == []


def test_inactivity_threshold_boundary():
    # 体长 50px，阈值 0.3*50=15px：位移 14 触发，位移 16 不触发
    small = [(0, 0, 0), (100, 14, 0)]
    large = [(0, 0, 0), (100, 16, 0)]
    rule = InactivityRule(window_seconds=10, move_ratio=0.3)
    assert len(rule.evaluate([make_track(1, small)], 100, FPS)) == 1
    assert rule.evaluate([make_track(2, large)], 100, FPS) == []


def _cluster(n, cx, cy, start_id=1):
    return [make_track(start_id + i, [(10, cx + (i % 3) * 20, cy + (i // 3) * 20)]) for i in range(n)]


def test_huddling_detects_dense_group():
    tracks = _cluster(7, 300, 300)
    events = HuddlingRule(radius_ratio=1.5, min_members=6).evaluate(tracks, 10, FPS)
    assert len(events) == 1 and len(events[0].track_ids) == 7


def test_huddling_ignores_spread_out_chickens():
    tracks = [make_track(i, [(10, i * 300, 0)]) for i in range(8)]
    assert HuddlingRule(min_members=6).evaluate(tracks, 10, FPS) == []


def test_outlier_detects_far_chicken():
    tracks = _cluster(8, 100, 100) + [make_track(99, [(10, 1000, 1000)])]
    events = OutlierRule().evaluate(tracks, 10, FPS)
    assert [e.track_ids for e in events] == [(99,)]


def test_outlier_needs_enough_tracks():
    tracks = _cluster(3, 100, 100) + [make_track(99, [(10, 1000, 1000)])]
    assert OutlierRule(min_tracks=5).evaluate(tracks, 10, FPS) == []
