"""
Async Waterfall Detector
Schema Version: 1.0.0

Mendeteksi pola async anti-pattern yang menyebabkan:
- Sequential await yang bisa diparalelkan
- Await dalam loop tanpa batching
- Sync I/O dalam async context (event-loop blocking)

Output bersifat informational dan tidak memberikan rekomendasi perubahan.
"""

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = "1.0.0"

SOURCE_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")

# Pattern A: Sequential await statements (independent variables)
SEQUENTIAL_AWAIT_REGEX = re.compile(
    r"^\s*(?:const|let|var)\s+(\w+)\s*=\s*await\s+",
    re.MULTILINE
)

# Pattern B: Await inside for/for-of/for-in/while loop
AWAIT_IN_LOOP_REGEX = re.compile(
    r"(?:for\s*\(|for\s+\(|while\s*\()[\s\S]*?await\s+",
    re.MULTILINE
)

# Pattern B more specific: await inside loop body
LOOP_AWAIT_DETAIL_REGEX = re.compile(
    r"(for\s*(?:\(|\s+)(?:const|let|var)?\s*\w+\s+(?:of|in)\s+[\w.]+\s*\{|"
    r"for\s*\([^)]*\)\s*\{|"
    r"while\s*\([^)]*\)\s*\{)"
    r"([\s\S]*?)"
    r"(\})",
    re.MULTILINE
)

AWAIT_INSIDE_REGEX = re.compile(r"await\s+[\w.]+\(")

# Pattern C: Sync I/O methods
SYNC_IO_REGEX = re.compile(
    r"(?:fs|readFileSync|writeFileSync|existsSync|mkdirSync|readdirSync|"
    r"statSync|unlinkSync|rmdirSync|renameSync|copyFileSync|"
    r"child_process\.execSync|child_process\.spawnSync|"
    r"execSync|spawnSync|readFileSync|writeFileSync)\s*\(",
    re.MULTILINE
)

# Async function detection
ASYNC_FUNC_REGEX = re.compile(
    r"(?:async\s+function|async\s+\(|async\s+\w+\s*[=(]|\w+\s*=\s*async)",
    re.MULTILINE
)


def _normalize_path(value: str) -> str:
    normalized = os.path.normpath(value).replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _is_source_file(filename: str) -> bool:
    return filename.endswith(SOURCE_EXTENSIONS) and not filename.endswith(".d.ts")


def _strip_comments(content: str) -> str:
    """Remove single-line and multi-line comments."""
    content = re.sub(r"//.*$", "", content, flags=re.MULTILINE)
    content = re.sub(r"/\*[\s\S]*?\*/", "", content)
    return content


def _strip_strings(content: str) -> str:
    """Remove string literals to avoid false positives."""
    content = re.sub(r"'[^']*'", "''", content)
    content = re.sub(r'"[^"]*"', '""', content)
    content = re.sub(r"`[^`]*`", "``", content)
    return content


def detect_sequential_awaits(content: str, file_path: str) -> List[Dict[str, Any]]:
    """
    Detect consecutive await statements that appear independent.
    Heuristic: 2+ await assignments within 5 lines of each other.
    """
    findings = []
    lines = content.split("\n")
    
    await_lines = []
    for i, line in enumerate(lines):
        match = SEQUENTIAL_AWAIT_REGEX.match(line)
        if match:
            await_lines.append({
                "line": i + 1,
                "variable": match.group(1),
                "content": line.strip()
            })
    
    # Group consecutive awaits (within 3 lines gap)
    if len(await_lines) >= 2:
        groups = []
        current_group = [await_lines[0]]
        
        for i in range(1, len(await_lines)):
            if await_lines[i]["line"] - await_lines[i-1]["line"] <= 3:
                current_group.append(await_lines[i])
            else:
                if len(current_group) >= 2:
                    groups.append(current_group)
                current_group = [await_lines[i]]
        
        if len(current_group) >= 2:
            groups.append(current_group)
        
        for group in groups:
            # Check if group items are dependent (subsequent item uses variable defined in prior item)
            independent_items = [group[0]]
            for i in range(1, len(group)):
                prev_vars = {item["variable"] for item in group[:i]}
                curr_content = group[i]["content"]
                is_dependent = any(
                    re.search(r"\b" + re.escape(v) + r"\b", curr_content)
                    for v in prev_vars
                )
                if not is_dependent:
                    independent_items.append(group[i])
            
            if len(independent_items) >= 2:
                findings.append({
                    "file": file_path,
                    "type": "sequential_await",
                    "severity": "medium",
                    "line_start": independent_items[0]["line"],
                    "line_end": independent_items[-1]["line"],
                    "count": len(independent_items),
                    "variables": [item["variable"] for item in independent_items],
                    "snippet": [item["content"] for item in independent_items],
                    "description": f"{len(independent_items)} sequential await statements detected (lines {independent_items[0]['line']}-{independent_items[-1]['line']})"
                })
    
    return findings


