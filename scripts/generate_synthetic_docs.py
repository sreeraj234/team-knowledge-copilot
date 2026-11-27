#!/usr/bin/env python3
"""Validate and export synthetic project documents into JSON and SQL seed data.

Reads Markdown documents with YAML-style frontmatter from data/synthetic_docs/,
resolves logical ACL principals (tenant, users, groups) to UUIDs, validates
fail-closed ACL invariants, and emits structured JSON plus an idempotent
PostgreSQL seed script compatible with backend/migrations/001_schema.sql.

Usage:
    python scripts/generate_synthetic_docs.py
    python scripts/generate_synthetic_docs.py --from-settings
    python scripts/generate_synthetic_docs.py --json-out data/synthetic_docs.json
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DOCS_DIR = _REPO_ROOT / "data" / "synthetic_docs"
_DEFAULT_JSON_OUT = _REPO_ROOT / "data" / "synthetic_docs.json"
_DEFAULT_SQL_OUT = _REPO_ROOT / "backend" / "migrations" / "002_seed.sql"

# Deterministic namespace for generating reproducible fixture UUIDs
_FIXTURE_NAMESPACE = uuid.UUID("7f3d9a10-4b2e-4c8d-9e1a-2b3c4d5e6f70")

DEFAULT_PRINCIPALS: dict[str, str] = {
    "tenant": str(uuid.uuid5(_FIXTURE_NAMESPACE, "tenant:kestrel-cloud")),
    "luke": str(uuid.uuid5(_FIXTURE_NAMESPACE, "user:luke")),
    "leia": str(uuid.uuid5(_FIXTURE_NAMESPACE, "user:leia")),
    "team-a": str(uuid.uuid5(_FIXTURE_NAMESPACE, "group:team-a")),
    "team-b": str(uuid.uuid5(_FIXTURE_NAMESPACE, "group:team-b")),
}

VALID_TIERS = frozenset(
    {"team-a", "team-b", "shared", "private-luke", "private-leia"}
)


@dataclass(frozen=True)
class SyntheticDocument:
    """Validated synthetic document with resolved ACL UUIDs."""

    id: str
    tenant_id: str
    title: str
    tier: str
    allowed_user_ids: list[str]
    allowed_group_ids: list[str]
    is_poisoned: bool
    near_duplicate_of: str | None
    source_path: str
    content: str


def _parse_scalar(raw: str) -> Any:
    """Parse a simple YAML scalar value (string, bool, null, or inline list)."""
    val = raw.strip()
    if val in ("null", "~", ""):
        return None
    if val == "true":
        return True
    if val == "false":
        return False
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(item) for item in inner.split(",")]
    if (val.startswith('"') and val.endswith('"')) or (
        val.startswith("'") and val.endswith("'")
    ):
        return val[1:-1]
    return val


def parse_frontmatter(text: str, source_path: Path) -> tuple[dict[str, Any], str]:
    """Extract YAML-style frontmatter and markdown body from a document."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{source_path}: missing opening '---' frontmatter delimiter")

    end_idx: int | None = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break

    if end_idx is None:
        raise ValueError(f"{source_path}: missing closing '---' frontmatter delimiter")

    metadata: dict[str, Any] = {}
    for line in lines[1:end_idx]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            raise ValueError(f"{source_path}: invalid frontmatter line: {line!r}")
        key, raw_val = stripped.split(":", 1)
        metadata[key.strip()] = _parse_scalar(raw_val)

    body = "\n".join(lines[end_idx + 1 :]).strip()
    if not body:
        raise ValueError(f"{source_path}: document body must not be empty")

    return metadata, body


def _resolve_uuid_list(
    keys: list[str],
    principals: dict[str, str],
    field_name: str,
    source_path: Path,
) -> list[str]:
    """Resolve logical principal names (or raw UUIDs) into validated UUID strings."""
    resolved: list[str] = []
    for key in keys:
        candidate = principals.get(key, key)
        try:
            normalized = str(uuid.UUID(candidate))
        except ValueError as exc:
            raise ValueError(
                f"{source_path}: invalid {field_name} principal/UUID {key!r}"
            ) from exc
        if normalized not in resolved:
            resolved.append(normalized)
    return resolved


def load_documents(
    docs_dir: Path,
    principals: dict[str, str],
) -> list[SyntheticDocument]:
    """Load, parse, and validate all synthetic markdown documents."""
    if not docs_dir.is_dir():
        raise FileNotFoundError(f"Synthetic docs directory not found: {docs_dir}")

    md_files = sorted(docs_dir.rglob("*.md"))
    if not md_files:
        raise ValueError(f"No markdown files found under {docs_dir}")

    documents: list[SyntheticDocument] = []
    seen_ids: set[str] = set()

    for md_path in md_files:
        raw_text = md_path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(raw_text, md_path)

        doc_id_raw = meta.get("id")
        if not doc_id_raw or not isinstance(doc_id_raw, str):
            raise ValueError(f"{md_path}: missing required 'id' in frontmatter")
        doc_id = str(uuid.UUID(doc_id_raw))
        if doc_id in seen_ids:
            raise ValueError(f"{md_path}: duplicate document id {doc_id}")
        seen_ids.add(doc_id)

        title = meta.get("title")
        if not title or not isinstance(title, str):
            raise ValueError(f"{md_path}: missing required 'title' in frontmatter")

        tier = meta.get("tier")
        if tier not in VALID_TIERS:
            raise ValueError(f"{md_path}: invalid tier {tier!r}")

        allowed_users_raw = meta.get("allowed_users")
        allowed_groups_raw = meta.get("allowed_groups")
        if not isinstance(allowed_users_raw, list) or not isinstance(
            allowed_groups_raw, list
        ):
            raise ValueError(
                f"{md_path}: 'allowed_users' and 'allowed_groups' must be lists"
            )

        allowed_user_ids = _resolve_uuid_list(
            allowed_users_raw, principals, "allowed_users", md_path
        )
        allowed_group_ids = _resolve_uuid_list(
            allowed_groups_raw, principals, "allowed_groups", md_path
        )

        # Fail-closed check: every document must grant access to at least one principal
        if not allowed_user_ids and not allowed_group_ids:
            raise ValueError(
                f"{md_path}: document must specify at least one allowed user or group"
            )

        tenant_id = str(uuid.UUID(principals["tenant"]))
        is_poisoned = bool(meta.get("is_poisoned", False))
        near_dup = meta.get("near_duplicate_of")
        if near_dup is not None and not isinstance(near_dup, str):
            raise ValueError(f"{md_path}: 'near_duplicate_of' must be a string or null")

        rel_path = md_path.relative_to(_REPO_ROOT).as_posix()
        documents.append(
            SyntheticDocument(
                id=doc_id,
                tenant_id=tenant_id,
                title=title,
                tier=tier,
                allowed_user_ids=allowed_user_ids,
                allowed_group_ids=allowed_group_ids,
                is_poisoned=is_poisoned,
                near_duplicate_of=near_dup,
                source_path=rel_path,
                content=body,
            )
        )

    return documents


