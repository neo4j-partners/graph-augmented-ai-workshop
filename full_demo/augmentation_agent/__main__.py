"""CLI entry point for the Graph Augmentation Agent demo.

Run with::

    cd full_demo
    python -m augmentation_agent

Configuration is loaded from ``.env`` in the project root (full_demo/).
All settings can be overridden via environment variables.

The script orchestrates eight steps:

1. Verify Databricks authentication.
2. Configure DSPy with the Supervisor Agent endpoint (BaseLM, model_type=responses).
3. Query the Supervisor Agent for gap analysis.
4. Run four DSPy analyses concurrently via ``dspy.Parallel``.
5. Validate and display the structured results.
6. Resolve schema-level suggestions into instance-level proposals.
7. Filter proposals by confidence level (HIGH/MEDIUM/LOW).
8. Write approved proposals back to Neo4j.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


# ---------------------------------------------------------------------------
# Configuration (loaded from .env + environment variables)
# ---------------------------------------------------------------------------

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """Agent configuration loaded from .env and environment variables."""

    model_config = {"env_file": str(_ENV_FILE), "env_file_encoding": "utf-8", "extra": "ignore"}

    supervisor_agent_endpoint: str = Field(default="mas-3ae5a347-endpoint")
    temperature: float = Field(default=0.1)
    max_tokens: int = Field(default=4000)
    neo4j_uri: str = Field(default="")
    neo4j_username: str = Field(default="neo4j")
    neo4j_password: str = Field(default="")
    databricks_volume_path: str = Field(default="")
    dry_run: bool = Field(default=False)
    analysis_only: bool = Field(default=False)


# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------


def _describe(ar) -> str:
    from augmentation_agent.schemas import (
        ImpliedRelationshipsAnalysis,
        InvestmentThemesAnalysis,
        MissingAttributesAnalysis,
        NewEntitiesAnalysis,
    )

    d = ar.data
    if isinstance(d, InvestmentThemesAnalysis):
        return f"{len(d.themes)} themes"
    if isinstance(d, NewEntitiesAnalysis):
        return f"{len(d.suggested_nodes)} nodes"
    if isinstance(d, MissingAttributesAnalysis):
        return f"{len(d.suggested_attributes)} attributes"
    if isinstance(d, ImpliedRelationshipsAnalysis):
        return f"{len(d.suggested_relationships)} relationships"
    return "ok"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    from pydantic import BaseModel

    from augmentation_agent.analyzers import GraphAugmentationAnalyzer
    from augmentation_agent.filter import filter_proposals
    from augmentation_agent.lm import configure_dspy
    from augmentation_agent.resolver import resolve_proposals
    from augmentation_agent.reporting import (
        ValidationHarness,
        print_response_summary,
    )
    from augmentation_agent.writeback import write_proposals

    settings = Settings()
    harness = ValidationHarness()

    print("=" * 60)
    print("Lab 7: Graph Augmentation Agent (DSPy)")
    print("=" * 60)
    print(f"  Endpoint:    {settings.supervisor_agent_endpoint}")
    print(f"  Temperature: {settings.temperature}")
    print(f"  Max tokens:  {settings.max_tokens}")
    print(f"  Neo4j URI:   {settings.neo4j_uri or '(not set)'}")
    print(f"  Dry run:     {settings.dry_run}")
    print(f"  Analysis only: {settings.analysis_only}")
    print()

    # ── Step 1: Authentication ────────────────────────────────────────

    print("Step 1: Databricks Authentication")
    try:
        from databricks.sdk import WorkspaceClient

        host = WorkspaceClient().config.host
        harness.record("authentication", True, f"connected to {host}")
    except Exception as e:
        harness.record("authentication", False, str(e))
        harness.print_summary()
        sys.exit(1)

    # ── Step 2: Configure DSPy ────────────────────────────────────────

    print("\nStep 2: Configure DSPy")
    try:
        configure_dspy(
            settings.supervisor_agent_endpoint,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )
        harness.record("dspy_config", True, "BaseLM  model_type=responses")
    except Exception as e:
        harness.record("dspy_config", False, str(e))
        harness.print_summary()
        sys.exit(1)

    # ── Step 3: Gap analysis via Supervisor Agent ─────────────────────

    print("\nStep 3: Query Supervisor Agent for Gap Analysis")
    try:
        from augmentation_agent.supervisor_client import fetch_gap_analysis

        gap_analysis = fetch_gap_analysis(settings.supervisor_agent_endpoint)
        harness.record(
            "supervisor_gap_analysis",
            len(gap_analysis) > 100,
            f"{len(gap_analysis):,} chars",
        )
        print(f"  Preview: {gap_analysis[:200]}...")
    except Exception as e:
        harness.record("supervisor_gap_analysis", False, str(e))
        harness.print_summary()
        sys.exit(1)

    # ── Step 4: Run analyses (parallel) ───────────────────────────────

    print("\nStep 4: Run DSPy Analyses")
    analyzer = GraphAugmentationAnalyzer()
    t0 = time.time()
    try:
        response = analyzer(gap_analysis)
        elapsed = time.time() - t0

        for name, field in [
            ("investment_themes", response.analysis.investment_themes),
            ("new_entities", response.analysis.new_entities),
            ("missing_attributes", response.analysis.missing_attributes),
            ("implied_relationships", response.analysis.implied_relationships),
        ]:
            harness.record(
                f"analysis_{name}",
                field is not None,
                f"{elapsed:.1f}s" if field is not None else "not returned",
            )
    except Exception as e:
        elapsed = time.time() - t0
        harness.record("analyses_parallel", False, f"{e} ({elapsed:.1f}s)")
        harness.print_summary()
        sys.exit(1)

    # ── Step 5: Validate ──────────────────────────────────────────────

    print("\nStep 5: Validate Results")
    print_response_summary(response)

    harness.record(
        "total_suggestions",
        response.total_suggestions > 0,
        f"{response.total_suggestions} suggestions, "
        f"{response.high_confidence_count} high-confidence",
    )

    has_pydantic = any(
        v is not None and isinstance(v, BaseModel)
        for v in [
            response.analysis.investment_themes,
            response.analysis.new_entities,
            response.analysis.missing_attributes,
            response.analysis.implied_relationships,
        ]
    )
    harness.record("structured_output", has_pydantic, "Pydantic models returned")

    # ── Stop here if analysis-only mode ──────────────────────────────

    if settings.analysis_only:
        harness.print_summary()
        sys.exit(0 if harness.all_passed else 1)

    # ── Step 6: Resolve into instance-level proposals ────────────────

    print("\nStep 6: Resolve Instance-Level Proposals")
    try:
        proposals = resolve_proposals(response, settings.supervisor_agent_endpoint)
        harness.record(
            "resolve_proposals",
            isinstance(proposals, list),
            f"{len(proposals)} proposals",
        )
    except Exception as e:
        harness.record("resolve_proposals", False, str(e))
        harness.print_summary()
        sys.exit(1)

    # ── Step 7: Filter by confidence ─────────────────────────────────

    print("\nStep 7: Filter Proposals by Confidence")
    enrichment_result = filter_proposals(proposals)
    writable = enrichment_result.approved + enrichment_result.flagged
    harness.record(
        "confidence_filter",
        True,
        f"{enrichment_result.approved_count} approved, "
        f"{enrichment_result.flagged_count} flagged, "
        f"{enrichment_result.rejected_count} rejected",
    )

    # ── Step 8: Write back to Neo4j ──────────────────────────────────

    print("\nStep 8: Write Enrichments to Neo4j")
    if not settings.neo4j_uri:
        harness.record(
            "neo4j_writeback",
            False,
            "skipped: NEO4J_URI not set in .env",
        )
    elif not writable:
        harness.record("neo4j_writeback", True, "no proposals to write")
    else:
        try:
            report = write_proposals(
                writable,
                settings.neo4j_uri,
                settings.neo4j_username,
                settings.neo4j_password,
                dry_run=settings.dry_run,
            )
            if settings.dry_run:
                harness.record(
                    "neo4j_writeback",
                    True,
                    f"dry run: {len(writable)} proposals previewed",
                )
            else:
                harness.record(
                    "neo4j_writeback",
                    True,
                    f"{report.created} created, {report.updated} updated, "
                    f"{len(report.skipped)} skipped",
                )
        except Exception as e:
            harness.record("neo4j_writeback", False, str(e))

    # ── Summary ───────────────────────────────────────────────────────

    harness.print_summary()
    sys.exit(0 if harness.all_passed else 1)


if __name__ == "__main__":
    main()
