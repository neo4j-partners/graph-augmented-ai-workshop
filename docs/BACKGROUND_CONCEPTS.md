# Background Concepts: Understanding Agent-Augmented Knowledge Graphs

Your customer's profile mentions renewable energy investments. Their portfolio holds zero renewable energy stocks. Somewhere between that PDF document and your database, valuable context got lost. This guide explains the technologies that bridge that gap.

If terms like "lakehouse architecture," "multi-agent orchestration," or "graph data science" feel unfamiliar, start here before diving into the workshop labs. The concepts build on each other, so working through them in order will make the integration patterns click faster.

## Databricks Lakehouse Architecture

Most enterprises maintain two separate systems for data. Data lakes store raw files cheaply but offer no query optimization or transaction guarantees. Data warehouses provide fast queries and ACID transactions but cost significantly more and struggle with unstructured content. Running both creates data silos, duplication headaches, and reconciliation nightmares.

The lakehouse architecture eliminates this split by adding database capabilities directly on top of cloud object storage.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATABRICKS LAKEHOUSE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        UNITY CATALOG                                 │   │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │   │
│  │   │   Tables     │  │   Volumes    │  │   ML Models & Functions  │  │   │
│  │   │  (schemas,   │  │ (documents,  │  │   (registered models,    │  │   │
│  │   │  permissions)│  │  images, PDFs)│  │    serving endpoints)   │  │   │
│  │   └──────────────┘  └──────────────┘  └──────────────────────────┘  │   │
│  │                         Unified Governance Layer                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                          DELTA LAKE                                  │   │
│  │                                                                      │   │
│  │   ACID Transactions  │  Time Travel  │  Schema Enforcement          │   │
│  │                                                                      │   │
│  │   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐   │   │
│  │   │ customers  │  │  accounts  │  │  positions │  │transactions│   │   │
│  │   │   table    │  │   table    │  │   table    │  │   table    │   │   │
│  │   └────────────┘  └────────────┘  └────────────┘  └────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     CLOUD OBJECT STORAGE                             │   │
│  │                   (S3 / ADLS / GCS - Parquet files)                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Delta Lake: The Transaction Layer

Delta Lake sits between your compute and cloud storage, turning raw Parquet files into a proper database. It handles concurrent reads and writes without corruption, enforces schemas so bad data fails loudly at write time, and maintains version history for every change.

That version history matters more than developers initially expect. When a data pipeline introduces bad records at 2 AM and nobody notices until the morning report breaks, Delta Lake lets you query the table as it existed yesterday. No restore from backup required.

```python
# Query historical data from any point in time
df = spark.read.format("delta") \
    .option("timestampAsOf", "2025-01-15 09:00:00") \
    .table("retail_investment.customers")

# Or roll back a table to a previous version after a bad write
spark.sql("RESTORE TABLE retail_investment.customers TO VERSION AS OF 42")
```

### Unity Catalog: The Governance Layer

Unity Catalog tracks everything in your lakehouse through a three-level namespace: catalog, schema, table. A customer table might live at `retail_investment.retail_investment.customer`. This hierarchy matters because permissions cascade. Grant access to a catalog and users can query every table within it. Restrict a specific schema and those tables become invisible to unauthorized users.

The 2025 releases added attribute-based access control (ABAC), which makes permission management significantly more practical at scale. Instead of maintaining explicit access lists for thousands of tables, you tag tables with attributes like `sensitivity: high` or `domain: finance` and write policies against those tags.

```sql
-- Tag a table with sensitivity metadata
ALTER TABLE retail_investment.customer
SET TAGS ('sensitivity' = 'pii', 'domain' = 'customer_data');

-- Create a policy that uses tags for access decisions
-- Users with 'pii_access' attribute can query PII-tagged tables
```

Unity Catalog also manages **volumes**, which store files that don't fit neatly into tables. Customer profiles written as narrative text documents, market research PDFs, scanned forms, images of signed agreements. These files live in Unity Catalog volumes with the same governance as tables, making unstructured data a first-class citizen in the lakehouse rather than an afterthought dumped in an ungoverned S3 bucket.

