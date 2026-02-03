#!/usr/bin/env python3
"""Check test results and print summary."""
import re

with open('test_output_full.txt', 'r') as f:
    content = f.read()

# Find test summary
summary_match = re.search(r'=+ (.*?) in [\d.]+s =+', content, re.DOTALL)
if summary_match:
    print("TEST SUMMARY:")
    print(summary_match.group(1))
    print()

# Find failures
failures = re.findall(r'FAILED (.*?) -', content)
if failures:
    print(f"FAILED TESTS ({len(failures)}):")
    for failure in failures:
        print(f"  - {failure}")
    print()

# Find passed count
passed_match = re.search(r'(\d+) passed', content)
if passed_match:
    print(f"PASSED: {passed_match.group(1)}")

# Find failed count
failed_match = re.search(r'(\d+) failed', content)
if failed_match:
    print(f"FAILED: {failed_match.group(1)}")

# Find warnings count
warnings_match = re.search(r'(\d+) warnings', content)
if warnings_match:
    print(f"WARNINGS: {warnings_match.group(1)}")
