# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
.DEFAULT_GOAL := help

SPHINXOPTS    ?=
# Prefer the checkout's documentation dependencies; allow an explicit override.
SPHINXBUILD   ?= $(if $(wildcard ../.venv/bin/sphinx-build),../.venv/bin/sphinx-build,sphinx-build)
SOURCEDIR     = .
BUILDDIR      = _build
SPHINXAUTO    ?= $(if $(wildcard ../.venv/bin/sphinx-autobuild),../.venv/bin/sphinx-autobuild,sphinx-autobuild)
SERVE_HOST    ?= 0.0.0.0
SERVE_PORT    ?= 8000

.PHONY: serve
serve:
	@$(SPHINXAUTO) --host $(SERVE_HOST) --port $(SERVE_PORT) "$(SOURCEDIR)" "$(BUILDDIR)/html" $(SPHINXOPTS)

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
