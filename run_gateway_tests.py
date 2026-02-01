#!/usr/bin/env python3
"""Run gateway-related tests"""
import subprocess
import sys

def run_tests():
    """Run all gateway tests"""
    test_files = [
        "tests/unit/test_gateway_auth.py",
        "tests/unit/test_gateway_replay_protection.py",
        "tests/unit/test_gateway_cache.py",
        "tests/unit/test_gateway_proxy.py",
        "tests/unit/test_gateway_proxy_cache_integration.py"
    ]
    
    print("="*80)
    print("RUNNING GATEWAY PROXY TESTS")
    print("="*80)
    
    all_passed = True
    results = {}
    
    for test_file in test_files:
        print(f"\n{'='*80}")
        print(f"Running: {test_file}")
        print(f"{'='*80}\n")
        
        result = subprocess.run(
            ["python3", "-m", "pytest", test_file, "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        passed = result.returncode == 0
        results[test_file] = passed
        all_passed = all_passed and passed
        
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"\n{status} - Exit code: {result.returncode}")
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_file, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_file:60s}: {status}")
    
    print("="*80)
    
    if all_passed:
        print("\n✅ All gateway tests passed!")
        return 0
    else:
        print("\n✗ Some gateway tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(run_tests())
