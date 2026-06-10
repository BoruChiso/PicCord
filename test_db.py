import asyncio
import os

import pytest
import pytest_asyncio
import asyncpg

from db import UserIdMapper, ImageCacheMapper

DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://piccord:piccord_dev@localhost:5432/piccord",
)


@pytest_asyncio.fixture
async def mapper():
    pool = await asyncpg.create_pool(DATABASE_URL)
    m = UserIdMapper(pool)
    await m.init()
    yield m
    # テスト後にテーブルをクリーンアップ
    await pool.execute("DELETE FROM user_id_mapping")
    await pool.close()


@pytest.mark.asyncio
async def test_get_or_create_returns_valid_range(mapper):
    """internal_idが0〜65535の範囲内であること"""
    internal_id = await mapper.get_or_create_internal_id(123456789012345678)
    assert 0 <= internal_id <= 65535


@pytest.mark.asyncio
async def test_same_user_gets_same_id(mapper):
    """同じDiscord UserIDには常に同じinternal_idが返ること"""
    discord_id = 999888777666555444
    id1 = await mapper.get_or_create_internal_id(discord_id)
    id2 = await mapper.get_or_create_internal_id(discord_id)
    assert id1 == id2


@pytest.mark.asyncio
async def test_different_users_get_different_ids(mapper):
    """異なるDiscord UserIDには異なるinternal_idが割り当てられること"""
    id1 = await mapper.get_or_create_internal_id(111111111111111111)
    id2 = await mapper.get_or_create_internal_id(222222222222222222)
    assert id1 != id2


@pytest.mark.asyncio
async def test_reverse_lookup(mapper):
    """internal_idからDiscord UserIDを逆引きできること"""
    discord_id = 333333333333333333
    internal_id = await mapper.get_or_create_internal_id(discord_id)
    result = await mapper.get_discord_id(internal_id)
    assert result == discord_id


@pytest.mark.asyncio
async def test_reverse_lookup_not_found(mapper):
    """存在しないinternal_idの逆引きはNoneを返すこと"""
    result = await mapper.get_discord_id(99999)
    assert result is None


@pytest.mark.asyncio
async def test_persistence_across_instances(mapper):
    """別のUserIdMapperインスタンスからも同じマッピングが取得できること（永続化の確認）"""
    discord_id = 444444444444444444
    internal_id = await mapper.get_or_create_internal_id(discord_id)

    # 同じプールで新しいインスタンスを作成
    mapper2 = UserIdMapper(mapper._pool)
    await mapper2.init()
    internal_id2 = await mapper2.get_or_create_internal_id(discord_id)
    assert internal_id == internal_id2


@pytest.mark.asyncio
async def test_many_users_no_collision(mapper):
    """100人のユーザーを登録しても衝突しないこと"""
    base_id = 100000000000000000
    ids = set()
    for i in range(100):
        internal_id = await mapper.get_or_create_internal_id(base_id + i)
        ids.add(internal_id)
    assert len(ids) == 100


@pytest_asyncio.fixture
async def cache_mapper():
    pool = await asyncpg.create_pool(DATABASE_URL)
    m = ImageCacheMapper(pool)
    await m.init()
    yield m
    await pool.execute("DELETE FROM image_cache")
    await pool.close()


@pytest.mark.asyncio
async def test_get_message_id_not_found(cache_mapper):
    """未登録の(thread_id, internal_id)はNoneを返すこと"""
    result = await cache_mapper.get_message_id(999, 0)
    assert result is None


@pytest.mark.asyncio
async def test_set_and_get_message_id(cache_mapper):
    """set後にgetで同じmessage_idが返ること"""
    await cache_mapper.set_message_id(111, 1, 9999999999)
    result = await cache_mapper.get_message_id(111, 1)
    assert result == 9999999999


@pytest.mark.asyncio
async def test_set_message_id_upsert(cache_mapper):
    """同じ(thread_id, internal_id)に再setすると上書きされること"""
    await cache_mapper.set_message_id(222, 2, 1111111111)
    await cache_mapper.set_message_id(222, 2, 2222222222)
    result = await cache_mapper.get_message_id(222, 2)
    assert result == 2222222222


@pytest.mark.asyncio
async def test_different_keys_independent(cache_mapper):
    """(thread_id, internal_id)の組み合わせが独立して管理されること"""
    await cache_mapper.set_message_id(333, 3, 1000000001)
    await cache_mapper.set_message_id(333, 4, 1000000002)
    await cache_mapper.set_message_id(444, 3, 1000000003)
    assert await cache_mapper.get_message_id(333, 3) == 1000000001
    assert await cache_mapper.get_message_id(333, 4) == 1000000002
    assert await cache_mapper.get_message_id(444, 3) == 1000000003
