"""SQLite-backed live memory."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json
import sqlite3
import time

from .models import IncomingMessage, StoredMessage


class LiveMemory:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        self._conn.close()

    def add_message(self, message: IncomingMessage, *, role: str = "user") -> int:
        payload = json.dumps(message.raw, ensure_ascii=False) if message.raw else ""
        cursor = self._conn.execute(
            """
            INSERT INTO messages
              (platform, group_id, user_id, nickname, role, text, message_id, created_at, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message.platform,
                message.group_id,
                message.user_id,
                message.nickname,
                role,
                message.visible_text,
                message.message_id,
                message.timestamp,
                payload,
            ),
        )
        row_id = int(cursor.lastrowid)

        for image in message.images:
            self._conn.execute(
                """
                INSERT INTO message_images
                  (message_row_id, sha256, source, file_id, local_path, caption, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row_id,
                    image.sha256,
                    image.source,
                    image.file_id,
                    image.local_path,
                    image.caption,
                    message.timestamp,
                ),
            )

        self._conn.commit()
        return row_id

    def add_agent_reply(self, group_id: str, text: str, *, message_id: str = "") -> None:
        now = time.time()
        self._conn.execute(
            """
            INSERT INTO messages
              (platform, group_id, user_id, nickname, role, text, message_id, created_at, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("onebot", group_id, "agent", "agent", "agent", text, message_id, now, ""),
        )
        self._conn.commit()

    def recent_messages(self, group_id: str, limit: int = 80) -> list[StoredMessage]:
        rows = self._conn.execute(
            """
            SELECT id, group_id, user_id, nickname, role, text, created_at
            FROM messages
            WHERE group_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (group_id, limit),
        ).fetchall()
        result = [
            StoredMessage(
                row_id=int(row["id"]),
                group_id=str(row["group_id"]),
                user_id=str(row["user_id"]),
                nickname=str(row["nickname"]),
                role=str(row["role"]),
                text=str(row["text"]),
                created_at=float(row["created_at"]),
            )
            for row in rows
        ]
        return list(reversed(result))

    def get_image_caption(self, sha256: str, instruction_hash: str) -> str | None:
        row = self._conn.execute(
            """
            SELECT caption
            FROM image_captions
            WHERE sha256 = ? AND instruction_hash = ?
            """,
            (sha256, instruction_hash),
        ).fetchone()
        if not row:
            return None
        self._conn.execute(
            """
            UPDATE image_captions
            SET last_seen_at = ?, seen_count = seen_count + 1
            WHERE sha256 = ? AND instruction_hash = ?
            """,
            (time.time(), sha256, instruction_hash),
        )
        self._conn.commit()
        return str(row["caption"])

    def upsert_image_caption(
        self,
        *,
        sha256: str,
        instruction_hash: str,
        caption: str,
        model: str,
        usage: dict[str, Any] | None = None,
    ) -> None:
        now = time.time()
        usage_json = json.dumps(usage or {}, ensure_ascii=False)
        self._conn.execute(
            """
            INSERT INTO image_captions
              (sha256, instruction_hash, caption, model, usage_json, created_at, last_seen_at, seen_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(sha256, instruction_hash) DO UPDATE SET
              caption = excluded.caption,
              model = excluded.model,
              usage_json = excluded.usage_json,
              last_seen_at = excluded.last_seen_at,
              seen_count = image_captions.seen_count + 1
            """,
            (sha256, instruction_hash, caption, model, usage_json, now, now),
        )
        self._conn.commit()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS messages (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              platform TEXT NOT NULL,
              group_id TEXT NOT NULL,
              user_id TEXT NOT NULL,
              nickname TEXT NOT NULL,
              role TEXT NOT NULL,
              text TEXT NOT NULL,
              message_id TEXT NOT NULL,
              created_at REAL NOT NULL,
              raw_json TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_messages_group_id
              ON messages(group_id, id);

            CREATE TABLE IF NOT EXISTS message_images (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              message_row_id INTEGER NOT NULL,
              sha256 TEXT NOT NULL,
              source TEXT NOT NULL,
              file_id TEXT NOT NULL,
              local_path TEXT NOT NULL,
              caption TEXT NOT NULL,
              created_at REAL NOT NULL,
              FOREIGN KEY(message_row_id) REFERENCES messages(id)
            );

            CREATE TABLE IF NOT EXISTS image_captions (
              sha256 TEXT NOT NULL,
              instruction_hash TEXT NOT NULL,
              caption TEXT NOT NULL,
              model TEXT NOT NULL,
              usage_json TEXT NOT NULL,
              created_at REAL NOT NULL,
              last_seen_at REAL NOT NULL,
              seen_count INTEGER NOT NULL,
              PRIMARY KEY(sha256, instruction_hash)
            );
            """
        )
        self._conn.commit()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_instruction(instruction: str) -> str:
    return hashlib.sha256(instruction.encode("utf-8")).hexdigest()[:16]

