"""
Pytest suite for extended CLI features:
- DiffEngine
- AbiFetcher
- WebhookNotifier
- Shell Completion
"""

import pytest
from unittest.mock import MagicMock, patch

from traptrace_cli.diff_engine import DiffEngine, render_diff_terminal
from traptrace_cli.abi_fetcher import AbiFetcher, render_abi_terminal
from traptrace_cli.webhook import WebhookNotifier
from traptrace_cli.completion import generate_completion
from traptrace_cli.rpc_client import SorobanRpcClient

def test_diff_engine():
    client = SorobanRpcClient("testnet")
    engine = DiffEngine(rpc_client=client)

    t1 = {
        "status": "SUCCESS",
        "resource_metrics": {"cpu_instructions": 10_000_000, "memory_bytes": 102400}
    }
    t2 = {
        "status": "SUCCESS",
        "resource_metrics": {"cpu_instructions": 15_000_000, "memory_bytes": 204800}
    }

    with patch.object(engine.inspector, "inspect", side_effect=[t1, t2]):
        diff = engine.diff_transactions("a"*64, "b"*64)
        assert diff["deltas"]["cpu_instruction_delta"] == 5_000_000
        assert diff["deltas"]["cpu_pct_change"] == 50.0
        assert diff["status_match"] is True

        term = render_diff_terminal(diff)
        assert "Comparative Transaction Resource Diff" in term

def test_abi_fetcher():
    client = SorobanRpcClient("testnet")
    fetcher = AbiFetcher(rpc_client=client)

    with patch.object(client, "get_ledger_entries", return_value={"entries": []}):
        abi = fetcher.fetch_contract_spec("CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC")
        assert len(abi["functions"]) >= 3
        assert abi["functions"][1]["name"] == "transfer"

        term = render_abi_terminal(abi)
        assert "Contract WASM ABI & Spec Inspector" in term
        assert "transfer" in term

def test_webhook_notifier():
    notifier = WebhookNotifier("https://discord.com/api/webhooks/mock")
    
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.status = 204
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        success = notifier.send_trap_alert("Test Alert", {"contract_id": "CAAA", "error_code": "HostError::BudgetExceeded"}, is_test=True)
        assert success is True

def test_shell_completion():
    bash_comp = generate_completion("bash")
    assert "_traptrace_completion" in bash_comp
    assert "complete -F" in bash_comp

    zsh_comp = generate_completion("zsh")
    assert "#compdef" in zsh_comp
