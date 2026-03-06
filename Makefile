.PHONY: test setup shell coverage render-examples publish-build publish-test publish publish-clean

test:
	uv run pytest

setup:
	uv sync --dev

shell:
	uv shell

coverage:
	uv run pytest --cov=merm --cov-report=term-missing

render-examples:
	uv run python scripts/render_examples.py

publish-build:
	uv run hatch build

publish-test:
	uv run hatch publish --repo test

publish:
	uv run hatch publish

publish-clean:
	rm -r dist/
