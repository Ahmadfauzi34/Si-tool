"""
Cache Invalidation & Key Collision Auditor
Schema Version: 1.0.0

Mendeteksi pola implementasi cache yang berpotensi menyebabkan:
- Cache key tidak deterministik (Date.now, Math.random, object reference)
- Unbounded cache tanpa eviction policy
- Missing TTL / expiration mechanism
- Key collision karena string concatenation tanpa delimiter
- Object reference sebagai cache key (identity comparison)

Output bersifat informational dan tidak memberikan rekomendasi perubahan.
"""

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "1.0.0"

SOURCE_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")

DEFAULT_IGNORE_DIRS = {
    "node_modules", ".git", "dist", ".angular",
    ".Jules", "coverage", ".next", "out"
}


def _normalize_path(value: str) -> str:
    normalized = os.path.normpath(value).replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _is_source_file(filename: str) -> bool:
    return filename.endswith(SOURCE_EXTENSIONS) and not filename.endswith(".d.ts")


def _strip_comments(content: str) -> str:
    content = re.sub(r"//.*$", "", content, flags=re.MULTILINE)
    content = re.sub(r"/\*[\s\S]*?\*/", "", content)
    return content


def _strip_strings(content: str) -> str:
    content = re.sub(r"'[^']*'", "''", content)
    content = re.sub(r'"[^"]*"', '""', content)
    content = re.sub(r"`[^`]*`", "``", content)
    return content


def detect_nondeterministic_cache_key(content: str, file_path: str) -> List[Dict[str, Any]]:
    """Detect cache keys that use non-deterministic values."""
    findings = []
    lines = content.split("\n")
    
    # Patterns that indicate cache operations
    cache_op_regex = re.compile(
        r"(?:\.set\s*\(|\.get\s*\(|\.has\s*\(|\.delete\s*\()"
    )
    
    # Non-deterministic value patterns
    nondeterministic_patterns = [
        (re.compile(r"Date\.now\s*\(\)"), "Date.now()", "Timestamp-based key changes every millisecond"),
        (re.compile(r"Math\.random\s*\(\)"), "Math.random()", "Random-based key never produces cache hits"),
        (re.compile(r"new\s+(?:Object|Array)\s*\(\s*\)"), "new Object/Array()", "Object identity as key uses reference comparison"),
        (re.compile(r"crypto\.randomUUID\s*\(\)"), "randomUUID()", "UUID-based key never produces cache hits"),
        (re.compile(r"uuid\s*\(\s*\)"), "uuid()", "UUID-based key never produces cache hits"),
    ]
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Only check lines that look like cache operations or key construction
        is_cache_context = (
            cache_op_regex.search(stripped) or
            "key" in stripped.lower() or
            "cache" in stripped.lower()
        )
        
        if not is_cache_context:
            continue
        
        for pattern, value_name, description in nondeterministic_patterns:
            if pattern.search(stripped):
                findings.append({
                    "file": file_path,
                    "type": "nondeterministic_cache_key",
                    "severity": "high",
                    "line": i + 1,
                    "value_used": value_name,
                    "content": stripped,
                    "description": f"{value_name} used in cache key context: {description}"
                })
    
    return findings


def detect_unbounded_cache(content: str, file_path: str) -> List[Dict[str, Any]]:
    """Detect Map/Set used as cache without eviction policy or size limit."""
    findings = []
    lines = content.split("\n")
    
    # Detect cache-like Map/Set declarations
    cache_decl_regex = re.compile(
        r"(?:const|let|var|private|public|protected|readonly)?\s*"
        r"(\w*(?:cache|Cache|CACHE|store|Store|pool|Pool|registry|Registry)\w*)\s*"
        r"=\s*new\s+(Map|Set|WeakMap|WeakSet)\s*\("
    )
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        match = cache_decl_regex.search(stripped)
        if match:
            var_name = match.group(1)
            collection_type = match.group(2)
            
            # Check if there's eviction/cleanup logic
            has_eviction = bool(re.search(
                rf"{re.escape(var_name)}\.(?:delete|clear)\s*\(|"
                rf"{re.escape(var_name)}\.size\s*[<>]|"
                rf"(?:maxSize|MAX_SIZE|capacity|CAPACITY|limit|LIMIT|evict|ttl|TTL|expire)",
                content,
                re.IGNORECASE
            ))
            
            if not has_eviction and collection_type in ("Map", "Set"):
                findings.append({
                    "file": file_path,
                    "type": "unbounded_cache",
                    "severity": "high",
                    "line": i + 1,
                    "variable": var_name,
                    "collection_type": collection_type,
                    "content": stripped,
                    "description": f"new {collection_type}() '{var_name}' appears to be a cache without eviction policy or size limit"
                })
    
    return findings


