"""
TrapTrace Rust Soroban Test Generator.
Generates executable #[test] Rust unit test fixtures to reproduce, test, and prevent specific Soroban contract errors.
"""

from typing import Optional, Dict

TEST_TEMPLATES: Dict[str, Dict[str, str]] = {
    "arith-error": {
        "title": "Test for Arithmetic Overflow Panic Prevention",
        "code": """#[test]
#[should_panic(expected = "attempt to add with overflow")]
fn test_reproduce_arith_overflow_panic() {
    let env = Env::default();
    let contract_id = env.register_contract(None, SampleContract);
    let client = SampleContractClient::new(&env, &contract_id);

    // Should trigger panic on unhandled overflow
    client.calculate(&u128::MAX, &1);
}

#[test]
fn test_safe_arithmetic_prevention() {
    let env = Env::default();
    let contract_id = env.register_contract(None, SampleContract);
    let client = SampleContractClient::new(&env, &contract_id);

    // Using checked arithmetic returns None/Err gracefully instead of panicking
    let res = client.try_calculate_safe(&u128::MAX, &1);
    assert!(res.is_err());
}"""
    },
    "require-auth-missing": {
        "title": "Test for Missing Caller Authorization",
        "code": """#[test]
#[should_panic(expected = "missing required authorization")]
fn test_reproduce_missing_auth() {
    let env = Env::default();
    let contract_id = env.register_contract(None, SampleContract);
    let client = SampleContractClient::new(&env, &contract_id);

    let caller = Address::generate(&env);
    // Invocations without mock_all_auths() will trigger auth missing trap
    client.withdraw(&caller, &1000);
}

#[test]
fn test_verified_auth_success() {
    let env = Env::default();
    env.mock_all_auths();
    let contract_id = env.register_contract(None, SampleContract);
    let client = SampleContractClient::new(&env, &contract_id);

    let caller = Address::generate(&env);
    let res = client.withdraw(&caller, &1000);
    assert_eq!(res, 1000);
}"""
    },
    "option-unwrap-none": {
        "title": "Test for Option::unwrap() on None Panic",
        "code": """#[test]
#[should_panic(expected = "called `Option::unwrap()` on a `None` value")]
fn test_reproduce_option_unwrap_panic() {
    let env = Env::default();
    let contract_id = env.register_contract(None, SampleContract);
    let client = SampleContractClient::new(&env, &contract_id);

    // Attempting to read non-existent storage key with .unwrap() panics
    client.get_uninitialized_value();
}

#[test]
fn test_safe_option_handling() {
    let env = Env::default();
    let contract_id = env.register_contract(None, SampleContract);
    let client = SampleContractClient::new(&env, &contract_id);

    let result = client.try_get_value_safe();
    assert_eq!(result, Err(Ok(Error::NotInitialized)));
}"""
    },
    "vec-index-out-of-bounds": {
        "title": "Test for Vec Bounds Panic",
        "code": """#[test]
#[should_panic(expected = "index out of bounds")]
fn test_reproduce_vec_out_of_bounds() {
    let env = Env::default();
    let contract_id = env.register_contract(None, SampleContract);
    let client = SampleContractClient::new(&env, &contract_id);

    // Querying index >= len
    client.get_item(&99);
}"""
    },
    "temporary-storage-expired": {
        "title": "Test for Temporary Storage TTL Expiration",
        "code": """#[test]
fn test_temporary_storage_ttl_lifecycle() {
    let env = Env::default();
    let contract_id = env.register_contract(None, SampleContract);
    let client = SampleContractClient::new(&env, &contract_id);

    client.store_temp_session(&12345);
    // Extend TTL to ensure entry survives past threshold
    env.as_contract(&contract_id, || {
        env.storage().temporary().extend_ttl(&symbol_short!("session"), 50, 100);
    });
}"""
    }
}

def generate_rust_test(error_id: str) -> Dict[str, str]:
    if error_id in TEST_TEMPLATES:
        return TEST_TEMPLATES[error_id]

    # Generic fallback test template
    return {
        "title": f"Test Template for {error_id}",
        "code": f"""#[test]
fn test_{error_id.replace('-', '_')}_prevention() {{
    let env = Env::default();
    let contract_id = env.register_contract(None, SampleContract);
    let client = SampleContractClient::new(&env, &contract_id);

    // Test contract execution guarding against {error_id}
    let res = client.try_execute();
    assert!(res.is_ok());
}}"""
    }
