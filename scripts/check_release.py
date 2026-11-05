"""Reject releases whose tag does not match the package version."""

from pathlib import Path

import os
import tomllib


def main() -> None:
    """Exit with an error unless RELEASE_TAG is v<package version>."""
    with Path("pyproject.toml").open("rb") as source:
        version = tomllib.load(source)["tool"]["poetry"]["version"]
    expected = f"v{version}"
    actual = os.environ.get("RELEASE_TAG")
    if actual != expected:
        raise SystemExit(f"Release tag must be {expected!r}, got {actual!r}")
    print(f"Publishing pyramid_customerio {version} from {actual}")  # noqa: T201


if __name__ == "__main__":
    main()
