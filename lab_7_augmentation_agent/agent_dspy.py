"""
Graph Augmentation Agent - DSPy Implementation

This script implements a DSPy-based agent for analyzing unstructured documents
and suggesting graph augmentations for Neo4j. It uses DSPy signatures for
declarative structured output instead of manual JSON parsing.

Key advantages over the original implementation:
- Automatic prompt generation from signatures
- Type-safe structured output via Pydantic models
- Built-in support for optimization via DSPy compiler
- Native MLflow tracing integration
- Simpler, more maintainable code

Prerequisites:
    1. Supervisor Agent from Lab 6 deployed as a Databricks serving endpoint
    2. DSPy and MLflow installed (see pyproject.toml)
    3. Authentication via one of:
       - On Databricks: Automatic (runtime provides credentials)
       - Locally: DATABRICKS_HOST and DATABRICKS_TOKEN in .env file

Usage:
    # Run on Databricks (via IDE plugin or notebook)
    # Run locally with uv
    uv run python -m lab_7_augmentation_agent.agent_dspy

References:
    - https://docs.databricks.com/aws/en/generative-ai/dspy/
    - https://dspy.ai/learn/programming/signatures/
    - https://dspy.ai/learn/programming/modules/
"""

from __future__ import annotations

from typing import Final

from lab_7_augmentation_agent.schemas import AugmentationResponse
from lab_7_augmentation_agent.dspy_modules.config import (
    configure_dspy,
    setup_mlflow_tracing,
)
from lab_7_augmentation_agent.dspy_modules.analyzers import (
    GraphAugmentationAnalyzer,
    InvestmentThemesResult,
    NewEntitiesResult,
    MissingAttributesResult,
    ImpliedRelationshipsResult,
)
from lab_7_augmentation_agent.utils import (
    ANALYSIS_TYPES,
    print_response_summary,
)
from lab_7_augmentation_agent.dspy_modules.supervisor_client import fetch_gap_analysis

# =============================================================================
# CONFIGURATION - Update these values as needed
# =============================================================================

# Supervisor Agent endpoint name
# This MUST be the Supervisor Agent endpoint created in Lab 6 (lab_6_multi_agent)
# The agent relies on the Supervisor Agent to route queries to Genie + Knowledge Assistant
# Get your endpoint name from the Supervisor Agent UI by clicking the cloud icon
# Note: Databricks uses the "mas-" prefix in endpoint names (Multi-Agent Supervisor)
SUPERVISOR_AGENT_ENDPOINT: Final[str] = "mas-3ae5a347-endpoint"

# Model parameters
DEFAULT_TEMPERATURE: Final[float] = 0.1  # Lower = more deterministic responses
DEFAULT_MAX_TOKENS: Final[int] = 4000    # Maximum tokens in LLM response

# =============================================================================

# Union of all result types for type hints
AnalysisResult = InvestmentThemesResult | NewEntitiesResult | MissingAttributesResult | ImpliedRelationshipsResult


def verify_databricks_connection() -> str:
    """
    Verify Databricks connection using WorkspaceClient.

    Authentication is handled automatically:
    - On Databricks: Uses runtime's built-in authentication
    - Locally: Uses DATABRICKS_HOST and DATABRICKS_TOKEN from .env

    Returns:
        The Databricks host URL.

    Raises:
        RuntimeError: If connection fails.
    """
    from databricks.sdk import WorkspaceClient

    print("=" * 60)
    print("AUTHENTICATION - Verifying Databricks connection")
    print("=" * 60)

    try:
        client = WorkspaceClient()
        host = client.config.host
        print(f"  [OK] Connected to: {host}")
        print("=" * 60)
        return host
    except Exception as e:
        print(f"  [FAIL] Connection failed: {e}")
        print("")
        print("  On Databricks: Authentication should be automatic")
        print("  Locally: Set DATABRICKS_HOST and DATABRICKS_TOKEN in .env")
        print("=" * 60)
        raise RuntimeError(f"Failed to connect to Databricks: {e}")


