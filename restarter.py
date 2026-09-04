import asyncio

DEFAULT_RESTART_INTERVAL_SECONDS = 24 * 60 * 60


class DailyRestarter:
    """一定時間経過後にclientをcloseし、プロセス自体を終了させるスケジューラ。

    Railway等のPaaSでrestart policyが有効な環境で、
    24時間ごとにプロセスを再起動させ、メモリリーク等を回避する目的で使う。
    """

    def __init__(self, client, interval_seconds: int = DEFAULT_RESTART_INTERVAL_SECONDS):
        self.client = client
        self.interval_seconds = interval_seconds
        self._scheduled = False

    async def start(self) -> None:
        if self._scheduled:
            return
        self._scheduled = True
        await asyncio.sleep(self.interval_seconds)
        await self.client.close()
