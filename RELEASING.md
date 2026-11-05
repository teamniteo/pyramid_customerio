# Releasing

Set the version in `pyproject.toml`, add a dated entry to `CHANGELOG.md`, and run `make tests`. Once the changes are on `main`, publish a GitHub release with a matching `v<version>` tag, such as `v1.1.0`.

The `publish.yml` workflow checks that the tag matches the package version, runs the checks, and publishes the wheel and source distribution to PyPI using Trusted Publishing. A tag push alone does not publish. The GitHub release must be published. No PyPI API token is needed.
