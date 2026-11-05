"""Tests for Customer.io tracking."""

from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from freezegun import freeze_time
from pyramid_customerio import Event
from pyramid_customerio import EventProperties
from pyramid_customerio import Events
from pyramid_customerio import ObjectProperties
from pyramid_customerio import ObjectType
from pyramid_customerio import ObjectTypes
from pyramid_customerio import ProfileMetaProperties
from pyramid_customerio import ProfileProperties
from pyramid_customerio import Property
from pyramid_customerio import RelationshipProperties
from pyramid_customerio.consumer import BufferedConsumer
from pyramid_customerio.consumer import Endpoint
from pyramid_customerio.consumer import MockedConsumer
from pyramid_customerio.track import CustomerIOTrack
from unittest import mock

import pytest
import typing as t


def test_customerio_init_distinct_id() -> None:
    """Test distinct_id is set in customerio_init function."""
    from pyramid_customerio.track import customerio_init

    # Requests without request.user
    request = mock.Mock(spec="registry headers".split())
    request.registry.settings = {}
    request.headers = {}

    result = customerio_init(request)

    assert result.__class__ == CustomerIOTrack
    assert result.distinct_id is None

    # Requests with request.user
    request = mock.Mock(spec="registry headers user".split())
    request.registry.settings = {}
    request.headers = {}
    request.user.distinct_id = "foo"

    result = customerio_init(request)

    assert result.__class__ == CustomerIOTrack
    assert result.distinct_id == "foo"


def test_init_consumers() -> None:
    """Test initialization of Consumer."""

    # default consumer (MockedConsumer when no credentials)
    customerio = CustomerIOTrack(settings={})
    assert isinstance(customerio.consumer, MockedConsumer)

    # if credentials are set, use BufferedConsumer
    with mock.patch("customerio.CustomerIO"):
        customerio = CustomerIOTrack(
            settings={
                "customerio.tracking.site_id": "site123",
                "customerio.tracking.api_key": "key123",
                "customerio.consumer": ".consumer.BufferedConsumer",
            }
        )
        assert isinstance(customerio.consumer, BufferedConsumer)

    # resolved from a dotted-name
    customerio = CustomerIOTrack(
        settings={
            "customerio.consumer": "pyramid_customerio.consumer.MockedConsumer",
        }
    )
    assert isinstance(customerio.consumer, MockedConsumer)


@dataclass(frozen=True)
class FooEvents(Events):
    foo: Event = Event("Foo")


@dataclass(frozen=True)
class FooEventProperties(EventProperties):
    foo: Property = Property("foo")


@dataclass(frozen=True)
class FooProfileProperties(ProfileProperties):
    foo: Property = Property("foo")


@dataclass(frozen=True)
class FooProfileMetaProperties(ProfileMetaProperties):
    foo: Property = Property("foo")


def test_init_events() -> None:
    """Test initialization of Events."""

    # default events
    customerio = CustomerIOTrack(settings={})
    assert isinstance(customerio.events, Events)

    # resolved from a dotted-name
    customerio = CustomerIOTrack(
        settings={
            "customerio.events": "pyramid_customerio.tests.test_track.FooEvents",
        }
    )
    assert isinstance(customerio.events, FooEvents)


def test_init_event_properties() -> None:
    """Test initialization of EventProperties."""

    # default event properties
    customerio = CustomerIOTrack(settings={})
    assert isinstance(customerio.event_properties, EventProperties)

    # resolved from a dotted-name
    customerio = CustomerIOTrack(
        settings={
            "customerio.event_properties": "pyramid_customerio.tests.test_track.FooEventProperties",
        }
    )
    assert isinstance(customerio.event_properties, FooEventProperties)


