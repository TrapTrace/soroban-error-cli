"""
Search and ranking logic for TrapTrace CLI.
"""

def search_errors(entries, query="", category=None, verified_only=False):
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

def calculate_match_score(entry, query):
    score = 0.0
    
    id_str = str(entry.get("id", "")).lower()
    title = str(entry.get("title", "")).lower()
    code = str(entry.get("error_code", "")).lower()
    summary = str(entry.get("summary", "")).lower()
    symptoms = str(entry.get("symptoms", "")).lower()
    solutions = str(entry.get("solutions", "")).lower()
    tags = [t.lower() for t in entry.get("tags", [])]
    body = str(entry.get("body", "")).lower()

    if query in id_str:
        score += 10.0
    if query in code:
        score += 8.0
    if query in title:
        score += 6.0
    if any(query in tag for tag in tags):
        score += 5.0
    if query in summary:
        score += 3.0
    if query in symptoms:
        score += 2.0
    if query in solutions or query in body:
        score += 1.0
        
    return score
