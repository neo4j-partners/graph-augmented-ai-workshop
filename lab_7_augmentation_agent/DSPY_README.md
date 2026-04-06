# DSPy Graph Augmentation Agent - Quick Start

This guide covers running the DSPy-based Graph Augmentation Agent locally and on Databricks.

## Quick Start (Local)

```bash
# Sync dependencies (includes dspy>=3.0.4 and mlflow[databricks]>=3.1)
uv sync

# Run all analyses
uv run python -m lab_7_augmentation_agent.agent_dspy
```

On Databricks, use the `augmentation_dspy_agent.ipynb` notebook which runs each analysis in separate cells.

## Environment Setup

Ensure your `.env` file contains:

```
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your-personal-access-token
SUPERVISOR_AGENT_ENDPOINT=your-supervisor-agent-endpoint
```

## Databricks Cluster Dependencies

Install these packages on your Databricks cluster:

| Package | Version | Purpose |
|---------|---------|---------|
| `dspy` | `>=3.0.4` | DSPy framework for programmatic AI |
| `mlflow[databricks]` | `>=3.1` | Tracing and experiment tracking |
| `pydantic` | `>=2.0.0` | Structured output schemas |
| `python-dotenv` | `>=1.0.0` | Environment configuration |

Install via cluster libraries or notebook:

```python
%pip install dspy>=3.0.4 mlflow[databricks]>=3.1 pydantic>=2.0.0 python-dotenv>=1.0.0
dbutils.library.restartPython()
```

## Project Structure

```
lab_7_augmentation_agent/
├── agent_dspy.py           # Main entry point
├── schemas.py              # Pydantic models for structured output
├── dspy_modules/
│   ├── __init__.py
│   ├── config.py           # DSPy + Databricks LM configuration
│   ├── signatures.py       # DSPy signatures for each analysis type
│   └── analyzers.py        # DSPy modules that perform analysis
├── DSPY_README.md          # This file
└── DSPYING.md              # Implementation proposal
```

## How It Works

### DSPy Signatures

Each analysis type has a declarative signature that defines inputs and outputs:

```python
class NewEntitiesSignature(dspy.Signature):
    """Analyze documents to suggest new entity types for the graph database."""

    document_context: str = dspy.InputField(
        desc="HTML data and documents containing entity information"
    )
    analysis: NewEntitiesAnalysis = dspy.OutputField(
        desc="Structured suggestions for new node types"
    )
```

DSPy automatically:
1. Generates prompts from the signature docstring and field descriptions
2. Calls the language model
3. Parses responses into your Pydantic types

### ChainOfThought Reasoning

Each analyzer uses `dspy.ChainOfThought` which encourages step-by-step reasoning:

```python
class NewEntitiesAnalyzer(dspy.Module):
    def __init__(self):
        self.analyze = dspy.ChainOfThought(NewEntitiesSignature)

    def forward(self, document_context: str):
        result = self.analyze(document_context=document_context)
        return result.analysis  # Typed NewEntitiesAnalysis
```

### Custom LM Adapter for Supervisor Agent

The agent includes a custom `DatabricksResponsesLM` class that works with Supervisor Agent endpoints. Supervisor Agent endpoints use the Databricks Responses API format instead of OpenAI Chat Completions:

```python
# Responses API format (Supervisor Agent endpoints)
client.responses.create(
    model="mas-endpoint",
    input=[{"role": "user", "content": "..."}]
)

# vs OpenAI format (Foundation Model APIs)
client.chat.completions.create(
    model="model-name",
    messages=[{"role": "user", "content": "..."}]
)
```

The `DatabricksResponsesLM` adapter handles this conversion automatically. This implementation only supports Supervisor Agent endpoints.

## Comparison with Original Agent

