"""
TrapTrace RPC & Network Health Checker.
Diagnostics endpoint latency, ledger synchronization, protocol version, and network availability.
"""

import time
from typing import Dict, Any, List
from .rpc_client import SorobanRpcClient, DEFAULT_NETWORKS

NETWORKS = DEFAULT_NETWORKS

def check_endpoint_health(rpc_url: str, network_name: str = "custom") -> Dict[str, Any]:
    client = SorobanRpcClient(network_or_url=rpc_url)

    start_time = time.time()
    ledger_res = client.get_latest_ledger()
    latency_ms = round((time.time() - start_time) * 1000, 2)

    if "error" in ledger_res:
        return {
            "network": network_name,
            "rpc_url": rpc_url,
            "status": "OFFLINE",
            "latency_ms": latency_ms,
            "error": ledger_res["error"],
            "latest_ledger": None,
            "protocol_version": None
        }

    net_res = client.get_network()
    seq = ledger_res.get("result", {}).get("sequence")
    protocol = net_res.get("result", {}).get("protocolVersion")
    passphrase = net_res.get("result", {}).get("passphrase")

    return {
        "network": network_name,
        "rpc_url": rpc_url,
        "status": "HEALTHY",
        "latency_ms": latency_ms,
        "latest_ledger": seq,
        "protocol_version": protocol,
        "passphrase": passphrase
    }

def check_all_networks() -> List[Dict[str, Any]]:
    results = []
    for name, url in NETWORKS.items():
        results.append(check_endpoint_health(url, name))
    return results
