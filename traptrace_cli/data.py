import os
import json
import re

# Bundled fallback dataset of Soroban errors for instant offline lookup
BUNDLED_ENTRIES = [
  {
    "id": "account-not-found",
    "title": "CLI Error - Identity Account Not Found on Network",
    "category": "cli-error",
    "error_code": "CLI::AccountNotFound",
    "verified": True,
    "summary": "Soroban CLI configured source identity account is not funded or does not exist on the target network.",
    "tags": [
      "account",
      "keypair",
      "fund",
      "friendbot",
      "cli-error"
    ],
    "symptoms": "- CLI displays `Error: Account G... not found on network`.\n- Invocation or deployment fails during transaction signing.",
    "solutions": "1. **Fund Account via Friendbot (Testnet):**\n```bash\nsoroban keys fund alice --network testnet\n```\n2. **Transfer Native Balance (Mainnet):** Send XLM to public key before deployment."
  },
  {
    "id": "invalid-chain-id",
    "title": "CLI Error - Network Passphrase or Chain ID Mismatch",
    "category": "cli-error",
    "error_code": "CLI::InvalidChainId",
    "verified": True,
    "summary": "Transaction simulation or submission rejected because the transaction network passphrase hash does not match the target Stellar node network ID.",
    "tags": [
      "network",
      "chain-id",
      "passphrase",
      "testnet",
      "mainnet",
      "futurenet",
      "cli-error"
    ],
    "symptoms": "- Transaction simulation or broadcast fails with error `Invalid network passphrase` or `Transaction signature verification failed for target network`.\n- Stellar RPC returns simulation error: `HostErro",
    "solutions": "1. **Explicitly Specify Network in CLI:** Use the pre-configured `--network testnet` or `--network mainnet` flag rather than hardcoding raw passphrase strings.\n2. **Verify Environment Configurations:*"
  },
  {
    "id": "tx-failed-bad-seq",
    "title": "CLI Error - Transaction Failed Bad Sequence Number",
    "category": "cli-error",
    "error_code": "txBAD_SEQ",
    "verified": True,
    "summary": "Transaction submission rejected because account sequence number did not match network sequence counter.",
    "tags": [
      "sequence",
      "nonce",
      "transaction",
      "txBAD_SEQ",
      "cli-error"
    ],
    "symptoms": "- Transaction rejected with status `txBAD_SEQ`.\n- CLI output: `Transaction submission failed: ResultCode txBAD_SEQ`.",
    "solutions": "1. **Retry Transaction:** Re-run command to refresh sequence number automatically from RPC.\n2. **Use Channels:** For high-throughput automated scripts, use separate channel accounts for transaction si"
  },
  {
    "id": "wasm-verification-failed",
    "title": "CLI Error - Contract WASM Module Bytecode Verification Failed",
    "category": "cli-error",
    "error_code": "CLI::WasmVerificationFailed",
    "verified": True,
    "summary": "Contract upload or installation failed because the compiled WASM binary violates Soroban VM constraints, contains unsupported floating-point operations, or imports unexported host interfaces.",
    "tags": [
      "wasm",
      "bytecode",
      "verification",
      "deployment",
      "install",
      "upload",
      "cli-error"
    ],
    "symptoms": "- Contract installation via `stellar contract install` or `soroban contract deploy` fails during the simulation or upload phase.\n- CLI output displays: `error: contract wasm verification failed: inval",
    "solutions": "1. **Build with the Official Toolchain:** Always compile contracts with `stellar contract build` (or `cargo build --target wasm32-unknown-unknown --release` followed by `stellar contract optimize`).\n2"
  },
  {
    "id": "arith-error",
    "title": "Host Error - Integer Arithmetic Overflow, Underflow, or Division by Zero",
    "category": "host-error",
    "error_code": "HostError::ArithDomain",
    "verified": True,
    "summary": "Contract execution panicked due to an arithmetic domain error such as integer overflow, underflow, or division by zero in WASM.",
    "tags": [
      "arithmetic",
      "overflow",
      "underflow",
      "divide-by-zero",
      "math",
      "host-error"
    ],
    "symptoms": "- Contract simulation or execution aborts immediately with `HostError(Error(Context, InvalidAction))` or `HostError::ArithDomain`.\n- Diagnostic events indicate an unreachable panic (`attempt to add wi",
    "solutions": "1. **Use Checked Arithmetic:** Replace raw operators with checked arithmetic methods (`checked_add`, `checked_sub`, `checked_mul`, `checked_div`) and handle `None` gracefully.\n2. **Use Saturating Arit"
  },
  {
    "id": "auth-invalid-signature",
    "title": "Host Error - Contract Authorization Invalid Signature",
    "category": "host-error",
    "error_code": "HostError::AuthInvalidSignature",
    "verified": True,
    "summary": "Transaction execution or simulation aborted because an authorization entry signature failed cryptographic verification against the required signer address or public key.",
    "tags": [
      "auth",
      "signature",
      "ed25519",
      "secp256k1",
      "verification",
      "require-auth",
      "host-error"
    ],
    "symptoms": "- Transaction simulation or on-chain submission fails with `HostError(Error(Auth, InvalidAction))` or `HostError::AuthInvalidSignature`.\n- RPC response returns `Simulation failed: Auth error: Signatur",
    "solutions": "1. **Verify Signer Matches Address:** Ensure the transaction signer or simulated auth entry keypair matches the `Address` parameter passed to `require_auth()`.\n2. **Simulate Auth Footprints First:** R"
  },
  {
    "id": "budget-exceeded",
    "title": "Host Error - CPU or Memory Execution Budget Exceeded",
    "category": "host-error",
    "error_code": "HostError::BudgetExceeded",
    "verified": True,
    "summary": "Contract execution terminated because CPU instruction count or memory allocation exceeded specified envelope limits.",
    "tags": [
      "budget",
      "cpu",
      "memory",
      "limits",
      "host-error"
    ],
    "symptoms": "- Transaction simulation or invocation returns `HostError::BudgetExceeded`.\n- CLI output displays `Error: HostError(Error(Budget, Exceeded))`.\n- Contract fails during high-iteration loops, complex cry",
    "solutions": "1. **Chunking & Pagination:** Break processing into smaller batches across multiple transactions rather than processing in a single call.\n2. **Optimize Host Functions:** Use Soroban host-provided prim"
  },
  {
    "id": "contract-data-size-exceeds-limit",
    "title": "Host Error - Contract Data Size Exceeds Ledger Entry Limit",
    "category": "host-error",
    "error_code": "HostError::StorageValueExceedsLimit",
    "verified": True,
    "summary": "Contract execution terminated because an attempted storage write or data structure serialization exceeded the maximum protocol ledger entry byte limit (64KB).",
    "tags": [
      "storage",
      "size-limit",
      "64kb",
      "contract-data",
      "payload",
      "host-error"
    ],
    "symptoms": "- Transaction simulation or invocation returns `HostError(Error(Storage, ExceededLimit))` or `HostError::StorageValueExceedsLimit`.\n- Invocation fails when writing large collections (`Vec`, `Map`, or ",
    "solutions": "1. **Partition State Across Keys:** Store individual items under distinct indexed keys (e.g. `DataKey::Item(u32)`) rather than a single monolithic `Vec`.\n2. **Chunking Mechanism:** Split large payload"
  },
  {
    "id": "contract-not-found",
    "title": "Host Error - Contract Code or Instance Not Found",
    "category": "host-error",
    "error_code": "HostError::ContractNotFound",
    "verified": True,
    "summary": "Host environment failed to locate WASM executable bytecode or instance storage for given contract ID.",
    "tags": [
      "contract-id",
      "wasm",
      "missing",
      "deploy",
      "host-error"
    ],
    "symptoms": "- Call fails with `Error(Storage, MissingValue)` or `ContractNotFound`.\n- Soroban CLI outputs `Error: Contract instance C... does not exist`.",
    "solutions": "1. **Verify Target Contract ID:** Re-check deployment output logs for exact address.\n2. **Confirm Network Target:** Ensure `--network testnet` / `--network mainnet` matches deployment target."
  },
  {
    "id": "crypto-verification-failed",
    "title": "Host Error - Cryptographic Signature or Curve Verification Failed",
    "category": "host-error",
    "error_code": "HostError::CryptoError",
    "verified": True,
    "summary": "Smart contract execution panicked during host cryptographic primitives verification (such as env.crypto().ed25519_verify) due to an invalid signature, corrupted public key, or payload mismatch.",
    "tags": [
      "crypto",
      "ed25519",
      "secp256k1",
      "signature",
      "verification",
      "curve",
      "host-error"
    ],
    "symptoms": "- Contract execution or simulation aborts with `HostError(Error(Crypto, InvalidInput))` or `HostError::CryptoError`.\n- Host diagnostic event logs report: `crypto function verification failure` or `ed2",
    "solutions": "1. **Verify Exact Message Hashing:** Ensure message payloads are canonicalized before hashing (e.g. SHA-256 / Keccak-256) and match the exact signing domain parameters.\n2. **Validate Fixed-Size Byte A"
  },
  {
    "id": "entry-archived-ttl-expired",
    "title": "Host Error - Storage Entry Archived or TTL Expired",
    "category": "host-error",
    "error_code": "HostError::EntryArchived",
    "verified": True,
    "summary": "Attempted access to a persistent or instance storage entry whose Time-To-Live (TTL) has expired and been archived.",
    "tags": [
      "storage",
      "ttl",
      "archive",
      "state-archival",
      "host-error"
    ],
    "symptoms": "- Call fails with error string `Error(Storage, ExceededStateArchival)`.\n- Transaction simulation rejects access to persistent key with message `ContractData entry archived`.\n- Previously functioning c",
    "solutions": "1. **Bump TTL in Contract Logic:** Use `env.storage().persistent().extend_ttl(&key, threshold, extend_to)` to proactively renew storage lifespan.\n2. **Issue Restore Transaction:** Submit a `RestoreFoo"
  },
  {
    "id": "host-invalid-action",
    "title": "Host Error - Invalid Action or Host Invariant Violation",
    "category": "host-error",
    "error_code": "HostError::InvalidAction",
    "verified": True,
    "summary": "Contract execution failed because a host function was called with invalid domain arguments or violated host state invariants.",
    "tags": [
      "host-error",
      "invalid-action",
      "host-functions",
      "validation",
      "crypto"
    ],
    "symptoms": "- Transaction simulation returns `HostError(Error(Context, InvalidAction))` or `HostError::InvalidAction`.\n- Diagnostic events log indicates failure inside host functions such as `crypto`, `events`, o",
    "solutions": "1. **Verify Cryptographic Key and Signature Lengths:** Ensure public keys are exact 32-byte slices (`BytesN<32>`) and signatures are exact 64-byte slices (`BytesN<64>`) before calling verification hos"
  },
  {
    "id": "instance-storage-expired",
    "title": "Host Error - Contract Instance and Executable Storage Archived",
    "category": "host-error",
    "error_code": "HostError::InstanceStorageExpired",
    "verified": True,
    "summary": "Contract invocation failed because the contract instance or executable WASM bytecode exceeded its maximum live TTL and was archived by the network.",
    "tags": [
      "storage",
      "instance-storage",
      "archival",
      "ttl",
      "cap-0046",
      "restore-footprint"
    ],
    "symptoms": "- Contract invocations revert during simulation with `HostError(Error(Storage, InstanceArchived))` or `Error(Storage, DeadEntry)`.\n- Transaction footprint indicates `ContractData` or `ContractCode` le",
    "solutions": "1. **Restore Footprint via CLI/SDK:** Submit a restoration transaction (`soroban contract restore --id <CONTRACT_ID> --network testnet`) to revive the contract instance.\n2. **Implement Proactive TTL B"
  },
  {
    "id": "invalid-scval-tag",
    "title": "Host Error - Invalid ScVal Tag Discriminator (Malformed Val Handle)",
    "category": "host-error",
    "error_code": "HostError::InvalidScValTag",
    "verified": True,
    "summary": "Host environment rejected a value representation because the 64-bit tagged Val or ScVal discriminator byte is corrupted, unrecognized, or invalid.",
    "tags": [
      "host-error",
      "scval",
      "val",
      "tagged-pointer",
      "val-tag",
      "malformed"
    ],
    "symptoms": "- Host aborts execution with `HostError(Error(Value, InvalidTag))` or `HostError(Error(Context, InvalidAction))`.\n- Diagnostic events indicate an invalid tag bitmask encountered during host object der",
    "solutions": "1. **Use Safe Soroban SDK Types:** Avoid `Val::from_payload` or raw unsafe pointers; rely on high-level SDK primitives (`Symbol`, `Address`, `Bytes`, `Map`, `Vec`).\n2. **Verify XDR Payloads:** Validat"
  },
  {
    "id": "map-key-not-found",
    "title": "Host Error - Soroban SDK Map Key Lookup Miss Panic",
    "category": "host-error",
    "error_code": "HostError::MapKeyNotFound",
    "verified": True,
    "summary": "Contract execution panicked because a key lookup on a Soroban SDK Map failed to find the key and was followed by an explicit unwrap.",
    "tags": [
      "host-error",
      "map",
      "collection",
      "key-not-found",
      "panic",
      "unwrap"
    ],
    "symptoms": "- Contract simulation reverts with `HostError(Error(Context, InvalidAction))` or `HostError(Error(Object, MissingKey))`.\n- Diagnostic events contain: `called Option::unwrap() on a None value` during M",
    "solutions": "1. **Use `get()` with `unwrap_or` or Default:**\n   ```rust\n   let balance = accounts.get(user).unwrap_or(0);\n   ```\n2. **Return `Result<T, CustomError>`:**\n   ```rust\n   let balance = accounts.get(use"
  },
  {
    "id": "option-unwrap-none",
    "title": "Host Error - Rust Option::unwrap() Called on None in Contract Code",
    "category": "host-error",
    "error_code": "HostError::OptionUnwrapNone",
    "verified": True,
    "summary": "Contract execution panicked because Option::unwrap() or Result::unwrap() was invoked on a None or Err value inside the smart contract WASM bytecode.",
    "tags": [
      "host-error",
      "unwrap",
      "panic",
      "option",
      "rust",
      "safe-rust"
    ],
    "symptoms": "- Contract simulation halts immediately with `HostError(Error(Context, InvalidAction))` or `HostError(Error(WasmVm, UnreachableCodeReached))`.\n- Diagnostic events contain: `panicked at 'called Option:",
    "solutions": "1. **Use `?` Operator with Custom Error Enums:**\n   ```rust\n   #[contracterror]\n   #[derive(Copy, Clone, Debug, Eq, PartialEq, PartialOrd, Ord)]\n   #[repr(u32)]\n   pub enum Error {\n       NotInitializ"
  },
  {
    "id": "require-auth-missing",
    "title": "Host Error - Missing Required Invocation Authorization",
    "category": "host-error",
    "error_code": "HostError::AuthMissing",
    "verified": True,
    "summary": "Contract execution halted because an operation required explicit authorization from an Address that was not provided in the invocation auth tree.",
    "tags": [
      "auth",
      "require-auth",
      "authorization",
      "security",
      "permissions",
      "host-error"
    ],
    "symptoms": "- Transaction simulation or invocation terminates with `HostError(Error(Auth, InvalidAction))` or `HostError::AuthMissing`.\n- RPC simulation returns `Auth error: HostError::AuthMissing (require_auth f",
    "solutions": "1. **Include Auth Entries:** In client applications using JS/Python/Rust SDKs, simulate the transaction first to generate the required `auth` tree and sign each required entry.\n2. **Authorizing Contra"
  },
  {
    "id": "storage-key-size-exceeds-limit",
    "title": "Host Error - Ledger Storage Key Size Exceeds Network Cap",
    "category": "host-error",
    "error_code": "HostError::StorageKeySizeLimit",
    "verified": True,
    "summary": "Contract attempted to persist a storage entry whose key exceeds Soroban's maximum ledger key size limit (typically 64KB or protocol cap).",
    "tags": [
      "storage",
      "limits",
      "key-size",
      "protocol-limits",
      "scval"
    ],
    "symptoms": "- Contract simulation fails during storage write with `HostError(Error(Storage, KeySizeLimitExceeded))` or `HostError(Error(Context, InvalidAction))`.\n- Writing dynamic keys containing large byte buff",
    "solutions": "1. **Hash Dynamic Keys with SHA-256 / Keccak:** Hash variable-length keys using `env.crypto().sha256(&large_key_data)` to produce a deterministic 32-byte `BytesN<32>` key.\n2. **Use Enums / Symbols for"
  },
  {
    "id": "storage-ledger-entry-not-found",
    "title": "Host Error - Storage Ledger Entry Not Found or Missing Value",
    "category": "host-error",
    "error_code": "HostError::StorageNotFound",
    "verified": True,
    "summary": "Contract attempted to read a non-existent or uninitialized key from instance, persistent, or temporary storage without fallback handling.",
    "tags": [
      "storage",
      "ledger-entry",
      "missing-value",
      "persistent",
      "temporary",
      "instance",
      "host-error"
    ],
    "symptoms": "- Contract invocation halts with `HostError(Error(Storage, MissingValue))` or `HostError::StorageNotFound`.\n- Diagnostic events indicate an unwrap on `None` following an `env.storage().instance().get(",
    "solutions": "1. **Use `get_or` Pattern:** Always use `.get(&key).unwrap_or(default_value)` or `env.storage().instance().has(&key)` before accessing storage values.\n2. **Safe Option Handling:** Return `Option<T>` f"
  },
  {
    "id": "sub-invocation-failed",
    "title": "Host Error - Cross-Contract Sub-Invocation Failed",
    "category": "host-error",
    "error_code": "HostError::ContextFailed",
    "verified": True,
    "summary": "Cross-contract call to child contract returned an unhandled error or panic.",
    "tags": [
      "cross-contract",
      "invocation",
      "call",
      "sub-call",
      "host-error"
    ],
    "symptoms": "- Parent contract invocation aborts with `Error(Context, Failed)`.\n- RPC log indicates sub-invocation call stack unwound.",
    "solutions": "1. **Verify Target Address:** Check target contract existence on-chain.\n2. **Propagate or Handle Error:** Wrap sub-invocations carefully and inspect child contract logs."
  },
  {
    "id": "sub-invocation-user-error",
    "title": "Host Error - User-Defined Contract Error in Cross-Contract Sub-Invocation",
    "category": "host-error",
    "error_code": "HostError::ContractUserError",
    "verified": True,
    "summary": "Cross-contract execution reverted because the callee contract returned an explicit user-defined contract error enum discriminant.",
    "tags": [
      "cross-contract",
      "sub-invocation",
      "custom-error",
      "contracterror",
      "bubbling",
      "host-error"
    ],
    "symptoms": "- Transaction simulation or invocation terminates with `HostError(Error(Contract, 1))` (or other integer error code).\n- Top-level contract aborts even though its own logic has not panicked.\n- Diagnost",
    "solutions": "1. **Catch and Handle Errors in Caller:** Avoid unconditional `.unwrap()`; use pattern matching or `match callee_client.try_withdraw(&amount)` to handle child error variants gracefully.\n2. **Inspect E"
  },
  {
    "id": "temporary-storage-expired",
    "title": "Host Error - Temporary Ledger Storage Entry Expired (TTL Evicted)",
    "category": "host-error",
    "error_code": "HostError::TemporaryStorageExpired",
    "verified": True,
    "summary": "Contract attempted to read or write a temporary storage key whose time-to-live (TTL) passed without being bumped, resulting in permanent eviction.",
    "tags": [
      "storage",
      "ttl",
      "temporary-storage",
      "eviction",
      "cap-0046",
      "rent"
    ],
    "symptoms": "- Contract simulation fails with `HostError(Error(Storage, DeadEntry))` or `Error(Storage, MissingValue)`.\n- Temporary state keys (nonces, short-lived signatures, session authorizations) cannot be rea",
    "solutions": "1. **Extend Temporary TTL on Read/Write:** Call `env.storage().temporary().extend_ttl(&TEMP_KEY, threshold, extend_to)` whenever accessing active sessions.\n2. **Use Persistent Storage for State:** Use"
  },
  {
    "id": "unreachable-code-reached",
    "title": "Host Error - WASM Unreachable Code Reached (Panic)",
    "category": "host-error",
    "error_code": "HostError::WasmUnreachable",
    "verified": True,
    "summary": "WASM virtual machine hit an explicit panic instruction or out-of-bounds index execution.",
    "tags": [
      "wasm",
      "panic",
      "unreachable",
      "bounds",
      "host-error"
    ],
    "symptoms": "- Call fails with `HostError(Error(WasmVm, Unexpected))`.\n- Terminal log reports `VM trapped: unreachable code executed`.\n- Contract panics abruptly during call.",
    "solutions": "1. **Use Checked Operations & Match:** Avoid `.unwrap()`. Return `Result<T, ContractError>` instead.\n2. **Safe Math & Boundary Checks:** Validate inputs before indexing or performing division.\n\n```rus"
  },
  {
    "id": "vec-index-out-of-bounds",
    "title": "Host Error - Soroban SDK Vec Index Out of Bounds Panic",
    "category": "host-error",
    "error_code": "HostError::VecIndexOutOfBounds",
    "verified": True,
    "summary": "Contract execution panicked because an indexing operation on a Soroban SDK Vec accessed an index greater than or equal to the vector length.",
    "tags": [
      "host-error",
      "vec",
      "collection",
      "index-out-of-bounds",
      "panic",
      "bounds-check"
    ],
    "symptoms": "- Contract simulation reverts abruptly with `HostError(Error(Context, InvalidAction))` or `HostError(Error(Object, IndexOutOfBounds))`.\n- Diagnostic events contain a panic message: `index out of bound",
    "solutions": "1. **Use `get()` and Match/Handle `None`:** Instead of unwrapping, handle `None` gracefully:\n   ```rust\n   match items.get(index) {\n       Some(val) => Ok(val),\n       None => Err(Error::ItemNotFound)"
  },
  {
    "id": "wasm-memory-exhausted",
    "title": "Host Error - WASM VM Memory Page Allocation Exhausted",
    "category": "host-error",
    "error_code": "HostError::MemoryExhausted",
    "verified": True,
    "summary": "Contract execution halted because total WASM linear memory pages allocated at runtime exceeded the Soroban VM memory cap.",
    "tags": [
      "wasm",
      "memory",
      "linear-memory",
      "pages",
      "out-of-memory",
      "host-error"
    ],
    "symptoms": "- Transaction simulation or invocation terminates with `HostError(Error(Budget, Exceeded))` or `HostError::MemoryExhausted`.\n- CLI output indicates out-of-memory (OOM) or memory page allocation failur",
    "solutions": "1. **Use Host Collections:** Replace `std::vec::Vec` and `std::collections::BTreeMap` with Soroban SDK host-managed types (`soroban_sdk::Vec`, `soroban_sdk::Map`), which reside in host memory and do n"
  },
  {
    "id": "simulate-tx-auth-failed",
    "title": "RPC Error - Simulate Transaction Authorization Verification Failed",
    "category": "rpc-error",
    "error_code": "RPC::SimulateAuthFailed",
    "verified": True,
    "summary": "Simulation node failed to verify invocation authorization payload or signature footprint.",
    "tags": [
      "rpc",
      "simulateTransaction",
      "auth",
      "signature",
      "rpc-error"
    ],
    "symptoms": "- RPC returns error JSON `{\"code\": -32600, \"message\": \"Simulation failed: Auth error\"}`.\n- Invocation client output: `Failed to construct Soroban auth tree`.",
    "solutions": "1. **Sign with Correct Key:** Ensure signature matches target address payload.\n2. **Re-simulate Auth Tree:** Use JS SDK `assembleTransaction` to compute full auth requirements automatically."
  },
  {
    "id": "storage-key-missing",
    "title": "RPC Error - Requested Ledger Storage Key Missing",
    "category": "rpc-error",
    "error_code": "RPC::StorageKeyNotFound",
    "verified": True,
    "summary": "RPC getLedgerEntries endpoint returned empty result for requested XDR storage key.",
    "tags": [
      "rpc",
      "storage",
      "key",
      "getLedgerEntries",
      "rpc-error"
    ],
    "symptoms": "- `getLedgerEntries` response returns `entries: []`.\n- SDK throws `NotFoundError` when fetching contract data instance.",
    "solutions": "1. **Initialize State:** Execute contract setup/init function first.\n2. **Check Archival Status:** Query state archival RPC endpoint to verify if restoration is required."
  },
  {
    "id": "scval-type-conversion-error",
    "title": "SDK Error - ScVal to Native Rust Type Conversion Failed",
    "category": "sdk-error",
    "error_code": "SDK::ScValConversionFailed",
    "verified": True,
    "summary": "Soroban SDK or client library failed to convert a serialized ScVal or Val handle into the expected native Rust type (e.g. integer width mismatch or invalid symbol).",
    "tags": [
      "sdk",
      "scval",
      "type-conversion",
      "val",
      "conversion",
      "deserialization"
    ],
    "symptoms": "- Contract invocations panic with `ConversionError` when deserializing function arguments or returned values.\n- Client SDKs (JS/TS, Python) fail with `Invalid ScVal discriminator` or `Cannot convert S",
    "solutions": "1. **Use Explicit ScVal Type Constructors:** Construct arguments explicitly in SDKs (`nativeToScVal(100n, { type: 'i128' })`).\n2. **Use `TryFromVal` for Safe Conversion:** In Rust contracts, convert d"
  },
  {
    "id": "value-conversion-failed",
    "title": "SDK Error - ScVal to Native JavaScript/Rust Value Conversion Failed",
    "category": "sdk-error",
    "error_code": "SDK::ScValConversionError",
    "verified": True,
    "summary": "Soroban SDK failed to deserialize raw XDR ScVal into target programming language primitive or struct.",
    "tags": [
      "sdk",
      "scval",
      "xdr",
      "conversion",
      "sdk-error"
    ],
    "symptoms": "- SDK throws `TypeError: Cannot convert ScVal to native type`.\n- Panic in Rust client: `called Result::unwrap() on an Err value: ConversionError`.",
    "solutions": "1. **Use Type-Safe Binding Generator:** Generate client bindings using `soroban contract bindings typescript`.\n2. **Explicit Conversion Helpers:** Use `scValToNative()` and `nativeToScVal()` helpers w"
  }
]

def load_entries(custom_dir=None):
    if custom_dir and os.path.exists(custom_dir):
        # Dynamically load from local directory if provided
        import glob
        pattern = os.path.join(custom_dir, '**', '*.md')
        files = glob.glob(pattern, recursive=True)
        if files:
            loaded = []
            for f in files:
                try:
                    with open(f, 'r', encoding='utf-8') as ef:
                        text = ef.read()
                    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
                    if match:
                        yaml_str, body = match.group(1), match.group(2)
                        meta = {}
                        for line in yaml_str.splitlines():
                            if ':' in line:
                                k, v = line.split(':', 1)
                                k, v = k.strip(), v.strip().strip('"\'')
                                if v.lower() == 'true': v = True
                                elif v.lower() == 'false': v = False
                                meta[k] = v
                        meta['body'] = body
                        loaded.append(meta)
                except Exception:
                    pass
            if loaded:
                return loaded
    return BUNDLED_ENTRIES
