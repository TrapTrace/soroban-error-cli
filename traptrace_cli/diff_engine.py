"""
Transaction Comparative Diff Engine for TrapTrace CLI.
Compares CPU gas instruction costs, WASM RAM consumption, execution status,
and event traces between two on-chain transactions or simulation envelopes.
"""

from typing import Dict, Any, Optional
from traptrace_cli.rpc_client import SorobanRpcClient
from traptrace_cli.inspector import TransactionInspector
from traptrace_cli.tui import (
    BOLD, RESET, DIM, TEAL, CYAN, RED, GREEN, YELLOW, WHITE,
    render_meter_bar, render_box
)

class DiffEngine:
    """Compares two transactions and calculates resource & diagnostic delta."""

    def __init__(self, rpc_client: Optional[SorobanRpcClient] = None):
        self.client = rpc_client or SorobanRpcClient("testnet")
        self.inspector = TransactionInspector(rpc_client=self.client)

    def diff_transactions(self, tx_hash_1: str, tx_hash_2: str) -> Dict[str, Any]:
        """Inspect and compare two transaction hashes."""
        t1 = self.inspector.inspect(tx_hash_1)
        t2 = self.inspector.inspect(tx_hash_2)

        m1 = t1.get("resource_metrics", {})
        m2 = t2.get("resource_metrics", {})

        cpu1 = m1.get("cpu_instructions", 0)
        cpu2 = m2.get("cpu_instructions", 0)
        cpu_diff = cpu2 - cpu1

        mem1 = m1.get("memory_bytes", 0)
        mem2 = m2.get("memory_bytes", 0)
        mem_diff = mem2 - mem1

        return {
            "tx1": {"hash": tx_hash_1, "status": t1.get("status"), "cpu": cpu1, "mem": mem1},
            "tx2": {"hash": tx_hash_2, "status": t2.get("status"), "cpu": cpu2, "mem": mem2},
            "deltas": {
                "cpu_instruction_delta": cpu_diff,
                "cpu_pct_change": round((cpu_diff / cpu1 * 100) if cpu1 else 0.0, 2),
                "memory_byte_delta": mem_diff,
                "memory_pct_change": round((mem_diff / mem1 * 100) if mem1 else 0.0, 2),
            },
            "status_match": t1.get("status") == t2.get("status")
        }

def render_diff_terminal(diff_data: Dict[str, Any]) -> str:
    """Render terminal report comparing two transactions."""
    t1 = diff_data["tx1"]
    t2 = diff_data["tx2"]
    d = diff_data["deltas"]

    cpu_change = d["cpu_instruction_delta"]
    cpu_sign = "+" if cpu_change >= 0 else ""
    cpu_color = RED if cpu_change > 0 else GREEN

    lines = [
        f"\n{TEAL}{BOLD}⚡ TrapTrace Comparative Transaction Resource Diff{RESET}\n",
        f"  • Transaction 1: {CYAN}{t1['hash'][:16]}...{RESET} | Status: {t1['status']} | CPU: {t1['cpu']:,} | RAM: {t1['mem']/1024:.1f} KB",
        f"  • Transaction 2: {CYAN}{t2['hash'][:16]}...{RESET} | Status: {t2['status']} | CPU: {t2['cpu']:,} | RAM: {t2['mem']/1024:.1f} KB\n",
        f"{BOLD}📊 Performance Delta Analysis:{RESET}",
        f"  • CPU Instructions: {cpu_color}{cpu_sign}{cpu_change:,} ({cpu_sign}{d['cpu_pct_change']} any change){RESET}",
        f"  • WASM Memory:     {d['memory_byte_delta']:,} bytes ({d['memory_pct_change']}% change)\n"
    ]
    return "\n".join(lines)