def test_init_profile_properties() -> None:
    """Test initialization of ProfileProperties."""

    # default profile properties
    customerio = CustomerIOTrack(settings={})
    assert isinstance(customerio.profile_properties, ProfileProperties)

    # resolved from a dotted-name
    customerio = CustomerIOTrack(
        settings={
            "customerio.profile_properties": "pyramid_customerio.tests.test_track.FooProfileProperties",
        }
    )
    assert isinstance(customerio.profile_properties, FooProfileProperties)


def test_init_profile_meta_properties() -> None:
    """Test initialization of ProfileMetaProperties."""

    # default profile meta properties
    customerio = CustomerIOTrack(settings={})
    assert isinstance(customerio.profile_meta_properties, ProfileMetaProperties)

    # resolved from a dotted-name
    customerio = CustomerIOTrack(
        settings={
            "customerio.profile_meta_properties": "pyramid_customerio.tests.test_track.FooProfileMetaProperties",
        }
    )
    assert isinstance(customerio.profile_meta_properties, FooProfileMetaProperties)


def test_track_event() -> None:
    """Test tracking events."""
    customerio = CustomerIOTrack(settings={}, distinct_id="foo-123")

    customerio.track(customerio.events.page_viewed)

    assert isinstance(customerio.consumer, MockedConsumer)
    assert customerio.consumer.mocked_messages == [
        {
            "endpoint": Endpoint.track,
            "msg": {
                "id": "foo-123",
                "name": "Page Viewed",
            },
        }
    ]


def test_track_event_with_properties() -> None:
    """Test tracking events with properties."""
    customerio = CustomerIOTrack(settings={}, distinct_id="foo-123")

    customerio.track(
        customerio.events.page_viewed,
        {
            customerio.event_properties.title: "Hello World",
            customerio.event_properties.path: "/hello",
        },
    )

    assert isinstance(customerio.consumer, MockedConsumer)
    assert customerio.consumer.mocked_messages == [
        {
            "endpoint": Endpoint.track,
            "msg": {
                "id": "foo-123",
                "name": "Page Viewed",
                "Title": "Hello World",
                "Path": "/hello",
            },
        }
    ]


@freeze_time("2019-01-01 00:00:00")
def test_track_event_with_datetime_properties() -> None:
    """Test tracking events with datetime properties."""
    customerio = CustomerIOTrack(settings={}, distinct_id="foo-123")

    dt = datetime(2019, 1, 1, 0, 0, 0)
    customerio.track(
        customerio.events.page_viewed,
        {customerio.event_properties.title: dt},
    )

    assert isinstance(customerio.consumer, MockedConsumer)
    assert customerio.consumer.mocked_messages == [
        {
            "endpoint": Endpoint.track,
            "msg": {
                "id": "foo-123",
                "name": "Page Viewed",
                "Title": 1546300800,  # Unix timestamp
            },
        }
    ]


def test_track_event_validation() -> None:
    """Test event validation."""
    customerio = CustomerIOTrack(settings={}, distinct_id="foo-123")

    # Invalid event
    with pytest.raises(
        ValueError, match="Event 'Invalid' must be a member of self.events"
    ):
        customerio.track(Event("Invalid"))

    # Invalid property
    with pytest.raises(
        ValueError, match="Property 'invalid' is not a member of self.event_properties"
    ):
        customerio.track(customerio.events.page_viewed, {Property("invalid"): "value"})


def test_track_event_requires_distinct_id() -> None:
    """Test that tracking requires distinct_id."""
    customerio = CustomerIOTrack(settings={})

    with pytest.raises(ValueError, match="self.distinct_id not set"):
        customerio.track(customerio.events.page_viewed)


def test_identify_user() -> None:
    """Test identifying users."""
    customerio = CustomerIOTrack(settings={}, distinct_id="foo-123")

    customerio.identify(
        {
            customerio.profile_properties.email: "test@example.com",
            customerio.profile_properties.name: "John Doe",
        }
    )

    assert isinstance(customerio.consumer, MockedConsumer)
    assert customerio.consumer.mocked_messages == [
        {
            "endpoint": Endpoint.identify,
            "msg": {
                "id": "foo-123",
                "email": "test@example.com",
                "name": "John Doe",
            },
        }
    ]


