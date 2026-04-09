---
applyTo: "*.ipynb"
---

# Jupyter Notebook Instructions

## Notebook Structure

Organize notebooks with clear sections:

1. **Title and Overview** (Markdown cell)
2. **Imports and Setup** (Code cells)
3. **Configuration** (Code cells with secrets management)
4. **Function Definitions** (Code cells)
5. **Main Execution** (Code cells)
6. **Verification and Testing** (Code cells)

## Databricks-Specific Guidelines

### Secrets Management

Always use Databricks secrets for sensitive data:

```python
# GOOD: Use secrets
neo4j_password = dbutils.secrets.get("neo4j", "password")
neo4j_url = dbutils.secrets.get("neo4j", "url")

# BAD: Never hardcode credentials
# neo4j_password = "my_password_123"
```

### Environment Variables

```python
import os

# Get environment variables with defaults
neo4j_url = os.getenv("NEO4J_URL", dbutils.secrets.get("neo4j", "url"))
neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
```

## Neo4j Spark Connector Usage

### Node Extraction Pattern

```python
def extract_nodes(node_label: str, schema: StructType) -> DataFrame:
    """
    Extract nodes from Neo4j.
    
    Args:
        node_label: Neo4j node label (e.g., "Customer")
        schema: PySpark schema for the node type
        
    Returns:
        DataFrame with node data
    """
    df = spark.read \
        .format("org.neo4j.spark.DataSource") \
        .option("url", neo4j_url) \
        .option("authentication.basic.username", neo4j_username) \
        .option("authentication.basic.password", neo4j_password) \
        .option("database", neo4j_database) \
        .option("labels", node_label) \
        .load()
    
    return df
```

### Relationship Extraction Pattern

```python
def extract_relationships(
    rel_type: str,
    source_label: str,
    dest_label: str,
    schema: StructType
) -> DataFrame:
    """
    Extract relationships from Neo4j.
    
    Args:
        rel_type: Relationship type (e.g., "HAS_ACCOUNT")
        source_label: Source node label
        dest_label: Destination node label
        schema: PySpark schema for the relationship
        
    Returns:
        DataFrame with relationship data
    """
    df = spark.read \
        .format("org.neo4j.spark.DataSource") \
        .option("url", neo4j_url) \
        .option("authentication.basic.username", neo4j_username) \
        .option("authentication.basic.password", neo4j_password) \
        .option("database", neo4j_database) \
        .option("relationship", rel_type) \
        .option("relationship.source.labels", source_label) \
        .option("relationship.target.labels", dest_label) \
        .option("relationship.nodes.map", "false") \
        .load()
    
    return df
```

## Unity Catalog Operations

### Table Creation

```python
# Write DataFrame to Unity Catalog table
df.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(table_name)

print(f"✓ Created table: {table_name}")
print(f"  Records: {df.count()}")
```

### Table Verification

```python
# Verify table creation
table_df = spark.read.table(table_name)
print(f"Table {table_name}:")
print(f"  Row count: {table_df.count()}")
print(f"  Schema: {table_df.columns}")
table_df.show(5)
```

## Error Handling

Use try-except blocks for external operations:

```python
try:
    # Attempt Neo4j connection
    df = extract_nodes("Customer", CUSTOMER_SCHEMA)
    print(f"✓ Successfully extracted {df.count()} customers")
except Exception as e:
    print(f"✗ Failed to extract customers: {str(e)}")
    print("  Check Neo4j connection settings and credentials")
    raise
```

## Markdown Cells

### Section Headers

```markdown
# Main Section Title

## Subsection Title

### Sub-subsection Title
```

### Documentation Best Practices

- Explain what the following code does
- Include expected outcomes
- Mention prerequisites
- Document any assumptions

Example:
```markdown
## Extract Customer Nodes

This section extracts customer data from Neo4j and loads it into Unity Catalog.

**Prerequisites:**
- Neo4j database is running and accessible
- Databricks secrets are configured (`neo4j/password`, `neo4j/url`)
- Unity Catalog is enabled

**Expected Output:**
- A Delta table at `retail_investment.retail_investment.customer`
- Approximately 100+ customer records
```

## Display and Visualization