For this project, the volume at `retail_investment.retail_investment.retail_investment_volume` holds 14 text documents: customer profiles describing investment preferences, bank branch descriptions, company analyses, and market research reports. These documents contain context that never made it into structured database fields.

## Databricks AI Agents

An AI agent takes a natural language question, figures out what tools and data sources to query, executes those queries, and synthesizes an answer. Unlike a chatbot that can only respond based on its training data, agents interact with live systems and retrieve current information.

Databricks provides purpose-built agents for different data types. Each agent specializes in a specific modality and uses different retrieval strategies under the hood.

### Genie Agent: Structured Data Queries

The Genie agent translates natural language into SQL. When you ask "Which customers have investment accounts with balances over $50,000?", Genie examines the table schemas in Unity Catalog, determines which tables contain customer and account data, identifies the join keys, generates the appropriate SQL, executes it, and returns results.

```
┌──────────────────────────────────────────────────────────────────────┐
│                         GENIE AGENT FLOW                             │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   User Question                                                      │
│        │                                                             │
│        ▼                                                             │
│   ┌─────────────┐     ┌─────────────────┐     ┌─────────────────┐   │
│   │   Schema    │────▶│  SQL Generation │────▶│  Query Execution│   │
│   │  Analysis   │     │  (with self-    │     │  (Delta Lake)   │   │
│   │             │     │   reflection)   │     │                 │   │
│   └─────────────┘     └─────────────────┘     └─────────────────┘   │
│                                                       │              │
│                                                       ▼              │
│                                              ┌─────────────────┐    │
│                                              │  Results with   │    │
│                                              │  Thinking Steps │    │
│                                              └─────────────────┘    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

The 2025 Genie release introduced self-reflection during SQL generation. As Genie writes the query, it evaluates whether the SQL will actually answer the question and fixes issues before execution. This reduces the frequency of syntactically valid but semantically wrong queries.

Genie now also exposes its reasoning. Each response includes the thinking steps that led to the generated SQL, showing which tables it considered and why it chose specific join conditions. When Genie returns unexpected results, those thinking steps help diagnose whether the agent misunderstood the question or whether the underlying data has quality issues.

**Example Genie Query:**

Natural language: "Show me the top 5 customers by total portfolio value"

Generated SQL:
```sql
SELECT
    c.customerId,
    c.firstName,
    c.lastName,
    SUM(p.currentValue) AS total_portfolio_value
FROM customer c
JOIN has_account ha ON c.customerId = ha.customerId
JOIN account a ON ha.accountId = a.accountId
JOIN has_position hp ON a.accountId = hp.accountId
JOIN position p ON hp.positionId = p.positionId
GROUP BY c.customerId, c.firstName, c.lastName
ORDER BY total_portfolio_value DESC
LIMIT 5
```

The Genie Conversation API, now in public preview, allows programmatic access to this capability. Applications can submit questions, retrieve the generated SQL, and get results through REST calls. This opens integration paths to Slack bots, internal dashboards, and custom applications that need natural language data access.

### Knowledge Assistant Agent: Unstructured Data Analysis

While Genie works with structured tables, the Knowledge Assistant agent handles documents. It reads PDFs, text files, and other unstructured content stored in Unity Catalog volumes, building semantic understanding of the narrative information within.

```
┌──────────────────────────────────────────────────────────────────────┐
│                   KNOWLEDGE ASSISTANT FLOW                           │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   User Question                                                      │
│        │                                                             │
│        ▼                                                             │
│   ┌─────────────┐     ┌─────────────────┐     ┌─────────────────┐   │
│   │   Vector    │────▶│    Semantic     │────▶│   LLM Answer    │   │
│   │   Search    │     │   Retrieval     │     │   Synthesis     │   │
│   │             │     │  (ranked docs)  │     │                 │   │
│   └─────────────┘     └─────────────────┘     └─────────────────┘   │
│                                                       │              │
│        ┌──────────────────────────────────────────────┘              │
│        ▼                                                             │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │  Answer with source document citations                       │   │
│   │  "James Anderson expressed interest in renewable energy      │   │
│   │   stocks, particularly solar and wind companies."            │   │
│   │   [Source: customer_profile_james_anderson.txt]              │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

