#!/usr/bin/env python3
"""
Comprehensive Checkpoint 10: Ensure Kafka and Merkle tree work
Tests all Kafka and Merkle tree functionality
"""
import subprocess
import sys
import os

def run_test_file(test_file, description):
    """Run a single test file and capture results"""
    print(f"\n{'='*80}")
    print(f"Testing: {description}")
    print(f"File: {test_file}")
    print(f"{'='*80}")
    
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', test_file, '-v', '--tb=short'],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    # Print output
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    passed = result.returncode == 0
    status = "✓ PASSED" if passed else "✗ FAILED"
    print(f"\nResult: {status}")
    
    return passed, result.stdout, result.stderr

def main():
    """Run all checkpoint 10 tests"""
    print("="*80)
    print("CHECKPOINT 10: Ensure Kafka and Merkle tree work")
    print("="*80)
    print("\nThis checkpoint verifies that:")
    print("  1. Merkle tree core functionality works")
    print("  2. Merkle batcher and signer work")
    print("  3. Merkle verifier works")
    print("  4. Kafka producer works")
    print("  5. Kafka consumer base class works")
    print("  6. Kafka LedgerWriter consumer works")
    
    test_suites = [
        ('tests/unit/test_merkle_tree.py', 'Merkle Tree Core'),
        ('tests/unit/test_merkle_batcher_signer.py', 'Merkle Batcher and Signer'),
        ('tests/unit/test_merkle_verifier.py', 'Merkle Verifier'),
        ('tests/unit/test_kafka_producer.py', 'Kafka Producer'),
        ('tests/unit/test_kafka_consumer.py', 'Kafka Consumer Base'),
        ('tests/unit/test_kafka_ledger_writer.py', 'Kafka LedgerWriter Consumer'),
    ]
    
    results = {}
    outputs = {}
    
    for test_file, description in test_suites:
        passed, stdout, stderr = run_test_file(test_file, description)
        results[description] = passed
        outputs[description] = (stdout, stderr)
    
    # Print summary
    print(f"\n{'='*80}")
    print("CHECKPOINT 10 TEST SUMMARY")
    print(f"{'='*80}")
    
    all_passed = True
    for description, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{description:40s} {status}")
        if not passed:
            all_passed = False
    
    print(f"{'='*80}")
    
    if all_passed:
        print("\n✓✓✓ CHECKPOINT 10 COMPLETE ✓✓✓")
        print("\nAll Kafka and Merkle tree tests passed!")
        print("The event-driven architecture and cryptographic ledger are working correctly.")
        print("\nNext steps:")
        print("  - Continue with Task 11: Implement policy versioning")
        print("  - Or run integration tests with live Kafka and PostgreSQL")
        return 0
    else:
        print("\n✗ CHECKPOINT 10 INCOMPLETE")
        print("\nSome tests failed. Please review the output above.")
        print("\nFailed test suites:")
        for description, passed in results.items():
            if not passed:
                print(f"  - {description}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
