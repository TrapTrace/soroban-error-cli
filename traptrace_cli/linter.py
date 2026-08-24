"""
TrapTrace Static Analysis & Anti-Pattern Linter for Soroban Smart Contracts.
Scans Rust smart contract code for common traps, anti-patterns, and vulnerability patterns.
"""

import os
import re
from typing import List, Dict, Any, Optional

LINT_RULES = [
    {
        "id": "TT-LINT-001",
        "name": "UNSAFE_UNWRAP",
        "severity": "CRITICAL",
        "category": "panic",
        "error_id": "option-unwrap-none",
        "pattern": r"\.(?:unwrap|expect)\s*\(",
        "message": "Unsafe .unwrap() or .expect() detected; unhandled None/Err will trigger a WASM panic and revert transactions.",
        "remediation": "Use '?' operator with custom #[contracterror] enums, or use .unwrap_or() / match."
    },
    {
        "id": "TT-LINT-002",
        "name": "RAW_ARITHMETIC",
        "severity": "WARNING",
        "category": "math",
        "error_id": "arith-error",
        "pattern": r"(?:\b[a-zA-Z_]\w*\s*(?:\+|\-|\*|\/)\s*[a-zA-Z0-9_]+)(?!\s*//)(?!\s*=>)",
        "message": "Raw arithmetic operator detected; unchecked arithmetic may trigger HostError::ArithDomain on overflow/underflow.",
        "remediation": "Use checked_add(), checked_sub(), checked_mul(), or saturating arithmetic methods."
    },
    {
        "id": "TT-LINT-003",
        "name": "MISSING_STORAGE_TTL_EXTEND",
        "severity": "WARNING",
        "category": "storage",
        "error_id": "instance-storage-expired",
        "pattern": r"env\.storage\(\)\.(?:instance|persistent)\(\)\.set\s*\(",
        "negative_check": r"extend_ttl",
        "message": "State written to storage without explicit TTL extension; idle entries risk archival under CAP-0046.",
        "remediation": "Add env.storage().instance().extend_ttl(threshold, extend_to) after storage writes."
    },
    {
        "id": "TT-LINT-004",
        "name": "UNGUARDED_CALLER_MUTATION",
        "severity": "CRITICAL",
        "category": "auth",
        "error_id": "require-auth-missing",
        "pattern": r"pub\s+fn\s+\w+\s*\([^)]*caller\s*:\s*Address[^)]*\)",
        "negative_check": r"caller\.require_auth\s*\(",
        "message": "Function accepts caller Address but lacks explicit require_auth() validation check.",
        "remediation": "Invoke caller.require_auth() at the beginning of the function body."
    },
    {
        "id": "TT-LINT-005",
        "name": "DIRECT_VEC_INDEXING",
        "severity": "CRITICAL",
        "category": "collection",
        "error_id": "vec-index-out-of-bounds",
        "pattern": r"\.get\s*\([^)]+\)\.unwrap\s*\(",
        "message": "Direct vector/map .get().unwrap() indexing will panic on out-of-bounds or key miss.",
        "remediation": "Handle None return value safely with match, if-let, or ok_or(Error::NotFound)?."
    }
]

class LintFinding:
    def __init__(self, rule_id: str, name: str, severity: str, message: str, line_num: int, line_content: str, remediation: str, error_id: str):
        self.rule_id = rule_id
        self.name = name
        self.severity = severity
        self.message = message
        self.line_num = line_num
        self.line_content = line_content.strip()
        self.remediation = remediation
        self.error_id = error_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "severity": self.severity,
            "message": self.message,
            "line_num": self.line_num,
            "line_content": self.line_content,
            "remediation": self.remediation,
            "error_id": self.error_id
        }

def lint_source_code(code: str, filename: str = "<stdin>") -> List[LintFinding]:
    findings: List[LintFinding] = []
    lines = code.splitlines()
    full_text = code

    for rule in LINT_RULES:
        regex = re.compile(rule["pattern"])
        neg_check = rule.get("negative_check")

        # If negative check exists and is present in the full file, skip
        if neg_check and re.search(neg_check, full_text):
            continue

        for i, line in enumerate(lines, 1):
            # Skip comments
            trimmed = line.strip()
            if trimmed.startswith("//") or trimmed.startswith("/*") or trimmed.startswith("*"):
                continue

            if regex.search(line):
                # Filter out obvious false positives for arithmetic (like type definitions or match arms)
                if rule["id"] == "TT-LINT-002":
                    if "fn " in line or "impl " in line or "struct " in line or "enum " in line or "let " not in line:
                        continue
                    if "+ 1" not in line and "- 1" not in line and " * " not in line and " / " not in line:
                        continue

                findings.append(
                    LintFinding(
                        rule_id=rule["id"],
                        name=rule["name"],
                        severity=rule["severity"],
                        message=rule["message"],
                        line_num=i,
                        line_content=line,
                        remediation=rule["remediation"],
                        error_id=rule["error_id"]
                    )
                )

    return findings

def lint_file(filepath: str) -> Dict[str, Any]:
    if not os.path.exists(filepath):
        return {"file": filepath, "error": "File not found", "findings": []}

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    findings = lint_source_code(content, filepath)
    return {
        "file": filepath,
        "total_findings": len(findings),
        "critical_count": sum(1 for f in findings if f.severity == "CRITICAL"),
        "warning_count": sum(1 for f in findings if f.severity == "WARNING"),
        "findings": [f.to_dict() for f in findings]
    }
