"""Lab 7 Validation: Graph Augmentation Agent (DSPy Implementation).

Tests the DSPy-based agent pipeline that analyzes unstructured documents
and suggests graph schema improvements for Neo4j.

Validates:
1. Databricks authentication
2. Supervisor Agent endpoint connectivity and gap analysis query
3. DSPy configuration with proper BaseLM adapter
4. Four concurrent analysis types via dspy.Parallel
5. Structured Pydantic output from each analysis

DSPy Best Practices Applied (vs original notebook code):
- DatabricksResponsesLM subclasses dspy.BaseLM and overrides forward()
  (not __call__), returning an OpenAI-compatible response object so DSPy's
  caching, callbacks, and history tracking all work correctly.
- model_type="responses" tells DSPy to use _process_response() for output
  extraction instead of the chat completions path.
- No explicit ChatAdapter — it is the default in DSPy 3.x.
- dspy.Parallel runs all four analyses concurrently for lower latency.

Prerequisites:
    - Supervisor Agent from Lab 6 deployed as a serving endpoint
    - dspy>=3.0.4 and pydantic installed on the cluster
    - Databricks authentication (automatic on cluster, or env vars locally)

Usage:
    python -m cli upload run_lab7.py && python -m cli submit run_lab7.py
"""

import os
import sys
import time
from dataclasses import dataclass
from enum import Enum
from types import SimpleNamespace
from typing import Any

# Parse KEY=VALUE parameters from cli.submit into environment variables.
for _arg in sys.argv[1:]:
    if "=" in _arg and not _arg.startswith("-"):
        _key, _, _value = _arg.partition("=")
        os.environ.setdefault(_key, _value)

import dspy
from databricks_openai import DatabricksOpenAI
from pydantic import BaseModel, Field


# ═══════════���══════════════════════════��════════════════════════════════
# PYDANTIC SCHEMAS  (self-contained — no imports from lab_7 package)
# ══════��═════════════���═════════════════════════���════════════════════════


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PropertyDefinition(BaseModel):
    name: str = Field(..., description="Property name")
    property_type: str = Field(..., description="Data type (string, int, float, boolean, date)")
    required: bool = Field(default=False, description="Whether the property is required")
    description: str | None = Field(default=None, description="Description of the property")


class SuggestedNode(BaseModel):
    label: str = Field(..., description="Node label (e.g., 'FINANCIAL_GOAL')")
    description: str = Field(..., description="What this node type represents")
    key_property: str = Field(..., description="Property that uniquely identifies nodes")
    properties: list[PropertyDefinition] = Field(default_factory=list)
    example_values: list[dict[str, Any]] = Field(default_factory=list)
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM)
    source_evidence: str = Field(..., description="Evidence supporting this suggestion")
    rationale: str = Field(..., description="Why this node type should be added")


class SuggestedRelationship(BaseModel):
    relationship_type: str = Field(..., description="Relationship type (e.g., 'HAS_GOAL')")
    description: str = Field(..., description="What this relationship represents")
    source_label: str = Field(..., description="Source node label")
    target_label: str = Field(..., description="Target node label")
    properties: list[PropertyDefinition] = Field(default_factory=list)
    example_instances: list[dict[str, Any]] = Field(default_factory=list)
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM)
    source_evidence: str = Field(..., description="Evidence supporting this suggestion")
    rationale: str = Field(..., description="Why this relationship type should be added")


class SuggestedAttribute(BaseModel):
    target_label: str = Field(..., description="Node type to add attribute to")
    property_name: str = Field(..., description="Name of the new property")
    property_type: str = Field(..., description="Data type")
    description: str = Field(..., description="What this attribute represents")
    example_values: list[Any] = Field(default_factory=list)
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM)
    source_evidence: str = Field(..., description="Evidence supporting this suggestion")
    rationale: str = Field(..., description="Why this attribute should be added")


