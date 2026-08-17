"""
Search and ranking logic for TrapTrace CLI.
Supports full-phrase matching, tokenized keyword scoring, and field-weighted ranking.
"""

import re
from typing import List, Dict, Any, Optional

def search_errors(
    entries: List[Dict[str, Any]],
    query: str = "",
    category: Optional[str] = None,
    verified_only: bool = False
) -> List[Dict[str, Any]]:
    results = []
    
    query = (query or "").strip().lower()
    
    for entry in entries:
        if category and entry.get("category") != category:
            continue
        if verified_only and not entry.get("verified", False):
            continue
            
        if not query:
            results.append((entry, 1.0))
            continue
            
        score = calculate_match_score(entry, query)
        if score > 0:
            results.append((entry, score))
            
    # Sort by relevance score descending
    results.sort(key=lambda x: x[1], reverse=True)
    return [r[0] for r in results]

def calculate_match_score(entry: Dict[str, Any], query: str) -> float:
    score = 0.0
    
    id_str = str(entry.get("id", "")).lower()
    title = str(entry.get("title", "")).lower()
    code = str(entry.get("error_code", "")).lower()
    summary = str(entry.get("summary", "")).lower()
    symptoms = str(entry.get("symptoms", "")).lower()
    solutions = str(entry.get("solutions", "")).lower()
    tags = [t.lower() for t in entry.get("tags", [])]
    body = str(entry.get("body", "")).lower()

    # 1. Direct full-query match
    if query in id_str:
        score += 25.0
    if query in code:
        score += 20.0
    if query in title:
        score += 15.0
    if any(query in tag for tag in tags):
        score += 10.0
    if query in summary:
        score += 8.0
    if query in symptoms:
        score += 5.0
    if query in solutions or query in body:
        score += 3.0

    # 2. Tokenized search for multi-word queries
    tokens = [t for t in re.split(r"[\s\:\(\)\_\-\,\#]+", query) if len(t) > 2]
    for tok in tokens:
        if tok in id_str:
            score += 10.0
        if tok in code:
            score += 8.0
        if tok in title:
            score += 6.0
        if any(tok in tag for tag in tags):
            score += 5.0
        if tok in summary:
            score += 3.0
        if tok in symptoms:
            score += 2.0
        if tok in solutions or tok in body:
            score += 1.0
        
    return score
