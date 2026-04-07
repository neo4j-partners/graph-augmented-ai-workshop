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

import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
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


# ---------------------------------------------------------------------------
# Consolidated response
# ---------------------------------------------------------------------------


class AugmentationAnalysis(BaseModel):
    """Combined analysis results from all analysis types."""

    investment_themes: InvestmentThemesAnalysis | None = None
    new_entities: NewEntitiesAnalysis | None = None
    missing_attributes: MissingAttributesAnalysis | None = None
    implied_relationships: ImpliedRelationshipsAnalysis | None = None


class AugmentationResponse(BaseModel):
    """Top-level response from the augmentation agent."""

    success: bool
    analysis: AugmentationAnalysis
    all_suggested_nodes: list[SuggestedNode] = Field(default_factory=list)
    all_suggested_relationships: list[SuggestedRelationship] = Field(default_factory=list)
    all_suggested_attributes: list[SuggestedAttribute] = Field(default_factory=list)
    high_confidence_count: int = 0
    total_suggestions: int = 0

    def compute_statistics(self) -> None:
        """Recompute counts from the suggestion lists."""
        all_items = (
            self.all_suggested_nodes
            + self.all_suggested_relationships
            + self.all_suggested_attributes
        )
        self.total_suggestions = len(all_items)
        self.high_confidence_count = sum(
            1 for s in all_items if s.confidence == ConfidenceLevel.HIGH
        )


# ---------------------------------------------------------------------------
# Instance-level enrichment proposals
# ---------------------------------------------------------------------------


class NodeReference(BaseModel):
    """A reference to a specific node in the graph."""

    label: str = Field(..., description="Node label (e.g., 'Customer')")
    key_property: str = Field(..., description="Property name used as identifier (e.g., 'customerId')")
    key_value: str = Field(..., description="Property value (e.g., 'C0001')")


class EnrichmentProposal(BaseModel):
    """A concrete, instance-level proposal to add a relationship between two specific nodes."""

    source_node: NodeReference
    relationship_type: str = Field(..., description="Relationship type (e.g., 'INTERESTED_IN')")
    target_node: NodeReference
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM)
    source_document: str = Field(..., description="Document that contains the evidence")
    extracted_phrase: str = Field(..., description="Quoted phrase supporting the proposal")


class EnrichmentResult(BaseModel):
    """Result of resolving schema-level suggestions into instance-level proposals."""

    proposals: list[EnrichmentProposal] = Field(default_factory=list)
    approved: list[EnrichmentProposal] = Field(default_factory=list)
    flagged: list[EnrichmentProposal] = Field(default_factory=list)
    rejected: list[EnrichmentProposal] = Field(default_factory=list)

    @property
    def approved_count(self) -> int:
        return len(self.approved)

    @property
    def flagged_count(self) -> int:
        return len(self.flagged)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected)


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


# ═══════════════════════════════════════════════════════════════════════
# CONSOLIDATION — merge analysis results into AugmentationResponse
# ═══════════════════════════════════════════════════════════════════════


def _consolidate(results: list[AnalysisResult]) -> AugmentationResponse:
    """Merge individual analysis results into a single AugmentationResponse."""
    analysis = AugmentationAnalysis()
    nodes: list[SuggestedNode] = []
    rels: list[SuggestedRelationship] = []
    attrs: list[SuggestedAttribute] = []
    any_ok = False

    for r in results:
        if r is None or not r.success or r.data is None:
            tag = "None" if r is None else (r.error or "no data")
            name = r.name if r else "unknown"
            print(f"  [{name}] FAILED: {tag}")
            continue

        any_ok = True
        print(f"  [{r.name}] OK")

        if isinstance(r.data, InvestmentThemesAnalysis):
            analysis.investment_themes = r.data
        elif isinstance(r.data, NewEntitiesAnalysis):
            analysis.new_entities = r.data
            nodes.extend(r.data.suggested_nodes)
        elif isinstance(r.data, MissingAttributesAnalysis):
            analysis.missing_attributes = r.data
            attrs.extend(r.data.suggested_attributes)
        elif isinstance(r.data, ImpliedRelationshipsAnalysis):
            analysis.implied_relationships = r.data
            rels.extend(r.data.suggested_relationships)

    resp = AugmentationResponse(
        success=any_ok,
        analysis=analysis,
        all_suggested_nodes=nodes,
        all_suggested_relationships=rels,
        all_suggested_attributes=attrs,
    )
    resp.compute_statistics()
    return resp


