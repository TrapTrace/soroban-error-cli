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
    BOLD, RESET, TEAL, CYAN, RED
)
from traptrace_cli.rpc_client import SorobanRpcClient
from traptrace_cli.inspector import TransactionInspector
from traptrace_cli.simulator import TransactionSimulator
from traptrace_cli.watcher import ContractEventWatcher
from traptrace_cli.storage_auditor import StorageAuditor
from traptrace_cli.xdr_decoder import decode_diagnostic_event

def handle_explain(args, client: Optional[SorobanRpcClient] = None):
    entries = load_entries(custom_dir=args.index_path)
    results = search_errors(entries, query=args.query, category=args.category, verified_only=args.verified)
    
    if args.json:
        print(json.dumps(results, indent=2))
        return
        
    if not results:
        print(f"\n❌ No matching Soroban error entries found for query: '{args.query}'\n")
        sys.exit(1)
        
    print(f"\n{TEAL}{BOLD}⚡ TrapTrace Soroban Error Diagnostics{RESET}\n")
    print(f"Found {len(results)} matching error catalog entries:\n")
    
    for idx, entry in enumerate(results, 1):
        print(f"{idx}. " + render_entry_terminal(entry, detailed=args.detailed or len(results) == 1))
        print()

def handle_inspect(args, client: SorobanRpcClient):
    inspector = TransactionInspector(rpc_client=client)
    report = inspector.inspect(args.tx_hash)
    
    if args.json:
        print(json.dumps(report, indent=2))
        return
        
    print()
    print(render_inspection_report(report))
    print()

def handle_simulate(args, client: SorobanRpcClient):
    simulator = TransactionSimulator(rpc_client=client)
    report = simulator.simulate(args.xdr, resource_leeway=args.leeway)
    
    if args.json:
        print(json.dumps(report, indent=2))
        return
        
    print()
    print(render_simulation_report(report))
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
    
    if args.json:
        print(json.dumps(report, indent=2))
        return
        
    print()
    print(render_storage_report(report))
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
    p_explain.add_argument("-d", "--detailed", action="store_true", help="Show full symptoms and solutions")
    p_explain.add_argument("--index-path", help="Path to local soroban-error-index directory")
    
    # inspect (tx hash)
    p_inspect = subparsers.add_parser("inspect", help="Inspect an on-chain transaction by hash and diagnose failure traces")
    p_inspect.add_argument("tx_hash", help="Transaction hash (hex string)")
    
    # simulate (xdr pre-flight)
    p_simulate = subparsers.add_parser("simulate", help="Run pre-flight simulation for transaction envelope XDR")
    p_simulate.add_argument("xdr", help="Base64 encoded transaction envelope XDR")
    p_simulate.add_argument("--leeway", type=int, help="Optional CPU instruction leeway")
    
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

    # If first arg is not a known subcommand and doesn't start with '-', default to 'explain'
    raw_args = sys.argv[1:]
    if raw_args and raw_args[0] not in ["explain", "inspect", "simulate", "decode", "watch", "storage", "-h", "--help", "--network", "--rpc-url", "--json"]:
        raw_args = ["explain"] + raw_args
        
    args = parser.parse_args(raw_args)
    
    # Initialize RPC client if needed
    rpc_target = args.rpc_url if args.rpc_url else args.network
    client = SorobanRpcClient(network_or_url=rpc_target)
    
    if args.subcommand == "inspect":
        handle_inspect(args, client)
    elif args.subcommand == "simulate":
        handle_simulate(args, client)
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
            args.detailed = False
            args.index_path = None
        handle_explain(args, client)

if __name__ == "__main__":
    main()
