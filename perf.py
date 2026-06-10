import time
import logging

logger = logging.getLogger("piccord.perf")
logging.basicConfig(level=logging.INFO, format="[PERF] %(message)s")


class StageTimer:
    """同期処理のステージ計測。CPU処理（PIL/numpy等）に使う。"""

    def __init__(self, name: str):
        self.name = name
        self._t = 0.0

    def __enter__(self):
        self._t = time.perf_counter()
        return self

    def __exit__(self, *_):
        ms = (time.perf_counter() - self._t) * 1000
        logger.info(f"{self.name}: {ms:.1f}ms")


class AsyncStageTimer:
    """非同期ステージ（await含む）の計測。Discordネットワーク往復・DBクエリに使う。"""

    def __init__(self, name: str):
        self.name = name
        self._t = 0.0

    async def __aenter__(self):
        self._t = time.perf_counter()
        return self

    async def __aexit__(self, *_):
        ms = (time.perf_counter() - self._t) * 1000
        logger.info(f"{self.name}: {ms:.1f}ms")


class TotalTimer:
    """関数全体の合計時間を計測する。"""

    def __init__(self, label: str):
        self.label = label
        self._t = 0.0

    def start(self):
        self._t = time.perf_counter()

    def stop(self):
        ms = (time.perf_counter() - self._t) * 1000
        logger.info(f"TOTAL [{self.label}]: {ms:.1f}ms")
