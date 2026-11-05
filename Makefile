# Convenience makefile to build the dev env and run common commands
# Based on https://github.com/teamniteo/Makefile
.EXPORT_ALL_VARIABLES:

.PHONY: all
all: .installed

.PHONY: install
install:
	@rm -f .installed  # force re-install
	@make .installed

.installed: pyproject.toml poetry.lock
	@echo "pyproject.toml or poetry.lock is newer than .installed, (re)installing"
	@poetry install
	@poetry run pre-commit install -f --hook-type pre-commit
	@poetry run pre-commit install -f --hook-type pre-push
	@echo "This file is used by 'make' for keeping track of last install time. If pyproject.toml or poetry.lock are newer then this file (.installed) then all 'make *' commands that depend on '.installed' know they need to run poetry install first." \
		> .installed

# Testing and linting targets
.PHONY: lint
lint: .installed
	@poetry run pre-commit run --all-files --hook-stage push

.PHONY: type
type: types

.PHONY: types
types: .installed
	@poetry run mypy pyramid_customerio
	@cat ./typecov/linecount.txt
	@poetry run typecov 100 ./typecov/linecount.txt

.PHONY: sort
sort: .installed
	@poetry run isort --atomic pyramid_customerio

.PHONY: fmt
fmt: format

.PHONY: black
black: format

.PHONY: format
format: .installed sort
	@poetry run black pyramid_customerio

# anything, in regex-speak
filter = "."
# additional arguments for pytest
args = ""
pytest_args = -k $(filter) $(args)
coverage_args = ""
ifeq ($(filter),".")
	coverage_args = --junitxml junit.xml --cov=pyramid_customerio --cov-branch --cov-report html --cov-report xml:cov.xml --cov-report term-missing --cov-fail-under=100
endif

.PHONY: unit
unit: .installed
	@poetry run pytest pyramid_customerio/ $(coverage_args) $(pytest_args)

.PHONY: test
test: tests

.PHONY: build
build: .installed
	@rm -rf dist
	@poetry build
	@poetry run twine check dist/*
	@smoke=$$(mktemp -d) && python3 -m venv $$smoke \
		&& $$smoke/bin/pip install -q "setuptools<82" dist/*.whl \
		&& $$smoke/bin/python scripts/smoke_wheel.py

.PHONY: tests
tests: format lint types unit build

.PHONY: clean
clean:
	@if [ -d ".venv/" ]; then rm -rf .venv; fi
	@rm -rf .coverage htmlcov/ pyramid_customerio.egg-info xunit.xml \
	    htmltypecov typecov \
	    .git/hooks/pre-commit .git/hooks/pre-push
	@rm -f .installed
