.PHONY: lint

lint:
	mypy lib2opds

test:
	pytest

isort:
	isort .

black:
	black lib2opds/

bandit:
	bandit -r lib2opds/
