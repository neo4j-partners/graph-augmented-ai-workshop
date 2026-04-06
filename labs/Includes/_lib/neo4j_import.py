"""
Neo4j import module for the Graph Augmented AI Workshop.

This module handles loading all data into Neo4j in a single step:
- Structured CSV data (7 node types, 7 relationship types) via Spark Connector
- Pre-computed document graph (Document and Chunk nodes with embeddings) via Neo4j Python driver

Called by the "1 - Neo4j Import" notebook.
"""

import json
import time

import yaml
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType


# =============================================================================
# CONFIGURATION
# =============================================================================

def _load_scope_name() -> str:
    """Read the secret scope name from Includes/config.yaml."""
    notebook_path = (
        dbutils.entry_point.getDbutils()  # noqa: F821
        .notebook().getContext().notebookPath().get()
    )
    workspace_base = "/Workspace" + notebook_path.rsplit("/", 1)[0]
    config_path = f"{workspace_base}/Includes/config.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config["secrets"]["scope_name"]


def load_neo4j_config():
    """Load Neo4j configuration from Databricks Secrets."""
    print("=" * 70)
    print("CONFIGURATION")
    print("=" * 70)

    scope = _load_scope_name()
    config = {
        "neo4j_url": dbutils.secrets.get(scope=scope, key="url"),  # noqa: F821
        "neo4j_user": dbutils.secrets.get(scope=scope, key="username"),  # noqa: F821
        "neo4j_pass": dbutils.secrets.get(scope=scope, key="password"),  # noqa: F821
        "volume_path": dbutils.secrets.get(scope=scope, key="volume_path"),  # noqa: F821
        "neo4j_database": "neo4j",
    }

    # Configure Spark session for Neo4j connector
    spark.conf.set("neo4j.url", config["neo4j_url"])  # noqa: F821
    spark.conf.set("neo4j.authentication.basic.username", config["neo4j_user"])  # noqa: F821
    spark.conf.set("neo4j.authentication.basic.password", config["neo4j_pass"])  # noqa: F821
    spark.conf.set("neo4j.database", config["neo4j_database"])  # noqa: F821

    print(f"  Neo4j URL:    {config['neo4j_url']}")
    print(f"  Volume Path:  {config['volume_path']}")
    print("  [OK] Configuration loaded")
    return config


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def write_nodes(df: DataFrame, label: str, node_key: str) -> dict:
    """Write DataFrame rows as nodes to Neo4j via Spark Connector."""
    count = df.count()
    start_time = time.time()
    (
        df.write.format("org.neo4j.spark.DataSource")
        .mode("Append")
        .option("labels", f":{label}")
        .option("node.keys", node_key)
        .save()
    )
    elapsed = time.time() - start_time
    print(f"  [OK] {count} {label} nodes ({elapsed:.1f}s)")
    return {"count": count, "elapsed": elapsed}


def write_relationship(df: DataFrame, rel_type: str, source_label: str, source_key: str, target_label: str, target_key: str) -> dict:
    """Write DataFrame rows as relationships to Neo4j via Spark Connector."""
    count = df.count()
    start_time = time.time()
    (
        df.write.format("org.neo4j.spark.DataSource")
        .mode("Append")
        .option("relationship", rel_type)
        .option("relationship.save.strategy", "keys")
        .option("relationship.source.save.mode", "Match")
        .option("relationship.source.labels", f":{source_label}")
        .option("relationship.source.node.keys", f"{source_key}:{source_key}")
        .option("relationship.target.save.mode", "Match")
        .option("relationship.target.labels", f":{target_label}")
        .option("relationship.target.node.keys", f"{target_key}:{target_key}")
        .save()
    )
    elapsed = time.time() - start_time
    print(f"  [OK] {count} {rel_type} ({elapsed:.1f}s)")
    return {"count": count, "elapsed": elapsed}


def run_cypher(config: dict, query: str) -> DataFrame:
    """Execute a Cypher query via the Spark Connector and return results."""
    return (
        spark.read.format("org.neo4j.spark.DataSource")  # noqa: F821
        .option("url", config["neo4j_url"])
        .option("authentication.basic.username", config["neo4j_user"])
        .option("authentication.basic.password", config["neo4j_pass"])
        .option("database", config["neo4j_database"])
        .option("query", query)
        .load()
    )


# =============================================================================
# CLEAR DATABASE
# =============================================================================

def clear_database(config: dict) -> bool:
    """Clear all nodes and relationships from Neo4j."""
    from neo4j import GraphDatabase

    print("\n" + "=" * 70)
    print("CLEARING DATABASE")
    print("=" * 70)

    driver = GraphDatabase.driver(config["neo4j_url"], auth=(config["neo4j_user"], config["neo4j_pass"]))
    with driver.session(database=config["neo4j_database"]) as session:
        result = session.run("MATCH (n) DETACH DELETE n")
        summary = result.consume()
        print(f"  Deleted {summary.counters.nodes_deleted} nodes, {summary.counters.relationships_deleted} relationships")
    driver.close()
    return True


