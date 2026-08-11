"""
GC Pressure & Memory Leak Analyzer
Schema Version: 1.0.0

Mendeteksi pola kode TypeScript/JavaScript yang berpotensi menyebabkan:
- High allocation rate (objek/array/string di loop)
- JSON.parse/stringify di hot path
- Event listener leak (add tanpa remove)
- Timer leak (setInterval/setTimeout tanpa clear)
- Closure creation berulang di loop
- Unbounded collection growth (Map/Set tanpa batas)

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


def _is_in_loop(lines: List[str], target_line_idx: int) -> bool:
    """Check if a line is inside a loop by counting braces upward."""
    brace_count = 0
    for i in range(target_line_idx, -1, -1):
        line = lines[i].strip()
        brace_count += line.count("}") - line.count("{")
        if re.match(r"^\s*(for\s*\(|for\s+(?:const|let|var)\s+\w+\s+(?:of|in)|while\s*\()", line):
            if brace_count <= 0:
                return True
    return False


def detect_allocation_in_loop(content: str, file_path: str) -> List[Dict[str, Any]]:
    """Detect object/array/string allocation inside loops."""
    findings = []
    lines = content.split("\n")
    
    alloc_patterns = [
        (re.compile(r"(?:const|let|var)\s+\w+\s*=\s*\{"), "object_literal", "Object literal created"),
        (re.compile(r"(?:const|let|var)\s+\w+\s*=\s*\["), "array_literal", "Array literal created"),
        (re.compile(r"(?:const|let|var)\s+\w+\s*=\s*new\s+(?:Object|Array|Map|Set|Date|RegExp)\s*\("), "new_builtin", "New built-in instance created"),
        (re.compile(r"\.concat\s*\("), "string_concat", "String/array concat (creates new instance)"),
        (re.compile(r"\.slice\s*\("), "slice", ".slice() creates a new array/string copy"),
        (re.compile(r"\.split\s*\("), "split", ".split() creates a new array"),
        (re.compile(r"\[\.\.\."), "spread", "Spread operator creates new array/object"),
        (re.compile(r"Object\.assign\s*\(\s*\{\s*\}"), "object_assign", "Object.assign({}, ...) creates new object"),
    ]
    
    for i, line in enumerate(lines):
        if not _is_in_loop(lines, i):
            continue
        
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("*"):
            continue
        
        for pattern, alloc_type, desc in alloc_patterns:
            if pattern.search(stripped):
                findings.append({
                    "file": file_path,
                    "type": "allocation_in_loop",
                    "subtype": alloc_type,
                    "severity": "medium",
                    "line": i + 1,
                    "content": stripped,
                    "description": f"{desc} inside loop (line {i+1})"
                })
                break
    
    return findings


def detect_json_in_loop(content: str, file_path: str) -> List[Dict[str, Any]]:
    """Detect JSON.parse/stringify usage inside loops."""
    findings = []
    lines = content.split("\n")
    
    json_parse_regex = re.compile(r"JSON\.parse\s*\(")
    json_stringify_regex = re.compile(r"JSON\.stringify\s*\(")
    
    for i, line in enumerate(lines):
        if not _is_in_loop(lines, i):
            continue
        
        stripped = line.strip()
        
        if json_parse_regex.search(stripped):
            findings.append({
                "file": file_path,
                "type": "json_in_loop",
                "subtype": "JSON.parse",
                "severity": "high",
                "line": i + 1,
                "content": stripped,
                "description": f"JSON.parse inside loop creates large temporary objects (line {i+1})"
            })
        
        if json_stringify_regex.search(stripped):
            findings.append({
                "file": file_path,
                "type": "json_in_loop",
                "subtype": "JSON.stringify",
                "severity": "high",
                "line": i + 1,
                "content": stripped,
                "description": f"JSON.stringify inside loop creates large string allocations (line {i+1})"
            })
    
    return findings


def detect_unclosed_event_listener(content: str, file_path: str) -> List[Dict[str, Any]]:
    """Detect addEventListener without corresponding removeEventListener."""
    findings = []
    
    add_regex = re.compile(r"\.addEventListener\s*\(\s*['\"](\w+)['\"]")
    remove_regex = re.compile(r"\.removeEventListener\s*\(\s*['\"](\w+)['\"]")
    
    add_events = set(add_regex.findall(content))
    remove_events = set(remove_regex.findall(content))
    
    unclosed = add_events - remove_events
    
    lines = content.split("\n")
    for event_name in unclosed:
        for i, line in enumerate(lines):
            if f".addEventListener" in line and (f"'{event_name}'" in line or f'"{event_name}"' in line):
                findings.append({
                    "file": file_path,
                    "type": "unclosed_event_listener",
                    "severity": "high",
                    "line": i + 1,
                    "event": event_name,
                    "content": line.strip(),
                    "description": f"addEventListener('{event_name}') without removeEventListener (memory leak)"
                })
                break
    
    return findings


def detect_uncleared_timer(content: str, file_path: str) -> List[Dict[str, Any]]:
    """Detect setInterval/setTimeout without clearInterval/clearTimeout."""
    findings = []
    lines = content.split("\n")
    
    # Track timer variables
    set_interval_regex = re.compile(r"(?:const|let|var)\s+(\w+)\s*=\s*setInterval\s*\(")
    set_timeout_regex = re.compile(r"(?:const|let|var)\s+(\w+)\s*=\s*setTimeout\s*\(")
    
    clear_interval_regex = re.compile(r"clearInterval\s*\(\s*(\w+)\s*\)")
    clear_timeout_regex = re.compile(r"clearTimeout\s*\(\s*(\w+)\s*\)")
    
    interval_vars = set()
    timeout_vars = set()
    cleared_intervals = set()
    cleared_timeouts = set()
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        interval_match = set_interval_regex.search(stripped)
        if interval_match:
            interval_vars.add((interval_match.group(1), i + 1))
        
        timeout_match = set_timeout_regex.search(stripped)
        if timeout_match:
            timeout_vars.add((timeout_match.group(1), i + 1))
        
        clear_interval_match = clear_interval_regex.search(stripped)
        if clear_interval_match:
            cleared_intervals.add(clear_interval_match.group(1))
        
        clear_timeout_match = clear_timeout_regex.search(stripped)
        if clear_timeout_match:
            cleared_timeouts.add(clear_timeout_match.group(1))
    
    # Check for uncleared intervals
    for var_name, line_num in interval_vars:
        if var_name not in cleared_intervals:
            findings.append({
                "file": file_path,
                "type": "uncleared_timer",
                "subtype": "setInterval",
                "severity": "high",
                "line": line_num,
                "variable": var_name,
                "description": f"setInterval assigned to '{var_name}' without clearInterval (timer leak)"
            })
    
    # Check for uncleared timeouts (lower severity, might be one-shot)
    for var_name, line_num in timeout_vars:
        if var_name not in cleared_timeouts:
            findings.append({
                "file": file_path,
                "type": "uncleared_timer",
                "subtype": "setTimeout",
                "severity": "medium",
                "line": line_num,
                "variable": var_name,
                "description": f"setTimeout assigned to '{var_name}' without clearTimeout"
            })
    
    return findings


def detect_closure_in_loop(content: str, file_path: str) -> List[Dict[str, Any]]:
    """Detect arrow function / function expression creation inside loops."""
    findings = []
    lines = content.split("\n")
    
    closure_patterns = [
        re.compile(r"(?:push|add)\s*\(\s*(?:\([^)]*\)|[^)]*)\s*=>"),
        re.compile(r"(?:push|add)\s*\(\s*function\s*\("),
    ]
    
    for i, line in enumerate(lines):
        if not _is_in_loop(lines, i):
            continue
        
        stripped = line.strip()
        
        for pattern in closure_patterns:
            if pattern.search(stripped):
                findings.append({
                    "file": file_path,
                    "type": "closure_in_loop",
                    "severity": "medium",
                    "line": i + 1,
                    "content": stripped,
                    "description": f"Closure/function created inside loop (line {i+1})"
                })
                break
    
    return findings


def detect_unbounded_collection(content: str, file_path: str) -> List[Dict[str, Any]]:
    """Detect Map/Set creation without apparent size limit."""
    findings = []
    lines = content.split("\n")
    
    map_set_regex = re.compile(r"(?:const|let|var|private|public|protected)?\s*(\w+)\s*=\s*new\s+(Map|Set|WeakMap|WeakSet)\s*\(")
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        match = map_set_regex.search(stripped)
        if match:
            var_name = match.group(1)
            collection_type = match.group(2)
            
            # Check if there's a .delete() or size check nearby
            has_cleanup = bool(re.search(
                rf"{re.escape(var_name)}\.(?:delete|clear)\s*\(|{re.escape(var_name)}\.size\s*[<>]",
                content
            ))
            
            if not has_cleanup and collection_type in ("Map", "Set"):
                findings.append({
                    "file": file_path,
                    "type": "unbounded_collection",
                    "severity": "medium",
                    "line": i + 1,
                    "variable": var_name,
                    "collection_type": collection_type,
                    "content": stripped,
                    "description": f"new {collection_type}() '{var_name}' without apparent size limit or cleanup"
                })
    
    return findings


def analyze_file(file_path: str) -> Dict[str, Any]:
    """Analyze a single file for GC pressure patterns."""
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
                "allocation_in_loop": 0,
                "json_in_loop": 0,
                "unclosed_event_listener": 0,
                "uncleared_timer": 0,
                "closure_in_loop": 0,
                "unbounded_collection": 0
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
    findings.extend(detect_allocation_in_loop(content, path_norm))
    findings.extend(detect_json_in_loop(content, path_norm))
    findings.extend(detect_unclosed_event_listener(content, path_norm))
    findings.extend(detect_uncleared_timer(content, path_norm))
    findings.extend(detect_closure_in_loop(content, path_norm))
    findings.extend(detect_unbounded_collection(content, path_norm))
    
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


def scan_directory_for_gc_pressure(
    path: str = ".",
    ignore_dirs: Optional[set] = None
) -> Dict[str, Any]:
    """Scan a directory for GC pressure patterns."""
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
                "allocation_in_loop": sum(1 for f in all_findings if f["type"] == "allocation_in_loop"),
                "json_in_loop": sum(1 for f in all_findings if f["type"] == "json_in_loop"),
                "unclosed_event_listener": sum(1 for f in all_findings if f["type"] == "unclosed_event_listener"),
                "uncleared_timer": sum(1 for f in all_findings if f["type"] == "uncleared_timer"),
                "closure_in_loop": sum(1 for f in all_findings if f["type"] == "closure_in_loop"),
                "unbounded_collection": sum(1 for f in all_findings if f["type"] == "unbounded_collection"),
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
        print(json.dumps(scan_directory_for_gc_pressure(root), indent=2))
    elif len(sys.argv) > 1:
        file_p = sys.argv[1]
        print(json.dumps(analyze_file(file_p), indent=2))
    else:
        print(json.dumps({
            "tool": "gc_pressure_analyzer",
            "schema_version": SCHEMA_VERSION,
            "usage": {
                "analyze_file": "python3 gc_pressure_analyzer.py <file_path>",
                "scan_directory": "python3 gc_pressure_analyzer.py scan [root_path]"
            }
        }, indent=2))
