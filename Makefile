.PHONY: test package lint

test:
	python3 -m compileall -q skills/results-db/scripts scripts
	python3 -m unittest discover -s tests -q

package:
	python3 scripts/package_skill.py --repo-root .

lint:
	python3 -m compileall -q skills/results-db/scripts scripts
