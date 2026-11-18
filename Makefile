.PHONY: all test lint format render-smoke

all: lint test render-smoke

test:
	uv run pytest --cov=post --cov=auth --cov=padroes --cov-report=term

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

# Renderiza os exemplos de examples/ com Playwright e confere o PDF e o PNG gerados.
# Precisa de `npm ci` e `npx playwright install chromium` antes.
render-smoke:
	npm run test:render
