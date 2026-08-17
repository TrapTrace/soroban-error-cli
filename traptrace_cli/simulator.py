"""
Soroban Pre-Flight Transaction Simulation and Resource Validator.
Runs simulateTransaction against live RPC, decodes footprints, auth trees, and diagnostic traps.
"""

from typing import Dict, Any, Optional, List
from traptrace_cli.rpc_client import SorobanRpcClient, SorobanRpcError
from traptrace_cli.xdr_decoder import parse_diagnostic_events_list, extract_trace_summary
from traptrace_cli.data import load_entries
from traptrace_cli.search_engine import search_errors

class TransactionSimulator:
    """
    Simulates transactions against live Soroban RPC endpoints without on-chain submission.
    """

    def __init__(self, rpc_client: Optional[SorobanRpcClient] = None, network: str = "testnet"):
        self.client = rpc_client or SorobanRpcClient(network_or_url=network)
        self.catalog = load_entries()

    def simulate(self, tx_envelope_xdr: str, resource_leeway: Optional[int] = None) -> Dict[str, Any]:
        """
        Simulates a transaction and produces an in-depth pre-flight validation report.
        """
        clean_xdr = tx_envelope_xdr.strip()
        try:
            sim_data = self.client.simulate_transaction(clean_xdr, resource_leeway=resource_leeway)
        except SorobanRpcError as e:
            return {
                "success": False,
                "status": "RPC_SIMULATION_ERROR",
                "error": str(e),
                "network": self.client.network_name
            }

        cost = sim_data.get("cost", {})
        min_fee = sim_data.get("minResourceFee", "0")
        results = sim_data.get("results", [])
        events_raw = sim_data.get("events", [])
        error_msg = sim_data.get("error")
        latest_ledger = sim_data.get("latestLedger")

        parsed_events = parse_diagnostic_events_list(events_raw)
        trace = extract_trace_summary(parsed_events)

        is_success = error_msg is None and len(results) > 0

        report: Dict[str, Any] = {
            "success": is_success,
            "network": self.client.network_name,
            "latest_ledger": latest_ledger,
            "min_resource_fee": min_fee,
            "cpu_instructions": cost.get("cpuInsns", 0),
            "mem_bytes": cost.get("memBytes", 0),
            "events_count": len(parsed_events),
            "trace_summary": trace,
            "raw_simulation": sim_data
        }

        if is_success:
            report["status"] = "SIMULATION_SUCCESS"
            report["summary"] = "Pre-flight simulation succeeded without traps or errors."
            report["auth_count"] = sum(len(r.get("auth", [])) for r in results)
            return report

        # Simulation failed
        report["status"] = "SIMULATION_FAILED"
        report["error_message"] = error_msg or "Contract simulation reverted or panicked."
        
        # Diagnostic analysis
        remediation_entries = self._analyze_simulation_error(error_msg, trace)
        report["matched_catalog_entries"] = remediation_entries
        
        return report

    def _analyze_simulation_error(self, error_msg: Optional[str], trace: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extracts diagnostic signals from failed simulation and cross-matches catalog entries.
        """
        query_parts = []
        if error_msg:
            query_parts.append(error_msg)
        
        for err in trace.get("errors", []):
            for t in err.get("topics", []):
                query_parts.append(str(t))
            if isinstance(err.get("detail"), dict):
                query_parts.append(str(err["detail"].get("error_type", "")))

        full_query = " ".join(query_parts) if query_parts else "host error trap"
        return search_errors(self.catalog, query=full_query)[:3]
