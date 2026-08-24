"""
Main entry point for TrapTrace CLI / soroban-explain.
Provides subcommands for error lookup, live transaction inspection, pre-flight simulation,
XDR event decoding, contract monitoring, and storage TTL auditing.
"""

import sys
import argparse
import json
from typing import Optional

from traptrace_cli.data import load_entries
from traptrace_cli.search_engine import search_errors
from traptrace_cli.formatter import (
    render_entry_terminal,
    render_inspection_report,
    render_simulation_report,
    render_storage_report,
    BOLD, RESET, TEAL, CYAN, RED, YELLOW
)
from traptrace_cli.rpc_client import SorobanRpcClient
from traptrace_cli.inspector import TransactionInspector
from traptrace_cli.simulator import TransactionSimulator
from traptrace_cli.watcher import ContractEventWatcher
from traptrace_cli.storage_auditor import StorageAuditor
from traptrace_cli.xdr_decoder import decode_diagnostic_event
from traptrace_cli.batch_inspector import (
    BatchInspector,
    render_batch_report_terminal,
    render_batch_report_markdown
)
from traptrace_cli.auth_checker import (
    AuthChecker,
    render_auth_report_terminal
)
from traptrace_cli.fix_generator import (
    FixGenerator,
    render_fix_terminal
)

def export_output(content_str: str, file_path: Optional[str] = None):
    if file_path:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content_str)
        print(f"\n✅ Diagnostic report saved to: {file_path}\n")
    else:
        print(content_str)

def handle_explain(args, client: Optional[SorobanRpcClient] = None):
    entries = load_entries(custom_dir=args.index_path)
    results = search_errors(
        entries, 
        query=args.query, 
        category=args.category, 
        verified_only=args.verified,
        include_scores=args.rank
    )
    
    if args.json:
        print(json.dumps(results, indent=2))
        return
        
    if not results:
        print(f"\n❌ No matching Soroban error entries found for query: '{args.query}'\n")
        sys.exit(1)
        
    print(f"\n{TEAL}{BOLD}⚡ TrapTrace Soroban Error Diagnostics{RESET}\n")
    print(f"Found {len(results)} matching error catalog entries:\n")
    
    for idx, entry in enumerate(results, 1):
        score_info = f" [Score: {entry.get('_score', 0):.1f}]" if args.rank else ""
        print(f"{idx}. {BOLD}{entry.get('title')}{RESET}{score_info}")
        print(render_entry_terminal(entry, detailed=args.detailed or len(results) == 1))
        print()

def handle_inspect(args, client: SorobanRpcClient):
    inspector = TransactionInspector(rpc_client=client)
    report = inspector.inspect(args.tx_hash)
    
    if getattr(args, "export_json", None) or args.json:
        json_str = json.dumps(report, indent=2)
        if getattr(args, "export_json", None):
            export_output(json_str, args.export_json)
        else:
            print(json_str)
        return
        
    md_content = render_inspection_report(report)
    if getattr(args, "export_md", None):
        export_output(md_content, args.export_md)
        return

    print()
    print(md_content)
    print()

def handle_simulate(args, client: SorobanRpcClient):
    simulator = TransactionSimulator(rpc_client=client)
    report = simulator.simulate(args.xdr, resource_leeway=args.leeway)
    
    if getattr(args, "export_json", None) or args.json:
        json_str = json.dumps(report, indent=2)
        if getattr(args, "export_json", None):
            export_output(json_str, args.export_json)
        else:
            print(json_str)
        return
        
    md_content = render_simulation_report(report)
    if getattr(args, "export_md", None):
        export_output(md_content, args.export_md)
        return

    print()
    print(md_content)
    print()

def handle_decode(args, client: Optional[SorobanRpcClient] = None):
    decoded = decode_diagnostic_event(args.xdr)
    
    if args.json:
        print(json.dumps(decoded, indent=2))
        return
        
    print(f"\n{TEAL}{BOLD}⚡ TrapTrace XDR Decoded Diagnostic Event{RESET}\n")
    print(f"  • Successful Call: {decoded.get('in_successful_call')}")
    print(f"  • Contract ID:     {decoded.get('contract_id', '<none>')}")
    print(f"  • Event Type:      {decoded.get('event_type')}")
    print(f"  • Topics:          {decoded.get('topics')}")
    print(f"  • Data:            {decoded.get('data')}")
    print()