# ═══════════════════════════════════════════════════════════════════════
# SUPERVISOR AGENT GAP ANALYSIS QUERY
# ═══════════════════════════════════════════════════════════════════════

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


def query_supervisor_agent(endpoint_name: str, prompt: str | None = None) -> str:
    """Send a single query to the Supervisor Agent endpoint.

    Uses the Databricks SDK directly (not DSPy) since this is a
    one-shot data-fetching call, not a structured-output task.

    Args:
        endpoint_name: Serving-endpoint name from Lab 6.
        prompt: Optional custom prompt. Defaults to the comprehensive
            gap analysis query.
    """
    client = DatabricksOpenAI()
    response = client.responses.create(
        model=endpoint_name,
        input=[{"role": "user", "content": prompt or COMPREHENSIVE_GAP_QUERY}],
    )
    return response.output[0].content[0].text


# ═══════════════════════════════════════════════════════════════════════
# RESOLVER — schema-level suggestions -> instance-level proposals
# ═══════════════════════════════════════════════════════════════════════


_RESOLUTION_PROMPT_TEMPLATE = """\
You are resolving schema-level graph enrichment suggestions into specific, \
instance-level proposals that can be written to Neo4j.

The analysis phase identified these suggested relationship types:

{suggestions}

For each suggested relationship type above, identify EVERY specific pair of \
nodes where evidence in the documents supports creating this relationship. \
For each pair, provide:
- The exact source node label, key property name, and key value
- The relationship type
- The exact target node label, key property name, and key value
- The confidence level: "high" if the document explicitly states it, \
"medium" if it is strongly implied, "low" if it is only loosely suggested
- The source document filename
- The exact quoted phrase from the document that supports this proposal

Return your answer as a JSON array of objects with this exact structure:
[
  {{
    "source_node": {{"label": "Customer", "key_property": "customerId", "key_value": "C0001"}},
    "relationship_type": "INTERESTED_IN",
    "target_node": {{"label": "Sector", "key_property": "name", "key_value": "Renewable Energy"}},
    "confidence": "high",
    "source_document": "customer_profile_001.html",
    "extracted_phrase": "expressed interest in expanding his portfolio to include renewable energy stocks"
  }}
]

Return ONLY the JSON array. No commentary, no markdown fencing.
"""


def _format_suggestions(relationships: list[SuggestedRelationship]) -> str:
    """Format schema-level suggestions into text for the resolution prompt."""
    lines = []
    for i, rel in enumerate(relationships, 1):
        lines.append(
            f"{i}. ({rel.source_label})-[{rel.relationship_type}]->({rel.target_label})"
        )
        lines.append(f"   Description: {rel.description}")
        lines.append(f"   Evidence: {rel.source_evidence}")
        if rel.example_instances:
            lines.append(f"   Examples: {rel.example_instances}")
        lines.append("")
    return "\n".join(lines)


def _strip_markdown_fence(text: str) -> str:
    """Remove markdown code fences from a response, if present."""
    cleaned = text.strip()
    if "```" not in cleaned:
        return cleaned

    first = cleaned.find("```")
    last = cleaned.rfind("```")

    if first == last:
        return cleaned

    after_first = cleaned[first + 3:]
    content_start = after_first.find("\n")
    if content_start == -1:
        return cleaned
    inner = after_first[content_start + 1:]

    trailing_fence = inner.rfind("```")
    if trailing_fence == -1:
        return inner.strip()
    return inner[:trailing_fence].strip()


