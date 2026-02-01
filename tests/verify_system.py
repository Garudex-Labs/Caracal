#!/usr/bin/env python3
"""
System verification script for Caracal Core v0.1 Final Checkpoint
Verifies all components are working correctly
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def verify_imports():
    """Verify all modules can be imported"""
    print("="*80)
    print("1. VERIFYING MODULE IMPORTS")
    print("="*80)
    
    modules = [
        "caracal",
        "caracal.core.identity",
        "caracal.core.policy",
        "caracal.core.ledger",
        "caracal.core.metering",
        "caracal.core.pricebook",
        "caracal.core.retry",
        "caracal.sdk.client",
        "caracal.sdk.context",
        "caracal.cli.main",
        "caracal.cli.agent",
        "caracal.cli.policy",
        "caracal.cli.ledger",
        "caracal.cli.pricebook",
        "caracal.config.settings",
        "caracal.exceptions",
        "caracal.logging_config",
    ]
    
    failed = []
    for module in modules:
        try:
            __import__(module)
            print(f"✓ {module}")
        except Exception as e:
            print(f"✗ {module}: {e}")
            failed.append(module)
    
    if failed:
        print(f"\n✗ {len(failed)} modules failed to import")
        return False
    else:
        print(f"\n✓ All {len(modules)} modules imported successfully")
        return True

def verify_cli_commands():
    """Verify CLI commands are available"""
    print("\n" + "="*80)
    print("2. VERIFYING CLI COMMANDS")
    print("="*80)
    
    try:
        from caracal.cli.main import cli
        
        # Get all commands
        commands = list(cli.commands.keys())
        print(f"Available commands: {', '.join(commands)}")
        
        expected_commands = ['agent', 'policy', 'ledger', 'pricebook', 'init']
        missing = [cmd for cmd in expected_commands if cmd not in commands]
        
        if missing:
            print(f"✗ Missing commands: {', '.join(missing)}")
            return False
        else:
            print(f"✓ All expected CLI commands available")
            return True
    except Exception as e:
        print(f"✗ Failed to verify CLI: {e}")
        return False

def verify_core_functionality():
    """Verify core functionality works"""
    print("\n" + "="*80)
    print("3. VERIFYING CORE FUNCTIONALITY")
    print("="*80)
    
    import tempfile
    from decimal import Decimal
    from caracal.core.identity import AgentRegistry
    from caracal.core.policy import PolicyStore
    from caracal.core.pricebook import Pricebook
    from caracal.core.ledger import LedgerWriter, LedgerQuery
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Test Agent Registry
            print("\nTesting Agent Registry...")
            registry = AgentRegistry(str(tmppath / "agents.json"))
            agent = registry.register_agent("test-agent", "test@example.com")
            assert agent.name == "test-agent"
            print("✓ Agent Registry works")
            
            # Test Policy Store
            print("\nTesting Policy Store...")
            policy_store = PolicyStore(str(tmppath / "policies.json"), registry)
            policy = policy_store.create_policy(
                agent.agent_id,
                Decimal("100.00"),
                "daily"
            )
            assert policy.agent_id == agent.agent_id
            print("✓ Policy Store works")
            
            # Test Pricebook
            print("\nTesting Pricebook...")
            pricebook_path = tmppath / "pricebook.csv"
            pricebook_path.write_text(
                "resource_type,price_per_unit,currency,updated_at\n"
                "test.resource,0.01,USD,2024-01-01T00:00:00Z\n"
            )
            pricebook = Pricebook(str(pricebook_path))
            price = pricebook.get_price("test.resource")
            assert price == Decimal("0.01")
            print("✓ Pricebook works")
            
            # Test Ledger
            print("\nTesting Ledger...")
            ledger_path = tmppath / "ledger.jsonl"
            ledger_writer = LedgerWriter(str(ledger_path))
            from datetime import datetime
            ledger_writer.append_event(
                agent_id=agent.agent_id,
                resource_type="test.resource",
                quantity=Decimal("10"),
                cost=Decimal("0.10"),
                timestamp=datetime.utcnow()
            )
            
            ledger_query = LedgerQuery(str(ledger_path))
            events = ledger_query.get_events(agent_id=agent.agent_id)
            assert len(events) == 1
            print("✓ Ledger works")
            
            print("\n✓ All core functionality verified")
            return True
            
    except Exception as e:
        print(f"\n✗ Core functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_sdk():
    """Verify SDK functionality"""
    print("\n" + "="*80)
    print("4. VERIFYING SDK")
    print("="*80)
    
    try:
        from caracal.sdk.client import CaracalClient
        from caracal.sdk.context import BudgetCheckContext
        
        print("✓ SDK modules imported successfully")
        
        # Note: Full SDK testing requires a complete setup
        # which is covered in integration tests
        print("✓ SDK structure verified (full testing in integration tests)")
        return True
        
    except Exception as e:
        print(f"✗ SDK verification failed: {e}")
        return False

def verify_exception_hierarchy():
    """Verify exception hierarchy"""
    print("\n" + "="*80)
    print("5. VERIFYING EXCEPTION HIERARCHY")
    print("="*80)
    
    try:
        from caracal.exceptions import (
            CaracalError,
            AgentNotFoundError,
            DuplicateAgentNameError,
            InvalidPolicyError,
            BudgetExceededError,
            PolicyEvaluationError,
            LedgerError,
            MeteringError,
            PricebookError,
            ConfigurationError,
        )
        
        exceptions = [
            "CaracalError",
            "AgentNotFoundError",
            "DuplicateAgentNameError",
            "InvalidPolicyError",
            "BudgetExceededError",
            "PolicyEvaluationError",
            "LedgerError",
            "MeteringError",
            "PricebookError",
            "ConfigurationError",
        ]
        
        for exc_name in exceptions:
            print(f"✓ {exc_name}")
        
        print(f"\n✓ All {len(exceptions)} exceptions defined")
        return True
        
    except Exception as e:
        print(f"✗ Exception verification failed: {e}")
        return False

def verify_logging():
    """Verify logging configuration"""
    print("\n" + "="*80)
    print("6. VERIFYING LOGGING CONFIGURATION")
    print("="*80)
    
    try:
        from caracal.logging_config import setup_logging
        import logging
        
        # Test logging setup
        logger = setup_logging("test", level="INFO")
        assert isinstance(logger, logging.Logger)
        
        print("✓ Logging configuration works")
        return True
        
    except Exception as e:
        print(f"✗ Logging verification failed: {e}")
        return False

def count_test_files():
    """Count test files"""
    print("\n" + "="*80)
    print("7. TEST FILE INVENTORY")
    print("="*80)
    
    test_dir = Path(__file__).parent / "tests"
    
    unit_tests = list((test_dir / "unit").glob("test_*.py"))
    integration_tests = list((test_dir / "integration").glob("test_*.py"))
    property_tests = list((test_dir / "property").glob("test_*.py"))
    
    print(f"Unit tests: {len(unit_tests)}")
    for test in unit_tests:
        print(f"  - {test.name}")
    
    print(f"\nIntegration tests: {len(integration_tests)}")
    for test in integration_tests:
        print(f"  - {test.name}")
    
    print(f"\nProperty tests: {len(property_tests)}")
    if property_tests:
        for test in property_tests:
            print(f"  - {test.name}")
    else:
        print("  (No property test files found - tests marked as optional)")
    
    total = len(unit_tests) + len(integration_tests) + len(property_tests)
    print(f"\nTotal test files: {total}")
    
    return True

def main():
    """Run all verifications"""
    print("\n" + "="*80)
    print("CARACAL CORE v0.1 - FINAL CHECKPOINT VERIFICATION")
    print("="*80)
    
    results = {
        "Module Imports": verify_imports(),
        "CLI Commands": verify_cli_commands(),
        "Core Functionality": verify_core_functionality(),
        "SDK": verify_sdk(),
        "Exception Hierarchy": verify_exception_hierarchy(),
        "Logging": verify_logging(),
        "Test Inventory": count_test_files(),
    }
    
    # Print summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    
    for check, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{check:30s}: {status}")
    
    print("="*80)
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✓ All verifications passed!")
        print("\nNext steps:")
        print("1. Run full test suite: python3 -m pytest tests/ -v")
        print("2. Check coverage: python3 -m pytest tests/ --cov=caracal --cov-report=html")
        print("3. Test CLI manually: caracal --help")
        return 0
    else:
        print("\n✗ Some verifications failed. Please review the output above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
