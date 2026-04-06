"""Lab 4 Validation: Export Neo4j graph data to Databricks Delta Lake.

Reads nodes and relationships from Neo4j via the Spark Connector and writes
them as Delta tables in Unity Catalog. Verifies each table exists and has
the expected row count.

Usage:
    python -m cli upload run_lab4.py && python -m cli submit run_lab4.py
"""

import os
import sys
import time

# Parse KEY=VALUE parameters from cli.submit into environment variables.
for _arg in sys.argv[1:]:
    if "=" in _arg and not _arg.startswith("-"):
        _key, _, _value = _arg.partition("=")
        os.environ.setdefault(_key, _value)

from pyspark.sql import SparkSession


# Expected counts (must match Lab 2 import)
EXPECTED_NODES = {
    "Customer": 102, "Bank": 102, "Account": 123,
    "Company": 102, "Stock": 102, "Position": 110, "Transaction": 123,
}
EXPECTED_RELS = {
    "HAS_ACCOUNT": 123, "AT_BANK": 123, "OF_COMPANY": 102,
    "PERFORMS": 123, "BENEFITS_TO": 123, "HAS_POSITION": 110, "OF_SECURITY": 110,
}

RELATIONSHIPS = [
    ("HAS_ACCOUNT", "Customer", "Account"),
    ("AT_BANK", "Account", "Bank"),
    ("OF_COMPANY", "Stock", "Company"),
    ("PERFORMS", "Account", "Transaction"),
    ("BENEFITS_TO", "Transaction", "Account"),
    ("HAS_POSITION", "Account", "Position"),
    ("OF_SECURITY", "Position", "Stock"),
]

results = []


def record(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append((name, passed, detail))
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


def _print_summary():
    passed = sum(1 for _, p, _ in results if p)
    failed = sum(1 for _, p, _ in results if not p)
    total = len(results)
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, p, detail in results:
        status = "PASS" if p else "FAIL"
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    print()
    print(f"Total: {total}  Passed: {passed}  Failed: {failed}")
    print("=" * 60)
    print("FAILED" if failed > 0 else "SUCCESS")


def main():
    neo4j_uri = os.environ["NEO4J_URI"]
    neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.environ["NEO4J_PASSWORD"]
    volume_path = os.environ["DATABRICKS_VOLUME_PATH"]

    print("=" * 60)
    print("Lab 4 Validation: Export Neo4j to Databricks Delta Lake")
    print("=" * 60)
    print(f"Neo4j URI:    {neo4j_uri}")
    print(f"Volume path:  {volume_path}")
    print()

    # Parse catalog and schema from volume_path
    # Format: /Volumes/{catalog}/{schema}/{volume}
    parts = volume_path.strip("/").split("/")
    if len(parts) >= 3 and parts[0] == "Volumes":
        catalog = parts[1]
        schema = "graph_data"
    else:
        print(f"Error: Cannot parse catalog from volume_path: {volume_path}")
        sys.exit(1)

    print(f"Target:       {catalog}.{schema}")
    print()

    spark = SparkSession.builder.getOrCreate()

    # Configure Spark for Neo4j
    spark.conf.set("neo4j.url", neo4j_uri)
    spark.conf.set("neo4j.authentication.basic.username", neo4j_username)
    spark.conf.set("neo4j.authentication.basic.password", neo4j_password)
    spark.conf.set("neo4j.database", "neo4j")

    # ── Step 1: Test connection ──────────────────────────────────────────────
    print("[Step 1] Testing Neo4j connection...")
    try:
        df = (
            spark.read.format("org.neo4j.spark.DataSource")
            .option("query", "RETURN 1 AS test")
            .load()
        )
        df.collect()
        record("Neo4j connection", True)
    except Exception as e:
        record("Neo4j connection", False, str(e))
        _print_summary()
        sys.exit(1)

    # ── Step 2: Setup catalog/schema ─────────────────────────────────────────
    print("\n[Step 2] Setting up Unity Catalog...")
    try:
        spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
        record("Create schema", True, f"{catalog}.{schema}")
    except Exception as e:
        record("Create schema", False, str(e))
        _print_summary()
        sys.exit(1)

    # ── Step 3: Export nodes ─────────────────────────────────────────────────
    print("\n[Step 3] Exporting nodes...")
    node_results = {}
    for label, expected in EXPECTED_NODES.items():
        table_name = label.lower()
        full_name = f"{catalog}.{schema}.{table_name}"
        try:
            t0 = time.time()
            df = (
                spark.read.format("org.neo4j.spark.DataSource")
                .option("labels", label)
                .load()
            )
            df.write.format("delta").mode("overwrite").saveAsTable(full_name)
            count = df.count()
            elapsed = time.time() - t0
            node_results[label] = count
            record(f"Export {label}", count == expected,
                   f"{count} rows in {elapsed:.1f}s (expected {expected})")
        except Exception as e:
            record(f"Export {label}", False, str(e))

    # ── Step 4: Export relationships ─────────────────────────────────────────
    print("\n[Step 4] Exporting relationships...")
    rel_results = {}
    for rel_type, src_label, tgt_label in RELATIONSHIPS:
        table_name = rel_type.lower()
        full_name = f"{catalog}.{schema}.{table_name}"
        expected = EXPECTED_RELS[rel_type]
        try:
            t0 = time.time()
            df = (
                spark.read.format("org.neo4j.spark.DataSource")
                .option("relationship", rel_type)
                .option("relationship.source.labels", src_label)
                .option("relationship.target.labels", tgt_label)
                .option("relationship.nodes.map", "false")
                .load()
            )
            df.write.format("delta").mode("overwrite").saveAsTable(full_name)
            count = df.count()
            elapsed = time.time() - t0
            rel_results[rel_type] = count
            record(f"Export {rel_type}", count == expected,
                   f"{count} rows in {elapsed:.1f}s (expected {expected})")
        except Exception as e:
            record(f"Export {rel_type}", False, str(e))

    # ── Step 5: Verify tables exist and are readable ─────────────────────────
    print("\n[Step 5] Verifying tables...")
    all_tables = list(EXPECTED_NODES.keys()) + [r[0] for r in RELATIONSHIPS]
    for name in all_tables:
        table_name = name.lower()
        full_name = f"{catalog}.{schema}.{table_name}"
        try:
            count = spark.table(full_name).count()
            record(f"Read {table_name}", count > 0, f"{count} rows")
        except Exception as e:
            record(f"Read {table_name}", False, str(e))

    _print_summary()
    failed = sum(1 for _, p, _ in results if not p)
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
