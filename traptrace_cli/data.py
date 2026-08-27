import os
import glob
import re

# Bundled fallback dataset of 35 Soroban errors for instant offline lookup
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
    "soroban_version": "21.0.0",
    "severity": "info",
    "related_entries": [],
    "symptoms": "- CLI displays `Error: Account G... not found on network`.\n- Invocation or deployment fails during transaction signing.",
    "root_causes": "1. **Unfunded Account:** Newly generated keys must be funded with minimum native XLM balance.\n2. **Incorrect Identity:** Using wrong keypair alias.",
    "reproduction_steps": "soroban keys generate alice\nsoroban contract deploy --wasm target/wasm32-unknown-unknown/release/contract.wasm --source alice",
    "solutions": "1. **Fund Account via Friendbot (Testnet):**\n```bash\nsoroban keys fund alice --network testnet\n```\n2. **Transfer Native Balance (Mainnet):** Send XLM to public key before deployment.",
    "references": "- [Soroban CLI Identity Management](https://developers.stellar.org/docs/tools/developer-tools/cli/keys)"
  },
  {
    "id": "contract-spec-missing",
    "title": "CLI Error - WASM Contract Specification (ABI) Metadata Missing or Stripped",
    "category": "cli-error",
    "error_code": "CLI::ContractSpecMissing",
    "verified": True,
    "summary": "Contract WASM file deployed without embedded contract specification custom sections, preventing automated ABI decoding, binding generation, and CLI inspection.",
    "tags": [
      "cli-error",
      "abi",
      "wasm",
      "spec",
      "tooling"
    ],
    "soroban_version": "21.0.0",
    "severity": "warning",
    "related_entries": [
      "wasm-verification-failed",
      "host-invalid-action"
    ],
    "symptoms": "- `stellar contract bindings` or `soroban contract bindings typescript` fails with `Error: Contract has no spec`.\n- `traptrace abi <contract_id>` or the Web Studio WASM ABI tab indicates `No exported contract functions found`.\n- Block explorers cannot render human-readable method signatures or argument input fields.",
    "root_causes": "1. **Aggressive WASM Optimization Stripping Custom Sections:** Compiling with `wasm-opt --strip-all` or `wasm-strip` instead of preserving the `.soroban_spec` custom section.\n2. **Missing `contractimpl` Macro Attribute:** Writing Rust methods without decorating the `impl` block with `#[contractimpl]`.\n3. **Manual WASM Assembly:** Compiling raw WASM bytecode without the Soroban SDK build target.",
    "reproduction_steps": "wasm-opt -Oz --strip-all contract.wasm -o contract_stripped.wasm\nstellar contract bindings typescript --wasm contract_stripped.wasm --output-dir ./bindings",
    "solutions": "1. **Preserve Custom Sections in `wasm-opt`:** When running `wasm-opt`, use `--strip-debug` instead of `--strip-all` to keep `.soroban_spec`:\n   ```bash\n   wasm-opt -Oz --strip-debug target/wasm32-unknown-unknown/release/contract.wasm -o contract.optimized.wasm\n   ```\n2. **Use `stellar contract build`:** Prefer the official Stellar CLI build command which automatically optimizes while preserving metadata:\n   ```bash\n   stellar contract build\n   ```\n3. **Verify with TrapTrace WASM Inspector:** Use `traptrace abi <contract_id>` to confirm your deployed contract exports valid method specifications.",
    "references": "- [Soroban CLI Contract Build & Optimization](https://developers.stellar.org/docs/tools/developer-tools/cli/stellar-cli)\n- [Soroban Contract Specification Format](https://developers.stellar.org/docs/learn/smart-contract-internals/types#contract-spec)"
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
    "soroban_version": "21.0.0",
    "severity": "warning",
    "related_entries": [
      "simulate-tx-auth-failed",
      "auth-invalid-signature"
    ],
    "symptoms": "- Transaction simulation or broadcast fails with error `Invalid network passphrase` or `Transaction signature verification failed for target network`.\n- Stellar RPC returns simulation error: `HostError: Error(Context, InvalidAction)` with transaction signature mismatch.\n- CLI displays error: `error: the transaction was signed for a different network passphrase than the connected node`.",
    "root_causes": "1. **Passphrase Mismatch:** The transaction envelope was constructed and signed with one network passphrase (e.g. `Public Global Stellar Network ; September 2015`) but submitted to a different node RPC (e.g. `https://soroban-testnet.stellar.org` expecting `Test SDF Network ; September 2015`).\n2. **CLI Network Configuration Drift:** The `--network` flag was omitted or pointed to a customized local standalone network while `--rpc-url` was directed at Public Testnet.\n3. **Multi-Environment Signature Pipelines:** Pre-signed envelopes generated in staging or offline hardware keys were broadcast to testnet without updating the target network hash.",
    "reproduction_steps": "soroban contract invoke \\\n  --id CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC \\\n  --network-passphrase \"Public Global Stellar Network ; September 2015\" \\\n  --rpc-url https://soroban-testnet.stellar.org \\\n  --fn hello",
    "solutions": "1. **Explicitly Specify Network in CLI:** Use the pre-configured `--network testnet` or `--network mainnet` flag rather than hardcoding raw passphrase strings.\n2. **Verify Environment Configurations:** Ensure `STELLAR_NETWORK_PASSPHRASE` matches the RPC endpoint defined in `STELLAR_RPC_URL`.\n3. **Use TrapTrace Network Manager:** Use `traptrace inspect <tx_hash> --network testnet` or `traptrace rpc` to verify the node's official passphrase before signing.",
    "references": "- [Stellar Network Passphrases Reference](https://developers.stellar.org/docs/learn/fundamentals/networks)\n- [Soroban CLI Network Management](https://developers.stellar.org/docs/tools/developer-tools/cli/stellar-cli)"
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
    "soroban_version": "21.0.0",
    "severity": "info",
    "related_entries": [],
    "symptoms": "- Transaction rejected with status `txBAD_SEQ`.\n- CLI output: `Transaction submission failed: ResultCode txBAD_SEQ`.",
    "root_causes": "1. **Concurrent Submissions:** Multiple transactions submitted simultaneously using the same source account.\n2. **Out of Sync Sequence Cache:** CLI local sequence counter out of sync with RPC node state.",
    "reproduction_steps": "Submit two transactions rapidly from separate terminal instances using identical `--source` keypair.",
    "solutions": "1. **Retry Transaction:** Re-run command to refresh sequence number automatically from RPC.\n2. **Use Channels:** For high-throughput automated scripts, use separate channel accounts for transaction signing.",
    "references": "- [Stellar Horizon & RPC Transaction Flow](https://developers.stellar.org/docs/learn/fundamentals/transactions/operations)"
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
    "soroban_version": "21.0.0",
    "severity": "critical",
    "related_entries": [
      "unreachable-code-reached",
      "wasm-memory-exhausted"
    ],
    "symptoms": "- Contract installation via `stellar contract install` or `soroban contract deploy` fails during the simulation or upload phase.\n- CLI output displays: `error: contract wasm verification failed: invalid import or unsupported opcode`.\n- Simulation RPC returns: `HostError(Error(WasmVm, InvalidAction))` or `contract bytecode failed validation against VM protocol limits`.",
    "root_causes": "1. **Floating Point Operations (f32/f64):** Standard Rust mathematical libraries compiled without `#![no_std]` or using floating-point operations that non-deterministically violate Soroban VM determinism rules.\n2. **Missing WASM Target Optimization:** The WASM file was compiled for generic `wasm32-unknown-unknown` without running `stellar contract build` or `soroban-opt`, leaving unsupported external imports or standard library system call bindings.\n3. **WASM Section Limit Exceeded:** The compiled bytecode imports host functions from non-existent modules or exceeds custom section table limits defined in the current Stellar Protocol version.",
    "reproduction_steps": "# Create a dummy malformed WASM header\necho -n -e '\\x00\\x61\\x73\\x6d\\x01\\x00\\x00\\x00\\x00\\x05\\x01\\x02\\x03\\x04\\x05' > invalid_contract.wasm\n\n# Attempt to install on testnet\nsoroban contract install \\\n  --wasm invalid_contract.wasm \\\n  --source default \\\n  --network testnet",
    "solutions": "1. **Build with the Official Toolchain:** Always compile contracts with `stellar contract build` (or `cargo build --target wasm32-unknown-unknown --release` followed by `stellar contract optimize`).\n2. **Ensure `#![no_std]` Compliance:** Avoid standard library dependencies that invoke OS syscalls (`std::fs`, `std::net`, `std::time`, or threading).\n3. **Run WASM Inspection & Validation:** Use `traptrace decode` or `wasm-tools validate contract.wasm` prior to deployment to verify opcode determinism and section tables.",
    "references": "- [Stellar Developers: Building and Optimizing Soroban Contracts](https://developers.stellar.org/docs/build/smart-contracts/getting-started/build)\n- [Soroban VM Bytecode Specification and Opcode Constraints](https://developers.stellar.org/docs/learn/smart-contract-internals/execution-model)"
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
    "soroban_version": "21.0.0",
    "severity": "critical",
    "related_entries": [
      "unreachable-code-reached",
      "host-invalid-action"
    ],
    "symptoms": "- Contract simulation or execution aborts immediately with `HostError(Error(Context, InvalidAction))` or `HostError::ArithDomain`.\n- Diagnostic events indicate an unreachable panic (`attempt to add with overflow` or `attempt to divide by zero`).\n- Token transfers, reward calculation math, or liquidity pool calculations fail during extreme value inputs.",
    "root_causes": "1. **Unchecked Integer Math:** Performing raw Rust operators (`+`, `-`, `*`, `/`) in release or debug mode where arithmetic overflows trigger a WASM trap.\n2. **Division by Zero:** Executing `/` or `%` on a variable denominator that evaluated to `0` without guard checks.\n3. **Lossy Casting:** Casting large integer types (`i128` to `u64` or `i64`) where values exceed destination type boundaries.",
    "reproduction_steps": "use soroban_sdk::{contract, contractimpl, Env};\n\n#[contract]\npub struct ArithErrorContract;\n\n#[contractimpl]\nimpl ArithErrorContract {\n    pub fn calculate_overflow(_env: Env, base: u128) -> u128 {\n        // Raw arithmetic addition triggers overflow panic on u128::MAX\n        base + 1\n    }\n\n    pub fn calculate_divide_zero(_env: Env, val: u64, divisor: u64) -> u64 {\n        // Triggers division by zero if divisor is 0\n        val / divisor\n    }\n}",
    "solutions": "1. **Use Checked Arithmetic:** Replace raw operators with checked arithmetic methods (`checked_add`, `checked_sub`, `checked_mul`, `checked_div`) and handle `None` gracefully.\n2. **Use Saturating Arithmetic:** Use `saturating_add` or `saturating_sub` where clamping values to type limits is acceptable.\n3. **Explicit Zero Checks:** Validate divisors before executing division or modulo operations (`if divisor == 0 { return Err(Error::ZeroDivisor); }`).",
    "references": "- [Stellar Developers: Soroban Safe Math Practices](https://developers.stellar.org/docs/learn/smart-contract-internals/errors)\n- [Rust Standard Library Checked Arithmetic](https://doc.rust-lang.org/std/primitive.u128.html#method.checked_add)"
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
    "soroban_version": "21.0.0",
    "severity": "critical",
    "related_entries": [
      "simulate-tx-auth-failed",
      "host-invalid-action"
    ],
    "symptoms": "- Transaction simulation or on-chain submission fails with `HostError(Error(Auth, InvalidAction))` or `HostError::AuthInvalidSignature`.\n- RPC response returns `Simulation failed: Auth error: Signature verification failed`.\n- Invocation involving custom accounts, multi-sig contracts, or delegated `require_auth` fails during signature checking.",
    "root_causes": "1. **Incorrect Signer Keypair:** Signing the invocation authorization payload with a secret key that does not correspond to the public key or `Address` declared in `require_auth`.\n2. **Signature Hash Mismatch:** Signing a different authorization tree hash (e.g. payload created for a different network passphrase or nonce) than what the Soroban host validates.\n3. **Invalid Signature Encoding:** Passing a malformed, non-canonical 64-byte Ed25519 or 65-byte Secp256k1 signature slice to custom account verification methods (`__check_auth`).\n4. **Expired Authorization Nonce:** Reusing an old authorization payload whose sequence nonce has already been consumed on-chain.",
    "reproduction_steps": "use soroban_sdk::{contract, contractimpl, Address, Env};\n\n#[contract]\npub struct AuthTestContract;\n\n#[contractimpl]\nimpl AuthTestContract {\n    pub fn transfer_protected(env: Env, from: Address, to: Address, amount: i128) {\n        // Enforces explicit cryptographic authorization\n        from.require_auth();\n        // State mutation logic...\n    }\n}",
    "solutions": "1. **Verify Signer Matches Address:** Ensure the transaction signer or simulated auth entry keypair matches the `Address` parameter passed to `require_auth()`.\n2. **Simulate Auth Footprints First:** Run `traptrace simulate <xdr>` to generate the required Soroban authorization tree before signing.\n3. **Verify Network Passphrase:** Ensure off-chain signers are hashing signatures with the correct network passphrase (`Test SDF Network ; September 2015` on Testnet, `Public Global Stellar Network ; September 2015` on Mainnet).\n4. **Handle Custom Account Auth:** In smart contract accounts implementing `__check_auth`, ensure signature verification returns `Ok(())` only when valid and bubbles explicit errors.",
    "references": "- [Stellar Developers: Smart Contract Authorization](https://developers.stellar.org/docs/learn/smart-contract-internals/authorization)\n- [Soroban Rust SDK Address and Auth Documentation](https://docs.rs/soroban-sdk/latest/soroban_sdk/struct.Address.html)"
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
    "soroban_version": "21.0.0",
    "severity": "critical",
    "related_entries": [
      "sub-invocation-failed"
    ],
    "symptoms": "- Transaction simulation or invocation returns `HostError::BudgetExceeded`.\n- CLI output displays `Error: HostError(Error(Budget, Exceeded))`.\n- Contract fails during high-iteration loops, complex cryptographic verification, or large serialization operations.",
    "root_causes": "1. **Unbounded Loops:** Iterating over unbounded storage vectors or maps within a single contract call.\n2. **Heavy Computation:** Performing cryptographic hashing, sorting, or heavy math operations inside WASM without leveraging built-in host functions.\n3. **Large Memory Allocations:** Instantiating large vectors, buffers, or complex nested structures that exceed allocated byte limits.",
    "reproduction_steps": "// Contract code containing unbounded iteration\npub fn process_all_items(env: Env, items: Vec<u32>) {\n    for item in items.iter() {\n        // Heavy computation per item causing CPU budget failure\n        let _result = heavy_hash_calculation(item);\n    }\n}",
    "solutions": "1. **Chunking & Pagination:** Break processing into smaller batches across multiple transactions rather than processing in a single call.\n2. **Optimize Host Functions:** Use Soroban host-provided primitives (`env.crypto().sha256()`) instead of pure WASM crypto implementations.\n3. **Increase Budget (Test Harness Only):** In local unit tests, raise the budget with `env.budget().reset_unlimited()`.",
    "references": "- [Stellar Developers: Soroban Resource Model](https://developers.stellar.org/docs/learn/fundamentals/fees-and-metering)\n- [Soroban Host Environment Budget Specification](https://github.com/stellar/rs-soroban-env)"
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
    "soroban_version": "21.0.0",
    "severity": "critical",
    "related_entries": [
      "budget-exceeded",
      "storage-ledger-entry-not-found"
    ],
    "symptoms": "- Transaction simulation or invocation returns `HostError(Error(Storage, ExceededLimit))` or `HostError::StorageValueExceedsLimit`.\n- Invocation fails when writing large collections (`Vec`, `Map`, or oversized `Bytes`) to instance or persistent storage.\n- RPC error indicates `txINTERNAL_ERROR` or simulation footprint exceeds maximum allowable ledger entry byte quota.",
    "root_causes": "1. **Monolithic Storage Arrays:** Appending unbounded items to a single `Vec` or `Map` under one storage key until the serialized XDR exceeds the 64KB ledger entry limit.\n2. **Oversized String / Blob Payloads:** Writing raw image data, JSON documents, or large byte buffers into a single storage slot instead of off-chain decentralized storage or split chunks.\n3. **Bloated Instance Storage:** Storing heavy dynamic user data in `instance` storage rather than dedicated partitioned keys in `persistent` storage.",
    "reproduction_steps": "use soroban_sdk::{contract, contractimpl, symbol_short, Bytes, Env, Symbol};\n\nconst LARGE_DATA: Symbol = symbol_short!(\"BIG_DATA\");\n\n#[contract]\npub struct SizeLimitContract;\n\n#[contractimpl]\nimpl SizeLimitContract {\n    pub fn store_oversized_payload(env: Env) {\n        // Create a 70KB buffer exceeding the 64KB Soroban ledger entry limit\n        let mut big_bytes = Bytes::new(&env);\n        for _ in 0..70_000 {\n            big_bytes.push_back(0x42);\n        }\n        env.storage().persistent().set(&LARGE_DATA, &big_bytes);\n    }\n}",
    "solutions": "1. **Partition State Across Keys:** Store individual items under distinct indexed keys (e.g. `DataKey::Item(u32)`) rather than a single monolithic `Vec`.\n2. **Chunking Mechanism:** Split large payloads into 32KB chunks stored across deterministic sub-keys (`DataKey::Chunk(hash, index)`).\n3. **Off-Chain Content Hashing:** Store only cryptographic hashes (e.g. IPFS / Arweave CID `BytesN<32>`) in contract storage and retain the raw data off-chain.\n4. **Pre-Flight Metering:** Run `traptrace simulate <xdr>` to check simulated storage byte footprint before submitting transactions.",
    "references": "- [Stellar Developers: Soroban Resource Limits and Fees](https://developers.stellar.org/docs/learn/fundamentals/fees-and-metering)\n- [CAP-0046: Soroban State Archival and Storage Sizing](https://github.com/stellar/stellar-protocol/blob/master/core/cap-0046.md)"
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
    "soroban_version": "21.0.0",
    "severity": "critical",
    "related_entries": [
      "account-not-found",
      "entry-archived-ttl-expired"
    ],
    "symptoms": "- Call fails with `Error(Storage, MissingValue)` or `ContractNotFound`.\n- Soroban CLI outputs `Error: Contract instance C... does not exist`.",
    "root_causes": "1. **Incorrect Contract Address:** Typo in contract address hash.\n2. **Network Mismatch:** Calling Testnet contract ID against Mainnet RPC.\n3. **Uninstalled WASM:** WASM code hash not uploaded prior to instance creation.",
    "reproduction_steps": "soroban contract invoke --id CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA --fn hello",
    "solutions": "1. **Verify Target Contract ID:** Re-check deployment output logs for exact address.\n2. **Confirm Network Target:** Ensure `--network testnet` / `--network mainnet` matches deployment target.",
    "references": "- [Stellar Soroban Contract Deployment Guide](https://developers.stellar.org/docs/build/smart-contracts/deploying)"
  },
  {
    "id": "cross-contract-reentrancy-blocked",
    "title": "Host Error - Cross-Contract Re-entrancy Blocked",
    "category": "host-error",
    "error_code": "HostError::ReentrancyBlocked",
    "verified": True,
    "summary": "Soroban host VM detected mutual recursive invocation cycle across contract call frames without explicit reentrancy permissions.",
    "tags": [
      "host-error",
      "reentrancy",
      "cross-contract",
      "security",
      "recursion"
    ],
    "soroban_version": "21.0.0",
    "severity": "critical",
    "related_entries": [
      "sub-invocation-failed",
      "budget-exceeded"
    ],
    "symptoms": "- Complex cross-contract calls fail with `HostError(Context, ReentrancyBlocked)` or WASM call stack abort.\n- Flash loan or automated market maker (AMM) callbacks fail unexpectedly.\n- Diagnostic events output circular contract invocation traces: `Contract A -> Contract B -> Contract A`.",
    "root_causes": "1. **Direct Circular Call Stack:** Contract A called Contract B, which attempted to call back into Contract A while execution frame A was still active.\n2. **Reentrancy Guard Activation:** The target contract employs a reentrancy mutex (`storage().instance().set(&LOCKED, &True)`) and detected an interleaved invocation.\n3. **Unchecked Callback Interfaces:** Implementing external hook/callback mechanisms without decoupling state mutations from external dispatch.",
    "reproduction_steps": "use soroban_sdk::{contract, contractimpl, Address, Env};\n\n#[contract]\npub struct ReentrantContract;\n\n#[contractimpl]\nimpl ReentrantContract {\n    pub fn execute_callback(env: Env, target: Address) {\n        let client = CallbackClient::new(&env, &target);\n        client.on_callback(&env.current_contract_address());\n    }\n}",
    "solutions": "1. **Checks-Effects-Interactions Pattern:** Perform all internal balance and state updates *before* calling external contract interfaces:\n   ```rust\n   // 1. Checks\n   assert!(balance >= amount);\n   // 2. Effects (Internal State Mutation)\n   env.storage().persistent().set(&user, &(balance - amount));\n   // 3. Interactions (External Call)\n   token_client.transfer(&user, &recipient, &amount);\n   ```\n2. **Asynchronous Architecture / Split Transactions:** Design multi-step workflows across separate ledger transactions rather than deep synchronous nested callbacks.\n3. **Non-Reentrant Status Enums:** Guard state transitions with strict lifecycle status machines instead of nested synchronous queries.",
    "references": "- [Soroban Cross-Contract Calls & Security](https://developers.stellar.org/docs/learn/smart-contract-internals/cross-contract)\n- [SWC-107: Reentrancy Vulnerability Guidance](https://swcregistry.io/docs/SWC-107)"
  },
  {
    "id": "crypto-curve25519-invalid-scalar",
    "title": "Host Error - Curve25519 / Ed25519 Invalid Scalar or Point",
    "category": "host-error",
    "error_code": "HostError::CryptoScalarInvalid",
    "verified": True,
    "summary": "Host cryptographic verification failed due to non-canonical point encoding, invalid scalar length, or scalar out of subgroup range.",
    "tags": [
      "host-error",
      "crypto",
      "curve25519",
      "ed25519",
      "verification"
    ],
    "soroban_version": "21.0.0",
    "severity": "critical",
    "related_entries": [
      "crypto-verification-failed",
      "auth-invalid-signature"
    ],
    "symptoms": "- Invocations involving custom cryptographic verification panic with `HostError::CryptoScalarInvalid` or `CryptoError`.\n- Zero-knowledge proof (ZKP) or multi-party computation (MPC) threshold signatures fail verification.\n- Diagnostic events output `crypto_ed25519_verify` or `curve25519_scalar_mul` trap codes.",
    "root_causes": "1. **Non-Canonical Point Encoding:** The passed public key or compressed Montgomery/Edwards point has highest-bit corruption or violates canonical 32-byte representation.\n2. **Scalar Out of Prime Order:** Scalar integer value is greater than or equal to the prime curve group order $L = 2^{252} + 27742317777372353535851937790883648493$.\n3. **Invalid Byte Array Length:** Passing a 64-byte raw signature into a function expecting a 32-byte public key slice or vice versa.",
    "reproduction_steps": "use soroban_sdk::{contract, contractimpl, BytesN, Env};\n\n#[contract]\npub struct CryptoScalarContract;\n\n#[contractimpl]\nimpl CryptoScalarContract {\n    pub fn verify_scalar(env: Env, invalid_key: BytesN<32>, msg: BytesN<32>, sig: BytesN<64>) {\n        env.crypto().ed25519_verify(&invalid_key, &msg.into(), &sig);\n    }\n}",
    "solutions": "1. **Canonicalize Public Keys Before Hashing:** Ensure client-side cryptographic libraries serialize keys using strict canonical Little-Endian representation:\n   ```typescript\n   import { Keypair } from '@stellar/stellar-sdk';\n   const canonicalBytes = keypair.rawPublicKey();\n   ```\n2. **Validate Scalar Subgroup Range:** Check scalar values with modulo arithmetic against the group order $L$ before passing to host operations.\n3. **Use Soroban SDK Native Crypto Helpers:** Prefer `env.crypto().ed25519_verify()` over custom WASM-compiled cryptography libraries.",
    "references": "- [RFC 8032: Edwards-Curve Digital Signature Algorithm (EdDSA)](https://datatracker.ietf.org/doc/html/rfc8032)\n- [Soroban Host Cryptography API](https://docs.rs/soroban-sdk/latest/soroban_sdk/struct.Crypto.html)"
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
    "soroban_version": "21.0.0",
    "severity": "critical",
    "related_entries": [
      "auth-invalid-signature",
      "host-invalid-action"
    ],
    "symptoms": "- Contract execution or simulation aborts with `HostError(Error(Crypto, InvalidInput))` or `HostError::CryptoError`.\n- Host diagnostic event logs report: `crypto function verification failure` or `ed25519 verification failed`.\n- Zero-knowledge proof, multi-sig verification, or off-chain message attestation methods fail with immediate execution revert.",
    "root_causes": "1. **Tampered Signature Payload:** The message byte slice passed into `env.crypto().ed25519_verify(&public_key, &message, &signature)` or `secp256k1_verify` does not match the exact bytes hashed during signing.\n2. **Invalid Public Key or Signature Length:** Passing a public key or signature byte buffer whose length deviates from curve standards (e.g. 32 bytes for Ed25519 public keys, 64 bytes for Ed25519 signatures, 65 bytes for uncompressed Secp256k1).\n3. **Mismatched Signature Encoding:** Providing DER-encoded or hex-encoded signatures when the Soroban cryptographic host function expects raw binary bytes (`BytesN<64>`).",
    "reproduction_steps": "use soroban_sdk::{contract, contractimpl, crypto::Crypto, Bytes, BytesN, Env};\n\n#[contract]\npub struct CryptoVerifierContract;\n\n#[contractimpl]\nimpl CryptoVerifierContract {\n    pub fn verify_signature(\n        env: Env,\n        public_key: BytesN<32>,\n        message: Bytes,\n        invalid_signature: BytesN<64>,\n    ) {\n        // Attempting to verify with an intentional dummy signature\n        env.crypto().ed25519_verify(&public_key, &message, &invalid_signature);\n    }\n}",
    "solutions": "1. **Verify Exact Message Hashing:** Ensure message payloads are canonicalized before hashing (e.g. SHA-256 / Keccak-256) and match the exact signing domain parameters.\n2. **Validate Fixed-Size Byte Arrays:** Enforce `BytesN<32>` and `BytesN<64>` type constraints in function arguments so malformed buffers fail before reaching the host cryptographic primitives.\n3. **Use Soroban Custom Account Contract Interfaces:** For account authentication, prefer implementing the standard `CustomAccountInterface` with `__check_auth` rather than manual ad-hoc crypto verification inside contract business logic.",
    "references": "- [Soroban SDK Crypto Module Docs](https://docs.rs/soroban-sdk/latest/soroban_sdk/crypto/struct.Crypto.html)\n- [Stellar Smart Contract Auth & Cryptography Standards](https://developers.stellar.org/docs/learn/smart-contract-internals/authorization)"
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
    "soroban_version": "21.0.0",
    "severity": "info",
    "related_entries": [],
    "symptoms": "- Call fails with error string `Error(Storage, ExceededStateArchival)`.\n- Transaction simulation rejects access to persistent key with message `ContractData entry archived`.\n- Previously functioning contract suddenly fails when accessing user balance or state.",
    "root_causes": "1. **State Archival:** State entry was not bumped prior to reaching minimum TTL threshold (CAP-0046).\n2. **Missing Restored Access:** Accessing archived state without issuing a `RestoreFootprint` transaction.",
    "reproduction_steps": "pub fn read_user_data(env: Env, user: Address) -> UserData {\n    // Fails if TTL has reached zero\n    env.storage().persistent().get(&user).unwrap()\n}",
    "solutions": "1. **Bump TTL in Contract Logic:** Use `env.storage().persistent().extend_ttl(&key, threshold, extend_to)` to proactively renew storage lifespan.\n2. **Issue Restore Transaction:** Submit a `RestoreFootprint` operation via Soroban CLI or SDK before invoking the contract.\n\n```bash\nsoroban contract restore --id <CONTRACT_ID> --key <STORAGE_KEY>\n```",
    "references": "- [CAP-0046: Soroban State Archival](https://github.com/stellar/stellar-protocol/blob/master/core/cap-0046.md)\n- [Stellar Documentation: State Archival Lifecycle](https://developers.stellar.org/docs/learn/fundamentals/state-archival)"
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
    "soroban_version": "21.0.0",
    "severity": "critical",
    "related_entries": [
      "sub-invocation-failed",
      "unreachable-code-reached"
    ],
    "symptoms": "- Transaction simulation returns `HostError(Error(Context, InvalidAction))` or `HostError::InvalidAction`.\n- Diagnostic events log indicates failure inside host functions such as `crypto`, `events`, or `prng`.\n- Contract aborts immediately during cryptographic verification, event publishing, or invalid handle conversion.",
    "root_causes": "1. **Malformed Cryptographic Inputs:** Passing invalid public key byte lengths or improperly encoded signatures to host functions like `env.crypto().ed25519_verify()`.\n2. **Excessive Event Topics:** Calling `env.events().publish(...)` with more than 4 topic elements, violating the Soroban topic limit invariant.\n3. **Invalid Context / State Mutation:** Attempting a reentrant call or mutating host storage during read-only execution contexts.\n4. **Invalid RawVal Handle Conversion:** Attempting to cast or dereference an invalid or uninitialized host `Val` handle.",
    "reproduction_steps": "use soroban_sdk::{contract, contractimpl, vec, BytesN, Env, Symbol};\n\n#[contract]\npub struct InvalidActionContract;\n\n#[contractimpl]\nimpl InvalidActionContract {\n    pub fn trigger_invalid_event(env: Env) {\n        // Violates topic length limit (max 4 topics allowed in Soroban)\n        let topics = (\n            Symbol::new(&env, \"topic1\"),\n            Symbol::new(&env, \"topic2\"),\n            Symbol::new(&env, \"topic3\"),\n            Symbol::new(&env, \"topic4\"),\n            Symbol::new(&env, \"topic5\"), // Invalid 5th topic\n        );\n        env.events().publish(topics, 100u32);\n    }\n}",
    "solutions": "1. **Verify Cryptographic Key and Signature Lengths:** Ensure public keys are exact 32-byte slices (`BytesN<32>`) and signatures are exact 64-byte slices (`BytesN<64>`) before calling verification host methods.\n2. **Limit Event Topics:** Ensure all event topic tuples contain between 1 and 4 elements maximum.\n3. **Validate Raw Val Handles:** Use SDK wrapper types (`Address`, `Bytes`, `Vec`, `Map`) rather than raw `Val` / `RawVal` representations to prevent uninitialized handle errors.\n4. **Inspect Diagnostic Events:** Run `traptrace inspect <tx_hash>` or check `diagnosticEvents` in the RPC response to pinpoint the exact host function call that triggered `InvalidAction`.",
    "references": "- [Soroban Host Environment Error Codes (rs-soroban-env)](https://github.com/stellar/rs-soroban-env)\n- [Stellar Developers: Smart Contract Events & Topics](https://developers.stellar.org/docs/learn/smart-contract-internals/events)"
  },
  {
    "id": "instance-already-initialized",
    "title": "Host Error - Smart Contract Instance Already Initialized",
    "category": "host-error",
    "error_code": "HostError::ContractAlreadyInitialized",
    "verified": True,
    "summary": "Attempting to invoke contract initialization logic on an already initialized contract instance.",
    "tags": [
      "host-error",
      "initialization",
      "constructor",
      "security",
      "state"
    ],
    "soroban_version": "21.0.0",
    "severity": "critical",
    "related_entries": [
      "host-invalid-action",
      "sub-invocation-user-error"
    ],
    "symptoms": "- Contract deployment and initialization scripts fail with `ContractAlreadyInitialized` or custom init error enum.\n- Re-invoking constructor-style methods like `init()`, `initialize()`, or `set_admin()` reverts on-chain.\n- Transaction simulation fails during contract onboarding flows.",
    "root_causes": "1. **Re-initialization Guard Triggered:** The contract implementation uses a boolean flag in instance storage (`IS_INIT`) or constructor pattern, and a second invocation was attempted after initial deployment.\n2. **Factory Contract Race Condition:** A factory contract deployed the instance and called `initialize` in the same transaction, followed by an external caller attempting initialization again.\n3. **Missing Idempotency Handling:** The deployment pipeline did not check if the contract was already initialized before calling setup methods.",
    "reproduction_steps": "use soroban_sdk::{contract, contractimpl, symbol_short, Env, Symbol};\n\nconst IS_INIT: Symbol = symbol_short!(\"IS_INIT\");\n\n#[contract]\npub struct InitializedContract;\n\n#[contractimpl]\nimpl InitializedContract {\n    pub fn initialize(env: Env) -> Result<(), ()> {\n        if env.storage().instance().has(&IS_INIT) {\n            return Err(()); // Already initialized\n        }\n        env.storage().instance().set(&IS_INIT, &True);\n        Ok(())\n    }\n}",
    "solutions": "1. **Check Initialization State First:** Use `.has(&IS_INIT)` before attempting initialization calls:\n   ```rust\n   if !client.is_initialized() {\n       client.initialize(&admin);\n   }\n   ```\n2. **Use Protocol 21 Native `__constructor`:** Utilize native Soroban constructors that can only execute once during initial instance deployment.\n3. **Atomic Factory Deployment:** Deploy and initialize instances in a single atomic transaction envelope.",
    "references": "- [Soroban Smart Contract Initialization Patterns](https://developers.stellar.org/docs/learn/smart-contract-internals)\n- [Stellar CAP-0046: Lifecycle Management](https://stellar.org)"
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
    "soroban_version": "21.0.0",
    "severity": "critical",
    "related_entries": [
      "entry-archived-ttl-expired",
      "temporary-storage-expired"
    ],
    "symptoms": "- Contract invocations revert during simulation with `HostError(Error(Storage, InstanceArchived))` or `Error(Storage, DeadEntry)`.\n- Transaction footprint indicates `ContractData` or `ContractCode` ledger keys are archived.\n- Contract execution cannot proceed until a `RestoreFootprintOp` transaction is submitted and confirmed on-chain.",
    "root_causes": "1. **Infrequent Contract Invocation:** Contracts that remain idle without invocations or explicit TTL bumps eventually hit their `live_until_ledger` threshold.\n2. **Missing Instance TTL Bump:** Failing to execute `env.storage().instance().extend_ttl(...)` in contract initialization or execution entrypoints.\n3. **Unrestored Footprint:** Attempting to invoke an archived contract without preceding the call with a footprint restoration operation.",
    "reproduction_steps": "use soroban_sdk::{contract, contractimpl, symbol_short, Env, Symbol};\n\nconst STATE_KEY: Symbol = symbol_short!(\"admin\");\n\n#[contract]\npub struct IdleContract;\n\n#[contractimpl]\nimpl IdleContract {\n    pub fn init(env: Env) {\n        // Initializes instance storage without setting an extended TTL\n        env.storage().instance().set(&STATE_KEY, &123u32);\n    }\n\n    pub fn execute(env: Env) -> u32 {\n        env.storage().instance().get(&STATE_KEY).unwrap()\n    }\n}",
    "solutions": "1. **Restore Footprint via CLI/SDK:** Submit a restoration transaction (`soroban contract restore --id <CONTRACT_ID> --network testnet`) to revive the contract instance.\n2. **Implement Proactive TTL Bumping:** Call `env.storage().instance().extend_ttl(50_000, 100_000)` inside popular contract methods to ensure the instance never archives during regular use.\n3. **Automated Rent Monitor:** Integrate TrapTrace Storage TTL Auditor (`traptrace storage --contract <ID>`) into operational monitoring workflows.",
    "references": "- [Stellar Docs: Restoring Archived Contracts](https://developers.stellar.org/docs/learn/smart-contract-internals/state-archival#restoring-archived-data)\n- [Soroban Storage TTL Management Guide](https://developers.stellar.org/docs/data/rpc/api-reference/simulateTransaction)"
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
    "soroban_version": "21.0.0",
    "severity": "critical",
    "related_entries": [
      "scval-type-conversion-error",
      "host-invalid-action"
    ],
    "symptoms": "- Host aborts execution with `HostError(Error(Value, InvalidTag))` or `HostError(Error(Context, InvalidAction))`.\n- Diagnostic events indicate an invalid tag bitmask encountered during host object dereferencing.\n- Occurs when passing manually constructed raw byte payloads or corrupted XDR to host functions.",
    "root_causes": "1. **Manual Bit-Manipulation on `Val`:** Constructing raw 64-bit integer values and casting them directly into Soroban `Val` without following the host's bit tagging scheme (tag bits in the lower 8 bits).\n2. **Malformed XDR Envelopes:** Binary deserialization of corrupted or truncated transaction envelopes where the `ScValType` enum discriminator is out of bounds.\n3. **Cross-Protocol Version Incompatibility:** Passing a newer `ScVal` variant to a contract compiled against an older protocol version.",
    "reproduction_steps": "use soroban_sdk::{contract, contractimpl, Env, Val};\n\n#[contract]\npub struct BadTagContract;\n\n#[contractimpl]\nimpl BadTagContract {\n    pub fn trigger_bad_tag(_env: Env, raw_num: u64) -> Val {\n        // Unsafe fabrication of a tagged pointer with an illegal tag mask\n        unsafe { Val::from_payload(raw_num | 0xFF) }\n    }\n}",
    "solutions": "1. **Use Safe Soroban SDK Types:** Avoid `Val::from_payload` or raw unsafe pointers; rely on high-level SDK primitives (`Symbol`, `Address`, `Bytes`, `Map`, `Vec`).\n2. **Verify XDR Payloads:** Validate transaction envelope XDR with `traptrace decode <xdr>` before broadcasting.\n3. **Keep SDKs Synchronized:** Ensure contracts and client libraries are built against matching Soroban SDK versions.",
    "references": "- [Soroban Host Val & Object Architecture](https://github.com/stellar/rs-soroban-env/blob/main/soroban-env-common/src/val.rs)\n- [Stellar Developers: Data Types & SCVal](https://developers.stellar.org/docs/learn/smart-contract-internals/types)"
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
    "soroban_version": "21.0.0",
    "severity": "critical",
    "related_entries": [
      "vec-index-out-of-bounds",
      "option-unwrap-none",
      "storage-ledger-entry-not-found"
    ],
    "symptoms": "- Contract simulation reverts with `HostError(Error(Context, InvalidAction))` or `HostError(Error(Object, MissingKey))`.\n- Diagnostic events contain: `called Option::unwrap() on a None value` during Map retrieval.\n- User profile lookups, allowance lookups, or account registry lookups fail for unregistered users.",
    "root_causes": "1. **Unsafe `map.get(key).unwrap()`:** Assuming all possible queried keys exist in the Map collection.\n2. **Missing Key Initialization:** Reading an account balance or settings map before an account has been initialized.\n3. **Key Equality Mismatch:** Querying a Map with a subtly mismatched key type (e.g., mismatched Symbol casing or different address formatting).",
    "reproduction_steps": "use soroban_sdk::{contract, contractimpl, Address, Env, Map};\n\n#[contract]\npub struct MapKeyContract;\n\n#[contractimpl]\nimpl MapKeyContract {\n    pub fn get_balance(_env: Env, accounts: Map<Address, i128>, user: Address) -> i128 {\n        // Panics if user is not present in accounts map\n        accounts.get(user).unwrap()\n    }\n}",
    "solutions": "1. **Use `get()` with `unwrap_or` or Default:**\n   ```rust\n   let balance = accounts.get(user).unwrap_or(0);\n   ```\n2. **Return `Result<T, CustomError>`:**\n   ```rust\n   let balance = accounts.get(user).ok_or(CustomError::UserNotFound)?;\n   ```\n3. **Check `contains_key()` First:** Check `if !accounts.contains_key(user)` before processing dependent logic.",
    "references": "- [Soroban SDK Map Documentation](https://docs.rs/soroban-sdk/latest/soroban_sdk/struct.Map.html)\n- [Soroban Error Handling Best Practices](https://developers.stellar.org/docs/learn/smart-contract-internals/errors)"
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
    "soroban_version": "21.0.0",
    "severity": "critical",
    "related_entries": [
      "vec-index-out-of-bounds",
      "map-key-not-found",
      "unreachable-code-reached"
    ],
    "symptoms": "- Contract simulation halts immediately with `HostError(Error(Context, InvalidAction))` or `HostError(Error(WasmVm, UnreachableCodeReached))`.\n- Diagnostic events contain: `panicked at 'called Option::unwrap() on a None value'`.\n- Gas is consumed up to the point of panic and all state modifications are rolled back.",
    "root_causes": "1. **Direct `unwrap()` on Fallible Operations:** Using `.unwrap()` on storage reads, map lookups, vector element indexing, or math helpers.\n2. **Missing Input / Environment Guards:** Assuming optional parameters or ambient contract configurations are always populated.\n3. **Rust Standard Panic in WASM:** In `no_std` Soroban builds, any `panic!` invokes the WASM unreachable instruction, causing the host to trap.",
    "reproduction_steps": "use soroban_sdk::{contract, contractimpl, symbol_short, Env, Symbol};\n\nconst OWNER_KEY: Symbol = symbol_short!(\"owner\");\n\n#[contract]\npub struct UnwrapContract;\n\n#[contractimpl]\nimpl UnwrapContract {\n    pub fn get_owner(env: Env) -> Symbol {\n        // Panics if OWNER_KEY was not previously written to instance storage\n        env.storage().instance().get(&OWNER_KEY).unwrap()\n    }\n}",
    "solutions": "1. **Use `?` Operator with Custom Error Enums:**\n   ```rust\n   #[contracterror]\n   #[derive(Copy, Clone, Debug, Eq, PartialEq, PartialOrd, Ord)]\n   #[repr(u32)]\n   pub enum Error {\n       NotInitialized = 1,\n   }\n\n   pub fn get_owner(env: Env) -> Result<Symbol, Error> {\n       env.storage().instance().get(&OWNER_KEY).ok_or(Error::NotInitialized)\n   }\n   ```\n2. **Use `unwrap_or()` or `unwrap_or_else()`:** Provide safe fallback defaults for non-critical reads.\n3. **Use TrapTrace Linter:** Run `traptrace lint <file.rs>` to automatically detect unsafe `.unwrap()` patterns before compiling.",
    "references": "- [Soroban Custom Errors Guide](https://developers.stellar.org/docs/learn/smart-contract-internals/errors#custom-errors)\n- [Rust Error Handling Book](https://doc.rust-lang.org/book/ch09-02-recoverable-errors-with-result.html)"
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
    "soroban_version": "21.0.0",
    "severity": "critical",
    "related_entries": [
      "auth-invalid-signature",
      "simulate-tx-auth-failed"
    ],
    "symptoms": "- Transaction simulation or invocation terminates with `HostError(Error(Auth, InvalidAction))` or `HostError::AuthMissing`.\n- RPC simulation returns `Auth error: HostError::AuthMissing (require_auth failed for address)`.\n- Contract aborts during privileged administrative functions, token transfers, or state ownership modifications.",
    "root_causes": "1. **Unsigned Client Invocation:** Client submitted a transaction envelope that called a contract method enforcing `address.require_auth()` without appending the corresponding `SorobanAuthorizationEntry` to the transaction footprint.\n2. **Sub-Invocation Authorization Gaps:** Contract invoked a child contract requiring caller authorization without wrapping the call in `require_auth_for_args(...)`.\n3. **Mismatched Authorization Address:** Passing an address parameter `admin` to the method that does not match the actual transaction submitter or signed credentials.",
    "reproduction_steps": "use soroban_sdk::{contract, contractimpl, Address, Env};\n\n#[contract]\npub struct AdminOnlyContract;\n\n#[contractimpl]\nimpl AdminOnlyContract {\n    pub fn update_admin(env: Env, new_admin: Address) {\n        let current_admin: Address = env.storage().instance().get(&1u32).unwrap();\n        // Fails if current_admin has not signed the invocation\n        current_admin.require_auth();\n        env.storage().instance().set(&1u32, &new_admin);\n    }\n}",
    "solutions": "1. **Include Auth Entries:** In client applications using JS/Python/Rust SDKs, simulate the transaction first to generate the required `auth` tree and sign each required entry.\n2. **Authorizing Contract Calls:** If calling between contracts, use `Address::require_auth_for_args(&address, args)` to explicitly authorize arguments passed to nested contracts.\n3. **Inspect Auth Trees with CLI:** Run `traptrace simulate <xdr>` to inspect required authorizers and verify whether all needed signatures are included.",
    "references": "- [Stellar Developers: Soroban Authorization Architecture](https://developers.stellar.org/docs/learn/smart-contract-internals/authorization)\n- [Soroban Rust SDK Address::require_auth](https://docs.rs/soroban-sdk/latest/soroban_sdk/struct.Address.html#method.require_auth)"
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
    "soroban_version": "21.0.0",
    "severity": "warning",
    "related_entries": [
      "contract-data-size-exceeds-limit",
      "host-invalid-action"
    ],
    "symptoms": "- Contract simulation fails during storage write with `HostError(Error(Storage, KeySizeLimitExceeded))` or `HostError(Error(Context, InvalidAction))`.\n- Writing dynamic keys containing large byte buffers or concatenated strings causes transactions to abort immediately.\n- RPC simulation returns zero execution progress past the storage write instruction.",
    "root_causes": "1. **Embedding Payloads Inside Storage Keys:** Using arbitrary user-supplied data (such as IPFS hashes, large string IDs, or public keys combined with descriptions) directly as a storage key instead of computing a fixed-size hash.\n2. **Unbounded Key Structures:** Serializing complex structs or nested tuples into storage keys without enforcing fixed upper bounds.\n3. **Protocol Key Size Quota Violation:** Exceeding Soroban's strict protocol limits on `ScVal` key serialization length.",
    "reproduction_steps": "use soroban_sdk::{contract, contractimpl, Bytes, Env};\n\n#[contract]\npub struct HugeKeyContract;\n\n#[contractimpl]\nimpl HugeKeyContract {\n    pub fn write_oversized_key(env: Env, large_key_data: Bytes, value: u32) {\n        // Attempting to write a key larger than allowable ledger limits\n        env.storage().persistent().set(&large_key_data, &value);\n    }\n}",
    "solutions": "1. **Hash Dynamic Keys with SHA-256 / Keccak:** Hash variable-length keys using `env.crypto().sha256(&large_key_data)` to produce a deterministic 32-byte `BytesN<32>` key.\n2. **Use Enums / Symbols for Fixed Keys:** Use short symbols (`symbol_short!(\"admin\")`) or typed enums (`DataKey::Balance(Address)`) for predictable key sizes.\n3. **Validate Key Lengths:** Enforce strict input validation in contract arguments before executing storage calls.",
    "references": "- [Stellar Network Protocol Limits](https://developers.stellar.org/docs/learn/fundamentals/stellar-data-structures/operations-and-transactions)\n- [Soroban Crypto Host Functions](https://docs.rs/soroban-sdk/latest/soroban_sdk/struct.Crypto.html)"
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
    "soroban_version": "21.0.0",
    "severity": "warning",
    "related_entries": [
      "storage-key-missing",
      "entry-archived-ttl-expired"
    ],
    "symptoms": "- Contract invocation halts with `HostError(Error(Storage, MissingValue))` or `HostError::StorageNotFound`.\n- Diagnostic events indicate an unwrap on `None` following an `env.storage().instance().get(&key)` call.\n- Simulation trace shows contract failed during state initialization or state transition reads.",
    "root_causes": "1. **Unchecked Storage Unwrap:** Calling `.get(&key).unwrap()` on a storage key that has not yet been set or initialized on-chain.\n2. **Storage Key Type Mismatch:** Querying a key using a different type representation than the one used during write (e.g. `Symbol` vs `u32` or enum variant discriminant).\n3. **Storage Tier Confusion:** Storing data in `temporary` storage that has expired at a ledger boundary, or confusing `instance` vs `persistent` storage locations.\n4. **Deleted State Entries:** Attempting to retrieve a key that was explicitly removed via `env.storage().persistent().remove(&key)`.",
    "reproduction_steps": "use soroban_sdk::{contract, contractimpl, symbol_short, Env, Symbol};\n\nconst COUNTER: Symbol = symbol_short!(\"COUNTER\");\n\n#[contract]\npub struct StorageMissingContract;\n\n#[contractimpl]\nimpl StorageMissingContract {\n    pub fn get_counter_unsafe(env: Env) -> u32 {\n        // Direct unwrap without checking existence or providing a default\n        env.storage().instance().get(&COUNTER).unwrap()\n    }\n}",
    "solutions": "1. **Use `get_or` Pattern:** Always use `.get(&key).unwrap_or(default_value)` or `env.storage().instance().has(&key)` before accessing storage values.\n2. **Safe Option Handling:** Return `Option<T>` from read-only contract methods instead of panicking on uninitialized values.\n3. **Consistent Type Serialization:** Define a dedicated enum for storage keys (e.g. `#[contracttype] pub enum DataKey { Counter, Admin }`) to eliminate type mismatches across reads and writes.\n4. **Inspect State with CLI:** Run `traptrace storage --contract <CONTRACT_ID>` to verify which storage keys exist on-chain and their TTL status.",
    "references": "- [Stellar Developers: State Storage in Soroban](https://developers.stellar.org/docs/learn/smart-contract-internals/state-archival)\n- [Soroban Rust SDK Storage Documentation](https://docs.rs/soroban-sdk/latest/soroban_sdk/storage/index.html)"
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
    "soroban_version": "21.0.0",
    "severity": "info",
    "related_entries": [],
    "symptoms": "- Parent contract invocation aborts with `Error(Context, Failed)`.\n- RPC log indicates sub-invocation call stack unwound.",
    "root_causes": "1. **Child Contract Trapped:** Target child contract raised a host error or panic.\n2. **Mismatch Interface / Symbol:** Calling non-existent function name or passing wrong argument types across contract boundary.",
    "reproduction_steps": "let client = TargetContractClient::new(&env, &target_address);\n// Fails if target_address is invalid or function panics\nclient.execute_action(&param);",
    "solutions": "1. **Verify Target Address:** Check target contract existence on-chain.\n2. **Propagate or Handle Error:** Wrap sub-invocations carefully and inspect child contract logs.",
    "references": "- [Soroban Cross-Contract Calls Specification](https://developers.stellar.org/docs/build/smart-contracts/invoking-contracts)"
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
    "soroban_version": "21.0.0",
    "severity": "warning",
    "related_entries": [
      "sub-invocation-failed",
      "unreachable-code-reached"
    ],
    "symptoms": "- Transaction simulation or invocation terminates with `HostError(Error(Contract, 1))` (or other integer error code).\n- Top-level contract aborts even though its own logic has not panicked.\n- Diagnostic events list shows callee contract emitting error discriminant before aborting execution context.",
    "root_causes": "1. **Callee Business Logic Assertion:** The target child contract hit a business logic validation failure (e.g. `InsufficientBalance`, `UnauthorizedCaller`) and returned a custom `#[contracterror]` variant.\n2. **Unhandled `Result<T, E>` in Caller:** The invoking contract called a child contract method that returns `Result` but immediately used `.unwrap()` or the `?` operator without catching or mapping domain errors.\n3. **Invalid Invariant in Child Contract:** Callee state was corrupted or uninitialized, leading the callee to return an error variant.",
    "reproduction_steps": "use soroban_sdk::{contract, contracterror, contractimpl, Address, Env};\n\n#[contracterror]\n#[derive(Copy, Clone, Debug, Eq, PartialEq, PartialOrd, Ord)]\n#[repr(u32)]\npub enum VaultError {\n    VaultLocked = 1,\n    InsufficientFunds = 2,\n}\n\n#[contract]\npub struct VaultContract;\n\n#[contractimpl]\nimpl VaultContract {\n    pub fn withdraw(_env: Env, _amount: i128) -> Result<(), VaultError> {\n        // Explicitly return a user-defined contract error\n        Err(VaultError::VaultLocked)\n    }\n}",
    "solutions": "1. **Catch and Handle Errors in Caller:** Avoid unconditional `.unwrap()`; use pattern matching or `match callee_client.try_withdraw(&amount)` to handle child error variants gracefully.\n2. **Inspect Error Code Enum:** Look up the callee contract's `#[contracterror]` definition to map the integer discriminant (e.g. `1` $\\rightarrow$ `VaultLocked`).\n3. **Trace Invocations with CLI:** Run `traptrace inspect <tx_hash>` or `traptrace simulate <xdr>` to view the full cross-contract call tree and pinpoint which child contract emitted the error code.",
    "references": "- [Stellar Developers: Soroban Custom Errors and ContractError](https://developers.stellar.org/docs/learn/smart-contract-internals/errors)\n- [Soroban Rust SDK ContractError Attribute](https://docs.rs/soroban-sdk/latest/soroban_sdk/attr.contracterror.html)"
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
    "soroban_version": "21.0.0",
    "severity": "critical",
    "related_entries": [
      "entry-archived-ttl-expired",
      "storage-ledger-entry-not-found"
    ],
    "symptoms": "- Contract simulation fails with `HostError(Error(Storage, DeadEntry))` or `Error(Storage, MissingValue)`.\n- Temporary state keys (nonces, short-lived signatures, session authorizations) cannot be read after a ledger threshold.\n- Unlike Persistent storage entries, calling `extend_ttl` or restoration transactions fails because temporary entries are permanently deleted upon TTL expiration.",
    "root_causes": "1. **Failure to Bump Temporary TTL:** Temporary storage entries (`env.storage().temporary()`) were created with a short initial TTL (e.g., 16 ledgers) and never renewed using `env.storage().temporary().extend_ttl(...)`.\n2. **Permanent Deletion Model:** Soroban state archival (CAP-0046) treats temporary entries as ephemeral; once expired, they cannot be restored via `RestoreFootprintOp`.\n3. **Misclassifying Persistent State as Temporary:** Storing critical protocol state (user balances, pool reserves) in temporary storage rather than persistent or instance storage.",
    "reproduction_steps": "use soroban_sdk::{contract, contractimpl, symbol_short, Env, Symbol};\n\nconst TEMP_KEY: Symbol = symbol_short!(\"session\");\n\n#[contract]\npub struct TempStorageContract;\n\n#[contractimpl]\nimpl TempStorageContract {\n    pub fn init_session(env: Env, user_id: u32) {\n        // Stored in temporary storage without TTL extension\n        env.storage().temporary().set(&TEMP_KEY, &user_id);\n    }\n\n    pub fn get_session(env: Env) -> u32 {\n        // Fails with Storage DeadEntry if called after temporary TTL expires\n        env.storage().temporary().get(&TEMP_KEY).unwrap()\n    }\n}",
    "solutions": "1. **Extend Temporary TTL on Read/Write:** Call `env.storage().temporary().extend_ttl(&TEMP_KEY, threshold, extend_to)` whenever accessing active sessions.\n2. **Use Persistent Storage for State:** Use `env.storage().persistent()` for ledger data that may need to be restored if archived.\n3. **Use Instance Storage for Shared Protocol State:** Store contract admin and configuration data in `env.storage().instance()`.",
    "references": "- [Stellar Docs: State Archival & Storage Types](https://developers.stellar.org/docs/learn/smart-contract-internals/state-archival)\n- [CAP-0046: Soroban State Archival](https://github.com/stellar/stellar-protocol/blob/master/core/cap-0046.md)"
  },
  {
    "id": "unauthorized-storage-access",
    "title": "Host Error - Unauthorized Contract Storage Footprint Access",
    "category": "host-error",
    "error_code": "HostError::StorageAccessUnauthorized",
    "verified": True,
    "summary": "Contract execution attempted to access storage ledger keys outside its allocated ledger footprint or across contract security boundaries.",
    "tags": [
      "host-error",
      "storage",
      "footprint",
      "security",
      "permissions"
    ],
    "soroban_version": "21.0.0",
    "severity": "critical",
    "related_entries": [
      "storage-ledger-entry-not-found",
      "storage-key-missing"
    ],
    "symptoms": "- Transactions fail during on-chain execution with `StorageAccessUnauthorized` or `FootprintMismatch`.\n- Simulation succeeds on local mock environment but fails when submitted to live network RPC.\n- Multi-contract transaction envelopes reject execution before state mutations take effect.",
    "root_causes": "1. **Cross-Contract Storage Boundary Violation:** Attempting to directly inspect or mutate another contract instance's private storage keys without going through its exported public methods.\n2. **Missing Ledger Footprint in Transaction Envelope:** The transaction envelope omitted read-only or read-write footprint keys required by nested sub-invocations.\n3. **Dynamic Key Resolution Drift:** The contract dynamically computed a storage key at runtime that was not present in the pre-flight simulated footprint.",
    "reproduction_steps": "use soroban_sdk::{contract, contractimpl, symbol_short, Env, Symbol};\n\n#[contract]\npub struct UnauthorizedStorageContract;\n\n#[contractimpl]\nimpl UnauthorizedStorageContract {\n    pub fn access_foreign_storage(env: Env) {\n        let key = symbol_short!(\"FOREIGN\");\n        let _val: u32 = env.storage().instance().get(&key).unwrap();\n    }\n}",
    "solutions": "1. **Access Foreign State via Public Methods:** Always query foreign contract data through its exported getter interface:\n   ```rust\n   let target_client = TargetContractClient::new(&env, &target_address);\n   let value = target_client.get_value();\n   ```\n2. **Pre-flight Footprint Synchronization:** Always generate transaction footprints via `simulateTransaction` and attach the exact returned footprint to the signed transaction envelope.\n3. **Inspect Contract Ledger Entries:** Use `traptrace storage --contract <id>` or the Web Studio Storage Auditor to verify valid storage ownership.",
    "references": "- [Stellar RPC simulateTransaction Footprint Specs](https://developers.stellar.org/docs/data/rpc/api-reference/methods/simulateTransaction)\n- [Soroban Storage Isolation Architecture](https://developers.stellar.org/docs/learn/smart-contract-internals/state-archival)"
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
    "soroban_version": "21.0.0",
    "severity": "info",
    "related_entries": [],
    "symptoms": "- Call fails with `HostError(Error(WasmVm, Unexpected))`.\n- Terminal log reports `VM trapped: unreachable code executed`.\n- Contract panics abruptly during call.",
    "root_causes": "1. **Unwrap on None/Err:** Calling `.unwrap()` or `.expect()` on an Option/Result that returned `None` or `Err`.\n2. **Out of Bounds Indexing:** Accessing vector or array elements at invalid indexes (`vec[index]`).\n3. **Integer Division by Zero:** Performing `a / b` when `b == 0`.",
    "reproduction_steps": "pub fn divide(env: Env, a: u64, b: u64) -> u64 {\n    // Triggers unreachable code panic when b == 0\n    a / b\n}",
    "solutions": "1. **Use Checked Operations & Match:** Avoid `.unwrap()`. Return `Result<T, ContractError>` instead.\n2. **Safe Math & Boundary Checks:** Validate inputs before indexing or performing division.\n\n```rust\npub fn safe_divide(env: Env, a: u64, b: u64) -> Result<u64, Error> {\n    if b == 0 {\n        return Err(Error::from_contract_error(1));\n    }\n    Ok(a / b)\n}\n```",
    "references": "- [Soroban Error Handling Best Practices](https://developers.stellar.org/docs/build/smart-contracts/getting-started/errors)"
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
    "soroban_version": "21.0.0",
    "severity": "critical",
    "related_entries": [
      "map-key-not-found",
      "option-unwrap-none",
      "unreachable-code-reached"
    ],
    "symptoms": "- Contract simulation reverts abruptly with `HostError(Error(Context, InvalidAction))` or `HostError(Error(Object, IndexOutOfBounds))`.\n- Diagnostic events contain a panic message: `index out of bounds: the len is X but the index is Y`.\n- Multi-recipient payouts or batch array iterations crash mid-execution.",
    "root_causes": "1. **Unchecked Direct Indexing:** Calling `vec.get(index).unwrap()` or `vec.get_unchecked(index)` where `index >= vec.len()`.\n2. **Off-by-One Loop Iteration:** Using `<=` instead of `<` in numeric iteration loops over vector lengths.\n3. **Empty Collection Assumptions:** Assuming a contract state vector or user input list has at least one element without guarding `if vec.is_empty()`.",
    "reproduction_steps": "use soroban_sdk::{contract, contractimpl, vec, Env, Vec};\n\n#[contract]\npub struct VecBoundsContract;\n\n#[contractimpl]\nimpl VecBoundsContract {\n    pub fn get_element(env: Env, index: u32) -> u32 {\n        let items: Vec<u32> = vec![&env, 10, 20, 30];\n        // Panics if index >= 3\n        items.get(index).unwrap()\n    }\n}",
    "solutions": "1. **Use `get()` and Match/Handle `None`:** Instead of unwrapping, handle `None` gracefully:\n   ```rust\n   match items.get(index) {\n       Some(val) => Ok(val),\n       None => Err(Error::ItemNotFound),\n   }\n   ```\n2. **Validate Input Index:** Check `if index >= items.len() { return Err(Error::OutOfBounds); }`.\n3. **Use Iterators:** Iterate elements directly with `for item in items.iter()` to eliminate manual indexing errors.",
    "references": "- [Soroban SDK Vec Documentation](https://docs.rs/soroban-sdk/latest/soroban_sdk/struct.Vec.html)\n- [Rust Array and Vector Bounds Checking](https://doc.rust-lang.org/book/ch08-01-vectors.html)"
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
    "soroban_version": "21.0.0",
    "severity": "critical",
    "related_entries": [
      "budget-exceeded",
      "unreachable-code-reached"
    ],
    "symptoms": "- Transaction simulation or invocation terminates with `HostError(Error(Budget, Exceeded))` or `HostError::MemoryExhausted`.\n- CLI output indicates out-of-memory (OOM) or memory page allocation failure (`grow_memory` returned -1).\n- Execution halts when constructing large vectors, allocating deep recursive stack frames, or decompressing large data in WASM.",
    "root_causes": "1. **Large Transient Heap Allocations:** Instantiating massive Rust `std::vec::Vec` or `String` buffers inside contract WASM heap rather than host-managed collections.\n2. **Deep Recursive Call Stacks:** Unbounded recursion consuming WASM shadow stack and memory pages.\n3. **In-Memory Sorting of Large Datasets:** Buffering thousands of objects in memory for sorting or aggregation instead of processing via batched iterations.\n4. **Memory Leaks in Custom Allocators:** Failure to free or reuse memory across high-iteration processing loops inside WASM.",
    "reproduction_steps": "use soroban_sdk::{contract, contractimpl, Env};\n\n#[contract]\npub struct MemoryExhaustedContract;\n\n#[contractimpl]\nimpl MemoryExhaustedContract {\n    pub fn allocate_huge_memory(_env: Env) {\n        // Attempt to allocate a 100MB transient buffer in WASM heap\n        let mut huge_vec: Vec<u8> = Vec::with_capacity(100 * 1024 * 1024);\n        huge_vec.resize(100 * 1024 * 1024, 0xEE);\n    }\n}",
    "solutions": "1. **Use Host Collections:** Replace `std::vec::Vec` and `std::collections::BTreeMap` with Soroban SDK host-managed types (`soroban_sdk::Vec`, `soroban_sdk::Map`), which reside in host memory and do not consume WASM linear heap.\n2. **Stream and Batch Processing:** Process records sequentially in stream-style chunks rather than buffering the complete dataset in memory.\n3. **Avoid Unbounded Recursion:** Convert recursive algorithms to iterative state loops with bounded iteration caps.\n4. **Pre-Flight Memory Profiling:** Run `traptrace simulate <xdr>` to inspect the `mem_bytes` consumption gauge before on-chain submission.",
    "references": "- [Stellar Developers: Soroban Memory and Metering Limits](https://developers.stellar.org/docs/learn/fundamentals/fees-and-metering)\n- [WebAssembly Linear Memory Specification](https://webassembly.github.io/spec/core/syntax/modules.html#memories)"
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
    "soroban_version": "21.0.0",
    "severity": "info",
    "related_entries": [],
    "symptoms": "- RPC returns error JSON `{\"code\": -32600, \"message\": \"Simulation failed: Auth error\"}`.\n- Invocation client output: `Failed to construct Soroban auth tree`.",
    "root_causes": "1. **Invalid Signature/Key:** Signer key does not match required `require_auth` address.\n2. **Missing Footprint Scope:** Auth payload missing child sub-invocations.",
    "reproduction_steps": "curl -s -X POST https://soroban-testnet.stellar.org \\\n  -H \"Content-Type: application/json\" \\\n  -d '{\n    \"jsonrpc\": \"2.0\",\n    \"id\": 1,\n    \"method\": \"simulateTransaction\",\n    \"params\": {\n      \"transaction\": \"<UNSIGNED_TRANSACTION_XDR>\"\n    }\n  }'",
    "solutions": "1. **Sign with Correct Key:** Ensure signature matches target address payload.\n2. **Re-simulate Auth Tree:** Use JS SDK `assembleTransaction` to compute full auth requirements automatically.",
    "references": "- [Soroban Auth Framework Overview](https://developers.stellar.org/docs/build/smart-contracts/authorization)"
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
    "soroban_version": "21.0.0",
    "severity": "info",
    "related_entries": [],
    "symptoms": "- `getLedgerEntries` response returns `entries: []`.\n- SDK throws `NotFoundError` when fetching contract data instance.",
    "root_causes": "1. **Uninitialized Storage:** Storage key was never written to on-chain.\n2. **Archived Key:** Key expired and was moved to archived ledger state.",
    "reproduction_steps": "curl -s -X POST https://soroban-testnet.stellar.org \\\n  -H \"Content-Type: application/json\" \\\n  -d '{\n    \"jsonrpc\": \"2.0\",\n    \"id\": 1,\n    \"method\": \"getLedgerEntries\",\n    \"params\": {\n      \"keys\": [\n        \"AAAAFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAAAAEAAAAEdGVzdAAAAAA=\"\n      ]\n    }\n  }'",
    "solutions": "1. **Initialize State:** Execute contract setup/init function first.\n2. **Check Archival Status:** Query state archival RPC endpoint to verify if restoration is required.",
    "references": "- [Stellar RPC API Specification: getLedgerEntries](https://developers.stellar.org/docs/data/rpc/api-reference/methods/getLedgerEntries)"
  },
  {
    "id": "tx-simulation-fee-insufficient",
    "title": "RPC Error - Insufficient Inclusion / Resource Fee for Transaction Submission",
    "category": "rpc-error",
    "error_code": "RPC::InsufficientInclusionFee",
    "verified": True,
    "summary": "Transaction envelope rejected by RPC node or Horizon because the specified base inclusion fee or resource fee is below current ledger surge requirements.",
    "tags": [
      "rpc-error",
      "fees",
      "inclusion-fee",
      "gas",
      "mempool"
    ],
    "soroban_version": "21.0.0",
    "severity": "warning",
    "related_entries": [
      "budget-exceeded",
      "tx-failed-bad-seq"
    ],
    "symptoms": "- `sendTransaction` RPC requests fail immediately with `txINSUFFICIENT_FEE` or `RESOURCE_LIMIT_EXCEEDED`.\n- Transactions stall in mempool during high network congestion or surge pricing.\n- Automated bots and relayer transactions fail with fee rejection errors.",
    "root_causes": "1. **Fee Below Network Base Reserve:** Specifying a `base_fee` lower than 100 stroops per operation (the Stellar protocol minimum).\n2. **Surge Pricing Spike:** During network traffic surges, the minimum inclusion fee escalates beyond the pre-set max fee in the transaction envelope.\n3. **Outdated `minResourceFee`:** Constructing the transaction using simulation data from a prior ledger without refreshing fee estimates.",
    "reproduction_steps": "curl -X POST \"https://soroban-testnet.stellar.org\" \\\n     -H \"Content-Type: application/json\" \\\n     -d '{\n       \"jsonrpc\": \"2.0\",\n       \"id\": 1,\n       \"method\": \"sendTransaction\",\n       \"params\": {\n         \"transaction\": \"AAAAAgAAAADpGsHrCHdI94ecdQ+kCJAORLt2V2oLk6H+/7asPt1kfAAAAAX/oAftBAjljQELlFpDYo3t97YZ45Kf3Uq7ihnBVVVYzAAAADwAAAAdmbl9jYWxsAAAAAA0AAAAg\"\n       }\n     }'",
    "solutions": "1. **Dynamic Fee Estimation via `getFeeStats`:** Query the current network fee stats before envelope assembly:\n   ```typescript\n   const feeStats = await server.getFeeStats();\n   const recommendedFee = feeStats.fee_charged.mode;\n   ```\n2. **Add Surge Buffer to `minResourceFee`:** Add a 15\u201320% buffer to the `minResourceFee` returned by `simulateTransaction`:\n   ```typescript\n   const bufferedFee = Math.ceil(simResult.minResourceFee * 1.20);\n   ```\n3. **Use TrapTrace Gas Profiler:** Use `traptrace profile <xdr>` or the Web Studio Gas Profiler to inspect required resource fees in advance.",
    "references": "- [Stellar RPC Documentation: sendTransaction](https://developers.stellar.org/docs/data/rpc/api-reference/methods/sendTransaction)\n- [Stellar Protocol 21 Surge Pricing & Fee Mechanics](https://developers.stellar.org/docs/learn/fundamentals/fees-metering)"
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
    "soroban_version": "21.0.0",
    "severity": "warning",
    "related_entries": [
      "value-conversion-failed",
      "invalid-scval-tag"
    ],
    "symptoms": "- Contract invocations panic with `ConversionError` when deserializing function arguments or returned values.\n- Client SDKs (JS/TS, Python) fail with `Invalid ScVal discriminator` or `Cannot convert ScVal to BigInt`.\n- Contract tests fail with `TryFromVal failed for target type`.",
    "root_causes": "1. **Integer Size Mismatches:** Passing an `i32` or `u32` into a function argument typed as `i128` or `u64` without explicit type coercion.\n2. **Invalid Symbol Character Encoding:** Constructing `Symbol` or `symbol_short!` with characters outside the allowed alphanumeric + underscore set or exceeding length limits.\n3. **Mismatched Struct Shape:** Contract ABI expected a tuple/struct with specific field keys, but the client passed a generic vector or mismatched map.",
    "reproduction_steps": "use soroban_sdk::{contract, contractimpl, symbol_short, Env, Symbol};\n\n#[contract]\npub struct ConversionContract;\n\n#[contractimpl]\nimpl ConversionContract {\n    pub fn process_amount(_env: Env, amount: i128) -> i128 {\n        amount\n    }\n}",
    "solutions": "1. **Use Explicit ScVal Type Constructors:** Construct arguments explicitly in SDKs (`nativeToScVal(100n, { type: 'i128' })`).\n2. **Use `TryFromVal` for Safe Conversion:** In Rust contracts, convert dynamic values using `.try_into_val(&env)` and handle conversion errors explicitly.\n3. **Inspect Contract ABI:** Use `traptrace abi <contract_id>` or the Web Studio WASM ABI tab to verify exact function signature types before calling.",
    "references": "- [Soroban Types & Conversions](https://developers.stellar.org/docs/learn/smart-contract-internals/types)\n- [Stellar SDK ScVal Serialization](https://stellar.github.io/js-stellar-sdk/)"
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
    "soroban_version": "21.0.0",
    "severity": "info",
    "related_entries": [],
    "symptoms": "- SDK throws `TypeError: Cannot convert ScVal to native type`.\n- Panic in Rust client: `called Result::unwrap() on an Err value: ConversionError`.",
    "root_causes": "1. **Type Mismatch:** Attempting to decode `ScVal::Symbol` as `ScVal::I128` or `ScVal::Address`.\n2. **Schema Drift:** SDK client bindings out of sync with contract Wasm interface schema.",
    "reproduction_steps": "Pass a string argument in JS SDK to a contract function parameter expecting `i128`.",
    "solutions": "1. **Use Type-Safe Binding Generator:** Generate client bindings using `soroban contract bindings typescript`.\n2. **Explicit Conversion Helpers:** Use `scValToNative()` and `nativeToScVal()` helpers with proper type casting.",
    "references": "- [Stellar Soroban JS SDK Documentation](https://stellar.github.io/js-soroban-client/)"
  }
]

def load_entries(custom_dir=None):
    if custom_dir and os.path.exists(custom_dir):
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
