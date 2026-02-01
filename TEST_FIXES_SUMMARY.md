# Test Fixes Summary

## Issues Fixed

### 1. JSON Format Tests (2 failures) - FIXED ✓
**Problem**: Logging output was being mixed with JSON output, causing JSON parsing errors.

**Solution**: Changed logging to use stderr instead of stdout in `caracal/logging_config.py`:
- Changed `StreamHandler(sys.stdout)` to `StreamHandler(sys.stderr)`
- Updated tests to use `CliRunner(mix_stderr=False)` to separate logs from JSON output

**Files Modified**:
- `Caracal/caracal/logging_config.py` - Line 45: Changed stdout to stderr
- `Caracal/tests/unit/test_cli_policy.py` - Lines 250, 360: Added `mix_stderr=False` to CliRunner

**Tests Fixed**:
- `test_policy_list_json_format` ✓
- `test_policy_get_json_format` ✓

### 2. Persistence Retry Tests (4 failures) - PARTIALLY FIXED
**Problem**: Mock tests were checking `args[0].endswith('.tmp')` but `args[0]` was a PosixPath object, not a string. Additionally, the retry decorator wasn't working because `_persist()` methods were catching exceptions and re-raising them as different types.

**Solution**: 
1. Fixed mocks to convert Path to string: `str(args[0]) if hasattr(args[0], '__fspath__') else args[0]`
2. Removed try-except blocks from `_persist()` methods to let OSError bubble up to retry decorator
3. Added try-except at call sites to convert OSError to FileWriteError after retries exhausted

**Files Modified**:
- `Caracal/tests/unit/test_persistence_retry.py` - Lines 37, 91, 126, 167: Fixed Path handling in mocks
- `Caracal/caracal/core/identity.py` - Lines 164-202: Removed try-except from `_persist()`, added at call site (line 132)
- `Caracal/caracal/core/policy.py` - Lines 214-250: Removed try-except from `_persist()`, added at call site (line 174)

**Tests Fixed**:
- `test_agent_registry_persist_with_transient_failure` ✓
- `test_policy_store_persist_with_transient_failure` ✓

**Tests Remaining** (need same fix):
- `test_ledger_writer_append_with_transient_failure` - Need to fix ledger.py
- `test_pricebook_persist_with_transient_failure` - Need to fix pricebook.py

### 3. SDK Client Test (1 failure) - NOT YET FIXED
**Problem**: `test_get_remaining_budget_no_policy` expects `None` but gets `Decimal('0')`.

**Solution Needed**: Check the SDK client implementation to see why it returns 0 instead of None when there's no policy.

**Files to Check**:
- `Caracal/caracal/sdk/client.py` - `get_remaining_budget()` method

## Summary

**Total Failures**: 7
**Fixed**: 4 ✓
**Remaining**: 3

**Next Steps**:
1. Apply same fix to `caracal/core/ledger.py` and `caracal/core/pricebook.py`
2. Fix SDK client to return None instead of 0 when no policy exists
3. Run full test suite to confirm all tests pass
