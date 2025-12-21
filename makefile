.PHONY: help install install-dev install-docs clean lint format check test test-cov test-watch test-report type-check docs build publish publish-test check-build pre-commit pre-commit-all version-patch version-minor version-major run-example runim-example-simple run-example-advanced export-requirements lock check-lock update-deps ci validate all

# Variables
PYTHON := python
POETRY := poetry
PYTEST := $(POETRY) run pytest
BLACK := $(POETRY) run black
ISORT := $(POETRY) run isort
FLAKE8 := $(POETRY) run flake8
MYPY := $(POETRY) run mypy
COVERAGE := $(POETRY) run coverage
PRECOMMIT := $(POETRY) run pre-commit
SPHINX := $(POETRY) run sphinx-build
PACKAGE_NAME := state-machine-amz
MODULE_NAME := state_machine
SRC_DIR := src

# Update paths in commands:
lint:  ## Run linter (flake8)
	@echo "Running flake8..."
	$(FLAKE8) $(SRC_DIR) tests examples

format:  ## Format code with black and isort
	@echo "Formatting code with black..."
	$(BLACK) $(SRC_DIR) tests examples
	@echo "Sorting imports with isort..."
	$(ISORT) $(SRC_DIR) tests examples

format-check:  ## Check formatting without making changes
	@echo "Checking black formatting..."
	$(BLACK) --check $(SRC_DIR) tests examples
	@echo "Checking import sorting..."
	$(ISORT) --check-only $(SRC_DIR) tests examples

type-check:  ## Run type checker (mypy)
	@echo "Running mypy..."
	$(MYPY) $(SRC_DIR) tests examples


# Default target
help:  ## Display this help message
	@echo "Available commands:"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation
install:  ## Install production dependencies
	@echo "Installing production dependencies..."
# 	$(POETRY) install --only main
	$(POETRY) install --no-root

install-dev:  ## Install development dependencies
	@echo "Installing development dependencies..."
	$(POETRY) install --with dev

install-docs:  ## Install documentation dependencies
	@echo "Installing documentation dependencies..."
	$(POETRY) install --with docs

install-all: install-dev install-docs  ## Install all dependencies (dev + docs)

# Cleanup
clean:  ## Clean build artifacts and cache files
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf docs/_build/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*~" -delete
	find . -type f -name "*.swp" -delete
	find . -type f -name "*.swo" -delete

clean-all: clean  ## Clean everything including Poetry virtual environment
	@echo "Removing Poetry virtual environment..."
	$(POETRY) env remove --all 2>/dev/null || true


format:  ## Format code with black and isort
	@echo "Formatting code with black..."
	$(BLACK) $(MODULE_NAME) tests examples
	@echo "Sorting imports with isort..."
	$(ISORT) $(MODULE_NAME) tests examples

format-check:  ## Check formatting without making changes
	@echo "Checking black formatting..."
	$(BLACK) --check $(MODULE_NAME) tests examples
	@echo "Checking import sorting..."
	$(ISORT) --check-only $(MODULE_NAME) tests examples

check: format-check lint type-check  ## Run all code quality checks

# Testing
test:  ## Run tests
	@echo "Running tests..."
	$(PYTEST) tests/

test-cov:  ## Run tests with coverage
	@echo "Running tests with coverage..."
	$(PYTEST) --cov=$(MODULE_NAME) --cov-report=term-missing --cov-report=html tests/

test-report: test-cov  ## Run tests and generate coverage report
	@echo "Coverage report generated in htmlcov/index.html"

test-watch:  ## Run tests in watch mode
	@echo "Running tests in watch mode..."
	$(PYTEST) -f tests/

test-specific:  ## Run specific test (usage: make test-specific test=path/to/test.py)
ifndef test
	$(error Please specify test file with test=path/to/test.py)
endif
	$(PYTEST) $(test)

# Type Checking
type-check:  ## Run type checker (mypy)
	@echo "Running mypy..."
	$(MYPY) $(MODULE_NAME) tests examples

# Documentation
docs:  ## Build documentation
	@echo "Building documentation..."
	$(POETRY) run sphinx-build -b html docs/ docs/_build/html

docs-serve: docs  ## Build and serve documentation
	@echo "Serving documentation at http://localhost:8000"
	cd docs/_build/html && $(POETRY) run python -m http.server 8000

docs-clean:  ## Clean documentation build
	@echo "Cleaning documentation build..."
	rm -rf docs/_build/

# Build & Publish
build:  ## Build package
	@echo "Building package..."
	$(POETRY) build

check-build:  ## Check if package can be built
	@echo "Checking package build..."
	$(POETRY) check
	$(POETRY) build --check

