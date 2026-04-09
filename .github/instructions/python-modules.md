---
applyTo: "*.py"
---

# Python Module Instructions

## Code Style

- Follow PEP 8 style guide strictly
- Use type hints for all function parameters and return values
- Maximum line length: 88 characters (Black formatter standard)
- Use double quotes for strings

## Module Structure

### Standard Module Template

```python
"""
Module Title - Brief Description

Detailed description of the module's purpose and functionality.

Usage:
    from module_name import function_name
    
    result = function_name(param1, param2)

Version: X.Y.Z
"""

from typing import Dict, List, Optional
# Standard library imports first
# Third-party imports second
# Local imports third

__version__ = "X.Y.Z"
__all__ = ["public_function1", "public_function2"]

# Constants
CONSTANT_NAME = "value"

# Functions and classes
```

## Type Hints

Always use comprehensive type hints:

```python
from typing import Dict, List, Optional, Tuple

def get_schema(node_label: str) -> StructType:
    """Get Spark schema for a node label."""
    pass

def process_data(
    input_data: List[Dict[str, str]], 
    config: Optional[Dict[str, any]] = None
) -> Tuple[List[str], int]:
    """Process input data with optional configuration."""
    pass
```

## Docstrings

Use Google-style docstrings with examples:

```python
def get_node_table_name(node_label: str) -> str:
    """
    Get Unity Catalog table name for a node label.

    Args:
        node_label: Neo4j node label (e.g., "Customer", "Bank").

    Returns:
        Unity Catalog table name (e.g., "retail_investment.retail_investment.customer").

    Raises:
        ValueError: If node_label is not defined.

    Example:
        >>> table = get_node_table_name("Customer")
        >>> print(table)
        retail_investment.retail_investment.customer
    """
    pass
```

## PySpark Schemas

### Schema Definition Pattern

```python
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    IntegerType,
    DoubleType,
    TimestampType,
)

# Define schema with semantic names
CUSTOMER_SCHEMA = StructType([
    StructField("neo4j_id", StringType(), nullable=False),
    StructField("customer_id", StringType(), nullable=False),
    StructField("first_name", StringType(), nullable=True),
    StructField("last_name", StringType(), nullable=True),
    StructField("email", StringType(), nullable=True),
    StructField("risk_profile", StringType(), nullable=True),
    StructField("labels", StringType(), nullable=True),
    StructField("ingestion_timestamp", TimestampType(), nullable=True),
])
```

### Schema Dictionary Pattern

```python
NODE_SCHEMAS: Dict[str, StructType] = {
    "Customer": CUSTOMER_SCHEMA,
    "Bank": BANK_SCHEMA,
    "Account": ACCOUNT_SCHEMA,
}
```

## Error Handling

Use descriptive error messages with available options:

```python
def get_schema(label: str) -> StructType:
    """Get schema for a label."""
    if label not in SCHEMAS:
        available = ", ".join(sorted(SCHEMAS.keys()))
        raise ValueError(
            f"No schema defined for label '{label}'. "
            f"Available labels: {available}"
        )
    return SCHEMAS[label]
```

## Constants

### Naming

- Use `UPPER_SNAKE_CASE` for constants
- Group related constants together
- Add comments explaining non-obvious values

```python
# Unity Catalog Configuration
CATALOG_NAME = "retail_investment"
SCHEMA_NAME = "retail_investment"

# Neo4j Connection Settings
DEFAULT_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
```

## Platform Agnostic Design

Keep `neo4j_schemas.py` platform-agnostic:

```python
# GOOD: Platform-agnostic schema definition
CUSTOMER_SCHEMA = StructType([...])

# BAD: Don't include Databricks-specific configs
# TABLE_PATH = "s3://bucket/path"  # This belongs in databricks_constants.py
```

## Databricks-Specific Code

Keep Databricks-specific code in `databricks_constants.py`:

```python
# GOOD: Databricks-specific configuration
CATALOG_NAME = "retail_investment"
SCHEMA_NAME = "retail_investment"

NODE_TABLE_NAMES: Dict[str, str] = {
    "Customer": f"{CATALOG_NAME}.{SCHEMA_NAME}.customer",
}

# Unity Catalog specific functions
def get_node_table_name(node_label: str) -> str:
    """Get Unity Catalog table name for a node label."""
    pass
```

## Validation Functions

Include validation functions for schemas:

```python
def validate_node_label(label: str) -> bool:
    """
    Validate if a node label exists in schema definitions.
    
    Args:
        label: Node label to validate
        
    Returns:
        True if valid, False otherwise
    """
    return label in NODE_SCHEMAS

def get_available_node_labels() -> List[str]:
    """
    Get list of all available node labels.
    
    Returns:
        Sorted list of node labels
    """
    return sorted(NODE_SCHEMAS.keys())
```

## Testing Considerations

While this is a demo repository without formal tests, write code that is testable:

- Pure functions without side effects
- Clear input/output contracts
- Minimal dependencies
- Doctest examples in docstrings

## Import Organization

```python
# 1. Standard library imports
import os
import sys
from typing import Dict, List, Optional

# 2. Third-party imports
from pyspark.sql.types import StructType, StructField
import pandas as pd

# 3. Local application imports
from databricks_constants import CATALOG_NAME, SCHEMA_NAME
```

## Module Exports

Use `__all__` to control public API:

```python
__all__ = [
    "NODE_SCHEMAS",
    "RELATIONSHIP_SCHEMAS",
    "get_node_schema",
    "get_relationship_schema",
]
```

## Version Management

Include version information:

```python
__version__ = "2.0.0"
```

Update version according to semantic versioning:
- Major: Breaking API changes
- Minor: New features, backward compatible
- Patch: Bug fixes
