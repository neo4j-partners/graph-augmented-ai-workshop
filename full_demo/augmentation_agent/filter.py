"""Confidence-based filter for enrichment proposals.

Sorts instance-level proposals into three decision buckets:
- HIGH  -> auto-approve, proceed to write-back
- MEDIUM -> approve with flag for human review, proceed to write-back
- LOW   -> reject, report but do not write

Both HIGH and MEDIUM proposals are passed forward to write-back.
"""

from __future__ import annotations

from augmentation_agent.schemas import (
    ConfidenceLevel,
    EnrichmentProposal,
    EnrichmentResult,
)


def filter_proposals(proposals: list[EnrichmentProposal]) -> EnrichmentResult:
    """Sort proposals by confidence level into decision buckets.

    Args:
        proposals: Instance-level proposals from the resolver.

    Returns:
        EnrichmentResult with proposals sorted into approved, flagged,
        and rejected lists.
    """
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
