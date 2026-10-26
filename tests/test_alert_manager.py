from chickguard.alert_manager import AlertManager
from chickguard.models import Event
from chickguard.storage import EventStore


def ev(ts, ids=(1,), type="inactivity"):
    return Event(type, int(ts * 10), ts, ids)


def test_duplicate_events_suppressed_within_cooldown():
    am = AlertManager(cooldown_seconds=30)
    assert len(am.submit([ev(10)])) == 1
    assert am.submit([ev(20)]) == []
    assert len(am.submit([ev(41)])) == 1       # 冷却结束后再次告警


def test_different_targets_or_types_not_merged():
    am = AlertManager(cooldown_seconds=30)
    out = am.submit([ev(10, (1,)), ev(10, (2,)), ev(10, (1,), "outlier")])
    assert len(out) == 3


def test_accepted_events_are_persisted():
    store = EventStore(":memory:")
    am = AlertManager(cooldown_seconds=30, store=store)
    am.submit([ev(10), ev(12)])
    saved = store.list_events()
    assert len(saved) == 1 and saved[0].track_ids == (1,)


def huddle(ts, ids):
    return Event("huddling", int(ts * 10), ts, tuple(sorted(ids)))


def test_huddle_with_changing_membership_is_one_incident():
    am = AlertManager(cooldown_seconds=30, overlap_threshold=0.5)
    assert len(am.submit([huddle(10, {1, 2, 3, 4, 5, 6})])) == 1
    # 下一秒成员变了一只（重叠 5/6），仍是同一个事件
    assert am.submit([huddle(11, {1, 2, 3, 4, 5, 7})]) == []


def test_disjoint_huddle_is_a_new_incident():
    am = AlertManager(cooldown_seconds=30, overlap_threshold=0.5)
    am.submit([huddle(10, {1, 2, 3, 4, 5, 6})])
    assert len(am.submit([huddle(11, {10, 11, 12, 13, 14, 15})])) == 1


def test_overlapping_events_in_same_batch_are_merged():
    am = AlertManager(cooldown_seconds=30, overlap_threshold=0.5)
    out = am.submit([huddle(10, {1, 2, 3, 4, 5, 6}), huddle(10, {1, 2, 3, 4, 5, 7})])
    assert len(out) == 1


def test_same_huddle_alerts_again_after_cooldown():
    am = AlertManager(cooldown_seconds=30, overlap_threshold=0.5)
    am.submit([huddle(10, {1, 2, 3, 4, 5, 6})])
    assert len(am.submit([huddle(41, {1, 2, 3, 4, 5, 6})])) == 1
