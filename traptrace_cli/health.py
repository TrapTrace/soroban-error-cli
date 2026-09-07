"""
TrapTrace RPC & Network Health Checker.
Diagnostics endpoint latency, ledger synchronization, protocol version, and network availability.
"""

import time
from typing import Dict, Any, List
from .rpc_client import SorobanRpcClient, DEFAULT_NETWORKS

NETWORKS = DEFAULT_NETWORKS

def check_endpoint_health(rpc_url: str, network_name: str = "custom") -> Dict[str, Any]:
    client = SorobanRpcClient(network_or_url=rpc_url, timeout=3)
    start_time = time.time()

    try:
        # SorobanRpcClient._call() unwraps the JSON-RPC envelope and returns
        # the result object directly (and raises SorobanRpcError on failure).
        ledger_res = client.get_latest_ledger()
        latency_ms = round((time.time() - start_time) * 1000, 2)

        net_res = client.get_network()
        seq = ledger_res.get("sequence")
        protocol = net_res.get("protocolVersion")
        passphrase = net_res.get("passphrase")

        return {
            "network": network_name,
            "rpc_url": rpc_url,
            "status": "HEALTHY",
            "latency_ms": latency_ms,
            "latest_ledger": seq,
            "protocol_version": protocol,
            "passphrase": passphrase
        }
    except Exception as e:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "network": network_name,
            "rpc_url": rpc_url,
            "status": "OFFLINE",
            "latency_ms": latency_ms,
            "error": str(e),
            "latest_ledger": None,
            "protocol_version": None
        }

def check_all_networks() -> List[Dict[str, Any]]:
    results = []
    for name, url in NETWORKS.items():
        results.append(check_endpoint_health(url, name))
    return results
