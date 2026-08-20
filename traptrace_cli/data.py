import os
import json
import re

# Bundled fallback dataset of Soroban errors for instant offline lookup
BUNDLED_ENTRIES = [
  {
    "id": "budget-exceeded",
    "title": "Host Error - CPU or Memory Execution Budget Exceeded",
    "category": "host-error",
    "error_code": "HostError::BudgetExceeded",
    "verified": True,
    "summary": "Contract execution terminated because CPU instruction count or memory allocation exceeded specified envelope limits.",
    "tags": ["budget", "cpu", "memory", "limits", "host-error"],
    "symptoms": "Transaction simulation or invocation returns HostError::BudgetExceeded.",
    "solutions": "Chunk operations into smaller batches; use native host crypto primitives; raise budget in test harness."
  },
  {
    "id": "entry-archived-ttl-expired",
    "title": "Host Error - Storage Entry Archived or TTL Expired",
    "category": "host-error",
    "error_code": "HostError::EntryArchived",
    "verified": True,
    "summary": "Attempted access to a persistent or instance storage entry whose Time-To-Live (TTL) has expired.",
    "tags": ["storage", "ttl", "archive", "state-archival", "host-error"],
    "symptoms": "Call fails with error string Storage, ExceededStateArchival.",
    "solutions": "Extend TTL in contract logic using extend_ttl(); issue a RestoreFootprint transaction before invocation."
  },
  {
    "id": "unreachable-code-reached",
    "title": "Host Error - WASM Unreachable Code Reached (Panic)",
    "category": "host-error",
    "error_code": "HostError::WasmUnreachable",
    "verified": True,
    "summary": "WASM virtual machine hit an explicit panic instruction or out-of-bounds index execution.",
    "tags": ["wasm", "panic", "unreachable", "bounds", "host-error"],
    "symptoms": "VM trapped: unreachable code executed.",
    "solutions": "Avoid .unwrap(); return Result<T, Error>; add bounds checking before indexing."
  },
  {
    "id": "sub-invocation-failed",
    "title": "Host Error - Cross-Contract Sub-Invocation Failed",
    "category": "host-error",
    "error_code": "HostError::ContextFailed",
    "verified": True,
    "summary": "Cross-contract call to child contract returned an unhandled error or panic.",
    "tags": ["cross-contract", "invocation", "call", "sub-call", "host-error"],
    "symptoms": "Parent contract invocation aborts with Error(Context, Failed).",
    "solutions": "Verify child contract address and check target function arguments and panic conditions."
  },
  {
    "id": "contract-not-found",
    "title": "Host Error - Contract Code or Instance Not Found",
    "category": "host-error",
    "error_code": "HostError::ContractNotFound",
    "verified": True,
    "summary": "Host environment failed to locate WASM executable bytecode or instance storage for given contract ID.",
    "tags": ["contract-id", "wasm", "missing", "deploy", "host-error"],
    "symptoms": "Contract instance does not exist.",
    "solutions": "Verify contract ID hash and ensure target network matches deployment network."
  },
  {
    "id": "account-not-found",
    "title": "CLI Error - Identity Account Not Found on Network",
    "category": "cli-error",
    "error_code": "CLI::AccountNotFound",
    "verified": True,
    "summary": "Soroban CLI configured source identity account is not funded or does not exist on the target network.",
    "tags": ["account", "keypair", "fund", "friendbot", "cli-error"],
    "symptoms": "Error: Account G... not found on network.",
    "solutions": "Fund account using soroban keys fund <alias> --network testnet."
  },
  {
    "id": "tx-failed-bad-seq",
    "title": "CLI Error - Transaction Failed Bad Sequence Number",
    "category": "cli-error",
    "error_code": "txBAD_SEQ",
    "verified": True,
    "summary": "Transaction submission rejected because account sequence number did not match network sequence counter.",
    "tags": ["sequence", "nonce", "transaction", "txBAD_SEQ", "cli-error"],
    "symptoms": "Transaction submission failed: ResultCode txBAD_SEQ.",
    "solutions": "Retry command to refresh sequence counter; use channel accounts for concurrent submissions."
  },
  {
    "id": "simulate-tx-auth-failed",
    "title": "RPC Error - Simulate Transaction Authorization Verification Failed",
    "category": "rpc-error",
    "error_code": "RPC::SimulateAuthFailed",
    "verified": True,
    "summary": "Simulation node failed to verify invocation authorization payload or signature footprint.",
    "tags": ["rpc", "simulateTransaction", "auth", "signature", "rpc-error"],
    "symptoms": "RPC returns Simulation failed: Auth error.",
    "solutions": "Ensure signer key matches require_auth address; re-simulate auth tree."
  },
  {
    "id": "storage-key-missing",
    "title": "RPC Error - Requested Ledger Storage Key Missing",
    "category": "rpc-error",
    "error_code": "RPC::StorageKeyNotFound",
    "verified": True,
    "summary": "RPC getLedgerEntries endpoint returned empty result for requested XDR storage key.",
    "tags": ["rpc", "storage", "key", "getLedgerEntries", "rpc-error"],
    "symptoms": "getLedgerEntries response returns empty entries list.",
    "solutions": "Initialize storage state on-chain before querying."
  },
  {
    "id": "value-conversion-failed",
    "title": "SDK Error - ScVal to Native Value Conversion Failed",
    "category": "sdk-error",
    "error_code": "SDK::ScValConversionError",
    "verified": True,
    "summary": "Soroban SDK failed to deserialize raw XDR ScVal into target programming language primitive or struct.",
    "tags": ["sdk", "scval", "xdr", "conversion", "sdk-error"],
    "symptoms": "Cannot convert ScVal to native type.",
    "solutions": "Use type-safe generated bindings (soroban contract bindings); verify ScVal variant."
  },
  {
    "id": "host-invalid-action",
    "title": "Host Error - Invalid Action or Host Invariant Violation",
    "category": "host-error",
    "error_code": "HostError::InvalidAction",
    "verified": True,
    "summary": "Contract execution failed because a host function was called with invalid domain arguments or violated host state invariants.",
    "tags": ["host-error", "invalid-action", "host-functions", "validation", "crypto"],
    "symptoms": "Transaction simulation returns HostError(Error(Context, InvalidAction)).",
    "solutions": "Verify cryptographic key/signature lengths; limit event topics to 4 maximum; validate raw Val handles."
  }
]

def load_entries(custom_dir=None):
    """Load entries from custom local index directory if available, otherwise return bundled dataset."""
    if custom_dir and os.path.isdir(custom_dir):
        # Read from local soroban-error-index entries folder
        entries = []
        entries_pattern = os.path.join(custom_dir, "entries")
        if os.path.exists(entries_pattern):
            for root, _, files in os.walk(entries_pattern):
                for file in files:
                    if file.endswith(".md"):
                        filepath = os.path.join(root, file)
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                        meta = parse_md_content(content)
                        if meta.get("id"):
                            entries.append(meta)
            if entries:
                return entries
    return BUNDLED_ENTRIES

def parse_md_content(content):
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        return {}
    yaml_str = match.group(1)
    body = match.group(2)
    meta = {}
    for line in yaml_str.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip()
            if v.lower() == "true": v = True
            elif v.lower() == "false": v = False
            elif v.startswith("[") and v.endswith("]"):
                v = [i.strip().strip("'\"") for i in v[1:-1].split(",") if i.strip()]
            elif (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                v = v[1:-1]
            meta[k] = v
    meta["body"] = body
    return meta
