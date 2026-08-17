"""
Pytest test suite for TrapTrace operational modules:
- SorobanRpcClient
- XDR & DiagnosticEvent Decoder
- TransactionInspector
- TransactionSimulator
- ContractEventWatcher
- StorageAuditor
"""

import pytest
import json
import base64
from unittest.mock import MagicMock, patch

from traptrace_cli.rpc_client import SorobanRpcClient, SorobanRpcError
from traptrace_cli.xdr_decoder import (
    decode_scval,
    decode_diagnostic_event,
    parse_diagnostic_events_list,
    extract_trace_summary,
    XdrReader
)
from traptrace_cli.inspector import TransactionInspector
from traptrace_cli.simulator import TransactionSimulator
from traptrace_cli.watcher import ContractEventWatcher
from traptrace_cli.storage_auditor import StorageAuditor

# --- RPC Client Tests ---

def test_rpc_client_networks():
    client_testnet = SorobanRpcClient("testnet")
    assert "testnet" in client_testnet.rpc_url
    assert "Test SDF Network" in client_testnet.passphrase

    client_mainnet = SorobanRpcClient("mainnet")
    assert "mainnet" in client_testnet.rpc_url or "mainnet" in client_mainnet.rpc_url
    assert "Public Global" in client_mainnet.passphrase

    client_custom = SorobanRpcClient("https://custom-rpc.example.com")
    assert client_custom.rpc_url == "https://custom-rpc.example.com"
    assert client_custom.network_name == "custom"

def test_rpc_client_call_mock():
    client = SorobanRpcClient("testnet")
    mock_resp = {"result": {"sequence": 123456, "protocolVersion": 21}}
    
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_cm = MagicMock()
        mock_cm.read.return_value = json.dumps(mock_resp).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_cm

        res = client.get_latest_ledger()
        assert res["sequence"] == 123456

def test_rpc_client_error_response():
    client = SorobanRpcClient("testnet")
    mock_err_resp = {"error": {"code": -32600, "message": "Invalid request parameters"}}
    
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_cm = MagicMock()
        mock_cm.read.return_value = json.dumps(mock_err_resp).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_cm

        with pytest.raises(SorobanRpcError) as exc_info:
            client.get_transaction("fakehash")
        assert "Invalid request" in str(exc_info.value)
        assert exc_info.value.code == -32600

# --- XDR Decoder Tests ---

def test_xdr_decode_scval_primitive():
    # SCVal Symbol: type=15 (int32 0x0000000f), len=4 (0x00000004), string="test"
    raw = b"\x00\x00\x00\x0f\x00\x00\x00\x04test"
    reader = XdrReader(raw)
    val = decode_scval(reader)
    assert val == "test"

def test_xdr_decode_scval_u32():
    # SCVal U32: type=3, val=42
    raw = b"\x00\x00\x00\x03\x00\x00\x00\x2a"
    reader = XdrReader(raw)
    val = decode_scval(reader)
    assert val == 42

def test_xdr_decode_scval_error():
    # SCVal Error: type=2, error_type=5 (BudgetError), code=1
    raw = b"\x00\x00\x00\x02\x00\x00\x00\x05\x00\x00\x00\x01"
    reader = XdrReader(raw)
    val = decode_scval(reader)
    assert isinstance(val, dict)
    assert val["error_type"] == "BudgetError"
    assert val["code"] == 1

def test_extract_trace_summary():
    mock_events = [
        {
            "in_successful_call": True,
            "contract_id": "CAAAABBBB",
            "topics": ["fn_call", "deposit"],
            "data": {"amount": 100}
        },
        {
            "in_successful_call": False,
            "contract_id": "CAAAABBBB",
            "topics": ["error", "HostError"],
            "data": {"error_type": "StorageError", "code": 2}
        }
    ]
    summary = extract_trace_summary(mock_events)
    assert summary["call_count"] == 1
    assert summary["error_count"] == 1
    assert summary["calls"][0]["function"] == "deposit"
    assert summary["errors"][0]["detail"]["error_type"] == "StorageError"

# --- Inspector Tests ---

