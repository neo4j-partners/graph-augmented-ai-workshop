# Databricks notebook source

# MAGIC %md
# MAGIC # Neo4j Import
# MAGIC
# MAGIC ### Estimated time: 5-10 minutes
# MAGIC
# MAGIC This notebook loads all workshop data into Neo4j in a single step:
# MAGIC
# MAGIC 1. **Structured data** (7 CSV files) loaded via the Neo4j Spark Connector as nodes and relationships
# MAGIC 2. **Document graph** (14 HTML documents) with pre-computed vector embeddings loaded via the Neo4j Python driver
# MAGIC
# MAGIC After this notebook runs, Neo4j contains the complete graph:
# MAGIC - **764 nodes** across 7 types (Customer, Account, Bank, Transaction, Position, Stock, Company)
# MAGIC - **814 relationships** across 7 types (HAS_ACCOUNT, AT_BANK, PERFORMS, BENEFITS_TO, HAS_POSITION, OF_SECURITY, OF_COMPANY)
# MAGIC - **14 Document nodes** and approximately 50-100 Chunk nodes with 1024-dimensional embedding vectors
# MAGIC - **Vector and full-text indexes** on Chunk nodes for hybrid search
# MAGIC
# MAGIC ### Prerequisites
# MAGIC
# MAGIC - Run **0 - Required Setup** first
# MAGIC - Cluster must be **Dedicated** mode with the Neo4j Spark Connector Maven library installed

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Model
# MAGIC
# MAGIC The structured graph models a retail investment domain:
# MAGIC
# MAGIC ```
# MAGIC Customer ──HAS_ACCOUNT──> Account ──AT_BANK──> Bank
# MAGIC                              │
# MAGIC                              ├──PERFORMS──> Transaction ──BENEFITS_TO──> Account
# MAGIC                              │
# MAGIC                              └──HAS_POSITION──> Position ──OF_SECURITY──> Stock ──OF_COMPANY──> Company
# MAGIC ```
# MAGIC
# MAGIC The document graph adds a layer of unstructured content:
# MAGIC
# MAGIC ```
# MAGIC Document ──DESCRIBES──> Customer
# MAGIC    ▲
# MAGIC    │
# MAGIC Chunk ──FROM_DOCUMENT──> Document
# MAGIC    │
# MAGIC Chunk ──NEXT_CHUNK──> Chunk
# MAGIC ```
# MAGIC
# MAGIC Each Chunk node stores a text segment and its vector embedding, enabling semantic search
# MAGIC across customer profiles, company analyses, investment guides, and regulatory documents.

# COMMAND ----------

# MAGIC %md
# MAGIC ## About the Pre-computed Embeddings
# MAGIC
# MAGIC The document embeddings were generated ahead of time using the **databricks-gte-large-en**
# MAGIC foundation model (1024 dimensions). The process was:
# MAGIC
# MAGIC 1. Parse 14 HTML documents with BeautifulSoup to extract clean text
# MAGIC 2. Split each document into chunks (4000 characters, 200 character overlap)
# MAGIC 3. Generate a vector embedding for each chunk via the Databricks embedding endpoint
# MAGIC 4. Save everything to a JSON file that ships with the workshop
# MAGIC
# MAGIC The generation script lives in `full_demo/agent_modules/generate_embeddings.py` if you want to see
# MAGIC exactly how it works or regenerate the embeddings with a different model.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run the Import

# COMMAND ----------

# MAGIC %run ./Includes/_lib/neo4j_import

# COMMAND ----------

run_full_import()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Explore the Graph
# MAGIC
# MAGIC Open Neo4j Browser and try these queries:
# MAGIC
# MAGIC **See the full schema:**
# MAGIC ```cypher
# MAGIC CALL db.schema.visualization()
# MAGIC ```
# MAGIC
# MAGIC **Count nodes by label:**
# MAGIC ```cypher
# MAGIC MATCH (n)
# MAGIC RETURN labels(n)[0] AS label, count(n) AS count
# MAGIC ORDER BY count DESC
# MAGIC ```
# MAGIC
# MAGIC **Find a customer's portfolio:**
# MAGIC ```cypher
# MAGIC MATCH (c:Customer {first_name: 'James', last_name: 'Anderson'})
# MAGIC       -[:HAS_ACCOUNT]->(a:Account)
# MAGIC       -[:HAS_POSITION]->(p:Position)
# MAGIC       -[:OF_SECURITY]->(s:Stock)
# MAGIC       -[:OF_COMPANY]->(co:Company)
# MAGIC RETURN c.first_name + ' ' + c.last_name AS customer,
# MAGIC        s.ticker, co.name, p.shares, p.current_value
# MAGIC ```
# MAGIC
# MAGIC **Search documents by vector similarity:**
# MAGIC ```cypher
# MAGIC // Requires calling the embedding endpoint first, but you can browse chunks:
# MAGIC MATCH (c:Chunk)-[:FROM_DOCUMENT]->(d:Document)
# MAGIC WHERE d.document_type = 'customer_profile'
# MAGIC RETURN d.title, c.index, left(c.text, 200) AS preview
# MAGIC ORDER BY d.title, c.index
# MAGIC LIMIT 10
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC
# MAGIC The graph is fully loaded. Continue to:
# MAGIC
# MAGIC - **4 - Neo4j to Lakehouse**: Export Neo4j data back to Delta Lake tables for use with Databricks AI agents
# MAGIC - **5 - AI Agents**: Create Genie and Knowledge Assistant agents
# MAGIC - **6 - Supervisor Agent**: Combine both agents into a unified multi-agent system
# MAGIC - **7 - Augmentation Agent**: Graph augmentation with DSPy
