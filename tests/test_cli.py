"""
Pytest test suite for TrapTrace CLI tool (soroban-explain).
"""

import pytest
from traptrace_cli.data import load_entries
from traptrace_cli.search_engine import search_errors, calculate_match_score
from traptrace_cli.formatter import render_entry_terminal

def test_load_bundled_entries():
    entries = load_entries()
    assert len(entries) >= 10
    ids = [e["id"] for e in entries]
    assert "budget-exceeded" in ids
    assert "entry-archived-ttl-expired" in ids

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
    assert "✔ Verified" in output