def _parse_proposals(text: str) -> list[EnrichmentProposal]:
    """Parse the supervisor's JSON response into EnrichmentProposal objects."""
    cleaned = _strip_markdown_fence(text)
    raw = json.loads(cleaned)
    if not isinstance(raw, list):
        raw = [raw]

    required_keys = {"label", "key_property", "key_value"}
    proposals = []

    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            print(f"  [WARN] Item {i}: not a dict, skipping")
            continue

        source = item.get("source_node")
        target = item.get("target_node")
        rel_type = item.get("relationship_type")

        if not isinstance(source, dict) or not required_keys.issubset(source):
            print(f"  [WARN] Item {i}: invalid or missing source_node, skipping")
            continue
        if not isinstance(target, dict) or not required_keys.issubset(target):
            print(f"  [WARN] Item {i}: invalid or missing target_node, skipping")
            continue
        if not rel_type:
            print(f"  [WARN] Item {i}: missing relationship_type, skipping")
            continue

        conf_str = str(item.get("confidence", "medium")).lower()
        if conf_str in ("high", "medium", "low"):
            confidence = ConfidenceLevel(conf_str)
        else:
            confidence = ConfidenceLevel.MEDIUM

        proposals.append(
            EnrichmentProposal(
                source_node=NodeReference(
                    label=source["label"],
                    key_property=source["key_property"],
                    key_value=str(source["key_value"]),
                ),
                relationship_type=rel_type,
                target_node=NodeReference(
                    label=target["label"],
                    key_property=target["key_property"],
                    key_value=str(target["key_value"]),
                ),
                confidence=confidence,
                source_document=item.get("source_document", "unknown"),
                extracted_phrase=item.get("extracted_phrase", ""),
            )
        )

    return proposals


def resolve_proposals(
    response: AugmentationResponse,
    endpoint_name: str,
) -> list[EnrichmentProposal]:
    """Resolve schema-level suggestions into instance-level proposals."""
    relationships = response.all_suggested_relationships
    if not relationships:
        print("  No suggested relationships to resolve.")
        return []

    print("\n" + "=" * 60)
    print("RESOLVING SCHEMA-LEVEL SUGGESTIONS INTO INSTANCE PROPOSALS")
    print("=" * 60)
    print(f"  Resolving {len(relationships)} suggested relationship types ...")
    print("  Calling Supervisor Agent (this may take 1-3 minutes) ...\n")

    suggestion_text = _format_suggestions(relationships)
    prompt = _RESOLUTION_PROMPT_TEMPLATE.format(suggestions=suggestion_text)

    t0 = time.time()
    raw_response = query_supervisor_agent(endpoint_name, prompt)
    elapsed = time.time() - t0

    try:
        proposals = _parse_proposals(raw_response)
        print(f"  [OK] {len(proposals)} instance-level proposals resolved in {elapsed:.1f}s")
    except (json.JSONDecodeError, TypeError) as e:
        print(f"  [WARN] Failed to parse resolver response: {e}")
        print(f"  Raw response preview: {raw_response[:500]}")
        proposals = []

    print("=" * 60)
    return proposals


# ═══════════════════════════════════════════════════════════════════════
# CONFIDENCE FILTER
# ═══════════════════════════════════════════════════════════════════════


def filter_proposals(proposals: list[EnrichmentProposal]) -> EnrichmentResult:
    """Sort proposals by confidence level into decision buckets."""
    approved: list[EnrichmentProposal] = []
    flagged: list[EnrichmentProposal] = []
    rejected: list[EnrichmentProposal] = []

    for p in proposals:
        if p.confidence == ConfidenceLevel.HIGH:
            approved.append(p)
        elif p.confidence == ConfidenceLevel.MEDIUM:
            flagged.append(p)
        else:
            rejected.append(p)

    result = EnrichmentResult(
        proposals=proposals,
        approved=approved,
        flagged=flagged,
        rejected=rejected,
    )

    print("\n" + "=" * 60)
    print("CONFIDENCE FILTER RESULTS")
    print("=" * 60)
    print(f"  Total proposals:      {len(proposals)}")
    print(f"  AUTO-APPROVED (HIGH): {result.approved_count}")
    print(f"  FLAGGED (MEDIUM):     {result.flagged_count}")
    print(f"  REJECTED (LOW):       {result.rejected_count}")

    if approved:
        print("\n  --- Auto-approved ---")
        for p in approved:
            print(
                f"    ({p.source_node.label}:{p.source_node.key_value})"
                f"-[{p.relationship_type}]->"
                f"({p.target_node.label}:{p.target_node.key_value})"
            )

    if flagged:
        print("\n  --- Flagged for review ---")
        for p in flagged:
            print(
                f"    ({p.source_node.label}:{p.source_node.key_value})"
                f"-[{p.relationship_type}]->"
                f"({p.target_node.label}:{p.target_node.key_value})"
            )

    if rejected:
        print("\n  --- Rejected ---")
        for p in rejected:
            print(
                f"    ({p.source_node.label}:{p.source_node.key_value})"
                f"-[{p.relationship_type}]->"
                f"({p.target_node.label}:{p.target_node.key_value})"
            )

    print("=" * 60)
    return result


