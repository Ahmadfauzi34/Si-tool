"""Persistent derived cache for the Memory Recall Projection.

The canonical memory store remains authoritative.  A warm lookup hashes the
store bytes under the project-scope lock and reuses this cache only when the
cryptographic content hash, scope, cache schema, and projection engine match.
On a store change, exact structural equality of complete memory records allows
unchanged projected entries to survive while changed/added/deleted records are
reconciled.

The cache contains full memory records because the public recall API returns
those records.  It is local, Git-ignored, owner-only, and never a recovery
source for canonical memory.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from memory.retrieval import (
    RECALL_PROJECTION_SCHEMA_VERSION,
    build_recall_projection,
    deserialize_recall_projection,
    serialize_recall_projection,
)
from memory.runtime import write_json_unlocked


RECALL_CACHE_SCHEMA_VERSION = "memory-recall-projection-cache-v1"
RECALL_CACHE_MODES = ("auto", "refresh", "off")
ABSENT_EMPTY_STORE_SIGNATURE = "sha256:" + hashlib.sha256(
    b"canonical-memory-store-absent-empty-v1"
).hexdigest()
RECALL_CACHE_INTEGRITY_BOUNDARY = (
    "SHA-256 detects accidental/stale local cache state; it is not an external "
    "tamper-proof trust anchor"
)


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )


def _sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _engine_signature() -> str:
    digest = hashlib.sha256()
    digest.update(
        f"python:{sys.version_info.major}.{sys.version_info.minor}".encode(
            "utf-8"
        )
    )
    digest.update(b"\0")
    for path in (
        Path(__file__),
        Path(__file__).with_name("retrieval.py"),
        Path(__file__).with_name("store.py"),
    ):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def _store_fingerprint(store_path: str) -> Dict[str, Any]:
    path = Path(store_path)
    backup_present = Path(f"{path}.bak").is_file()
    if not path.is_file():
        return {
            "content_sha256": ABSENT_EMPTY_STORE_SIGNATURE,
            "bytes_hashed": 0,
            "present": False,
            "backup_present": backup_present,
            "recovery_pending": backup_present,
        }
    payload = path.read_bytes()
    return {
        "content_sha256": _sha256_bytes(payload),
        "bytes_hashed": len(payload),
        "present": True,
        "backup_present": backup_present,
        "recovery_pending": False,
    }


def _integrity_path(cache_path: str) -> Path:
    return Path(f"{cache_path}.sha256")


def _load_cache_unlocked(
    cache_path: str,
    scope_id: str,
) -> Tuple[
    Optional[Dict[str, Any]],
    Optional[Dict[str, Any]],
    Optional[str],
]:
    path = Path(cache_path)
    integrity_path = _integrity_path(cache_path)
    if not path.is_file():
        if integrity_path.exists():
            return None, None, "recall_cache_payload_missing"
        return None, None, None
    try:
        raw_payload = path.read_bytes()
        with integrity_path.open("r", encoding="utf-8") as handle:
            integrity = json.load(handle)
    except Exception as exc:
        return None, None, f"recall_cache_read_error:{type(exc).__name__}"
    if (
        not isinstance(integrity, dict)
        or integrity.get("schema_version") != RECALL_CACHE_SCHEMA_VERSION
        or integrity.get("cache_sha256") != _sha256_bytes(raw_payload)
    ):
        return None, None, "recall_cache_checksum_mismatch"
    try:
        payload = json.loads(raw_payload)
    except Exception as exc:
        return None, None, f"recall_cache_json_error:{type(exc).__name__}"
    if not isinstance(payload, dict):
        return None, None, "recall_cache_payload_not_object"
    if payload.get("schema_version") != RECALL_CACHE_SCHEMA_VERSION:
        return None, None, "recall_cache_schema_mismatch"
    if payload.get("scope_id") != scope_id:
        return None, None, "recall_cache_scope_mismatch"
    if payload.get("projection_schema_version") != RECALL_PROJECTION_SCHEMA_VERSION:
        return None, None, "recall_projection_schema_mismatch"
    if not isinstance(payload.get("store_content_sha256"), str):
        return None, None, "recall_cache_store_signature_missing"
    if not isinstance(payload.get("engine_signature"), str):
        return None, None, "recall_cache_engine_signature_missing"
    try:
        projection = deserialize_recall_projection(payload.get("projection"))
    except Exception as exc:
        return None, None, f"recall_cache_projection_invalid:{type(exc).__name__}"
    return payload, projection, None


def _write_cache_unlocked(
    cache_path: str,
    scope_id: str,
    store_fingerprint: Dict[str, Any],
    projection: Dict[str, Any],
    engine_signature: str,
    created_at: Optional[str],
) -> Optional[str]:
    payload = {
        "schema_version": RECALL_CACHE_SCHEMA_VERSION,
        "projection_schema_version": RECALL_PROJECTION_SCHEMA_VERSION,
        "scope_id": scope_id,
        "engine_signature": engine_signature,
        "store_content_sha256": store_fingerprint["content_sha256"],
        "canonical_store_present": bool(store_fingerprint["present"]),
        "canonical_backup_present": bool(
            store_fingerprint.get("backup_present", False)
        ),
        "canonical_recovery_pending": bool(
            store_fingerprint.get("recovery_pending", False)
        ),
        "canonical_store_bytes": int(store_fingerprint["bytes_hashed"]),
        "created_at": created_at or _utc_now(),
        "updated_at": _utc_now(),
        "contains_full_memory_content": True,
        "canonical_store_authoritative": True,
        "cache_can_restore_canonical_store": False,
        "integrity_boundary": RECALL_CACHE_INTEGRITY_BOUNDARY,
        "projection": serialize_recall_projection(projection),
    }
    try:
        write_json_unlocked(
            cache_path,
            payload,
            retain_backup=False,
            compact=True,
        )
        raw_payload = Path(cache_path).read_bytes()
        write_json_unlocked(
            str(_integrity_path(cache_path)),
            {
                "schema_version": RECALL_CACHE_SCHEMA_VERSION,
                "cache_sha256": _sha256_bytes(raw_payload),
            },
            retain_backup=False,
            compact=True,
        )
        return None
    except Exception as exc:
        return f"recall_cache_write_error:{type(exc).__name__}"


def _base_metrics(
    mode: str,
    paths: Dict[str, Any],
    store_fingerprint: Dict[str, Any],
    engine_signature: str,
) -> Dict[str, Any]:
    return {
        "mode": mode,
        "status": "miss",
        "cache_path": paths["recall_cache_path"],
        "integrity_path": str(_integrity_path(paths["recall_cache_path"])),
        "cache_schema_version": RECALL_CACHE_SCHEMA_VERSION,
        "projection_schema_version": RECALL_PROJECTION_SCHEMA_VERSION,
        "scope_id": paths["scope_id"],
        "engine_signature": engine_signature,
        "store_content_sha256": store_fingerprint["content_sha256"],
        "canonical_store_present": bool(store_fingerprint["present"]),
        "canonical_backup_present": bool(
            store_fingerprint.get("backup_present", False)
        ),
        "canonical_recovery_pending": bool(
            store_fingerprint.get("recovery_pending", False)
        ),
        "canonical_store_bytes_hashed": int(store_fingerprint["bytes_hashed"]),
        "canonical_store_load_count": 0,
        "entries_reused": 0,
        "entries_rebuilt": 0,
        "entries_removed": 0,
        "hit_ratio": 0.0,
        "contains_full_memory_content": True,
        "canonical_store_authoritative": True,
        "cache_can_restore_canonical_store": False,
        "integrity_boundary": RECALL_CACHE_INTEGRITY_BOUNDARY,
    }


def load_or_build_recall_projection_unlocked(
    paths: Dict[str, Any],
    load_store_unlocked: Callable[[], Dict[str, Any]],
    mode: str = "auto",
) -> Dict[str, Any]:
    """Return a projection while the caller holds the memory scope lock."""
    normalized_mode = str(mode).strip().lower()
    if normalized_mode not in RECALL_CACHE_MODES:
        raise ValueError(
            f"Unsupported memory recall cache mode: {mode}. Expected one of: "
            f"{', '.join(RECALL_CACHE_MODES)}"
        )

    engine_signature = _engine_signature()
    fingerprint = _store_fingerprint(paths["store_path"])
    metrics = _base_metrics(
        normalized_mode,
        paths,
        fingerprint,
        engine_signature,
    )

    cached_payload: Optional[Dict[str, Any]] = None
    cached_projection: Optional[Dict[str, Any]] = None
    load_error: Optional[str] = None
    if normalized_mode == "auto":
        cached_payload, cached_projection, load_error = _load_cache_unlocked(
            paths["recall_cache_path"], paths["scope_id"]
        )
        if load_error:
            metrics["recovery_reason"] = load_error

    engine_compatible = bool(
        cached_payload
        and cached_payload.get("engine_signature") == engine_signature
    )
    store_compatible = bool(
        cached_payload
        and not fingerprint.get("recovery_pending", False)
        and cached_payload.get("store_content_sha256")
        == fingerprint["content_sha256"]
        and bool(cached_payload.get("canonical_store_present"))
        == bool(fingerprint["present"])
    )
    if cached_projection and engine_compatible and store_compatible:
        total = int(cached_projection.get("snapshot_memory_count", 0))
        metrics.update({
            "status": "hit",
            "entries_reused": total,
            "hit_ratio": 1.0,
            "projection_signature": cached_projection.get(
                "snapshot_signature"
            ),
        })
        cached_projection["cache"] = metrics
        return cached_projection

    invalidation_reasons = []
    if cached_payload and not engine_compatible:
        invalidation_reasons.append("projection_engine_changed")
    if cached_payload and not store_compatible:
        invalidation_reasons.append(
            "canonical_recovery_pending"
            if fingerprint.get("recovery_pending", False)
            else "canonical_store_changed"
        )
    if invalidation_reasons:
        metrics["invalidation_reasons"] = invalidation_reasons

    store = load_store_unlocked()
    metrics["canonical_store_load_count"] = 1
    # Recovery may atomically recreate the primary store. Bind the new cache to
    # the actual bytes after canonical validation/recovery completed.
    fingerprint = _store_fingerprint(paths["store_path"])
    metrics.update({
        "store_content_sha256": fingerprint["content_sha256"],
        "canonical_store_present": bool(fingerprint["present"]),
        "canonical_backup_present": bool(
            fingerprint.get("backup_present", False)
        ),
        "canonical_recovery_pending": bool(
            fingerprint.get("recovery_pending", False)
        ),
        "canonical_store_bytes_hashed": int(fingerprint["bytes_hashed"]),
    })
    previous = (
        cached_projection
        if normalized_mode == "auto" and engine_compatible
        else None
    )
    projection = build_recall_projection(
        store.get("memories", []),
        previous_projection=previous,
    )
    build = projection.get("build", {})
    reused = int(build.get("entries_reused", 0))
    metrics.update({
        "entries_reused": reused,
        "entries_rebuilt": int(build.get("entries_rebuilt", 0)),
        "entries_removed": int(build.get("entries_removed", 0)),
        "hit_ratio": round(
            reused
            / max(
                1,
                reused
                + int(build.get("entries_rebuilt", 0))
                + int(build.get("entries_removed", 0)),
            ),
            6,
        ),
        "projection_signature": projection.get("snapshot_signature"),
    })

    if normalized_mode == "off":
        metrics["status"] = "disabled"
        projection["cache"] = metrics
        return projection

    if normalized_mode == "refresh":
        status = "refreshed"
    elif load_error:
        status = "recovered"
    elif cached_payload and engine_compatible and reused:
        status = "partial"
    elif cached_payload:
        status = "invalidated"
    else:
        status = "miss"

    write_error = _write_cache_unlocked(
        paths["recall_cache_path"],
        paths["scope_id"],
        fingerprint,
        projection,
        engine_signature,
        cached_payload.get("created_at") if cached_payload else None,
    )
    if write_error:
        metrics["build_status"] = status
        metrics["status"] = "write_failed"
        metrics["write_error"] = write_error
    else:
        metrics["status"] = status
    projection["cache"] = metrics
    return projection


def get_recall_cache_status_unlocked(paths: Dict[str, Any]) -> Dict[str, Any]:
    """Inspect derived-cache compatibility without parsing canonical JSON."""
    fingerprint = _store_fingerprint(paths["store_path"])
    engine_signature = _engine_signature()
    payload, projection, load_error = _load_cache_unlocked(
        paths["recall_cache_path"], paths["scope_id"]
    )
    if load_error:
        return {
            **_base_metrics("status", paths, fingerprint, engine_signature),
            "status": "corrupt",
            "recovery_reason": load_error,
        }
    if not payload or not projection:
        return {
            **_base_metrics("status", paths, fingerprint, engine_signature),
            "status": "missing",
        }
    stale_reasons = []
    if payload.get("engine_signature") != engine_signature:
        stale_reasons.append("projection_engine_changed")
    if (
        payload.get("store_content_sha256") != fingerprint["content_sha256"]
        or bool(payload.get("canonical_store_present"))
        != bool(fingerprint["present"])
    ):
        stale_reasons.append("canonical_store_changed")
    if fingerprint.get("recovery_pending", False):
        stale_reasons.append("canonical_recovery_pending")
    total = int(projection.get("snapshot_memory_count", 0))
    return {
        **_base_metrics("status", paths, fingerprint, engine_signature),
        "status": "stale" if stale_reasons else "valid",
        "stale_reasons": stale_reasons,
        "entries_reused": total if not stale_reasons else 0,
        "hit_ratio": 1.0 if not stale_reasons else 0.0,
        "projection_signature": projection.get("snapshot_signature"),
        "cached_store_content_sha256": payload.get("store_content_sha256"),
        "created_at": payload.get("created_at"),
        "updated_at": payload.get("updated_at"),
    }


def clear_recall_cache_unlocked(paths: Dict[str, Any]) -> Dict[str, Any]:
    path = Path(paths["recall_cache_path"])
    integrity_path = _integrity_path(paths["recall_cache_path"])
    existing = [
        candidate
        for candidate in (path, integrity_path)
        if candidate.exists()
    ]
    if not existing:
        return {
            "status": "missing",
            "cache_path": str(path),
            "integrity_path": str(integrity_path),
            "scope_id": paths["scope_id"],
        }
    try:
        for candidate in existing:
            candidate.unlink()
        return {
            "status": "cleared",
            "cache_path": str(path),
            "integrity_path": str(integrity_path),
            "scope_id": paths["scope_id"],
        }
    except OSError as exc:
        return {
            "status": "clear_failed",
            "cache_path": str(path),
            "integrity_path": str(integrity_path),
            "scope_id": paths["scope_id"],
            "error": f"{type(exc).__name__}: {exc}",
        }


__all__ = [
    "ABSENT_EMPTY_STORE_SIGNATURE",
    "RECALL_CACHE_INTEGRITY_BOUNDARY",
    "RECALL_CACHE_MODES",
    "RECALL_CACHE_SCHEMA_VERSION",
    "clear_recall_cache_unlocked",
    "get_recall_cache_status_unlocked",
    "load_or_build_recall_projection_unlocked",
]
