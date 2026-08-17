"""
Stellar / Soroban RPC client for live network communication.
Handles JSON-RPC 2.0 communication with Testnet, Mainnet, Futurenet, and local nodes.
"""

import json
import urllib.request
import urllib.error
import ssl
from typing import Dict, Any, Optional, List, Union

DEFAULT_NETWORKS = {
    "testnet": "https://soroban-testnet.stellar.org",
    "mainnet": "https://mainnet.stellar.org:443",
    "futurenet": "https://rpc-futurenet.stellar.org",
    "local": "http://localhost:8000/soroban/rpc",
    "standalone": "http://localhost:8000/soroban/rpc"
}

DEFAULT_PASSPHRASES = {
    "testnet": "Test SDF Network ; September 2015",
    "mainnet": "Public Global Stellar Network ; September 2015",
    "futurenet": "Test SDF Future Network ; October 2022",
    "local": "Standalone Network ; February 2022",
    "standalone": "Standalone Network ; February 2022"
}

class SorobanRpcError(Exception):
    """Exception raised when an RPC endpoint returns an error."""
    def __init__(self, message: str, code: Optional[int] = None, data: Optional[Any] = None):
        super().__init__(message)
        self.code = code
        self.data = data

class SorobanRpcClient:
    """
    Client for interacting with Stellar Soroban JSON-RPC endpoints.
    """

    def __init__(self, network_or_url: str = "testnet", timeout: int = 15):
        if network_or_url.lower() in DEFAULT_NETWORKS:
            self.network_name = network_or_url.lower()
            self.rpc_url = DEFAULT_NETWORKS[self.network_name]
            self.passphrase = DEFAULT_PASSPHRASES.get(self.network_name, "")
        else:
            self.network_name = "custom"
            self.rpc_url = network_or_url
            self.passphrase = ""
        self.timeout = timeout
        self._request_id = 1

    def _call(self, method: str, params: Optional[Union[Dict[str, Any], List[Any]]] = None) -> Any:
        """
        Executes a JSON-RPC 2.0 POST request to the Soroban RPC server.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {}
        }
        self._request_id += 1

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "TrapTrace-CLI/0.2.0 (Stellar Soroban Diagnostics)"
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.rpc_url, data=data_bytes, headers=headers, method="POST")

        context = ssl.create_default_context()

        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=context) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_content = e.read().decode("utf-8") if e.fp else str(e)
            raise SorobanRpcError(f"HTTP Error {e.code} connecting to {self.rpc_url}: {err_content}", code=e.code)
        except urllib.error.URLError as e:
            raise SorobanRpcError(f"Network error connecting to {self.rpc_url}: {e.reason}")
        except Exception as e:
            raise SorobanRpcError(f"Unexpected connection error to {self.rpc_url}: {str(e)}")

        if "error" in resp_data:
            err = resp_data["error"]
            raise SorobanRpcError(
                message=err.get("message", "Unknown RPC error"),
                code=err.get("code"),
                data=err.get("data")
            )

        return resp_data.get("result")

    def get_network(self) -> Dict[str, Any]:
        """Returns general network information (passphrase, protocol version, friendbot url)."""
        return self._call("getNetwork")

    def get_latest_ledger(self) -> Dict[str, Any]:
        """Returns the latest ledger sequence and close timestamp."""
        return self._call("getLatestLedger")

    def get_transaction(self, tx_hash: str) -> Dict[str, Any]:
        """
        Fetches the status and metadata for a transaction by hash.
        Returns SUCCESS, NOT_FOUND, or FAILED with resultXdr, resultMetaXdr, diagnosticEventsXdr.
        """
        clean_hash = tx_hash.strip()
        return self._call("getTransaction", {"hash": clean_hash})

    def simulate_transaction(self, tx_envelope_xdr: str, resource_leeway: Optional[int] = None) -> Dict[str, Any]:
        """
        Simulates a transaction against the current ledger state without submitting it.
        Returns footprint, minResourceFee, results (with auth, return value, etc.), diagnosticEvents, and error info.
        """
        params: Dict[str, Any] = {"transaction": tx_envelope_xdr.strip()}
        if resource_leeway is not None:
            params["resourceConfig"] = {"instructionLeeway": resource_leeway}
        return self._call("simulateTransaction", params)

    def get_events(
        self,
        start_ledger: int,
        end_ledger: Optional[int] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        pagination: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Queries contract and diagnostic events emitted by Soroban contracts within a ledger range.
        """
        params: Dict[str, Any] = {"startLedger": start_ledger}
        if end_ledger is not None:
            params["endLedger"] = end_ledger
        if filters:
            params["filters"] = filters
        if pagination:
            params["pagination"] = pagination
        return self._call("getEvents", params)

    def get_ledger_entries(self, keys: List[str]) -> Dict[str, Any]:
        """
        Reads ledger entries (contracts, storage keys, wasm bytecode, TTL records) directly by XDR key.
        """
        return self._call("getLedgerEntries", {"keys": keys})

    def send_transaction(self, tx_envelope_xdr: str) -> Dict[str, Any]:
        """Submits a signed transaction envelope XDR to the network."""
        return self._call("sendTransaction", {"transaction": tx_envelope_xdr.strip()})