class InvestmentTheme(BaseModel):
    name: str = Field(..., description="Theme name")
    description: str = Field(..., description="Description of the theme")
    market_size: str | None = Field(default=None)
    growth_projection: str | None = Field(default=None)
    key_sectors: list[str] = Field(default_factory=list)
    key_companies: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM)
    source_evidence: str = Field(..., description="Evidence supporting this theme")


class InvestmentThemesAnalysis(BaseModel):
    summary: str = Field(..., description="Overall summary of investment themes")
    themes: list[InvestmentTheme] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class NewEntitiesAnalysis(BaseModel):
    summary: str = Field(..., description="Overall summary of suggested entities")
    suggested_nodes: list[SuggestedNode] = Field(default_factory=list)
    implementation_priority: list[str] = Field(default_factory=list)


class MissingAttributesAnalysis(BaseModel):
    summary: str = Field(..., description="Overall summary of missing attributes")
    suggested_attributes: list[SuggestedAttribute] = Field(default_factory=list)
    affected_node_types: list[str] = Field(default_factory=list)


class ImpliedRelationshipsAnalysis(BaseModel):
    summary: str = Field(..., description="Overall summary of implied relationships")
    suggested_relationships: list[SuggestedRelationship] = Field(default_factory=list)
    relationship_patterns: list[str] = Field(default_factory=list)


# ═══════��══════════════════════���════════════════════════════════════════
# CUSTOM LM — Databricks Responses API via BaseLM.forward()
#
# Key fix: the original code subclassed LM and overrode __call__(),
# which bypassed DSPy's caching, callbacks, and history tracking.
# The correct pattern is to subclass BaseLM and override forward()
# to return an OpenAI-compatible response object.
# ══════════════════���═══════════════════════════════════════════��════════


