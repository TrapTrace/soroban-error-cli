"""
Pytest test suite for TrapTrace CLI tool (soroban-explain).
"""

import pytest
from traptrace_cli.data import load_entries
from traptrace_cli.search_engine import search_errors, calculate_match_score
from traptrace_cli.formatter import render_entry_terminal

def test_load_bundled_entries():
    entries = load_entries()
    assert len(entries) >= 35
    ids = [e["id"] for e in entries]
    assert "budget-exceeded" in ids
    assert "entry-archived-ttl-expired" in ids
    assert "host-invalid-action" in ids
    assert "storage-ledger-entry-not-found" in ids
    assert "contract-data-size-exceeds-limit" in ids
    assert "wasm-memory-exhausted" in ids
    assert "auth-invalid-signature" in ids
    assert "sub-invocation-user-error" in ids
    assert "require-auth-missing" in ids
    assert "arith-error" in ids
    assert "invalid-chain-id" in ids
    assert "crypto-verification-failed" in ids
    assert "wasm-verification-failed" in ids
    assert "temporary-storage-expired" in ids
    assert "instance-storage-expired" in ids
    assert "option-unwrap-none" in ids
    assert "vec-index-out-of-bounds" in ids
    assert "map-key-not-found" in ids
    assert "instance-already-initialized" in ids
    assert "cross-contract-reentrancy-blocked" in ids
    assert "unauthorized-storage-access" in ids
    assert "crypto-curve25519-invalid-scalar" in ids
    assert "tx-simulation-fee-insufficient" in ids
    assert "contract-spec-missing" in ids

def test_search_by_keyword():
    entries = load_entries()
    results = search_errors(entries, query="budget")
    assert len(results) > 0
    assert results[0]["id"] == "budget-exceeded"

def test_search_by_category():
    entries = load_entries()
    results = search_errors(entries, category="host-error")
    assert all(e["category"] == "host-error" for e in results)

def test_search_verified_only():
    entries = load_entries()
    results = search_errors(entries, verified_only=True)
    assert all(e["verified"] is True for e in results)

def test_render_formatter():
    entry = {
        "id": "test-error",
        "title": "Test Error Title",
        "category": "host-error",
        "error_code": "TestCode",
        "verified": True,
        "summary": "This is a test error summary."
    }
    output = render_entry_terminal(entry)
    assert "test-error" in output
    assert "Test Error Title" in output

def test_ranked_search_scores():
    entries = load_entries()
    results = search_errors(entries, query="budget", include_scores=True)
    assert len(results) > 0
    assert "_score" in results[0]
    assert results[0]["_score"] > 20.0
    assert results[0]["id"] == "budget-exceeded"

def test_typo_tolerant_search():
    entries = load_entries()
    results = search_errors(entries, query="budgt")
    assert len(results) > 0
    assert any(r["id"] == "budget-exceeded" for r in results)

def test_export_output_helper(tmp_path):
    from traptrace_cli.cli import export_output
    export_file = tmp_path / "test_report.md"
    export_output("# Test Markdown Report", str(export_file))
    assert export_file.exists()
    assert export_file.read_text(encoding="utf-8") == "# Test Markdown Report"

def test_calculate_match_score():
    entry = {
        "id": "arith-error",
        "title": "Arithmetic Error",
        "summary": "HostError ArithDomain panic on overflow",
        "tags": ["arithmetic", "overflow", "math"]
    }
    score = calculate_match_score(entry, "arithmetic")
    assert score > 0
