import time


from typing import Any, Tuple


# https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/cache.py#L22-L43
class ExpiringDict(dict):
    """Subclassed dict for expiring cache"""

    def __init__(self, items: dict = {}, maxAgeSeconds: int = 3600) -> None:
        self.maxAgeSeconds: int = maxAgeSeconds #(Default: 3600 seconds (1 hour))
        curTime: float = time.monotonic()
        super().__init__({k: (v, curTime) for k, v in items.items()})

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

    def __getitem__(self, key: Any) -> Any:
        self.verifyCache()
        return super().__getitem__(key)[0]

    def get(self, key: Any, fallback: Any = None) -> Any:
        try:
            return self.__getitem__(key)
        except KeyError:
            return fallback

    def getRaw(self, key: Any) -> Tuple[Any]:
        self.verifyCache()
        return super().__getitem__(key)

    def __setitem__(self, key: Any, value: Any) -> None:
        self.verifyCache()
        return super().__setitem__(key, (value, time.monotonic()))
