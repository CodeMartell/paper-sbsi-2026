"""Evidence about file identity and reference time; mtime is never freshness."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temp.replace(path)


def read_metadata(path):
    sidecar = Path(str(path) + ".meta.json")
    if not sidecar.exists():
        return {"temporal_evidence": "absent"}
    try:
        meta = json.loads(sidecar.read_text(encoding="utf-8"))
        if meta.get("sha256") != digest(path):
            return {"temporal_evidence": "hash_mismatch"}
        # Strict allowlist avoids persisting arbitrary fields or credentials.
        return {k: meta[k] for k in ("obtained_at", "reference_start", "reference_end", "reference_basis") if k in meta}
    except (ValueError, TypeError, AttributeError):
        return {"temporal_evidence": "invalid_metadata"}


def freshness(metadata, max_age_days, now=None):
    now = now or datetime.now(timezone.utc)
    try:
        start = datetime.fromisoformat(metadata["reference_start"])
        end = datetime.fromisoformat(metadata["reference_end"])
        if start.tzinfo is None or end.tzinfo is None or start > end or end > now:
            raise ValueError("Invalid reference interval")
        age = (now-end).total_seconds()/86400
        return {"state": "stale" if age > max_age_days else "current", "age_days": round(age, 6)}
    except (KeyError, ValueError, TypeError):
        return {"state": "unknown", "age_days": None}