The agent employs vector search to find semantically relevant document passages. When you ask "What investment interests has Maria Rodriguez expressed?", it doesn't just grep for the string "Maria Rodriguez." It identifies documents that discuss Maria's financial preferences, extracts the relevant passages, and synthesizes an answer from that context.

This capability answers questions that structured data cannot address. A customer profile might mention "strong interest in ESG investing and socially responsible funds." That preference never made it into a database column, but the Knowledge Assistant can find it, extract it, and use it to inform personalization decisions.

**Example Knowledge Assistant Query:**

Question: "What sectors does the renewable energy trends document recommend for investment?"

The agent searches the `renewable_energy_investment_trends.txt` document, identifies mentions of specific companies and sectors, and returns:

> The document highlights solar energy, wind power, battery storage, and hydrogen fuel cells as high-growth sectors. Specific companies mentioned include Solar Energy Systems (SOEN), Renewable Power Inc (RPOW), Wind Power Systems (WIND), Battery Technology Corp (BATT), and Hydrogen Fuel Cells Inc (HYDR). The analysis emphasizes that government incentives and declining technology costs make renewable energy an attractive long-term investment category.

### Multi-Agent Orchestration: The Supervisor Pattern

Real questions rarely fit neatly into either structured or unstructured categories. "Find customers who mentioned renewable energy in their profiles but don't hold any renewable energy stocks" requires both document analysis and database queries. Neither agent alone can answer it.

The Supervisor Agent coordinates multiple specialized agents, routing subtasks to whichever agent can handle them and synthesizing the results.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    MULTI-AGENT SUPERVISOR PATTERN                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Complex User Question                                                      │
│   "Find customers interested in renewable energy but lacking those stocks"   │
│        │                                                                     │
│        ▼                                                                     │
│   ┌────────────────────────────────────────────────────────────────────┐    │
│   │                    MULTI-AGENT SUPERVISOR                           │    │
│   │                                                                     │    │
│   │   1. Parse question into subtasks                                   │    │
│   │   2. Route each subtask to appropriate agent                        │    │
│   │   3. Collect and synthesize results                                 │    │
│   │   4. Identify gaps and opportunities                                │    │
│   └────────────────────────────────────────────────────────────────────┘    │
│        │                                        │                            │
│        │ Subtask 1                              │ Subtask 2                  │
│        ▼                                        ▼                            │
│   ┌─────────────────┐                   ┌─────────────────┐                 │
│   │   Knowledge     │                   │     Genie       │                 │
│   │   Assistant     │                   │     Agent       │                 │
│   │                 │                   │                 │                 │
│   │ "Which customer │                   │ "Show portfolio │                 │
│   │  profiles       │                   │  holdings for   │                 │
│   │  mention        │                   │  these customer │                 │
│   │  renewable      │                   │  IDs"           │                 │
│   │  energy?"       │                   │                 │                 │
│   └────────┬────────┘                   └────────┬────────┘                 │
│            │                                     │                          │
│            │ James Anderson (C0001)              │ C0001 holds: TCOR,       │
│            │ Maria Rodriguez (C0002)             │ SMTC, MOBD (tech stocks) │
│            │                                     │ C0002 holds: FINC, BANK  │
│            │                                     │ (financial stocks)       │
│            ▼                                     ▼                          │
│   ┌────────────────────────────────────────────────────────────────────┐   │
│   │                      SYNTHESIZED ANSWER                             │   │
│   │                                                                     │   │
│   │  GAP IDENTIFIED:                                                    │   │
│   │  - James Anderson: Interested in renewable energy, holds 0%         │   │
│   │  - Maria Rodriguez: Interested in renewable energy, holds 0%        │   │
│   │                                                                     │   │
│   │  RECOMMENDATION: Cross-sell opportunity for renewable energy ETFs   │   │
│   └────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

