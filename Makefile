.PHONY: help install test test-security test-quality test-integration test-performance test-coverage clean lint format type-check setup-dev run-server download-data

# Default target
help:
	@echo "🚀 NIST MCP Server Development Commands"
	@echo "======================================"
	@echo ""
	@echo "Setup Commands:"
	@echo "  install      Install dependencies with uv"
	@echo "  install-pip  Install dependencies with pip (fallback)"
	@echo "  install-auto Automated installation (uv + deps + data)"
	@echo "  setup-dev    Setup development environment"
	@echo ""
	@echo "Testing Commands:"
	@echo "  test         Run all tests"
	@echo "  test-security    Run security tests only"
	@echo "  test-quality     Run code quality tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-performance Run performance tests only"
	@echo "  test-coverage    Run coverage tests only"
	@echo ""
	@echo "Code Quality Commands:"
	@echo "  lint         Run linting (Ruff)"
	@echo "  format       Format code (Ruff + Black)"
	@echo "  type-check   Run type checking (MyPy)"
	@echo "  security     Run security scans (Bandit + Safety)"
	@echo ""
	@echo "Development Commands:"
	@echo "  run-server   Start the MCP server"
	@echo "  download-data Download NIST data"
	@echo "  clean        Clean build artifacts"

# Installation and setup
install:
	@echo "📦 Installing dependencies with uv..."
	uv sync --dev

install-pip:
	@echo "📦 Installing dependencies with pip (fallback)..."
	pip install -e ".[dev]"

install-auto:
	@echo "🚀 Running automated installation..."
	./scripts/install.sh

setup-dev: install
	@echo "🔧 Setting up development environment..."
	pre-commit install
	@echo "✅ Development environment ready!"

# Testing commands
test:
	@echo "🧪 Running all tests..."
	python scripts/run_tests.py --all

test-security:
	@echo "🔒 Running security tests..."
	python scripts/run_tests.py --security

test-quality:
	@echo "📊 Running code quality tests..."
	python scripts/run_tests.py --quality

test-integration:
	@echo "🔗 Running integration tests..."
	python scripts/run_tests.py --integration

test-performance:
	@echo "⚡ Running performance tests..."
	python scripts/run_tests.py --performance

test-coverage:
	@echo "📈 Running coverage tests..."
	python scripts/run_tests.py --coverage

# Code quality commands
lint:
	@echo "🔍 Running linting..."
	ruff check src/ tests/ scripts/

format:
	@echo "🎨 Formatting code..."
	ruff format src/ tests/ scripts/
	black src/ tests/ scripts/
	isort src/ tests/ scripts/

type-check:
	@echo "🔍 Running type checking..."
	mypy src/

security:
	@echo "🔒 Running security scans..."
	bandit -r src/
	safety check

# Development commands
run-server:
	@echo "🚀 Starting MCP server..."
	python -m nist_mcp.server

download-data:
	@echo "📥 Downloading NIST data..."
	python scripts/download_nist_data.py

# Cleanup
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -f .coverage
	rm -f coverage.xml
	rm -f test-report.json
	rm -f bandit-report.json
	rm -f safety-report.json
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Pre-commit hooks
pre-commit:
	@echo "🔄 Running pre-commit hooks..."
	pre-commit run --all-files

# Quick development cycle
dev-cycle: format lint type-check test-quality
	@echo "✅ Development cycle complete!"

# CI simulation
ci-local: clean install format lint type-check security test
	@echo "✅ Local CI simulation complete!"