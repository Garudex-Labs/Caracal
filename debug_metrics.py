
print("Importing caracal.monitoring.metrics...")
try:
    from caracal.monitoring.metrics import MetricsRegistry
    print("Import successful.")
except Exception as e:
    print(f"Import failed: {e}")

print("Instantiating MetricsRegistry...")
try:
    registry = MetricsRegistry()
    print("Instantiation successful.")
except Exception as e:
    print(f"Instantiation failed: {e}")