This orchestration pattern scales to more complex scenarios. An enterprise might deploy a Genie agent for sales data, another for inventory, a Knowledge Assistant for contract documents, and a third agent for customer support tickets. The supervisor routes questions to whichever combination of agents can provide the complete answer.

Databricks released the Supervisor Agent as a configurable "Agent Brick" in 2025, reducing the implementation effort from custom orchestration code to configuration. Organizations can also integrate Genie with external platforms through managed MCP (Model Context Protocol) servers, connecting Databricks agents to Microsoft Copilot Studio or Azure AI Foundry.

## Knowledge Graphs

Relational databases store data in tables with rows and columns. This works well for transactional systems, but relationship-heavy queries become painful. "Find customers who bank at institutions where other customers holding renewable energy stocks also bank" requires multiple self-joins, subqueries, and careful index optimization. The SQL is hard to write, harder to read, and expensive to execute.

Knowledge graphs flip the model. Instead of tables with foreign keys, data lives as nodes connected by explicit relationships. The graph structure makes relationship traversals native operations rather than afterthoughts.

### Nodes: The Entities

Nodes represent the things in your domain. In a retail investment context, nodes include customers, accounts, banks, companies, stocks, positions, and transactions. Each node has a label indicating its type and properties storing its attributes.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SAMPLE GRAPH STRUCTURE                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│                          ┌───────────────┐                              │
│                          │    Company    │                              │
│                          │   "TechCore"  │                              │
│                          │  sector: Tech │                              │
│                          └───────┬───────┘                              │
│                                  │                                      │
│                           OF_COMPANY                                    │
│                                  │                                      │
│                                  ▼                                      │
│  ┌──────────────┐         ┌───────────────┐                            │
│  │   Customer   │         │     Stock     │                            │
│  │   "James"    │         │  ticker: TCOR │                            │
│  │ risk: Moderate│        │ price: $142.50│                            │
│  └──────┬───────┘         └───────┬───────┘                            │
│         │                         │                                     │
│    HAS_ACCOUNT              OF_SECURITY                                 │
│         │                         │                                     │
│         ▼                         │                                     │
│  ┌──────────────┐         ┌───────┴───────┐         ┌──────────────┐   │
│  │   Account    │         │   Position    │         │     Bank     │   │
│  │  type: INV   │◀────────│  shares: 150  │         │ "First Natl" │   │
│  │balance: $52K │ HAS_POS │ value: $21,375│         │  type: Comm  │   │
│  └──────┬───────┘         └───────────────┘         └──────────────┘   │
│         │                                                   ▲           │
│         └───────────────────AT_BANK─────────────────────────┘           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

A Customer node might have properties like `customerId`, `firstName`, `lastName`, `annualIncome`, `riskProfile`, and `creditScore`. A Stock node stores `ticker`, `currentPrice`, `exchange`, `peRatio`, and `dividendYield`. Properties capture attributes; the graph structure captures relationships.

### Edges: The Relationships

Edges (also called relationships) connect nodes with semantic meaning. A `HAS_ACCOUNT` edge between a Customer and an Account node says "this customer owns this account." An `AT_BANK` edge between an Account and a Bank says "this account is held at this bank."

Edges have direction, meaning `(Customer)-[:HAS_ACCOUNT]->(Account)` is different from the reverse. They can also carry properties. A transaction relationship might include the transaction date, amount, and status as edge properties.

The power shows up in queries. Finding related data requires traversing edges rather than joining tables.

**Cypher Query Example:**
```cypher
// Find all stocks held by customers who bank at First National Trust
MATCH (b:Bank {name: "First National Trust"})
      <-[:AT_BANK]-(a:Account)
      <-[:HAS_ACCOUNT]-(c:Customer)
      -[:HAS_ACCOUNT]->(a2:Account)
      -[:HAS_POSITION]->(p:Position)
      -[:OF_SECURITY]->(s:Stock)
RETURN DISTINCT s.ticker, s.currentPrice, count(c) as holder_count
ORDER BY holder_count DESC
```