def handle_watch(args, client: SorobanRpcClient):
    watcher = ContractEventWatcher(rpc_client=client)
    print(f"\n{TEAL}{BOLD}⚡ TrapTrace Contract Event Watcher{RESET}")
    print(f"Streaming live events for contract {CYAN}{args.contract or 'ALL'}{RESET} on {client.network_name}...\n")
    
    def on_event(ev):
        if args.json:
            print(json.dumps(ev))
        else:
            status_tag = f"{RED}[TRAP/ERROR]{RESET}" if ev.get("is_error") else "[OK]"
            print(f"[{ev.get('timestamp', 'now')}] Ledger #{ev.get('ledger')} | Contract: {ev.get('contract_id', 'N/A')} {status_tag}")
            print(f"  Topics: {ev.get('topics')}")
            print(f"  Data:   {ev.get('value')}\n")

    try:
        watcher.watch(
            contract_id=args.contract,
            poll_interval_seconds=args.interval,
            max_iterations=args.count,
            callback=on_event
        )
    except KeyboardInterrupt:
        print(f"\n{BOLD}Watcher stopped by user.{RESET}\n")

def handle_storage(args, client: SorobanRpcClient):
    auditor = StorageAuditor(rpc_client=client)
    report = auditor.audit_contract_keys(contract_id=args.contract, xdr_keys=args.keys)
    
    if getattr(args, "export_json", None) or args.json:
        json_str = json.dumps(report, indent=2)
        if getattr(args, "export_json", None):
            export_output(json_str, args.export_json)
        else:
            print(json_str)
        return
        
    md_content = render_storage_report(report)
    if getattr(args, "export_md", None):
        export_output(md_content, args.export_md)
        return

    print()
    print(md_content)
    print()

def handle_batch_inspect(args, client: SorobanRpcClient):
    inspector = BatchInspector(rpc_client=client)
    if getattr(args, "file", None):
        report = inspector.inspect_file(args.file, max_limit=args.limit)
    else:
        report = inspector.inspect_hashes(args.hashes)
        
    if getattr(args, "export_json", None) or args.json:
        json_str = json.dumps(report, indent=2)
        if getattr(args, "export_json", None):
            export_output(json_str, args.export_json)
        else:
            print(json_str)
        return
        
    if getattr(args, "export_md", None):
        md_content = render_batch_report_markdown(report)
        export_output(md_content, args.export_md)
        return

    print(render_batch_report_terminal(report))

def handle_auth_check(args, client: SorobanRpcClient):
    checker = AuthChecker(rpc_client=client)
    report = checker.check_xdr(args.xdr)
    
    if getattr(args, "export_json", None) or args.json:
        json_str = json.dumps(report, indent=2)
        if getattr(args, "export_json", None):
            export_output(json_str, args.export_json)
        else:
            print(json_str)
        return
        
    print(render_auth_report_terminal(report))

def handle_fix(args, client: Optional[SorobanRpcClient] = None):
    generator = FixGenerator()
    fix_data = generator.get_fix(args.error_id)
    
    if not fix_data:
        all_snippets = generator.generate_all()
        print(f"\n❌ No direct auto-fix snippet found for '{args.error_id}'.")
        print(f"\n{BOLD}Available Auto-Fix Remediation Templates ({len(all_snippets)}):{RESET}")
        for k, v in all_snippets.items():
            print(f"  • {CYAN}traptrace fix {k:<25}{RESET} -> {v.get('title')}")
        print()
        sys.exit(1)
        
    if args.json:
        print(json.dumps(fix_data, indent=2))
        return
        
def handle_lint(args, client: Optional[SorobanRpcClient] = None):
    from traptrace_cli.linter import lint_file
    result = lint_file(args.file)
    if args.json:
        print(json.dumps(result, indent=2))
        return
        
    print(f"\n{TEAL}{BOLD}⚡ TrapTrace Soroban Smart Contract Linter{RESET}")
    print(f"Target: {BOLD}{args.file}{RESET} | Findings: {result['total_findings']} (Critical: {RED}{result['critical_count']}{RESET}, Warning: {YELLOW}{result['warning_count']}{RESET})\n")
    
    if not result["findings"]:
        print("✅ No common Soroban anti-patterns or trap conditions detected.\n")
        return
        
    for f in result["findings"]:
        sev_color = RED if f["severity"] == "CRITICAL" else YELLOW
        print(f"  {sev_color}[{f['severity']}]{RESET} {BOLD}{f['rule_id']}: {f['name']}{RESET} (line {f['line_num']})")
        print(f"    Code: {CYAN}{f['line_content']}{RESET}")
        print(f"    Issue: {f['message']}")
        print(f"    Fix: {f['remediation']}")
        print(f"    Catalog Guide: {BOLD}traptrace explain {f['error_id']}{RESET}\n")