class DatabricksResponsesLM(dspy.BaseLM):
    """DSPy LM adapter for Databricks Supervisor Agent endpoints.

    Uses the Responses API format (``input`` array instead of ``messages``).
    Authentication is handled by the Databricks SDK WorkspaceClient:
    - On Databricks clusters: automatic runtime credentials
    - Locally: DATABRICKS_HOST and DATABRICKS_TOKEN environment variables
    """

    def __init__(self, model: str, **kwargs: Any) -> None:
        # model_type="responses" tells BaseLM._process_lm_response to use
        # _process_response() which understands the Responses API output format.
        super().__init__(model=model, model_type="responses", **kwargs)
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazily create the Databricks OpenAI-compatible client."""
        if self._client is not None:
            return self._client
        self._client = DatabricksOpenAI()
        return self._client

    def forward(self, prompt=None, messages=None, **kwargs):
        """Call the Supervisor Agent endpoint and return the raw OpenAI response object.

        Supervisor Agent endpoints only support single-turn conversations,
        so we combine multi-turn messages (generated by DSPy's ChatAdapter)
        into one user message before sending.

        Returns:
            An OpenAI Responses API object that BaseLM._process_response()
            can parse (response.output[].content[].text).
        """
        client = self._get_client()

        # Combine multi-turn messages into a single user message for Supervisor Agent
        if messages:
            parts = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    parts.append(content)
                elif role == "user":
                    parts.append(content)
                elif role == "assistant":
                    parts.append(f"Assistant: {content}")
            input_messages = [{"role": "user", "content": "\n\n".join(parts)}]
        elif prompt:
            input_messages = [{"role": "user", "content": prompt}]
        else:
            raise ValueError("Either prompt or messages must be provided")

        response = client.responses.create(
            model=self.model,
            input=input_messages,
        )

        # Ensure usage is present — Supervisor Agent endpoints may not return token counts,
        # but BaseLM._process_lm_response() calls dict(response.usage).
        if not hasattr(response, "usage") or response.usage is None:
            response.usage = SimpleNamespace(
                prompt_tokens=0, completion_tokens=0, total_tokens=0,
            )

        return response


# ���═════════════════════════��════════════════════════════���═══════════════
# DSPY SIGNATURES
# ═══════════════════════��═══════════════════════════════════════════════


class InvestmentThemesSignature(dspy.Signature):
    """Analyze market research documents to identify emerging investment themes.

    Extract investment themes with supporting evidence, market sizing,
    growth projections, and confidence assessments. Focus on themes
    that could inform graph database augmentation for financial analysis.
    """

    document_context: str = dspy.InputField(
        desc="Market research documents and financial analysis content to analyze"
    )
    analysis: InvestmentThemesAnalysis = dspy.OutputField(
        desc="Structured analysis of investment themes with evidence and recommendations"
    )


class NewEntitiesSignature(dspy.Signature):
    """Analyze documents to suggest new entity types for the graph database.

    Identify entities that should be extracted and added as new node types,
    including their properties, key identifiers, and example values.
    Focus on entities that capture customer goals, preferences, interests,
    and life stages.
    """

    document_context: str = dspy.InputField(
        desc="HTML data and documents containing entity information to extract"
    )
    analysis: NewEntitiesAnalysis = dspy.OutputField(
        desc="Structured suggestions for new node types with properties and examples"
    )


class MissingAttributesSignature(dspy.Signature):
    """Analyze customer profiles to identify attributes missing from graph nodes.

    Compare information mentioned in customer profiles against the current
    Customer node schema to identify missing attributes that should be added.
    Include professional details, investment preferences, financial goals,
    and behavioral attributes.
    """

    document_context: str = dspy.InputField(
        desc="Customer profile documents and data containing attribute information"
    )
    analysis: MissingAttributesAnalysis = dspy.OutputField(
        desc="Structured suggestions for missing attributes with types and examples"
    )


class ImpliedRelationshipsSignature(dspy.Signature):
    """Analyze documents to identify relationships implied but not captured in the graph.

    Find relationships between customers, companies, and investments that are
    mentioned or implied in documents but not explicitly modeled. Focus on
    customer-goal, customer-interest, and customer-similarity relationships.
    """

    document_context: str = dspy.InputField(
        desc="Documents containing information about entity relationships"
    )
    analysis: ImpliedRelationshipsAnalysis = dspy.OutputField(
        desc="Structured suggestions for new relationship types with properties"
    )


# ═══════════════════════════════════════════════════════════════════════
# DSPY ANALYZER MODULES
# ═══════════════════���════════════════════════════════════��══════════════


@dataclass(slots=True)
class AnalysisResult:
    """Unified result type for all analysis modules."""

    name: str
    success: bool
    data: Any = None
    error: str | None = None
    reasoning: str | None = None


class InvestmentThemesAnalyzer(dspy.Module):
    def __init__(self):
        super().__init__()
        self.analyze = dspy.ChainOfThought(InvestmentThemesSignature)

    def forward(self, document_context: str) -> AnalysisResult:
        try:
            result = self.analyze(document_context=document_context)
            return AnalysisResult(
                name="investment_themes", success=True,
                data=result.analysis,
                reasoning=getattr(result, "reasoning", None),
            )
        except Exception as e:
            return AnalysisResult(name="investment_themes", success=False, error=str(e))


class NewEntitiesAnalyzer(dspy.Module):
    def __init__(self):
        super().__init__()
        self.analyze = dspy.ChainOfThought(NewEntitiesSignature)

    def forward(self, document_context: str) -> AnalysisResult:
        try:
            result = self.analyze(document_context=document_context)
            return AnalysisResult(
                name="new_entities", success=True,
                data=result.analysis,
                reasoning=getattr(result, "reasoning", None),
            )
        except Exception as e:
            return AnalysisResult(name="new_entities", success=False, error=str(e))


class MissingAttributesAnalyzer(dspy.Module):
    def __init__(self):
        super().__init__()
        self.analyze = dspy.ChainOfThought(MissingAttributesSignature)

    def forward(self, document_context: str) -> AnalysisResult:
        try:
            result = self.analyze(document_context=document_context)
            return AnalysisResult(
                name="missing_attributes", success=True,
                data=result.analysis,
                reasoning=getattr(result, "reasoning", None),
            )
        except Exception as e:
            return AnalysisResult(name="missing_attributes", success=False, error=str(e))


class ImpliedRelationshipsAnalyzer(dspy.Module):
    def __init__(self):
        super().__init__()
        self.analyze = dspy.ChainOfThought(ImpliedRelationshipsSignature)

    def forward(self, document_context: str) -> AnalysisResult:
        try:
            result = self.analyze(document_context=document_context)
            return AnalysisResult(
                name="implied_relationships", success=True,
                data=result.analysis,
                reasoning=getattr(result, "reasoning", None),
            )
        except Exception as e:
            return AnalysisResult(name="implied_relationships", success=False, error=str(e))


# ═══════════════���═══════════════════════════════════════════════════════
# SUPERVISOR AGENT GAP ANALYSIS QUERY
# ════════════════���══════════════════════════════════════════════════════

COMPREHENSIVE_GAP_QUERY = """
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


def query_supervisor_agent(endpoint_name: str) -> str:
    """Query the Supervisor Agent for gap analysis.

    Uses the Databricks SDK directly (not DSPy) since this is a
    one-shot data-fetching call, not a structured-output task.
    """
    client = DatabricksOpenAI()
    response = client.responses.create(
        model=endpoint_name,
        input=[{"role": "user", "content": COMPREHENSIVE_GAP_QUERY}],
    )
    return response.output[0].content[0].text


# ════════���═══════════════════════════════════════��══════════════════════
# VALIDATION HARNESS
# ═════════════��══════════════════════════════════���══════════════════════


def _print_summary(results):
    passed = sum(1 for _, p, _ in results if p)
    failed = sum(1 for _, p, _ in results if not p)
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {len(results)} total")
    print("=" * 60)
    for name, p, detail in results:
        status = "PASS" if p else "FAIL"
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    print("=" * 60)
    if failed == 0:
        print("SUCCESS: All checks passed")
    else:
        print(f"FAILURE: {failed} check(s) failed")
    print("=" * 60)


def main():
    supervisor_endpoint = os.getenv("SUPERVISOR_AGENT_ENDPOINT", "mas-3ae5a347-endpoint")

    print("=" * 60)
    print("Lab 7: Graph Augmentation Agent (DSPy)")
    print("=" * 60)
    print(f"  Supervisor Agent Endpoint: {supervisor_endpoint}")
    print()

    results = []

    def record(name, passed, detail=""):
        status = "PASS" if passed else "FAIL"
        results.append((name, passed, detail))
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))

    # ── Step 1: Verify Databricks authentication ───────────────────────

    print("Step 1: Databricks Authentication")
    try:
        from databricks.sdk import WorkspaceClient

        wc = WorkspaceClient()
        host = wc.config.host
        record("authentication", True, f"connected to {host}")
    except Exception as e:
        record("authentication", False, str(e))
        _print_summary(results)
        sys.exit(1)

    # ── Step 2: Configure DSPy with fixed BaseLM ──────────────────────

    print("\nStep 2: Configure DSPy")
    try:
        lm = DatabricksResponsesLM(
            model=supervisor_endpoint,
            temperature=0.1,
            max_tokens=4000,
        )
        # ChatAdapter is the default in DSPy 3.x — no need to set explicitly.
        dspy.configure(lm=lm, track_usage=True)
        record(
            "dspy_config", True,
            f"BaseLM(model_type=responses), endpoint={supervisor_endpoint}",
        )
    except Exception as e:
        record("dspy_config", False, str(e))
        _print_summary(results)
        sys.exit(1)

    # ── Step 3: Query Supervisor Agent for gap analysis ────────────────

    print("\nStep 3: Query Supervisor Agent for Gap Analysis")
    print("  (This may take 1-3 minutes as Supervisor Agent routes to multiple agents...)")
    gap_analysis = ""
    try:
        t0 = time.time()
        gap_analysis = query_supervisor_agent(supervisor_endpoint)
        elapsed = time.time() - t0
        record(
            "supervisor_gap_analysis",
            len(gap_analysis) > 100,
            f"{len(gap_analysis):,} chars in {elapsed:.1f}s",
        )
        print(f"  Preview: {gap_analysis[:200]}...")
    except Exception as e:
        record("supervisor_gap_analysis", False, str(e))
        _print_summary(results)
        sys.exit(1)

    # ── Step 4: Run DSPy analyses concurrently via dspy.Parallel ──────

    print("\nStep 4: Run DSPy Analyses (4 concurrent via dspy.Parallel)")

    analyzers = [
        InvestmentThemesAnalyzer(),
        NewEntitiesAnalyzer(),
        MissingAttributesAnalyzer(),
        ImpliedRelationshipsAnalyzer(),
    ]

    exec_pairs = [
        (
            analyzer,
            dspy.Example(document_context=gap_analysis).with_inputs(
                "document_context"
            ),
        )
        for analyzer in analyzers
    ]

    analysis_results: list[AnalysisResult] = []
    t0 = time.time()
    try:
        parallel = dspy.Parallel(
            num_threads=4,
            max_errors=4,
            provide_traceback=True,
        )
        analysis_results = parallel(exec_pairs)
        total_elapsed = time.time() - t0
        print(f"  All analyses completed in {total_elapsed:.1f}s\n")

        for ar in analysis_results:
            if ar is None:
                record("analysis_unknown", False, "returned None")
                continue
            if ar.success:
                detail = _describe_result(ar)
                record(f"analysis_{ar.name}", True, detail)
                if ar.reasoning:
                    preview = ar.reasoning[:120].replace("\n", " ")
                    print(f"           Reasoning: {preview}...")
            else:
                record(f"analysis_{ar.name}", False, ar.error or "unknown error")

    except Exception as e:
        total_elapsed = time.time() - t0
        record("analyses_parallel", False, f"{e} ({total_elapsed:.1f}s)")

    # ── Step 5: Validate aggregated results ────────��──────────────────

    print("\nStep 5: Validate Results")
    successful = [r for r in analysis_results if r is not None and r.success]

    total_suggestions = 0
    high_confidence = 0
    for r in successful:
        items = _get_suggestion_items(r)
        total_suggestions += len(items)
        high_confidence += sum(
            1 for item in items
            if getattr(item, "confidence", None) == ConfidenceLevel.HIGH
        )

    record(
        "result_count",
        len(successful) >= 2,
        f"{len(successful)}/4 analyses succeeded, "
        f"{total_suggestions} suggestions, {high_confidence} high-confidence",
    )

    has_typed_output = any(
        r.data is not None and isinstance(r.data, BaseModel)
        for r in successful
    )
    record("structured_output", has_typed_output, "Pydantic models returned")

    # ── Summary ───────────────────────────────────────────────────────

    _print_summary(results)
    sys.exit(0 if all(p for _, p, _ in results) else 1)


def _describe_result(ar: AnalysisResult) -> str:
    """Return a human-readable summary of an analysis result."""
    d = ar.data
    if isinstance(d, InvestmentThemesAnalysis):
        return f"{len(d.themes)} themes found"
    if isinstance(d, NewEntitiesAnalysis):
        return f"{len(d.suggested_nodes)} nodes suggested"
    if isinstance(d, MissingAttributesAnalysis):
        return f"{len(d.suggested_attributes)} attributes suggested"
    if isinstance(d, ImpliedRelationshipsAnalysis):
        return f"{len(d.suggested_relationships)} relationships suggested"
    return "ok"


def _get_suggestion_items(ar: AnalysisResult) -> list:
    """Extract countable suggestion items from an analysis result."""
    d = ar.data
    if isinstance(d, NewEntitiesAnalysis):
        return d.suggested_nodes
    if isinstance(d, MissingAttributesAnalysis):
        return d.suggested_attributes
    if isinstance(d, ImpliedRelationshipsAnalysis):
        return d.suggested_relationships
    return []


if __name__ == "__main__":
    main()
