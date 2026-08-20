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
    verified_only: bool = False,
    include_scores: bool = False
) -> List[Dict[str, Any]]:
    results = []
    
    query = (query or "").strip()
    
    for entry in entries:
        if category and entry.get("category") != category:
            continue
        if verified_only and not entry.get("verified", False):
            continue
            
        if not query:
            entry_copy = dict(entry)
            if include_scores:
                entry_copy["_score"] = 1.0
            results.append((entry_copy, 1.0))
            continue
            
        score = calculate_match_score(entry, query)
        if score > 0:
            entry_copy = dict(entry)
            if include_scores:
                entry_copy["_score"] = score
            results.append((entry_copy, score))
            
    # Sort by relevance score descending
    results.sort(key=lambda x: x[1], reverse=True)
    return [r[0] for r in results]

def calculate_match_score(entry: Dict[str, Any], query: str) -> float:
    score = 0.0
    original_query = query.strip()
    q = original_query.lower()
    if not q:
        return 1.0
    
    id_str = str(entry.get("id", "")).lower()
    title = str(entry.get("title", "")).lower()
    code = str(entry.get("error_code", "")).lower()
    summary = str(entry.get("summary", "")).lower()
    symptoms = str(entry.get("symptoms", "")).lower()
    solutions = str(entry.get("solutions", "")).lower()
    tags = [t.lower() for t in entry.get("tags", [])]
    body = str(entry.get("body", "")).lower()

    # 1. Exact full-match bonus
    if q == id_str or q == code:
        score += 50.0
    elif q in id_str:
        score += 30.0
    elif q in code:
        score += 25.0
        
    if q in title:
        score += 20.0
    if any(q in tag for tag in tags):
        score += 15.0
    if q in summary:
        score += 10.0
    if q in symptoms:
        score += 8.0
    if q in solutions or q in body:
        score += 5.0

    # 2. Tokenized search with CamelCase / PascalCase sub-word decomposition
    raw_tokens = [t for t in re.split(r"[\s\:\(\)\_\-\,\#\.\/\@]+", original_query) if t]
    extracted_tokens = set()
    for tok in raw_tokens:
        if len(tok) > 2:
            extracted_tokens.add(tok.lower())
        camel_parts = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\W|$)|\d+', tok)
        for cp in camel_parts:
            if len(cp) > 2:
                extracted_tokens.add(cp.lower())

    for tok in extracted_tokens:
        matched_tok = False
        id_words = set(id_str.split("-"))
        if tok in id_words:
            score += 15.0
            matched_tok = True
        elif tok in id_str:
            score += 10.0
            matched_tok = True

        if tok in code:
            score += 10.0
            matched_tok = True
        if tok in title:
            score += 8.0
            matched_tok = True
        if any(tok == tag for tag in tags):
            score += 10.0
            matched_tok = True
        elif any(tok in tag for tag in tags):
            score += 6.0
            matched_tok = True
        if tok in summary:
            score += 4.0
            matched_tok = True
        if tok in symptoms:
            score += 3.0
            matched_tok = True
        if tok in solutions or tok in body:
            score += 2.0
            matched_tok = True
            
        # 3. Typo-tolerant fuzzy matching for tokens that didn't match directly
        if not matched_tok and len(tok) >= 4:
            for word in re.split(r"[\s\_\-]+", f"{id_str} {title}"):
                if len(word) >= 4:
                    common = set(tok) & set(word)
                    if len(common) >= len(tok) - 1:
                        score += 3.5
                        break
        
    return score
