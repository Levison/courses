# Course Makefile. Learner commands:
#   make start 01      copy modules/01-*/code/ to workspace/01-*/ and create NOTES.md
#   make check 01      run module 01's exercise tests against your workspace copy
#   make progress      run all exercise tests and write PROGRESS.md
#   make test          run the reference tests (course content must stay green)
#   make solve 01 FORCE=1   overwrite workspace/01-*/ with the reference solutions (spoiler)
#   make learner-branch NAME=you   create learner/you, where workspace/ and PROGRESS.md are tracked
#   make list          list modules and whether you have started them
# `make start M=01` works too.

# ADAPT: toolchain. The kit itself only needs Python 3.10+ (stdlib).
PYTHON     ?= uv run python
TEST       ?= uv run pytest
# ADAPT: where the reference tests live (shell globs are fine).
TEST_PATHS ?= modules/*/code
# ADAPT: exercise runner for non-pytest courses; must write JUnit XML to {junit}.
# export COURSE_EXERCISE_CMD = npx jest --reporters=jest-junit {paths}   (JEST_JUNIT_OUTPUT_FILE={junit})

KIT := $(PYTHON) course_kit/kit.py
UNIT_CMDS := start check solve
ifneq ($(filter $(UNIT_CMDS) learner-branch,$(firstword $(MAKECMDGOALS))),)
  ARG := $(word 2,$(MAKECMDGOALS))
  ifneq ($(ARG),)
    $(eval $(ARG):;@:)
  endif
endif
M ?= $(ARG)

.PHONY: start check solve progress test list learner-branch
start check solve:
	@test -n "$(M)" || { echo "usage: make $@ NN   (see: make list)"; exit 2; }
	@$(KIT) $@ $(M)

progress list:
	@$(KIT) $@

learner-branch:
	@$(KIT) learner-branch $(or $(NAME),$(M))

test:
	$(TEST) $(TEST_PATHS)
