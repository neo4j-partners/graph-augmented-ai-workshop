"""
Supervisor Agent Client for Graph Augmentation Analysis.

This module queries the Supervisor Agent endpoint from Lab 6
to perform gap analysis between structured graph data (via Genie) and
unstructured documents (via Knowledge Assistant).

The Supervisor Agent coordinates both agents to answer questions that span the
structured-unstructured divide, which is the core capability needed
for graph augmentation.

Key queries supported:
- Interest-holding gap analysis (customers with interests not in portfolios)
- Risk profile alignment (portfolio vs stated risk tolerance)
- Data quality gaps (profile info missing from structured data)
- Investment theme extraction (from market research documents)

Authentication is handled automatically by WorkspaceClient:
- On Databricks: Uses runtime's built-in authentication
- Locally: Uses DATABRICKS_HOST and DATABRICKS_TOKEN from .env
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT: Final[Path] = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

# Default Supervisor Agent endpoint name (from Lab 6)
# Note: Databricks uses the "mas-" prefix in endpoint names (Multi-Agent Supervisor)
DEFAULT_ENDPOINT: Final[str] = os.environ.get("SUPERVISOR_AGENT_ENDPOINT", "mas-3ae5a347-endpoint")


# =============================================================================
# GAP ANALYSIS QUERIES
# These queries leverage the Supervisor Agent to combine structured data (Genie)
# with unstructured documents (Knowledge Assistant) to find enrichment opportunities.
# =============================================================================

INTEREST_HOLDING_GAP_QUERY: Final[str] = """
Analyze customer investment interests vs their actual portfolio holdings.

For each customer with profile documents:
1. What investment interests have they expressed? (renewable energy, ESG,
   technology, real estate, etc.)
2. What stocks/sectors do they currently hold in their portfolios?
3. Identify gaps where expressed interests don't match holdings.

Format your response as a detailed analysis for each customer including:
- Customer ID and name
- Expressed interests (from profile documents)
- Current holdings (from portfolio data)
- Identified gaps (interests not reflected in portfolio)
- Specific quotes from their profile showing the interest

Focus especially on:
- James Anderson (C0001) and renewable energy interest
- Maria Rodriguez (C0002) and ESG/sustainable investing interest
- Robert Chen (C0003) and technology/aggressive growth interest
"""

RISK_PROFILE_ALIGNMENT_QUERY: Final[str] = """
Analyze risk profile alignment between customer profiles and portfolios.

For each customer:
1. What is their stated risk tolerance in the structured database?
2. What risk-related language appears in their profile documents?
3. Does their actual portfolio composition match their risk profile?

Identify customers where:
- Profile narrative suggests different risk tolerance than database field
- Portfolio composition doesn't match stated risk tolerance
- Risk preferences have evolved based on profile updates

Include specific evidence from both structured data and profile documents.
"""

DATA_QUALITY_GAP_QUERY: Final[str] = """
Identify data quality gaps between customer profiles and structured database.

Compare the information in customer profile documents against what's stored
in the structured customer database tables.

Look for:
1. Personal attributes mentioned in profiles but missing from database
   (occupation details, employer, life stage, family situation)
2. Financial goals mentioned in profiles but not captured as structured data
3. Investment preferences detailed in profiles but not in database fields
4. Contact preferences or communication style notes
5. Any temporal information (retirement timeline, education savings goals)

For each gap found, provide:
- The customer ID
- The attribute/information found in the profile
- Whether it exists in the structured database
- The exact quote or reference from the profile document
"""

INVESTMENT_THEMES_QUERY: Final[str] = """
Extract investment themes from market research documents.

Analyze all market research, sector analysis, and investment guide documents to identify:

1. Major investment themes being discussed
   - Theme name (e.g., "Renewable Energy Transition", "AI Infrastructure")
   - Market size and growth projections mentioned
   - Key sectors within the theme
   - Specific companies mentioned as opportunities

2. Sector-specific insights
   - Technology sector trends and key players
   - Renewable energy opportunities and companies
   - Financial sector analysis
   - Any emerging sectors discussed

3. Risk considerations mentioned
   - Valuation concerns
   - Market timing considerations
   - Sector-specific risks

For each theme, include the source document and relevant quotes.
"""

COMPREHENSIVE_GAP_ANALYSIS_QUERY: Final[str] = """
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


@dataclass
class GapAnalysisResult:
    """Results from a gap analysis query."""

    query_type: str
    response: str
    success: bool
    error: str | None = None


