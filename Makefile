.PHONY: install run dev web test lint format check release clean

install:
	bash scripts/install.sh

run:
	bash scripts/dev.sh

web:
	bash scripts/dev.sh web

dev:
	bash scripts/dev.sh web

test:
	bash scripts/test.sh

lint:
	bash scripts/lint.sh

format:
	bash scripts/format.sh

check:
	bash scripts/lint.sh
	bash scripts/test.sh

release:
	bash scripts/release.sh

clean:
	rm -rf build dist *.egg-info .coverage .pytest_cache .mypy_cache .ruff_cache htmlcov
