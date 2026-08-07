<div align="center">

# ⚡ TrapTrace CLI — Terminal Error Explainer

**A lightweight, high-speed terminal utility (`soroban-explain`) to decode Soroban VM traps, CLI errors, RPC simulation failures, and SDK conversion issues.**

[![CI Workflow](https://img.shields.io/github/actions/workflow/status/TrapTrace/soroban-error-cli/ci.yml?branch=main&style=flat-square&color=2FA98C&label=CI%20Workflow)](https://github.com/TrapTrace/soroban-error-cli/actions)
[![Python](https://img.shields.io/badge/Python-3.10%2B-1B1F23?style=flat-square)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-2FA98C?style=flat-square)](./LICENSE)
[![Stellar Wave](https://img.shields.io/badge/Drips%20Wave-8%20Target-E2984B?style=flat-square)](https://drips.network)

</div>

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
