# Closing the Loop: Implementation Proposal for Minimum Viable Enrichment

The paper describes a seven-step enrichment loop. The implementation covers the first three steps well: extracting graph state, setting up agents, and running gap analysis. But the pipeline stops at step three. It produces schema-level suggestions ("add a HAS_GOAL relationship type") rather than instance-level proposals ("Customer C0001 is interested in Renewable Energy, confidence 0.92"), and it never writes anything back to Neo4j. Without write-back, there is no loop. Without instance-level proposals and numeric confidence, there is nothing meaningful to write back.

Three changes close this gap. Each one depends on the previous, and together they let the workshop demonstrate one complete pass through the enrichment cycle. All changes are made first in `full_demo/augmentation_agent/`, which serves as the development copy with its own CLI, dependencies, and test infrastructure. Once the implementation is working there, the changes carry over to `lab_7_augmentation_agent/` for the workshop notebooks.

## 1. Resolve Schema-Level Suggestions into Instance-Level Proposals

The four DSPy analyzers currently produce suggestions at the type level. The ImpliedRelationshipsAnalyzer might propose that INTERESTED_IN relationships should exist between Customer and Sector nodes, with example instances listed as illustrative strings. The paper's argument depends on something different: a concrete proposal that names Customer C0001, names the Sector Renewable Energy, quotes a specific phrase from a specific document, and carries a confidence level.

The approach is to add a resolution step after the existing analysis. The analyzers would continue producing their current output. A new resolver would take that output and cross-reference it against the actual graph state and document corpus to generate specific node-to-node proposals. For each suggested relationship type, the resolver would identify which specific source and target nodes the relationship should connect, pull the supporting evidence from the document that justifies it, and attach a confidence level.

The resolver would call back into the supervisor agent endpoint. The supervisor already coordinates Genie (for structured graph queries) and the Knowledge Assistant (for document retrieval), so it can reason about whether a document phrase actually supports a specific customer-sector pairing. A direct query approach would require building that matching logic from scratch, reimplementing what the supervisor already does with lower accuracy. For a workshop where proposal quality is the whole point, the supervisor is the correct choice. Cost is per-run against a small customer set, not continuous.

The resolver would take a schema-level suggestion like "Customers have implied INTERESTED_IN relationships with Sectors based on document analysis" and ask the supervisor to identify every specific customer-sector pair where the evidence supports the relationship, returning the source document and extracted phrase for each.

The output format would match the paper's enrichment proposal structure: source node with label and key, relationship type, target node with label and key, confidence level (HIGH, MEDIUM, or LOW), source document identifier, and the extracted phrase that supports the proposal.

## 2. Map Confidence Levels to Tiered Decisions

The current implementation uses a three-level enum (HIGH, MEDIUM, LOW) but attaches no decision logic to those levels. The paper's core mechanism is tiered decision-making: some proposals auto-approve, some get flagged, some get rejected. The existing enum maps directly to that without requiring numeric scores.

HIGH proposals auto-approve and proceed to write-back. MEDIUM proposals write back but get flagged in the output for human review. LOW proposals get rejected and reported but not written to the graph. This gives the pipeline the same three-bucket behavior the paper describes. Asking the language model to produce calibrated floats is genuinely hard to do reliably; the enum sidesteps that problem while preserving the decision mechanism that matters.

The filter step would sit between the resolver and write-back. It would sort instance-level proposals by their confidence level into the three buckets, then pass the HIGH and MEDIUM proposals forward. The output would report counts for each bucket so the workshop can show how many proposals were auto-approved, how many were flagged, and how many were rejected.

The existing `compute_statistics` method on `AugmentationResponse` would shift from simply counting confidence levels to reporting proposal counts by decision bucket: how many written (HIGH), how many written-with-flag (MEDIUM), how many rejected (LOW).

## 3. Write Approved Proposals Back to Neo4j

The pipeline currently ends at JSON output. The paper's central claim is that each enrichment cycle changes the graph, which changes what the next cycle discovers. Without write-back, there is no cycle.

The write-back step would take every HIGH and MEDIUM proposal and generate a Cypher MERGE statement for it. The paper specifies the pattern: MATCH the source node, MATCH the target node, MERGE the relationship between them, and SET provenance properties on the relationship. Those properties would include the confidence level, source document, extracted phrase, and a timestamp marking when the enrichment occurred.

