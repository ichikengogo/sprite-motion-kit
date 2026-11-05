.PHONY: test demo check

test:
	python -m unittest discover -s tests -v
	node tests/test_coordinates.cjs
	node tests/test_playback.cjs
	node tests/test_project_load.cjs
	node tests/test_render_status.cjs
	node --check web/app.js

check:
	python scripts/check_public_release.py

demo:
	python server.py
