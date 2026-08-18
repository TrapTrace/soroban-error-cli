## Summary of Changes
<!-- Concise summary of features, bug fixes, or test enhancements introduced in this PR. -->

## Subcommands Affected
- [ ] `traptrace explain` (Error lookup)
- [ ] `traptrace inspect` (On-chain tx debugger)
- [ ] `traptrace simulate` (Pre-flight simulation)
- [ ] `traptrace decode` (DiagnosticEvent XDR parser)
- [ ] `traptrace watch` (Live event stream)
- [ ] `traptrace storage` (TTL & storage auditor)

## Testing Checklist
- [ ] All unit and mock integration tests pass: `pytest`
- [ ] Code formatting and types verified: `python3 -m unittest discover`
- [ ] Added new tests in `tests/` for newly added features
- [ ] Manual test against Stellar Testnet / local RPC node
