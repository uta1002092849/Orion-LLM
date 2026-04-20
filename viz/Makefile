.PHONY: build clean setup open

build: setup
	uv run schema_graph.py

setup:
	uv sync

open: build
	open freebase-schema.html

clean:
	rm -f freebase-schema.html
