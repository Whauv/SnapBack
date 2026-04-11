.PHONY: lint format build-zoom test-backend test-extension clean

lint:
	ruff check --select ALL --ignore D203,D213,COM812 .
	ruff check --select D203 .
	ruff check --select D211 .
	ruff check --select D212 .
	ruff check --select D213 .

format:
	ruff format .

build-zoom:
	cd apps/zoom-app && npm install && npm run build

test-backend:
	python -m unittest discover -s tests -t .

test-extension:
	node --test tests/apps/meet_extension/host-adapter.test.mjs

clean:
	rm -rf .ruff_cache
	rm -rf apps/zoom-app/dist
	rm -rf apps/zoom-app/node_modules
