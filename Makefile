.ONESHELL:
SHELL := /bin/bash
SRC = $(wildcard ./*.ipynb)

all: mrspuff docs

mrspuff: $(SRC)
	nbdev_build_lib
	touch mrspuff

sync:
	nbdev_update_lib

docs_serve: docs
	cd docs && bundle exec jekyll serve

docs: $(SRC)
	nbdev_build_docs
	touch docs

git_update: mrspuff docs
	git add *.ipynb settings.ini README.md mrspuff docs
	git commit
	git push

test:
	nbdev_test_nbs

release: pypi conda_release
	nbdev_bump_version

conda_release:
	fastrelease_conda_package

pypi: dist
	twine upload --repository pypi dist/*

dist: clean
	python setup.py sdist bdist_wheel

clean:
	rm -rf dist
