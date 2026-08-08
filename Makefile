COMPOSE := docker compose -p locadev

.PHONY: start up teams down verify test logs harness playground

start:
	bash scripts/start.sh

up:
	$(COMPOSE) up -d --build

teams:
	$(COMPOSE) --profile teams up -d --build

down:
	$(COMPOSE) down $(ARGS)

verify:
	bash scripts/verify.sh

test:
	@if [ ! -d .venv ]; then python3 -m venv .venv; fi
	. .venv/bin/activate && pip -q install -r tests/requirements.txt && pytest -q tests

logs:
	$(COMPOSE) logs -f

harness:
	. .venv/bin/activate 2>/dev/null; python3 bridge/harness.py

# Static GitHub Pages site → http://127.0.0.1:8088
site:
	@echo "Open http://127.0.0.1:8088/"
	python3 -m http.server 8088 --directory docs

# DaisyUI web playground (host-side) → http://127.0.0.1:19191
playground:
	@if [ ! -d demos/playground/.venv ]; then python3 -m venv demos/playground/.venv; fi
	. demos/playground/.venv/bin/activate && pip -q install -r demos/playground/requirements.txt
	cd demos/playground && . .venv/bin/activate && uvicorn app:app --host 127.0.0.1 --port 19191
