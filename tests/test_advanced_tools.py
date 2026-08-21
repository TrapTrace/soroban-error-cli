"""
Comprehensive pytest test suite for TrapTrace CLI advanced tools:
- TUI gauges & dashboards
- BatchInspector
- AuthChecker
- FixGenerator
- CLI subcommands (batch-inspect, auth-check, fix)
"""

import os
import json
import pytest
from unittest.mock import MagicMock, patch

from traptrace_cli.tui import (
    render_meter_bar,
    render_gauge,
    render_resource_dashboard,
    render_box,
    DEFAULT_MAX_CPU_INSTRUCTIONS
)
from traptrace_cli.batch_inspector import (
    BatchInspector,
    render_batch_report_terminal,
    render_batch_report_markdown
)
from traptrace_cli.auth_checker import (
    AuthChecker,
    render_auth_report_terminal
)
from traptrace_cli.fix_generator import (
    FixGenerator,
    render_fix_terminal,
    REMEDIATION_SNIPPETS
)
from traptrace_cli.rpc_client import SorobanRpcClient

# --- TUI Tests ---

def test_tui_render_meter_bar():
    bar_low = render_meter_bar(20, 100, width=10)
    assert len(bar_low) > 0
    assert "█" in bar_low
    assert "░" in bar_low

    bar_high = render_meter_bar(95, 100, width=10)
    assert "█" in bar_high

    bar_zero = render_meter_bar(0, 0, width=10)
    assert len(bar_zero) > 0

def test_tui_render_gauge():
    gauge_cpu = render_gauge("CPU Gas", 45_000_000, DEFAULT_MAX_CPU_INSTRUCTIONS, unit="instructions")
    assert "CPU Gas" in gauge_cpu
    assert "45.0%" in gauge_cpu
    assert "45.00M" in gauge_cpu

    gauge_mem = render_gauge("WASM Memory", 10 * 1024 * 1024, 40 * 1024 * 1024, unit="bytes")
    assert "WASM Memory" in gauge_mem
    assert "10.00 MB" in gauge_mem

def test_tui_render_resource_dashboard():
    dashboard = render_resource_dashboard(
        cpu_insns=50_000_000,
        mem_bytes=20 * 1024 * 1024,
        storage_bytes=32 * 1024
    )
    assert "Soroban Resource Consumption Meter" in dashboard
    assert "CPU Instructions" in dashboard
    assert "WASM Memory" in dashboard
    assert "Storage Entry" in dashboard

def test_tui_render_box():
    box = render_box("Test Title", ["Line 1", "Line 2"])
    assert "Test Title" in box
    assert "Line 1" in box
    assert "Line 2" in box

# --- BatchInspector Tests ---

def test_batch_inspector_hashes():
    client = SorobanRpcClient("testnet")
    inspector = BatchInspector(rpc_client=client)

    # Mock inspector.inspect output
    mock_success = {
        "tx_hash": "a"*64,
        "is_successful": True,
        "resource_metrics": {"cpu_instructions": 5_000_000, "memory_bytes": 102400},
        "diagnostics": {"matched": False}
    }
    mock_fail = {
        "tx_hash": "b"*64,
        "is_successful": False,
        "resource_metrics": {"cpu_instructions": 2_000_000, "memory_bytes": 51200},
        "diagnostics": {"matched": True, "entry_id": "arith-error", "category": "host-error", "error_code": "HostError::ArithDomain"}
    }

    with patch.object(inspector.inspector, "inspect", side_effect=[mock_success, mock_fail]):
        report = inspector.inspect_hashes(["a"*64, "b"*64], delay_between_requests=0)

        s = report["summary"]
        assert s["total_inspected"] == 2
        assert s["successful_transactions"] == 1
        assert s["failed_transactions"] == 1
        assert s["failure_rate_percent"] == 50.0
        assert s["average_cpu_instructions"] == 3_500_000
        assert "host-error" in report["category_breakdown"]
        assert len(report["top_matched_catalog_entries"]) == 1
        assert report["top_matched_catalog_entries"][0][0] == "arith-error"

        term_out = render_batch_report_terminal(report)
        assert "Multi-Transaction Batch Inspection" in term_out
        assert "arith-error" in term_out

        md_out = render_batch_report_markdown(report)
        assert "Multi-Transaction Diagnostic Report" in md_out
        assert "`arith-error`" in md_out