| Feature | Original (`augmentation_agent.py`) | DSPy (`agent_dspy.py`) |
|---------|-----------------------------------|------------------------|
| Prompt engineering | Manual prompt strings | Declarative signatures |
| JSON parsing | Regex extraction + manual parsing | Automatic via DSPy |
| Type safety | Post-hoc validation | Native Pydantic types |
| Error handling | Try/except around parsing | Built into DSPy |
| Optimization | Not supported | DSPy compiler ready |
| Lines of code | ~1200 | ~300 |

## Troubleshooting

### Authentication Errors

```
RuntimeError: Databricks credentials not found
```

Ensure `.env` has `DATABRICKS_HOST` and `DATABRICKS_TOKEN` set correctly.

### Import Errors

```
ModuleNotFoundError: No module named 'dspy'
```

Run `uv sync` to install dependencies.

### Parsing Failures

If DSPy fails to parse structured output, it will retry automatically. For persistent issues:

1. Simplify the Pydantic schema (reduce nesting depth to 2-3 levels)
2. Add clearer `Field(description=...)` hints for complex fields
3. Check MLflow traces to see what the model is actually returning
4. Ensure your Supervisor Agent endpoint is responding correctly (test with a simple query first)

## Best Practices for DSPy with Supervisor Agent

When building DSPy agents that use Databricks Supervisor Agent endpoints for structured output, follow these best practices:

### 1. Use the Custom LM Adapter for Supervisor Agent

Supervisor Agent endpoints use the Databricks Responses API format, not OpenAI Chat Completions. Always use the `DatabricksResponsesLM` adapter:

```python
from lab_7_augmentation_agent.dspy_modules.config import configure_dspy

# This automatically uses DatabricksResponsesLM for Supervisor Agent endpoints
lm = configure_dspy(model_name="your-supervisor-agent-endpoint")
```

**Do NOT** use `dspy.LM` or `dspy.OpenAI` directly with Supervisor Agent endpoints—they send the wrong API format.

### 2. Use ChatAdapter, Not JSONAdapter

Supervisor Agent endpoints require `ChatAdapter` for structured output. JSONAdapter is not supported:

```python
import dspy

# Correct for Supervisor Agent
adapter = dspy.ChatAdapter()

# Wrong - will fail with Supervisor Agent
# adapter = dspy.JSONAdapter()
```

### 3. Define Pydantic Models in a Separate schemas.py

Keep your Pydantic models in a dedicated file for reusability:

```python
# schemas.py
from pydantic import BaseModel, Field
from enum import Enum

class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class SuggestedNode(BaseModel):
    label: str = Field(..., description="Node label")
    description: str = Field(..., description="What this node represents")
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM)
```

**Best practices for Pydantic models:**
- Use `Field(...)` with descriptions—DSPy uses these in prompt generation
- Use enums for constrained string values
- Keep nesting shallow (2-3 levels max) for reliable parsing
- Use `list[Model]` for collections, not `List[Model]`

### 4. Write Declarative Signatures with Clear Docstrings

The signature docstring becomes part of the prompt. Make it specific:

```python
# Good - specific and actionable
class NewEntitiesSignature(dspy.Signature):
    """
    Analyze documents to suggest new entity types for the graph database.

    Identify entities that should be extracted and added as new node types,
    including their properties, key identifiers, and example values.
    """
    document_context: str = dspy.InputField(
        desc="HTML data and documents containing entity information to extract"
    )
    analysis: NewEntitiesAnalysis = dspy.OutputField(
        desc="Structured suggestions for new node types with properties and examples"
    )

# Bad - vague and generic
class BadSignature(dspy.Signature):
    """Analyze stuff."""
    input: str = dspy.InputField()
    output: dict = dspy.OutputField()
```

### 5. Use ChainOfThought for Complex Analysis

`ChainOfThought` encourages step-by-step reasoning before producing structured output:

```python
class MyAnalyzer(dspy.Module):
    def __init__(self):
        super().__init__()
        # ChainOfThought adds a "reasoning" field to the output
        self.analyze = dspy.ChainOfThought(MySignature)

    def forward(self, document_context: str):
        result = self.analyze(document_context=document_context)
        # Access both the reasoning and structured output
        print(f"Reasoning: {result.reasoning}")
        return result.analysis  # Your Pydantic model
```

