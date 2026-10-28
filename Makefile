.PHONY: compile test build browser skill-sync
compile:
	python3 -m py_compile workspace_server.py paper_tools.py rich_documents.py tests/*.py scripts/sync_skill.py scripts/check_assistant.py
	bash -n backup.sh
	node --check workspace/static/app.js
	node --check tests/browser.spec.cjs
	node --check workspace/static/vendor/pdf-reader.mjs

test:
	python3 -m unittest discover -s tests -v
	npm run test:commands

build:
	npm run build

browser:
	npm run test:browser

skill-sync:
	python3 scripts/sync_skill.py
