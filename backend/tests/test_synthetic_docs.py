"""Unit tests for the synthetic document corpus and seed generator."""

from __future__ import annotations

import json
import sys
import uuid
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import generate_synthetic_docs as gen  # noqa: E402


def test_corpus_document_count_and_tier_distribution() -> None:
    """Verify 42 synthetic docs exist with the expected permission tier breakdown."""
    docs_dir = _REPO_ROOT / "data" / "synthetic_docs"
    docs = gen.load_documents(docs_dir, gen.DEFAULT_PRINCIPALS)

    assert len(docs) == 42
    tier_counts = Counter(doc.tier for doc in docs)
    assert tier_counts["team-a"] == 12
    assert tier_counts["team-b"] == 11
    assert tier_counts["shared"] == 13
    assert tier_counts["private-luke"] == 3
    assert tier_counts["private-leia"] == 3


def test_every_document_has_explicit_acl_and_tenant() -> None:
    """Ensure every document has valid tenant_id and non-empty ACL principals."""
    docs_dir = _REPO_ROOT / "data" / "synthetic_docs"
    docs = gen.load_documents(docs_dir, gen.DEFAULT_PRINCIPALS)

    team_a_gid = gen.DEFAULT_PRINCIPALS["team-a"]
    team_b_gid = gen.DEFAULT_PRINCIPALS["team-b"]
    luke_oid = gen.DEFAULT_PRINCIPALS["luke"]
    leia_oid = gen.DEFAULT_PRINCIPALS["leia"]

    for doc in docs:
        uuid.UUID(doc.id)
        uuid.UUID(doc.tenant_id)
        assert doc.allowed_user_ids or doc.allowed_group_ids

        if doc.tier == "team-a":
            assert doc.allowed_group_ids == [team_a_gid]
            assert doc.allowed_user_ids == []
        elif doc.tier == "team-b":
            assert doc.allowed_group_ids == [team_b_gid]
            assert doc.allowed_user_ids == []
        elif doc.tier == "shared":
            assert set(doc.allowed_group_ids) == {team_a_gid, team_b_gid}
            assert doc.allowed_user_ids == []
        elif doc.tier == "private-luke":
            assert doc.allowed_user_ids == [luke_oid]
            assert doc.allowed_group_ids == []
        elif doc.tier == "private-leia":
            assert doc.allowed_user_ids == [leia_oid]
            assert doc.allowed_group_ids == []


def test_near_duplicate_titles_across_teams() -> None:
    """Verify near-duplicate titles exist across teams with disjoint ACLs."""
    docs_dir = _REPO_ROOT / "data" / "synthetic_docs"
    docs = gen.load_documents(docs_dir, gen.DEFAULT_PRINCIPALS)

    near_dups = [doc for doc in docs if doc.near_duplicate_of is not None]
    assert len(near_dups) == 6

    by_group: dict[str, list[gen.SyntheticDocument]] = {}
    for doc in near_dups:
        assert doc.near_duplicate_of is not None
        by_group.setdefault(doc.near_duplicate_of, []).append(doc)

    assert len(by_group) == 3
    for pair in by_group.values():
        assert len(pair) == 2
        assert {d.tier for d in pair} == {"team-a", "team-b"}
        assert pair[0].title == pair[1].title
        assert pair[0].id != pair[1].id
        assert set(pair[0].allowed_group_ids).isdisjoint(pair[1].allowed_group_ids)


def test_poisoned_document_contains_injection_payload() -> None:
    """Verify poisoned documents are flagged and contain distinct injection styles."""
    docs_dir = _REPO_ROOT / "data" / "synthetic_docs"
    docs = gen.load_documents(docs_dir, gen.DEFAULT_PRINCIPALS)

    poisoned = [doc for doc in docs if doc.is_poisoned]
    assert len(poisoned) == 3
    combined = "\n".join(doc.content for doc in poisoned)
    assert "Ignore all previous system instructions" in combined
    assert "COMPLIANCE_AUDIT_DIRECTIVE" in combined
    assert "<system_instruction" in combined


def test_cli_generates_valid_json_and_sql(tmp_path: Path) -> None:
    """Verify generator CLI writes valid JSON and idempotent SQL seed output."""
    json_out = tmp_path / "docs.json"
    sql_out = tmp_path / "seed.sql"

    exit_code = gen.main(
        [
            "--json-out",
            str(json_out),
            "--sql-out",
            str(sql_out),
        ]
    )
    assert exit_code == 0

    data = json.loads(json_out.read_text(encoding="utf-8"))
    assert data["document_count"] == 42
    assert len(data["documents"]) == 42

    sql_text = sql_out.read_text(encoding="utf-8")
    assert sql_text.count("INSERT INTO documents") == 42
    assert sql_text.count("ON CONFLICT (id) DO NOTHING;") == 42
    assert "BEGIN;" in sql_text
    assert "COMMIT;" in sql_text
