# TrapTrace CLI (`soroban-error-cli`)

![CI Workflow](https://github.com/TrapTrace/soroban-error-cli/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/License-MIT-teal.svg)
![PyPI](https://img.shields.io/badge/Python-3.8%2B-blue.svg)

**TrapTrace CLI** (`soroban-explain`) is a lightweight, high-speed terminal utility that decodes cryptic Soroban VM traps, CLI errors, RPC simulation failures, and SDK conversion issues directly in your local terminal workflow.

---

## ⚡ Quick Installation

Install locally via `pip`:

```bash
pip install -e .
```

Or run directly with Python:

```bash
python3 -m traptrace_cli.cli "budget"
```

---

## 🎯 Usage Examples

### 1. Explain an Error String or Code
```bash
soroban-explain "HostError::BudgetExceeded"
```

### 2. View Detailed Symptoms and Resolution Steps
```bash
soroban-explain "ttl" --detailed
```

### 3. Filter by Error Category
```bash
soroban-explain --category host-error
```

### 4. Output JSON for IDE Integration & Scripts
```bash
soroban-explain "account-not-found" --json
```

---

## 🧪 Running Unit Tests

Run the test suite using `pytest`:

```bash
pip install pytest
pytest tests/
```

---

## 📄 License

MIT License. Copyright (c) 2026 TrapTrace.
