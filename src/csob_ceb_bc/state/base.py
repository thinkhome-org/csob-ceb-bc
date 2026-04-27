from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class StateRepository(ABC):
    @abstractmethod
    def get_profile_cursor(self, profile_key: str) -> datetime | None:
        ...

    @abstractmethod
    def set_profile_cursor(self, profile_key: str, timestamp: datetime) -> None:
        ...

    @abstractmethod
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
        ...

    @abstractmethod
    def get_upload_attempt(self, attempt_id: str) -> dict[str, Any] | None:
        ...

    @abstractmethod
    def save_upload_new_file_id(self, attempt_id: str, new_file_id: str) -> None:
        ...

    @abstractmethod
    def save_upload_finish_result(
        self, attempt_id: str, finish_status: str, ticket_id: str | None
    ) -> None:
        ...

    @abstractmethod
    def mark_idempotency_key(self, file_hash: str, attempt_id: str) -> None:
        ...

    @abstractmethod
    def get_attempt_id_by_hash(self, file_hash: str) -> str | None:
        ...

    @abstractmethod
    def create_import_protocol(
        self,
        *,
        new_file_id: str,
        upload_hash: str,
        filename: str,
        client_app_guid: str,
    ) -> None:
        ...
