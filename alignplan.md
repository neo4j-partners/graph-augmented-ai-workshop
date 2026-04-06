# Closing the Loop: Implementation Proposal for Minimum Viable Enrichment

The paper describes a seven-step enrichment loop. The implementation covers the first three steps well: extracting graph state, setting up agents, and running gap analysis. But the pipeline stops at step three. It produces schema-level suggestions ("add a HAS_GOAL relationship type") rather than instance-level proposals ("Customer C0001 is interested in Renewable Energy, confidence 0.92"), and it never writes anything back to Neo4j. Without write-back, there is no loop. Without instance-level proposals and numeric confidence, there is nothing meaningful to write back.

Three changes close this gap. Each one depends on the previous, and together they let the workshop demonstrate one complete pass through the enrichment cycle.

## 1. Resolve Schema-Level Suggestions into Instance-Level Proposals

The four DSPy analyzers currently produce suggestions at the type level. The ImpliedRelationshipsAnalyzer might propose that INTERESTED_IN relationships should exist between Customer and Sector nodes, with example instances listed as illustrative strings. The paper's argument depends on something different: a concrete proposal that names Customer C0001, names the Sector Renewable Energy, quotes a specific phrase from a specific document, and carries a numeric confidence score.

The approach is to add a resolution step after the existing analysis. The analyzers would continue producing their current output. A new resolver would take that output and cross-reference it against the actual graph state and document corpus to generate specific node-to-node proposals. For each suggested relationship type, the resolver would identify which specific source and target nodes the relationship should connect, pull the supporting evidence from the document that justifies it, and attach a confidence score.

This resolver would call back into the supervisor agent endpoint. It would take a schema-level suggestion like "Customers have implied INTERESTED_IN relationships with Sectors based on document analysis" and ask the supervisor to identify every specific customer-sector pair where the evidence supports the relationship. The supervisor already has access to both Genie (for structured graph queries) and the Knowledge Assistant (for document retrieval), so it can cross-reference customer identities against document mentions to produce instance-level results.

The output format would match the paper's enrichment proposal structure: source node with label and key, relationship type, target node with label and key, numeric confidence, source document identifier, and the extracted phrase that supports the proposal.

## 2. Replace the Confidence Enum with Numeric Scores and Threshold-Based Decisions

The current implementation uses a three-level enum: HIGH, MEDIUM, LOW. The paper defines a numeric system where 0.95 auto-approves, 0.70 approves with a flag, 0.40 queues for review, and below 0.30 rejects. The enum carries no decision logic. Replacing it with a float between 0.0 and 1.0 lets the pipeline make threshold-based decisions about what to do with each proposal.

The change has two parts. First, the schema models would use a numeric confidence field instead of the enum. The DSPy signatures would instruct the language model to produce a float score reflecting extraction certainty, with guidance on what the scale means: direct statements of intent score higher than indirect mentions, and multiple corroborating documents boost confidence above any single extraction.

Second, a filter step would sort proposals into buckets based on configurable thresholds. Proposals above the auto-approve threshold proceed directly to write-back. Proposals in the middle range get flagged for review but still proceed. Proposals below the reject threshold are discarded. The thresholds themselves would be configurable parameters, not hardcoded values, so they can be adjusted for the workshop demonstration or tuned for different risk tolerances in production.

The existing `compute_statistics` method on `AugmentationResponse` would shift from counting HIGH/MEDIUM/LOW to reporting proposal counts by threshold bucket: how many auto-approved, how many flagged, how many rejected.

## 3. Write Approved Proposals Back to Neo4j

The pipeline currently ends at JSON output. The paper's central claim is that each enrichment cycle changes the graph, which changes what the next cycle discovers. Without write-back, there is no cycle.

The write-back step would take every proposal that passed the confidence threshold and generate a Cypher MERGE statement for it. The paper already specifies the pattern: MERGE the target node if it does not exist, MATCH the source node, MERGE the relationship between them, and SET provenance properties on the relationship. Those properties would include the confidence score, source document, extracted phrase, and a timestamp marking when the enrichment occurred.

MERGE is idempotent. Running the same proposal twice creates no duplicates. This matters because it means the write-back step does not need sophisticated deduplication logic. If a proposal already exists in the graph with the same source, target, and relationship type, the MERGE updates the properties rather than creating a second relationship.

The implementation already has Neo4j write infrastructure in the lab setup code, which uses the Spark Connector to write DataFrames as nodes and relationships. The write-back step for enrichment proposals would be simpler: it would use the Neo4j Python driver directly to execute Cypher MERGE statements, since each proposal is a single relationship with properties rather than a bulk data load. The driver connection details are already available in the environment from the lab setup.

After write-back completes, the step would report what it wrote: how many relationships created, how many updated, and how many target nodes were newly created versus already existing.

## How the Three Changes Connect

The resolver produces instance-level proposals from the existing schema-level analysis. Numeric confidence scoring filters those proposals into action buckets. Write-back executes the approved proposals against Neo4j. Running the pipeline a second time would then start from a graph that contains those new relationships, and the gap analysis would reflect the changed state. That is the compounding behavior the paper argues for.

None of these changes require reworking the existing analyzers or the supervisor agent. The four DSPy modules continue producing their current output. The new work layers on top: resolve, score, filter, write.

## Open Questions

A few decisions would shape the implementation:

**Where does the resolver run?** The resolver needs to cross-reference schema-level suggestions against actual graph data and documents to produce instance-level proposals. It could call the supervisor agent endpoint (which already coordinates Genie and the Knowledge Assistant), or it could query Neo4j and the document store directly. Using the supervisor keeps the architecture consistent with the paper's multi-agent design, but it adds inference cost and latency for each resolution call. Querying directly is faster but duplicates coordination logic that already exists in the supervisor.

**How should the DSPy signatures guide numeric scoring?** The language model currently assigns HIGH/MEDIUM/LOW without explicit criteria. Shifting to numeric scores means the signature prompts need to define what the scale represents. Should the prompt include the paper's specific examples ("expressed strong interest in" maps to 0.95, "mentioned considering" maps to 0.70)? Or should it describe the scale in general terms and let the model calibrate? Explicit examples produce more consistent scores but may not generalize well beyond the workshop's document corpus.

keep at HIGH/MEDIUM/LOW

**What happens when a target node does not exist in the graph?** If the resolver proposes an INTERESTED_IN relationship between Customer C0001 and a Sector node for Renewable Energy, but no Sector node with that key exists in the graph, the MERGE statement will create it. Should the write-back step create these nodes freely, or should node creation require a higher confidence threshold or separate approval? Creating nodes changes the graph's schema in a way that creating relationships between existing nodes does not.


what would the best practice be?

**Should the workshop demonstrate one pass or two?** One complete pass through the loop (extract, analyze, propose, score, write) demonstrates that the mechanism works. Two passes demonstrate compounding, where the second run discovers different gaps because the first run changed the graph. Two passes are more compelling but double the workshop time and inference cost. Is the second pass essential for the workshop, or is it sufficient to explain that a second run would operate on the changed graph?

one pass is fine?

**How do we handle proposals for relationship types the analyzers suggest but the graph schema does not yet include?** The ImpliedRelationshipsAnalyzer might suggest CONCERNED_ABOUT relationships. If that relationship type does not exist in the graph's current schema, writing it is trivially supported by Neo4j (schema-free for relationship types), but it means the enrichment pipeline is evolving the graph's schema without the ontology validation layer described in the paper's long-term plan. Is that acceptable for the minimum viable implementation, or should the minimum include a simple allowlist of approved relationship types?


yes let's add the relationship types it is ok to not have validation initially 