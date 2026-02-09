import sys
try:
    from caracal.config import settings
    print("Import successful")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)
