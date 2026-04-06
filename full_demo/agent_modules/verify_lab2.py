"""Lab 2 Read-Only Verification: Check Neo4j data without modification.

Runs Cypher queries to verify node counts, relationship counts, and
constraint existence. Does not modify any data.

Usage:
    python -m cli upload verify_lab2.py && python -m cli submit verify_lab2.py
"""

import os
import sys
import time

# Parse KEY=VALUE parameters from cli.submit into environment variables.
for _arg in sys.argv[1:]:
    if "=" in _arg and not _arg.startswith("-"):
        _key, _, _value = _arg.partition("=")
        os.environ.setdefault(_key, _value)


EXPECTED_NODES = {
    "Customer": 102, "Bank": 102, "Account": 123,
    "Company": 102, "Stock": 102, "Position": 110, "Transaction": 123,
}
EXPECTED_RELS = {
    "HAS_ACCOUNT": 123, "AT_BANK": 123, "OF_COMPANY": 102,
    "PERFORMS": 123, "BENEFITS_TO": 123, "HAS_POSITION": 110, "OF_SECURITY": 110,
}
EXPECTED_CONSTRAINTS = [
    "customer_id_unique", "bank_id_unique", "account_id_unique",
    "company_id_unique", "stock_id_unique", "position_id_unique",
    "transaction_id_unique",
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

    from neo4j import GraphDatabase

    print("=" * 60)
    print("Lab 2 Verification: Read-Only Data Check")
    print("=" * 60)
    print(f"Neo4j URI: {neo4j_uri}")
    print()

    # ── Connect ──────────────────────────────────────────────────────────────
    try:
        t0 = time.time()
        driver = GraphDatabase.driver(
            neo4j_uri, auth=(neo4j_username, neo4j_password)
        )
        driver.verify_connectivity()
        record("Neo4j connectivity", True, f"connected in {time.time() - t0:.2f}s")
    except Exception as e:
        record("Neo4j connectivity", False, str(e))
        _print_summary()
        sys.exit(1)

    # ── Node counts ──────────────────────────────────────────────────────────
    print("\nChecking node counts...")
    try:
        recs, _, _ = driver.execute_query(
            "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY label"
        )
        node_counts = {r["label"]: r["count"] for r in recs}
        for label, expected in EXPECTED_NODES.items():
            actual = node_counts.get(label, 0)
            record(f"Node: {label}", actual == expected,
                   f"expected {expected}, got {actual}")
    except Exception as e:
        record("Node counts query", False, str(e))

    # ── Relationship counts ──────────────────────────────────────────────────
    print("\nChecking relationship counts...")
    try:
        recs, _, _ = driver.execute_query(
            "MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count ORDER BY type"
        )
        rel_counts = {r["type"]: r["count"] for r in recs}
        for rel_type, expected in EXPECTED_RELS.items():
            actual = rel_counts.get(rel_type, 0)
            record(f"Rel: {rel_type}", actual == expected,
                   f"expected {expected}, got {actual}")
    except Exception as e:
        record("Relationship counts query", False, str(e))

    # ── Constraints ──────────────────────────────────────────────────────────
    print("\nChecking constraints...")
    try:
        recs, _, _ = driver.execute_query("SHOW CONSTRAINTS")
        constraint_names = {r["name"] for r in recs}
        for name in EXPECTED_CONSTRAINTS:
            record(f"Constraint: {name}", name in constraint_names)
    except Exception as e:
        record("Constraints query", False, str(e))

    # ── Sample queries ───────────────────────────────────────────────────────
    print("\nRunning sample queries...")

    # Portfolio value query
    try:
        recs, _, _ = driver.execute_query(
            "MATCH (c:Customer)-[:HAS_ACCOUNT]->(a:Account)-[:HAS_POSITION]->(p:Position) "
            "RETURN count(DISTINCT c) AS customers_with_positions"
        )
        count = recs[0]["customers_with_positions"]
        record("Customers with positions", count > 0, f"{count} customers")
    except Exception as e:
        record("Customers with positions", False, str(e))

    # Transaction flow query
    try:
        recs, _, _ = driver.execute_query(
            "MATCH (a:Account)-[:PERFORMS]->(t:Transaction)-[:BENEFITS_TO]->(b:Account) "
            "RETURN count(t) AS transaction_count"
        )
        count = recs[0]["transaction_count"]
        record("Transaction flow", count > 0, f"{count} transactions with flow")
    except Exception as e:
        record("Transaction flow", False, str(e))

    driver.close()

    _print_summary()
    failed = sum(1 for _, p, _ in results if not p)
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
