"""
Shell Auto-Completion Generator for TrapTrace CLI.
Generates autocomplete definitions for Bash, Zsh, and Fish shells.
"""

BASH_COMPLETION = """
_traptrace_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    opts="explain inspect batch-inspect simulate auth-check fix diff abi webhook decode watch storage --network --rpc-url --json --help"

    case "${prev}" in
        --network)
            COMPREPLY=( $(compgen -W "testnet mainnet futurenet local standalone" -- ${cur}) )
            return 0
            ;;
        fix|explain)
            COMPREPLY=( $(compgen -W "arith-error require-auth-missing auth-invalid-signature entry-archived-ttl-expired contract-data-size-exceeds-limit wasm-memory-exhausted sub-invocation-user-error wasm-verification-failed crypto-verification-failed invalid-chain-id" -- ${cur}) )
            return 0
            ;;
        *)
            ;;
    esac

    COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
    return 0
}
complete -F _traptrace_completion traptrace
complete -F _traptrace_completion soroban-explain
"""

ZSH_COMPLETION = """
#compdef traptrace soroban-explain

_traptrace() {
    local -a commands
    commands=(
        'explain:Search error codes and keywords'
        'inspect:Inspect on-chain transaction by hash'
        'batch-inspect:Run multi-transaction diagnostics'
        'simulate:Pre-flight simulation with resource meters'
        'auth-check:Validate contract authorization trees'
        'fix:Generate remediation code snippets'
        'diff:Compare resource costs between transactions'
        'abi:Inspect contract WASM ABI and specifications'
        'watch:Stream live contract events and traps'
        'storage:Audit storage keys and TTL health'
    )
    _describe 'command' commands
}
_traptrace "$@"
"""

def generate_completion(shell: str = "bash") -> str:
    """Generate shell completion script."""
    sh = shell.lower().strip()
    if sh == "zsh":
        return ZSH_COMPLETION.strip()
    return BASH_COMPLETION.strip()