def test_batch_inspector_file_load(tmp_path):
    client = SorobanRpcClient("testnet")
    inspector = BatchInspector(rpc_client=client)

    test_file = tmp_path / "txs.json"
    test_file.write_text(json.dumps(["c"*64, "d"*64]))

    mock_resp = {
        "tx_hash": "c"*64,
        "is_successful": True,
        "resource_metrics": {},
        "diagnostics": {}
    }

    with patch.object(inspector.inspector, "inspect", return_value=mock_resp):
        report = inspector.inspect_file(str(test_file), max_limit=1)
        assert report["summary"]["total_inspected"] == 1

# --- AuthChecker Tests ---

def test_auth_checker_success():
    client = SorobanRpcClient("testnet")
    checker = AuthChecker(rpc_client=client)

    mock_sim_valid = {
        "is_valid": True,
        "simulated_result": {
            "result": {
                "auth": [
                    {
                        "credentials": {
                            "type": "AddressCredentials",
                            "address": "GBYXYZ123",
                            "nonce": 1
                        },
                        "root_invocation": {
                            "function": "transfer",
                            "contract_id": "CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
                            "sub_invocations": []
                        }
                    }
                ]
            }
        },
        "diagnostic_events": []
    }

    with patch.object(checker.simulator, "simulate", return_value=mock_sim_valid):
        report = checker.check_xdr("AAAAAgAAAAB6QZ5cAAAAAA==")
        assert report["is_valid"] is True
        assert report["status"] == "PASS"
        assert report["auth_entries_count"] == 1
        assert report["auth_trees"][0]["address"] == "GBYXYZ123"

        term_out = render_auth_report_terminal(report)
        assert "Contract Authorization Tree Validator" in term_out
        assert "GBYXYZ123" in term_out

def test_auth_checker_trap_detection():
    client = SorobanRpcClient("testnet")
    checker = AuthChecker(rpc_client=client)

    mock_sim_invalid = {
        "is_valid": False,
        "simulated_result": {
            "error": "HostError: Error(Auth, InvalidAction)"
        },
        "diagnostic_events": [
            {
                "contract_id": "CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
                "topics": ["error", "auth"],
                "data": "missing required authorization for address GABC"
            }
        ]
    }

    with patch.object(checker.simulator, "simulate", return_value=mock_sim_invalid):
        report = checker.check_xdr("AAAAAgAAAAB6QZ5cAAAAAA==")
        assert report["is_valid"] is False
        assert report["status"] == "FAIL"
        assert len(report["detected_issues"]) == 1
        assert "missing required authorization" in report["detected_issues"][0]["details"]

        term_out = render_auth_report_terminal(report)
        assert "Detected Authorization Errors & Traps" in term_out
        assert "traptrace fix require-auth-missing" in term_out

# --- FixGenerator Tests ---

def test_fix_generator_entries():
    generator = FixGenerator()
    
    # Test major error IDs
    for error_id in ["arith-error", "require-auth-missing", "auth-invalid-signature", "entry-archived-ttl-expired", "contract-data-size-exceeds-limit", "wasm-memory-exhausted"]:
        fix = generator.get_fix(error_id)
        assert fix is not None
        assert "title" in fix
        assert "bad_code" in fix
        assert "fix_code" in fix

    all_fixes = generator.generate_all()
    assert len(all_fixes) >= 10

def test_fix_generator_render():
    generator = FixGenerator()
    fix = generator.get_fix("arith-error")
    term = render_fix_terminal("arith-error", fix)
    assert "Auto-Fix Generator" in term
    assert "arith-error" in term
    assert "Checked Arithmetic" in term
    assert "checked_mul" in term

def test_fix_generator_unknown():
    generator = FixGenerator()
    fix = generator.get_fix("nonexistent-error-12345")
    assert fix is None