### 6. Handle Errors with Result Wrappers

Wrap DSPy results in dataclasses that capture success/failure state:

```python
from dataclasses import dataclass

@dataclass(slots=True)
class AnalysisResult:
    success: bool
    data: MyAnalysis | None = None
    error: str | None = None
    reasoning: str | None = None

class MyAnalyzer(dspy.Module):
    def forward(self, document_context: str) -> AnalysisResult:
        try:
            result = self.analyze(document_context=document_context)
            return AnalysisResult(
                success=True,
                data=result.analysis,
                reasoning=getattr(result, "reasoning", None),
            )
        except Exception as e:
            return AnalysisResult(success=False, error=str(e))
```

### 7. Use WorkspaceClient for Authentication

Let `WorkspaceClient()` handle authentication automatically:

```python
from databricks.sdk import WorkspaceClient

# On Databricks: auto-authenticates via runtime
# Locally: uses DATABRICKS_HOST and DATABRICKS_TOKEN from .env
client = WorkspaceClient()
openai_client = client.serving_endpoints.get_open_ai_client()
```

**Do NOT** use `dbutils.secrets` for Databricks credentials—they're not needed.

### 8. Enable MLflow Tracing

MLflow tracing captures inputs, outputs, and reasoning for debugging:

```python
import mlflow

mlflow.dspy.autolog()  # Requires MLflow 3.1+
```

View traces in the MLflow UI to debug prompt/response issues.

### 9. Keep Configuration Simple

For demos and production code, avoid unnecessary configuration options:

```python
# Good - simple, Supervisor Agent-only
def configure_dspy(model_name: str, temperature: float = 0.1):
    lm = DatabricksResponsesLM(model=model_name, temperature=temperature)
    dspy.configure(lm=lm, adapter=dspy.ChatAdapter())

# Bad - too many options that can cause errors
def configure_dspy(model_name, use_json_adapter=False, use_responses_api=True, ...):
    if use_json_adapter:  # This will fail with Supervisor Agent anyway
        ...
```

### 10. Test Locally Before Deploying

Use the same code path locally and on Databricks:

```bash
# Local testing
uv run python -m lab_7_augmentation_agent.agent_dspy

# Same code runs on Databricks via notebook or IDE plugin
```

### Summary: Supervisor Agent + DSPy Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Your DSPy Application                       │
├─────────────────────────────────────────────────────────────────┤
│  Pydantic Models (schemas.py)                                   │
│    └─ Type-safe structured output definitions                   │
├─────────────────────────────────────────────────────────────────┤
│  DSPy Signatures (signatures.py)                                │
│    └─ Declarative input/output specs with Pydantic types        │
├─────────────────────────────────────────────────────────────────┤
│  DSPy Modules (analyzers.py)                                    │
│    └─ ChainOfThought predictors wrapping signatures             │
├─────────────────────────────────────────────────────────────────┤
│  DatabricksResponsesLM (config.py)                              │
│    └─ Custom LM adapter for Responses API format                │
├─────────────────────────────────────────────────────────────────┤
│  Supervisor Agent Endpoint                                │
│    └─ Routes to Genie + Knowledge Assistant (Lab 6)                 │
└─────────────────────────────────────────────────────────────────┘
```

## References

- [DSPy on Databricks](https://docs.databricks.com/aws/en/generative-ai/dspy/)
- [DSPy Signatures](https://dspy.ai/learn/programming/signatures/)
- [DSPy Modules](https://dspy.ai/learn/programming/modules/)
- [DSPy Adapters](https://dspy.ai/learn/programming/adapters/)
- [MLflow DSPy Tracing](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/integrations/dspy)
- [Databricks Structured Outputs](https://docs.databricks.com/aws/en/machine-learning/model-serving/structured-outputs)
