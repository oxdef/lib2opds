.PHONY: lint run clean isort test black bandit

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

run:
	python3 -m lib2opds -u

build:
	python3 -m build

clean:
	rm -f dist/*
