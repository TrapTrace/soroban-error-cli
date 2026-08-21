"""
Contract Authorization Tree Validator for TrapTrace CLI.
Inspects and visualizes Soroban authorization hierarchies, validates signature credentials,
and flags missing authorizations or misconfigured sub-invocation trees.
"""

import json
import base64
from typing import Dict, Any, List, Optional

from traptrace_cli.rpc_client import SorobanRpcClient
from traptrace_cli.simulator import TransactionSimulator
from traptrace_cli.tui import (
    BOLD, RESET, DIM, TEAL, CYAN, RED, GREEN, YELLOW, WHITE,
    render_box
)

class AuthChecker:
    """Validator for Soroban authorization credentials and invocation trees."""

    def __init__(self, rpc_client: Optional[SorobanRpcClient] = None):
        self.client = rpc_client or SorobanRpcClient("testnet")
        self.simulator = TransactionSimulator(rpc_client=self.client)

    def check_xdr(self, xdr_str: str) -> Dict[str, Any]:
        """Simulate envelope XDR and analyze returned authorization footprint and errors."""
        sim_report = self.simulator.simulate(xdr_str)
        
        auth_entries = sim_report.get("simulated_result", {}).get("result", {}).get("auth", [])
        events = sim_report.get("diagnostic_events", [])
        has_error = not sim_report.get("is_valid", False)
        
        # Analyze auth issues
        auth_issues = []
        auth_trees = []
        
        # Check diagnostic events for auth keywords
        for ev in events:
            topics_str = " ".join([str(t) for t in ev.get("topics", [])])
            data_str = str(ev.get("data", ""))
            combined = f"{topics_str} {data_str}".lower()
            
            if "auth" in combined or "signature" in combined or "unauthorized" in combined:
                auth_issues.append({
                    "type": "AuthDiagnosticTrap",
                    "contract_id": ev.get("contract_id"),
                    "details": data_str or topics_str
                })

        # Process authorization entries
        for idx, entry in enumerate(auth_entries):
            parsed_tree = self._parse_auth_entry(entry, idx)
            auth_trees.append(parsed_tree)

        status = "FAIL" if (has_error and auth_issues) else ("PASS" if not has_error else "WARN")

        return {
            "is_valid": len(auth_issues) == 0 and not has_error,
            "status": status,
            "auth_entries_count": len(auth_entries),
            "auth_trees": auth_trees,
            "detected_issues": auth_issues,
            "simulation_error": sim_report.get("simulated_result", {}).get("error"),
            "network": self.client.network_name
        }

    def _parse_auth_entry(self, entry: Any, index: int) -> Dict[str, Any]:
        """Parse authorization entry dictionary or raw structure."""
        if isinstance(entry, dict):
            credentials = entry.get("credentials", {})
            root_invocation = entry.get("root_invocation", {})
            return {
                "index": index,
                "credentials_type": credentials.get("type", "AddressCredentials"),
                "address": credentials.get("address", "G..."),
                "nonce": credentials.get("nonce", 0),
                "signature_expiration_ledger": credentials.get("signature_expiration_ledger"),
                "function": root_invocation.get("function", "invoke"),
                "contract_id": root_invocation.get("contract_id", ""),
                "sub_invocations": root_invocation.get("sub_invocations", [])
            }
        return {
            "index": index,
            "raw": str(entry)
        }

def render_auth_report_terminal(report: Dict[str, Any]) -> str:
    """Render terminal colored authorization tree and issue diagnosis."""
    is_valid = report.get("is_valid", False)
    status_tag = f"{GREEN}{BOLD}[VALID AUTH]{RESET}" if is_valid else f"{RED}{BOLD}[AUTH ERROR / TRAP]{RESET}"
    
    lines = [
        f"\n{TEAL}{BOLD}⚡ TrapTrace Contract Authorization Tree Validator{RESET}\n",
        f"  • Status:               {status_tag}",
        f"  • Network:              {CYAN}{report.get('network')}{RESET}",
        f"  • Auth Entries Count:   {report.get('auth_entries_count', 0)}\n"
    ]
    
    issues = report.get("detected_issues", [])
    if issues:
        lines.append(f"{RED}{BOLD}⚠️ Detected Authorization Errors & Traps:{RESET}")
        for idx, iss in enumerate(issues, 1):
            lines.append(f"  {idx}. {YELLOW}{iss.get('type')}{RESET}: {iss.get('details')}")
            if iss.get("contract_id"):
                lines.append(f"     Contract: {CYAN}{iss.get('contract_id')}{RESET}")
        lines.append(f"\n  👉 Remediation: run {CYAN}traptrace fix require-auth-missing{RESET} or {CYAN}traptrace fix auth-invalid-signature{RESET}\n")

    trees = report.get("auth_trees", [])
    if trees:
        lines.append(f"{BOLD}🌳 Invocation Authorization Hierarchy:{RESET}")
        for t in trees:
            lines.append(f"  ├─ 👤 Signer Address: {CYAN}{t.get('address', 'N/A')}{RESET} (Type: {t.get('credentials_type')})")
            lines.append(f"  │  ├── Nonce: {t.get('nonce', 0)}")
            lines.append(f"  │  └── 🎯 Root Invocation: {YELLOW}{t.get('function')}{RESET} on {CYAN}{t.get('contract_id', '<contract>')}{RESET}")
            
            subs = t.get("sub_invocations", [])
            if subs:
                for sub in subs:
                    lines.append(f"  │      └── 🔄 Sub-Invocation: {sub.get('function', 'call')} on {sub.get('contract_id', '')}")
            else:
                lines.append(f"  │      └── (No sub-contract delegations)")
        lines.append("")
    elif not issues:
        lines.append(f"  {DIM}(No explicit custom authorization footprint required for this operation){RESET}\n")

    return "\n".join(lines)
