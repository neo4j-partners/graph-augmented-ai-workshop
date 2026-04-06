# Lab 7: Graph Augmentation Agent


### Quick Start

```bash
# Sync dependencies (includes dspy>=3.0.4)
uv sync

# Run all analyses
uv run python -m lab_7_augmentation_agent.agent_dspy
```

On Databricks, use the `augmentation_dspy_agent.ipynb` notebook.

---

## Environment Setup

Ensure your `.env` file contains:

```
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your-personal-access-token
SUPERVISOR_AGENT_ENDPOINT=your-supervisor-agent-endpoint
```

### Databricks Cluster Libraries

Install these libraries on your Databricks cluster:

| Library | Version | Purpose |
|---------|---------|---------|
| `dspy` | `>=3.0.4` | DSPy framework |
| `mlflow[databricks]` | `>=3.1` | Tracing |
| `pydantic` | `>=2.0.0` | Structured output schemas |
| `python-dotenv` | `>=1.0.0` | Environment configuration |

Install via cluster UI or `%pip`:
```python
%pip install dspy>=3.0.4 mlflow[databricks]>=3.1 pydantic>=2.0.0 python-dotenv>=1.0.0
dbutils.library.restartPython()
```

---

## Project Structure

```
lab_7_augmentation_agent/
├── agent_dspy.py                # DSPy entry point (RECOMMENDED)
├── augmentation_dspy_agent.ipynb # DSPy notebook for Databricks
├── schemas.py                   # Pydantic schemas for structured output
├── dspy_modules/                # DSPy implementation
│   ├── config.py               # DSPy + Databricks LM configuration
│   ├── signatures.py           # DSPy signatures for each analysis
│   └── analyzers.py            # DSPy modules that perform analysis
├── DSPY_README.md              # DSPy documentation
```

---

## Analysis Types

The agent performs four types of analysis:

| Analysis | Description | Output |
|----------|-------------|--------|
| **Investment Themes** | Identifies emerging investment trends | Themes with market data |
| **New Entities** | Suggests new node types for the graph | Node definitions with properties |
| **Missing Attributes** | Finds attributes not captured in schema | Property suggestions |
| **Implied Relationships** | Discovers hidden connections | Relationship types |


---

## Documentation References

- [DSPy on Databricks](https://docs.databricks.com/aws/en/generative-ai/dspy/)
- [DSPy Signatures](https://dspy.ai/learn/programming/signatures/)
- [Databricks Supervisor Agent](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/multi-agent-supervisor)

---
