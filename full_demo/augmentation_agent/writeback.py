"""Write approved enrichment proposals back to Neo4j.

Executes Cypher MERGE statements for each approved proposal. Only creates
relationships between nodes that already exist in the graph. Proposals
referencing a target node that does not exist are reported as skipped.

MERGE is idempotent: running the same proposal twice updates properties
rather than creating duplicates.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from augmentation_agent.schemas import EnrichmentProposal


_CYPHER_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _validate_identifier(name: str, context: str) -> None:
    """Validate that a string is a safe Cypher identifier.

    Labels, property names, and relationship types are interpolated into
    Cypher queries because the language does not support parameterizing them.
    This check prevents injection through those positions.
    """
    if not _CYPHER_IDENTIFIER_RE.match(name):
        raise ValueError(
            f"Invalid Cypher {context}: {name!r} "
            f"(must match {_CYPHER_IDENTIFIER_RE.pattern})"
        )


@dataclass
class WriteBackReport:
    """Summary of what was written to Neo4j."""

    created: int = 0
    updated: int = 0
    skipped: list[str] = field(default_factory=list)

    @property
    def total_written(self) -> int:
        return self.created + self.updated


# language=cypher
_MERGE_QUERY = """\
MATCH (src:{source_label} {{{source_key}: $source_value}})
MATCH (tgt:{target_label} {{{target_key}: $target_value}})
MERGE (src)-[r:{relationship_type}]->(tgt)
ON CREATE SET
  r.confidence = $confidence,
  r.source_document = $source_document,
  r.extracted_phrase = $extracted_phrase,
  r.enriched_at = $enriched_at,
  r._created = true
ON MATCH SET
  r.confidence = $confidence,
  r.source_document = $source_document,
  r.extracted_phrase = $extracted_phrase,
  r.enriched_at = $enriched_at,
  r._created = false