publish: build  ## Publish to PyPI
	@echo "Publishing to PyPI..."
	$(POETRY) publish

publish-test: build  ## Publish to TestPyPI
	@echo "Publishing to TestPyPI..."
	$(POETRY) publish --repository testpypi

# Version Management
version-patch:  ## Bump patch version
	@echo "Bumping patch version..."
	$(POETRY) version patch

version-minor:  ## Bump minor version
	@echo "Bumping minor version..."
	$(POETRY) version minor

version-major:  ## Bump major version
	@echo "Bumping major version..."
	$(POETRY) version major

version-show:  ## Show current version
	@echo "Current version:"
	$(POETRY) version

# Dependencies
export-requirements:  ## Export requirements to requirements.txt
	@echo "Exporting requirements..."
	$(POETRY) export -f requirements.txt --output requirements.txt --without-hashes
	$(POETRY) export -f requirements.txt --output requirements-dev.txt --with dev --without-hashes

lock:  ## Lock dependencies
	@echo "Locking dependencies..."
	$(POETRY) lock

check-lock:  ## Check if lock file is up to date
	@echo "Checking lock file..."
	$(POETRY) lock --check

update-deps:  ## Update all dependencies
	@echo "Updating dependencies..."
	$(POETRY) update

update-deps-dry-run:  ## Show what would be updated
	@echo "Dry run of dependency updates..."
	$(POETRY) update --dry-run

# Pre-commit
pre-commit:  ## Run pre-commit on staged files
	@echo "Running pre-commit on staged files..."
	$(PRECOMMIT) run

pre-commit-all:  ## Run pre-commit on all files
	@echo "Running pre-commit on all files..."
	$(PRECOMMIT) run --all-files

pre-commit-install:  ## Install pre-commit hooks
	@echo "Installing pre-commit hooks..."
	$(PRECOMMIT) install
	$(PRECOMMIT) install --hook-type pre-push

# Examples
run-example: run-example-simple  ## Run simple example (default)

run-example-simple:  ## Run simple state machine example
	@echo "Running simple example..."
	$(POETRY) run python examples/simple_state_machine.py

run-example-advanced:  ## Run advanced state machine example
	@echo "Running advanced example..."
	$(POETRY) run python examples/advanced_state_machine.py

# Virtual Environment
venv-show:  ## Show virtual environment info
	@echo "Virtual environment info:"
	$(POETRY) env info

venv-list:  ## List virtual environments
	@echo "Available virtual environments:"
	$(POETRY) env list

venv-remove:  ## Remove current virtual environment
	@echo "Removing current virtual environment..."
	$(POETRY) env remove $(shell $(POETRY) env info --path 2>/dev/null | xargs basename 2>/dev/null || echo "")

# CI/CD
ci: install-dev check test-cov  ## Run CI pipeline (install, check, test with coverage)

# Validation
validate: check test-cov  ## Validate code quality and tests

# All-in-one
all: clean install-dev check test-cov build  ## Clean, install, check, test, and build

# Shell
shell:  ## Open Poetry shell
	@echo "Opening Poetry shell..."
	$(POETRY) shell

# Run specific module
run:  ## Run a module (usage: make run module=state_machine.core)
ifndef module
	$(error Please specify module with module=path.to.module)
endif
	$(POETRY) run python -m $(module)

# Interactive Python
ipython:  ## Open IPython shell
	@echo "Opening IPython shell..."
	$(POETRY) run ipython

# Jupyter
jupyter:  ## Start Jupyter notebook
	@echo "Starting Jupyter notebook..."
	$(POETRY) run jupyter notebook

# Package info
info:  ## Show package information
	@echo "Package Information:"
	@echo "===================="
	$(POETRY) show --tree
	@echo
	@echo "Package details:"
	$(POETRY) show $(PACKAGE_NAME) || true

# Dependency tree
tree:  ## Show dependency tree
	@echo "Dependency tree:"
	$(POETRY) show --tree

# Check for vulnerabilities
audit:  ## Check for security vulnerabilities
	@echo "Checking for security vulnerabilities..."
	$(POETRY) run pip-audit || echo "pip-audit not installed. Install with: poetry add pip-audit --group dev"

# Code complexity
complexity:  ## Check code complexity
	@echo "Checking code complexity..."
	$(POETRY) run radon cc $(MODULE_NAME) -a

# Lines of code
loc:  ## Count lines of code
	@echo "Lines of code:"
	@find $(MODULE_NAME) -name "*.py" -type f -exec cat {} \; | wc -l
	@echo "Lines in $(MODULE_NAME)/"