@freeze_time("2019-01-01 00:00:00")
def test_identify_user_with_datetime() -> None:
    """Test identifying users with datetime properties."""
    customerio = CustomerIOTrack(settings={}, distinct_id="foo-123")

    dt = datetime(2019, 1, 1, 0, 0, 0)
    customerio.identify(
        {
            customerio.profile_properties.created_at: dt,
            customerio.profile_properties.email: "test@example.com",
        }
    )

    assert isinstance(customerio.consumer, MockedConsumer)
    assert customerio.consumer.mocked_messages == [
        {
            "endpoint": Endpoint.identify,
            "msg": {
                "id": "foo-123",
                "created_at": 1546300800,  # Unix timestamp
                "email": "test@example.com",
            },
        }
    ]


def test_identify_user_with_meta() -> None:
    """Test identifying users with meta properties."""
    customerio = CustomerIOTrack(settings={}, distinct_id="foo-123")

    customerio.identify(
        {customerio.profile_properties.email: "test@example.com"},
        {customerio.profile_meta_properties.ip: "192.168.1.1"},
    )

    assert isinstance(customerio.consumer, MockedConsumer)
    assert customerio.consumer.mocked_messages == [
        {
            "endpoint": Endpoint.identify,
            "msg": {
                "id": "foo-123",
                "email": "test@example.com",
                "ip": "192.168.1.1",
            },
        }
    ]


def test_identify_user_validation() -> None:
    """Test user identification validation."""
    customerio = CustomerIOTrack(settings={}, distinct_id="foo-123")

    # Invalid property
    with pytest.raises(
        ValueError,
        match="Property 'invalid' is not a member of self.profile_properties",
    ):
        customerio.identify({Property("invalid"): "value"})

    # Invalid meta property
    with pytest.raises(
        ValueError,
        match="Property 'invalid' is not a member of self.profile_meta_properties",
    ):
        customerio.identify(
            {customerio.profile_properties.email: "test@example.com"},
            {Property("invalid"): "value"},
        )


def test_identify_user_requires_distinct_id() -> None:
    """Test that identification requires distinct_id."""
    customerio = CustomerIOTrack(settings={})

    with pytest.raises(ValueError, match="self.distinct_id not set"):
        customerio.identify({customerio.profile_properties.email: "test@example.com"})


def test_init_unknown_consumer() -> None:
    """Test initialization with unknown consumer."""
    with pytest.raises(ValueError, match="Unknown consumer: .UnknownConsumer"):
        CustomerIOTrack(settings={"customerio.consumer": ".UnknownConsumer"})


def test_init_unknown_events() -> None:
    """Test initialization with unknown events."""
    with pytest.raises(ValueError, match="Unknown events: .UnknownEvents"):
        CustomerIOTrack(settings={"customerio.events": ".UnknownEvents"})


def test_init_unknown_event_properties() -> None:
    """Test initialization with unknown event properties."""
    with pytest.raises(
        ValueError, match="Unknown event_properties: .UnknownEventProperties"
    ):
        CustomerIOTrack(
            settings={"customerio.event_properties": ".UnknownEventProperties"}
        )


def test_init_unknown_profile_properties() -> None:
    """Test initialization with unknown profile properties."""
    with pytest.raises(
        ValueError, match="Unknown profile_properties: .UnknownProfileProperties"
    ):
        CustomerIOTrack(
            settings={"customerio.profile_properties": ".UnknownProfileProperties"}
        )


def test_init_unknown_profile_meta_properties() -> None:
    """Test initialization with unknown profile meta properties."""
    with pytest.raises(
        ValueError,
        match="Unknown profile_meta_properties: .UnknownProfileMetaProperties",
    ):
        CustomerIOTrack(
            settings={
                "customerio.profile_meta_properties": ".UnknownProfileMetaProperties"
            }
        )


