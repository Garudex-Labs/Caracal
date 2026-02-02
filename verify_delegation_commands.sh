#!/bin/bash
# Verification script for delegation CLI commands

echo "==================================="
echo "Verifying Delegation CLI Commands"
echo "==================================="
echo ""

echo "1. Checking agent register --help includes new options..."
caracal agent register --help 2>&1 | grep -q "parent-id" && echo "✓ --parent-id option found" || echo "✗ --parent-id option NOT found"
caracal agent register --help 2>&1 | grep -q "delegated-budget" && echo "✓ --delegated-budget option found" || echo "✗ --delegated-budget option NOT found"

echo ""
echo "2. Checking delegation list command exists..."
caracal delegation list --help 2>&1 | grep -q "List delegation" && echo "✓ delegation list command found" || echo "✗ delegation list command NOT found"

echo ""
echo "3. Checking delegation revoke command exists..."
caracal delegation revoke --help 2>&1 | grep -q "Revoke a delegated" && echo "✓ delegation revoke command found" || echo "✗ delegation revoke command NOT found"

echo ""
echo "==================================="
echo "Verification Complete"
echo "==================================="