This query starts at a bank, traverses to accounts at that bank, to customers who own those accounts, to all accounts those customers own, to positions in those accounts, and finally to the stocks those positions represent. In SQL, this would require five joins with careful aliasing. In Cypher, the pattern reads almost like the English description of what we want.

### Why Graphs for This Problem

Knowledge graphs excel when relationships matter as much as entities. Financial services fit this pattern perfectly: customers own accounts, accounts hold positions, positions represent securities, securities are issued by companies, transactions flow between accounts. Every useful question involves traversing these connections.

Graphs also evolve gracefully. When agents discover that customers express investment interests in their profile documents, adding an `INTERESTED_IN` relationship type to connect customers to sectors requires no schema migration. The existing Customer and Sector nodes gain new edges without modifying any table structures or rebuilding indexes.

## Ontology Tables

An ontology table catalogs what can exist in your knowledge graph. While the graph itself stores actual instances (specific customers, particular accounts), the ontology describes the templates. It lists all node labels, all relationship types, their expected properties, and the rules governing how they connect.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      ONTOLOGY TABLE STRUCTURE                            │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  NODE TYPES                                                              │
│  ────────────────────────────────────────────────────────────────────   │
│  Label       │ Description              │ Required Properties           │
│  ────────────┼──────────────────────────┼─────────────────────────────  │
│  Customer    │ Individual investor      │ customerId, firstName,        │
│              │                          │ lastName, riskProfile         │
│  Account     │ Financial account        │ accountId, accountType,       │
│              │                          │ balance                       │
│  Stock       │ Tradable security        │ stockId, ticker, exchange     │
│  Sector      │ Investment category      │ sectorId, name                │
│                                                                          │
│  RELATIONSHIP TYPES                                                      │
│  ────────────────────────────────────────────────────────────────────   │
│  Type           │ Source    │ Target   │ Cardinality │ Description      │
│  ───────────────┼───────────┼──────────┼─────────────┼────────────────  │
│  HAS_ACCOUNT    │ Customer  │ Account  │ 1:N         │ Ownership        │
│  AT_BANK        │ Account   │ Bank     │ N:1         │ Institution      │
│  INTERESTED_IN  │ Customer  │ Sector   │ N:M         │ Expressed pref   │
│  OF_SECURITY    │ Position  │ Stock    │ N:1         │ What is held     │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

For agent-augmented systems, the ontology serves a critical function: it tells agents what relationship types already exist before they propose new ones. When the Knowledge Assistant extracts that a customer mentioned "interest in sustainable investing," it queries the ontology to check whether an `INTERESTED_IN` relationship type exists. If so, it creates an instance of that relationship. If not, it proposes adding a new type to the ontology.

This prevents fragmentation. Without ontology governance, one agent might create `INTERESTED_IN` while another creates `HAS_INTEREST_IN` and a third uses `PREFERS`. Three relationship types for the same concept makes the graph harder to query and understand. The ontology enforces a controlled vocabulary for graph evolution.

**Python Ontology Check Example:**
```python
def propose_relationship(source_label: str, target_label: str,
                         rel_type: str, ontology_df) -> dict:
    """
    Check if a relationship type exists in the ontology before proposing it.
    Returns approval status and any existing alternatives.
    """
    # Check for exact match
    exact_match = ontology_df.filter(
        (ontology_df.rel_type == rel_type) &
        (ontology_df.source_label == source_label) &
        (ontology_df.target_label == target_label)
    ).count() > 0

    if exact_match:
        return {"status": "approved", "rel_type": rel_type}

    # Check for semantic alternatives (same source/target, different name)
    alternatives = ontology_df.filter(
        (ontology_df.source_label == source_label) &
        (ontology_df.target_label == target_label)
    ).select("rel_type").collect()

    if alternatives:
        return {
            "status": "review_required",
            "message": f"Similar relationships exist: {[r.rel_type for r in alternatives]}",
            "proposed": rel_type
        }

    return {"status": "new_type_proposed", "rel_type": rel_type}
```

## Neo4j Graph Data Science (GDS)