class SupervisorAgentClient:
    """
    Client for querying the Supervisor Agent endpoint.

    The Supervisor Agent coordinates Genie (structured data) and Knowledge
    Assistant (unstructured documents) to answer questions that span both
    data types. This is essential for graph augmentation, which requires
    comparing what's in the graph against what's in the documents.
    """

    def __init__(self, endpoint_name: str | None = None) -> None:
        """
        Initialize the Supervisor Agent client.

        Args:
            endpoint_name: The Supervisor Agent endpoint name from Lab 6.
                          Uses DEFAULT_ENDPOINT if not specified.
        """
        self.endpoint_name = endpoint_name or DEFAULT_ENDPOINT
        self._client: Any = None

    def _get_client(self) -> Any:
        """Get or create the Databricks OpenAI-compatible client."""
        if self._client is not None:
            return self._client

        try:
            from databricks.sdk import WorkspaceClient

            workspace_client = WorkspaceClient()
            self._client = workspace_client.serving_endpoints.get_open_ai_client()
            return self._client
        except Exception as e:
            raise RuntimeError(f"Failed to create Databricks client: {e}")

    def query(self, prompt: str) -> str:
        """
        Query the Supervisor Agent endpoint with a prompt.

        Args:
            prompt: The query to send to the Supervisor Agent.

        Returns:
            The text response from the Supervisor Agent.

        Raises:
            RuntimeError: If the query fails.
        """
        client = self._get_client()

        try:
            response = client.responses.create(
                model=self.endpoint_name,
                input=[{"role": "user", "content": prompt}],
            )
            return response.output[0].content[0].text
        except Exception as e:
            raise RuntimeError(f"Supervisor Agent query failed: {e}")

    def analyze_interest_holding_gaps(self) -> GapAnalysisResult:
        """
        Find gaps between customer interests and portfolio holdings.

        This is the core use case from GRAPH_AUGMENTATION.md:
        James Anderson mentions renewable energy interest but holds only tech stocks.

        Returns:
            GapAnalysisResult with interest-holding gap analysis.
        """
        print("  Analyzing interest-holding gaps...")
        try:
            response = self.query(INTEREST_HOLDING_GAP_QUERY)
            return GapAnalysisResult(
                query_type="interest_holding_gaps",
                response=response,
                success=True,
            )
        except Exception as e:
            return GapAnalysisResult(
                query_type="interest_holding_gaps",
                response="",
                success=False,
                error=str(e),
            )

    def analyze_risk_alignment(self) -> GapAnalysisResult:
        """
        Find mismatches between risk profiles and portfolio composition.

        Returns:
            GapAnalysisResult with risk alignment analysis.
        """
        print("  Analyzing risk profile alignment...")
        try:
            response = self.query(RISK_PROFILE_ALIGNMENT_QUERY)
            return GapAnalysisResult(
                query_type="risk_alignment",
                response=response,
                success=True,
            )
        except Exception as e:
            return GapAnalysisResult(
                query_type="risk_alignment",
                response="",
                success=False,
                error=str(e),
            )

    def analyze_data_quality_gaps(self) -> GapAnalysisResult:
        """
        Find information in profiles missing from structured database.

        Returns:
            GapAnalysisResult with data quality gap analysis.
        """
        print("  Analyzing data quality gaps...")
        try:
            response = self.query(DATA_QUALITY_GAP_QUERY)
            return GapAnalysisResult(
                query_type="data_quality_gaps",
                response=response,
                success=True,
            )
        except Exception as e:
            return GapAnalysisResult(
                query_type="data_quality_gaps",
                response="",
                success=False,
                error=str(e),
            )

    def extract_investment_themes(self) -> GapAnalysisResult:
        """
        Extract investment themes from market research documents.

        Returns:
            GapAnalysisResult with investment theme extraction.
        """
        print("  Extracting investment themes from research...")
        try:
            response = self.query(INVESTMENT_THEMES_QUERY)
            return GapAnalysisResult(
                query_type="investment_themes",
                response=response,
                success=True,
            )
        except Exception as e:
            return GapAnalysisResult(
                query_type="investment_themes",
                response="",
                success=False,
                error=str(e),
            )

    def run_comprehensive_analysis(self) -> GapAnalysisResult:
        """
        Run comprehensive gap analysis for graph augmentation.

        This combines all analysis types into a single query that identifies
        all opportunities for enriching the graph with information from documents.

        Returns:
            GapAnalysisResult with comprehensive analysis.
        """
        print("  Running comprehensive gap analysis...")
        try:
            response = self.query(COMPREHENSIVE_GAP_ANALYSIS_QUERY)
            return GapAnalysisResult(
                query_type="comprehensive",
                response=response,
                success=True,
            )
        except Exception as e:
            return GapAnalysisResult(
                query_type="comprehensive",
                response="",
                success=False,
                error=str(e),
            )


def fetch_gap_analysis(endpoint_name: str | None = None) -> str:
    """
    Fetch comprehensive gap analysis from the Supervisor Agent.

    This queries the Supervisor Agent to identify gaps between structured graph data
    and unstructured documents - the core input for graph augmentation.

    Args:
        endpoint_name: The Supervisor Agent endpoint name. Uses DEFAULT_ENDPOINT if not specified.

    Returns:
        Comprehensive gap analysis text for graph augmentation.

    Example:
        >>> from lab_7_augmentation_agent.dspy_modules.supervisor_client import fetch_gap_analysis
        >>> analysis = fetch_gap_analysis()
        >>> print(f"Retrieved {len(analysis)} characters of gap analysis")
    """
    print("\n" + "=" * 60)
    print("STEP 1: QUERYING MULTI-AGENT SUPERVISOR FOR GAP ANALYSIS")
    print("=" * 60)
    print("  The Supervisor Agent coordinates Genie (structured data) and")
    print("  Knowledge Assistant (documents) to find enrichment opportunities.")
    print("  This may take 1-3 minutes as the Supervisor Agent routes to multiple agents...")
    print("")

    start_time = time.time()
    client = SupervisorAgentClient(endpoint_name)
    result = client.run_comprehensive_analysis()
    elapsed = time.time() - start_time

    if result.success:
        print(f"\n  [OK] Retrieved {len(result.response):,} characters of analysis ({elapsed:.1f}s)")
    else:
        print(f"\n  [FAIL] Analysis failed: {result.error} ({elapsed:.1f}s)")

    print("=" * 60)

    if not result.success:
        raise RuntimeError(f"Gap analysis failed: {result.error}")

    return result.response
