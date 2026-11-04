"""Tests for provided consumers."""

from pyramid_customerio.consumer import BufferedConsumer
from pyramid_customerio.consumer import Endpoint
from pyramid_customerio.consumer import MockedConsumer
from testfixtures import LogCapture
from unittest import mock

import structlog
import typing as t


def test_MockedConsumer() -> None:
    """Test that MockedConsumer saves messages."""
    consumer = MockedConsumer()

    consumer.send(endpoint=Endpoint.track, msg={"foo": "Foo"})
    consumer.send(endpoint=Endpoint.identify, msg={"bar": "Bar"})

    assert consumer.mocked_messages == [
        {"endpoint": Endpoint.track, "msg": {"foo": "Foo"}},
        {"endpoint": Endpoint.identify, "msg": {"bar": "Bar"}},
    ]

    consumer.flush()
    assert consumer.flushed is True


def test_MockedConsumer_drop_system_properties() -> None:
    """Test that MockedConsumer drops system properties."""
    TRACK_MSG: t.Dict[str, t.Any] = {
        "id": "user-123",
        "name": "Page Viewed",
        "path": "/hello",
        "time": 1546300800,
    }
    IDENTIFY_MSG: t.Dict[str, t.Any] = {
        "id": "user-123",
        "email": "test@example.com",
        "time": 1546300800,
    }

    # Default behaviour - drops system properties
    consumer = MockedConsumer()
    consumer.send(endpoint=Endpoint.track, msg=TRACK_MSG)
    consumer.send(endpoint=Endpoint.identify, msg=IDENTIFY_MSG)

    assert consumer.mocked_messages == [
        {
            "endpoint": Endpoint.track,
            "msg": {
                "id": "user-123",
                "name": "Page Viewed",
                "path": "/hello",
            },
        },
        {
            "endpoint": Endpoint.identify,
            "msg": {
                "id": "user-123",
                "email": "test@example.com",
            },
        },
    ]

    # Verbose behaviour - keeps all properties
    consumer = MockedConsumer()
    consumer.DROP_SYSTEM_MESSAGE_PROPERTIES = False
    consumer.send(endpoint=Endpoint.track, msg=TRACK_MSG)
    consumer.send(endpoint=Endpoint.identify, msg=IDENTIFY_MSG)

    assert consumer.mocked_messages == [
        {
            "endpoint": Endpoint.track,
            "msg": {
                "id": "user-123",
                "name": "Page Viewed",
                "path": "/hello",
                "time": 1546300800,
            },
        },
        {
            "endpoint": Endpoint.identify,
            "msg": {
                "id": "user-123",
                "email": "test@example.com",
                "time": 1546300800,
            },
        },
    ]


@mock.patch("customerio.CustomerIO")
def test_BufferedConsumer(mock_cio: mock.MagicMock) -> None:
    """Test that BufferedConsumer sends messages to Customer.io."""
    mock_client = mock.MagicMock()
    mock_cio.return_value = mock_client

    consumer = BufferedConsumer(mock_client)

    consumer.send(
        endpoint=Endpoint.track,
        msg={"id": "user-123", "name": "Page Viewed", "path": "/hello"},
    )
    consumer.send(
        endpoint=Endpoint.identify, msg={"id": "user-123", "email": "test@example.com"}
    )

    # Messages should be buffered
    assert len(consumer.messages) == 2

    # Flush should send to Customer.io
    consumer.flush()

    mock_client.track.assert_called_once_with(
        customer_id="user-123", name="Page Viewed", path="/hello"
    )
    mock_client.identify.assert_called_once_with(
        id="user-123", email="test@example.com"
    )

    # Messages should be cleared after flush
    assert len(consumer.messages) == 0


@mock.patch("customerio.CustomerIO")
def test_BufferedConsumer_error_handling(mock_cio: mock.MagicMock) -> None:
    """Test that BufferedConsumer logs errors and continues."""
    structlog.configure(
        processors=[structlog.processors.KeyValueRenderer(sort_keys=True)],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    mock_client = mock.MagicMock()
    mock_client.track.side_effect = Exception("Connection failed")

    consumer = BufferedConsumer(mock_client, use_structlog=True)
    consumer.send(
        endpoint=Endpoint.track, msg={"id": "user-123", "name": "Page Viewed"}
    )

    with LogCapture() as logs:
        consumer.flush()

    logs.check(
        (
            "pyramid_customerio.consumer",
            "ERROR",
            "event='Failed to send to Customer.io' exc_info=True",
        )
    )

    # Test with regular logging
    consumer = BufferedConsumer(mock_client, use_structlog=False)
    consumer.send(
        endpoint=Endpoint.track, msg={"id": "user-123", "name": "Page Viewed"}
    )

    with LogCapture() as logs:
        consumer.flush()

    logs.check(
        ("pyramid_customerio.consumer", "ERROR", "Failed to send to Customer.io")
    )


@mock.patch("customerio.CustomerIO")
def test_BufferedConsumer_identify_error_handling(mock_cio: mock.MagicMock) -> None:
    """Test that BufferedConsumer logs errors for identify endpoint."""
    mock_client = mock.MagicMock()
    mock_client.identify.side_effect = Exception("Connection failed")

    consumer = BufferedConsumer(mock_client, use_structlog=False)
    consumer.send(
        endpoint=Endpoint.identify, msg={"id": "user-123", "email": "test@example.com"}
    )

    with LogCapture() as logs:
        consumer.flush()

    logs.check(
        ("pyramid_customerio.consumer", "ERROR", "Failed to send to Customer.io")
    )


@mock.patch("customerio.CustomerIO")
def test_BufferedConsumer_unknown_endpoint(mock_cio: mock.MagicMock) -> None:
    """Test that BufferedConsumer handles unknown endpoints gracefully."""
    mock_client = mock.MagicMock()
    consumer = BufferedConsumer(mock_client, use_structlog=False)

    # Manually add a message with unknown endpoint
    consumer.messages.append({"endpoint": "unknown", "msg": {"id": "user-123"}})

    # Should not raise an error, just skip the unknown endpoint
    consumer.flush()

    # No client methods should be called for unknown endpoint
    mock_client.track.assert_not_called()
    mock_client.identify.assert_not_called()


def test_consumer_protocol() -> None:
    """Test Consumer protocol methods."""
    consumer = MockedConsumer()

    # Test send method
    consumer.send(Endpoint.track, {"test": "message"})
    assert len(consumer.mocked_messages) == 1

    # Test flush method
    consumer.flush()
    assert consumer.flushed is True


@mock.patch("customerio.CustomerIO")
def test_BufferedConsumer_object(mock_cio: mock.MagicMock) -> None:
    """Test that BufferedConsumer sends object operations through the batch API."""
    mock_client = mock.MagicMock()
    consumer = BufferedConsumer(mock_client)

    operation = {
        "type": "object",
        "identifiers": {"object_type_id": "1", "object_id": "acme"},
        "action": "identify",
        "attributes": {"name": "Acme Inc."},
    }
    consumer.send(endpoint=Endpoint.entity, msg=operation)
    consumer.flush()

    mock_client.batch.assert_called_once_with([operation])
    assert len(consumer.messages) == 0
