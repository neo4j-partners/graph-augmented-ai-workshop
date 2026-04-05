"""Lab 2 Validation: Import financial demo data into Neo4j.

Destructive — clears Neo4j before importing. Reads CSV files from the Unity
Catalog Volume, transforms data types, creates constraints, writes nodes and
relationships via the Neo4j Spark Connector, then verifies counts.

Usage:
    python -m cli upload run_lab2.py && python -m cli submit run_lab2.py
"""

import argparse
import sys
import time

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType


# Expected counts for validation
EXPECTED_NODES = {
    "Customer": 102, "Bank": 102, "Account": 123,
    "Company": 102, "Stock": 102, "Position": 110, "Transaction": 123,
}
EXPECTED_RELS = {
    "HAS_ACCOUNT": 123, "AT_BANK": 123, "OF_COMPANY": 102,
    "PERFORMS": 123, "BENEFITS_TO": 123, "HAS_POSITION": 110, "OF_SECURITY": 110,
}

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


def write_nodes(spark, df, label, node_key):
    count = df.count()
    t0 = time.time()
    (
        df.write.format("org.neo4j.spark.DataSource")
        .mode("Append")
        .option("labels", f":{label}")
        .option("node.keys", node_key)
        .save()
    )
    elapsed = time.time() - t0
    print(f"    {label}: {count} nodes in {elapsed:.1f}s")
    return count


def write_relationship(spark, df, rel_type, src_label, src_key, tgt_label, tgt_key):
    count = df.count()
    t0 = time.time()
    (
        df.write.format("org.neo4j.spark.DataSource")
        .mode("Append")
        .option("relationship", rel_type)
        .option("relationship.save.strategy", "keys")
        .option("relationship.source.save.mode", "Match")
        .option("relationship.source.labels", f":{src_label}")
        .option("relationship.source.node.keys", f"{src_key}:{src_key}")
        .option("relationship.target.save.mode", "Match")
        .option("relationship.target.labels", f":{tgt_label}")
        .option("relationship.target.node.keys", f"{tgt_key}:{tgt_key}")
        .save()
    )
    elapsed = time.time() - t0
    print(f"    {rel_type}: {count} rels in {elapsed:.1f}s")
    return count