# ═══════════════════════════════════════════════════════════════════════
# NEO4J WRITE-BACK
# ═══════════════════════════════════════════════════════════════════════


_CYPHER_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _validate_identifier(name: str, context: str) -> None:
    """Validate that a string is a safe Cypher identifier."""
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
    """Build a parameterized Cypher MERGE query for a proposal."""
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
    """Write approved proposals to Neo4j."""
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
                try:
                    query = _build_merge_query(p)
                except ValueError as e:
                    skip_msg = f"Invalid identifier: {e}"
                    report.skipped.append(skip_msg)
                    print(f"  [SKIP] {skip_msg}")
                    continue

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


# ═══════════════════════════════════════════════════════════════════════
# VALIDATION HARNESS
# ═══════════════════════════════════════════════════════════════════════


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
    neo4j_uri = os.getenv("NEO4J_URI", "")
    neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")
    dry_run = os.getenv("DRY_RUN", "true").lower() in ("true", "1", "yes")
    analysis_only = os.getenv("ANALYSIS_ONLY", "false").lower() in ("true", "1", "yes")

    print("=" * 60)
    print("Lab 7: Graph Augmentation Agent (DSPy)")
    print("=" * 60)
    print(f"  Supervisor Agent Endpoint: {supervisor_endpoint}")
    print(f"  Neo4j URI:     {neo4j_uri or '(not set)'}")
    print(f"  Dry run:       {dry_run}")
    print(f"  Analysis only: {analysis_only}")
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

    # ── Step 5: Consolidate and validate results ─────────────────────

    print("\nStep 5: Consolidate and Validate Results")
    response = _consolidate(analysis_results)

    record(
        "result_count",
        response.success,
        f"{response.total_suggestions} suggestions, "
        f"{response.high_confidence_count} high-confidence",
    )

    has_typed_output = any(
        v is not None and isinstance(v, BaseModel)
        for v in [
            response.analysis.investment_themes,
            response.analysis.new_entities,
            response.analysis.missing_attributes,
            response.analysis.implied_relationships,
        ]
    )
    record("structured_output", has_typed_output, "Pydantic models returned")

    # ── Stop here if analysis-only mode ──────────────────────────────

    if analysis_only:
        _print_summary(results)
        sys.exit(0 if all(p for _, p, _ in results) else 1)

    # ── Step 6: Resolve into instance-level proposals ────────────────

    print("\nStep 6: Resolve Instance-Level Proposals")
    try:
        proposals = resolve_proposals(response, supervisor_endpoint)
        record(
            "resolve_proposals",
            isinstance(proposals, list),
            f"{len(proposals)} proposals",
        )
    except Exception as e:
        record("resolve_proposals", False, str(e))
        _print_summary(results)
        sys.exit(1)

    # ── Step 7: Filter by confidence ─────────────────────────────────

    print("\nStep 7: Filter Proposals by Confidence")
    enrichment_result = filter_proposals(proposals)
    writable = enrichment_result.approved + enrichment_result.flagged
    record(
        "confidence_filter",
        True,
        f"{enrichment_result.approved_count} approved, "
        f"{enrichment_result.flagged_count} flagged, "
        f"{enrichment_result.rejected_count} rejected",
    )

    # ── Step 8: Write back to Neo4j ──────────────────────────────────

    print("\nStep 8: Write Enrichments to Neo4j")
    if not neo4j_uri:
        record(
            "neo4j_writeback",
            False,
            "skipped: NEO4J_URI not set",
        )
    elif not writable:
        record("neo4j_writeback", True, "no proposals to write")
    else:
        try:
            report = write_proposals(
                writable,
                neo4j_uri,
                neo4j_username,
                neo4j_password,
                dry_run=dry_run,
            )
            if dry_run:
                record(
                    "neo4j_writeback",
                    True,
                    f"dry run: {len(writable)} proposals previewed",
                )
            else:
                record(
                    "neo4j_writeback",
                    True,
                    f"{report.created} created, {report.updated} updated, "
                    f"{len(report.skipped)} skipped",
                )
        except Exception as e:
            record("neo4j_writeback", False, str(e))

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
