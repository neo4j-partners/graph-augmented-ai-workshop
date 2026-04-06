# Graph Augmentation Agent

A standalone DSPy demo that analyzes unstructured documents through a Databricks Supervisor Agent and proposes structured graph schema improvements for Neo4j. This is the reference implementation for Lab 7 of the Graph-Augmented AI Workshop.

## Quick Start

```bash
cd solutions
python -m augmentation_agent --supervisor-endpoint <your-supervisor-agent-endpoint>
```

The agent runs a five-step pipeline: authenticate with Databricks, configure DSPy, query the Supervisor Agent for a gap analysis, run four concurrent DSPy analyses against the gap text, and validate the structured results.

### Prerequisites

- Python 3.10+ with `dspy>=3.0.4`, `databricks-sdk`, and `pydantic` installed
- A Databricks workspace with an active Supervisor Agent endpoint from Lab 6
- Authentication configured: either Databricks runtime credentials (on-cluster) or `DATABRICKS_HOST` and `DATABRICKS_TOKEN` environment variables (local)

### CLI Options

```
--supervisor-endpoint   Supervisor Agent endpoint name (default: mas-3ae5a347-endpoint)
--temperature    LM temperature (default: 0.1)
--max-tokens     Maximum response tokens (default: 4000)
```

## Architecture

The Neo4j graph in this workshop captures what customers hold: accounts, positions, securities, all connected by typed relationships that Cypher traverses in milliseconds. Customer intent, however, lives in unstructured profile documents and market research PDFs that the graph cannot see. A profile might say "Maria Rodriguez is focused on sustainable investing and plans to retire in 10 years," but none of that reaches the graph as queryable structure.

This agent bridges that gap. It reads the unstructured documents through a Supervisor Agent (which coordinates a Genie agent for structured data and a Knowledge Assistant for documents), then uses DSPy to decompose the free-text gap analysis into four typed proposals for graph enrichment: new node types, missing attributes on existing nodes, implied relationships, and investment themes.

### Data Flow

```
Unstructured Documents + Graph Data
        |
        v
  Supervisor Agent (Databricks)
  ├── Genie Agent ──> structured queries
  └── Knowledge Assistant ──> document retrieval
        |
        v
  Gap Analysis Text (~2-5k chars)
        |
        v
  DSPy Parallel Analyzers (4 concurrent)
  ├── InvestmentThemesAnalyzer
  ├── NewEntitiesAnalyzer
  ├── MissingAttributesAnalyzer
  └── ImpliedRelationshipsAnalyzer
        |
        v
  AugmentationResponse (Pydantic)
  ├── SuggestedNode[]
  ├── SuggestedRelationship[]
  ├── SuggestedAttribute[]
  └── InvestmentTheme[]
```

The Supervisor Agent query takes 1-3 minutes. The four DSPy analyses run concurrently via `dspy.Parallel` and typically complete in 30-60 seconds total.

### Module Responsibilities

The package splits into six modules, each with a single concern:

| Module | Responsibility |
|---|---|
| `schemas.py` | Pydantic models for all structured output. No DSPy dependency. |
| `signatures.py` | DSPy `Signature` classes that pair input fields with Pydantic output types. |
| `lm.py` | `DatabricksResponsesLM`, a custom `dspy.BaseLM` subclass for Supervisor Agent endpoints. |
| `supervisor_client.py` | Plain Databricks SDK calls to query the Supervisor Agent. No DSPy dependency. |
| `analyzers.py` | DSPy `Module` classes wrapping `ChainOfThought` predictors, plus the composite `GraphAugmentationAnalyzer` orchestrator. |
| `reporting.py` | Pretty-printing and the `ValidationHarness` for PASS/FAIL output. |

`__main__.py` wires these together into the five-step CLI pipeline.

## Tutorial

### Step 1: Schemas Define the Output Shape

Everything starts with `schemas.py`. These are plain Pydantic models that describe what graph enrichment proposals look like, independent of how they are produced. A `SuggestedNode` carries a label, key property, confidence level, and source evidence. A `SuggestedRelationship` names its source and target labels plus a relationship type. Each suggestion includes a `ConfidenceLevel` enum (HIGH, MEDIUM, LOW) so downstream consumers can filter by certainty.

The top-level `AugmentationResponse` consolidates all four analysis types and exposes `compute_statistics()` to tally total suggestions and high-confidence counts.

```python
class SuggestedNode(BaseModel):
    label: str
    key_property: str
    confidence: ConfidenceLevel
    source_evidence: str
    # ... properties, examples, rationale
```

Because these models carry no DSPy dependency, they can be serialized to JSON, stored in Delta Lake, or passed directly to a Neo4j write pipeline.

### Step 2: Signatures Declare What DSPy Should Produce

Each `dspy.Signature` in `signatures.py` pairs a `document_context` input field with a Pydantic output type. The class docstring becomes the task description that DSPy includes in the generated prompt.

```python
class NewEntitiesSignature(dspy.Signature):
    """Analyze documents to suggest new entity types for the graph database."""

    document_context: str = dspy.InputField(...)
    analysis: NewEntitiesAnalysis = dspy.OutputField(...)
```

