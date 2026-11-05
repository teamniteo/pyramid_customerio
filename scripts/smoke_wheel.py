"""Run outside the project environment to check the built distribution."""

from pathlib import Path
from pyramid.config import Configurator
from pyramid.request import Request
from pyramid.response import Response

import pyramid_customerio


def view(request: Request) -> Response:
    """Identify a person, so the view exercises the installed package."""
    request.customerio.distinct_id = "user-1"
    request.customerio.identify(
        {request.customerio.profile_properties.email: "user@example.com"}
    )
    return Response(str(len(request.customerio.consumer.mocked_messages)))


package = Path(pyramid_customerio.__file__).resolve().parent
assert "site-packages" in str(package)
assert (package / "py.typed").exists()

config = Configurator()
config.include("pyramid_customerio")
config.add_route("root", "/")
config.add_view(view, route_name="root")
response = Request.blank("/").get_response(config.make_wsgi_app())
assert response.status_int == 200
assert response.text == "1"
print("Installed wheel smoke test passed.")  # noqa: T201
