import asyncio
from unittest.mock import AsyncMock

import pytest

from restarter import DailyRestarter


@pytest.mark.asyncio
async def test_start_closes_client_after_interval(monkeypatch):
    """interval秒経過後にclient.close()が呼ばれること"""
    sleep_calls = []

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    client = AsyncMock()
    restarter = DailyRestarter(client, interval_seconds=86400)

    await restarter.start()

    assert sleep_calls == [86400]
    client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_is_idempotent(monkeypatch):
    """二重にstart()してもclient.close()は1回だけ呼ばれること"""

    async def fake_sleep(_seconds):
        pass

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    client = AsyncMock()
    restarter = DailyRestarter(client, interval_seconds=1)

    await asyncio.gather(restarter.start(), restarter.start())

    client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_default_interval_is_24_hours():
    """デフォルト間隔が24時間(86400秒)であること"""
    restarter = DailyRestarter(AsyncMock())
    assert restarter.interval_seconds == 24 * 60 * 60
