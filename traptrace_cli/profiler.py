"""
TrapTrace Resource & Gas Profiler for Soroban Smart Contract Transactions.
Profiles CPU instructions, memory footprint, and storage IO against network protocol limits.
"""

from typing import Dict, Any, Optional

# Soroban Protocol 21 Limit Constants
MAX_CPU_INSTRUCTIONS = 100_000_000
MAX_MEM_BYTES = 41_943_040  # 40 MiB
MAX_READ_BYTES = 200_000
MAX_WRITE_BYTES = 65_536
MAX_READ_ENTRIES = 40
MAX_WRITE_ENTRIES = 25

class GasProfile:
    def __init__(
        self,
        cpu_insns: int = 0,
        mem_bytes: int = 0,
        read_bytes: int = 0,
        write_bytes: int = 0,
        read_entries: int = 0,
        write_entries: int = 0,
        min_resource_fee: int = 0
    ):
        self.cpu_insns = cpu_insns
        self.mem_bytes = mem_bytes
        self.read_bytes = read_bytes
        self.write_bytes = write_bytes
        self.read_entries = read_entries
        self.write_entries = write_entries
        self.min_resource_fee = min_resource_fee

    @property
    def cpu_pct(self) -> float:
        return min(100.0, (self.cpu_insns / MAX_CPU_INSTRUCTIONS) * 100.0)

    @property
    def mem_pct(self) -> float:
        return min(100.0, (self.mem_bytes / MAX_MEM_BYTES) * 100.0)

    @property
    def read_bytes_pct(self) -> float:
        return min(100.0, (self.read_bytes / MAX_READ_BYTES) * 100.0)

    @property
    def write_bytes_pct(self) -> float:
        return min(100.0, (self.write_bytes / MAX_WRITE_BYTES) * 100.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_instructions": {
                "used": self.cpu_insns,
                "limit": MAX_CPU_INSTRUCTIONS,
                "percentage": round(self.cpu_pct, 2),
                "status": "NORMAL" if self.cpu_pct < 70 else ("WARNING" if self.cpu_pct < 90 else "CRITICAL")
            },
            "memory_bytes": {
                "used": self.mem_bytes,
                "limit": MAX_MEM_BYTES,
                "percentage": round(self.mem_pct, 2),
                "status": "NORMAL" if self.mem_pct < 70 else ("WARNING" if self.mem_pct < 90 else "CRITICAL")
            },
            "read_bytes": {
                "used": self.read_bytes,
                "limit": MAX_READ_BYTES,
                "percentage": round(self.read_bytes_pct, 2)
            },
            "write_bytes": {
                "used": self.write_bytes,
                "limit": MAX_WRITE_BYTES,
                "percentage": round(self.write_bytes_pct, 2)
            },
            "read_entries": self.read_entries,
            "write_entries": self.write_entries,
            "min_resource_fee_stroops": self.min_resource_fee,
            "min_resource_fee_xlm": round(self.min_resource_fee / 10_000_000, 7)
        }

def profile_simulation_result(sim_result: Dict[str, Any]) -> GasProfile:
    cost = sim_result.get("cost", {})
    cpu = int(cost.get("cpuInsns", 0))
    mem = int(cost.get("memBytes", 0))
    fee = int(sim_result.get("minResourceFee", 0))

    # Parse footprint if available
    footprint = sim_result.get("transactionData", {}).get("footprint", {})
    read_only = footprint.get("readOnly", [])
    read_write = footprint.get("readWrite", [])

    return GasProfile(
        cpu_insns=cpu,
        mem_bytes=mem,
        read_entries=len(read_only),
        write_entries=len(read_write),
        min_resource_fee=fee
    )

def render_ascii_flamegraph(profile: GasProfile) -> str:
    def make_bar(pct: float, width: int = 30) -> str:
        filled = int(round((pct / 100.0) * width))
        filled = max(0, min(width, filled))
        bar = "█" * filled + "░" * (width - filled)
        return bar

    lines = [
        "┌────────────────────────────────────────────────────────────────────────┐",
        "│                      SOROBAN RESOURCE PROFILE                          │",
        "├────────────────────────────────────────────────────────────────────────┤",
        f"│ CPU Instructions : [{make_bar(profile.cpu_pct)}] {profile.cpu_pct:5.1f}% ({profile.cpu_insns:,} / {MAX_CPU_INSTRUCTIONS:,})",
        f"│ Memory Footprint : [{make_bar(profile.mem_pct)}] {profile.mem_pct:5.1f}% ({profile.mem_bytes:,} / {MAX_MEM_BYTES:,} B)",
        f"│ Min Resource Fee : {profile.min_resource_fee:,} stroops ({profile.min_resource_fee / 10_000_000:.7f} XLM)",
        f"│ Footprint Access : {profile.read_entries} read-only entries | {profile.write_entries} read-write entries",
        "└────────────────────────────────────────────────────────────────────────┘"
    ]
    return "\n".join(lines)