def _sql_quote(value: str) -> str:
    """Escape a string literal for PostgreSQL."""
    return "'" + value.replace("'", "''") + "'"


def _sql_uuid_array(values: list[str]) -> str:
    """Format a list of UUID strings as a PostgreSQL uuid[] literal."""
    if not values:
        return "ARRAY[]::uuid[]"
    quoted = ", ".join(_sql_quote(v) for v in values)
    return f"ARRAY[{quoted}]::uuid[]"


def render_sql_seed(documents: list[SyntheticDocument]) -> str:
    """Render idempotent PostgreSQL INSERT statements for the documents table."""
    lines = [
        "-- Auto-generated by scripts/generate_synthetic_docs.py",
        "-- Synthetic clean-room documents with explicit ACL metadata.",
        "",
        "BEGIN;",
        "",
    ]

    for doc in documents:
        lines.append(
            "INSERT INTO documents "
            "(id, tenant_id, title, allowed_user_ids, allowed_group_ids)"
        )
        lines.append("VALUES (")
        lines.append(f"    {_sql_quote(doc.id)}::uuid,")
        lines.append(f"    {_sql_quote(doc.tenant_id)}::uuid,")
        lines.append(f"    {_sql_quote(doc.title)},")
        lines.append(f"    {_sql_uuid_array(doc.allowed_user_ids)},")
        lines.append(f"    {_sql_uuid_array(doc.allowed_group_ids)}")
        lines.append(")")
        lines.append("ON CONFLICT (id) DO NOTHING;")
        lines.append("")

    lines.append("COMMIT;")
    lines.append("")
    return "\n".join(lines)


def resolve_principals(args: argparse.Namespace) -> dict[str, str]:
    """Build principal UUID mapping from defaults, optional settings, and CLI flags."""
    principals = dict(DEFAULT_PRINCIPALS)

    if args.from_settings:
        backend_dir = _REPO_ROOT / "backend"
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        from app.config import get_settings

        settings = get_settings()
        if settings.tenant_id:
            principals["tenant"] = settings.tenant_id
        if settings.luke_oid:
            principals["luke"] = settings.luke_oid
        if settings.leia_oid:
            principals["leia"] = settings.leia_oid
        if settings.team_a_group_id:
            principals["team-a"] = settings.team_a_group_id
        if settings.team_b_group_id:
            principals["team-b"] = settings.team_b_group_id

    overrides = {
        "tenant": args.tenant_id,
        "luke": args.luke_oid,
        "leia": args.leia_oid,
        "team-a": args.team_a_group_id,
        "team-b": args.team_b_group_id,
    }
    for key, val in overrides.items():
        if val:
            principals[key] = val

    # Validate all resolved principals are valid UUIDs
    return {k: str(uuid.UUID(v)) for k, v in principals.items()}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Generate JSON and SQL seed data from synthetic markdown docs."
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=_DEFAULT_DOCS_DIR,
        help="Directory containing synthetic markdown documents.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=_DEFAULT_JSON_OUT,
        help="Output path for structured JSON seed data.",
    )
    parser.add_argument(
        "--sql-out",
        type=Path,
        default=_DEFAULT_SQL_OUT,
        help="Output path for PostgreSQL seed SQL.",
    )
    parser.add_argument(
        "--from-settings",
        action="store_true",
        help="Load tenant/user/group UUIDs from app.config.get_settings() when set.",
    )
    parser.add_argument("--tenant-id", default=None, help="Override tenant UUID.")
    parser.add_argument("--luke-oid", default=None, help="Override Luke user OID.")
    parser.add_argument("--leia-oid", default=None, help="Override Leia user OID.")
    parser.add_argument(
        "--team-a-group-id", default=None, help="Override Team-A group UUID."
    )
    parser.add_argument(
        "--team-b-group-id", default=None, help="Override Team-B group UUID."
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point for generating synthetic JSON and SQL seed artifacts."""
    args = parse_args(argv)
    principals = resolve_principals(args)
    documents = load_documents(args.docs_dir, principals)

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "document_count": len(documents),
        "principals": principals,
        "documents": [asdict(doc) for doc in documents],
    }
    args.json_out.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    args.sql_out.parent.mkdir(parents=True, exist_ok=True)
    args.sql_out.write_text(render_sql_seed(documents), encoding="utf-8")

    print(
        f"Generated {len(documents)} documents -> {args.json_out} and {args.sql_out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
