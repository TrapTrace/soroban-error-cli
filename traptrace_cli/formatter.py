"""
Terminal formatting and color rendering for TrapTrace CLI.
"""

# ANSI Color codes
BOLD = "\033[1m"
RESET = "\033[0m"
CYAN = "\033[36m"
TEAL = "\033[38;2;47;169;140m"
AMBER = "\033[38;2;226;152;75m"
RED = "\033[31m"
GREEN = "\033[32m"
GRAY = "\033[90m"

def render_entry_terminal(entry, detailed=False):
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
