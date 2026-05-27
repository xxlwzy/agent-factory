from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Literal

MessageStatus = Literal["pending", "delivered", "processed"]


@dataclass(frozen=True)
class TeamMessage:
    message_id: str
    sender: str
    receiver: str
    task_ref: str
    payload: str
    status: MessageStatus = "pending"


@dataclass
class MessageBus:
    _inboxes: dict[str, list[TeamMessage]] = field(default_factory=dict)
    _by_id: dict[str, TeamMessage] = field(default_factory=dict)

    def send(
        self,
        *,
        sender: str,
        receiver: str,
        task_ref: str,
        payload: str,
        message_id: str | None = None,
    ) -> TeamMessage:
        message = TeamMessage(
            message_id=message_id or uuid.uuid4().hex[:12],
            sender=sender,
            receiver=receiver,
            task_ref=task_ref,
            payload=payload,
            status="pending",
        )
        self._by_id[message.message_id] = message
        self._inboxes.setdefault(receiver, []).append(message)
        return message

    def receive(self, receiver: str, *, mark_delivered: bool = True) -> list[TeamMessage]:
        messages = list(self._inboxes.get(receiver, ()))
        if mark_delivered:
            delivered: list[TeamMessage] = []
            for message in messages:
                updated = TeamMessage(
                    message_id=message.message_id,
                    sender=message.sender,
                    receiver=message.receiver,
                    task_ref=message.task_ref,
                    payload=message.payload,
                    status="delivered",
                )
                self._by_id[message.message_id] = updated
                delivered.append(updated)
            self._inboxes[receiver] = delivered
            return delivered
        return messages

    def mark_processed(self, message_id: str) -> TeamMessage:
        message = self._by_id.get(message_id)
        if message is None:
            raise KeyError(f"Unknown message id: {message_id}")
        updated = TeamMessage(
            message_id=message.message_id,
            sender=message.sender,
            receiver=message.receiver,
            task_ref=message.task_ref,
            payload=message.payload,
            status="processed",
        )
        self._by_id[message_id] = updated
        inbox = self._inboxes.get(message.receiver, [])
        self._inboxes[message.receiver] = [
            updated if item.message_id == message_id else item for item in inbox
        ]
        return updated

    def get(self, message_id: str) -> TeamMessage | None:
        return self._by_id.get(message_id)
