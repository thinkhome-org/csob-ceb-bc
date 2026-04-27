from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from csob_ceb_bc.state.base import StateRepository


class SqliteStateRepository(StateRepository):
    def __init__(self, state_url: str) -> None:
        # Accept sqlite:///path or file path directly
        if state_url.startswith("sqlite:///"):
            self._db_path = state_url[len("sqlite:///") :]
        else:
            self._db_path = state_url
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, isolation_level=None)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        with self._connect() as conn:
            conn.executescript(schema_path.read_text())

    def get_profile_cursor(self, profile_key: str) -> datetime | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT last_query_timestamp FROM profiles WHERE profile_key = ?",
                (profile_key,),
            ).fetchone()
        if row is None or row["last_query_timestamp"] is None:
            return None
        return datetime.fromisoformat(row["last_query_timestamp"])

    def set_profile_cursor(self, profile_key: str, timestamp: datetime) -> None:
        ts_str = timestamp.isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO profiles(profile_key, last_query_timestamp)
                   VALUES(?, ?)
                   ON CONFLICT(profile_key) DO UPDATE SET
                     last_query_timestamp = excluded.last_query_timestamp""",
                (profile_key, ts_str),
            )

    def create_upload_attempt(
        self,
        *,
        attempt_id: str,
        filename: str,
        file_hash: str,
        size: int,
        file_format: str,
        mode: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO upload_attempts
                   (attempt_id, filename, file_hash, size, file_format, mode, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (attempt_id, filename, file_hash, size, file_format, mode, "started"),
            )

    def get_upload_attempt(self, attempt_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM upload_attempts WHERE attempt_id = ?",
                (attempt_id,),
            ).fetchone()
        if row is None:
            return None
        d = dict(row)
        # enrich with rest result if present
        with self._connect() as conn:
            rest = conn.execute(
                "SELECT new_file_id FROM upload_rest_results WHERE attempt_id = ? ORDER BY id DESC LIMIT 1",
                (attempt_id,),
            ).fetchone()
        if rest:
            d["new_file_id"] = rest["new_file_id"]
        return d

    def save_upload_new_file_id(self, attempt_id: str, new_file_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO upload_rest_results (attempt_id, new_file_id)
                   VALUES (?, ?)""",
                (attempt_id, new_file_id),
            )
            conn.execute(
                "UPDATE upload_attempts SET status = ? WHERE attempt_id = ?",
                ("rest_done", attempt_id),
            )

    def save_upload_finish_result(
        self, attempt_id: str, finish_status: str, ticket_id: str | None
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO upload_finish_results (attempt_id, finish_status, ticket_id)
                   VALUES (?, ?, ?)""",
                (attempt_id, finish_status, ticket_id),
            )
            conn.execute(
                "UPDATE upload_attempts SET status = ? WHERE attempt_id = ?",
                (f"finish_{finish_status}", attempt_id),
            )

    def mark_idempotency_key(self, file_hash: str, attempt_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO idempotency_keys (file_hash, attempt_id)
                   VALUES (?, ?)
                   ON CONFLICT(file_hash) DO NOTHING""",
                (file_hash, attempt_id),
            )

    def get_attempt_id_by_hash(self, file_hash: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT attempt_id FROM idempotency_keys WHERE file_hash = ?",
                (file_hash,),
            ).fetchone()
        return row["attempt_id"] if row else None

    def create_import_protocol(
        self,
        *,
        new_file_id: str,
        upload_hash: str,
        filename: str,
        client_app_guid: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO import_protocols
                   (new_file_id, upload_hash, filename, client_app_guid)
                   VALUES (?, ?, ?, ?)""",
                (new_file_id, upload_hash, filename, client_app_guid),
            )
