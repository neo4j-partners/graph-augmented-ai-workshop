---
applyTo: "*.md"
excludeAgent: "coding-agent"
---

# Documentation Instructions

These instructions apply only to Markdown documentation files, not to code files.

## Markdown Style Guide

### Headers

- Use ATX-style headers (`#`, `##`, `###`)
- One `#` for document title
- Don't skip header levels
- Add blank lines before and after headers

```markdown
# Document Title

## Section Header

### Subsection Header
```

### Lists

**Unordered Lists:**
- Use `-` for unordered lists
- Indent with 2 spaces for nested items
- Add blank line before list

**Ordered Lists:**
- Use `1.` for all items (auto-numbering)
- Or use sequential numbers if order matters
- Maintain consistent indentation

### Code Blocks

Use fenced code blocks with language identifiers:

````markdown
```python
def example_function():
    return "Hello, World!"
```

```sql
CREATE CATALOG IF NOT EXISTS retail_investment;
```

```bash
databricks secrets create-scope neo4j
```
````

### Emphasis

- **Bold** for important terms: `**bold**`
- *Italic* for emphasis: `*italic*`
- `Code` for inline code: `` `code` ``

### Links

```markdown
[Link text](https://example.com)
[Relative link](./DATA_IMPORT.md)
[Reference link][ref-id]

[ref-id]: https://example.com
```

## Document Structure

### README.md Structure

1. **Title and Badges** (if applicable)
2. **Overview** - What the project does
3. **Prerequisites** - What's needed before starting
4. **Setup Instructions** - Step-by-step guide
5. **Usage** - How to use the project
6. **Project Structure** - File/directory layout
7. **Troubleshooting** - Common issues and solutions
8. **Contributing** - How to contribute
9. **License** - License information

### Technical Documentation

1. **Title**
2. **Purpose** - Why this document exists
3. **Prerequisites** - Required knowledge/setup
4. **Instructions** - Detailed steps
5. **Examples** - Practical examples
6. **References** - Additional resources

## Technical Documentation Best Practices

### Step-by-Step Instructions

Number major steps and use clear action verbs:

```markdown
### Step 1: Create Databricks Catalog

First, create the Unity Catalog namespace:

1. Navigate to **Catalog** in Databricks workspace
2. Click **Create Catalog**
3. Enter name: `retail_investment`
4. Click **Create**

Expected outcome: A new catalog appears in the catalog list.
```

### Code Examples

Always include:
- Context about what the code does
- Expected input/output
- Common variations

```markdown
### Connection Configuration

Set your Neo4j connection details:

```python
NEO4J_URL = "neo4j+s://xxxxx.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = dbutils.secrets.get("neo4j", "password")
```

Replace `xxxxx` with your actual Neo4j instance ID.
````

### Prerequisites Sections

Be explicit about requirements:

```markdown
## Prerequisites

Before you begin, ensure you have:

- **Databricks Workspace** with Unity Catalog enabled
- **Neo4j Database** (AuraDB or Desktop)
- **Proper permissions**: Catalog creation, cluster creation
- **Installed tools**: Databricks CLI (optional)
```

### Troubleshooting Sections

Organize by problem type:

```markdown
## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to Neo4j database

**Solution**: 
- Verify Neo4j instance is running
- Check firewall settings
- Validate credentials in Databricks secrets
- Test connection with: `neo4j://your-instance`

### Permission Issues

**Problem**: "Permission denied" when creating catalog

**Solution**:
- Verify account admin or metastore admin role
- Check Unity Catalog is enabled
- Contact workspace administrator
```

## Schema and Data Model Documentation

### Entity Descriptions

Describe entities with:
- Purpose
- Key attributes
- Relationships
- Example use cases

```markdown
### Customer Node

Represents individual customers in the investment platform.

**Key Attributes:**
- `customer_id` - Unique customer identifier
- `first_name`, `last_name` - Customer name
- `email` - Contact email
- `risk_profile` - Investment risk tolerance (Conservative, Moderate, Aggressive)
- `credit_score` - Credit rating

**Relationships:**
- `(Customer)-[:HAS_ACCOUNT]->(Account)` - Owns accounts
```

### Relationship Documentation

```markdown
### HAS_ACCOUNT Relationship

Connects customers to their accounts.

**Pattern:** `(Customer)-[:HAS_ACCOUNT]->(Account)`

**Properties:**
- `account_type` - Type of account relationship
- `opened_date` - When account was opened

**Business Rules:**
- One customer can have multiple accounts
- Each account belongs to exactly one customer
```

## API and Configuration Documentation

### Configuration Parameters

```markdown
### Configuration Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `NEO4J_URL` | String | Yes | - | Neo4j connection URL |
| `NEO4J_USERNAME` | String | Yes | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | String | Yes | - | Neo4j password |
| `CATALOG_NAME` | String | No | `retail_investment` | Unity Catalog name |
```

### Function Documentation

```markdown
### `get_node_table_name(node_label: str) -> str`

Get Unity Catalog table name for a node label.

**Parameters:**
- `node_label` (str): Neo4j node label (e.g., "Customer", "Bank")

**Returns:**
- (str): Unity Catalog table name (e.g., "retail_investment.retail_investment.customer")

**Raises:**
- `ValueError`: If node_label is not defined

**Example:**
```python
table = get_node_table_name("Customer")
print(table)  # "retail_investment.retail_investment.customer"
```
````

## Warnings and Notes

Use appropriate admonitions:

```markdown
⚠️ **WARNING**: This operation will overwrite existing data

ℹ️ **NOTE**: This feature requires Databricks Runtime 13.3 or higher

✓ **TIP**: Use `--dry-run` flag to preview changes first
```

## Version Information

Include version info for dependencies:

```markdown
### Required Versions

- **Databricks Runtime**: 13.3 LTS or higher
- **Neo4j Spark Connector**: 5.3.1 for Spark 3
- **Neo4j Python Driver**: 6.0.2
- **Apache Spark**: 3.x
```

## Cross-References

Link to related documentation:

```markdown
For detailed setup instructions, see [DATA_IMPORT.md](./DATA_IMPORT.md).

The graph schema is documented in [SCHEMA_MODEL_OVERVIEW.md](./SCHEMA_MODEL_OVERVIEW.md).
```

## Examples Section

Always include practical examples:

```markdown
## Usage Examples

### Example 1: Extract Customer Data

```python
from neo4j_schemas import get_node_schema
from databricks_constants import get_node_table_name

# Get schema and table name
schema = get_node_schema("Customer")
table_name = get_node_table_name("Customer")

# Extract data
df = spark.read.format("org.neo4j.spark.DataSource") \
    .option("labels", "Customer") \
    .load()

# Save to Unity Catalog
df.write.mode("overwrite").saveAsTable(table_name)
```

**Output:**
```
✓ Created table: retail_investment.retail_investment.customer
  Records: 102
```
````

## Maintenance Notes

Include information about keeping docs updated:

```markdown
## Maintaining This Documentation

When adding new features:
1. Update README.md with new setup steps
2. Add examples to relevant sections
3. Update schema documentation if data model changes
4. Add troubleshooting entries for common issues
```

## Line Length

- Aim for 80-100 characters per line in paragraphs
- Exception: Code blocks, URLs, tables can be longer
- Use natural breaks in sentences

## Consistency

Maintain consistency across all documentation:
- Terminology (e.g., "Unity Catalog" not "unity catalog")
- Code style (e.g., always use `` `code` `` for inline code)
- Section ordering
- Header capitalization (Title Case for major headers)
