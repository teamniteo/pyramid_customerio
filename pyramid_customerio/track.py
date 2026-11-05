"""Track events to Customer.io."""

from datetime import datetime
from functools import wraps
from pyramid.events import NewRequest
from pyramid.request import Request
from pyramid.response import Response
from pyramid.settings import asbool
from pyramid_customerio import Event
from pyramid_customerio import EventProperties
from pyramid_customerio import Events
from pyramid_customerio import ObjectProperties
from pyramid_customerio import ObjectType
from pyramid_customerio import ObjectTypes
from pyramid_customerio import ProfileMetaProperties
from pyramid_customerio import ProfileProperties
from pyramid_customerio import PropertiesType
from pyramid_customerio import RelationshipProperties
from pyramid_customerio import RelationshipsType
from pyramid_customerio.consumer import BufferedConsumer
from pyramid_customerio.consumer import Consumer
from pyramid_customerio.consumer import Endpoint
from pyramid_customerio.consumer import MockedConsumer

import typing as t


def distinct_id_is_required(func: t.Callable) -> t.Callable:
    """Check if distinct_id is set before calling the wrapped function."""

    @wraps(func)
    def wrapper(instance: "CustomerIOTrack", *args: t.Any, **kwargs: t.Any) -> t.Any:
        """Check if distinct_id is set before calling the wrapped function."""
        if not instance.distinct_id:
            raise ValueError(
                "self.distinct_id not set. Pass it to __init__() or set it manually."
            )
        return func(instance, *args, **kwargs)

    return wrapper