def test_inspector_success_tx():
    mock_client = MagicMock()
    mock_client.network_name = "testnet"
    mock_client.rpc_url = "https://soroban-testnet.stellar.org"
    mock_client.get_transaction.return_value = {
        "status": "SUCCESS",
        "ledger": 54321,
        "createdAt": "2026-08-17T12:00:00Z",
        "diagnosticEventsXdr": []
    }

    inspector = TransactionInspector(rpc_client=mock_client)
    report = inspector.inspect("a" * 64)
    assert report["status"] == "SUCCESS"
    assert report["is_success"] is True
    assert report["ledger"] == 54321

def test_inspector_failed_tx_diagnostics():
    mock_client = MagicMock()
    mock_client.network_name = "testnet"
    mock_client.rpc_url = "https://soroban-testnet.stellar.org"
    mock_client.get_transaction.return_value = {
        "status": "FAILED",
        "ledger": 54322,
        "resultXdr": "AAAA...",
        "diagnosticEventsXdr": []
    }

    inspector = TransactionInspector(rpc_client=mock_client)
    report = inspector.inspect("b" * 64)
    assert report["status"] == "FAILED"
    assert report["is_success"] is False
    assert "diagnosis" in report
    assert len(report["matched_catalog_entries"]) > 0

# --- Simulator Tests ---

def test_simulator_success():
    mock_client = MagicMock()
    mock_client.network_name = "testnet"
    mock_client.simulate_transaction.return_value = {
        "latestLedger": 9999,
        "minResourceFee": "1000",
        "cost": {"cpuInsns": 150000, "memBytes": 45000},
        "results": [{"auth": ["sig1"], "xdr": "..."}],
        "events": []
    }

    simulator = TransactionSimulator(rpc_client=mock_client)
    res = simulator.simulate("AAAAfakeXdr")
    assert res["success"] is True
    assert res["cpu_instructions"] == 150000
    assert res["mem_bytes"] == 45000

def test_simulator_failure():
    mock_client = MagicMock()
    mock_client.network_name = "testnet"
    mock_client.simulate_transaction.return_value = {
        "latestLedger": 9999,
        "error": "HostError: BudgetExceeded (CPU limit reached)",
        "cost": {"cpuInsns": 100000000, "memBytes": 40000000},
        "results": [],
        "events": []
    }

    simulator = TransactionSimulator(rpc_client=mock_client)
    res = simulator.simulate("AAAAfakeXdr")
    assert res["success"] is False
    assert "BudgetExceeded" in res["error_message"]
    assert len(res["matched_catalog_entries"]) > 0
    assert res["matched_catalog_entries"][0]["id"] == "budget-exceeded"

# --- Storage Auditor Tests ---

def test_storage_auditor_ttl_expiry():
    mock_client = MagicMock()
    mock_client.network_name = "testnet"
    mock_client.get_latest_ledger.return_value = {"sequence": 10000}
    mock_client.get_ledger_entries.return_value = {
        "entries": [
            {
                "key": "AAAAkey1",
                "xdr": "AAAAval1",
                "lastModifiedLedgerSeq": 9000,
                "liveUntilLedgerSeq": 10000 # Expired
            },
            {
                "key": "AAAAkey2",
                "xdr": "AAAAval2",
                "lastModifiedLedgerSeq": 9500,
                "liveUntilLedgerSeq": 10500 # Warning (< 1000 ledgers)
            },
            {
                "key": "AAAAkey3",
                "xdr": "AAAAval3",
                "lastModifiedLedgerSeq": 9800,
                "liveUntilLedgerSeq": 50000 # Healthy
            }
        ]
    }

    auditor = StorageAuditor(rpc_client=mock_client)
    report = auditor.audit_contract_keys("CAAAABBBB", xdr_keys=["AAAAkey1", "AAAAkey2", "AAAAkey3"])
    
    assert report["success"] is True
    assert report["expired_count"] == 1
    assert report["warning_count"] == 1
    assert report["entries"][0]["health"] == "EXPIRED"
    assert report["entries"][1]["health"] == "CRITICAL"
    assert report["entries"][2]["health"] == "HEALTHY"
    assert len(report["remediation"]) >= 2
