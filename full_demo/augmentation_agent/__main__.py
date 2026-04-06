"""CLI entry point for the Graph Augmentation Agent demo.

Run with::

    cd solutions
    python -m augmentation_agent --supervisor-endpoint <endpoint-name>

The script orchestrates five steps:

1. Verify Databricks authentication.
2. Configure DSPy with the Supervisor Agent endpoint (BaseLM, model_type=responses).
3. Query the Supervisor Agent for gap analysis.
4. Run four DSPy analyses concurrently via ``dspy.Parallel``.
5. Validate and display the structured results.
"""

from __future__ import annotations

import argparse
import sys
import time

from pydantic import BaseModel

from augmentation_agent.analyzers import (
    AnalysisResult,
    GraphAugmentationAnalyzer,
    InvestmentThemesAnalyzer,
    NewEntitiesAnalyzer,
    MissingAttributesAnalyzer,
    ImpliedRelationshipsAnalyzer,
)
from augmentation_agent.lm import configure_dspy
from augmentation_agent.supervisor_client import fetch_gap_analysis
from augmentation_agent.reporting import (
    ValidationHarness,
    print_analysis_result,
    print_response_summary,
)
from augmentation_agent.schemas import (
    ConfidenceLevel,
    ImpliedRelationshipsAnalysis,
    InvestmentThemesAnalysis,
    MissingAttributesAnalysis,
    NewEntitiesAnalysis,
)

DEFAULT_ENDPOINT = "mas-3ae5a347-endpoint"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Lab 7: Graph Augmentation Agent (DSPy)",
    )
    p.add_argument(
        "--supervisor-endpoint",
        default=DEFAULT_ENDPOINT,
        help="Supervisor Agent endpoint name from Lab 6",
    )
    p.add_argument("--temperature", type=float, default=0.1)
    p.add_argument("--max-tokens", type=int, default=4000)
    # Accepted from cli.submit but unused by this script.
    p.add_argument("--neo4j-uri", default="")
    p.add_argument("--neo4j-username", default="")
    p.add_argument("--neo4j-password", default="")
    p.add_argument("--volume-path", default="")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------


def _describe(ar: AnalysisResult) -> str:
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


def _count_suggestions(results: list[AnalysisResult]) -> tuple[int, int]:
    total = high = 0
    for r in results:
        d = r.data
        items: list = []
        if isinstance(d, NewEntitiesAnalysis):
            items = d.suggested_nodes
        elif isinstance(d, MissingAttributesAnalysis):
            items = d.suggested_attributes
        elif isinstance(d, ImpliedRelationshipsAnalysis):
            items = d.suggested_relationships
        total += len(items)
        high += sum(1 for i in items if i.confidence == ConfidenceLevel.HIGH)
    return total, high


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    args = _parse_args()
    harness = ValidationHarness()

    print("=" * 60)
    print("Lab 7: Graph Augmentation Agent (DSPy)")
    print("=" * 60)
    print(f"  Endpoint:    {args.supervisor_endpoint}")
    print(f"  Temperature: {args.temperature}")
    print(f"  Max tokens:  {args.max_tokens}")
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
            args.supervisor_endpoint,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
        harness.record("dspy_config", True, "BaseLM  model_type=responses")
    except Exception as e:
        harness.record("dspy_config", False, str(e))
        harness.print_summary()
        sys.exit(1)

    # ── Step 3: Gap analysis via Supervisor Agent ─────────────────────

    print("\nStep 3: Query Supervisor Agent for Gap Analysis")
    try:
        gap_analysis = fetch_gap_analysis(args.supervisor_endpoint)
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

        # Record per-analysis pass/fail from the consolidated response
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

    # ── Summary ───────────────────────────────────────────────────────

    harness.print_summary()
    sys.exit(0 if harness.all_passed else 1)


if __name__ == "__main__":
    main()
