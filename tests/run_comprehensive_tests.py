#!/usr/bin/env python3
"""
Comprehensive test runner for Caracal Core v0.1
Runs all tests and generates a detailed report
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and capture output"""
    print(f"\n{'='*80}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*80}\n")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        print(f"\nExit Code: {result.returncode}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"ERROR: Command timed out after 300 seconds")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    """Run comprehensive test suite"""
    os.chdir(Path(__file__).parent)
    
    results = {}
    
    # 1. Run unit tests
    results['unit_tests'] = run_command(
        ['python3', '-m', 'pytest', 'tests/unit/', '-v', '--tb=short'],
        "Unit Tests"
    )
    
    # 2. Run integration tests
    results['integration_tests'] = run_command(
        ['python3', '-m', 'pytest', 'tests/integration/', '-v', '--tb=short'],
        "Integration Tests"
    )
    
    # 3. Run property-based tests (if any exist)
    property_tests_exist = len(list(Path('tests/property').glob('test_*.py'))) > 0
    if property_tests_exist:
        results['property_tests'] = run_command(
            ['python3', '-m', 'pytest', 'tests/property/', '-v', '--tb=short'],
            "Property-Based Tests"
        )
    else:
        print("\n" + "="*80)
        print("Property-Based Tests: SKIPPED (no test files found)")
        print("="*80)
        results['property_tests'] = None
    
    # 4. Run all tests with coverage
    results['coverage'] = run_command(
        ['python3', '-m', 'pytest', 'tests/', '-v', '--cov=caracal', 
         '--cov-report=term-missing', '--cov-report=html'],
        "Full Test Suite with Coverage"
    )
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_type, passed in results.items():
        if passed is None:
            status = "SKIPPED"
        elif passed:
            status = "✓ PASSED"
        else:
            status = "✗ FAILED"
        print(f"{test_type:30s}: {status}")
    
    print("="*80)
    
    # Check if all tests passed
    all_passed = all(result in [True, None] for result in results.values())
    
    if all_passed:
        print("\n✓ All tests passed successfully!")
        return 0
    else:
        print("\n✗ Some tests failed. Please review the output above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
