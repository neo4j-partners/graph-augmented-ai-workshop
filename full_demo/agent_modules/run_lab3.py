"""Lab 3 Validation: Load pre-computed embeddings and verify hybrid search.

Destructive for document nodes — clears existing Document/Chunk nodes before
loading. Reads the pre-computed embeddings JSON from the Unity Catalog Volume,
writes Document and Chunk nodes to Neo4j, creates vector and fulltext indexes,
and verifies search functionality.

Usage:
    python -m cli upload run_lab3.py && python -m cli submit run_lab3.py
"""

import argparse
import json
import sys
import time


# ── Configuration ────────────────────────────────────────────────────────────

VECTOR_INDEX_NAME = "chunk_embedding_index"
FULLTEXT_INDEX_NAME = "chunk_text_index"
EMBEDDINGS_FILE = "embeddings/document_chunks_embedded.json"

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


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Lab 3: Load Pre-computed Embeddings")
    parser.add_argument("--neo4j-uri", required=True)
    parser.add_argument("--neo4j-username", default="neo4j")
    parser.add_argument("--neo4j-password", required=True)
    parser.add_argument("--volume-path", required=True)
    args = parser.parse_args()

    from neo4j import GraphDatabase

    embeddings_path = f"{args.volume_path}/{EMBEDDINGS_FILE}"

    print("=" * 60)
    print("Lab 3 Validation: Pre-computed Embeddings and Hybrid Search")
    print("=" * 60)
    print(f"Neo4j URI:    {args.neo4j_uri}")
    print(f"Volume path:  {args.volume_path}")
    print(f"Embeddings:   {embeddings_path}")
    print()

    driver = GraphDatabase.driver(
        args.neo4j_uri, auth=(args.neo4j_username, args.neo4j_password)
    )

    # ── Step 1: Clear existing document nodes ────────────────────────────────
    print("[Step 1] Clearing existing Document/Chunk nodes...")
    try:
        for idx_name in [VECTOR_INDEX_NAME, FULLTEXT_INDEX_NAME]:
            try:
                driver.execute_query(f"DROP INDEX {idx_name} IF EXISTS")
            except Exception:
                pass

        recs, _, _ = driver.execute_query(
            "MATCH (n) WHERE n:Document OR n:Chunk "
            "DETACH DELETE n RETURN count(n) AS deleted"
        )
        deleted = recs[0]["deleted"]
        record("Clear document nodes", True, f"deleted {deleted} nodes")
    except Exception as e:
        record("Clear document nodes", False, str(e))

    # ── Step 2: Load pre-computed embeddings JSON ────────────────────────────
    print("\n[Step 2] Loading pre-computed embeddings...")
    try:
        with open(embeddings_path, "r") as f:
            data = json.load(f)

        metadata = data["metadata"]
        documents = data["documents"]
        chunks = data["chunks"]

        embedding_model = metadata["embedding_model"]
        embedding_dims = metadata["embedding_dimensions"]

        # Validate all chunks have embeddings of the right dimension
        dims_ok = all(len(c["embedding"]) == embedding_dims for c in chunks)

        record("Load embeddings JSON", dims_ok,
               f"{len(documents)} docs, {len(chunks)} chunks, "
               f"{embedding_model} ({embedding_dims} dims)")
        if not dims_ok:
            _print_summary()
            sys.exit(1)
    except Exception as e:
        record("Load embeddings JSON", False, str(e))
        _print_summary()
        sys.exit(1)

    # ── Step 3: Write Document and Chunk nodes to Neo4j ──────────────────────
    print("\n[Step 3] Writing to Neo4j...")
    try:
        # Write Document nodes
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
        recs, _, _ = driver.execute_query(doc_query, parameters_={"documents": documents})
        doc_count = recs[0]["count"]
        print(f"    {doc_count} Document nodes written")

        # Write Chunk nodes with embeddings (in batches)
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
        total_chunks = 0
        batch_size = 25
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            recs, _, _ = driver.execute_query(chunk_query, parameters_={"chunks": batch})
            total_chunks += recs[0]["count"]
        print(f"    {total_chunks} Chunk nodes written")

        # Create FROM_DOCUMENT relationships
        recs, _, _ = driver.execute_query(
            "MATCH (c:Chunk) WHERE c.document_id IS NOT NULL "
            "MATCH (d:Document {document_id: c.document_id}) "
            "MERGE (c)-[r:FROM_DOCUMENT]->(d) "
            "RETURN count(r) AS count"
        )
        fd_count = recs[0]["count"]
        print(f"    {fd_count} FROM_DOCUMENT relationships")

        # Create NEXT_CHUNK relationships
        recs, _, _ = driver.execute_query(
            "MATCH (c1:Chunk) WHERE c1.document_id IS NOT NULL AND c1.index IS NOT NULL "
            "WITH c1 "
            "MATCH (c2:Chunk) "
            "WHERE c2.document_id = c1.document_id AND c2.index = c1.index + 1 "
            "MERGE (c1)-[r:NEXT_CHUNK]->(c2) "
            "RETURN count(r) AS count"
        )
        nc_count = recs[0]["count"]
        print(f"    {nc_count} NEXT_CHUNK relationships")

        # Create DESCRIBES relationships (customer profiles -> Customer nodes)
        recs, _, _ = driver.execute_query(
            "MATCH (d:Document) "
            "WHERE d.document_type = 'customer_profile' "
            "WITH d, "
            "     replace(replace(d.title, 'Customer Profile - ', ''), 'Customer Profile: ', '') AS customer_name "
            "MATCH (c:Customer) "
            "WHERE c.first_name + ' ' + c.last_name = customer_name "
            "MERGE (d)-[r:DESCRIBES]->(c) "
            "RETURN count(r) AS count"
        )
        desc_count = recs[0]["count"]
        print(f"    {desc_count} DESCRIBES relationships")

        record("Write to Neo4j", True,
               f"{doc_count} docs, {total_chunks} chunks, "
               f"{fd_count} FROM_DOCUMENT, {nc_count} NEXT_CHUNK, {desc_count} DESCRIBES")
    except Exception as e:
        record("Write to Neo4j", False, str(e))
        _print_summary()
        sys.exit(1)

    # ── Step 4: Create indexes ───────────────────────────────────────────────
    print("\n[Step 4] Creating indexes...")
    try:
        driver.execute_query(
            f"CREATE VECTOR INDEX {VECTOR_INDEX_NAME} IF NOT EXISTS "
            f"FOR (c:Chunk) ON (c.embedding) "
            f"OPTIONS {{indexConfig: {{`vector.dimensions`: {embedding_dims}, "
            f"`vector.similarity_function`: 'cosine'}}}}"
        )
        print(f"    Vector index: {VECTOR_INDEX_NAME}")

        driver.execute_query(
            f"CREATE FULLTEXT INDEX {FULLTEXT_INDEX_NAME} IF NOT EXISTS "
            f"FOR (c:Chunk) ON EACH [c.text]"
        )
        print(f"    Fulltext index: {FULLTEXT_INDEX_NAME}")

        # Wait for indexes to come online
        print("    Waiting for indexes to come ONLINE...")
        for attempt in range(30):
            recs, _, _ = driver.execute_query(
                "SHOW INDEXES YIELD name, state "
                "WHERE name IN [$v, $f] "
                "RETURN name, state",
                v=VECTOR_INDEX_NAME, f=FULLTEXT_INDEX_NAME,
            )
            states = {r["name"]: r["state"] for r in recs}
            if all(s == "ONLINE" for s in states.values()):
                break
            time.sleep(10)
        else:
            record("Create indexes", False, f"timed out — states: {states}")
            _print_summary()
            sys.exit(1)

        record("Create indexes", True, "both ONLINE")
    except Exception as e:
        record("Create indexes", False, str(e))
        _print_summary()
        sys.exit(1)

    # ── Step 5: Verify counts ────────────────────────────────────────────────
    print("\n[Step 5] Verifying counts...")
    try:
        recs, _, _ = driver.execute_query(
            "MATCH (d:Document) RETURN count(d) AS count"
        )
        doc_count_verify = recs[0]["count"]
        record("Document count", doc_count_verify == len(documents),
               f"expected {len(documents)}, got {doc_count_verify}")
    except Exception as e:
        record("Document count", False, str(e))

    try:
        recs, _, _ = driver.execute_query(
            "MATCH (c:Chunk) RETURN count(c) AS count"
        )
        chunk_count_verify = recs[0]["count"]
        record("Chunk count", chunk_count_verify == len(chunks),
               f"expected {len(chunks)}, got {chunk_count_verify}")
    except Exception as e:
        record("Chunk count", False, str(e))

    try:
        recs, _, _ = driver.execute_query(
            "MATCH (c:Chunk)-[:FROM_DOCUMENT]->(d:Document) RETURN count(c) AS count"
        )
        rel_count = recs[0]["count"]
        record("FROM_DOCUMENT rels", rel_count == len(chunks),
               f"expected {len(chunks)}, got {rel_count}")
    except Exception as e:
        record("FROM_DOCUMENT rels", False, str(e))

    # ── Step 6: Test vector search ───────────────────────────────────────────
    print("\n[Step 6] Testing search...")
    try:
        # Use the first chunk's embedding as a query vector
        query_embedding = chunks[0]["embedding"]

        recs, _, _ = driver.execute_query(
            f"CALL db.index.vector.queryNodes('{VECTOR_INDEX_NAME}', 3, $embedding) "
            "YIELD node, score "
            "RETURN node.chunk_id AS chunk_id, score",
            embedding=query_embedding,
        )
        record("Vector search", len(recs) > 0, f"{len(recs)} results returned")
    except Exception as e:
        record("Vector search", False, str(e))

    # Fulltext search
    try:
        recs, _, _ = driver.execute_query(
            f"CALL db.index.fulltext.queryNodes('{FULLTEXT_INDEX_NAME}', 'renewable energy') "
            "YIELD node, score "
            "RETURN node.chunk_id AS chunk_id, score "
            "LIMIT 3"
        )
        record("Fulltext search", len(recs) > 0, f"{len(recs)} results returned")
    except Exception as e:
        record("Fulltext search", False, str(e))

    driver.close()

    _print_summary()
    failed = sum(1 for _, p, _ in results if not p)
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