class CustomerIOTrack:
    """Track events and update profiles in Customer.io."""

    def __init__(
        self,
        settings: t.Dict[str, t.Any],
        distinct_id: t.Optional[str] = None,
    ) -> None:
        """Configure Customer.io tracking."""
        # Consumer is what connects to Customer.io's HTTP API
        consumer: t.Union[str, t.Any] = settings.get(
            "customerio.consumer", ".consumer.MockedConsumer"
        )
        if isinstance(consumer, str):
            if not consumer.startswith("."):
                consumer = self._resolve_class(consumer)()
            elif consumer == ".consumer.MockedConsumer":
                consumer = MockedConsumer()
            elif consumer == ".consumer.BufferedConsumer":
                # Initialize Customer.io client
                try:
                    from customerio import CustomerIO
                    from customerio import Regions
                except ImportError:
                    raise ImportError(
                        "customerio package is not installed. "
                        "Install it with: pip install customerio"
                    )

                site_id = settings.get("customerio.tracking.site_id")
                api_key = settings.get("customerio.tracking.api_key")
                region = settings.get("customerio.tracking.region", "us")

                if not site_id or not api_key:
                    # Fall back to MockedConsumer if credentials are missing
                    consumer = MockedConsumer()
                else:
                    # Convert string region to Regions enum
                    if region == "us":
                        region_enum = Regions.US
                    elif region == "eu":
                        region_enum = Regions.EU
                    else:
                        raise ValueError(
                            f"Unsupported region '{region}'. Valid regions are: 'us', 'eu'"
                        )

                    cio_client = CustomerIO(
                        site_id=site_id, api_key=api_key, region=region_enum
                    )
                    use_structlog = asbool(
                        settings.get("pyramid_heroku.structlog", False)
                    )
                    consumer = BufferedConsumer(cio_client, use_structlog)
            else:
                raise ValueError(f"Unknown consumer: {consumer}")
        self.consumer: Consumer = consumer

        # Events
        events = settings.get("customerio.events", ".Events")
        if isinstance(events, str):
            if not events.startswith("."):
                self.events = self._resolve_class(events)()
            elif events == ".Events":
                self.events = Events()
            else:
                raise ValueError(f"Unknown events: {events}")
        else:
            self.events = events

        # Event properties
        event_properties = settings.get(
            "customerio.event_properties", ".EventProperties"
        )
        if isinstance(event_properties, str):
            if not event_properties.startswith("."):
                self.event_properties = self._resolve_class(event_properties)()
            elif event_properties == ".EventProperties":
                self.event_properties = EventProperties()
            else:
                raise ValueError(f"Unknown event_properties: {event_properties}")
        else:
            self.event_properties = event_properties

        # Profile properties
        profile_properties = settings.get(
            "customerio.profile_properties", ".ProfileProperties"
        )
        if isinstance(profile_properties, str):
            if not profile_properties.startswith("."):
                self.profile_properties = self._resolve_class(profile_properties)()
            elif profile_properties == ".ProfileProperties":
                self.profile_properties = ProfileProperties()
            else:
                raise ValueError(f"Unknown profile_properties: {profile_properties}")
        else:
            self.profile_properties = profile_properties

        # Profile meta properties
        profile_meta_properties = settings.get(
            "customerio.profile_meta_properties", ".ProfileMetaProperties"
        )
        if isinstance(profile_meta_properties, str):
            if not profile_meta_properties.startswith("."):
                self.profile_meta_properties = self._resolve_class(
                    profile_meta_properties
                )()
            elif profile_meta_properties == ".ProfileMetaProperties":
                self.profile_meta_properties = ProfileMetaProperties()
            else:
                raise ValueError(
                    f"Unknown profile_meta_properties: {profile_meta_properties}"
                )
        else:
            self.profile_meta_properties = profile_meta_properties

        # Object types
        object_types = settings.get("customerio.object_types", ".ObjectTypes")
        if isinstance(object_types, str):
            if not object_types.startswith("."):
                self.object_types = self._resolve_class(object_types)()
            elif object_types == ".ObjectTypes":
                self.object_types = ObjectTypes()
            else:
                raise ValueError(f"Unknown object_types: {object_types}")
        else:
            self.object_types = object_types

        # Object properties
        object_properties = settings.get(
            "customerio.object_properties", ".ObjectProperties"
        )
        if isinstance(object_properties, str):
            if not object_properties.startswith("."):
                self.object_properties = self._resolve_class(object_properties)()
            elif object_properties == ".ObjectProperties":
                self.object_properties = ObjectProperties()
            else:
                raise ValueError(f"Unknown object_properties: {object_properties}")
        else:
            self.object_properties = object_properties

        # Relationship properties
        relationship_properties = settings.get(
            "customerio.relationship_properties", ".RelationshipProperties"
        )
        if isinstance(relationship_properties, str):
            if not relationship_properties.startswith("."):
                self.relationship_properties = self._resolve_class(
                    relationship_properties
                )()
            elif relationship_properties == ".RelationshipProperties":
                self.relationship_properties = RelationshipProperties()
            else:
                raise ValueError(
                    f"Unknown relationship_properties: {relationship_properties}"
                )
        else:
            self.relationship_properties = relationship_properties

        # Distinct ID
        self.distinct_id = distinct_id

    def _resolve_class(self, dotted_path: str) -> t.Any:
        """Resolve a dotted path to a class."""
        module_name, class_name = dotted_path.rsplit(".", 1)
        module = __import__(module_name, fromlist=[class_name])
        return getattr(module, class_name)

    @distinct_id_is_required
    def track(self, event: Event, props: t.Optional[PropertiesType] = None) -> None:
        """Track a Customer.io event.

        Args:
            event: Event object defining the event to track
            props: Optional dict of Property->value mappings
        """
        if not props:
            props = {}

        # Validate event
        if event not in self.events.__dict__.values():
            raise ValueError(f"Event '{event.name}' must be a member of self.events")

        # Validate properties
        for prop in props:
            if prop not in self.event_properties.__dict__.values():
                raise ValueError(
                    f"Property '{prop.name}' is not a member of self.event_properties"
                )

        # If event has specific allowed properties, validate against those
        if event.properties:
            for prop in props:
                if prop not in event.properties:
                    raise ValueError(
                        f"Property '{prop}' must be a member of Event.properties"
                    )

        # Send to Customer.io
        msg = {
            "id": self.distinct_id,
            "name": event.name,
            **_format_properties(props),
        }
        self.consumer.send(Endpoint.track, msg)

    @distinct_id_is_required
    def identify(
        self,
        props: PropertiesType,
        meta: t.Optional[PropertiesType] = None,
    ) -> None:
        """Create or update a customer profile in Customer.io.

        Args:
            props: Dict of ProfileProperty->value mappings
            meta: Optional dict of ProfileMetaProperty->value mappings
        """
        if not meta:
            meta = {}

        # Validate properties
        for prop in props:
            if prop not in self.profile_properties.__dict__.values():
                raise ValueError(
                    f"Property '{prop.name}' is not a member of self.profile_properties"
                )

        for prop in meta:
            if prop not in self.profile_meta_properties.__dict__.values():
                raise ValueError(
                    f"Property '{prop.name}' is not a member of self.profile_meta_properties"
                )

        formatted_props = _format_properties(props)

        # Merge in meta properties
        for prop, value in meta.items():
            formatted_props[prop.name] = value

        # Send to Customer.io
        msg = {
            "id": self.distinct_id,
            **formatted_props,
        }
        self.consumer.send(Endpoint.identify, msg)

    def _validate_object_type(self, object_type: ObjectType) -> None:
        """Raise if the object type is not one of self.object_types."""
        if object_type not in self.object_types.__dict__.values():
            raise ValueError(
                f"Object type '{object_type.type_id}' must be a member of self.object_types"
            )

    def _format_relationships(
        self, relationships: RelationshipsType
    ) -> t.List[t.Dict[str, t.Any]]:
        """Validate and format people's relationships to an object."""
        formatted = []
        for distinct_id, props in relationships.items():
            for prop in props:
                if prop not in self.relationship_properties.__dict__.values():
                    raise ValueError(
                        f"Property '{prop.name}' is not a member of "
                        "self.relationship_properties"
                    )
            relationship: t.Dict[str, t.Any] = {"identifiers": {"id": distinct_id}}
            if props:
                relationship["relationship_attributes"] = _format_properties(props)
            formatted.append(relationship)
        return formatted

    def identify_object(
        self,
        object_type: ObjectType,
        object_id: str,
        props: PropertiesType,
        relationships: t.Optional[RelationshipsType] = None,
    ) -> None:
        """Create or update an object in Customer.io, and relate people to it.

        Args:
            object_type: ObjectType object defining the kind of object
            object_id: Your identifier of the object, e.g. a company's id
            props: Dict of ObjectProperty->value mappings
            relationships: Optional dict of distinct_id->RelationshipProperty
                mappings; people listed here are related to the object,
                people not listed keep whatever relationship they had
        """
        self._validate_object_type(object_type)

        # Validate properties
        for prop in props:
            if prop not in self.object_properties.__dict__.values():
                raise ValueError(
                    f"Property '{prop.name}' is not a member of self.object_properties"
                )

        # If object type has specific allowed properties, validate against those
        if object_type.properties:
            for prop in props:
                if prop not in object_type.properties:
                    raise ValueError(
                        f"Property '{prop}' must be a member of ObjectType.properties"
                    )

        # Send to Customer.io
        msg: t.Dict[str, t.Any] = {
            "type": "object",
            "identifiers": {
                "object_type_id": object_type.type_id,
                "object_id": object_id,
            },
            "action": "identify",
            "attributes": _format_properties(props),
        }
        if relationships:
            msg["cio_relationships"] = self._format_relationships(relationships)
        self.consumer.send(Endpoint.entity, msg)

    def delete_object(self, object_type: ObjectType, object_id: str) -> None:
        """Delete an object from Customer.io, along with its relationships.

        Args:
            object_type: ObjectType object defining the kind of object
            object_id: Your identifier of the object, e.g. a company's id
        """
        self._validate_object_type(object_type)

        msg = {
            "type": "object",
            "identifiers": {
                "object_type_id": object_type.type_id,
                "object_id": object_id,
            },
            "action": "delete",
        }
        self.consumer.send(Endpoint.entity, msg)

    def delete_object_relationships(
        self, object_type: ObjectType, object_id: str, distinct_ids: t.List[str]
    ) -> None:
        """Unrelate people from an object in Customer.io.

        Args:
            object_type: ObjectType object defining the kind of object
            object_id: Your identifier of the object, e.g. a company's id
            distinct_ids: The people to unrelate from the object
        """
        self._validate_object_type(object_type)

        msg = {
            "type": "object",
            "identifiers": {
                "object_type_id": object_type.type_id,
                "object_id": object_id,
            },
            "action": "delete_relationships",
            "cio_relationships": [
                {"identifiers": {"id": distinct_id}} for distinct_id in distinct_ids
            ],
        }
        self.consumer.send(Endpoint.entity, msg)


def _format_properties(props: PropertiesType) -> t.Dict[str, t.Any]:
    """Format properties for Customer.io, with dates as unix timestamps."""
    formatted = {}
    for prop, value in props.items():
        if isinstance(value, datetime):
            formatted[prop.name] = round(value.timestamp())
        else:
            formatted[prop.name] = value
    return formatted


def customerio_init(request: Request) -> CustomerIOTrack:
    """Return a configured CustomerIOTrack class instance."""
    distinct_id = None
    if getattr(request, "user", None):
        distinct_id = request.user.distinct_id

    customerio = CustomerIOTrack(
        settings=request.registry.settings, distinct_id=distinct_id
    )

    return customerio


def customerio_flush(event: NewRequest) -> None:
    """Send out all pending messages on Pyramid request end."""

    def flush(request: Request, response: Response) -> None:
        """Send all the enqueued messages at the end of request lifecycle."""

        # If request.customerio was never called during request runtime, then
        # skip initializing and flushing CustomerIOTrack.
        if "customerio" not in request.__dict__:
            return

        request.customerio.consumer.flush()

    event.request.add_response_callback(flush)
