"""
Stellar / Soroban Transaction Inspector.
Fetches on-chain transactions, decodes execution metadata, pinpoints failures,
and maps root causes to verified TrapTrace catalog remediation guides.
"""

from typing import Dict, Any, Optional, List
from traptrace_cli.rpc_client import SorobanRpcClient, SorobanRpcError
from traptrace_cli.xdr_decoder import parse_diagnostic_events_list, extract_trace_summary
from traptrace_cli.data import load_entries
from traptrace_cli.search_engine import search_errors

class TransactionInspector:
    """
    Analyzes live on-chain Soroban transactions by hash.
    """

    def __init__(self, rpc_client: Optional[SorobanRpcClient] = None, network: str = "testnet"):
        self.client = rpc_client or SorobanRpcClient(network_or_url=network)
        self.catalog = load_entries()

    def inspect(self, tx_hash: str) -> Dict[str, Any]:
        """
        Inspects a transaction by hash and returns a structured diagnostic report.
        """
        try:
            tx_data = self.client.get_transaction(tx_hash)
        except SorobanRpcError as e:
            return {
                "status": "RPC_ERROR",
                "tx_hash": tx_hash,
                "error": str(e),
                "network": self.client.network_name
            }

        status = tx_data.get("status", "UNKNOWN")
        
        report: Dict[str, Any] = {
            "tx_hash": tx_hash,
            "status": status,
            "network": self.client.network_name,
            "rpc_url": self.client.rpc_url,
            "ledger": tx_data.get("ledger"),
            "created_at": tx_data.get("createdAt"),
            "application_order": tx_data.get("applicationOrder"),
            "raw_data": tx_data
        }

        # Parse diagnostic events if present
        diagnostic_events_raw = tx_data.get("diagnosticEventsXdr", [])
        events = parse_diagnostic_events_list(diagnostic_events_raw)
        trace = extract_trace_summary(events)
        
        report["diagnostic_events_count"] = len(events)
        report["trace_summary"] = trace

        if status == "SUCCESS":
            report["summary"] = "Transaction executed successfully on ledger."
            report["is_success"] = True
            return report

        elif status == "NOT_FOUND":
            report["summary"] = "Transaction not found on this network / RPC node."
            report["is_success"] = False
            report["remediation"] = [
                "Verify that the transaction hash is correct.",
                f"Ensure you are querying the right network (currently '{self.client.network_name}').",
                "The transaction may still be in the mempool or pending ingestion."
            ]
            return report

        # FAILED transaction analysis
        report["is_success"] = False
        diagnosis = self._diagnose_failure(tx_data, trace)
        report["diagnosis"] = diagnosis

        # Match with catalog
        matching_entries = self._match_catalog(diagnosis)
        report["matched_catalog_entries"] = matching_entries

        return report

    def _diagnose_failure(self, tx_data: Dict[str, Any], trace: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts error reason, failing contract, and error code from raw RPC data and trace.
        """
        error_msg = tx_data.get("resultXdr", "")
        extracted_errors = trace.get("errors", [])
        
        error_type = "TransactionFailed"
        details = []

        for err in extracted_errors:
            err_topics = err.get("topics", [])
            err_detail = err.get("detail")
            
            if isinstance(err_detail, dict) and "error_type" in err_detail:
                error_type = f"{err_detail['error_type']} (Code #{err_detail.get('code')})"
                details.append(str(err_detail))
            elif err_topics:
                details.append(" : ".join(err_topics))

        return {
            "error_type": error_type,
            "error_details": details or ["Execution halted with host error."],
            "failing_calls": [c for c in trace.get("calls", []) if not c.get("success", True)],
            "auth_issues": trace.get("auth_events", []),
            "cpu_instructions": trace.get("metrics", {}).get("cpu_insns"),
            "mem_bytes": trace.get("metrics", {}).get("mem_bytes")
        }

    def _match_catalog(self, diagnosis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Matches diagnosed error symptoms with verified catalog entries.
        """
        query_terms = [diagnosis.get("error_type", "")]
        for d in diagnosis.get("error_details", []):
            query_terms.append(d)
            
        full_query = " ".join(query_terms)
        matches = search_errors(self.catalog, query=full_query)
        return matches[:3]