RETURN r._created AS was_created
"""

# language=cypher
_CHECK_NODE_EXISTS = """\
MATCH (n:{label} {{{key}: $value}})
RETURN count(n) > 0 AS exists
"""


def _build_merge_query(proposal: EnrichmentProposal) -> str:
    """Build a parameterized Cypher MERGE query for a proposal.

    Node labels and property names are interpolated into the query string
    because Cypher does not support parameterized labels or property keys.
    Values are passed as parameters to prevent injection.

    Raises ValueError if any identifier fails validation.
    """
    _validate_identifier(proposal.source_node.label, "source label")
    _validate_identifier(proposal.source_node.key_property, "source key property")
    _validate_identifier(proposal.target_node.label, "target label")
    _validate_identifier(proposal.target_node.key_property, "target key property")
    _validate_identifier(proposal.relationship_type, "relationship type")

    return _MERGE_QUERY.format(
        source_label=proposal.source_node.label,
        source_key=proposal.source_node.key_property,
        target_label=proposal.target_node.label,
        target_key=proposal.target_node.key_property,
        relationship_type=proposal.relationship_type,
    )


def _check_node_exists(tx, label: str, key: str, value: str) -> bool:
    """Check whether a node exists in the graph."""
    _validate_identifier(label, "label")
    _validate_identifier(key, "key property")
    query = _CHECK_NODE_EXISTS.format(label=label, key=key)
    result = tx.run(query, value=value)
    record = result.single()
    return record is not None and record["exists"]


def _execute_merge(tx, query: str, params: dict) -> dict | None:
    """Execute a MERGE query inside a write transaction."""
    result = tx.run(query, **params)
    return result.single()


def write_proposals(
    proposals: list[EnrichmentProposal],
    neo4j_uri: str,
    neo4j_username: str,
    neo4j_password: str,
    *,
    dry_run: bool = False,
) -> WriteBackReport:
    """Write approved proposals to Neo4j.

    Args:
        proposals: Proposals that passed the confidence filter (HIGH + MEDIUM).
        neo4j_uri: Neo4j connection URI.
        neo4j_username: Neo4j username.
        neo4j_password: Neo4j password.
        dry_run: If True, report what would be written without executing.

    Returns:
        WriteBackReport summarizing the results.
    """
    if not proposals:
        print("  No proposals to write.")
        return WriteBackReport()

    print("\n" + "=" * 60)
    if dry_run:
        print("WRITE-BACK TO NEO4J (DRY RUN)")
    else:
        print("WRITE-BACK TO NEO4J")
    print("=" * 60)
    print(f"  Proposals to write: {len(proposals)}")

    if dry_run:
        print("\n  --- Dry run: no changes will be made ---")
        for p in proposals:
            print(
                f"  WOULD WRITE: ({p.source_node.label}:{p.source_node.key_value})"
                f"-[{p.relationship_type}]->"
                f"({p.target_node.label}:{p.target_node.key_value})"
                f"  [{p.confidence.value}]"
            )
        print("=" * 60)
        return WriteBackReport()

    from neo4j import GraphDatabase

    report = WriteBackReport()
    enriched_at = datetime.now(timezone.utc).isoformat()

    t0 = time.time()
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))

    try:
        driver.verify_connectivity()
    except Exception as e:
        driver.close()
        raise ConnectionError(f"Failed to connect to Neo4j at {neo4j_uri}: {e}") from e

    try:
        with driver.session() as session:
            for p in proposals:
                # Validate identifiers before querying
                try:
                    query = _build_merge_query(p)
                except ValueError as e:
                    skip_msg = f"Invalid identifier: {e}"
                    report.skipped.append(skip_msg)
                    print(f"  [SKIP] {skip_msg}")
                    continue

                # Check that both source and target nodes exist
                source_exists = session.execute_read(
                    _check_node_exists,
                    p.source_node.label,
                    p.source_node.key_property,
                    p.source_node.key_value,
                )
                target_exists = session.execute_read(
                    _check_node_exists,
                    p.target_node.label,
                    p.target_node.key_property,
                    p.target_node.key_value,
                )

                if not source_exists:
                    skip_msg = (
                        f"Source node not found: "
                        f"{p.source_node.label}:{p.source_node.key_value}"
                    )
                    report.skipped.append(skip_msg)
                    print(f"  [SKIP] {skip_msg}")
                    continue

                if not target_exists:
                    skip_msg = (
                        f"Target node not found: "
                        f"{p.target_node.label}:{p.target_node.key_value}"
                    )
                    report.skipped.append(skip_msg)
                    print(f"  [SKIP] {skip_msg}")
                    continue

                # Execute the MERGE inside a write transaction
                params = {
                    "source_value": p.source_node.key_value,
                    "target_value": p.target_node.key_value,
                    "confidence": p.confidence.value,
                    "source_document": p.source_document,
                    "extracted_phrase": p.extracted_phrase,
                    "enriched_at": enriched_at,
                }

                record = session.execute_write(_execute_merge, query, params)

                if record is None:
                    skip_msg = (
                        f"MERGE returned no result: "
                        f"({p.source_node.label}:{p.source_node.key_value})"
                        f"-[{p.relationship_type}]->"
                        f"({p.target_node.label}:{p.target_node.key_value})"
                    )
                    report.skipped.append(skip_msg)
                    print(f"  [SKIP] {skip_msg}")
                    continue

                if record["was_created"]:
                    report.created += 1
                    tag = "CREATED"
                else:
                    report.updated += 1
                    tag = "UPDATED"

                print(
                    f"  [{tag}] ({p.source_node.label}:{p.source_node.key_value})"
                    f"-[{p.relationship_type}]->"
                    f"({p.target_node.label}:{p.target_node.key_value})"
                )
    finally:
        driver.close()

    elapsed = time.time() - t0
    print(f"\n  Results: {report.created} created, {report.updated} updated, "
          f"{len(report.skipped)} skipped  ({elapsed:.1f}s)")
    print("=" * 60)
    return report
