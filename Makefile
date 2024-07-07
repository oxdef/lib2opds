.PHONY: lint

lint:
	mypy lib2opds

test:
	pytest
