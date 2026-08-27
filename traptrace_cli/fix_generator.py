"""
Remediation Code Snippet & Auto-Fix Generator for TrapTrace CLI.
Generates idiomatic Rust and Soroban SDK remediation code blocks, best practice templates,
and compiler flags for catalog errors.
"""

from typing import Dict, Any, Optional
from traptrace_cli.tui import (
    BOLD, RESET, DIM, TEAL, CYAN, RED, GREEN, YELLOW, WHITE,
    render_box
)

# Registry of curated Rust remediation code blocks for Soroban error patterns
REMEDIATION_SNIPPETS: Dict[str, Dict[str, str]] = {
    "arith-error": {
        "title": "Checked Arithmetic & Zero-Division Guards",
        "description": "Replace raw unchecked arithmetic operators (+, -, *, /) with checked host arithmetic.",
        "bad_code": """// ❌ BUGGY: Raw arithmetic triggers WASM unreachable trap on overflow
pub fn calculate_reward(env: Env, base: u64, multiplier: u64) -> u64 {
    base * multiplier + 100 // Overflow panic if product > u64::MAX
}""",
        "fix_code": """// ✅ REMEDIATED: Use checked arithmetic with custom contract error enum
#[contracterror]
#[derive(Copy, Clone, Debug, Eq, PartialEq, PartialOrd, Ord)]
pub enum Error {
    ArithmeticOverflow = 1,
    DivisionByZero = 2,
}

pub fn calculate_reward(env: Env, base: u64, multiplier: u64) -> Result<u64, Error> {
    let product = base.checked_mul(multiplier).ok_or(Error::ArithmeticOverflow)?;
    let total = product.checked_add(100).ok_or(Error::ArithmeticOverflow)?;
    Ok(total)
}"""
    },
    "require-auth-missing": {
        "title": "Explicit Caller Authorization & Scoped Args",
        "description": "Ensure the required Address signs the invocation or scope authorization to arguments.",
        "bad_code": """// ❌ BUGGY: Missing require_auth allows any unauthenticated caller to transfer funds
pub fn withdraw(env: Env, owner: Address, amount: i128) {
    // Missing owner.require_auth()
    transfer_internal(&env, &owner, amount);
}""",
        "fix_code": """// ✅ REMEDIATED: Enforce explicit authentication before performing state mutations
pub fn withdraw(env: Env, owner: Address, amount: i128) {
    // Verifies that the owner signed this transaction
    owner.require_auth();
    
    // For specialized sub-calls, scope auth to specific parameters:
    // owner.require_auth_for_args((&owner, amount).into_val(&env));
    
    transfer_internal(&env, &owner, amount);
}"""
    },
    "auth-invalid-signature": {
        "title": "Custom Account Interface & Signature Verification",
        "description": "Implement standard Soroban CustomAccountInterface for custom multisig or smart wallets.",
        "bad_code": """// ❌ BUGGY: Manually verifying uncanonicalized signatures in business logic
pub fn execute_multisig(env: Env, pubkey: BytesN<32>, sig: BytesN<64>, msg: Bytes) {
    env.crypto().ed25519_verify(&pubkey, &msg, &sig);
}""",
        "fix_code": """// ✅ REMEDIATED: Implement standard Soroban __check_auth entrypoint
use soroban_sdk::auth::{Context, CustomAccountInterface};

#[contractimpl]
impl CustomAccountInterface for SmartWalletContract {
    type Error = Error;
    type Signature = SignaturePayload;

    fn __check_auth(
        env: Env,
        signature_payload: Self::Signature,
        auth_context: Context,
        auth_contexts: Vec<Context>,
    ) -> Result<(), Error> {
        // Authenticate against wallet signer thresholds
        verify_signatures(&env, &signature_payload, &auth_context)?;
        Ok(())
    }
}"""
    },
    "entry-archived-ttl-expired": {
        "title": "Storage State TTL Auto-Extension",
        "description": "Extend instance and persistent storage TTL to prevent ledger entry archival.",
        "bad_code": """// ❌ BUGGY: Storing contract state without TTL maintenance causes state expiration
pub fn store_config(env: Env, config: Config) {
    env.storage().instance().set(&DataKey::Config, &config);
}""",
        "fix_code": """// ✅ REMEDIATED: Automatically extend state TTL during contract interaction
const MIN_TTL_LEDGERS: u32 = 17280;   // ~1 day (5s ledgers)
const EXTEND_TTL_LEDGERS: u32 = 518400; // ~30 days

pub fn store_config(env: Env, config: Config) {
    env.storage().instance().set(&DataKey::Config, &config);
    
    // Extend contract instance & code TTL
    env.storage().instance().extend_ttl(MIN_TTL_LEDGERS, EXTEND_TTL_LEDGERS);
}"""
    },
    "contract-data-size-exceeds-limit": {
        "title": "Storage Chunking & Sharded Keys",
        "description": "Shard large collections or blobs across multiple keys to stay below the 64KB entry limit.",
        "bad_code": """// ❌ BUGGY: Appending unbounded list into a single persistent storage key
pub fn add_log(env: Env, log: String) {
    let mut logs: Vec<String> = env.storage().persistent().get(&DataKey::Logs).unwrap_or(Vec::new(&env));
    logs.push_back(log); // Eventually exceeds 64 KB storage entry limit!
    env.storage().persistent().set(&DataKey::Logs, &logs);
}""",
        "fix_code": """// ✅ REMEDIATED: Shard items across numbered indexed keys (paginated)
#[contracttype]
pub enum DataKey {
    LogCount,
    LogIndex(u32),
}

pub fn add_log(env: Env, log: String) {
    let count: u32 = env.storage().persistent().get(&DataKey::LogCount).unwrap_or(0);
    env.storage().persistent().set(&DataKey::LogIndex(count), &log);
    env.storage().persistent().set(&DataKey::LogCount, &(count + 1));
}"""
    },
    "wasm-memory-exhausted": {
        "title": "Use Host-Managed Collections (soroban_sdk::Vec)",
        "description": "Avoid allocating heavy heap objects in Rust memory; utilize host-managed collections.",
        "bad_code": """// ❌ BUGGY: Allocating large std/alloc collections in WASM linear memory
extern crate alloc;
use alloc::vec::Vec as StdVec;

pub fn process_data(env: Env) {
    let mut heap_buf: StdVec<u8> = StdVec::with_capacity(5_000_000); // Exceeds WASM memory limit
}""",
        "fix_code": """// ✅ REMEDIATED: Use Soroban SDK host-managed collections that live outside WASM memory
use soroban_sdk::{Bytes, Env, Vec};

pub fn process_data(env: Env) {
    // Host collections are stored in host memory and bypass WASM linear memory page limits
    let mut host_vec: Vec<u64> = Vec::new(&env);
    host_vec.push_back(100);
}"""
    },
    "sub-invocation-user-error": {
        "title": "Defensive Cross-Contract Invocation & Error Catching",
        "description": "Catch and handle sub-invocation contract error returns with try_invoke.",
        "bad_code": """// ❌ BUGGY: Unchecked contract client invocation panics parent transaction
pub fn call_external(env: Env, callee_id: Address) {
    let client = ExternalContractClient::new(&env, &callee_id);
    client.do_action(); // Reverts entire tx if callee returns error
}""",
        "fix_code": """// ✅ REMEDIATED: Use try_invoke to gracefully handle callee errors
pub fn call_external(env: Env, callee_id: Address) -> Result<bool, Error> {
    let client = ExternalContractClient::new(&env, &callee_id);
    match client.try_do_action() {
        Ok(Ok(val)) => Ok(val),
        Ok(Err(callee_err)) => {
            // Handle expected contract error
            Err(Error::ExternalContractFailed)
        },
        Err(host_err) => {
            // Handle host panic / trap
            Err(Error::HostInvocationFailed)
        }
    }
}"""
    },
    "wasm-verification-failed": {
        "title": "Soroban Standard #![no_std] Build Configuration",
        "description": "Ensure contracts compile with #![no_std] and target wasm32-unknown-unknown with optimization.",
        "bad_code": """// ❌ BUGGY: Including standard library features in contract root
// Cargo.toml missing release optimization flags
use std::time::SystemTime; // Unsupported syscalls in WASM VM""",
        "fix_code": """// ✅ REMEDIATED: Pure #![no_std] contract configuration
#![no_std]
use soroban_sdk::{contract, contractimpl, Env, Symbol};

// Build command:
// stellar contract build --package my-contract
// stellar contract optimize --wasm target/wasm32-unknown-unknown/release/my_contract.wasm"""
    },
    "crypto-verification-failed": {
        "title": "Canonical Cryptographic Signature Buffers",
        "description": "Pass fixed-size 32-byte public keys and 64-byte signatures with canonical hashing.",
        "bad_code": """// ❌ BUGGY: Unchecked byte lengths passed to cryptographic host primitives
pub fn verify(env: Env, key_bytes: Bytes, sig_bytes: Bytes, msg: Bytes) {
    // Panics if key_bytes is not exactly 32 bytes or sig_bytes not 64 bytes
}""",
        "fix_code": """// ✅ REMEDIATED: Enforce exact BytesN lengths in function signatures
pub fn verify(env: Env, key: BytesN<32>, sig: BytesN<64>, msg: Bytes) -> bool {
    // Verified by type system before calling host primitive
    env.crypto().ed25519_verify(&key, &msg, &sig);
    true
}"""
    },
    "unreachable-code-reached": {
        "title": "Replace unwrap() and panic!() with Result<T, E>",
        "description": "Avoid unwrap() and panic!() inside contract functions; return explicit contract error enums.",
        "bad_code": """// ❌ BUGGY: unwrap() panics with WASM unreachable on None
pub fn get_balance(env: Env, user: Address) -> i128 {
    env.storage().persistent().get(&user).unwrap() // PANIC if user not registered
}""",
        "fix_code": """// ✅ REMEDIATED: Return Result with explicit error enum
#[contracterror]
#[derive(Copy, Clone, Debug, Eq, PartialEq)]
pub enum Error {
    UserNotFound = 101,
}

pub fn get_balance(env: Env, user: Address) -> Result<i128, Error> {
    env.storage().persistent().get(&user).ok_or(Error::UserNotFound)
}"""
    },
    "instance-already-initialized": {
        "title": "Idempotent Initialization & Constructor Pattern",
        "description": "Prevent re-initialization panics by guarding constructor logic with storage state flags.",
        "bad_code": """// ❌ BUGGY: Calling initialize again overwrites admin without checks
pub fn initialize(env: Env, admin: Address) {
    env.storage().instance().set(&symbol_short!("ADMIN"), &admin);
}""",
        "fix_code": """// ✅ REMEDIATED: Guard initialization with storage flag or native constructor
pub fn initialize(env: Env, admin: Address) -> Result<(), Error> {
    if env.storage().instance().has(&symbol_short!("ADMIN")) {
        return Err(Error::AlreadyInitialized);
    }
    env.storage().instance().set(&symbol_short!("ADMIN"), &admin);
    Ok(())
}"""
    },
    "cross-contract-reentrancy-blocked": {
        "title": "Checks-Effects-Interactions Security Pattern",
        "description": "Update internal state before calling external contract interfaces to eliminate reentrancy traps.",
        "bad_code": """// ❌ BUGGY: External invocation happens before state balance update
pub fn withdraw(env: Env, recipient: Address, amount: i128) {
    token_client.transfer(&env.current_contract_address(), &recipient, &amount);
    let bal = env.storage().persistent().get(&recipient).unwrap_or(0);
    env.storage().persistent().set(&recipient, &(bal - amount));
}""",
        "fix_code": """// ✅ REMEDIATED: State is updated before external dispatch
pub fn withdraw(env: Env, recipient: Address, amount: i128) -> Result<(), Error> {
    recipient.require_auth();
    let bal = env.storage().persistent().get(&recipient).unwrap_or(0);
    let new_bal = bal.checked_sub(amount).ok_or(Error::InsufficientBalance)?;
    env.storage().persistent().set(&recipient, &new_bal);
    
    token_client.transfer(&env.current_contract_address(), &recipient, &amount);
    Ok(())
}"""
    },
    "unauthorized-storage-access": {
        "title": "Cross-Contract State Isolation & Public Interface",
        "description": "Access state across contract boundaries via exported client getters.",
        "bad_code": """// ❌ BUGGY: Accessing foreign storage key directly without interface
let val = env.storage().instance().get(&foreign_key).unwrap();""",
        "fix_code": """// ✅ REMEDIATED: Query target contract via generated client getter
let foreign_client = ForeignContractClient::new(&env, &foreign_contract_address);
let val = foreign_client.get_state_value();"""
    },
    "crypto-curve25519-invalid-scalar": {
        "title": "Canonical Key Encoding & Subgroup Validation",
        "description": "Validate public key bytes and verify modulo subgroup range before host crypto calls.",
        "bad_code": """// ❌ BUGGY: Passing unvalidated raw slice directly to host crypto
env.crypto().ed25519_verify(&raw_bytes, &msg, &sig);""",
        "fix_code": """// ✅ REMEDIATED: Ensure 32-byte canonical representation
let canonical_key: BytesN<32> = raw_bytes.try_into().map_err(|_| Error::InvalidKeyLength)?;
env.crypto().ed25519_verify(&canonical_key, &msg, &sig);"""
    },
    "tx-simulation-fee-insufficient": {
        "title": "Dynamic Fee Estimation with Surge Buffer",
        "description": "Estimate inclusion fees dynamically and add safety buffer against network congestion.",
        "bad_code": """// ❌ BUGGY: Hardcoded static base fee
const fee = 100;""",
        "fix_code": """// ✅ REMEDIATED: Dynamic fee with 20% surge pricing buffer
const feeStats = await rpc.getFeeStats();
const baseFee = feeStats.fee_charged.mode || 100;
const inclusionFee = Math.ceil(baseFee * 1.20);"""
    },
    "contract-spec-missing": {
        "title": "Preserve Soroban Custom Metadata Sections",
        "description": "Build with stellar CLI and retain .soroban_spec section during optimization.",
        "bad_code": """# ❌ BUGGY: Strips custom metadata section required by SDKs
wasm-opt -Oz --strip-all target.wasm -o stripped.wasm""",
        "fix_code": """# ✅ REMEDIATED: Strip debug symbols only or use stellar build
stellar contract build
# or: wasm-opt -Oz --strip-debug target.wasm -o optimized.wasm"""
    }
}