def detect_missing_ttl(content: str, file_path: str) -> List[Dict[str, Any]]:
    """Detect cache.set() calls without any TTL/expiration mechanism."""
    findings = []
    lines = content.split("\n")
    
    cache_set_regex = re.compile(r"(\w*(?:cache|Cache|CACHE)\w*)\.set\s*\(")
    
    # Check if file has any TTL mechanism
    has_ttl_mechanism = bool(re.search(
        r"(?:ttl|TTL|expire|expiry|expiration|maxAge|max_age|timeToLive|"
        r"setTimeout.*(?:delete|remove|clear|evict)|"
        r"setInterval.*(?:delete|remove|clear|evict|cleanup))",
        content,
        re.IGNORECASE
    ))
    
    if has_ttl_mechanism:
        return findings  # File has TTL mechanism, skip
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        match = cache_set_regex.search(stripped)
        if match:
            cache_var = match.group(1)
            findings.append({
                "file": file_path,
                "type": "missing_ttl",
                "severity": "medium",
                "line": i + 1,
                "variable": cache_var,
                "content": stripped,
                "description": f"cache.set() on '{cache_var}' without TTL/expiration mechanism in this file"
            })
    
    return findings


def detect_key_collision_risk(content: str, file_path: str) -> List[Dict[str, Any]]:
    """Detect string concatenation for cache keys without proper delimiter."""
    findings = []
    lines = content.split("\n")
    
    # Detect key construction via concatenation in cache context
    concat_key_regex = re.compile(
        r"(?:key|Key|cacheKey|cache_key)\s*=\s*"
        r"[\w.'\"\[\]]+\s*\+\s*[\w.'\"\[\]]+"
    )
    
    # Also detect template literals without clear delimiter
    template_key_regex = re.compile(
        r"(?:key|Key|cacheKey|cache_key)\s*=\s*`\$\{[^}]+\}\$\{[^}]+\}`"
    )
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        concat_match = concat_key_regex.search(stripped)
        if concat_match:
            # Check if there's a clear delimiter (like ':', '-', '|', '_')
            has_delimiter = bool(re.search(
                r"['\"][\-:_|.]+['\"]", stripped
            ))
            
            if not has_delimiter:
                findings.append({
                    "file": file_path,
                    "type": "key_collision_risk",
                    "severity": "medium",
                    "line": i + 1,
                    "content": stripped,
                    "description": "Cache key constructed via string concatenation without clear delimiter (collision risk)"
                })
        
        template_match = template_key_regex.search(stripped)
        if template_match:
            # Check if template has delimiter between interpolations
            has_delimiter = bool(re.search(
                r"\}\s*[\-:_|.]+\s*\$\{", stripped
            ))
            
            if not has_delimiter:
                findings.append({
                    "file": file_path,
                    "type": "key_collision_risk",
                    "severity": "medium",
                    "line": i + 1,
                    "content": stripped,
                    "description": "Cache key template literal without delimiter between interpolations (collision risk)"
                })
    
    return findings


def detect_object_as_cache_key(content: str, file_path: str) -> List[Dict[str, Any]]:
    """Detect object/array literals being passed as cache keys."""
    findings = []
    lines = content.split("\n")
    
    # Detect .set({ or .set([ patterns on cache/map/store variables
    cache_set_obj_regex = re.compile(
        r"(\w*(?:cache|Cache|CACHE|store|Store|pool|Pool|map|Map|registry|Registry)\w*)"
        r"\.set\s*\(\s*(?:\{|\[)"
    )
    # Detect .get({ or .get([ patterns on cache/map/store variables
    cache_get_obj_regex = re.compile(
        r"(\w*(?:cache|Cache|CACHE|store|Store|pool|Pool|map|Map|registry|Registry)\w*)"
        r"\.get\s*\(\s*(?:\{|\[)"
    )
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        if cache_set_obj_regex.search(stripped):
            findings.append({
                "file": file_path,
                "type": "object_as_cache_key",
                "severity": "high",
                "line": i + 1,
                "content": stripped,
                "description": "Object/array literal passed as cache key (identity comparison, never matches different instances)"
            })
        
        if cache_get_obj_regex.search(stripped):
            findings.append({
                "file": file_path,
                "type": "object_as_cache_key",
                "severity": "high",
                "line": i + 1,
                "content": stripped,
                "description": "Object/array literal passed to cache.get() (identity comparison, will miss for different instances)"
            })
    
    return findings