def main():
    parser = argparse.ArgumentParser(description="Lab 2: Import Financial Data to Neo4j")
    parser.add_argument("--neo4j-uri", required=True)
    parser.add_argument("--neo4j-username", default="neo4j")
    parser.add_argument("--neo4j-password", required=True)
    parser.add_argument("--volume-path", required=True)
    args = parser.parse_args()

    print("=" * 60)
    print("Lab 2 Validation: Import Financial Data to Neo4j")
    print("=" * 60)
    print(f"Neo4j URI:    {args.neo4j_uri}")
    print(f"Volume path:  {args.volume_path}")
    print()

    spark = SparkSession.builder.getOrCreate()

    # Configure Spark for Neo4j
    spark.conf.set("neo4j.url", args.neo4j_uri)
    spark.conf.set("neo4j.authentication.basic.username", args.neo4j_username)
    spark.conf.set("neo4j.authentication.basic.password", args.neo4j_password)
    spark.conf.set("neo4j.database", "neo4j")

    # ── Step 1: Clear database ───────────────────────────────────────────────
    print("[Step 1] Clearing Neo4j database...")
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(args.neo4j_uri, auth=(args.neo4j_username, args.neo4j_password))
        with driver.session(database="neo4j") as session:
            summary = session.run("MATCH (n) DETACH DELETE n").consume()
            nodes_del = summary.counters.nodes_deleted
            rels_del = summary.counters.relationships_deleted
        driver.close()
        record("Clear database", True, f"deleted {nodes_del} nodes, {rels_del} rels")
    except Exception as e:
        record("Clear database", False, str(e))
        _print_summary()
        sys.exit(1)

    # ── Step 2: Load CSV files ───────────────────────────────────────────────
    print("\n[Step 2] Loading CSV files...")
    csv_path = f"{args.volume_path}/csv"
    try:
        data = {}
        files = [
            ("customers", "customers.csv"), ("banks", "banks.csv"),
            ("accounts", "accounts.csv"), ("companies", "companies.csv"),
            ("stocks", "stocks.csv"), ("positions", "portfolio_holdings.csv"),
            ("transactions", "transactions.csv"),
        ]
        for key, filename in files:
            df = spark.read.option("header", "true").csv(f"{csv_path}/{filename}")
            data[key] = df
            print(f"    {filename}: {df.count()} rows")
        record("Load CSV files", True, f"{len(files)} files loaded")
    except Exception as e:
        record("Load CSV files", False, str(e))
        _print_summary()
        sys.exit(1)

    # ── Step 3: Transform data types ─────────────────────────────────────────
    print("\n[Step 3] Transforming data types...")
    try:
        data["customers"] = (
            data["customers"]
            .withColumn("annual_income", F.col("annual_income").cast(IntegerType()))
            .withColumn("credit_score", F.col("credit_score").cast(IntegerType()))
            .withColumn("registration_date", F.to_date(F.col("registration_date")))
            .withColumn("date_of_birth", F.to_date(F.col("date_of_birth")))
        )
        data["banks"] = (
            data["banks"]
            .withColumn("total_assets_billions", F.col("total_assets_billions").cast(DoubleType()))
            .withColumn("established_year", F.col("established_year").cast(IntegerType()))
        )
        data["accounts"] = (
            data["accounts"]
            .withColumn("balance", F.col("balance").cast(DoubleType()))
            .withColumn("interest_rate", F.col("interest_rate").cast(DoubleType()))
            .withColumn("opened_date", F.to_date(F.col("opened_date")))
        )
        data["companies"] = (
            data["companies"]
            .withColumn("market_cap_billions", F.col("market_cap_billions").cast(DoubleType()))
            .withColumn("annual_revenue_billions", F.col("annual_revenue_billions").cast(DoubleType()))
            .withColumn("founded_year", F.col("founded_year").cast(IntegerType()))
            .withColumn("employee_count", F.col("employee_count").cast(IntegerType()))
        )
        data["stocks"] = (
            data["stocks"]
            .withColumn("current_price", F.col("current_price").cast(DoubleType()))
            .withColumn("previous_close", F.col("previous_close").cast(DoubleType()))
            .withColumn("opening_price", F.col("opening_price").cast(DoubleType()))
            .withColumn("day_high", F.col("day_high").cast(DoubleType()))
            .withColumn("day_low", F.col("day_low").cast(DoubleType()))
            .withColumn("volume", F.col("volume").cast(IntegerType()))
            .withColumn("market_cap_billions", F.col("market_cap_billions").cast(DoubleType()))
            .withColumn("pe_ratio", F.col("pe_ratio").cast(DoubleType()))
            .withColumn("dividend_yield", F.col("dividend_yield").cast(DoubleType()))
            .withColumn("fifty_two_week_high", F.col("fifty_two_week_high").cast(DoubleType()))
            .withColumn("fifty_two_week_low", F.col("fifty_two_week_low").cast(DoubleType()))
        )
        data["positions"] = (
            data["positions"]
            .withColumnRenamed("holding_id", "position_id")
            .withColumn("shares", F.col("shares").cast(IntegerType()))
            .withColumn("purchase_price", F.col("purchase_price").cast(DoubleType()))
            .withColumn("current_value", F.col("current_value").cast(DoubleType()))
            .withColumn("percentage_of_portfolio", F.col("percentage_of_portfolio").cast(DoubleType()))
            .withColumn("purchase_date", F.to_date(F.col("purchase_date")))
        )
        data["transactions"] = (
            data["transactions"]
            .withColumn("amount", F.col("amount").cast(DoubleType()))
            .withColumn("transaction_date", F.to_date(F.col("transaction_date")))
        )
        record("Transform data types", True)
    except Exception as e:
        record("Transform data types", False, str(e))
        _print_summary()
        sys.exit(1)

    # ── Step 4: Create constraints ───────────────────────────────────────────
    print("\n[Step 4] Creating constraints...")
    try:
        driver = GraphDatabase.driver(args.neo4j_uri, auth=(args.neo4j_username, args.neo4j_password))
        constraints = [
            ("customer_id_unique", "Customer", "customer_id"),
            ("bank_id_unique", "Bank", "bank_id"),
            ("account_id_unique", "Account", "account_id"),
            ("company_id_unique", "Company", "company_id"),
            ("stock_id_unique", "Stock", "stock_id"),
            ("position_id_unique", "Position", "position_id"),
            ("transaction_id_unique", "Transaction", "transaction_id"),
        ]
        with driver.session(database="neo4j") as session:
            for name, label, prop in constraints:
                session.run(
                    f"CREATE CONSTRAINT {name} IF NOT EXISTS "
                    f"FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
                )
        driver.close()
        record("Create constraints", True, f"{len(constraints)} constraints")
    except Exception as e:
        record("Create constraints", False, str(e))

    # ── Step 5: Write nodes ──────────────────────────────────────────────────
    print("\n[Step 5] Writing nodes...")
    try:
        write_nodes(spark, data["customers"], "Customer", "customer_id")
        write_nodes(spark, data["banks"], "Bank", "bank_id")

        account_props = data["accounts"].select(
            "account_id", "account_number", "account_type",
            "balance", "currency", "opened_date", "status", "interest_rate"
        )
        write_nodes(spark, account_props, "Account", "account_id")
        write_nodes(spark, data["companies"], "Company", "company_id")

        stock_props = data["stocks"].select(
            "stock_id", "ticker", "current_price", "previous_close", "opening_price",
            "day_high", "day_low", "volume", "market_cap_billions", "pe_ratio",
            "dividend_yield", "fifty_two_week_high", "fifty_two_week_low", "exchange"
        )
        write_nodes(spark, stock_props, "Stock", "stock_id")

        position_props = data["positions"].select(
            "position_id", "shares", "purchase_price", "purchase_date",
            "current_value", "percentage_of_portfolio"
        )
        write_nodes(spark, position_props, "Position", "position_id")

        transaction_props = data["transactions"].select(
            "transaction_id", "amount", "currency", "transaction_date",
            "transaction_time", "type", "status", "description"
        )
        write_nodes(spark, transaction_props, "Transaction", "transaction_id")
        record("Write nodes", True, "7 node types written")
    except Exception as e:
        record("Write nodes", False, str(e))
        _print_summary()
        sys.exit(1)

    # ── Step 6: Write relationships ──────────────────────────────────────────
    print("\n[Step 6] Writing relationships...")
    try:
        write_relationship(spark, data["accounts"].select("customer_id", "account_id"),
                           "HAS_ACCOUNT", "Customer", "customer_id", "Account", "account_id")
        write_relationship(spark, data["accounts"].select("account_id", "bank_id"),
                           "AT_BANK", "Account", "account_id", "Bank", "bank_id")
        write_relationship(spark, data["stocks"].select("stock_id", "company_id"),
                           "OF_COMPANY", "Stock", "stock_id", "Company", "company_id")
        write_relationship(spark,
                           data["transactions"].select(F.col("from_account_id").alias("account_id"), "transaction_id"),
                           "PERFORMS", "Account", "account_id", "Transaction", "transaction_id")
        write_relationship(spark,
                           data["transactions"].select("transaction_id", F.col("to_account_id").alias("account_id")),
                           "BENEFITS_TO", "Transaction", "transaction_id", "Account", "account_id")
        write_relationship(spark, data["positions"].select("account_id", "position_id"),
                           "HAS_POSITION", "Account", "account_id", "Position", "position_id")
        write_relationship(spark, data["positions"].select("position_id", "stock_id"),
                           "OF_SECURITY", "Position", "position_id", "Stock", "stock_id")
        record("Write relationships", True, "7 relationship types written")
    except Exception as e:
        record("Write relationships", False, str(e))
        _print_summary()
        sys.exit(1)

    # ── Step 7: Validate counts ──────────────────────────────────────────────
    print("\n[Step 7] Validating counts...")
    try:
        driver = GraphDatabase.driver(args.neo4j_uri, auth=(args.neo4j_username, args.neo4j_password))

        # Node counts
        recs, _, _ = driver.execute_query(
            "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY label"
        )
        node_counts = {r["label"]: r["count"] for r in recs}
        for label, expected in EXPECTED_NODES.items():
            actual = node_counts.get(label, 0)
            record(f"Node count: {label}", actual == expected,
                   f"expected {expected}, got {actual}")

        # Relationship counts
        recs, _, _ = driver.execute_query(
            "MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count ORDER BY type"
        )
        rel_counts = {r["type"]: r["count"] for r in recs}
        for rel_type, expected in EXPECTED_RELS.items():
            actual = rel_counts.get(rel_type, 0)
            record(f"Rel count: {rel_type}", actual == expected,
                   f"expected {expected}, got {actual}")

        driver.close()
    except Exception as e:
        record("Validate counts", False, str(e))

    _print_summary()
    failed = sum(1 for _, p, _ in results if not p)
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