def handle_profile(args, client: SorobanRpcClient):
    from traptrace_cli.profiler import profile_simulation_result, render_ascii_flamegraph
    simulator = TransactionSimulator(rpc_client=client)
    sim_res = simulator.simulate(args.xdr)
    profile = profile_simulation_result(sim_res.get("raw_simulation", {}))
    
    if args.json:
        print(json.dumps(profile.to_dict(), indent=2))
        return
        
    print()
    print(render_ascii_flamegraph(profile))
    print()

def handle_generate_test(args, client: Optional[SorobanRpcClient] = None):
    from traptrace_cli.test_generator import generate_rust_test
    test_fixture = generate_rust_test(args.error_id)
    
    if args.json:
        print(json.dumps(test_fixture, indent=2))
        return
        
    if getattr(args, "export_rs", None):
        export_output(test_fixture["code"], args.export_rs)
        return
        
    print(f"\n{TEAL}{BOLD}⚡ TrapTrace Rust Unit Test Fixture: {test_fixture['title']}{RESET}\n")
    print(test_fixture["code"])
    print()

def handle_health(args, client: Optional[SorobanRpcClient] = None):
    from traptrace_cli.health import check_all_networks, check_endpoint_health
    if args.rpc_url:
        results = [check_endpoint_health(args.rpc_url, "custom")]
    else:
        results = check_all_networks()
        
    if args.json:
        print(json.dumps(results, indent=2))
        return
        
    print(f"\n{TEAL}{BOLD}⚡ Stellar & Soroban RPC Health Status{RESET}\n")
    for r in results:
        status_color = TEAL if r["status"] == "HEALTHY" else RED
        print(f"  • {BOLD}{r['network'].upper():<12}{RESET} -> {status_color}{r['status']:<8}{RESET} ({r['latency_ms']}ms)")
        if r['status'] == 'HEALTHY':
            print(f"    Ledger: #{r['latest_ledger']} | Protocol: v{r['protocol_version']} | URL: {r['rpc_url']}")
        else:
            print(f"    Error: {r.get('error')} | URL: {r['rpc_url']}")
    print()