# =============================================================================
# CONSTRAINTS
# =============================================================================

def create_constraints(config: dict):
    """Create uniqueness constraints in Neo4j."""
    from neo4j import GraphDatabase

    print("\n" + "=" * 70)
    print("CREATING CONSTRAINTS")
    print("=" * 70)

    constraints = [
        ("customer_id_unique", "Customer", "customer_id"),
        ("bank_id_unique", "Bank", "bank_id"),
        ("account_id_unique", "Account", "account_id"),
        ("company_id_unique", "Company", "company_id"),
        ("stock_id_unique", "Stock", "stock_id"),
        ("position_id_unique", "Position", "position_id"),
        ("transaction_id_unique", "Transaction", "transaction_id"),
        ("document_id_unique", "Document", "document_id"),
        ("chunk_id_unique", "Chunk", "chunk_id"),
    ]

    driver = GraphDatabase.driver(config["neo4j_url"], auth=(config["neo4j_user"], config["neo4j_pass"]))
    with driver.session(database=config["neo4j_database"]) as session:
        for name, label, prop in constraints:
            query = f"CREATE CONSTRAINT {name} IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
            try:
                session.run(query)
                print(f"  [OK] {name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  [OK] {name} (exists)")
                else:
                    print(f"  [FAIL] {name}: {e}")
    driver.close()


# =============================================================================
# CSV DATA LOADING
# =============================================================================

def load_and_transform_csv(config: dict) -> dict:
    """Load CSV files from volume and apply type transformations."""
    print("\n" + "=" * 70)
    print("LOADING CSV DATA")
    print("=" * 70)

    csv_path = f"{config['volume_path']}/csv"
    data = {}

    files = [
        ("customers", "customers.csv"),
        ("banks", "banks.csv"),
        ("accounts", "accounts.csv"),
        ("companies", "companies.csv"),
        ("stocks", "stocks.csv"),
        ("positions", "portfolio_holdings.csv"),
        ("transactions", "transactions.csv"),
    ]

    for key, filename in files:
        path = f"{csv_path}/{filename}"
        df = spark.read.option("header", "true").csv(path)  # noqa: F821
        print(f"  [OK] {filename}: {df.count()} rows")
        data[key] = df

    # Apply type transformations
    print("\n  Applying type transformations...")

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

    print("  [OK] All transformations applied")
    return data


def write_all_nodes(data: dict) -> dict:
    """Write all 7 node types to Neo4j."""
    print("\n" + "=" * 70)
    print("WRITING NODES")
    print("=" * 70)

    results = {}
    results["Customer"] = write_nodes(data["customers"], "Customer", "customer_id")
    results["Bank"] = write_nodes(data["banks"], "Bank", "bank_id")

    account_props = data["accounts"].select(
        "account_id", "account_number", "account_type",
        "balance", "currency", "opened_date", "status", "interest_rate"
    )
    results["Account"] = write_nodes(account_props, "Account", "account_id")
    results["Company"] = write_nodes(data["companies"], "Company", "company_id")

    stock_props = data["stocks"].select(
        "stock_id", "ticker", "current_price", "previous_close", "opening_price",
        "day_high", "day_low", "volume", "market_cap_billions", "pe_ratio",
        "dividend_yield", "fifty_two_week_high", "fifty_two_week_low", "exchange"
    )
    results["Stock"] = write_nodes(stock_props, "Stock", "stock_id")

    position_props = data["positions"].select(
        "position_id", "shares", "purchase_price", "purchase_date",
        "current_value", "percentage_of_portfolio"
    )
    results["Position"] = write_nodes(position_props, "Position", "position_id")

    transaction_props = data["transactions"].select(
        "transaction_id", "amount", "currency", "transaction_date",
        "transaction_time", "type", "status", "description"
    )
    results["Transaction"] = write_nodes(transaction_props, "Transaction", "transaction_id")

    total = sum(r["count"] for r in results.values())
    print(f"\n  Total: {total} nodes written")
    return results


