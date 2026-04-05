# Lab 6: Supervisor Agent

This lab combines the Genie and Knowledge Assistant into a unified system that answers complex questions requiring both structured data and unstructured document analysis.

## Prerequisites

- Completed [Lab 5](../lab_5_ai_agents/README.md) with both agents created:
  - Retail Investment Data Assistant (Genie)
  - Customer Insights Knowledge Assistant

---

## Setup

### 1. Create Supervisor Agent

- Navigate to the **Supervisor Agent** interface
- Click **Build** to create a new multi-agent system

### 2. Add Agents

Click **Configure Agents** to add your agents. You can select up to 20 different agents and tools.

**Agent 1: Genie Space**

| Field | Value |
|-------|-------|
| Type | `Genie Space` |
| Genie space | Select your Retail Investment Genie |
| Agent Name | `agent-retail-investment-genie` |
| Describe the content | `Answers questions about retail investment customers, account balances, portfolio holdings, stock positions, banking relationships, and transaction history across structured data extracted from a graph database into Delta Lake tables.` |

**Agent 2: Knowledge Assistant**


| Field | Value |
|-------|-------|
| Type | `Agent Endpoint` |
| Agent Endpoint | Select your Knowledge Assistant endpoint (e.g., `ka-6f0994b4-endpoint`) |
| Agent Name | `graph-augmentation-knowledge-assistant` |
| Describe the content | `This knowledge base contains comprehensive customer profiles, institutional data, and investment research documents for a retail investment platform. The content includes: CUSTOMER PROFILES: Detailed narratives containing demographics, risk profiles, current account holdings, investment preferences, personal financial goals, life circumstances, stated investment interests that may not yet be reflected in portfolios, savings habits, customer service preferences, credit scores, and banking relationship history.` |

### 3. Configure System Settings

- **Name**: `Retail Investment Intelligence System`

- **Description**:
  ```
  Provides comprehensive retail investment intelligence by combining structured transactional data analysis with unstructured customer insights and market research. Analyzes customer portfolios, account activity, and holdings alongside qualitative preferences, investment interests, and research recommendations to identify opportunities, gaps, and personalized financial guidance.
  ```

- **Instructions**:
  ```
  You are an intelligent investment analysis system. Use the Genie agent to query
  structured data about customers, accounts, and portfolios. Use the Knowledge Assistant
  to analyze customer profiles and documents. Your goal is to:

  1. Identify gaps between customer interests (from profiles) and actual investments
  2. Find data quality issues where profile information isn't captured in structured data
  3. Discover cross-sell opportunities based on customer insights
  4. Provide comprehensive customer analysis combining both data sources
  ```

### 4. Get Endpoint Name

After creating the Supervisor Agent, click the **cloud icon** in the top right corner to view the endpoint details. Copy the endpoint name (e.g., `mas-01875d0e-endpoint`) - you'll need this in Lab 7.

---

## Test Queries

Basic tests to verify the system works:

```
Find customers interested in renewable energy stocks and show me their current holdings
Which customers have risk profiles that don't match their portfolio composition?
What information exists in customer profiles that isn't captured in the structured database?
```

---

## Sample Queries

See [SAMPLE_QUERIES.md](./SAMPLE_QUERIES.md) for comprehensive examples including:

- **Use Case Categories**: Gap analysis, risk mismatch, data quality, customer intelligence, portfolio analysis, transactions, market research, banking relationships, cross-sell, compliance

- **Advanced Multi-Agent Questions**: Sophisticated queries that combine structured and unstructured data for personalized investment discovery, portfolio-profile alignment, research-driven targeting, life stage analysis, and comprehensive customer reports

---

## Next Steps

Continue to [Lab 7: Graph Augmentation Agent](../lab_7_augmentation_agent/README.md) to use the Supervisor Agent for analyzing documents and suggesting graph enrichments.
