# Lab 4: Export Neo4j to Databricks Lakehouse

This lab exports graph data from Neo4j back to Databricks as Delta Lake tables, enabling integration with Databricks AI/BI tools.

## Prerequisites

Before running this lab, ensure you have:

1. Completed the setup steps in the main [README.md](../README.md)
2. Completed [1 - Neo4j Import](../labs/1%20-%20Neo4j%20Import.py) to populate Neo4j with data
3. A Databricks cluster with the Neo4j Spark Connector installed

## Cluster Requirements

Create a dedicated cluster with the Neo4j Spark Connector:

1. **Create a new cluster**:
   - Navigate to **Compute** in your Databricks workspace
   - Click **Create Compute**
   - Configure:
     - **Cluster name**: "Neo4j-Export-Cluster"
     - **Access mode**: **Dedicated** (required for Neo4j Spark Connector)
     - **Databricks Runtime**: 13.3 LTS or higher (Spark 3.x)

2. **Install the Neo4j Spark Connector**:
   - Click on your cluster → **Libraries** tab
   - Click **Install New** → **Maven**
   - Enter coordinates:
     ```
     org.neo4j:neo4j-connector-apache-spark_2.12:5.3.1_for_spark_3
     ```
   - Click **Install**

## What Gets Exported

The notebook exports all node and relationship data as Delta tables:

**Node Tables (7)**:
- `customer` - Customer profile data
- `bank` - Financial institution data
- `account` - Customer account information
- `company` - Corporate entity information
- `stock` - Stock and security data
- `position` - Investment portfolio holdings
- `transaction` - Financial transaction records

**Relationship Tables (7)**:
- `has_account` - Customer-Account relationships
- `at_bank` - Account-Bank relationships
- `of_company` - Stock-Company relationships
- `performs` - Account-Transaction relationships
- `benefits_to` - Transaction-Account relationships
- `has_position` - Account-Position relationships
- `of_security` - Position-Stock relationships

## Running the Export

### Option A: Databricks Notebook

1. In Databricks, go to **Workspace** → **Import**
2. Upload `export_neo4j_to_databricks.ipynb`
3. Attach to a cluster with the Neo4j Spark Connector
4. Run all cells

### Option B: Local Python Script

```bash
uv run python lab_4_neo4j_to_lakehouse/export_neo4j_to_databricks.py
```

## Neo4j Spark Connector Configuration

The export uses optimized `labels` and `relationship` options:

```python
# Node extraction
df = spark.read \
    .format("org.neo4j.spark.DataSource") \
    .option("labels", node_label) \
    .load()

# Relationship extraction
df = spark.read \
    .format("org.neo4j.spark.DataSource") \
    .option("relationship", rel_type) \
    .option("relationship.source.labels", source_label) \
    .option("relationship.target.labels", dest_label) \
    .option("relationship.nodes.map", "false") \
    .load()
```

## Verification

After export, verify the tables in Databricks:

```sql
-- List all tables
SHOW TABLES IN <catalog>.<schema>;

-- Check record counts
SELECT 'customer' as table_name, count(*) as records FROM <catalog>.<schema>.customer
UNION ALL
SELECT 'account', count(*) FROM <catalog>.<schema>.account
UNION ALL
SELECT 'bank', count(*) FROM <catalog>.<schema>.bank;
```

## Lakehouse Structure

After export, your Unity Catalog will contain:

```
<catalog>/
├── <schema>/
│   ├── customer         # Node table
│   ├── bank             # Node table
│   ├── account          # Node table
│   ├── company          # Node table
│   ├── stock            # Node table
│   ├── position         # Node table
│   ├── transaction      # Node table
│   ├── has_account      # Relationship table
│   ├── at_bank          # Relationship table
│   ├── of_company       # Relationship table
│   ├── performs         # Relationship table
│   ├── benefits_to      # Relationship table
│   ├── has_position     # Relationship table
│   └── of_security      # Relationship table
```

## Next Steps

Continue to [Lab 5: Create AI Agents](../lab_5_ai_agents/README.md) to set up Databricks Genie and Knowledge Assistants for natural language queries.
