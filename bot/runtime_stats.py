from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class RecentEvent:
    at: float
    kind: str
    detail: str


@dataclass
class RecentMessage:
    at: float
    user_id: int | None
    chat_id: int
    name: str | None
    username: str | None
    text: str


@dataclass
class RuntimeStats:
    started_at: float = field(default_factory=time.time)
    updates: int = 0
    messages: int = 0
    media: int = 0
    deleted: int = 0
    edits: int = 0
    errors: int = 0
    connection_events: int = 0
    last_event_at: float = 0.0
    last_event_kind: str = "—"
    last_poll_at: float = 0.0
    status: str = "stopped"
    db_messages: int = 0
    db_deleted: int = 0
    recent: deque[RecentEvent] = field(default_factory=lambda: deque(maxlen=80))
    recent_messages: deque[RecentMessage] = field(default_factory=lambda: deque(maxlen=120))
    recent_errors: deque[RecentEvent] = field(default_factory=lambda: deque(maxlen=80))
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def reset_session(self) -> None:
        with self._lock:
            self.started_at = time.time()
            self.updates = 0
            self.messages = 0
            self.media = 0
            self.deleted = 0
            self.edits = 0
            self.errors = 0
            self.connection_events = 0
            self.last_event_at = 0.0
            self.last_event_kind = "—"
            self.last_poll_at = 0.0
            self.status = "starting"
            self.recent.clear()
            self.recent_messages.clear()
            self.recent_errors.clear()

    def set_status(self, status: str) -> None:
        with self._lock:
            self.status = status

    def touch_poll(self) -> None:
        with self._lock:
            self.last_poll_at = time.time()
            if self.status in {"starting", "online", "conflict"}:
                self.status = "online"

    def _touch(self, kind: str) -> None:
        self.last_event_at = time.time()
        self.last_event_kind = kind

    def _push_event(self, kind: str, detail: str) -> None:
        self._touch(kind)
        self.recent.appendleft(RecentEvent(self.last_event_at, kind, detail))

    def note_update(self, kinds: list[str]) -> None:
        with self._lock:
            self.updates += 1

    def note_message(
        self,
        *,
        user_id: int | None,
        chat_id: int,
        name: str | None,
        username: str | None = None,
        text: str,
        media_type: str | None = None,
        is_one_time: bool = False,
    ) -> None:
        body = (text or "").replace("\n", " ").strip()
        if not body:
            if media_type and is_one_time:
                body = f"[одноразовое {media_type}]"
            else:
                body = f"[{media_type}]" if media_type else "[пусто]"
        if len(body) > 160:
            body = body[:159] + "…"

        with self._lock:
            self.messages += 1
            now = time.time()
            self.recent_messages.appendleft(
                RecentMessage(
                    at=now,
                    user_id=user_id,
                    chat_id=chat_id,
                    name=name,
                    username=username,
                    text=body,
                )
            )
            who = str(user_id) if user_id is not None else "?"
            if media_type:
                label = "одноразовое медиа" if is_one_time else "медиа"
                self._push_event("save", f"{label} · {media_type} · от {who}")
            else:
                self._push_event("save", f"сообщение · от {who}")

    def note_media(self, media_type: str | None = None) -> None:
        pass
        with self._lock:
            self.media += 1

    def note_deleted(self, count: int = 1) -> None:
        if count <= 0:
            return
        with self._lock:
            self.deleted += count
            self._push_event("deleted", f"удалено {count} сообщ.")

    def note_edit(self) -> None:
        with self._lock:
            self.edits += 1
            self._push_event("edit", "правка текста")

    def note_error(self, detail: str = "error") -> None:
        text = detail.replace("\n", " ").strip()
        if len(text) > 120:
            text = text[:119] + "…"
        with self._lock:
            self.errors += 1
            self._touch("error")
            self.recent_errors.appendleft(RecentEvent(self.last_event_at, "error", text))

    def note_connection(self, enabled: bool) -> None:
        with self._lock:
            self.connection_events += 1
            self._push_event(
                "connection",
                "подключение включено" if enabled else "подключение отключено",
            )

    def set_db_totals(self, messages: int, deleted: int) -> None:
        with self._lock:
            self.db_messages = messages
            self.db_deleted = deleted

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "started_at": self.started_at,
                "updates": self.updates,
                "messages": self.messages,
                "media": self.media,
                "deleted": self.deleted,
                "edits": self.edits,
                "errors": self.errors,
                "connection_events": self.connection_events,
                "last_event_at": self.last_event_at,
                "last_event_kind": self.last_event_kind,
                "last_poll_at": self.last_poll_at,
                "status": self.status,
                "db_messages": self.db_messages,
                "db_deleted": self.db_deleted,
                "recent": list(self.recent),
                "recent_messages": list(self.recent_messages),
                "recent_errors": list(self.recent_errors),
            }


STATS = RuntimeStats()
