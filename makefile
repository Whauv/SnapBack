.PHONY: lint format build-zoom clean

lint:
	ruff check --exit-zero --select ALL --ignore D203,D213,COM812 .
	# Additional docstring checks are intentionally not blocking CI here
	# (kept for local development in separate checks if desired)

format:
	ruff format .

build-zoom:
	cd apps/zoom-app && npm install && npm run build

clean:
	rm -rf .ruff_cache
	rm -rf apps/zoom-app/dist
	rm -rf apps/zoom-app/node_modules
