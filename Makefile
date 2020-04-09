################################################
## variables

## executables
POETRY      = poetry
SPHINXBUILD = $(POETRY) run sphinx-build
PYTEST      = $(POETRY) run py.test
PYTHON      = $(POETRY) run python
FLAKE8      = $(POETRY) run flake8

## sources
DOCSOURCEDIR   = docs/
DOCSOURCES     = $(wildcard $(DOCSOURCEDIR)/*)
# DOCSOURCEFILES = index.rst reference.rst conf.py
# DOCSOURCES     = $(addprefix $(DOCSOURCEDIR),$(DOCSOURCEFILES))
SPHINX_BUILDDIR = sphinx_build

## opts
POETRYOPTS =
PYTESTOPTS =
FLAKE8OPTS =
COVOPTS    =
SPHINXOPTS =

ALLCOVOPTS = $(PYTESTOPTS) --cov resumeback --cov-config .coveragerc $(COVOPTS)
ALLSPHINXOPTS = -d $(SPHINX_BUILDDIR)/doctrees $(SPHINXOPTS) $(DOCSOURCEDIR)



################################################
## targets

## meta ####################

.PHONY: all
# target: all - (DEFAULT) Build dist and docs.
all: dist docs
	@echo

.PHONY: help
# target: help - Display callable targets.
help:
	@grep -E "^# target:" [Mm]akefile

.PHONY: clean
# target: clean
clean: dist_clean docs_clean
	if poetry env info -p; then $(POETRY) env remove python; fi
	rm -f publish


## env #####################

.PHONY: env
env: pyproject.toml poetry.lock

.PHONY: test_env
test_env: env
	$(POETRY) install -E test $(POETRYOPTS)

.PHONY: flake8_env
flake8_env: env
	$(POETRY) install --no-root -E flake8 $(POETRYOPTS)

.PHONY: docs_env
docs_env: env
	$(POETRY) install --no-root -E docs $(POETRYOPTS)

## dist ####################

.PHONY: dist_clean
# target: dist_clean - clean dist folder.
dist_clean:
	rm -rf dist/*

.PHONY: dist
# target: dist - Build distribution files (source and binary).
dist:
	$(POETRY) build

# target: publish - Upload dist/ to pypi.
publish: dist/resumeback-*.gz dist/resumeback-*.whl
	$(POETRY) publish
	touch publish


## docs ####################

.PHONY: docs_clean
# target: docs_clean - Remove built docs.
docs_clean:
	rm -rf $(SPHINX_BUILDDIR)/*

$(SPHINX_BUILDDIR)/html: docs_env $(DOCSOURCES)
	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) $(SPHINX_BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(SPHINX_BUILDDIR)/html."

# target: html - Build html docs.
html: $(SPHINX_BUILDDIR)/html

# target: docs - Alias for `html`.
docs: html

# TODO docsupload target


## test/lint ###############

.PHONY: test
# target: test - Run tests.
test: test_env
	$(PYTEST) $(PYTESTOPTS)

.PHONY: coverage
# target: coverage - Run tests and report coverage.
coverage: test_env
	$(PYTEST) $(ALLCOVOPTS) --cov-report term-missing

.PHONY: htmlcoverage
# target: htmlcoverage - Run tests and build html coverage report.
htmlcoverage: test_env
	$(PYTEST) $(ALLCOVOPTS) --cov-report html

.PHONY: flake8
# target: flake8 - Run flake8 on source.
flake8: flake8_env
	$(FLAKE8) $(FLAKE8OPTS) .