class DSPyGraphAugmentationAgent:
    """
    DSPy-based agent for graph augmentation analysis.

    This agent uses DSPy modules with typed signatures to analyze documents
    and produce structured suggestions for graph schema improvements.

    Attributes:
        analyzer: The GraphAugmentationAnalyzer DSPy module
    """

    def __init__(
        self,
        model_name: str | None = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        enable_tracing: bool = True,
    ):
        """
        Initialize the DSPy agent.

        Args:
            model_name: Supervisor Agent endpoint name from Lab 6. Uses SUPERVISOR_AGENT_ENDPOINT if None.
            temperature: Sampling temperature for the LM.
            max_tokens: Maximum tokens in LM responses.
            enable_tracing: Enable MLflow tracing for observability.
        """
        # Use configured endpoint if not specified
        endpoint = model_name or SUPERVISOR_AGENT_ENDPOINT

        # Configure DSPy globally with Supervisor Agent endpoint
        # (Supervisor Agent endpoints use Responses API format via DatabricksResponsesLM)
        configure_dspy(
            model_name=endpoint,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Enable MLflow tracing if requested
        if enable_tracing:
            setup_mlflow_tracing()

        # Create the analyzer module
        self.analyzer = GraphAugmentationAnalyzer()

        print("[OK] DSPy Graph Augmentation Agent initialized")

    def run_all_analyses(
        self,
        document_context: str,
    ) -> AugmentationResponse:
        """
        Run all analysis types on the provided document context.

        Args:
            document_context: The document content to analyze.

        Returns:
            AugmentationResponse with all suggestions consolidated.
        """
        print("\nRunning all analyses...")
        return self.analyzer(document_context=document_context)

    def run_single_analysis(
        self,
        analysis_type: str,
        document_context: str,
    ) -> AnalysisResult:
        """
        Run a single analysis type.

        Args:
            analysis_type: One of the ANALYSIS_TYPES.
            document_context: The document content to analyze.

        Returns:
            AnalysisResult for the specified analysis.
        """
        if analysis_type not in ANALYSIS_TYPES:
            raise ValueError(
                f"Unknown analysis type: {analysis_type}. "
                f"Must be one of: {ANALYSIS_TYPES}"
            )

        print(f"\nRunning {analysis_type} analysis...")
        return self.analyzer.run_single(analysis_type, document_context)


def main() -> tuple[DSPyGraphAugmentationAgent, AugmentationResponse]:
    """
    Main entry point for the DSPy Graph Augmentation Agent.

    Runs all analyses using sample document context.

    Returns:
        Tuple of (agent, response) for further interaction.
    """
    print("\n" + "=" * 70)
    print("GRAPH AUGMENTATION AGENT - DSPY IMPLEMENTATION")
    print("=" * 70)

    # Print configuration
    print(f"\nConfiguration:")
    print(f"  Supervisor Agent Endpoint: {SUPERVISOR_AGENT_ENDPOINT}")
    print(f"  Temperature:     {DEFAULT_TEMPERATURE}")
    print(f"  Max Tokens:      {DEFAULT_MAX_TOKENS}")
    print("")

    # Verify Databricks connection
    verify_databricks_connection()

    # Initialize the agent
    agent = DSPyGraphAugmentationAgent(
        model_name=SUPERVISOR_AGENT_ENDPOINT,
        temperature=DEFAULT_TEMPERATURE,
        max_tokens=DEFAULT_MAX_TOKENS,
        enable_tracing=True,
    )

    # Query the Supervisor Agent for gap analysis between structured data and documents
    print("\n" + "=" * 60)
    print("STEP 1: QUERYING MULTI-AGENT SUPERVISOR FOR GAP ANALYSIS")
    print("=" * 60)
    gap_analysis = fetch_gap_analysis(SUPERVISOR_AGENT_ENDPOINT)
    print(f"\n  Gap analysis snippet ({len(gap_analysis)} chars total):")
    print(f"  {gap_analysis[:200]}...")

    # Run DSPy analyses to convert gaps into structured enrichment proposals
    print("\n" + "=" * 60)
    print("STEP 2: RUNNING DSPY ANALYSES FOR ENRICHMENT PROPOSALS")
    print("=" * 60)
    print("  Converting gap analysis into structured enrichment proposals...")
    print("  Running 4 analyses (each may take 30-60 seconds)...")
    response = agent.run_all_analyses(gap_analysis)
    print_response_summary(response)

    return agent, response


if __name__ == "__main__":
    agent, result = main()
