# Wave engineering backlog

Drafted October 8, 2026 against current implementation. These are proposed contributor tasks, not Wave enrollment or earned points. Complexity requires maintainer review in the app.

## 1. Decode raw RPC authorization entries into actual trees

## Context

Parse canonical supported authorization-entry XDR, preserve unsupported entries explicitly and never infer valid signatures; test captured nested RPC auth.

## Acceptance criteria

- Implement and document the specific behavior above.
- Cover positive, negative and unavailable-input cases appropriate to the change.
- Pass the repository documented build/test checks and required CI.
- Preserve exact identities/amounts and uncertain evidence outcomes.

## Relevant files

traptrace_cli/auth_checker.py

## Proposed complexity

medium; planning only. Actual Wave complexity and enrollment are set by maintainers in the Drips app.

## Contribution

Open a focused feat/fix/test/docs branch. PRs explain behavior and actual validation and include Closes #<issue_id>. Follow CONTRIBUTING.md and SECURITY.md.

## 2. Add simulation response-shape validation

## Context

Reject malformed results/auth/events structures with a diagnostic error; unavailable RPC and empty results must never become a successful simulation.

## Acceptance criteria

- Implement and document the specific behavior above.
- Cover positive, negative and unavailable-input cases appropriate to the change.
- Pass the repository documented build/test checks and required CI.
- Preserve exact identities/amounts and uncertain evidence outcomes.

## Relevant files

traptrace_cli/simulator.py

## Proposed complexity

medium; planning only. Actual Wave complexity and enrollment are set by maintainers in the Drips app.

## Contribution

Open a focused feat/fix/test/docs branch. PRs explain behavior and actual validation and include Closes #<issue_id>. Follow CONTRIBUTING.md and SECURITY.md.

## 3. Capture a valid missing-authorization execution fixture

## Context

Use a real contract and valid envelope; distinguish auth failure from malformed XDR and compare actual simulator/checker output.

## Acceptance criteria

- Implement and document the specific behavior above.
- Cover positive, negative and unavailable-input cases appropriate to the change.
- Pass the repository documented build/test checks and required CI.
- Preserve exact identities/amounts and uncertain evidence outcomes.

## Relevant files

tests/, traptrace_cli/auth_checker.py

## Proposed complexity

high; planning only. Actual Wave complexity and enrollment are set by maintainers in the Drips app.

## Contribution

Open a focused feat/fix/test/docs branch. PRs explain behavior and actual validation and include Closes #<issue_id>. Follow CONTRIBUTING.md and SECURITY.md.

## 4. Bound XDR and diagnostic output sizes

## Context

Set explicit input/event/report limits; reject oversized synthetic payloads before expensive decoding and preserve a useful exit/error result.

## Acceptance criteria

- Implement and document the specific behavior above.
- Cover positive, negative and unavailable-input cases appropriate to the change.
- Pass the repository documented build/test checks and required CI.
- Preserve exact identities/amounts and uncertain evidence outcomes.

## Relevant files

traptrace_cli/xdr_decoder.py, traptrace_cli/cli.py

## Proposed complexity

medium; planning only. Actual Wave complexity and enrollment are set by maintainers in the Drips app.

## Contribution

Open a focused feat/fix/test/docs branch. PRs explain behavior and actual validation and include Closes #<issue_id>. Follow CONTRIBUTING.md and SECURITY.md.

## 5. Document simulation versus signature verification

## Context

Provide raw auth footprint and unrelated trap examples; explain REVIEW_REQUIRED and FAIL without equating simulation with transaction acceptance.

## Acceptance criteria

- Implement and document the specific behavior above.
- Cover positive, negative and unavailable-input cases appropriate to the change.
- Pass the repository documented build/test checks and required CI.
- Preserve exact identities/amounts and uncertain evidence outcomes.

## Relevant files

README.md

## Proposed complexity

trivial; planning only. Actual Wave complexity and enrollment are set by maintainers in the Drips app.

## Contribution

Open a focused feat/fix/test/docs branch. PRs explain behavior and actual validation and include Closes #<issue_id>. Follow CONTRIBUTING.md and SECURITY.md.

## 6. Add a package installation smoke check to CI

## Context

Build/install the wheel in an isolated environment and verify CLI JSON/search imports its bundled catalog without sibling repositories.

## Acceptance criteria

- Implement and document the specific behavior above.
- Cover positive, negative and unavailable-input cases appropriate to the change.
- Pass the repository documented build/test checks and required CI.
- Preserve exact identities/amounts and uncertain evidence outcomes.

## Relevant files

pyproject.toml, .github/workflows/ci.yml

## Proposed complexity

medium; planning only. Actual Wave complexity and enrollment are set by maintainers in the Drips app.

## Contribution

Open a focused feat/fix/test/docs branch. PRs explain behavior and actual validation and include Closes #<issue_id>. Follow CONTRIBUTING.md and SECURITY.md.

## Published contributor issues

- [Decode raw RPC authorization entries into actual trees](https://github.com/TrapTrace/soroban-error-cli/issues/7) — proposed medium.
- [Add simulation response-shape validation](https://github.com/TrapTrace/soroban-error-cli/issues/8) — proposed medium.
- [Capture a valid missing-authorization execution fixture](https://github.com/TrapTrace/soroban-error-cli/issues/9) — proposed high.
- [Bound XDR and diagnostic output sizes](https://github.com/TrapTrace/soroban-error-cli/issues/10) — proposed medium.
- [Document simulation versus signature verification](https://github.com/TrapTrace/soroban-error-cli/issues/11) — proposed trivial.
- [Add a package installation smoke check to CI](https://github.com/TrapTrace/soroban-error-cli/issues/12) — proposed medium.
