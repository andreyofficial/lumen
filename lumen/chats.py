"""Persistent storage for AI conversations.

Conversations are kept in a single JSON document at
``$XDG_CONFIG_HOME/Lumen/Lumen/ai-chats.json``. The format is
intentionally simple so the file can be inspected, edited, or backed up
by hand:

.. code-block:: json

    {
        "version": 1,
        "active": "abcd1234",
        "chats": [
            {
                "id": "abcd1234",
                "title": "Explain decorators",
                "created_at": 1715200000,
                "updated_at": 1715200120,
                "messages": [
                    {"role": "user", "content": "What does @dataclass do?"},
                    {"role": "assistant", "content": "..."}
                ]
            }
        ]
    }

``ChatStore`` debounces writes — calling :py:meth:`mark_dirty` from a
hot path (e.g. on every streaming token) is cheap; the actual file
write happens 600ms after the last mutation, on the Qt event loop.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Iterable

from PyQt6.QtCore import QObject, QStandardPaths, QTimer, pyqtSignal


SCHEMA_VERSION = 1
_FLUSH_DELAY_MS = 600
_MAX_CHATS = 60     # cap so the file can't grow unbounded


@dataclass
class StoredMessage:
    role: str             # "user" | "assistant"
    content: str = ""


@dataclass
class StoredChat:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = "New chat"
    created_at: int = field(default_factory=lambda: int(time.time()))
    updated_at: int = field(default_factory=lambda: int(time.time()))
    messages: list[StoredMessage] = field(default_factory=list)

    def add_message(self, role: str, content: str) -> StoredMessage:
        msg = StoredMessage(role=role, content=content)
        self.messages.append(msg)
        self.updated_at = int(time.time())
        return msg

    def auto_title(self) -> str:
        """Derive a title from the first user message, capped to ~40 chars."""
        for m in self.messages:
            if m.role == "user" and m.content.strip():
                line = m.content.strip().splitlines()[0]
                return line[:40] + ("…" if len(line) > 40 else "")
        return "New chat"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["messages"] = [asdict(m) for m in self.messages]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "StoredChat":
        msgs = [
            StoredMessage(
                role=str(m.get("role", "user")),
                content=str(m.get("content", "")),
            )
            for m in (data.get("messages") or [])
        ]
        return cls(
            id=str(data.get("id") or uuid.uuid4().hex[:12]),
            title=str(data.get("title") or "New chat"),
            created_at=int(data.get("created_at") or time.time()),
            updated_at=int(data.get("updated_at") or time.time()),
            messages=msgs,
        )


class ChatStore(QObject):
    """Owns the on-disk chat history; emits when chats change."""

    chats_changed = pyqtSignal()

    def __init__(self, path: str | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._path = path or self._default_path()
        self._chats: list[StoredChat] = []
        self._active_id: str | None = None

        # Debounced writer — coalesces bursts of mutations into a single
        # disk write. Single-shot timer that we restart on every mark.
        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.setInterval(_FLUSH_DELAY_MS)
        self._flush_timer.timeout.connect(self._flush)

        self._load()

    # ---------------- Path / IO ----------------

    @staticmethod
    def _default_path() -> str:
        base = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppConfigLocation
        )
        if not base:
            base = os.path.join(
                os.path.expanduser("~"), ".config", "Lumen", "Lumen"
            )
        return os.path.join(base, "ai-chats.json")

    def path(self) -> str:
        return self._path

    def _load(self) -> None:
        if not os.path.isfile(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return
        chats_raw = data.get("chats") or []
        chats: list[StoredChat] = []
        for c in chats_raw:
            if isinstance(c, dict):
                try:
                    chats.append(StoredChat.from_dict(c))
                except Exception:
                    continue
        # Newest first.
        chats.sort(key=lambda c: c.updated_at, reverse=True)
        self._chats = chats[:_MAX_CHATS]
        self._active_id = str(data.get("active") or "") or None
        if self._active_id and self._active_id not in {c.id for c in self._chats}:
            self._active_id = None

    def _flush(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        # Atomic rename keeps the file readable even if we crash mid-write.
        tmp = self._path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "version": SCHEMA_VERSION,
                        "active": self._active_id,
                        "chats": [c.to_dict() for c in self._chats[:_MAX_CHATS]],
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            os.replace(tmp, self._path)
        except OSError:
            pass

    def mark_dirty(self) -> None:
        """Schedule a flush after the debounce delay."""
        self._flush_timer.start(_FLUSH_DELAY_MS)
        self.chats_changed.emit()

    def flush_now(self) -> None:
        """Force an immediate flush (used on app close)."""
        self._flush_timer.stop()
        self._flush()

    # ---------------- Public API ----------------

    def chats(self) -> list[StoredChat]:
        return list(self._chats)

    def active(self) -> StoredChat | None:
        if not self._chats:
            return None
        if self._active_id:
            for c in self._chats:
                if c.id == self._active_id:
                    return c
        return self._chats[0]

    def set_active(self, chat_id: str) -> None:
        if any(c.id == chat_id for c in self._chats):
            self._active_id = chat_id
            self.mark_dirty()

    def get(self, chat_id: str) -> StoredChat | None:
        for c in self._chats:
            if c.id == chat_id:
                return c
        return None

    def new_chat(self) -> StoredChat:
        chat = StoredChat()
        self._chats.insert(0, chat)
        self._active_id = chat.id
        self._chats = self._chats[:_MAX_CHATS]
        self.mark_dirty()
        return chat

    def delete(self, chat_id: str) -> None:
        self._chats = [c for c in self._chats if c.id != chat_id]
        if self._active_id == chat_id:
            self._active_id = self._chats[0].id if self._chats else None
        self.mark_dirty()

    def rename(self, chat_id: str, title: str) -> None:
        chat = self.get(chat_id)
        if not chat:
            return
        chat.title = title.strip() or "Untitled"
        chat.updated_at = int(time.time())
        self.mark_dirty()

    # ---------------- Mutators called by AIPanel ----------------

    def append_message(self, chat_id: str, role: str, content: str) -> StoredMessage | None:
        chat = self.get(chat_id)
        if not chat:
            return None
        msg = chat.add_message(role, content)
        # Auto-derive title once we have something to title from.
        if chat.title in ("New chat", "", "Untitled") and role == "user":
            chat.title = chat.auto_title()
        # Move chat to the top of the recent list.
        self._chats = [chat] + [c for c in self._chats if c.id != chat.id]
        self.mark_dirty()
        return msg

    def update_last_message(self, chat_id: str, content: str) -> None:
        chat = self.get(chat_id)
        if not chat or not chat.messages:
            return
        chat.messages[-1].content = content
        chat.updated_at = int(time.time())
        if chat.title in ("New chat", "", "Untitled"):
            chat.title = chat.auto_title()
        self.mark_dirty()

    def replace_messages(self, chat_id: str, messages: Iterable[tuple[str, str]]) -> None:
        chat = self.get(chat_id)
        if not chat:
            return
        chat.messages = [StoredMessage(role=r, content=c) for r, c in messages]
        chat.updated_at = int(time.time())
        chat.title = chat.auto_title()
        self.mark_dirty()


__all__ = [
    "ChatStore",
    "StoredChat",
    "StoredMessage",
]
