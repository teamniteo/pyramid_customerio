"""Consumers send events/profiles messages to Customer.io's HTTP API."""

from dataclasses import dataclass
from dataclasses import field
from enum import auto
from enum import StrEnum
from typing import Protocol

import typing as t


class Endpoint(StrEnum):
    """Customer.io API endpoints."""

    track = auto()
    identify = auto()
    # Objects go to the v2 entity API through its batch call, since the
    # customerio package has no single-entity method
    entity = auto()


class Consumer(Protocol):
    """Protocol for Customer.io consumers."""

    def send(self, endpoint: Endpoint, msg: t.Dict[str, t.Any]) -> None:
        """Send a message to the consumer."""
        ...  # pragma: no cover

    def flush(self, *args: t.Any, **kwargs: t.Any) -> None:
        """Flush any buffered messages."""
        ...  # pragma: no cover


@dataclass
class MockedConsumer:
    """Save messages in an internal list, useful in unit testing."""

    # Internal storage of mocked message
    mocked_messages: t.List[t.Dict[str, t.Any]] = field(default_factory=list)

    # Drop message properties that are usually not needed in testing
    DROP_SYSTEM_MESSAGE_PROPERTIES: bool = True

    # True if .flush() was called
    flushed: bool = False

    def send(self, endpoint: Endpoint, msg: t.Dict[str, t.Any]) -> None:
        """Append message to the mocked_messages list."""
        message = {
            "endpoint": endpoint,
            "msg": msg.copy(),
        }

        if self.DROP_SYSTEM_MESSAGE_PROPERTIES:
            # Remove system properties that are not useful in tests
            msg_dict = t.cast(t.Dict[str, t.Any], message["msg"])
            if endpoint == Endpoint.track and "time" in msg_dict:
                msg_dict.pop("time", None)
            elif endpoint == Endpoint.identify and "time" in msg_dict:
                msg_dict.pop("time", None)

        self.mocked_messages.append(message)

    def flush(self, *args: t.Any, **kwargs: t.Any) -> None:
        """Set self.flushed to True."""
        self.flushed = True


class BufferedConsumer:
    """Send messages to Customer.io with buffering and error handling.

    This consumer buffers messages and sends them when flush() is called.
    Network errors are logged but don't raise exceptions.
    """

    def __init__(
        self, cio_client: t.Any, use_structlog: t.Optional[bool] = False
    ) -> None:
        """Initialize BufferedConsumer with Customer.io client."""
        self.client = cio_client
        self.use_structlog = use_structlog
        self.messages: t.List[t.Dict[str, t.Any]] = []

    def send(self, endpoint: Endpoint, msg: t.Dict[str, t.Any]) -> None:
        """Buffer message for sending."""
        self.messages.append({"endpoint": endpoint, "msg": msg})

    def flush(self, *args: t.Any, **kwargs: t.Any) -> None:
        """Send all buffered messages to Customer.io."""
        for message in self.messages:
            endpoint = message["endpoint"]
            msg = message["msg"].copy()

            try:
                if endpoint == Endpoint.track:
                    # Extract customer_id and event data
                    customer_id = msg.pop("id")
                    event_name = msg.pop("name")
                    self.client.track(customer_id=customer_id, name=event_name, **msg)
                elif endpoint == Endpoint.identify:
                    # Extract customer_id and attributes
                    customer_id = msg.pop("id")
                    self.client.identify(id=customer_id, **msg)
                elif endpoint == Endpoint.entity:
                    # The message is a ready-made Track API v2 operation
                    self.client.batch([msg])
            except Exception:
                if self.use_structlog:
                    import structlog

                    logger = structlog.get_logger(__name__)
                    logger.exception("Failed to send to Customer.io", exc_info=True)
                else:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.exception("Failed to send to Customer.io", exc_info=True)

        self.messages.clear()
