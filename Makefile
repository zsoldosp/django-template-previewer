TRAVIS_YML=.travis.yml
TOX2TRAVIS=tox2travis.py
.PHONY: clean-pyc clean-build clean-tox ${TRAVIS_YML} ci
PYPI_SERVER?=https://pypi.python.org/pypi
SHELL=/bin/bash

help:
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "lint - check style with flake8"
	@echo "test - run tests quickly with the default Python"
	@echo "testall - run tests on every Python version with tox"
	@echo "coverage - check code coverage quickly with the default Python"
	@echo "release - package and upload a release"
	@echo "sdist - package"
	@echo "${TRAVIS_YML} - convert tox.ini to ${TRAVIS_YML}"

ci: ${TRAVIS_YML} test-all

${TRAVIS_YML}: tox.ini ${TOX2TRAVIS}
	./${TOX2TRAVIS} > $@
	git diff $@; echo $$?  # FYI
	test 0 -eq $$(git diff $@ | wc -l)

clean: clean-build clean-pyc clean-tox

clean-build:
	rm -fr build/
	rm -fr dist/
	find -name *.egg-info -type d | xargs rm -rf

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

lint:
	flake8 template_previewer tests

test:
	#python manage.py test testapp.tests.RegressionTestCase.test_can_parse_translations_with_vars --traceback
	python manage.py test testapp --traceback

clean-tox:
	if [[ -d .tox ]]; then rm -r .tox; fi

test-all:
	tox

coverage:
	coverage run --source template_previewer setup.py test
	coverage report -m
	coverage html
	open htmlcov/index.html

release: clean
	echo "if the release fails, setup a ~/pypirc file as per https://docs.python.org/2/distutils/packageindex.html#pypirc"
	python setup.py register -r ${PYPI_SERVER}
	python setup.py sdist upload -r ${PYPI_SERVER}

sdist: clean
	python setup.py sdist
	ls -l dist
