<div align="center">

# ⚡ TrapTrace CLI — Operational Soroban Diagnostic Engine & Explainer

**An operational developer tool, on-chain transaction inspector, simulation pre-flight debugger, batch transaction analyzer, and automated remediation code generator for the Stellar Soroban smart contract ecosystem.**

[![CI Workflow](https://img.shields.io/github/actions/workflow/status/TrapTrace/soroban-error-cli/ci.yml?branch=main&style=flat-square&color=2FA98C&label=CI%20Workflow)](https://github.com/TrapTrace/soroban-error-cli/actions)
[![Python](https://img.shields.io/badge/Python-3.8%2B-1B1F23?style=flat-square)](https://python.org)
[![Version](https://img.shields.io/badge/Version-v0.3.0-2FA98C?style=flat-square)](https://github.com/TrapTrace/soroban-error-cli/releases)
[![License](https://img.shields.io/badge/License-MIT-2FA98C?style=flat-square)](./LICENSE)
[![Stellar Wave](https://img.shields.io/badge/Drips%20Wave-8%20Target-E2984B?style=flat-square)](https://drips.network)

</div>

---

## ⚡ Quick Installation

Install from PyPI / local source in editable mode:

```bash
pip install -e .
```

Both `traptrace` and `soroban-explain` CLI binaries are available globally.

---

## 🛠️ Operational Commands & Developer Workflows

### 1. Live On-Chain Transaction Inspector (`traptrace inspect`)
Connects directly to Stellar RPC (Testnet, Mainnet, Futurenet, or local node) to fetch transactions, decode meta XDR, parse `DiagnosticEvents`, and pinpoint exact host traps with verified fixes.

```bash
# Inspect a failed transaction on Testnet
traptrace inspect 8a3f7c12d9e4a5b6c7d8e9f0123456789abcdef0123456789abcdef012345678 --network testnet

# Inspect on Mainnet with JSON output or export to Markdown report
traptrace inspect <TX_HASH> --network mainnet --export-md report.md
```

### 2. Multi-Transaction Batch Inspector (`traptrace batch-inspect`)
Performs bulk diagnostics across arrays or datasets of transaction hashes, calculating aggregate failure rates, average CPU/memory consumption, category distributions, and top recurring trap root causes.

```bash
# Batch inspect transactions from a JSON file
traptrace batch-inspect -f failed_txs.json --network testnet --export-md batch_report.md
```

### 3. Pre-Flight Transaction Simulation & TUI Gauges (`traptrace simulate`)
Runs `simulateTransaction` against live Soroban RPC without submitting on-chain. Renders real-time ANSI meter gauges for CPU gas instructions, WASM RAM bytes, auth requirements, and fee calculations.

```bash
traptrace simulate "AAAAAgAAAA..." --network testnet
```

### 4. Contract Authorization Tree Validator (`traptrace auth-check`)
Simulates envelope XDR and validates Soroban authorization hierarchies (`AddressCredentials`, `require_auth`, `require_auth_for_args`), surfacing missing signatures or unauthorized sub-invocation trees.

```bash
traptrace auth-check "AAAAAgAAAA..." --network testnet
```

### 5. Automated Remediation Code Snippet Generator (`traptrace fix`)
Generates tailored, idiomatic Rust and Soroban SDK remediation code snippets illustrating *Before (Buggy pattern)* vs *After (Remediated best practice)* for any catalog error.

```bash
# View fix for arithmetic overflow / underflow
traptrace fix arith-error

# Export remediation code directly to a Rust file
traptrace fix require-auth-missing --export-rs fix_auth.rs
```

### 6. Real-Time Contract Trap Watcher (`traptrace watch`)
Streams contract and diagnostic events from the ledger in real time, alerting developers to contract panics, auth failures, and host errors as they occur.

```bash
# Stream events for a specific contract ID
traptrace watch --contract CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA --interval 2.0
```

### 7. Storage & State TTL Expiration Auditor (`traptrace storage`)
Audits contract ledger storage keys and checks live TTL values to detect expired/archived keys before transactions fail on-chain.

```bash
traptrace storage --contract CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA --keys "AAAA..." --network testnet
```

### 8. XDR Diagnostic Event Decoder (`traptrace decode`)
Decodes base64-encoded `DiagnosticEvent` and `SCVal` structures into human-readable contract calls, arguments, and host error types.

```bash
traptrace decode "AAAAAgAAAA..."
```

### 9. Error Catalog Explainer (`traptrace explain`)
Performs tokenized fuzzy lookup across the 21 testnet-verified Soroban error catalog entries with ranked scoring.

```bash
traptrace explain "HostError::BudgetExceeded" --rank --detailed
```

---

## 🌐 Supported Networks & RPC Endpoints

| Network | Flag | Default RPC URL |
|---|---|---|
| **Testnet** | `--network testnet` | `https://soroban-testnet.stellar.org` |
| **Mainnet** | `--network mainnet` | `https://mainnet.stellar.org:443` |
| **Futurenet** | `--network futurenet` | `https://rpc-futurenet.stellar.org` |
| **Local Standalone** | `--network local` | `http://localhost:8000/soroban/rpc` |
| **Custom RPC** | `--rpc-url <URL>` | Any custom JSON-RPC 2.0 endpoint |

---

## 🧪 Running Unit & Integration Tests

```bash
pytest tests/ -v
```

All 31 unit, mock integration, and operational tests pass with zero external dependencies.

---

## 📄 License

MIT License. Copyright (c) 2026 TrapTrace.
