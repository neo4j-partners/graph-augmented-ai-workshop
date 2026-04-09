# GitHub Copilot Instructions for Neo4j-Databricks Demo

## Project Overview

This is a demonstration repository showcasing the integration of Neo4j graph data with Databricks lakehouse architecture. The project extracts graph data from Neo4j into Delta Lake tables and builds a multi-agent AI system for retail investment analysis.

## Repository Structure

- **Python Modules**: `neo4j_schemas.py`, `databricks_constants.py` - Reusable schema definitions and constants
- **Jupyter Notebooks**: `data_extraction.ipynb`, `OpenAI LLM Agent Inquiry.ipynb` - ETL and AI agent notebooks
- **Data Files**: 
  - `data/csv/` - Source CSV files for Neo4j import
  - `data/profiles/` - Customer profile documents for knowledge agents
- **Documentation**: Multiple markdown files describing setup, data model, and use cases

## Technology Stack

- **Neo4j**: Graph database (AuraDB or Desktop)
- **Databricks**: Lakehouse platform with Unity Catalog
- **Apache Spark**: Data processing (via Neo4j Spark Connector)
- **Python**: Primary programming language
- **PySpark**: Spark DataFrame API for data transformations

## Coding Standards

### Python Code

1. **Style**: Follow PEP 8 conventions
2. **Type Hints**: Use type hints for function parameters and return values
3. **Docstrings**: Include comprehensive docstrings with examples
4. **Naming**:
   - Variables: `snake_case`
   - Constants: `UPPER_SNAKE_CASE`
   - Functions: `snake_case`
   - Classes: `PascalCase`

### Spark Schemas

- Define schemas in `neo4j_schemas.py` using PySpark StructType
- Use semantic, business-meaningful column names
- Include metadata fields: `neo4j_id`, `labels`, `ingestion_timestamp`
- Keep schemas platform-agnostic (separate Databricks-specific configs in `databricks_constants.py`)

### Unity Catalog Names

- All table names use three-level namespace: `catalog.schema.table`
- Current catalog: `retail_investment`
- Current schema: `retail_investment`
- Define all table names in `databricks_constants.py`

## Neo4j Graph Model

### Node Types (7)
- **Customer**: Customer profiles with demographics and risk profiles
- **Bank**: Financial institutions
- **Account**: Customer accounts (checking, savings, investment)
- **Company**: Corporate entities
- **Stock**: Securities and stocks
- **Position**: Investment portfolio holdings
- **Transaction**: Financial transactions

### Relationship Types (7)
- `HAS_ACCOUNT`: Customer → Account
- `AT_BANK`: Account → Bank
- `OF_COMPANY`: Stock → Company
- `PERFORMS`: Account → Transaction
- `BENEFITS_TO`: Transaction → Account
- `HAS_POSITION`: Account → Position
- `OF_SECURITY`: Position → Stock

## Key Guidelines for Changes

### When Modifying Schemas (`neo4j_schemas.py`)

1. Keep schemas platform-agnostic
2. Maintain backward compatibility with existing Delta tables
3. Update both node and relationship schemas if structure changes
4. Include type-safe validation functions
5. Document any schema changes in docstrings

### When Modifying Constants (`databricks_constants.py`)

1. Use the three-level namespace format: `{CATALOG_NAME}.{SCHEMA_NAME}.{table_name}`
2. Update both `NODE_TABLE_NAMES` and `RELATIONSHIP_TABLE_NAMES` dictionaries
3. Keep table names lowercase with underscores
4. Maintain consistency with Neo4j labels/relationship types

### When Modifying Notebooks

1. **Cell Structure**: Keep logical separation (imports, config, functions, execution)
2. **Documentation**: Add markdown cells explaining complex operations
3. **Error Handling**: Include try-except blocks for external connections
4. **Secrets**: Never hardcode credentials - use Databricks secrets
5. **Testing**: Test cells incrementally before running full notebook

### When Adding New Features

1. **Data Extraction**: Add new node/relationship types to `neo4j_schemas.py` first
2. **Constants**: Update `databricks_constants.py` with new table names
3. **Documentation**: Update relevant markdown files (README.md, SCHEMA_MODEL_OVERVIEW.md)
4. **Data Files**: Add new CSV files to `data/csv/` with proper formatting

## Dependencies

### Databricks Cluster Requirements

- **Access Mode**: Must be "Dedicated (formerly: Single user)" - REQUIRED for Neo4j Spark Connector
- **Runtime**: 13.3 LTS or higher (Spark 3.x)
- **Libraries**:
  - Maven: `org.neo4j:neo4j-connector-apache-spark_2.12:5.3.1_for_spark_3`
  - PyPI: `neo4j==6.0.2`

### Neo4j Spark Connector Usage

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

## Testing

- This is a demo/tutorial repository without automated tests
- Manual testing via Databricks notebooks is the primary validation method
- Test data extraction by verifying row counts in Unity Catalog
- Test AI agents by running sample queries

## Common Tasks

### Adding a New Node Type

1. Add schema to `NODE_SCHEMAS` in `neo4j_schemas.py`
2. Add table name to `NODE_TABLE_NAMES` in `databricks_constants.py`
3. Update the extraction notebook to include the new node type
4. Update documentation (README.md, SCHEMA_MODEL_OVERVIEW.md)

### Adding a New Relationship Type

1. Add schema to `RELATIONSHIP_SCHEMAS` in `neo4j_schemas.py`
2. Add table name to `RELATIONSHIP_TABLE_NAMES` in `databricks_constants.py`
3. Update the extraction notebook to include the new relationship
4. Update documentation with the relationship pattern

### Modifying Data Model

1. Update Neo4j importer model: `neo4j_importer_model_financial_demo.json`
2. Update source CSV files in `data/csv/`
3. Update schemas in `neo4j_schemas.py`
4. Re-run data extraction notebook
5. Update all documentation

## Security Considerations

1. **Never commit secrets** to the repository
2. Use Databricks secrets for:
   - Neo4j passwords
   - Neo4j connection URLs
   - Any API keys
3. Store secrets in scope: `neo4j`
4. Access via: `dbutils.secrets.get("neo4j", "password")`

## Environment Variables

When running the extraction notebook, ensure these are set:
- `NEO4J_URL`: Neo4j connection URL (e.g., `neo4j+s://xxxxx.databases.neo4j.io`)
- `NEO4J_USERNAME`: Neo4j username (typically `neo4j`)
- `NEO4J_DATABASE`: Neo4j database name (typically `neo4j`)
- Secrets: `neo4j/password`, `neo4j/url`

## Documentation Style

- Use clear, concise language
- Include code examples where applicable
- Provide step-by-step instructions for complex processes
- Use proper Markdown formatting
- Include troubleshooting sections for common issues