def test_init_with_custom_classes() -> None:
    """Test initialization with custom class instances."""
    custom_consumer = MockedConsumer()
    custom_events = Events()
    custom_event_properties = EventProperties()
    custom_profile_properties = ProfileProperties()
    custom_profile_meta_properties = ProfileMetaProperties()

    customerio = CustomerIOTrack(settings={}, distinct_id="test-id")
    customerio.consumer = custom_consumer
    customerio.events = custom_events
    customerio.event_properties = custom_event_properties
    customerio.profile_properties = custom_profile_properties
    customerio.profile_meta_properties = custom_profile_meta_properties

    assert customerio.consumer is custom_consumer
    assert customerio.events is custom_events
    assert customerio.event_properties is custom_event_properties
    assert customerio.profile_properties is custom_profile_properties
    assert customerio.profile_meta_properties is custom_profile_meta_properties


def test_init_with_object_instances() -> None:
    """Test initialization by passing object instances directly in settings."""
    custom_consumer = MockedConsumer()
    custom_events = Events()
    custom_event_properties = EventProperties()
    custom_profile_properties = ProfileProperties()
    custom_profile_meta_properties = ProfileMetaProperties()

    # Pass objects directly instead of strings
    customerio = CustomerIOTrack(
        settings={
            "customerio.consumer": custom_consumer,
            "customerio.events": custom_events,
            "customerio.event_properties": custom_event_properties,
            "customerio.profile_properties": custom_profile_properties,
            "customerio.profile_meta_properties": custom_profile_meta_properties,
        },
        distinct_id="test-id",
    )

    # Verify objects are used directly (not string-resolved)
    assert customerio.consumer is custom_consumer
    assert customerio.events is custom_events
    assert customerio.event_properties is custom_event_properties
    assert customerio.profile_properties is custom_profile_properties
    assert customerio.profile_meta_properties is custom_profile_meta_properties


def test_track_event_with_restricted_properties() -> None:
    """Test tracking event with restricted properties."""
    import typing as t

    @dataclass(frozen=True)
    class RestrictedEvent:
        name: str
        properties: t.Optional[t.List[Property]] = None

    @dataclass(frozen=True)
    class CustomEventProperties(EventProperties):
        allowed: Property = Property("allowed")

    @dataclass(frozen=True)
    class RestrictedEvents:
        restricted: RestrictedEvent = RestrictedEvent(
            "Restricted Event", [Property("allowed")]
        )

    customerio = CustomerIOTrack(settings={}, distinct_id="foo-123")
    customerio.events = RestrictedEvents()
    customerio.event_properties = CustomEventProperties()

    # Should work with allowed property
    customerio.track(
        customerio.events.restricted, {customerio.event_properties.allowed: "value"}
    )

    # Should fail with disallowed property
    with pytest.raises(
        ValueError, match="Property '.*' must be a member of Event.properties"
    ):
        customerio.track(
            customerio.events.restricted, {customerio.event_properties.title: "value"}
        )


def test_init_buffered_consumer_import_error() -> None:
    """Test BufferedConsumer initialization when customerio package not installed."""
    with mock.patch.dict("sys.modules", {"customerio": None}):
        with pytest.raises(ImportError, match="customerio package is not installed"):
            CustomerIOTrack(
                settings={
                    "customerio.consumer": ".consumer.BufferedConsumer",
                    "customerio.tracking.site_id": "site123",
                    "customerio.tracking.api_key": "key123",
                }
            )


def test_init_buffered_consumer_with_region() -> None:
    """Test BufferedConsumer initialization with custom region."""
    from customerio import Regions

    with mock.patch("customerio.CustomerIO") as mock_cio:
        CustomerIOTrack(
            settings={
                "customerio.consumer": ".consumer.BufferedConsumer",
                "customerio.tracking.site_id": "site123",
                "customerio.tracking.api_key": "key123",
                "customerio.tracking.region": "eu",
            }
        )
        mock_cio.assert_called_once_with(
            site_id="site123", api_key="key123", region=Regions.EU
        )