def detect_await_in_loop(content: str, file_path: str) -> List[Dict[str, Any]]:
    """Detect await statements inside loop bodies."""
    findings = []
    lines = content.split("\n")
    
    in_loop = False
    loop_start = 0
    brace_count = 0
    loop_type = ""
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Detect loop start
        if re.match(r"^\s*(for\s*\(|for\s+(?:const|let|var)\s+\w+\s+(?:of|in)|while\s*\()", stripped):
            in_loop = True
            loop_start = i + 1
            brace_count = 0
            if "for" in stripped:
                loop_type = "for"
            else:
                loop_type = "while"
        
        if in_loop:
            brace_count += stripped.count("{") - stripped.count("}")
            
            # Check for await inside loop
            if AWAIT_INSIDE_REGEX.search(stripped) and brace_count > 0:
                findings.append({
                    "file": file_path,
                    "type": "await_in_loop",
                    "severity": "high",
                    "line": i + 1,
                    "loop_start_line": loop_start,
                    "loop_type": loop_type,
                    "content": stripped,
                    "description": f"await inside {loop_type} loop (line {i+1})"
                })
            
            if brace_count <= 0 and i > loop_start:
                in_loop = False
    
    return findings


def detect_sync_io(content: str, file_path: str) -> List[Dict[str, Any]]:
    """Detect synchronous I/O operations."""
    findings = []
    lines = content.split("\n")
    
    for i, line in enumerate(lines):
        match = SYNC_IO_REGEX.search(line)
        if match:
            findings.append({
                "file": file_path,
                "type": "sync_io",
                "severity": "high",
                "line": i + 1,
                "content": line.strip(),
                "sync_method": match.group(0).strip(),
                "description": f"Synchronous I/O operation: {match.group(0).strip()}"
            })
    
    return findings


def analyze_file(file_path: str) -> Dict[str, Any]:
    """Analyze a single file for async anti-patterns."""
    path_norm = _normalize_path(file_path)
    
    result = {
        "schema_version": SCHEMA_VERSION,
        "file": path_norm,
        "exists": False,
        "error": None,
        "is_async_file": False,
        "findings": [],
        "summary": {
            "total_findings": 0,
            "sequential_awaits": 0,
            "await_in_loops": 0,
            "sync_io": 0,
            "severity_counts": {
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
    
    # Check if file has async context
    if not ASYNC_FUNC_REGEX.search(raw_content):
        result["is_async_file"] = False
        return result
    
    result["is_async_file"] = True
    
    # Strip comments and strings for analysis
    content = _strip_comments(raw_content)
    content = _strip_strings(content)
    
    # Run detections
    findings = []
    findings.extend(detect_sequential_awaits(content, path_norm))
    findings.extend(detect_await_in_loop(content, path_norm))
    findings.extend(detect_sync_io(content, path_norm))
    
    # Sort by line number
    findings.sort(key=lambda x: x.get("line", x.get("line_start", 0)))
    
    result["findings"] = findings
    
    # Build summary
    result["summary"]["total_findings"] = len(findings)
    result["summary"]["sequential_awaits"] = sum(1 for f in findings if f["type"] == "sequential_await")
    result["summary"]["await_in_loops"] = sum(1 for f in findings if f["type"] == "await_in_loop")
    result["summary"]["sync_io"] = sum(1 for f in findings if f["type"] == "sync_io")
    
    for f in findings:
        severity = f.get("severity", "low")
        if severity in result["summary"]["severity_counts"]:
            result["summary"]["severity_counts"][severity] += 1
    
    return result


def scan_directory_for_async_issues(
    path: str = ".",
    ignore_dirs: Optional[set] = None
) -> Dict[str, Any]:
    """Scan a directory for async anti-patterns across all source files."""
    if ignore_dirs is None:
        ignore_dirs = {"node_modules", ".git", "dist", ".angular", "coverage", ".next", "out"}
    
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
            
            if result["exists"] and result["is_async_file"]:
                files_scanned += 1
                
                if result["findings"]:
                    files_with_issues += 1
                    all_findings.extend(result["findings"])
    
    # Sort findings by severity then line
    severity_order = {"high": 0, "medium": 1, "low": 2}
    all_findings.sort(key=lambda x: (severity_order.get(x.get("severity", "low"), 3), x.get("file", ""), x.get("line", x.get("line_start", 0))))
    
    return {
        "schema_version": SCHEMA_VERSION,
        "scan_root": _normalize_path(path),
        "files_scanned": files_scanned,
        "files_with_issues": files_with_issues,
        "total_findings": len(all_findings),
        "findings": all_findings,
        "summary": {
            "by_type": {
                "sequential_await": sum(1 for f in all_findings if f["type"] == "sequential_await"),
                "await_in_loop": sum(1 for f in all_findings if f["type"] == "await_in_loop"),
                "sync_io": sum(1 for f in all_findings if f["type"] == "sync_io"),
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
        print(json.dumps(scan_directory_for_async_issues(root), indent=2))
    elif len(sys.argv) > 1:
        file_p = sys.argv[1]
        print(json.dumps(analyze_file(file_p), indent=2))
    else:
        print(json.dumps({
            "tool": "async_waterfall_detector",
            "schema_version": SCHEMA_VERSION,
            "usage": {
                "analyze_file": "python3 async_waterfall_detector.py <file_path>",
                "scan_directory": "python3 async_waterfall_detector.py scan [root_path]"
            }
        }, indent=2))
