from .base import Rule
from .huddling import HuddlingRule
from .inactivity import InactivityRule
from .outlier import OutlierRule

REGISTRY = {
    "inactivity": InactivityRule,
    "huddling": HuddlingRule,
    "outlier": OutlierRule,
}

__all__ = ["Rule", "InactivityRule", "HuddlingRule", "OutlierRule", "REGISTRY"]
