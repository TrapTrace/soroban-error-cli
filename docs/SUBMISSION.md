# Soroban simulation and diagnostic CLI

Prepared October 8, 2026 for same-day Stellar Wave application.

## Implemented utility

Standalone Python CLI searches 35 error entries, queries RPC, simulates transactions and reports diagnostic events. The authorization checker now consumes the actual simulator report and distinguishes simulation outcomes from signature verification.

## Reproduce and evidence

python3 -m pytest -q: 44 tests passed October 8. Python compile checks and CLI JSON output passed. Runtime dependencies are standard-library only.

## Supported scope

Successful simulation requires review and never proves valid signatures. Catalog entries are suggestions pending named-error reproduction; raw auth XDR is retained when not decoded.

## Maintainers and application

Maintainers xteesamz and EthTobi were owner-confirmed across these project families; contact through GitHub, available anytime. Follow CONTRIBUTING.md and SECURITY.md (or organization defaults). Review the preparation PR and its CI before using its final revision in the application. Engineering issues and draft complexity do not establish Wave enrollment. No application has been submitted by this work.
