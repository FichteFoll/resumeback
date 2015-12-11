## variables ###################################

## Paths
SPHINXBUILD = sphinx-build
PIP         = pip
PIP2        = pip-2.7
PYTEST      = py.test
PYTHON      = python
FLAKE8      = flake8

## Sources
DOCSOURCEDIR   = docs/source
DOCSOURCEFILES = index.rst reference.rst conf.py
DOCSOURCES     = $(addprefix $(DOCSOURCEDIR),$(DOCSOURCEFILES))

## Opts
SPHINXOPTS      =
SPHINX_BUILDDIR = sphinx_build
ALLSPHINXOPTS   = -d $(SPHINX_BUILDDIR)/doctrees $(SPHINXOPTS) docs/source

COVOPTS    =
ALLCOVOPTS = --cov . --cov-config .coveragerc $(COVOPTS)

FLAKE8OPTS = -v

## Continuous Tests
# TODO build/alter init and test recipes
# INIT =
# TEST =


## targets ########################################

.PHONY: all help clean init install uninstall \
	distclean dist \
	docsinit docsclean html \
	flake8 test test2 coverage htmlcoverage


## meta ########################################

# target: all - (DEFAULT) Build dist and docs.
all: distclean dist html
	@echo

# target: help - Display callable targets.
help:
	@grep -E "^# target:" [Mm]akefile

# target: clean
clean: distclean docsclean
	rm upload

# target: init -Install dev-requirements.txt
init:
	$(PIP) install -r dev-requirements.txt

# target: install - Run setup.py to install.
install:
	$(PYTHON) setup.py install

# target: uninstall - Use pip to uninstall.
uninstall:
	$(PIP) uninstall resumeback -y


## dist ########################################

# target: distclean - clean dist folder.
distclean:
	rm -rf dist/*

# target: dist - Build distribution files (source and binary).
dist:
	$(PYTHON) setup.py sdist bdist_wheel

# target: upload - Upload dist/ to pypi.
# dist/resumeback-*.zip dist/resumeback-*.whl
upload: dist/resumeback-*.zip dist/resumeback-*.whl
	twine upload $?
	touch upload


## docs ########################################

# target: docsinit - Install requirements for building docs.
docsinit:
	$(PIP2) install docs/requirements.txt

# target: docsclean - Remove built docs.
docsclean:
	rm -rf $(SPHINX_BUILDDIR)/*

# target: htmldocs - Build html docs.
html: $(addprefix docs/source/,$(DOCSOURCES))
	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) $(SPHINX_BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(SPHINX_BUILDDIR)/html."

# TODO uploaddocs target


## other tasks #################################

# target: flake8 - Run flake8 on source.
flake8:
	$(FLAKE8) $(FLAKE8OPTS)

# target: test - Run tests (default).
test:
	$(PYTEST)

# target: test2 - Run tests (Python 2.7).
test2:
	py.test-2.7

# target: coverage - Run tests (default) and report coverage.
coverage:
	$(PYTEST) $(ALLCOVOPTS) --cov-report term-missing

# target: htmlcoverage - Run tests (default) and build html coverage report.
htmlcoverage:
	$(PYTEST) $(ALLCOVOPTS) --cov-report html