DSPy handles prompt construction and response parsing automatically. The signature author specifies *what* the LM should produce; DSPy determines *how* to ask for it and how to extract the structured result from the response.

### Step 3: The Custom LM Adapter Speaks Responses API

The Databricks Supervisor Agent endpoint uses the OpenAI Responses API format (`input` array, not `messages`), and it only supports single-turn conversations. `DatabricksResponsesLM` in `lm.py` handles both constraints.

The class extends `dspy.BaseLM` and overrides `forward()`, which is the documented extension point in DSPy 3.x. It does not override `__call__()`. This distinction matters: `BaseLM.__call__` is decorated with `@with_callbacks` and routes the return value through `_process_lm_response()` for caching, history tracking, and usage metrics. Overriding `__call__` would silently bypass all of that.

```python
class DatabricksResponsesLM(dspy.BaseLM):
    def __init__(self, model, **kwargs):
        super().__init__(model=model, model_type="responses", **kwargs)

    def forward(self, prompt=None, messages=None, **kwargs):
        # Combine multi-turn messages into single user message
        # Call client.responses.create()
        # Return raw OpenAI response object
```

Setting `model_type="responses"` tells DSPy to route output extraction through `_process_response()` instead of `_process_completion()`, matching the response shape that the Supervisor Agent endpoint returns.

`configure_dspy()` creates the LM and calls `dspy.configure(lm=lm, track_usage=True)`. `ChatAdapter` is the default adapter in DSPy 3.x and does not need to be set explicitly.

### Step 4: Analyzers Wrap ChainOfThought

Each analyzer in `analyzers.py` is a `dspy.Module` with a single `ChainOfThought` predictor. `ChainOfThought` adds step-by-step reasoning before producing the structured output, which improves result quality for complex analytical tasks.

```python
class NewEntitiesAnalyzer(dspy.Module):
    def __init__(self):
        super().__init__()
        self.analyze = dspy.ChainOfThought(NewEntitiesSignature)

    def forward(self, document_context: str) -> AnalysisResult:
        result = self.analyze(document_context=document_context)
        return AnalysisResult(
            name="new_entities",
            success=True,
            data=result.analysis,
            reasoning=getattr(result, "reasoning", None),
        )
```

All four analyzers return a uniform `AnalysisResult` dataclass, which carries the analyzer name, success flag, typed data, and optional error or reasoning text.

### Step 5: Parallel Execution via dspy.Parallel

`GraphAugmentationAnalyzer` is the composite orchestrator. It registers all four analyzers as sub-modules, then runs them concurrently through `dspy.Parallel`.

```python
example = dspy.Example(document_context=document_context).with_inputs("document_context")
exec_pairs = [(getattr(self, name), example) for name in self._names]

parallel = dspy.Parallel(
    num_threads=len(exec_pairs),
    max_errors=len(exec_pairs),
    provide_traceback=True,
)
results = parallel(exec_pairs)
```

`dspy.Parallel` properly propagates DSPy's thread-local settings (configured LM, adapter, callbacks) to worker threads. A plain `ThreadPoolExecutor` would lose this context and fail silently. Setting `max_errors` equal to the number of analyses ensures partial results are collected even if some analyses fail.

After all analyses complete, `_consolidate()` merges the individual results into a single `AugmentationResponse` with aggregated suggestion lists and computed statistics.

### Step 6: The Supervisor Agent Client Queries for Gap Analysis

`supervisor_client.py` is independent of DSPy. It sends a comprehensive four-part gap analysis prompt to the Supervisor Agent endpoint using the Databricks SDK's OpenAI-compatible client. The prompt asks the supervisor to compare structured graph holdings against unstructured document content, identifying gaps in customer interests, missing entity relationships, absent customer attributes, and investment themes.

The returned text (typically 2,000-5,000 characters) becomes the `document_context` input to all four DSPy analyzers.

## DSPy Best Practices Applied

This implementation follows several patterns recommended for DSPy 3.x:

- **`BaseLM.forward()` not `__call__()`** for custom LM adapters, preserving the callback and caching infrastructure
- **`model_type="responses"`** for endpoints that return Responses API format
- **Pydantic output types on signatures** for type-safe structured output without manual JSON parsing
- **`dspy.Parallel`** instead of raw threading, ensuring thread-local DSPy settings propagate correctly
- **`ChainOfThought`** for analytical tasks that benefit from explicit reasoning steps
- **No explicit `ChatAdapter`**, relying on the DSPy 3.x default
- **Separation of schemas from signatures**, keeping Pydantic models reusable outside DSPy

## Limitations

The Supervisor Agent endpoint is the bottleneck. Each gap analysis query takes 1-3 minutes because the supervisor coordinates multiple sub-agents. The DSPy analyses themselves are fast by comparison, but they depend entirely on the quality and completeness of the gap text the Supervisor Agent returns.

The four analyses run independently against the same input text. They do not cross-reference each other's findings. A suggested `INTERESTED_IN` relationship from the relationships analyzer and a suggested `InvestmentInterest` node from the entities analyzer might overlap without either being aware of the other. Downstream consumers should deduplicate.

Confidence levels are self-assessed by the LM. They correlate with the strength of textual evidence but are not calibrated against ground truth.
