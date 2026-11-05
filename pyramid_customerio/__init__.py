"""Integration with Customer.io.

Send user interaction events and set profile properties via
track.CustomerIOTrack(), which is prepared as `request.customerio`
for easier usage in view code.
"""

from dataclasses import dataclass
from pyramid.config import Configurator
from pyramid.events import NewRequest

import typing as t


@dataclass(frozen=True)
class Event:
    """A single event that we send to Customer.io."""

    # The name of this event that will be shown in Customer.io. Should be
    # something nice, like "Page Viewed".
    name: str

    # Optional list of properties that are allowed for this event
    properties: t.Optional[t.List["Property"]] = None


@dataclass(frozen=True)
class Events:
    """Let's be precise which events we will send.

    Otherwise different parts of code will send slightly differently named
    events and then you can wish good luck to the marketing/product team
    when they are trying to decipher what's the difference between
    "Page Load", "User Visited" and "Viewed Page".

    So we're only allowing events listed below. You can provide your own
    list of events via the `customerio.events` setting.
    """

    # Any page view should be tracked with this event. More specific events
    # can then be built with Customer.io's segmentation tools.
    page_viewed: Event = Event("Page Viewed")

    # Any click should be tracked with this event. More specific events
    # can then be built with Customer.io's segmentation tools.
    button_link_clicked: Event = Event("Button/Link Clicked")

    # Events for tracking user's account/subscription status.
    user_signed_up: Event = Event("User Signed Up")
    user_converted_to_paid: Event = Event("User Converted to Paid")
    user_logged_in: Event = Event("User Logged In")
    user_charged: Event = Event("User Charged")
    user_disabled: Event = Event("User Disabled")


@dataclass(frozen=True)
class Property:
    """A single property that we attach to Customer.io events or profiles."""

    # The name of this property that will be shown in Customer.io. Should be
    # something nice, like "Path" or "Title".
    name: str


@dataclass(frozen=True)
class EventProperties:
    """Let's be precise which properties we will set on Events.

    Otherwise different parts of code will set slightly differently named
    properties and then you can wish good luck to the marketing/product team
    when they are trying to decipher what's the difference between "title" and
    "name".

    So we're only allowing properties listed below. You can provide your own
    list of properties via the `customerio.event_properties` setting.
    """

    # Used for building bespoke custom events
    title: Property = Property("Title")
    path: Property = Property("Path")

    # Referring URL, including your own domain.
    referrer: Property = Property("referrer")


@dataclass(frozen=True)
class ProfileProperties:
    """Let's be precise which properties we will set on Profile records.

    Otherwise different parts of code will set slightly differently named
    properties and then you can wish good luck to the marketing/product team
    when they are trying to decipher what's the difference between "state" and
    "status".

    So we're only allowing properties listed below. You can provide your own
    list of properties via `customerio.profile_properties` setting.
    """

    # The time when the user created their account.
    created_at: Property = Property("created_at")

    # The user's email address as a string, e.g. "joe.doe@example.com".
    email: Property = Property("email")

    # The users full name.
    name: Property = Property("name")

    # The user's phone number as a string, e.g. "4805551212".
    phone: Property = Property("phone")

    # If this property is set to any value, a user will be unsubscribed
    # from Customer.io messaging.
    unsubscribed: Property = Property("unsubscribed")


@dataclass(frozen=True)
class ProfileMetaProperties:
    """Warning: here be dragons! Overrides of how Customer.io works.

    These are used very rarely to send special values to Customer.io to override
    sane default behavior.
    """

    # The IP address associated with a given profile. Customer.io uses IP for
    # geo-locating the profile.
    ip: Property = Property("ip")

    # Seconds since midnight, January 1st 1970, UTC. Updates are applied
    # in time order, so setting this value can lead to unexpected results
    # unless care is taken.
    time: Property = Property("time")

    # If the ignore_time property is present and true in your update request,
    # Customer.io will not automatically update the "Last Seen" property of the
    # profile.
    ignore_time: Property = Property("ignore_time")

    # If the ignore_alias property is present and true in your update request,
    # Customer.io will apply the update directly to the profile with the
    # distinct_id included in the request.
    ignore_alias: Property = Property("ignore_alias")


@dataclass(frozen=True)
class ObjectType:
    """A kind of non-person entity, such as a company, an account or a course.

    People relate to objects, and Customer.io can then segment people by the
    objects they belong to, or message everyone related to one object.
    """

    # Customer.io's numeric id of the object type, shown in the workspace's
    # Objects settings. Object types are numbered per workspace.
    type_id: str

    # Optional list of properties that are allowed on objects of this type
    properties: t.Optional[t.List[Property]] = None


@dataclass(frozen=True)
class ObjectTypes:
    """Let's be precise which object types we will send.

    Customer.io numbers object types per workspace, so there are no defaults
    here. Provide your own list via the `customerio.object_types` setting.
    """


@dataclass(frozen=True)
class ObjectProperties:
    """Let's be precise which properties we will set on Objects.

    Same reasoning as for ProfileProperties: a single list of allowed
    properties keeps object attributes consistent across the codebase. You
    can provide your own list via the `customerio.object_properties` setting.
    """

    # The time when the object was created.
    created_at: Property = Property("created_at")

    # The object's display name, e.g. "Acme Inc.".
    name: Property = Property("name")


@dataclass(frozen=True)
class RelationshipProperties:
    """Let's be precise which properties we will set on Relationships.

    A relationship links a person to an object, and can carry its own
    properties, such as the person's role in a company. There are no defaults
    here. Provide your own list via the `customerio.relationship_properties`
    setting.
    """


# Type alias to make passing dicts of properties easier
PropertiesType = t.Dict[Property, t.Any]

# Type alias for relating people to an object: a person's distinct_id mapped
# to the properties stored on the relationship (an empty dict for none)
RelationshipsType = t.Dict[str, PropertiesType]


def includeme(config: Configurator) -> None:
    """Pyramid knob."""
    from pyramid_customerio.consumer import MockedConsumer
    from pyramid_customerio.track import customerio_flush
    from pyramid_customerio.track import customerio_init
    from pyramid_customerio.track import CustomerIOTrack

    customerio = CustomerIOTrack(settings=config.registry.settings)
    if config.registry.settings.get("pyramid_heroku.structlog"):
        import structlog

        logger = structlog.get_logger(__name__)
        logger.info(
            "Customer.io configured",
            consumer=customerio.consumer.__class__.__name__,
            events=customerio.events.__class__.__name__,
            event_properties=customerio.event_properties.__class__.__name__,
            profile_properties=customerio.profile_properties.__class__.__name__,
            profile_meta_properties=customerio.profile_meta_properties.__class__.__name__,
        )
        if customerio.consumer.__class__ == MockedConsumer:  # pragma: no cover
            logger.warning("Customer.io is in testing mode, no messages will be sent!")

    else:
        import logging

        logger = logging.getLogger(__name__)

        logger.info(
            "Customer.io configured "
            f"consumer={customerio.consumer.__class__.__name__}, "
            f"events={customerio.events.__class__.__name__}, "
            f"event_properties={customerio.event_properties.__class__.__name__}, "
            f"profile_properties={customerio.profile_properties.__class__.__name__}, "
            f"profile_meta_properties={customerio.profile_meta_properties.__class__.__name__}"
        )
        if customerio.consumer.__class__ == MockedConsumer:  # pragma: no cover
            logger.warning("Customer.io is in testing mode, no messages will be sent!")

    config.add_request_method(customerio_init, "customerio", reify=True)
    config.add_subscriber(customerio_flush, NewRequest)
