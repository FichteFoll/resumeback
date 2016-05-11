################################################
## variables

## executables
SPHINXBUILD = sphinx-build
PIP         = pip
PIP2        = pip-2.7
PYTEST      = py.test
PYTHON      = python
FLAKE8      = flake8

## sources
DOCSOURCEDIR   = docs/source/
DOCSOURCEFILES = index.rst reference.rst conf.py
DOCSOURCES     = $(addprefix $(DOCSOURCEDIR),$(DOCSOURCEFILES))

## opts
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


################################################
## targets

.PHONY: all help clean dev install uninstall \
	distclean dist \
	docsinit docsclean \
	flake8 test test2 coverage htmlcoverage \
	ci_install ci_script ci_after


## meta ####################

# target: all - (DEFAULT) Build dist and docs.
all: distclean dist html
	@echo

# target: help - Display callable targets.
help:
	@grep -E "^# target:" [Mm]akefile

# target: clean
clean: distclean docsclean
	rm upload

# target: dev - Install dev-requirements.txt
dev:
	$(PIP) install -r dev-requirements.txt

# target: install - Run setup.py to install.
install:
	$(PYTHON) setup.py install

# target: uninstall - Use pip to uninstall.
uninstall:
	$(PIP) uninstall resumeback -y


## dist ####################

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


## docs ####################

# target: docsinit - Install requirements for building docs.
docsinit:
	$(PIP2) install docs/requirements.txt

# target: docsclean - Remove built docs.
docsclean:
	rm -rf $(SPHINX_BUILDDIR)/*

# target: html - Build html docs.
html: $(SPHINX_BUILDDIR)/html

$(SPHINX_BUILDDIR)/html: $(DOCSOURCES)
	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) $(SPHINX_BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(SPHINX_BUILDDIR)/html."

# TODO docsupload target


## other tasks #############

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


## CI ######################

# target: ci_install - Initialize CI environment
ci_install: dev
ifneq ($(RUN_FLAKE8),1)
	$(PIP) install coveralls
endif

# target: ci_script - Perform correct CI action according to env
ifeq ($(RUN_FLAKE8),1)
ci_script: flake8
else
ci_script: coverage
endif

# target: ci_after - Perform operations after the script succeeded
ci_after:
ifneq ($(RUN_FLAKE8),1)
	coveralls
endif
