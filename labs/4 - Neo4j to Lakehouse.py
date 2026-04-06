# Databricks notebook source
# MAGIC %md
# MAGIC # Neo4j to Lakehouse
# MAGIC
# MAGIC ### Estimated time: 5-10 minutes
# MAGIC
# MAGIC This notebook exports the Neo4j graph data to Delta tables in Unity Catalog.
# MAGIC After running, you'll have 14 Delta tables (7 node types + 7 relationship types)
# MAGIC available for downstream use with Databricks AI agents, Genie, and analytics.
# MAGIC
# MAGIC ### Prerequisites
# MAGIC
# MAGIC - Run **0 - Required Setup** and **1 - Neo4j Import** first
# MAGIC - Cluster must be **Dedicated** mode with the Neo4j Spark Connector Maven library installed
# MAGIC
# MAGIC ### Output
# MAGIC
# MAGIC Creates 14 Delta tables in Unity Catalog:
# MAGIC - **7 node tables**: customer, bank, account, company, stock, position, transaction
# MAGIC - **7 relationship tables**: has_account, at_bank, of_company, performs, benefits_to, has_position, of_security

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Configuration
# MAGIC
# MAGIC Define the node labels and relationship types to export from Neo4j.

# COMMAND ----------

import time

# Node labels to extract
NODE_LABELS = [
    "Customer",
    "Bank",
    "Account",
    "Company",
    "Stock",
    "Position",
    "Transaction",
]

# Relationships: (type, source_label, target_label)
RELATIONSHIPS = [
    ("HAS_ACCOUNT", "Customer", "Account"),
    ("AT_BANK", "Account", "Bank"),
    ("OF_COMPANY", "Stock", "Company"),
    ("PERFORMS", "Account", "Transaction"),
    ("BENEFITS_TO", "Transaction", "Account"),
    ("HAS_POSITION", "Account", "Position"),
    ("OF_SECURITY", "Position", "Stock"),
]

