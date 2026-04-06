---
marp: true
theme: default
paginate: true
---

<style>
section {
  font-size: 22px;
}
h1 { font-size: 36px; }
h2 { font-size: 28px; }
code { font-size: 18px; }
table { font-size: 20px; }
</style>

# Lab 6: Supervisor Agent
## Combining Structured + Unstructured

---

## Concepts Introduced

**Multi-Agent Systems** - Architectures where multiple specialized agents collaborate to solve complex problems.

**Key Concepts:**
- **Supervisor** - Orchestrator that routes questions to appropriate agents
- **Tool Selection** - LLM decides which agent/tool best answers each question
- **Agent Composition** - Combining specialized agents into a unified system
- **Endpoint** - Deployed agent accessible via API

**Why Multi-Agent?**
- No single agent excels at everything
- Specialized agents = better answers for their domain
- Supervisor handles routing complexity for users

---

## The Multi-Agent Architecture

```
                    ┌─────────────────────────┐
                    │  Supervisor Agent │
                    │   (Routes Questions)    │
                    └───────────┬─────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
              v                 v                 v
    ┌─────────────────┐  ┌─────────────┐  ┌─────────────┐
    │  Genie Agent    │  │  Knowledge  │  │  Future     │
    │  (SQL Queries)  │  │    Agent    │  │   Agents    │
    └─────────────────┘  └─────────────┘  └─────────────┘
              │                 │
              v                 v
    ┌─────────────────┐  ┌─────────────────┐
    │  Delta Tables   │  │  HTML Documents │
    └─────────────────┘  └─────────────────┘
```

---

## What It Enables

**Complex questions that span both data sources:**

```
"Find customers interested in renewable energy and show their current holdings"

"Which customers have risk profiles that don't match their portfolio composition?"

"What information exists in customer profiles that isn't captured in the database?"
```

**The supervisor:**
1. Analyzes the question
2. Routes to appropriate agent(s)
3. Combines responses
4. Returns unified answer

**Next:** Use the Supervisor Agent for graph augmentation analysis