def test_init_buffered_consumer_with_invalid_region() -> None:
    """Test BufferedConsumer initialization with invalid region raises error."""
    import pytest

    with pytest.raises(
        ValueError, match="Unsupported region 'invalid'. Valid regions are: 'us', 'eu'"
    ):
        CustomerIOTrack(
            settings={
                "customerio.consumer": ".consumer.BufferedConsumer",
                "customerio.tracking.site_id": "site123",
                "customerio.tracking.api_key": "key123",
                "customerio.tracking.region": "invalid",
            }
        )


def test_flush_callback() -> None:
    """Test that flush callback is properly registered."""
    from pyramid_customerio.track import customerio_flush

    # Mock event and request
    request = mock.Mock(spec=[])
    response = mock.Mock()

    # Mock customerio with consumer
    customerio = mock.Mock()
    request.customerio = customerio
    request.add_response_callback = mock.Mock()

    event = mock.Mock()
    event.request = request

    # Call flush registration
    customerio_flush(event)

    # Verify callback was registered
    request.add_response_callback.assert_called_once()

    # Get the callback function and call it
    flush_callback = request.add_response_callback.call_args[0][0]
    flush_callback(request, response)

    # Verify consumer.flush was called
    customerio.consumer.flush.assert_called_once()


def test_flush_callback_no_customerio() -> None:
    """Test flush callback when customerio was never accessed."""
    from pyramid_customerio.track import customerio_flush

    # Mock event and request without customerio
    request = mock.Mock(spec=[])
    response = mock.Mock()

    # No customerio attribute
    request.add_response_callback = mock.Mock()

    event = mock.Mock()
    event.request = request

    # Call flush registration
    customerio_flush(event)

    # Get the callback function and call it
    flush_callback = request.add_response_callback.call_args[0][0]
    flush_callback(request, response)

    # Should not raise an error


@dataclass(frozen=True)
class FooObjectProperties(ObjectProperties):
    plan: Property = Property("plan")


@dataclass(frozen=True)
class FooRelationshipProperties(RelationshipProperties):
    role: Property = Property("role")


@dataclass(frozen=True)
class FooObjectTypes(ObjectTypes):
    company: ObjectType = ObjectType("1")
    team: ObjectType = ObjectType("2", properties=[ObjectProperties.name])


OBJECT_SETTINGS = {
    "customerio.object_types": "pyramid_customerio.tests.test_track.FooObjectTypes",
    "customerio.object_properties": "pyramid_customerio.tests.test_track.FooObjectProperties",
    "customerio.relationship_properties": "pyramid_customerio.tests.test_track.FooRelationshipProperties",
}


def test_init_object_types() -> None:
    """Test initialization of ObjectTypes."""

    # default object types
    customerio = CustomerIOTrack(settings={})
    assert isinstance(customerio.object_types, ObjectTypes)

    # resolved from a dotted-name
    customerio = CustomerIOTrack(settings=OBJECT_SETTINGS)
    assert isinstance(customerio.object_types, FooObjectTypes)


def test_init_object_properties() -> None:
    """Test initialization of ObjectProperties."""

    # default object properties
    customerio = CustomerIOTrack(settings={})
    assert isinstance(customerio.object_properties, ObjectProperties)

    # resolved from a dotted-name
    customerio = CustomerIOTrack(settings=OBJECT_SETTINGS)
    assert isinstance(customerio.object_properties, FooObjectProperties)


def test_init_relationship_properties() -> None:
    """Test initialization of RelationshipProperties."""

    # default relationship properties
    customerio = CustomerIOTrack(settings={})
    assert isinstance(customerio.relationship_properties, RelationshipProperties)

    # resolved from a dotted-name
    customerio = CustomerIOTrack(settings=OBJECT_SETTINGS)
    assert isinstance(customerio.relationship_properties, FooRelationshipProperties)


