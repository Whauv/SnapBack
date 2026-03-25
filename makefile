.PHONY: lint format build-zoom clean

lint:
	ruff check --select ALL --fix .
	ruff check --select ALL --ignore D203,D213,COM812 .
	ruff check --select D211 .
	ruff check --select D212 .
	ruff check --select D213 .

format:
	ruff format .

build-zoom:
	cd apps/zoom-app && npm install && npm run build

clean:
	rm -rf .ruff_cache
	rm -rf apps/zoom-app/dist
	rm -rf apps/zoom-app/node_modules