def write_all_relationships(data: dict) -> dict:
    """Write all 7 relationship types to Neo4j."""
    print("\n" + "=" * 70)
    print("WRITING RELATIONSHIPS")
    print("=" * 70)

    results = {}

    has_account_df = data["accounts"].select("customer_id", "account_id")
    results["HAS_ACCOUNT"] = write_relationship(has_account_df, "HAS_ACCOUNT", "Customer", "customer_id", "Account", "account_id")

    at_bank_df = data["accounts"].select("account_id", "bank_id")
    results["AT_BANK"] = write_relationship(at_bank_df, "AT_BANK", "Account", "account_id", "Bank", "bank_id")

    of_company_df = data["stocks"].select("stock_id", "company_id")
    results["OF_COMPANY"] = write_relationship(of_company_df, "OF_COMPANY", "Stock", "stock_id", "Company", "company_id")

    performs_df = data["transactions"].select(F.col("from_account_id").alias("account_id"), "transaction_id")
    results["PERFORMS"] = write_relationship(performs_df, "PERFORMS", "Account", "account_id", "Transaction", "transaction_id")

    benefits_df = data["transactions"].select("transaction_id", F.col("to_account_id").alias("account_id"))
    results["BENEFITS_TO"] = write_relationship(benefits_df, "BENEFITS_TO", "Transaction", "transaction_id", "Account", "account_id")

    has_position_df = data["positions"].select("account_id", "position_id")
    results["HAS_POSITION"] = write_relationship(has_position_df, "HAS_POSITION", "Account", "account_id", "Position", "position_id")

    of_security_df = data["positions"].select("position_id", "stock_id")
    results["OF_SECURITY"] = write_relationship(of_security_df, "OF_SECURITY", "Position", "position_id", "Stock", "stock_id")

    total = sum(r["count"] for r in results.values())
    print(f"\n  Total: {total} relationships written")
    return results


# =============================================================================
# DOCUMENT GRAPH (PRE-COMPUTED EMBEDDINGS)
# =============================================================================

def load_and_write_document_graph(config: dict) -> dict:
    """Load pre-computed embeddings JSON and write Document/Chunk nodes to Neo4j.

    This creates:
    - Document nodes with metadata
    - Chunk nodes with text and embedding vectors
    - FROM_DOCUMENT relationships (Chunk -> Document)
    - NEXT_CHUNK relationships (Chunk -> Chunk)
    - DESCRIBES relationships (Document -> Customer)
    - Vector and full-text indexes on Chunk nodes
    """
    from neo4j import GraphDatabase

    print("\n" + "=" * 70)
    print("LOADING DOCUMENT GRAPH (Pre-computed Embeddings)")
    print("=" * 70)

    # Read the pre-computed embeddings JSON
    # Volumes are mounted as regular filesystem paths in Databricks
    embeddings_path = f"{config['volume_path']}/embeddings/document_chunks_embedded.json"
    print(f"\n  Reading: {embeddings_path}")

    with open(embeddings_path, "r") as f:
        data = json.load(f)

    metadata = data["metadata"]
    documents = data["documents"]
    chunks = data["chunks"]

    print(f"  Model:      {metadata['embedding_model']}")
    print(f"  Dimensions: {metadata['embedding_dimensions']}")
    print(f"  Documents:  {len(documents)}")
    print(f"  Chunks:     {len(chunks)}")

    driver = GraphDatabase.driver(config["neo4j_url"], auth=(config["neo4j_user"], config["neo4j_pass"]))

    # Write Document nodes
    print("\n  Writing Document nodes...")
    with driver.session(database=config["neo4j_database"]) as session:
        doc_query = """
        UNWIND $documents AS doc
        MERGE (d:Document {document_id: doc.document_id})
        SET d.filename = doc.filename,
            d.document_type = doc.document_type,
            d.title = doc.title,
            d.source_path = doc.source_path,
            d.char_count = doc.char_count
        RETURN count(d) AS count
        """
        result = session.run(doc_query, {"documents": documents})
        doc_count = result.single()["count"]
        print(f"  [OK] {doc_count} Document nodes")

    # Write Chunk nodes with embeddings (in batches)
    print("\n  Writing Chunk nodes with embeddings...")
    batch_size = 25
    total_chunks = 0
    with driver.session(database=config["neo4j_database"]) as session:
        chunk_query = """
        UNWIND $chunks AS chunk
        MERGE (c:Chunk {chunk_id: chunk.chunk_id})
        SET c.text = chunk.text,
            c.document_id = chunk.document_id,
            c.`index` = chunk.index,
            c.document_title = chunk.metadata.document_title,
            c.document_type = chunk.metadata.document_type,
            c.embedding = chunk.embedding
        RETURN count(c) AS count
        """
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            result = session.run(chunk_query, {"chunks": batch})
            total_chunks += result.single()["count"]

    print(f"  [OK] {total_chunks} Chunk nodes (with embeddings)")

    # Create relationships
    print("\n  Creating relationships...")
    with driver.session(database=config["neo4j_database"]) as session:
        # FROM_DOCUMENT
        result = session.run("""
            MATCH (c:Chunk) WHERE c.document_id IS NOT NULL
            MATCH (d:Document {document_id: c.document_id})
            MERGE (c)-[r:FROM_DOCUMENT]->(d)
            RETURN count(r) AS count
        """)
        fd_count = result.single()["count"]
        print(f"  [OK] {fd_count} FROM_DOCUMENT relationships")

        # NEXT_CHUNK
        result = session.run("""
            MATCH (c1:Chunk) WHERE c1.document_id IS NOT NULL AND c1.index IS NOT NULL
            WITH c1
            MATCH (c2:Chunk)
            WHERE c2.document_id = c1.document_id AND c2.index = c1.index + 1
            MERGE (c1)-[r:NEXT_CHUNK]->(c2)
            RETURN count(r) AS count
        """)
        nc_count = result.single()["count"]
        print(f"  [OK] {nc_count} NEXT_CHUNK relationships")

        # DESCRIBES (customer profiles -> Customer nodes)
        result = session.run("""
            MATCH (d:Document)
            WHERE d.document_type = 'customer_profile'
            WITH d,
                 replace(replace(d.title, 'Customer Profile - ', ''), 'Customer Profile: ', '') AS customer_name
            MATCH (c:Customer)
            WHERE c.first_name + ' ' + c.last_name = customer_name
            MERGE (d)-[r:DESCRIBES]->(c)
            RETURN count(r) AS count
        """)
        desc_count = result.single()["count"]
        print(f"  [OK] {desc_count} DESCRIBES relationships")

    # Create indexes
    print("\n  Creating indexes...")
    dimensions = metadata["embedding_dimensions"]
    with driver.session(database=config["neo4j_database"]) as session:
        # Vector index
        try:
            session.run(f"""
                CREATE VECTOR INDEX chunk_embedding_index IF NOT EXISTS
                FOR (c:Chunk) ON (c.embedding)
                OPTIONS {{indexConfig: {{
                    `vector.dimensions`: {dimensions},
                    `vector.similarity_function`: 'cosine'
                }}}}
            """)
            print(f"  [OK] Vector index (cosine, {dimensions} dims)")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"  [OK] Vector index (exists)")
            else:
                print(f"  [WARN] Vector index: {e}")

        # Full-text index
        try:
            session.run("""
                CREATE FULLTEXT INDEX chunk_text_index IF NOT EXISTS
                FOR (c:Chunk) ON EACH [c.text]
            """)
            print("  [OK] Full-text index")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("  [OK] Full-text index (exists)")
            else:
                print(f"  [WARN] Full-text index: {e}")

    driver.close()

    return {
        "documents": doc_count,
        "chunks": total_chunks,
        "from_document": fd_count,
        "next_chunk": nc_count,
        "describes": desc_count,
    }


