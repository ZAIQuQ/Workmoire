.PHONY: run test compile skill-sync

run:
	python3 workspace_server.py

test:
	python3 -m unittest discover -s tests -v

compile:
	python3 -m py_compile workspace_server.py

skill-sync:
	python3 scripts/sync_skill.py
