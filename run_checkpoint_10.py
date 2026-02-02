#!/usr/bin/env python3
"""
Checkpoint 10: Ensure Kafka and Merkle tree work
Run all Kafka and Merkle tree tests
"""
import subprocess
import sys
import os

def run_test_suite(test_path, description):
    """Run a test suite and return results"""
    print(f"\n{'='*80}")
    print(f"Running: {description}")
    print(f"{'='*80}")
    
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', test_path, '-v', '--tb=short', '-x'],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    return result.returncode == 0

def main():
    """Run all checkpoint tests"""
    print("="*80)
    print("CHECKPOINT 10: Ensure Kafka and Merkle tree work")
    print("="*80)
    
    test_suites = [
        ('tests/unit/test_merkle_tree.py', 'Merkle Tree Core Tests'),
        ('tests/unit/test_merkle_batcher_signer.py', 'Merkle Batcher and Signer Tests'),
        ('tests/unit/test_merkle_verifier.py', 'Merkle Verifier Tests'),
        ('tests/unit/test_kafka_producer.py', 'Kafka Producer Tests'),
        ('tests/unit/test_kafka_consumer.py', 'Kafka Consumer Tests'),
        ('tests/unit/test_kafka_ledger_writer.py', 'Kafka LedgerWriter Consumer Tests'),
    ]
    
    results = {}
    for test_path, description in test_suites:
        results[description] = run_test_suite(test_path, description)
    
    # Print summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    
    all_passed = True
    for description, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{description}: {status}")
        if not passed:
            all_passed = False
    
    print(f"{'='*80}")
    
    if all_passed:
        print("\n✓ All Kafka and Merkle tree tests passed!")
        print("Checkpoint 10 complete.")
        return 0
    else:
        print("\n✗ Some tests failed. Please review the output above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