Storing data in a graph enables relationship queries. Analyzing the graph's structure reveals patterns invisible in the raw data. Neo4j Graph Data Science (GDS) provides 65+ algorithms that examine graph topology to find communities, measure influence, discover similar nodes, and predict likely relationships.

The latest GDS releases (v2.23 as of late 2025) added clique counting algorithms and promoted the all-pairs shortest paths algorithm to production tier. Memory estimation for centrality algorithms improved, and a new `labelFilter` parameter for triangle counting lets you constrain which node types participate in the count.

### Community Detection: Finding Natural Groups

Community detection algorithms identify clusters of nodes that connect more densely to each other than to the rest of the graph. In a retail investment context, this might reveal that certain customers form natural groups based on shared banking relationships, similar portfolio compositions, or common transaction patterns.

```cypher
// Project a graph for community detection
CALL gds.graph.project(
    'customer-network',
    ['Customer', 'Account', 'Bank'],
    {
        HAS_ACCOUNT: {orientation: 'UNDIRECTED'},
        AT_BANK: {orientation: 'UNDIRECTED'}
    }
)

// Run Louvain community detection
CALL gds.louvain.stream('customer-network')
YIELD nodeId, communityId
WITH gds.util.asNode(nodeId) AS node, communityId
WHERE node:Customer
RETURN node.customerId AS customer,
       node.firstName AS name,
       communityId
ORDER BY communityId, customer
```

The Louvain algorithm optimizes for modularity, grouping nodes to maximize within-community connections while minimizing between-community links. Customers in the same community likely share characteristics worth investigating: maybe they all bank at the same regional institution, hold similar sector allocations, or exhibit comparable trading frequencies.

### Centrality: Identifying Important Nodes

Centrality algorithms measure node importance based on position in the graph. Different centrality measures capture different notions of "important."

**PageRank** considers both how many connections a node has and how important those connections are. A customer referred by five other high-value customers ranks higher than one referred by five inactive accounts. PageRank identifies influential nodes in referral networks or systemically important accounts in transaction flows.

```cypher
// Find the most influential customers in a referral network
CALL gds.pageRank.stream('referral-network')
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS customer, score
RETURN customer.customerId, customer.firstName, score
ORDER BY score DESC
LIMIT 10
```

**Betweenness Centrality** finds nodes that sit on paths between other nodes. High betweenness accounts might be clearing accounts or intermediaries where transaction flows converge. Identifying these chokepoints matters for operational risk analysis and fraud detection.

### Similarity: Finding Related Nodes

Similarity algorithms compare nodes based on their neighborhoods rather than their attributes. Two customers who have accounts at the same banks, hold the same stocks, and perform similar transaction patterns are considered similar even if their demographic profiles differ.

This becomes especially powerful with agent-enriched relationships. Once agents create `INTERESTED_IN` edges connecting customers to investment sectors, Jaccard similarity can find customers with overlapping interests.

```cypher
// Find customers with similar investment interests
// (assumes INTERESTED_IN relationships created by agent enrichment)
MATCH (c1:Customer)-[:INTERESTED_IN]->(sector)<-[:INTERESTED_IN]-(c2:Customer)
WHERE c1.customerId < c2.customerId
WITH c1, c2, count(sector) AS shared_interests,
     [(c1)-[:INTERESTED_IN]->(s) | s] AS c1_interests,
     [(c2)-[:INTERESTED_IN]->(s) | s] AS c2_interests
WITH c1, c2, shared_interests,
     size(c1_interests) AS c1_count,
     size(c2_interests) AS c2_count
RETURN c1.customerId AS customer_1,
       c2.customerId AS customer_2,
       shared_interests,
       toFloat(shared_interests) / (c1_count + c2_count - shared_interests) AS jaccard
ORDER BY jaccard DESC
LIMIT 20
```

### Path Finding: Discovering Connections

Path finding algorithms discover how nodes connect through the graph. The shortest path between two customers might reveal unexpected relationships through shared banks, overlapping portfolios, or transaction chains.

