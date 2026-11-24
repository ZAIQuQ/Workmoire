.PHONY: compile test build browser skill-sync preflight check-source
.DEFAULT_GOAL := compile

preflight: check-source compile test

check-source:
	python3 scripts/check_public_source.py
	npm run build
	git diff --exit-code HEAD -- workspace/static
	test -z "$$(git ls-files --others --exclude-standard -- workspace/static)"
	git diff --check HEAD
compile:
	python3 -m py_compile workspace_server.py paper_tools.py paper_intake.py rich_documents.py share_store.py share_server.py app_release.py bug_reports.py paper_runtime.py paper_acceptance.py tests/*.py scripts/*.py
	bash -n backup.sh
	node --check workspace/static/app.js
	node --check tests/browser.spec.cjs
	node --check scripts/evaluate_papers.cjs
	node --check workspace/static/vendor/pdf-reader.mjs

test:
	python3 -m unittest discover -s tests -v
	python3 scripts/check_document_templates.py
	npm run test:commands

build:
	npm run build

browser:
	npm run test:browser

skill-sync:
	python3 scripts/sync_skill.py
