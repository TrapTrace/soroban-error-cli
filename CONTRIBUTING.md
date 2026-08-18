# Contributing to TrapTrace CLI (`traptrace-cli`)

Thank you for contributing to the TrapTrace operational CLI!

---

## 🛠 Local Development Setup

```bash
# Clone the repository
git clone https://github.com/TrapTrace/soroban-error-cli.git
cd soroban-error-cli

# Install in editable mode with development dependencies
pip install -e .
pip install pytest flake8

# Run test suite
pytest
```

---

## 🏗 Architecture & Modules

The `traptrace_cli` package is structured into modular operational subcomponents:
- `rpc_client.py`: Zero-dependency JSON-RPC 2.0 network client.
- `xdr_decoder.py`: Binary/base64 XDR parser for `DiagnosticEvents` and `ScVal`.
- `inspector.py`: Transaction hash inspector and failure mapper.
- `simulator.py`: Pre-flight transaction envelope simulation engine.
- `storage_auditor.py`: Contract ledger entry and TTL auditor.
- `watcher.py`: Real-time contract event monitor.
- `formatter.py`: ANSI colorized terminal output renderer.
- `cli.py`: Unified argparse entrypoint (`traptrace` and `soroban-explain`).

---

## 🧪 Testing Guidelines

All contributions must include tests:
- Place unit and mock integration tests in `tests/test_operational.py` or `tests/test_cli.py`.
- Mock external network RPC calls using `unittest.mock.patch`.
- Verify 100% pass rate before opening a PR: `pytest`.