```cypher
// Find the shortest path between two customers through any relationships
MATCH path = shortestPath(
    (c1:Customer {customerId: 'C0001'})-[*]-(c2:Customer {customerId: 'C0042'})
)
RETURN path,
       [node IN nodes(path) | labels(node)[0]] AS node_types,
       [rel IN relationships(path) | type(rel)] AS relationship_types
```

Path finding supports compliance use cases. Undisclosed relationships between customers and advisors, or potential conflicts of interest through shared investment positions, become visible when you can traverse the full relationship graph.

## How These Technologies Work Together

The individual technologies combine into a continuous enrichment loop that makes knowledge graphs smarter over time.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     THE ENRICHMENT LOOP ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                         ┌───────────────────┐                               │
│                         │   NEO4J GRAPH     │                               │
│                         │   (Foundation)    │                               │
│                         │                   │                               │
│                         │  Customers,       │                               │
│                         │  Accounts, Stocks │                               │
│                         │  + Relationships  │                               │
│                         └─────────┬─────────┘                               │
│                                   │                                         │
│              ┌────────────────────┼────────────────────┐                    │
│              │ 1. EXTRACT         │        6. INGEST   │                    │
│              │    (Spark          │           (new     │                    │
│              │    Connector)      │           edges)   │                    │
│              ▼                    │                    ▲                    │
│  ┌───────────────────────────────────────────────────────────────────┐     │
│  │                    DATABRICKS LAKEHOUSE                           │     │
│  │  ┌──────────────────────┐        ┌──────────────────────┐        │     │
│  │  │  STRUCTURED DATA     │        │  UNSTRUCTURED DATA   │        │     │
│  │  │  (Delta Lake tables) │        │  (UC Volumes)        │        │     │
│  │  │                      │        │                      │        │     │
│  │  │  customer, account,  │        │  customer_profiles/  │        │     │
│  │  │  position, stock,    │        │  market_research/    │        │     │
│  │  │  has_account, etc.   │        │  investment_guides/  │        │     │
│  │  └──────────┬───────────┘        └──────────┬───────────┘        │     │
│  │             │                               │                     │     │
│  │             │ 2. QUERY                      │ 3. ANALYZE          │     │
│  │             ▼                               ▼                     │     │
│  │  ┌──────────────────┐           ┌──────────────────────┐         │     │
│  │  │   GENIE AGENT    │           │  KNOWLEDGE ASSISTANT │         │     │
│  │  │                  │           │                      │         │     │
│  │  │  "What stocks    │           │  "What interests     │         │     │
│  │  │   does C0001     │           │   did James mention  │         │     │
│  │  │   hold?"         │           │   in his profile?"   │         │     │
│  │  └────────┬─────────┘           └──────────┬───────────┘         │     │
│  │           │                                │                      │     │
│  │           └────────────┬───────────────────┘                      │     │
│  │                        │                                          │     │
│  │                        ▼ 4. ORCHESTRATE                           │     │
│  │           ┌────────────────────────────┐                          │     │
│  │           │   MULTI-AGENT SUPERVISOR   │                          │     │
│  │           │                            │                          │     │
│  │           │   Compare interests vs.    │                          │     │
│  │           │   holdings. Identify gaps. │                          │     │
│  │           │   Propose new INTERESTED_IN│                          │     │
│  │           │   relationships.           │                          │     │
│  │           └────────────┬───────────────┘                          │     │
│  │                        │                                          │     │
│  │                        │ 5. VALIDATE                              │     │
│  │                        ▼                                          │     │
│  │           ┌────────────────────────────┐                          │     │
│  │           │      ONTOLOGY TABLE        │──────────────────────────┘     │
│  │           │                            │                                │
│  │           │   Check: Does INTERESTED_IN│                                │
│  │           │   already exist? Approve   │                                │
│  │           │   or propose new type.     │                                │
│  │           └────────────────────────────┘                                │
│  │                                                                         │
│  └─────────────────────────────────────────────────────────────────────────┘
│                                                                             │
│    7. ANALYZE: Run GDS algorithms on enriched graph                        │
│       - Community detection on INTERESTED_IN to find customer segments     │
│       - Jaccard similarity to match customers with compatible interests    │
│       - PageRank on referral network to identify influencers               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