def test_init_unknown_object_types() -> None:
    """Test initialization with unknown object types."""
    with pytest.raises(ValueError, match="Unknown object_types: .UnknownObjectTypes"):
        CustomerIOTrack(settings={"customerio.object_types": ".UnknownObjectTypes"})


def test_init_unknown_object_properties() -> None:
    """Test initialization with unknown object properties."""
    with pytest.raises(
        ValueError, match="Unknown object_properties: .UnknownObjectProperties"
    ):
        CustomerIOTrack(
            settings={"customerio.object_properties": ".UnknownObjectProperties"}
        )


def test_init_unknown_relationship_properties() -> None:
    """Test initialization with unknown relationship properties."""
    with pytest.raises(
        ValueError,
        match="Unknown relationship_properties: .UnknownRelationshipProperties",
    ):
        CustomerIOTrack(
            settings={
                "customerio.relationship_properties": ".UnknownRelationshipProperties"
            }
        )


def test_init_with_object_instances_for_objects() -> None:
    """Test initialization with object instances for the object settings."""
    object_types = FooObjectTypes()
    object_properties = FooObjectProperties()
    relationship_properties = FooRelationshipProperties()

    customerio = CustomerIOTrack(
        settings={
            "customerio.object_types": object_types,
            "customerio.object_properties": object_properties,
            "customerio.relationship_properties": relationship_properties,
        }
    )

    assert customerio.object_types is object_types
    assert customerio.object_properties is object_properties
    assert customerio.relationship_properties is relationship_properties


def test_identify_object() -> None:
    """Test creating or updating an object, with dates as timestamps."""
    customerio = CustomerIOTrack(settings=OBJECT_SETTINGS)
    object_types = t.cast(FooObjectTypes, customerio.object_types)
    object_properties = t.cast(FooObjectProperties, customerio.object_properties)

    customerio.identify_object(
        object_types.company,
        "acme",
        {
            object_properties.name: "Acme Inc.",
            object_properties.created_at: datetime(2019, 1, 1, tzinfo=timezone.utc),
            object_properties.plan: "pro",
        },
    )

    consumer = t.cast(MockedConsumer, customerio.consumer)
    assert consumer.mocked_messages == [
        {
            "endpoint": Endpoint.entity,
            "msg": {
                "type": "object",
                "identifiers": {"object_type_id": "1", "object_id": "acme"},
                "action": "identify",
                "attributes": {
                    "name": "Acme Inc.",
                    "created_at": 1546300800,
                    "plan": "pro",
                },
            },
        }
    ]


def test_identify_object_with_relationships() -> None:
    """Test relating people to an object, with and without properties."""
    customerio = CustomerIOTrack(settings=OBJECT_SETTINGS)
    object_types = t.cast(FooObjectTypes, customerio.object_types)
    object_properties = t.cast(FooObjectProperties, customerio.object_properties)
    relationship_properties = t.cast(
        FooRelationshipProperties, customerio.relationship_properties
    )

    customerio.identify_object(
        object_types.company,
        "acme",
        {object_properties.name: "Acme Inc."},
        relationships={
            "user-1": {relationship_properties.role: "admin"},
            "user-2": {},
        },
    )

    consumer = t.cast(MockedConsumer, customerio.consumer)
    assert consumer.mocked_messages == [
        {
            "endpoint": Endpoint.entity,
            "msg": {
                "type": "object",
                "identifiers": {"object_type_id": "1", "object_id": "acme"},
                "action": "identify",
                "attributes": {"name": "Acme Inc."},
                "cio_relationships": [
                    {
                        "identifiers": {"id": "user-1"},
                        "relationship_attributes": {"role": "admin"},
                    },
                    {"identifiers": {"id": "user-2"}},
                ],
            },
        }
    ]


