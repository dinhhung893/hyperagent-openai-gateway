.PHONY: install dev test serve login doctor agents docker up down

install:      ## Install the CLI + deps into the current environment
	pip install -e .

dev:          ## Install with dev extras (pytest, openai)
	pip install -e ".[dev]"

test:         ## Run the test suite
	python -m pytest tests/ -q

serve:        ## Run the gateway (reads .env)
	hyperagent-gateway serve

login:        ## One-time Hyperagent OAuth
	hyperagent-gateway login

doctor:       ## Check config + upstream reachability
	hyperagent-gateway doctor

agents:       ## List your Hyperagent agents
	hyperagent-gateway agents

docker:       ## Build the Docker image
	docker build -t hyperagent-openai-gateway .

up:           ## Start via docker compose
	docker compose up -d --build

down:         ## Stop docker compose
	docker compose down
