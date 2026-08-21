"""
Terminal User Interface (TUI) components and colored gauge meters for TrapTrace CLI.
Provides ANSI progress bars, resource consumption gauges, and formatted status boxes.
"""

# ANSI Color Codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
TEAL = "\033[38;2;47;169;140m"
AMBER = "\033[38;2;226;152;75m"

BG_RED = "\033[41m"
BG_GREEN = "\033[42m"
BG_YELLOW = "\033[43m"
BG_DARK = "\033[40m"

# Soroban Protocol Limits (Protocol 21)
DEFAULT_MAX_CPU_INSTRUCTIONS = 100_000_000
DEFAULT_MAX_MEMORY_BYTES = 40 * 1024 * 1024  # 40 MB
DEFAULT_MAX_STORAGE_BYTES = 64 * 1024         # 64 KB per entry

def render_meter_bar(
    current: int,
    maximum: int,
    width: int = 24,
    warn_pct: float = 0.70,
    crit_pct: float = 0.90
) -> str:
    """Render an ANSI colored horizontal meter bar with filled and empty blocks."""
    if maximum <= 0:
        pct = 0.0
    else:
        pct = min(max(current / maximum, 0.0), 1.0)
        
    filled_len = int(round(width * pct))
    empty_len = width - filled_len
    
    if pct >= crit_pct:
        bar_color = RED
    elif pct >= warn_pct:
        bar_color = YELLOW
    else:
        bar_color = GREEN
        
    bar = f"{bar_color}{'█' * filled_len}{DIM}{'░' * empty_len}{RESET}"
    return bar

def render_gauge(
    label: str,
    current: int,
    maximum: int,
    unit: str = "",
    width: int = 22,
    warn_pct: float = 0.70,
    crit_pct: float = 0.90
) -> str:
    """
    Render a single labeled resource gauge.
    Example: CPU Instructions [████████░░░░░░░░] 48.5% (4.85M / 10.00M)
    """
    if maximum <= 0:
        pct = 0.0
    else:
        pct = (current / maximum) * 100.0
        
    bar = render_meter_bar(current, maximum, width=width, warn_pct=warn_pct, crit_pct=crit_pct)
    
    # Format numbers with human readable units
    if unit == "instructions":
        cur_str = f"{current / 1_000_000:.2f}M" if current >= 1_000_000 else f"{current:,}"
        max_str = f"{maximum / 1_000_000:.2f}M"
    elif unit == "bytes":
        cur_str = f"{current / (1024 * 1024):.2f} MB" if current >= 1024 * 1024 else (f"{current / 1024:.1f} KB" if current >= 1024 else f"{current} B")
        max_str = f"{maximum / (1024 * 1024):.2f} MB" if maximum >= 1024 * 1024 else f"{maximum / 1024:.1f} KB"
    else:
        cur_str = f"{current:,}"
        max_str = f"{maximum:,}"
        
    pct_color = RED if pct >= crit_pct * 100 else (YELLOW if pct >= warn_pct * 100 else GREEN)
    status_tag = ""
    if pct >= 100.0:
        status_tag = f" {BG_RED}{WHITE}{BOLD} EXCEEDED {RESET}"
    elif pct >= crit_pct * 100:
        status_tag = f" {YELLOW}{BOLD}[HIGH LOAD]{RESET}"

    return f"  {BOLD}{label:<18}{RESET} [{bar}] {pct_color}{pct:>5.1f}%{RESET} ({cur_str} / {max_str}){status_tag}"

def render_resource_dashboard(
    cpu_insns: int,
    max_cpu: int = DEFAULT_MAX_CPU_INSTRUCTIONS,
    mem_bytes: int = 0,
    max_mem: int = DEFAULT_MAX_MEMORY_BYTES,
    storage_bytes: int = 0,
    max_storage: int = DEFAULT_MAX_STORAGE_BYTES
) -> str:
    """Render a comprehensive multi-gauge resource consumption dashboard."""
    lines = [
        f"{CYAN}{BOLD}┌─ Soroban Resource Consumption Meter ─────────────────────────────┐{RESET}",
        render_gauge("CPU Instructions", cpu_insns, max_cpu, unit="instructions"),
        render_gauge("WASM Memory", mem_bytes, max_mem, unit="bytes"),
    ]
    if storage_bytes > 0:
        lines.append(render_gauge("Storage Entry", storage_bytes, max_storage, unit="bytes"))
    lines.append(f"{CYAN}{BOLD}└──────────────────────────────────────────────────────────────────┘{RESET}")
    return "\n".join(lines)

def render_box(title: str, content_lines: list, color: str = CYAN) -> str:
    """Render content inside a stylized ANSI box."""
    max_len = max([len(title)] + [len(line) for line in content_lines] + [50])
    border_len = max_len + 4
    
    out = [f"{color}{BOLD}┌─ {title} " + ("─" * (border_len - len(title) - 5)) + f"┐{RESET}"]
    for line in content_lines:
        out.append(f"{color}│{RESET}  {line:<{max_len}}  {color}│{RESET}")
    out.append(f"{color}└" + ("─" * (border_len - 2)) + f"┘{RESET}")
    return "\n".join(out)