def test_identify_object_validation() -> None:
    """Test identify_object rejects unknown types and properties."""
    customerio = CustomerIOTrack(settings=OBJECT_SETTINGS)
    object_types = t.cast(FooObjectTypes, customerio.object_types)
    object_properties = t.cast(FooObjectProperties, customerio.object_properties)

    # unknown object type
    with pytest.raises(
        ValueError, match="Object type '9' must be a member of self.object_types"
    ):
        customerio.identify_object(ObjectType("9"), "acme", {})

    # unknown object property
    with pytest.raises(
        ValueError, match="Property 'foo' is not a member of self.object_properties"
    ):
        customerio.identify_object(
            object_types.company, "acme", {Property("foo"): "bar"}
        )

    # property not allowed on this object type
    with pytest.raises(
        ValueError,
        match="must be a member of ObjectType.properties",
    ):
        customerio.identify_object(
            object_types.team, "devs", {object_properties.plan: "pro"}
        )

    # unknown relationship property
    with pytest.raises(
        ValueError,
        match="Property 'foo' is not a member of self.relationship_properties",
    ):
        customerio.identify_object(
            object_types.company,
            "acme",
            {},
            relationships={"user-1": {Property("foo"): "bar"}},
        )

    consumer = t.cast(MockedConsumer, customerio.consumer)
    assert consumer.mocked_messages == []


def test_identify_object_does_not_require_distinct_id() -> None:
    """Objects are not tied to the current user, so no distinct_id is needed."""
    customerio = CustomerIOTrack(settings=OBJECT_SETTINGS, distinct_id=None)
    object_types = t.cast(FooObjectTypes, customerio.object_types)

    customerio.identify_object(object_types.company, "acme", {})

    consumer = t.cast(MockedConsumer, customerio.consumer)
    assert len(consumer.mocked_messages) == 1


def test_delete_object() -> None:
    """Test deleting an object."""
    customerio = CustomerIOTrack(settings=OBJECT_SETTINGS)
    object_types = t.cast(FooObjectTypes, customerio.object_types)

    customerio.delete_object(object_types.company, "acme")

    consumer = t.cast(MockedConsumer, customerio.consumer)
    assert consumer.mocked_messages == [
        {
            "endpoint": Endpoint.entity,
            "msg": {
                "type": "object",
                "identifiers": {"object_type_id": "1", "object_id": "acme"},
                "action": "delete",
            },
        }
    ]

    with pytest.raises(ValueError, match="must be a member of self.object_types"):
        customerio.delete_object(ObjectType("9"), "acme")


def test_delete_object_relationships() -> None:
    """Test unrelating people from an object."""
    customerio = CustomerIOTrack(settings=OBJECT_SETTINGS)
    object_types = t.cast(FooObjectTypes, customerio.object_types)

    customerio.delete_object_relationships(
        object_types.company, "acme", ["user-1", "user-2"]
    )

    consumer = t.cast(MockedConsumer, customerio.consumer)
    assert consumer.mocked_messages == [
        {
            "endpoint": Endpoint.entity,
            "msg": {
                "type": "object",
                "identifiers": {"object_type_id": "1", "object_id": "acme"},
                "action": "delete_relationships",
                "cio_relationships": [
                    {"identifiers": {"id": "user-1"}},
                    {"identifiers": {"id": "user-2"}},
                ],
            },
        }
    ]

    with pytest.raises(ValueError, match="must be a member of self.object_types"):
        customerio.delete_object_relationships(ObjectType("9"), "acme", ["user-1"])


def test_identify_object_with_restricted_properties() -> None:
    """Test identify_object accepts a property the object type allows."""
    customerio = CustomerIOTrack(settings=OBJECT_SETTINGS)
    object_types = t.cast(FooObjectTypes, customerio.object_types)
    object_properties = t.cast(FooObjectProperties, customerio.object_properties)

    customerio.identify_object(
        object_types.team, "devs", {object_properties.name: "Developers"}
    )

    consumer = t.cast(MockedConsumer, customerio.consumer)
    assert consumer.mocked_messages[0]["msg"]["attributes"] == {"name": "Developers"}