The flow works like this:

1. **Extract**: The Neo4j Spark Connector pulls graph data into Delta Lake tables with full schema preservation. Node tables contain entity properties plus metadata (Neo4j element IDs, labels, ingestion timestamps). Relationship tables use business-meaningful column names like `customerId` and `accountId` rather than generic source/destination identifiers.

2. **Query Structured Data**: The Genie agent answers questions against the lakehouse tables. "Show portfolio holdings for customer C0001" becomes a SQL query that joins customer, account, position, and stock tables.

3. **Analyze Documents**: The Knowledge Assistant searches Unity Catalog volumes for relevant documents. "What investment interests does James Anderson express?" triggers vector search across customer profiles, extracting mentions of renewable energy, ESG investing, or other themes.

4. **Orchestrate**: The Supervisor Agent coordinates both agents for complex questions. It might first ask the Knowledge Assistant which customers mentioned renewable energy, then ask Genie for those customers' current holdings, then compare the results to identify gaps.

5. **Validate**: Before creating new relationships, agents check the ontology. If `INTERESTED_IN` already exists as a relationship type, they create instances of it. If not, they propose adding a new type through a governance workflow.

6. **Ingest**: Approved relationship proposals write to edge tables and load back into Neo4j. The graph gains new edges representing agent-discovered insights without manual ETL work.

7. **Analyze**: With enriched relationships in Neo4j, GDS algorithms reveal patterns. Community detection finds customer segments with shared interests. Similarity algorithms identify customers who would likely value similar products. Centrality measures find influential accounts for targeted outreach.

This loop runs continuously. Each cycle discovers new relationships, enriches the graph, and enables more sophisticated analysis. The knowledge graph evolves from a static snapshot of transactional relationships into a living model of customer intent, preferences, and potential.

## Practical Tradeoffs and Limitations

No architecture is free of tradeoffs. Understanding the limitations helps set realistic expectations and plan mitigation strategies.

**Agent extraction quality varies.** LLMs occasionally misinterpret document context or extract facts that aren't actually stated. Production deployments need confidence scoring, human review queues for low-confidence extractions, and audit trails tracking which agent decisions led to which graph modifications.

**Flattened graph representations lose semantic power.** When graph data lands in lakehouse tables, multi-hop traversals become complex joins. The ontology table helps agents understand graph structure, but human analysts querying the lakehouse directly face cognitive overhead that doesn't exist in native graph queries. Keep analytical workloads in Neo4j where relationship queries belong.

**Schema evolution requires governance.** Letting agents create arbitrary relationship types leads to fragmentation. The ontology provides a controlled vocabulary, but someone needs to review proposed additions. Fully autonomous schema evolution risks creating an unmaintainable mess.

**The enrichment loop has latency.** Agent analysis takes time. Large document collections require significant processing. Near-real-time enrichment is achievable for triggered updates (a single customer profile changed), but full-corpus analysis runs as a batch process. Design applications to handle graphs that are enriched eventually rather than immediately.

**Not everything belongs in a graph.** Large-scale aggregations, time-series analytics, and machine learning feature engineering often work better in the lakehouse. The architecture shines for relationship-rich queries, not every analytical workload. Use each system for what it does best.

## Further Reading

**External Resources:**

- [Databricks AI/BI Genie Documentation](https://docs.databricks.com/aws/en/genie/)
- [Neo4j Graph Data Science Manual v2.23](https://neo4j.com/docs/graph-data-science/current/)
- [Unity Catalog Overview](https://docs.databricks.com/aws/en/data-governance/unity-catalog/)
- [Supervisor Agent in Databricks](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/multi-agent-supervisor)
- [GraphRAG and Agentic Architecture with Neo4j](https://neo4j.com/blog/developer/graphrag-and-agentic-architecture-with-neoconverse/)
- [Zep: Temporal Knowledge Graphs for Agent Memory](https://arxiv.org/html/2501.13956v1)
