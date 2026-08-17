"""
Terminal formatting and color rendering for TrapTrace CLI.
Provides rich ANSI output for catalog entries, transaction inspections, simulations, events, and storage audits.
"""

from typing import Dict, Any

# ANSI Color codes
BOLD = "\033[1m"
RESET = "\033[0m"
CYAN = "\033[36m"
TEAL = "\033[38;2;47;169;140m"
AMBER = "\033[38;2;226;152;75m"
RED = "\033[31m"
GREEN = "\033[32m"
GRAY = "\033[90m"
MAGENTA = "\033[35m"

def render_entry_terminal(entry: Dict[str, Any], detailed: bool = False) -> str:
    verified_badge = f"{GREEN}✔ Verified{RESET}" if entry.get("verified") else f"{AMBER}⚠ Unverified{RESET}"
    category_str = f"{CYAN}{entry.get('category', 'unknown')}{RESET}"
    code_str = f"{BOLD}{entry.get('error_code', 'N/A')}{RESET}"
    
    header = f"{BOLD}📌 [{entry.get('id')}] {entry.get('title')}{RESET}"
    meta = f"   Category: {category_str} | Error Code: {code_str} | Status: {verified_badge}"
    summary = f"   {BOLD}Summary:{RESET} {entry.get('summary', '')}"
    
    output = [header, meta, summary]
    
    if detailed:
        if entry.get("symptoms"):
            output.append(f"   {RED}Symptoms:{RESET} {entry.get('symptoms')}")
        if entry.get("solutions"):
            output.append(f"   {GREEN}Solutions:{RESET} {entry.get('solutions')}")
        if entry.get("tags"):
            tags_formatted = " ".join([f"#{t}" for t in entry.get("tags", [])])
            output.append(f"   {GRAY}Tags: {tags_formatted}{RESET}")
            
    return "\n".join(output)

def render_inspection_report(report: Dict[str, Any]) -> str:
    lines = []
    lines.append(f"{TEAL}{BOLD}⚡ TrapTrace Transaction Diagnostic Report{RESET}")
    lines.append(f"Hash:    {BOLD}{report.get('tx_hash')}{RESET}")
    lines.append(f"Network: {CYAN}{report.get('network')}{RESET} ({report.get('rpc_url', '')})")
    
    status = report.get("status", "UNKNOWN")
    if status == "SUCCESS":
        status_str = f"{GREEN}{BOLD}✔ SUCCESS (Ledger #{report.get('ledger')}){RESET}"
    elif status == "NOT_FOUND":
        status_str = f"{AMBER}{BOLD}⏳ NOT_FOUND (Pending / Ingestion Delay){RESET}"
    else:
        status_str = f"{RED}{BOLD}✖ FAILED / TRAPPED{RESET}"

    lines.append(f"Status:  {status_str}\n")

    if report.get("summary"):
        lines.append(f"{BOLD}Summary:{RESET} {report['summary']}")

    trace = report.get("trace_summary", {})
    if trace:
        calls = trace.get("calls", [])
        if calls:
            lines.append(f"\n{BOLD}Execution Call Trace ({len(calls)} call(s)):{RESET}")
            for c in calls:
                lines.append(f"  • Contract: {MAGENTA}{c.get('contract')}{RESET} | Func: {CYAN}{c.get('function')}{RESET}")
                if c.get("args"):
                    lines.append(f"    Args: {GRAY}{str(c.get('args'))[:120]}{RESET}")

        errors = trace.get("errors", [])
        if errors:
            lines.append(f"\n{RED}{BOLD}Detected Host Traps / Diagnostic Errors ({len(errors)}):{RESET}")
            for err in errors:
                lines.append(f"  ✖ Contract: {err.get('contract', '<host>')}")
                lines.append(f"    Topics: {GRAY}{', '.join(err.get('topics', []))}{RESET}")
                if err.get("detail"):
                    lines.append(f"    Detail: {RED}{err['detail']}{RESET}")

    matched = report.get("matched_catalog_entries", [])
    if matched:
        lines.append(f"\n{TEAL}{BOLD}Matched TrapTrace Catalog Remediations:{RESET}")
        for idx, m in enumerate(matched, 1):
            lines.append(f"\n{idx}. {render_entry_terminal(m, detailed=True)}")

    remediation = report.get("remediation", [])
    if remediation:
        lines.append(f"\n{BOLD}Actionable Steps:{RESET}")
        for r in remediation:
            lines.append(f"  ➜ {r}")

    return "\n".join(lines)

def render_simulation_report(report: Dict[str, Any]) -> str:
    lines = []
    lines.append(f"{TEAL}{BOLD}⚡ TrapTrace Pre-Flight Simulation Report{RESET}")
    lines.append(f"Network: {CYAN}{report.get('network')}{RESET} | Latest Ledger: #{report.get('latest_ledger')}")
    
    if report.get("success"):
        lines.append(f"Status:  {GREEN}{BOLD}✔ SIMULATION PASSED{RESET}\n")
        lines.append(f"{BOLD}Resource Consumption & Costs:{RESET}")
        lines.append(f"  • CPU Instructions:  {CYAN}{report.get('cpu_instructions', 0):,}{RESET}")
        lines.append(f"  • Memory Bytes:      {CYAN}{report.get('mem_bytes', 0):,} bytes{RESET}")
        lines.append(f"  • Min Resource Fee:  {AMBER}{report.get('min_resource_fee', '0')} stroops{RESET}")
        lines.append(f"  • Auth Requirements: {report.get('auth_count', 0)} signature(s)")
    else:
        lines.append(f"Status:  {RED}{BOLD}✖ SIMULATION REVERTED / TRAPPED{RESET}\n")
        lines.append(f"{RED}{BOLD}Error Message:{RESET} {report.get('error_message')}\n")
        
        matched = report.get("matched_catalog_entries", [])
        if matched:
            lines.append(f"{TEAL}{BOLD}Recommended Fixes from Catalog:{RESET}")
            for idx, m in enumerate(matched, 1):
                lines.append(f"\n{idx}. {render_entry_terminal(m, detailed=True)}")

    return "\n".join(lines)

def render_storage_report(report: Dict[str, Any]) -> str:
    lines = []
    lines.append(f"{TEAL}{BOLD}⚡ TrapTrace Contract Storage & TTL Health Audit{RESET}")
    lines.append(f"Contract:       {MAGENTA}{report.get('contract_id')}{RESET}")
    lines.append(f"Current Ledger: #{report.get('current_ledger')}\n")

    if not report.get("success"):
        lines.append(f"{RED}Error: {report.get('error')}{RESET}")
        return "\n".join(lines)

    entries = report.get("entries", [])
    lines.append(f"Checked {len(entries)} state entries ({report.get('expired_count', 0)} expired, {report.get('warning_count', 0)} warnings):\n")

    for idx, e in enumerate(entries, 1):
        health = e.get("health")
        if health == "EXPIRED":
            badge = f"{RED}[EXPIRED]{RESET}"
        elif health in ("CRITICAL", "WARNING"):
            badge = f"{AMBER}[{health}]{RESET}"
        else:
            badge = f"{GREEN}[HEALTHY]{RESET}"

        lines.append(f"  {idx}. Key: {GRAY}{e.get('key')[:40]}...{RESET} {badge}")
        lines.append(f"     Live Until Ledger: #{e.get('live_until_ledger')} (~{e.get('approx_remaining_hours')} hrs remaining)")

    remediations = report.get("remediation", [])
    if remediations:
        lines.append(f"\n{BOLD}Remediation Commands:{RESET}")
        for r in remediations:
            lines.append(f"  {r}")

    return "\n".join(lines)
