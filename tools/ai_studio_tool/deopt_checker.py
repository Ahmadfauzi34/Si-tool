"""
V8 Deoptimization Checker
Schema Version: 1.0.0

Mendeteksi pola kode TypeScript/JavaScript yang berpotensi memicu:
- Hidden Class Transition (dynamic property addition/deletion)
- Deoptimization via eval/new Function
- Polymorphic object shapes dalam loop
- Arguments object leak

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


def detect_delete_operator(content: str, file_path: str) -> List[Dict[str, Any]]:
    """Detect usage of delete operator on object properties."""
    findings = []
    lines = content.split("\n")
    
    delete_regex = re.compile(r"\bdelete\s+[\w.$\[\]'\"]+")
    
    for i, line in enumerate(lines):
        match = delete_regex.search(line)
        if match:
            findings.append({
                "file": file_path,
                "type": "delete_operator",
                "severity": "high",
                "line": i + 1,
                "content": line.strip(),
                "description": "delete operator forces V8 into dictionary mode (slow properties)"
            })
    
    return findings


def detect_eval_new_function(content: str, file_path: str) -> List[Dict[str, Any]]:
    """Detect eval() and new Function() usage."""
    findings = []
    lines = content.split("\n")
    
    eval_regex = re.compile(r"\beval\s*\(")
    new_func_regex = re.compile(r"\bnew\s+Function\s*\(")
    
    for i, line in enumerate(lines):
        if eval_regex.search(line):
            findings.append({
                "file": file_path,
                "type": "eval_usage",
                "severity": "high",
                "line": i + 1,
                "content": line.strip(),
                "description": "eval() disables optimization in the enclosing scope"
            })
        
        if new_func_regex.search(line):
            findings.append({
                "file": file_path,
                "type": "new_function",
                "severity": "high",
                "line": i + 1,
                "content": line.strip(),
                "description": "new Function() creates unoptimizable dynamic code"
            })
    
    return findings


def detect_dynamic_property_addition(content: str, file_path: str) -> List[Dict[str, Any]]:
    """
    Detect patterns where properties are added to objects after initialization.
    Heuristic: const/let obj = {...}; followed by obj.newProp = ...
    """
    findings = []
    lines = content.split("\n")
    
    # Track object declarations
    obj_decl_regex = re.compile(
        r"(?:const|let|var)\s+(\w+)\s*=\s*\{[^}]*\}"
    )
    
    declared_objects = {}
    
    for i, line in enumerate(lines):
        # Track object declarations
        decl_match = obj_decl_regex.search(line)
        if decl_match:
            obj_name = decl_match.group(1)
            declared_objects[obj_name] = i + 1
        
        # Check for property additions to declared objects
        for obj_name, decl_line in declared_objects.items():
            prop_add_regex = re.compile(
                rf"\b{re.escape(obj_name)}\.(\w+)\s*=(?!=)"
            )
            prop_match = prop_add_regex.search(line)
            if prop_match and (i + 1) > decl_line:
                prop_name = prop_match.group(1)
                findings.append({
                    "file": file_path,
                    "type": "dynamic_property_addition",
                    "severity": "medium",
                    "line": i + 1,
                    "object": obj_name,
                    "property": prop_name,
                    "declared_at_line": decl_line,
                    "content": line.strip(),
                    "description": f"Property '{prop_name}' added to '{obj_name}' after initialization (hidden class transition)"
                })
    
    return findings


def detect_conditional_shape_in_loop(content: str, file_path: str) -> List[Dict[str, Any]]:
    """
    Detect objects created in loops with conditional property additions.
    This creates polymorphic shapes that hurt V8 optimization.
    """
    findings = []
    lines = content.split("\n")
    
    in_loop = False
    loop_start = 0
    brace_count = 0
    obj_created_in_loop = {}
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Detect loop start
        if re.match(r"^\s*(for\s*\(|for\s+(?:const|let|var)\s+\w+\s+(?:of|in)|while\s*\()", stripped):
            in_loop = True
            loop_start = i + 1
            brace_count = 0
            obj_created_in_loop = {}
        
        if in_loop:
            brace_count += stripped.count("{") - stripped.count("}")
            
            # Track object creation inside loop
            obj_match = re.search(r"(?:const|let|var)\s+(\w+)\s*=\s*\{", stripped)
            if obj_match and brace_count > 0:
                obj_created_in_loop[obj_match.group(1)] = i + 1
            
            # Check for conditional property addition
            for obj_name, create_line in obj_created_in_loop.items():
                cond_prop_regex = re.compile(
                    rf"if\s*\([^)]*\)\s*{re.escape(obj_name)}\.(\w+)\s*="
                )
                if cond_prop_regex.search(stripped):
                    findings.append({
                        "file": file_path,
                        "type": "conditional_shape_in_loop",
                        "severity": "medium",
                        "line": i + 1,
                        "loop_start_line": loop_start,
                        "object": obj_name,
                        "content": stripped,
                        "description": f"Conditional property addition to '{obj_name}' in loop creates polymorphic shapes"
                    })
            
            if brace_count <= 0 and i > loop_start:
                in_loop = False
    
    return findings


def detect_arguments_leak(content: str, file_path: str) -> List[Dict[str, Any]]:
    """Detect functions that return or leak the arguments object."""
    findings = []
    lines = content.split("\n")
    
    args_return_regex = re.compile(r"\breturn\s+arguments\s*;")
    args_pass_regex = re.compile(r"\w+\s*\(\s*arguments\s*\)")
    
    for i, line in enumerate(lines):
        if args_return_regex.search(line):
            findings.append({
                "file": file_path,
                "type": "arguments_leak",
                "severity": "medium",
                "line": i + 1,
                "content": line.strip(),
                "description": "Returning arguments object prevents optimization"
            })
        
        if args_pass_regex.search(line) and "function" not in line:
            findings.append({
                "file": file_path,
                "type": "arguments_leak",
                "severity": "low",
                "line": i + 1,
                "content": line.strip(),
                "description": "Passing arguments object to another function may prevent optimization"
            })
    
    return findings


def analyze_file(file_path: str) -> Dict[str, Any]:
    """Analyze a single file for V8 deoptimization patterns."""
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
                "delete_operator": 0,
                "eval_usage": 0,
                "new_function": 0,
                "dynamic_property_addition": 0,
                "conditional_shape_in_loop": 0,
                "arguments_leak": 0
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
    findings.extend(detect_delete_operator(content, path_norm))
    findings.extend(detect_eval_new_function(content, path_norm))
    findings.extend(detect_dynamic_property_addition(content, path_norm))
    findings.extend(detect_conditional_shape_in_loop(content, path_norm))
    findings.extend(detect_arguments_leak(content, path_norm))
    
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


def scan_directory_for_deopt(
    path: str = ".",
    ignore_dirs: Optional[set] = None
) -> Dict[str, Any]:
    """Scan a directory for V8 deoptimization patterns."""
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
                "delete_operator": sum(1 for f in all_findings if f["type"] == "delete_operator"),
                "eval_usage": sum(1 for f in all_findings if f["type"] == "eval_usage"),
                "new_function": sum(1 for f in all_findings if f["type"] == "new_function"),
                "dynamic_property_addition": sum(1 for f in all_findings if f["type"] == "dynamic_property_addition"),
                "conditional_shape_in_loop": sum(1 for f in all_findings if f["type"] == "conditional_shape_in_loop"),
                "arguments_leak": sum(1 for f in all_findings if f["type"] == "arguments_leak"),
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
        print(json.dumps(scan_directory_for_deopt(root), indent=2))
    elif len(sys.argv) > 1:
        file_p = sys.argv[1]
        print(json.dumps(analyze_file(file_p), indent=2))
    else:
        print(json.dumps({
            "tool": "deopt_checker",
            "schema_version": SCHEMA_VERSION,
            "usage": {
                "analyze_file": "python3 deopt_checker.py <file_path>",
                "scan_directory": "python3 deopt_checker.py scan [root_path]"
            }
        }, indent=2))
