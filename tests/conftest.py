from chickguard.models import Track


def make_track(track_id, points, diagonal=50.0, born=None):
    """points: [(frame_idx, x, y), ...]，直接构造一条轨迹，便于独立测试规则。"""
    born = points[0][0] if born is None else born
    return Track(track_id=track_id, born=born, diagonal=diagonal, history=list(points))