print(f"Nodes to export: {len(NODE_LABELS)}")
print(f"Relationships to export: {len(RELATIONSHIPS)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Load Credentials
# MAGIC
# MAGIC Retrieve Neo4j connection credentials and Unity Catalog configuration from Databricks Secrets.
# MAGIC The volume path secret is parsed to extract the catalog and schema names, ensuring
# MAGIC consistency with other labs.

# COMMAND ----------

# MAGIC %run ./Includes/config

# COMMAND ----------

_scope = CONFIG["secrets"]["scope_name"]

NEO4J_URL = dbutils.secrets.get(scope=_scope, key="url")
NEO4J_USER = dbutils.secrets.get(scope=_scope, key="username")
NEO4J_PASS = dbutils.secrets.get(scope=_scope, key="password")
NEO4J_DATABASE = "neo4j"

# Extract catalog/schema from volume_path: /Volumes/{catalog}/{schema}/{volume}
volume_path = dbutils.secrets.get(scope=_scope, key="volume_path")
parts = volume_path.strip("/").split("/")
if len(parts) < 3 or parts[0] != "Volumes":
    raise ValueError(
        f"Cannot parse catalog/schema from volume_path: {volume_path}\n"
        f"Expected format: /Volumes/{{catalog}}/{{schema}}/{{volume}}"
    )
CATALOG = parts[1]
SCHEMA = parts[2]
print(f"[OK] Catalog: {CATALOG}")
print(f"[OK] Schema: {SCHEMA}")

# Configure Spark for Neo4j
spark.conf.set("neo4j.url", NEO4J_URL)
spark.conf.set("neo4j.authentication.basic.username", NEO4J_USER)
spark.conf.set("neo4j.authentication.basic.password", NEO4J_PASS)
spark.conf.set("neo4j.database", NEO4J_DATABASE)

print(f"[OK] Neo4j URL: {NEO4J_URL}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Test Connection
# MAGIC
# MAGIC Verify that Spark can connect to Neo4j using the configured credentials.

# COMMAND ----------

print("Testing Neo4j connection...")

try:
    test_df = spark.read.format("org.neo4j.spark.DataSource").option("query", "RETURN 1 AS test").load()
    test_df.collect()
    print("[OK] Connected to Neo4j!")
except Exception as e:
    print(f"[FAIL] {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Setup Unity Catalog
# MAGIC
# MAGIC Verify the target catalog exists and create the schema if needed.

# COMMAND ----------

# Check catalog exists
catalogs = [row.catalog for row in spark.sql("SHOW CATALOGS").collect()]
if CATALOG not in catalogs:
    raise ValueError(f"Catalog '{CATALOG}' not found. Available: {catalogs}")
print(f"[OK] Catalog exists: {CATALOG}")

# Create schema
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
print(f"[OK] Schema ready: {CATALOG}.{SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Define Helper Functions

# COMMAND ----------

def read_nodes(label):
    """Read nodes from Neo4j."""
    return spark.read.format("org.neo4j.spark.DataSource").option("labels", label).load()

def read_relationship(rel_type, source_label, target_label):
    """Read relationships from Neo4j."""
    return (
        spark.read.format("org.neo4j.spark.DataSource")
        .option("relationship", rel_type)
        .option("relationship.source.labels", source_label)
        .option("relationship.target.labels", target_label)
        .option("relationship.nodes.map", "false")
        .load()
    )

def write_table(df, table_name):
    """Write DataFrame to Delta table."""
    full_name = f"{CATALOG}.{SCHEMA}.{table_name}"
    df.write.format("delta").mode("overwrite").saveAsTable(full_name)
    return df.count()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Export Nodes
# MAGIC
# MAGIC Read each node type from Neo4j and write as a Delta table.

# COMMAND ----------

print("=" * 50)
print("EXPORTING NODES")
print("=" * 50)

node_results = {}

for i, label in enumerate(NODE_LABELS, 1):
    table_name = label.lower()
    print(f"\n[{i}/{len(NODE_LABELS)}] {label} -> {table_name}")

    start = time.time()
    df = read_nodes(label)
    count = write_table(df, table_name)
    elapsed = time.time() - start

    node_results[label] = {"count": count, "time": elapsed}
    print(f"    [OK] {count} rows in {elapsed:.2f}s")

print(f"\nExported {len(node_results)} node tables")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7: Export Relationships
# MAGIC
# MAGIC Read each relationship type from Neo4j and write as a Delta table.

# COMMAND ----------

print("=" * 50)
print("EXPORTING RELATIONSHIPS")
print("=" * 50)

rel_results = {}

for i, (rel_type, source, target) in enumerate(RELATIONSHIPS, 1):
    table_name = rel_type.lower()
    print(f"\n[{i}/{len(RELATIONSHIPS)}] {rel_type} -> {table_name}")

    start = time.time()
    df = read_relationship(rel_type, source, target)
    count = write_table(df, table_name)
    elapsed = time.time() - start

    rel_results[rel_type] = {"count": count, "time": elapsed}
    print(f"    [OK] {count} rows in {elapsed:.2f}s")

print(f"\nExported {len(rel_results)} relationship tables")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 8: Validate
# MAGIC
# MAGIC Compare exported row counts against expected values.

# COMMAND ----------

expected_nodes = {
    "Customer": 102, "Bank": 102, "Account": 123, "Company": 102,
    "Stock": 102, "Position": 110, "Transaction": 123,
}

expected_rels = {
    "HAS_ACCOUNT": 123, "AT_BANK": 123, "OF_COMPANY": 102, "PERFORMS": 123,
    "BENEFITS_TO": 123, "HAS_POSITION": 110, "OF_SECURITY": 110,
}

all_valid = True

print(f"{'Table':<15} {'Expected':>10} {'Actual':>10} {'Status':>10}")
print("-" * 50)

for label, expected in expected_nodes.items():
    actual = node_results.get(label, {}).get("count", 0)
    status = "OK" if actual == expected else "MISMATCH"
    if actual != expected:
        all_valid = False
    print(f"{label.lower():<15} {expected:>10} {actual:>10} {status:>10}")

for rel_type, expected in expected_rels.items():
    actual = rel_results.get(rel_type, {}).get("count", 0)
    status = "OK" if actual == expected else "MISMATCH"
    if actual != expected:
        all_valid = False
    print(f"{rel_type.lower():<15} {expected:>10} {actual:>10} {status:>10}")

print(f"\n{'All validations passed!' if all_valid else 'Some counts do not match'}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

total_nodes = sum(r["count"] for r in node_results.values())
total_rels = sum(r["count"] for r in rel_results.values())

print("=" * 50)
print("EXPORT COMPLETE")
print("=" * 50)
print(f"Destination: {CATALOG}.{SCHEMA}")
print(f"Tables: {len(node_results) + len(rel_results)}")
print(f"Total rows: {total_nodes + total_rels}")
print("=" * 50)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC
# MAGIC The graph data is now available as Delta tables. Continue to:
# MAGIC
# MAGIC - **5 - AI Agents**: Create Genie and Knowledge Assistant agents
# MAGIC - **6 - Supervisor Agent**: Combine both agents into a unified multi-agent system
# MAGIC - **7 - Augmentation Agent**: Graph augmentation with DSPy
