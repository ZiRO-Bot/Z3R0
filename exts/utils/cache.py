import time


from typing import Any, Tuple


# https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/cache.py#L22-L43
class ExpiringCache(dict):
    """Subclassed dict"""

    def __init__(self, maxAgeSeconds: int = 5) -> None:
        self.maxAgeSeconds: int = maxAgeSeconds
        super().__init__()

    def verifyCache(self) -> None:
        curTime: float = time.monotonic()
        toRemove: list = [
            k for (k, (v, t)) in self.items() if curTime > (t + self.maxAgeSeconds)
        ]
        for k in toRemove:
            del self[k]

    def __contains__(self, key: Any) -> bool:
        self.verifyCache()
        return super().__contains__(key)

    def __getitem__(self, key: Any) -> Tuple[Any]:
        self.verifyCache()
        return super().__getitem__(key)

    def __setitem__(self, key: Any, value: Any) -> None:
        self.verifyCache()
        return super().__setitem__(key, (value, time.monotonic()))