def analyze_file(file_path: str) -> Dict[str, Any]:
    """Analyze a single file for cache anti-patterns."""
    path_norm = _normalize_path(file_path)
    
    result = {
        "schema_version": SCHEMA_VERSION,
        "file": path_norm,
        "exists": False,
        "error": None,
        "findings": [],
        "summary": {
            "total_findings": 0,
            "by_type": {
                "nondeterministic_cache_key": 0,
                "unbounded_cache": 0,
                "missing_ttl": 0,
                "key_collision_risk": 0,
                "object_as_cache_key": 0
            },
            "by_severity": {
                "high": 0,
                "medium": 0,
                "low": 0
            }
        }
    }
    
    if not os.path.isfile(path_norm):
        result["error"] = "file_not_found"
        return result
    
    try:
        with open(path_norm, "r", encoding="utf-8", errors="ignore") as f:
            raw_content = f.read()
    except Exception as exc:
        result["error"] = f"read_error: {exc}"
        return result
    
    result["exists"] = True
    
    # Strip comments and strings
    content = _strip_comments(raw_content)
    content = _strip_strings(content)
    
    # Run all detections
    findings = []
    findings.extend(detect_nondeterministic_cache_key(content, path_norm))
    findings.extend(detect_unbounded_cache(content, path_norm))
    findings.extend(detect_missing_ttl(content, path_norm))
    findings.extend(detect_key_collision_risk(content, path_norm))
    findings.extend(detect_object_as_cache_key(content, path_norm))
    
    # Sort by severity then line
    severity_order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda x: (severity_order.get(x.get("severity", "low"), 3), x.get("line", 0)))
    
    result["findings"] = findings
    
    # Build summary
    result["summary"]["total_findings"] = len(findings)
    
    for f in findings:
        ftype = f.get("type", "unknown")
        if ftype in result["summary"]["by_type"]:
            result["summary"]["by_type"][ftype] += 1
        
        severity = f.get("severity", "low")
        if severity in result["summary"]["by_severity"]:
            result["summary"]["by_severity"][severity] += 1
    
    return result


def scan_directory_for_cache_issues(
    path: str = ".",
    ignore_dirs: Optional[set] = None
) -> Dict[str, Any]:
    """Scan a directory for cache anti-patterns."""
    if ignore_dirs is None:
        ignore_dirs = set(DEFAULT_IGNORE_DIRS)
    
    all_findings = []
    files_scanned = 0
    files_with_issues = 0
    
    for root, dirs, files in os.walk(path):
        dirs[:] = sorted([d for d in dirs if d not in ignore_dirs and not d.startswith(".")])
        
        for file in sorted(files):
            if not _is_source_file(file):
                continue
            
            full_path = _normalize_path(os.path.join(root, file))
            result = analyze_file(full_path)
            
            if result["exists"]:
                files_scanned += 1
                
                if result["findings"]:
                    files_with_issues += 1
                    all_findings.extend(result["findings"])
    
    # Sort by severity then file then line
    severity_order = {"high": 0, "medium": 1, "low": 2}
    all_findings.sort(key=lambda x: (severity_order.get(x.get("severity", "low"), 3), x.get("file", ""), x.get("line", 0)))
    
    return {
        "schema_version": SCHEMA_VERSION,
        "scan_root": _normalize_path(path),
        "files_scanned": files_scanned,
        "files_with_issues": files_with_issues,
        "total_findings": len(all_findings),
        "findings": all_findings,
        "summary": {
            "by_type": {
                "nondeterministic_cache_key": sum(1 for f in all_findings if f["type"] == "nondeterministic_cache_key"),
                "unbounded_cache": sum(1 for f in all_findings if f["type"] == "unbounded_cache"),
                "missing_ttl": sum(1 for f in all_findings if f["type"] == "missing_ttl"),
                "key_collision_risk": sum(1 for f in all_findings if f["type"] == "key_collision_risk"),
                "object_as_cache_key": sum(1 for f in all_findings if f["type"] == "object_as_cache_key"),
            },
            "by_severity": {
                "high": sum(1 for f in all_findings if f.get("severity") == "high"),
                "medium": sum(1 for f in all_findings if f.get("severity") == "medium"),
                "low": sum(1 for f in all_findings if f.get("severity") == "low"),
            }
        }
    }


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "scan":
        root = sys.argv[2] if len(sys.argv) > 2 else "."
        print(json.dumps(scan_directory_for_cache_issues(root), indent=2))
    elif len(sys.argv) > 1:
        file_p = sys.argv[1]
        print(json.dumps(analyze_file(file_p), indent=2))
    else:
        print(json.dumps({
            "tool": "cache_auditor",
            "schema_version": SCHEMA_VERSION,
            "usage": {
                "analyze_file": "python3 cache_auditor.py <file_path>",
                "scan_directory": "python3 cache_auditor.py scan [root_path]"
            }
        }, indent=2))
