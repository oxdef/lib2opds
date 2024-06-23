.PHONY: lint
PYTHON := $(shell poetry env info -p)/bin/python

lint:
	mypy --python-executable="$(PYTHON)" lib2opds

test:
	pytest