class FixGenerator:
    """Remediation generator for Soroban smart contract error patterns."""

    def get_fix(self, error_id: str) -> Optional[Dict[str, str]]:
        """Retrieve remediation code snippet for a given error ID."""
        clean_id = error_id.strip().lower()
        return REMEDIATION_SNIPPETS.get(clean_id)

    def generate_all(self) -> Dict[str, Dict[str, str]]:
        """Return all available remediation snippets."""
        return REMEDIATION_SNIPPETS

def render_fix_terminal(error_id: str, fix_data: Dict[str, str]) -> str:
    """Render terminal colored remediation code blocks."""
    lines = [
        f"\n{TEAL}{BOLD}⚡ TrapTrace Auto-Fix Generator — {fix_data.get('title')}{RESET}\n",
        f"  • Catalog Error ID: {CYAN}{error_id}{RESET}",
        f"  • Description:      {fix_data.get('description')}\n",
        f"{RED}{BOLD}--- Before (Buggy / Risky Pattern) ---{RESET}",
        f"{DIM}{fix_data.get('bad_code')}{RESET}\n",
        f"{GREEN}{BOLD}+++ After (Remediated Rust Soroban Best Practice) +++{RESET}",
        f"{CYAN}{fix_data.get('fix_code')}{RESET}\n"
    ]
    return "\n".join(lines)
