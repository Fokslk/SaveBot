from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


@dataclass
class StoredMessage:
    message_id: int
    chat_id: int
    business_connection_id: str
    from_user_id: int | None
    from_user_name: str | None
    text: str | None
    caption: str | None
    media_type: str | None
    file_id: str | None
    file_unique_id: str | None
    local_path: str | None
    has_protected_content: bool
    date: str
    edit_date: str | None
    is_deleted: bool
    raw_json: str


class MessageStorage:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS business_connections (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    user_chat_id INTEGER NOT NULL,
                    is_enabled INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    business_connection_id TEXT NOT NULL,
                    from_user_id INTEGER,
                    from_user_name TEXT,
                    text TEXT,
                    caption TEXT,
                    media_type TEXT,
                    file_id TEXT,
                    file_unique_id TEXT,
                    local_path TEXT,
                    has_protected_content INTEGER NOT NULL DEFAULT 0,
                    date TEXT NOT NULL,
                    edit_date TEXT,
                    is_deleted INTEGER NOT NULL DEFAULT 0,
                    raw_json TEXT,
                    PRIMARY KEY (message_id, chat_id, business_connection_id)
                );

                CREATE TABLE IF NOT EXISTS message_edits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    business_connection_id TEXT NOT NULL,
                    original_text TEXT,
                    original_caption TEXT,
                    new_text TEXT,
                    new_caption TEXT,
                    edited_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_messages_lookup
                    ON messages (message_id, chat_id, business_connection_id);

                CREATE TABLE IF NOT EXISTS chat_connections (
                    chat_id INTEGER PRIMARY KEY,
                    business_connection_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    def upsert_connection(
        self,
        connection_id: str,
        user_id: int,
        user_chat_id: int,
        is_enabled: bool,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO business_connections (id, user_id, user_chat_id, is_enabled, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    user_id = excluded.user_id,
                    user_chat_id = excluded.user_chat_id,
                    is_enabled = excluded.is_enabled,
                    updated_at = excluded.updated_at
                """,
                (connection_id, user_id, user_chat_id, int(is_enabled), now),
            )

    def get_connection(self, connection_id: str) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM business_connections WHERE id = ?",
                (connection_id,),
            ).fetchone()

    def get_primary_connection_id(self) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id FROM business_connections
                WHERE is_enabled = 1
                ORDER BY updated_at DESC
                LIMIT 1
                """
            ).fetchone()
        return row["id"] if row else None

    def bind_chat_connection(self, chat_id: int, business_connection_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_connections (chat_id, business_connection_id, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    business_connection_id = excluded.business_connection_id,
                    updated_at = excluded.updated_at
                """,
                (chat_id, business_connection_id, now),
            )

    def get_chat_connection(self, chat_id: int) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT business_connection_id FROM chat_connections WHERE chat_id = ?",
                (chat_id,),
            ).fetchone()
        return row["business_connection_id"] if row else None

    def get_active_connections(self) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT user_id, updated_at
                FROM business_connections AS bc
                WHERE is_enabled = 1
                ORDER BY updated_at DESC
                """
            ).fetchall()

    def save_message(self, data: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO messages (
                    message_id, chat_id, business_connection_id,
                    from_user_id, from_user_name, text, caption,
                    media_type, file_id, file_unique_id, local_path,
                    has_protected_content, date, edit_date, is_deleted, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                ON CONFLICT(message_id, chat_id, business_connection_id) DO UPDATE SET
                    text = excluded.text,
                    caption = excluded.caption,
                    media_type = excluded.media_type,
                    file_id = excluded.file_id,
                    file_unique_id = excluded.file_unique_id,
                    local_path = COALESCE(excluded.local_path, messages.local_path),
                    has_protected_content = excluded.has_protected_content,
                    edit_date = excluded.edit_date,
                    raw_json = excluded.raw_json
                """,
                (
                    data["message_id"],
                    data["chat_id"],
                    data["business_connection_id"],
                    data.get("from_user_id"),
                    data.get("from_user_name"),
                    data.get("text"),
                    data.get("caption"),
                    data.get("media_type"),
                    data.get("file_id"),
                    data.get("file_unique_id"),
                    data.get("local_path"),
                    int(data.get("has_protected_content", False)),
                    data["date"],
                    data.get("edit_date"),
                    data.get("raw_json"),
                ),
            )

    @staticmethod
    def _row_to_message(row: sqlite3.Row, *, is_deleted: bool | None = None) -> StoredMessage:
        return StoredMessage(
            message_id=row["message_id"],
            chat_id=row["chat_id"],
            business_connection_id=row["business_connection_id"],
            from_user_id=row["from_user_id"],
            from_user_name=row["from_user_name"],
            text=row["text"],
            caption=row["caption"],
            media_type=row["media_type"],
            file_id=row["file_id"],
            file_unique_id=row["file_unique_id"],
            local_path=row["local_path"],
            has_protected_content=bool(row["has_protected_content"]),
            date=row["date"],
            edit_date=row["edit_date"],
            is_deleted=is_deleted if is_deleted is not None else bool(row["is_deleted"]),
            raw_json=row["raw_json"] or "{}",
        )

    def get_message(
        self,
        message_id: int,
        chat_id: int,
        business_connection_id: str,
    ) -> StoredMessage | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM messages
                WHERE message_id = ? AND chat_id = ? AND business_connection_id = ?
                """,
                (message_id, chat_id, business_connection_id),
            ).fetchone()
            if row:
                return self._row_to_message(row)

            row = conn.execute(
                """
                SELECT * FROM messages
                WHERE message_id = ? AND business_connection_id = ?
                ORDER BY date DESC
                LIMIT 1
                """,
                (message_id, business_connection_id),
            ).fetchone()
        return self._row_to_message(row) if row else None

    def mark_deleted(
        self,
        message_ids: list[int],
        chat_id: int,
        business_connection_id: str,
    ) -> list[StoredMessage]:
        deleted: list[StoredMessage] = []
        with self._connect() as conn:
            for message_id in message_ids:
                row = conn.execute(
                    """
                    SELECT * FROM messages
                    WHERE message_id = ? AND business_connection_id = ?
                    ORDER BY
                        CASE WHEN chat_id = ? THEN 0 ELSE 1 END,
                        date DESC
                    LIMIT 1
                    """,
                    (message_id, business_connection_id, chat_id),
                ).fetchone()
                if not row or row["is_deleted"]:
                    continue

                conn.execute(
                    """
                    UPDATE messages SET is_deleted = 1
                    WHERE message_id = ? AND chat_id = ? AND business_connection_id = ?
                    """,
                    (row["message_id"], row["chat_id"], business_connection_id),
                )
                deleted.append(self._row_to_message(row, is_deleted=True))
        return deleted

    def save_edit(
        self,
        message_id: int,
        chat_id: int,
        business_connection_id: str,
        original_text: str | None,
        original_caption: str | None,
        new_text: str | None,
        new_caption: str | None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO message_edits (
                    message_id, chat_id, business_connection_id,
                    original_text, original_caption, new_text, new_caption, edited_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    chat_id,
                    business_connection_id,
                    original_text,
                    original_caption,
                    new_text,
                    new_caption,
                    now,
                ),
            )

    def count_totals(self) -> tuple[int, int]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COALESCE(SUM(is_deleted), 0) AS deleted
                FROM messages
                """
            ).fetchone()
        return int(row["total"] or 0), int(row["deleted"] or 0)

    @staticmethod
    def message_to_json(message: Any) -> str:
        try:
            return json.dumps(message.to_dict(), ensure_ascii=False)
        except Exception:
            return "{}"
