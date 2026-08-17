"""
Contract Storage and State TTL Expiration Auditor.
Inspects contract ledger entries, checks TTL health, and identifies archived/expired state.
"""

from typing import Dict, Any, Optional, List
from traptrace_cli.rpc_client import SorobanRpcClient, SorobanRpcError

TTL_CRITICAL_THRESHOLD_LEDGERS = 1000   # ~1.4 hours
TTL_WARNING_THRESHOLD_LEDGERS = 10000   # ~14 hours

class StorageAuditor:
    """
    Audits contract state storage and TTL expiration on Stellar / Soroban.
    """

    def __init__(self, rpc_client: Optional[SorobanRpcClient] = None, network: str = "testnet"):
        self.client = rpc_client or SorobanRpcClient(network_or_url=network)

    def audit_contract_keys(self, contract_id: str, xdr_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Audits specific contract ledger keys or contract instance entries for state and TTL health.
        """
        clean_contract = contract_id.strip()
        
        try:
            latest = self.client.get_latest_ledger()
            current_ledger = latest.get("sequence", 0)
        except SorobanRpcError as e:
            return {
                "success": False,
                "error": f"Failed to retrieve latest ledger: {e}",
                "network": self.client.network_name
            }

        keys_to_query = xdr_keys or []
        
        if not keys_to_query:
            return {
                "contract_id": clean_contract,
                "current_ledger": current_ledger,
                "network": self.client.network_name,
                "status": "READY_FOR_QUERY",
                "message": "Specify contract storage XDR keys with --keys to audit specific instance/persistent entries."
            }

        try:
            res = self.client.get_ledger_entries(keys_to_query)
        except SorobanRpcError as e:
            return {
                "success": False,
                "error": f"Failed to query getLedgerEntries: {e}",
                "network": self.client.network_name
            }

        raw_entries = res.get("entries", [])
        audited_entries = []
        expired_count = 0
        warning_count = 0

        for entry in raw_entries:
            key_xdr = entry.get("key")
            xdr_val = entry.get("xdr")
            last_modified = entry.get("lastModifiedLedgerSeq")
            live_until = entry.get("liveUntilLedgerSeq")

            if live_until is not None:
                remaining_ledgers = max(0, live_until - current_ledger)
                if remaining_ledgers == 0:
                    health = "EXPIRED"
                    expired_count += 1
                elif remaining_ledgers < TTL_CRITICAL_THRESHOLD_LEDGERS:
                    health = "CRITICAL"
                    warning_count += 1
                elif remaining_ledgers < TTL_WARNING_THRESHOLD_LEDGERS:
                    health = "WARNING"
                    warning_count += 1
                else:
                    health = "HEALTHY"
            else:
                remaining_ledgers = None
                health = "UNKNOWN"

            audited_entries.append({
                "key": key_xdr,
                "last_modified_ledger": last_modified,
                "live_until_ledger": live_until,
                "remaining_ledgers": remaining_ledgers,
                "approx_remaining_hours": round(remaining_ledgers * 5 / 3600, 2) if remaining_ledgers is not None else None,
                "health": health
            })

        remediation = []
        if expired_count > 0:
            remediation.append(
                f"🚨 {expired_count} entry(s) have EXPIRED/ARCHIVED. Use `soroban contract restore` or `stellar contract restore` to recover them before invoking."
            )
        if warning_count > 0:
            remediation.append(
                f"⚠️ {warning_count} entry(s) are near expiration. Use `stellar contract extend --durability persistent` to bump their TTL."
            )

        return {
            "success": True,
            "contract_id": clean_contract,
            "current_ledger": current_ledger,
            "entries_checked": len(audited_entries),
            "expired_count": expired_count,
            "warning_count": warning_count,
            "entries": audited_entries,
            "remediation": remediation
        }
