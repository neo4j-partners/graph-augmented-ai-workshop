"""Resolve schema-level suggestions into instance-level enrichment proposals.

Takes the AugmentationResponse (schema-level: "add INTERESTED_IN between
Customer and Sector") and calls the Supervisor Agent to produce concrete
proposals ("Customer C0001 -> INTERESTED_IN -> Sector RenewableEnergy").

The Supervisor Agent coordinates Genie (structured graph queries) and the
Knowledge Assistant (document retrieval) to cross-reference each suggestion
against actual graph data and documents.
"""

from __future__ import annotations

import json
import time

from augmentation_agent.schemas import (
    AugmentationResponse,
    ConfidenceLevel,
    EnrichmentProposal,
    NodeReference,
    SuggestedRelationship,
)
from augmentation_agent.supervisor_client import query_supervisor_agent


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

    # Need two distinct fence markers to extract content between them
    if first == last:
        return cleaned

    # Skip the opening fence line (e.g. ```json)
    after_first = cleaned[first + 3:]
    content_start = after_first.find("\n")
    if content_start == -1:
        return cleaned
    inner = after_first[content_start + 1:]

    # Remove trailing fence
    trailing_fence = inner.rfind("```")
    if trailing_fence == -1:
        return inner.strip()
    return inner[:trailing_fence].strip()


def _parse_proposals(text: str) -> list[EnrichmentProposal]:
    """Parse the supervisor's JSON response into EnrichmentProposal objects.

    Parses each item individually so that a malformed item does not
    discard the entire batch.
    """
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
    """Resolve schema-level suggestions into instance-level proposals.

    Calls the Supervisor Agent to cross-reference suggested relationship
    types against actual graph data and documents.

    Args:
        response: The schema-level AugmentationResponse from the analyzers.
        endpoint_name: Supervisor Agent serving endpoint name.

    Returns:
        List of concrete EnrichmentProposal instances.
    """
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
