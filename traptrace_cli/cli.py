"""
Main entry point for TrapTrace CLI / soroban-explain.
"""

import sys
import argparse
import json
from traptrace_cli.data import load_entries
from traptrace_cli.search_engine import search_errors
from traptrace_cli.formatter import render_entry_terminal, BOLD, RESET, TEAL

def main():
    parser = argparse.ArgumentParser(
        prog="soroban-explain",
        description="TrapTrace CLI: Instant error lookup and diagnostic tool for Stellar Soroban smart contracts."
    )
    
    parser.add_argument("query", nargs="?", default="", help="Error string, code, or keyword to explain")
    parser.add_argument("-c", "--category", choices=["host-error", "cli-error", "rpc-error", "sdk-error"], help="Filter by category")
    parser.add_argument("-v", "--verified", action="store_true", help="Show verified entries only")
    parser.add_argument("-d", "--detailed", action="store_true", help="Show full detailed symptoms and solutions")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--index-path", help="Path to local soroban-error-index directory")
    
    args = parser.parse_args()
    
    entries = load_entries(custom_dir=args.index_path)
    results = search_errors(entries, query=args.query, category=args.category, verified_only=args.verified)
    
    if args.json:
        print(json.dumps(results, indent=2))
        sys.exit(0)
        
    if not results:
        print(f"\n❌ No matching Soroban error entries found for query: '{args.query}'\n")
        sys.exit(1)
        
    print(f"\n{TEAL}{BOLD}⚡ TrapTrace Soroban Error Diagnostics{RESET}\n")
    print(f"Found {len(results)} matching error catalog entries:\n")
    
    for idx, entry in enumerate(results, 1):
        print(f"{idx}. " + render_entry_terminal(entry, detailed=args.detailed or len(results) == 1))
        print()

if __name__ == "__main__":
    main()