```python
# Display DataFrame with formatting
from pyspark.sql.functions import col

# Show sample records
print("Sample Customer Records:")
df.select("customer_id", "first_name", "last_name", "email") \
  .show(10, truncate=False)

# Show statistics
print("\nData Statistics:")
df.describe().show()

# Count by category
print("\nRisk Profile Distribution:")
df.groupBy("risk_profile").count().orderBy("count", ascending=False).show()
```

## Import Organization

```python
# Standard library imports
import os
import sys
from datetime import datetime

# PySpark imports
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, current_timestamp, lit
from pyspark.sql.types import StructType, StructField, StringType

# Local module imports
from neo4j_schemas import NODE_SCHEMAS, RELATIONSHIP_SCHEMAS
from databricks_constants import NODE_TABLE_NAMES, RELATIONSHIP_TABLE_NAMES
```

## Configuration Cell Pattern

```python
# ============================================================
# CONFIGURATION
# ============================================================

# Neo4j Connection
NEO4J_URL = dbutils.secrets.get("neo4j", "url")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = dbutils.secrets.get("neo4j", "password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# Unity Catalog
CATALOG_NAME = "retail_investment"
SCHEMA_NAME = "retail_investment"

# Module Paths
PYTHON_REPO_URL = "/Workspace/Users/your-email@example.com/neo4j-databricks"

print("Configuration loaded successfully")
print(f"  Neo4j URL: {NEO4J_URL}")
print(f"  Neo4j Database: {NEO4J_DATABASE}")
print(f"  Unity Catalog: {CATALOG_NAME}.{SCHEMA_NAME}")
```

## Progress Tracking

```python
# Track processing progress
total_tables = len(NODE_TABLE_NAMES)
processed = 0

for node_label, table_name in NODE_TABLE_NAMES.items():
    processed += 1
    print(f"[{processed}/{total_tables}] Processing {node_label}...")
    
    try:
        df = extract_nodes(node_label, NODE_SCHEMAS[node_label])
        df.write.mode("overwrite").saveAsTable(table_name)
        print(f"  ✓ Created {table_name} ({df.count()} records)")
    except Exception as e:
        print(f"  ✗ Failed: {str(e)}")

print(f"\nCompleted: {processed}/{total_tables} tables processed")
```

## Cell Outputs

- Keep cell outputs clean and informative
- Use emoji or symbols for status indicators: ✓ ✗ ⚠
- Include row counts and statistics
- Show sample data with `show()` or `display()`

## Testing Cells

```python
# ============================================================
# VERIFICATION
# ============================================================

def verify_table(table_name: str, expected_min_rows: int = 0) -> bool:
    """Verify that a table exists and has data."""
    try:
        df = spark.read.table(table_name)
        row_count = df.count()
        
        if row_count >= expected_min_rows:
            print(f"✓ {table_name}: {row_count} rows")
            return True
        else:
            print(f"⚠ {table_name}: {row_count} rows (expected >= {expected_min_rows})")
            return False
    except Exception as e:
        print(f"✗ {table_name}: Not found or error - {str(e)}")
        return False

# Run verification
print("Verifying tables...")
print("\nNode Tables:")
for node_label, table_name in NODE_TABLE_NAMES.items():
    verify_table(table_name, expected_min_rows=1)

print("\nRelationship Tables:")
for rel_type, table_name in RELATIONSHIP_TABLE_NAMES.items():
    verify_table(table_name, expected_min_rows=1)
```

## Common Patterns

### Incremental Development

Test small portions before running full notebook:

```python
# Test with LIMIT first
test_query = """
    MATCH (c:Customer)
    RETURN c
    LIMIT 10
"""

# Then run full extraction
```

### Memory Management

```python
# Clear cache for large operations
spark.catalog.clearCache()

# Persist intermediate results
df_cached = df.cache()
df_cached.count()  # Materialize the cache
```

## Comments

Use comments to explain:
- Why certain approaches were chosen
- Known limitations or issues
- TODO items for future improvements
- References to documentation

```python
# Using relationship.nodes.map=false to get node IDs instead of full node data
# This reduces payload size and improves performance
# See: https://neo4j.com/docs/spark/current/reading/#relationship-nodes-map
df = spark.read \
    .format("org.neo4j.spark.DataSource") \
    .option("relationship.nodes.map", "false") \
    .load()
```
