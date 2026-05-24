.PHONY: test setup shell coverage render-examples publish-build publish-clean release

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

publish-clean:
	rm -r dist/

# Release: tag the current version and push to trigger CI publish.
# CI workflow: .github/workflows/publish.yml (on tag push v*)
release:
	@VERSION=$$(grep -E "^__version__" src/merm/__version__.py | sed -E "s/.*['\"]([^'\"]+)['\"].*/\1/"); \
	echo "Releasing v$$VERSION"; \
	git tag "v$$VERSION"; \
	git push origin "v$$VERSION"
