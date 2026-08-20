SHELL := /bin/bash

LIGHTWELL_SKILLS_REPO ?= https://github.com/garethahealy/lightwell-skills.git
LIGHTWELL_SKILLS_REF ?= main
SKILLS_DIR := .cursor/skills
SKILLS_SRC := plugins/lightwell/skills

.PHONY: help skills

help:
	@echo "Targets:"
	@echo "  skills  Remove $(SKILLS_DIR) and clone a fresh copy from lightwell-skills"

# Wipe project skills and copy a fresh checkout of lightwell-skills.
skills:
	@set -euo pipefail; \
	rm -rf "$(SKILLS_DIR)"; \
	tmpdir=$$(mktemp -d); \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	git clone --depth 1 --branch "$(LIGHTWELL_SKILLS_REF)" "$(LIGHTWELL_SKILLS_REPO)" "$$tmpdir"; \
	src="$$tmpdir/$(SKILLS_SRC)"; \
	if [ ! -d "$$src" ]; then \
		echo "clone missing $$src" >&2; \
		exit 1; \
	fi; \
	mkdir -p "$(SKILLS_DIR)"; \
	cp -a "$$src/." "$(SKILLS_DIR)/"; \
	echo "Installed skills from $(LIGHTWELL_SKILLS_REPO)@$(LIGHTWELL_SKILLS_REF) into $(SKILLS_DIR)"