# =============================================================================
# VALIDATION
# =============================================================================

def validate_import(config: dict) -> bool:
    """Validate the import by checking node and relationship counts."""
    print("\n" + "=" * 70)
    print("VALIDATION")
    print("=" * 70)

    node_query = """
    MATCH (n)
    RETURN labels(n)[0] AS label, count(n) AS count
    ORDER BY label
    """
    rel_query = """
    MATCH ()-[r]->()
    RETURN type(r) AS type, count(r) AS count
    ORDER BY type
    """

    print("\n  Node counts:")
    node_counts = run_cypher(config, node_query).collect()
    for row in node_counts:
        print(f"    {row['label']:<15} {row['count']:>6}")

    print("\n  Relationship counts:")
    rel_counts = run_cypher(config, rel_query).collect()
    for row in rel_counts:
        print(f"    {row['type']:<20} {row['count']:>6}")

    total_nodes = sum(row["count"] for row in node_counts)
    total_rels = sum(row["count"] for row in rel_counts)
    print(f"\n  Total: {total_nodes} nodes, {total_rels} relationships")

    return True


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

def run_full_import() -> bool:
    """Run the complete Neo4j import pipeline."""
    total_start = time.time()

    # Load config
    config = load_neo4j_config()

    # Verify connection
    print("\n  Verifying Neo4j connection...")
    test_df = run_cypher(config, "RETURN 'Connected' AS status")
    test_df.collect()
    print("  [OK] Connected to Neo4j")

    # Clear database
    clear_database(config)

    # Create constraints
    create_constraints(config)

    # Load and write CSV data
    data = load_and_transform_csv(config)
    write_all_nodes(data)
    write_all_relationships(data)

    # Load and write document graph
    load_and_write_document_graph(config)

    # Validate
    validate_import(config)

    total_elapsed = time.time() - total_start
    print("\n" + "=" * 70)
    print(f"IMPORT COMPLETE ({total_elapsed:.1f}s)")
    print("=" * 70)
    print("\n  Proceed to Lab 4 (Export to Lakehouse) or explore the graph in Neo4j Browser.")

    return True
