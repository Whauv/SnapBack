.PHONY: lint format build-zoom clean

lint:
	ruff check .

format:
	ruff format .

build-zoom:
	cd apps/zoom-app && npm install && npm run build

clean:
	rm -rf .ruff_cache
	rm -rf apps/zoom-app/dist
	rm -rf apps/zoom-app/node_modules
