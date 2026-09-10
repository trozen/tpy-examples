# Everyday tasks. The harness lives in .verify/ (see .verify/README.md); uv
# bootstraps its venv from .verify/pyproject.toml on first run.

.DEFAULT_GOAL := help
.PHONY: help test bless bless-all

help:  ## list available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-8s %s\n", $$1, $$2}'

test:  ## build every example with the pinned compiler, run the runnable ones, compare outputs
	cd .verify && uv run pytest

bless:  ## record outputs for examples that have none yet (verify them against the original first)
	cd .verify && uv run pytest --bless

bless-all:  ## re-record every output, for a compiler bump; review the diff before committing
	cd .verify && uv run pytest --bless=all