Write-back only creates relationships between nodes that already exist in the graph. It does not create new nodes. If a proposal references a target node that does not exist (like a Sector node for "Renewable Energy"), that proposal gets surfaced as a separate "node creation needed" item in the output rather than silently creating the node during write-back. The risk with unchecked node creation from LLM output is name variation: the model might propose "Renewable Energy" in one proposal and "Renewables" in another, creating two nodes for the same concept. For the workshop, the practical approach is to pre-populate the expected target nodes (Sectors, Themes) during lab setup, so the enrichment step only creates relationships. That sidesteps the naming problem entirely and keeps write-back simple.

Relationship types are written freely to Neo4j without an allowlist or validation step. Neo4j is schema-free for relationship types, so INTERESTED_IN, CONCERNED_ABOUT, and any other type the analyzers propose will work without schema migration. Ontology validation to prevent type sprawl is part of the long-term plan, not the minimum implementation.

MERGE is idempotent. Running the same proposal twice creates no duplicates. If a proposal already exists in the graph with the same source, target, and relationship type, the MERGE updates the properties rather than creating a second relationship.

The implementation already has Neo4j write infrastructure in the lab setup code, which uses the Spark Connector to write DataFrames as nodes and relationships. The write-back step for enrichment proposals would be simpler: it would use the Neo4j Python driver directly to execute Cypher MERGE statements, since each proposal is a single relationship with properties rather than a bulk data load. The driver connection details are already available in the environment from the lab setup.

After write-back completes, the step would report what it wrote: how many relationships created, how many updated, and how many proposals skipped because their target node did not exist.

## How the Three Changes Connect

The resolver produces instance-level proposals from the existing schema-level analysis. Confidence levels filter those proposals into action buckets. Write-back executes the approved proposals against Neo4j. Running the pipeline a second time would then start from a graph that contains those new relationships, and the gap analysis would reflect the changed state. That is the compounding behavior the paper argues for. One pass through the loop is sufficient for the workshop to demonstrate the mechanism; the paper explains the compounding that subsequent passes produce.

None of these changes require reworking the existing analyzers or the supervisor agent. The four DSPy modules continue producing their current output. The new work layers on top: resolve, filter, write.

## Implementation Order

All work starts in `full_demo/augmentation_agent/`. This directory has its own `pyproject.toml`, CLI entry point, virtual environment, and test scripts in `full_demo/agent_modules/`. It is the right place to iterate because changes can be run and validated locally through the CLI without needing a Databricks notebook environment.

**Step 1: Schema changes in `full_demo/augmentation_agent/schemas.py`.** Add the instance-level proposal model (source node, relationship type, target node, confidence level, source document, extracted phrase). Add a resolution response model that holds a list of these proposals alongside summary counts by decision bucket. The existing schema-level models stay unchanged since the analyzers still produce them.

**Step 2: Resolver in `full_demo/augmentation_agent/`.** Add a resolver module that takes the existing `AugmentationResponse` and calls the supervisor endpoint to resolve schema-level suggestions into instance-level proposals. This module sits between the existing analysis step and the new filter/write-back steps.

**Step 3: Confidence filter in `full_demo/augmentation_agent/`.** Add a filter that takes the resolver's instance-level proposals and sorts them into HIGH (auto-approve), MEDIUM (approve with flag), and LOW (reject) buckets. Pass HIGH and MEDIUM proposals forward. Report counts for all three buckets.

**Step 4: Write-back in `full_demo/augmentation_agent/`.** Add a Neo4j write-back module that takes approved proposals and executes Cypher MERGE statements via the Neo4j Python driver. Each MERGE creates a relationship with provenance properties. Proposals whose target node does not exist in the graph get reported as skipped.

**Step 5: Wire the pipeline in `full_demo/augmentation_agent/__main__.py`.** Update the CLI entry point to chain the existing analysis into the resolver, then the filter, then write-back. Add CLI flags for Neo4j connection details and a dry-run mode that reports what would be written without executing.

**Step 6: Validate end-to-end through `full_demo/cli/`.** Run the full pipeline against the workshop's Neo4j instance. Verify that proposals are generated, filtered, and written. Confirm idempotency by running twice and checking that no duplicates appear.

**Step 7: Port to `lab_7_augmentation_agent/`.** Once the implementation is validated in `full_demo/`, carry the schema changes, resolver, filter, and write-back modules into the lab notebook codebase. Adapt the entry point for the Databricks notebook environment rather than CLI invocation.