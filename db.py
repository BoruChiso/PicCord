from typing import Optional

import asyncpg

from constants import ID_MAX


class UserIdMapper:
    """Discord UserIDと16bit内部IDの1:1マッピングをPostgreSQLで永続化する。

    myCrypterが要求する16bit ID空間（0〜65535）に対して、
    Discord UserID（19桁整数）を衝突なしにマッピングする。
    """

    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def init(self):
        """テーブルが存在しなければ作成する。"""
        await self._pool.execute("""
            CREATE TABLE IF NOT EXISTS user_id_mapping (
                internal_id INTEGER PRIMARY KEY
                    CHECK (internal_id >= 0 AND internal_id <= 65535),
                discord_user_id BIGINT NOT NULL UNIQUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        await self._pool.execute("""
            CREATE INDEX IF NOT EXISTS idx_discord_user_id
                ON user_id_mapping(discord_user_id)
        """)

    async def get_or_create_internal_id(self, discord_user_id: int) -> int:
        """Discord UserIDに対応するinternal_idを取得する。未登録なら新規割り当て。

        Args:
            discord_user_id: Discord UserID（19桁整数）

        Returns:
            0〜65535の範囲のinternal_id

        Raises:
            RuntimeError: ID空間（65536）が枯渇した場合
        """
        # 既存のマッピングを検索し、last_accessed_atを更新
        row = await self._pool.fetchrow(
            """
            UPDATE user_id_mapping
            SET last_accessed_at = NOW()
            WHERE discord_user_id = $1
            RETURNING internal_id
            """,
            discord_user_id,
        )
        if row is not None:
            return row["internal_id"]

        # 新規割り当て: 未使用の最小IDを取得
        row = await self._pool.fetchrow(
            """
            INSERT INTO user_id_mapping (internal_id, discord_user_id)
            SELECT s.id, $1
            FROM generate_series(0, $2 - 1) AS s(id)
            WHERE s.id NOT IN (SELECT internal_id FROM user_id_mapping)
            ORDER BY s.id
            LIMIT 1
            RETURNING internal_id
            """,
            discord_user_id,
            ID_MAX,
        )
        if row is None:
            raise RuntimeError(
                f"ID空間が枯渇しました（上限: {ID_MAX}ユーザー）"
            )
        return row["internal_id"]

    async def get_discord_id(self, internal_id: int) -> Optional[int]:
        """internal_idからDiscord UserIDを逆引きする。

        Args:
            internal_id: 0〜65535の範囲のinternal_id

        Returns:
            対応するDiscord UserID。見つからない場合はNone。
        """
        row = await self._pool.fetchrow(
            "SELECT discord_user_id FROM user_id_mapping WHERE internal_id = $1",
            internal_id,
        )
        if row is None:
            return None
        return row["discord_user_id"]