def main():
    parser = argparse.ArgumentParser(
        prog="traptrace",
        description="TrapTrace: Operational diagnostic engine, transaction inspector, and error resolver for Stellar Soroban."
    )
    
    parser.add_argument("--network", choices=["testnet", "mainnet", "futurenet", "local", "standalone"], default="testnet", help="Stellar network (default: testnet)")
    parser.add_argument("--rpc-url", help="Custom Soroban JSON-RPC endpoint URL")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    
    subparsers = parser.add_subparsers(dest="subcommand", help="Operational Subcommands")
    
    # explain (error lookup)
    p_explain = subparsers.add_parser("explain", help="Search error codes, keywords, and stack traces in the catalog")
    p_explain.add_argument("query", nargs="?", default="", help="Error string, code, or keyword")
    p_explain.add_argument("-c", "--category", choices=["host-error", "cli-error", "rpc-error", "sdk-error"], help="Filter by category")
    p_explain.add_argument("-v", "--verified", action="store_true", help="Show verified entries only")
    p_explain.add_argument("-r", "--rank", action="store_true", help="Display relevance score ranking for results")
    p_explain.add_argument("-d", "--detailed", action="store_true", help="Show full symptoms and solutions")
    p_explain.add_argument("--index-path", help="Path to local soroban-error-index directory")
    
    # inspect (tx hash)
    p_inspect = subparsers.add_parser("inspect", help="Inspect an on-chain transaction by hash and diagnose failure traces")
    p_inspect.add_argument("tx_hash", help="Transaction hash (hex string)")
    p_inspect.add_argument("--export-md", help="Export inspection diagnosis as Markdown file")
    p_inspect.add_argument("--export-json", help="Export inspection report as JSON file")
    
    # batch-inspect (multi-tx diagnostics)
    p_batch = subparsers.add_parser("batch-inspect", help="Run multi-transaction diagnostics from a JSON dataset or hash list")
    p_batch.add_argument("hashes", nargs="*", help="Transaction hashes to inspect")
    p_batch.add_argument("-f", "--file", help="Path to JSON file containing list of transaction hashes")
    p_batch.add_argument("--limit", type=int, help="Maximum number of transactions to inspect")
    p_batch.add_argument("--export-md", help="Export batch diagnostic report as Markdown file")
    p_batch.add_argument("--export-json", help="Export batch diagnostic report as JSON file")
    
    # simulate (xdr pre-flight)
    p_simulate = subparsers.add_parser("simulate", help="Run pre-flight simulation for transaction envelope XDR")
    p_simulate.add_argument("xdr", help="Base64 encoded transaction envelope XDR")
    p_simulate.add_argument("--leeway", type=int, help="Optional CPU instruction leeway")
    p_simulate.add_argument("--export-md", help="Export simulation analysis as Markdown file")
    p_simulate.add_argument("--export-json", help="Export simulation report as JSON file")
    
    # profile (resource gas flamegraph)
    p_prof = subparsers.add_parser("profile", help="Profile CPU instructions, WASM memory, and storage footprints with visual gauges")
    p_prof.add_argument("xdr", help="Base64 encoded transaction envelope XDR")

    # lint (contract static analysis)
    p_lint = subparsers.add_parser("lint", help="Static analysis scanner for Soroban smart contracts (.rs)")
    p_lint.add_argument("file", help="Path to Rust smart contract source file")

    # generate-test (rust unit test fixture generator)
    p_gentest = subparsers.add_parser("generate-test", help="Generate #[test] Rust unit test fixtures for catalog errors")
    p_gentest.add_argument("error_id", help="Catalog error ID")
    p_gentest.add_argument("--export-rs", help="Export test code to a Rust file")

    # health (rpc diagnostics)
    p_health = subparsers.add_parser("health", help="Check latency and health across Stellar & Soroban RPC endpoints")

    # auth-check (contract auth tree validator)
    p_auth = subparsers.add_parser("auth-check", help="Simulate and validate contract invocation authorization trees")
    p_auth.add_argument("xdr", help="Base64 encoded transaction envelope XDR to validate")
    p_auth.add_argument("--export-json", help="Export authorization tree diagnosis as JSON file")
    
    # fix (auto-fix snippet generator)
    p_fix = subparsers.add_parser("fix", help="Generate idiomatic Rust/Soroban remediation code snippets for catalog errors")
    p_fix.add_argument("error_id", help="Error catalog ID (e.g. arith-error, require-auth-missing)")
    p_fix.add_argument("--export-rs", help="Export remediation code snippet directly to a Rust file (.rs)")
    
    # decode (xdr decoder)
    p_decode = subparsers.add_parser("decode", help="Decode base64 Soroban DiagnosticEvent XDR")
    p_decode.add_argument("xdr", help="Base64 encoded DiagnosticEvent XDR string")
    
    # watch (live contract stream)
    p_watch = subparsers.add_parser("watch", help="Stream and monitor live contract events and traps")
    p_watch.add_argument("-c", "--contract", help="Contract ID to filter events")
    p_watch.add_argument("--interval", type=float, default=3.0, help="Polling interval in seconds")
    p_watch.add_argument("--count", type=int, default=None, help="Maximum number of polling iterations")
    
    # storage (state & TTL audit)
    p_storage = subparsers.add_parser("storage", help="Audit contract storage keys and TTL expiration health")
    p_storage.add_argument("-c", "--contract", required=True, help="Contract ID")
    p_storage.add_argument("-k", "--keys", nargs="*", help="Storage key XDR strings to inspect")
    p_storage.add_argument("--export-md", help="Export storage report as Markdown file")
    p_storage.add_argument("--export-json", help="Export storage report as JSON file")

    # If first arg is not a known subcommand and doesn't start with '-', default to 'explain'
    known_cmds = ["explain", "inspect", "batch-inspect", "simulate", "profile", "lint", "generate-test", "health", "auth-check", "fix", "decode", "watch", "storage", "-h", "--help", "--network", "--rpc-url", "--json"]
    raw_args = sys.argv[1:]
    if raw_args and raw_args[0] not in known_cmds:
        raw_args = ["explain"] + raw_args
        
    args = parser.parse_args(raw_args)
    
    # Initialize RPC client if needed
    rpc_target = args.rpc_url if args.rpc_url else args.network
    client = SorobanRpcClient(network_or_url=rpc_target)
    
    if args.subcommand == "inspect":
        handle_inspect(args, client)
    elif args.subcommand == "batch-inspect":
        handle_batch_inspect(args, client)
    elif args.subcommand == "simulate":
        handle_simulate(args, client)
    elif args.subcommand == "profile":
        handle_profile(args, client)
    elif args.subcommand == "lint":
        handle_lint(args, client)
    elif args.subcommand == "generate-test":
        handle_generate_test(args, client)
    elif args.subcommand == "health":
        handle_health(args, client)
    elif args.subcommand == "auth-check":
        handle_auth_check(args, client)
    elif args.subcommand == "fix":
        handle_fix(args, client)
    elif args.subcommand == "decode":
        handle_decode(args, client)
    elif args.subcommand == "watch":
        handle_watch(args, client)
    elif args.subcommand == "storage":
        handle_storage(args, client)
    else:
        # Default to explain
        if not hasattr(args, "query"):
            args.query = ""
            args.category = None
            args.verified = False
            args.rank = False
            args.detailed = False
            args.index_path = None
        handle_explain(args, client)

if __name__ == "__main__":
    main()
