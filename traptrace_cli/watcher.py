"""
Real-time Contract Event Stream and Trap Monitor.
Polls getEvents on Stellar RPC to detect contract failures, traps, and logs as they occur on-chain.
"""

import time
from typing import Dict, Any, Optional, List, Callable
from traptrace_cli.rpc_client import SorobanRpcClient, SorobanRpcError
from traptrace_cli.xdr_decoder import decode_scval, XdrReader

class ContractEventWatcher:
    """
    Streams and monitors contract events from Stellar Soroban RPC.
    """

    def __init__(self, rpc_client: Optional[SorobanRpcClient] = None, network: str = "testnet"):
        self.client = rpc_client or SorobanRpcClient(network_or_url=network)

    def fetch_events(
        self,
        contract_id: Optional[str] = None,
        start_ledger: Optional[int] = None,
        end_ledger: Optional[int] = None,
        event_types: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Fetches a slice of contract events from the RPC.
        """
        if start_ledger is None:
            latest = self.client.get_latest_ledger()
            latest_seq = latest.get("sequence", 1000)
            start_ledger = max(1, latest_seq - 100)

        filters = []
        if contract_id:
            filters.append({"type": "contract", "contractIds": [contract_id]})
        if event_types:
            for et in event_types:
                filters.append({"type": et})

        pagination = {"limit": limit}
        res = self.client.get_events(
            start_ledger=start_ledger,
            end_ledger=end_ledger,
            filters=filters if filters else None,
            pagination=pagination
        )

        raw_events = res.get("events", [])
        parsed_events = []

        for ev in raw_events:
            parsed = self._parse_event_item(ev)
            parsed_events.append(parsed)

        return parsed_events

    def _parse_event_item(self, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses a single event object returned by getEvents.
        """
        ledger = event_dict.get("ledger")
        ledger_closed_at = event_dict.get("ledgerClosedAt")
        contract_id = event_dict.get("contractId")
        event_id = event_dict.get("id")
        event_type = event_dict.get("type", "contract")
        in_success = event_dict.get("inSuccessfulContractCall", True)
        
        # Topic parsing
        raw_topics = event_dict.get("topic", [])
        topics = []
        for t in raw_topics:
            if isinstance(t, str):
                topics.append(t)
            else:
                topics.append(str(t))

        is_error = not in_success or any("error" in str(t).lower() or "trap" in str(t).lower() for t in topics)

        return {
            "id": event_id,
            "ledger": ledger,
            "timestamp": ledger_closed_at,
            "contract_id": contract_id,
            "type": event_type,
            "in_successful_call": in_success,
            "is_error": is_error,
            "topics": topics,
            "value": event_dict.get("value", {})
        }

    def watch(
        self,
        contract_id: Optional[str] = None,
        poll_interval_seconds: float = 3.0,
        max_iterations: Optional[int] = None,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        Polls for new contract events continuously in real time.
        """
        latest = self.client.get_latest_ledger()
        current_cursor = latest.get("sequence", 1)
        iteration = 0

        while True:
            if max_iterations is not None and iteration >= max_iterations:
                break
            iteration += 1

            try:
                events = self.fetch_events(contract_id=contract_id, start_ledger=current_cursor)
                for ev in events:
                    if callback:
                        callback(ev)
                    if ev.get("ledger", 0) >= current_cursor:
                        current_cursor = ev["ledger"] + 1
            except SorobanRpcError:
                pass

            time.sleep(poll_interval_seconds)
