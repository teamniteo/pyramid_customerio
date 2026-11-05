## Integrate your [Pyramid](https://trypyramid.com) app with [Customer.io](https://customer.io/)

<p align="center">
  <a href="https://github.com/teamniteo/pyramid_customerio/blob/master/LICENSE">
    <img alt="License: MIT"
         src="https://img.shields.io/badge/License-MIT-yellow.svg">
  </a>
  <a href="https://github.com/teamniteo/pyramid_customerio/graphs/contributors">
    <img alt="Built by these great folks!"
         src="https://img.shields.io/github/contributors/teamniteo/pyramid_customerio.svg">
  </a>
  <a href="https://web.libera.chat/#pyramid">
    <img alt="Talk to us in #pyramid on Libera.Chat IRC"
         src="https://img.shields.io/badge/irc-libera.chat-blue.svg">
  </a>
</p>

## Opinionated Customer.io integration

The reason this package exists is to provide sane defaults when integrating with Customer.io. Instead of chasing down event name typos and debugging why tracking does not work, you can focus on building meaningful customer relationships.

- You **never have typo-duplicated events** in Customer.io, because every event name comes from a dataclass, never from a string that can be miss-typed by mistake.
- Same for properties. Like events, **properties are hardcoded** as dataclasses.
- All **"special" and "reserved" events and properties are already provided**, no need to chase them down in various Customer.io docs.
- Your **app never stops working if Customer.io is down**, but you still get errors in your logs so you know what is going on.
- You **never forget to call `flush()`** on the events buffer, since `pyramid_customerio` hooks into the request life-cycle and calls `flush()` at the end of the request processing.
- You **defer sending events until the entire request is processed successfully**, i.e. never send events like "User added a thing" if adding the thing to DB failed at a later stage in the request life-cycle.

## Getting started

Install the package:

```bash
pip install pyramid_customerio
```

Or if you're using Poetry:

```bash
poetry add pyramid_customerio
```

Include the package in your Pyramid app configuration:

```python
config.include('pyramid_customerio')
```

Configure your Customer.io credentials:

```ini
customerio.tracking.site_id = <your-site-id>
customerio.tracking.api_key = <your-api-key>
customerio.tracking.region = us  # or 'eu'
```

Start tracking events and identifying users:

```python
def my_view(request):
    # Track an event
    request.customerio.track(
        request.customerio.events.user_signed_up,
        {request.customerio.event_properties.path: request.path}
    )

    # Identify a user
    request.customerio.identify({
        request.customerio.profile_properties.email: 'user@example.com',
        request.customerio.profile_properties.name: 'John Doe'
    })
```

## Objects

Customer.io [Objects](https://docs.customer.io/journeys/objects/) are non-person entities, such as companies or accounts, that people relate to. Declare your object types and the properties allowed on them, then identify objects and relate people to them the same way you identify people:

```python
from dataclasses import dataclass
from pyramid_customerio import ObjectProperties
from pyramid_customerio import ObjectType
from pyramid_customerio import ObjectTypes
from pyramid_customerio import Property
from pyramid_customerio import RelationshipProperties


@dataclass(frozen=True)
class MyObjectTypes(ObjectTypes):
    # The id comes from your workspace's Objects settings
    company: ObjectType = ObjectType("1")


@dataclass(frozen=True)
class MyRelationshipProperties(RelationshipProperties):
    role: Property = Property("role")


def my_view(request):
    request.customerio.identify_object(
        request.customerio.object_types.company,
        "acme",
        {request.customerio.object_properties.name: "Acme Inc."},
        relationships={
            request.user.distinct_id: {
                request.customerio.relationship_properties.role: "admin"
            }
        },
    )
```

```ini
customerio.object_types = myapp.customerio.MyObjectTypes
customerio.relationship_properties = myapp.customerio.MyRelationshipProperties
```

## Releasing

Release instructions are in [RELEASING.md](RELEASING.md).

## Development

This project uses Nix for development environment management and Poetry for Python dependency management.

### Setup

```bash
# Enter the Nix development shell
nix-shell

# Install dependencies
make install
```

### Running tests

```bash
# Run all tests with coverage
make test

# Run only unit tests
make unit

# Run specific tests
make unit filter="test_name"
```

### Code quality

```bash
# Run linting
make lint

# Run type checking
make types

# Format code
make format
```

## License

MIT
