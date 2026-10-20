# SAM's custom builder packages only production source and installed runtime libraries.
# Local .env, examples, tests, .venv, outputs and source configuration never enter the ZIP.
.PHONY: build-CrawlerFunction
build-CrawlerFunction:
	python3.12 -m pip install -r requirements.txt --target "$(ARTIFACTS_DIR)"
	python3.12 -c 'import shutil; shutil.copytree("agent_crawler", "$(ARTIFACTS_DIR)/agent_crawler", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"), dirs_exist_ok=True)'
