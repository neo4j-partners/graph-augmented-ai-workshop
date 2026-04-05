"""Supervisor Agent client for gap analysis.

This module queries the MAS endpoint created in Lab 6 to compare
structured graph data (via Genie) with unstructured documents (via
Knowledge Assistant).  The result is a text-based gap analysis that serves
as input to the DSPy analyzers.

No DSPy dependency — this is a plain Databricks SDK call.
"""

from __future__ import annotations

import time
from typing import Any

COMPREHENSIVE_GAP_QUERY = """\
Perform comprehensive gap analysis for graph augmentation opportunities.

This analysis will identify information in documents that should be captured
as new nodes, relationships, or attributes in the Neo4j graph.

PART 1: Customer Interest-Holding Gaps
For each customer (James Anderson, Maria Rodriguez, Robert Chen):
- What investment interests are expressed in their profiles?
- What do they currently hold in their portfolios?
- What's the gap between interests and holdings?
- Quote the specific profile text showing their interests.

PART 2: Missing Entity Relationships
What relationships are implied in documents but not in the graph?
- Customer-to-interest relationships (INTERESTED_IN)
- Customer-to-goal relationships (HAS_GOAL)
- Customer-to-employer relationships (WORKS_AT)
- Customer similarity patterns (SIMILAR_TO)

PART 3: Missing Customer Attributes
What customer attributes appear in profiles but aren't in structured data?
- Occupation and employer details
- Life stage (mid-career, approaching retirement, etc.)
- Investment philosophy
- Communication preferences

PART 4: Investment Theme Entities
What investment themes from research should become graph nodes?
- Theme names and descriptions
- Associated sectors and companies
- Market size and growth data

Provide specific evidence and quotes for each finding.
"""


def _get_responses_client(endpoint_name: str | None = None) -> tuple[Any, str]:
    """Return ``(openai_client, endpoint_name)`` using the Databricks SDK."""
    from databricks.sdk import WorkspaceClient

    wc = WorkspaceClient()
    client = wc.serving_endpoints.get_open_ai_client()
    return client, endpoint_name or ""


def query_mas(endpoint_name: str, prompt: str | None = None) -> str:
    """Send a single query to the MAS endpoint.

    Args:
        endpoint_name: Serving-endpoint name from Lab 6.
        prompt: Optional custom prompt.  Defaults to the comprehensive
            gap analysis query.

    Returns:
        The text response from the MAS.
    """
    client, _ = _get_responses_client()
    response = client.responses.create(
        model=endpoint_name,
        input=[{"role": "user", "content": prompt or COMPREHENSIVE_GAP_QUERY}],
    )
    return response.output[0].content[0].text


def fetch_gap_analysis(endpoint_name: str) -> str:
    """High-level helper: query MAS and return the gap analysis text.

    Prints progress banners that match the workshop's output style.
    """
    print("\n" + "=" * 60)
    print("QUERYING MULTI-AGENT SUPERVISOR FOR GAP ANALYSIS")
    print("=" * 60)
    print("  The MAS coordinates Genie (structured data) and")
    print("  Knowledge Assistant (documents) to find enrichment opportunities.")
    print("  This may take 1-3 minutes ...\n")

    t0 = time.time()
    text = query_mas(endpoint_name)
    elapsed = time.time() - t0

    print(f"  [OK] {len(text):,} chars in {elapsed:.1f}s")
    print("=" * 60)
    return text
