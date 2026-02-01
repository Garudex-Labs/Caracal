#!/usr/bin/env python3
"""
Run final tests and generate report
"""

import subprocess
import sys
from pathlib import Path

def main():
    os.chdir(Path(__file__).parent)
    
    print("="*80)
    print("RUNNING FINAL TEST SUITE")
    print("="*80)
    
    # Run pytest with verbose output
    cmd = [
        sys.executable, '-m', 'pytest',
        'tests/',
        '-v',
        '--tb=short',
        '--cov=caracal',
        '--cov-report=term-missing',
        '--cov-report=html'
    ]
    
    print(f"\nCommand: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd)
    
    print("\n" + "="*80)
    print("TEST SUITE COMPLETE")
    print("="*80)
    print(f"Exit code: {result.returncode}")
    
    if result.returncode == 0:
        print("\n✓ All tests passed!")
        print("\nCoverage report generated in htmlcov/index.html")
    else:
        print("\n✗ Some tests failed")
    
    return result.returncode

if __name__ == '__main__':
    import os
    sys.exit(main())
