#!/usr/bin/env python3
"""
Comprehensive Test Runner for NIST MCP Server

Runs all tests including security, performance, and integration tests.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def run_command(cmd, description, capture_output=True):
    """Run a command and return the result"""
    print(f"🔄 {description}...")

    try:
        start_time = time.time()
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture_output,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        end_time = time.time()

        duration = end_time - start_time

        if result.returncode == 0:
            print(f"✅ {description} passed ({duration:.2f}s)")
            return True, result.stdout, result.stderr
        else:
            print(f"❌ {description} failed ({duration:.2f}s)")
            if result.stdout:
                print(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                print(f"STDERR:\n{result.stderr}")
            return False, result.stdout, result.stderr

    except Exception as e:
        print(f"❌ {description} error: {e}")
        return False, "", str(e)


def run_security_tests():
    """Run security-focused tests"""
    print("\n🔒 Running Security Tests")
    print("=" * 50)

    tests = [
        ("ruff check src/ tests/ scripts/ --select=S", "Ruff Security Checks"),
        ("bandit -r src/ -f json -o bandit-report.json", "Bandit Security Scan"),
        ("safety check", "Safety Dependency Check"),
        ("pytest tests/test_security.py -v", "Security Unit Tests"),
    ]

    results = []
    for cmd, desc in tests:
        success, stdout, stderr = run_command(cmd, desc)
        results.append((desc, success, stdout, stderr))

    return results


def run_code_quality_tests():
    """Run code quality tests"""
    print("\n📊 Running Code Quality Tests")
    print("=" * 50)

    tests = [
        ("ruff check src/ tests/ scripts/", "Ruff Linting"),
        ("ruff format --check src/ tests/ scripts/", "Ruff Format Check"),
        ("mypy src/", "Type Checking"),
        ("pytest tests/test_server.py tests/test_data_loader.py -v", "Unit Tests"),
    ]

    results = []
    for cmd, desc in tests:
        success, stdout, stderr = run_command(cmd, desc)
        results.append((desc, success, stdout, stderr))

    return results


def run_integration_tests():
    """Run MCP integration tests"""
    print("\n🔗 Running MCP Integration Tests")
    print("=" * 50)

    tests = [
        ("pytest tests/test_mcp_integration.py -v", "MCP Integration Tests"),
        (
            'python -c "import asyncio; from src.nist_mcp.server import NISTMCPServer; asyncio.run(NISTMCPServer().loader.initialize())"',
            "Server Initialization Test",
        ),
    ]

    results = []
    for cmd, desc in tests:
        success, stdout, stderr = run_command(cmd, desc)
        results.append((desc, success, stdout, stderr))

    return results


def run_performance_tests():
    """Run performance tests"""
    print("\n⚡ Running Performance Tests")
    print("=" * 50)

    tests = [
        ("pytest tests/test_performance.py -v", "Performance Tests"),
    ]

    results = []
    for cmd, desc in tests:
        success, stdout, stderr = run_command(cmd, desc)
        results.append((desc, success, stdout, stderr))

    return results


def run_coverage_tests():
    """Run tests with coverage"""
    print("\n📈 Running Coverage Tests")
    print("=" * 50)

    tests = [
        (
            "pytest --cov=src/nist_mcp --cov-report=term-missing --cov-report=xml --cov-fail-under=70",
            "Coverage Tests",
        ),
    ]

    results = []
    for cmd, desc in tests:
        success, stdout, stderr = run_command(cmd, desc)
        results.append((desc, success, stdout, stderr))

    return results


def generate_report(all_results):
    """Generate a comprehensive test report"""
    print("\n📋 Test Report")
    print("=" * 50)

    total_tests = 0
    passed_tests = 0

    for category, results in all_results.items():
        print(f"\n{category}:")
        for desc, success, stdout, stderr in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status} {desc}")
            total_tests += 1
            if success:
                passed_tests += 1

    print(f"\n📊 Summary: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("🎉 All tests passed! Repository is ready for production.")
        return True
    else:
        print("⚠️  Some tests failed. Please review and fix issues before deployment.")
        return False


def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(
        description="Run comprehensive tests for NIST MCP Server"
    )
    parser.add_argument(
        "--security", action="store_true", help="Run only security tests"
    )
    parser.add_argument(
        "--quality", action="store_true", help="Run only code quality tests"
    )
    parser.add_argument(
        "--integration", action="store_true", help="Run only integration tests"
    )
    parser.add_argument(
        "--performance", action="store_true", help="Run only performance tests"
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Run only coverage tests"
    )
    parser.add_argument("--all", action="store_true", help="Run all tests (default)")
    parser.add_argument(
        "--use-pip", action="store_true", help="Use pip instead of uv for commands"
    )

    args = parser.parse_args()

    # If no specific test type is specified, run all
    if not any(
        [args.security, args.quality, args.integration, args.performance, args.coverage]
    ):
        args.all = True

    print("🚀 NIST MCP Server Test Suite")
    print("=" * 50)

    # Check if uv is available unless --use-pip is specified
    if not args.use_pip:
        try:
            subprocess.run(["uv", "--version"], capture_output=True, check=True)
            print("✅ Using uv for package management")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  uv not found, falling back to pip")
            args.use_pip = True

    all_results = {}

    if args.all or args.quality:
        all_results["Code Quality"] = run_code_quality_tests()

    if args.all or args.security:
        all_results["Security"] = run_security_tests()

    if args.all or args.integration:
        all_results["Integration"] = run_integration_tests()

    if args.all or args.performance:
        all_results["Performance"] = run_performance_tests()

    if args.all or args.coverage:
        all_results["Coverage"] = run_coverage_tests()

    # Generate final report
    success = generate_report(all_results)

    # Create JSON report for CI/CD
    json_report = {
        "timestamp": time.time(),
        "total_categories": len(all_results),
        "results": {},
    }

    for category, results in all_results.items():
        json_report["results"][category] = [
            {
                "test": desc,
                "passed": success,
                "stdout": stdout[:1000] if stdout else "",  # Truncate for JSON
                "stderr": stderr[:1000] if stderr else "",
            }
            for desc, success, stdout, stderr in results
        ]

    # Save JSON report
    with open("test-report.json", "w") as f:
        json.dump(json_report, f, indent=2)

    print("\n📄 Detailed report saved to: test-report.json")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
