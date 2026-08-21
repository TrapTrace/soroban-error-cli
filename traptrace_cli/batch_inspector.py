"""
Batch Transaction Inspector for TrapTrace CLI.
Performs concurrent or sequential diagnostics across multi-transaction datasets,
aggregates failure patterns, and generates comprehensive batch reports.
"""

import json
import time
from typing import List, Dict, Any, Optional

from traptrace_cli.rpc_client import SorobanRpcClient
from traptrace_cli.inspector import TransactionInspector
from traptrace_cli.tui import (
    BOLD, RESET, DIM, TEAL, CYAN, RED, GREEN, YELLOW, WHITE,
    render_meter_bar, render_box
)

class BatchInspector:
    """Inspector engine for analyzing multiple transactions in batch."""

    def __init__(self, rpc_client: Optional[SorobanRpcClient] = None):
        self.client = rpc_client or SorobanRpcClient("testnet")
        self.inspector = TransactionInspector(rpc_client=self.client)

    def inspect_file(self, file_path: str, max_limit: Optional[int] = None) -> Dict[str, Any]:
        """Load transaction hashes from a JSON file and inspect."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        hashes = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    hashes.append(item)
                elif isinstance(item, dict) and "tx_hash" in item:
                    hashes.append(item["tx_hash"])
                elif isinstance(item, dict) and "hash" in item:
                    hashes.append(item["hash"])
        elif isinstance(data, dict) and "transactions" in data:
            for item in data["transactions"]:
                if isinstance(item, str):
                    hashes.append(item)
                elif isinstance(item, dict) and "hash" in item:
                    hashes.append(item["hash"])
                elif isinstance(item, dict) and "tx_hash" in item:
                    hashes.append(item["tx_hash"])
                    
        if max_limit and len(hashes) > max_limit:
            hashes = hashes[:max_limit]
            
        return self.inspect_hashes(hashes)

    def inspect_hashes(self, tx_hashes: List[str], delay_between_requests: float = 0.05) -> Dict[str, Any]:
        """Inspect a list of transaction hashes and aggregate analytics."""
        results = []
        category_counts: Dict[str, int] = {}
        error_code_counts: Dict[str, int] = {}
        catalog_matches: Dict[str, int] = {}
        
        success_count = 0
        failed_count = 0
        total_cpu = 0
        total_mem = 0
        measured_tx_count = 0
        
        for idx, h in enumerate(tx_hashes, 1):
            h_clean = h.strip()
            if not h_clean:
                continue
                
            report = self.inspector.inspect(h_clean)
            results.append(report)
            
            is_success = report.get("is_successful", False)
            if is_success:
                success_count += 1
            else:
                failed_count += 1
                
            # Collect metrics
            metrics = report.get("resource_metrics", {})
            cpu = metrics.get("cpu_instructions", 0)
            mem = metrics.get("memory_bytes", 0)
            if cpu > 0 or mem > 0:
                total_cpu += cpu
                total_mem += mem
                measured_tx_count += 1
                
            # Failure categorization
            diag = report.get("diagnostics", {})
            if diag and diag.get("matched"):
                entry_id = diag.get("entry_id")
                cat = diag.get("category", "unknown")
                code = diag.get("error_code", "UNKNOWN")
                
                catalog_matches[entry_id] = catalog_matches.get(entry_id, 0) + 1
                category_counts[cat] = category_counts.get(cat, 0) + 1
                error_code_counts[code] = error_code_counts.get(code, 0) + 1
                
            if delay_between_requests > 0 and idx < len(tx_hashes):
                time.sleep(delay_between_requests)
                
        total = len(results)
        failure_rate = (failed_count / total * 100.0) if total > 0 else 0.0
        avg_cpu = int(total_cpu / measured_tx_count) if measured_tx_count > 0 else 0
        avg_mem = int(total_mem / measured_tx_count) if measured_tx_count > 0 else 0
        
        return {
            "summary": {
                "total_inspected": total,
                "successful_transactions": success_count,
                "failed_transactions": failed_count,
                "failure_rate_percent": round(failure_rate, 2),
                "average_cpu_instructions": avg_cpu,
                "average_memory_bytes": avg_mem,
                "network": self.client.network_name,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            },
            "category_breakdown": category_counts,
            "error_code_breakdown": error_code_counts,
            "top_matched_catalog_entries": sorted(catalog_matches.items(), key=lambda x: x[1], reverse=True),
            "transactions": results
        }

def render_batch_report_terminal(batch_data: Dict[str, Any]) -> str:
    """Render terminal formatted output for batch transaction inspection."""
    s = batch_data.get("summary", {})
    total = s.get("total_inspected", 0)
    succ = s.get("successful_transactions", 0)
    fail = s.get("failed_transactions", 0)
    rate = s.get("failure_rate_percent", 0.0)
    
    rate_color = GREEN if rate == 0 else (YELLOW if rate < 25 else RED)
    
    lines = [
        f"\n{TEAL}{BOLD}⚡ TrapTrace Multi-Transaction Batch Inspection Report{RESET}\n",
        f"  • Network:           {CYAN}{s.get('network')}{RESET}",
        f"  • Total Inspected:   {BOLD}{total}{RESET} transactions",
        f"  • Successful:        {GREEN}{succ}{RESET} ({(succ/total*100 if total else 0):.1f}%)",
        f"  • Failed / Reverted: {RED}{fail}{RESET} ({(fail/total*100 if total else 0):.1f}%)",
        f"  • Failure Rate:      {rate_color}{BOLD}{rate:.1f}%{RESET}",
        f"  • Avg CPU Gas:       {s.get('average_cpu_instructions', 0):,} instructions",
        f"  • Avg WASM Memory:   {s.get('average_memory_bytes', 0) / 1024:.1f} KB\n",
    ]
    
    # Error categories
    cats = batch_data.get("category_breakdown", {})
    if cats:
        lines.append(f"{BOLD}📊 Failure Category Distribution:{RESET}")
        for cat, cnt in cats.items():
            bar = render_meter_bar(cnt, fail or total, width=18)
            lines.append(f"  • {cat:<16} [{bar}] {cnt} tx ({(cnt/(fail or total)*100):.1f}%)")
        lines.append("")
        
    # Top errors
    top_entries = batch_data.get("top_matched_catalog_entries", [])
    if top_entries:
        lines.append(f"{BOLD}🔍 Top Diagnosed Root Causes & Fixes:{RESET}")
        for entry_id, cnt in top_entries[:5]:
            lines.append(f"  • {YELLOW}{BOLD}{entry_id}{RESET}: {cnt} occurrences -> fix with: {CYAN}traptrace fix {entry_id}{RESET}")
        lines.append("")
        
    # Detailed transaction list preview
    txs = batch_data.get("transactions", [])
    lines.append(f"{BOLD}📋 Transaction Execution Breakdown (First 10):{RESET}")
    for idx, tx in enumerate(txs[:10], 1):
        status_tag = f"{GREEN}[SUCCESS]{RESET}" if tx.get("is_successful") else f"{RED}[FAILED]{RESET}"
        diag = tx.get("diagnostics", {})
        root_cause = diag.get("entry_id", "Unknown") if diag.get("matched") else "N/A"
        tx_short = tx.get("tx_hash", "")[:12] + "..." + tx.get("tx_hash", "")[-6:] if len(tx.get("tx_hash", "")) > 18 else tx.get("tx_hash")
        lines.append(f"  {idx:2d}. {tx_short} | Status: {status_tag} | Root Cause: {root_cause}")
        
    if len(txs) > 10:
        lines.append(f"  {DIM}... and {len(txs) - 10} more transactions (use --export-json to view all){RESET}")
        
    lines.append("")
    return "\n".join(lines)

def render_batch_report_markdown(batch_data: Dict[str, Any]) -> str:
    """Render GitHub-flavored markdown report for batch inspection."""
    s = batch_data.get("summary", {})
    md = [
        "# ⚡ TrapTrace Multi-Transaction Diagnostic Report",
        "",
        f"**Generated:** `{s.get('timestamp')}` | **Network:** `{s.get('network')}`",
        "",
        "## Executive Summary",
        "",
        f"| Metric | Value |",
        f"| :--- | :--- |",
        f"| **Total Transactions** | `{s.get('total_inspected')}` |",
        f"| **Successful Transactions** | `{s.get('successful_transactions')}` |",
        f"| **Failed Transactions** | `{s.get('failed_transactions')}` |",
        f"| **Failure Rate** | `{s.get('failure_rate_percent')}%` |",
        f"| **Average CPU Instructions** | `{s.get('average_cpu_instructions'):,}` |",
        f"| **Average WASM Memory** | `{s.get('average_memory_bytes', 0) / 1024:.2f} KB` |",
        "",
        "## Failure Breakdown by Category",
        "",
        "| Category | Occurrences | Share |",
        "| :--- | :--- | :--- |",
    ]
    
    fail = s.get("failed_transactions", 1) or 1
    for cat, cnt in batch_data.get("category_breakdown", {}).items():
        md.append(f"| `{cat}` | {cnt} | {(cnt/fail*100):.1f}% |")
        
    md.extend([
        "",
        "## Top Diagnosed Root Causes",
        "",
        "| Catalog Error ID | Count | Remediation Command |",
        "| :--- | :--- | :--- |",
    ])
    
    for entry_id, cnt in batch_data.get("top_matched_catalog_entries", []):
        md.append(f"| [`{entry_id}`](https://traptrace-explorer.vercel.app/?tab=catalog&id={entry_id}) | {cnt} | `traptrace fix {entry_id}` |")
        
    md.extend([
        "",
        "## Transaction Details",
        "",
        "| # | Transaction Hash | Status | Root Cause | CPU Gas |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ])
    
    for idx, tx in enumerate(batch_data.get("transactions", []), 1):
        status = "✅ SUCCESS" if tx.get("is_successful") else "❌ FAILED"
        diag = tx.get("diagnostics", {})
        cause = diag.get("entry_id", "-") if diag.get("matched") else "-"
        cpu = tx.get("resource_metrics", {}).get("cpu_instructions", 0)
        h = tx.get("tx_hash", "")
        short_h = f"`{h[:8]}...{h[-6:]}`" if len(h) > 16 else f"`{h}`"
        md.append(f"| {idx} | {short_h} | {status} | {cause} | {cpu:,} |")
        
    md.append("")
    return "\n".join(md)
