.PHONY: test list catalog install

install:
	pip install -e ".[dev]"

test:
	pytest -v

list:
	kunlib list

catalog:
	kunlib catalog
