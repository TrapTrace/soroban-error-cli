"""
Pytest test suite for TrapTrace CLI linter, profiler, test generator, and health checker.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from traptrace_cli.linter import lint_source_code, lint_file
from traptrace_cli.profiler import GasProfile, profile_simulation_result, render_ascii_flamegraph
from traptrace_cli.test_generator import generate_rust_test
from traptrace_cli.health import check_endpoint_health, check_all_networks

def test_linter_detects_unsafe_unwrap():
    code = """
    pub fn get_val(env: Env) -> u32 {
        let opt = Some(10);
        opt.unwrap()
    }
    """
    findings = lint_source_code(code)
    assert len(findings) >= 1
    f_ids = [f.rule_id for f in findings]
    assert "TT-LINT-001" in f_ids

def test_linter_detects_raw_arithmetic():
    code = """
    pub fn calculate(a: u128, b: u128) -> u128 {
        let result = a + 1;
        result
    }
    """
    findings = lint_source_code(code)
    assert len(findings) >= 1
    f_ids = [f.rule_id for f in findings]
    assert "TT-LINT-002" in f_ids

def test_linter_detects_unguarded_caller():
    code = """
    pub fn mutate_state(env: Env, caller: Address, amount: i128) {
        env.storage().instance().set(&symbol_short!("amt"), &amount);
    }
    """
    findings = lint_source_code(code)
    assert len(findings) >= 1
    f_ids = [f.rule_id for f in findings]
    assert "TT-LINT-004" in f_ids

def test_linter_file_scanner(tmp_path):
    rs_file = tmp_path / "contract.rs"
    rs_file.write_text("""
    pub fn process(caller: Address) {
        let val = items.get(0).unwrap();
    }
    """)
    res = lint_file(str(rs_file))
    assert res["total_findings"] >= 1
    assert res["critical_count"] >= 1

def test_gas_profiler_calculations():
    sim_data = {
        "cost": {"cpuInsns": "50000000", "memBytes": "20971520"},
        "minResourceFee": "1500000",
        "transactionData": {
            "footprint": {
                "readOnly": ["k1", "k2"],
                "readWrite": ["w1"]
            }
        }
    }
    profile = profile_simulation_result(sim_data)
    assert profile.cpu_insns == 50_000_000
    assert profile.cpu_pct == 50.0
    assert profile.mem_pct == 50.0
    assert profile.read_entries == 2
    assert profile.write_entries == 1
    assert profile.min_resource_fee == 1_500_000

    flamegraph = render_ascii_flamegraph(profile)
    assert "SOROBAN RESOURCE PROFILE" in flamegraph
    assert "50.0%" in flamegraph

def test_test_generator_output():
    test_arith = generate_rust_test("arith-error")
    assert "Arithmetic Overflow" in test_arith["title"]
    assert "test_reproduce_arith_overflow_panic" in test_arith["code"]

    test_auth = generate_rust_test("require-auth-missing")
    assert "Authorization" in test_auth["title"]
    assert "mock_all_auths" in test_auth["code"]

    test_fallback = generate_rust_test("custom-contract-error")
    assert "custom_contract_error" in test_fallback["code"]

def test_health_checker_mock():
    mock_ledger_res = {"result": {"sequence": 4257911}}
    mock_net_res = {"result": {"protocolVersion": 21, "passphrase": "Test SDF Network ; September 2015"}}

    with patch("traptrace_cli.rpc_client.SorobanRpcClient.get_latest_ledger", return_value=mock_ledger_res):
        with patch("traptrace_cli.rpc_client.SorobanRpcClient.get_network", return_value=mock_net_res):
            health = check_endpoint_health("https://soroban-testnet.stellar.org", "testnet")
            assert health["status"] == "HEALTHY"
            assert health["latest_ledger"] == 4257911
            assert health["protocol_version"] == 21
