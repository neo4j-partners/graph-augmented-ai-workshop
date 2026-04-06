"""
Generate pre-computed embeddings for HTML documents.

This script processes the workshop's HTML files into chunks and generates
vector embeddings using the Databricks foundation model endpoint. The output
is a JSON file that ships with the workshop so students don't need to wait
for embedding generation.

Prerequisites:
    1. Databricks cluster running with access to foundation model endpoints
    2. HTML files uploaded to a Unity Catalog Volume
    3. Neo4j credentials configured (for document type classification)

Usage:
    Run as a Databricks job via submit.sh, or directly on a cluster:

    python generate_embeddings.py \
        --volume-path /Volumes/catalog/schema/volume \
        --output-path /Volumes/catalog/schema/volume/embeddings/document_chunks_embedded.json

    Download the output JSON and commit it to Includes/data/embeddings/.
"""

import argparse
import json
import re
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from bs4 import BeautifulSoup


# =============================================================================
# DOCUMENT TYPES
# =============================================================================

class DocumentType(str, Enum):
    CUSTOMER_PROFILE = "customer_profile"
    COMPANY_ANALYSIS = "company_analysis"
    COMPANY_REPORT = "company_report"
    BANK_PROFILE = "bank_profile"
    BANK_BRANCH = "bank_branch"
    INVESTMENT_GUIDE = "investment_guide"
    MARKET_ANALYSIS = "market_analysis"
    REGULATORY = "regulatory"
    UNKNOWN = "unknown"


def classify_document_type(filename: str) -> DocumentType:
    """Classify document type based on filename patterns."""
    filename_lower = filename.lower()
    if "customer_profile" in filename_lower:
        return DocumentType.CUSTOMER_PROFILE
    if "company_analysis" in filename_lower:
        return DocumentType.COMPANY_ANALYSIS
    if "company_quarterly_report" in filename_lower or "quarterly_report" in filename_lower:
        return DocumentType.COMPANY_REPORT
    if "bank_profile" in filename_lower:
        return DocumentType.BANK_PROFILE
    if "bank_branch" in filename_lower:
        return DocumentType.BANK_BRANCH
    if "investment" in filename_lower and ("guide" in filename_lower or "strategy" in filename_lower):
        return DocumentType.INVESTMENT_GUIDE
    if "market_analysis" in filename_lower:
        return DocumentType.MARKET_ANALYSIS
    if "regulatory" in filename_lower or "compliance" in filename_lower:
        return DocumentType.REGULATORY
    return DocumentType.UNKNOWN


# =============================================================================
# HTML PROCESSING
# =============================================================================

def extract_text_from_html(html_content: str) -> tuple[str, str]:
    """Extract clean text and title from HTML content."""
    soup = BeautifulSoup(html_content, "html.parser")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "Untitled Document"

    for element in soup(["script", "style", "head", "meta", "link"]):
        element.decompose()

    text_parts = []
    for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li"]):
        text = element.get_text(strip=True)
        if text:
            text_parts.append(text)

    extracted_text = "\n\n".join(text_parts)
    extracted_text = re.sub(r"\n{3,}", "\n\n", extracted_text)
    extracted_text = re.sub(r" +", " ", extracted_text)

    return title, extracted_text.strip()


def extract_entity_references(text: str, document_type: DocumentType) -> dict:
    """Extract entity references from document text."""
    references = {"customers": [], "companies": [], "stock_tickers": []}

    ticker_pattern = r"\(([A-Z]{2,5})\)|(?<!\w)([A-Z]{2,5})(?=\s|,|\.|$)"
    ticker_matches = re.findall(ticker_pattern, text)
    for match in ticker_matches:
        ticker = match[0] or match[1]
        if ticker and len(ticker) >= 2:
            references["stock_tickers"].append(ticker)

    company_patterns = [
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Corp|Corporation|Inc|Company|Ltd|LLC|Solutions|Tech|Bank|Trust|Finance|Holdings))",
        r"((?:First|Second|Global|Pacific|National)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
    ]
    for pattern in company_patterns:
        matches = re.findall(pattern, text)
        references["companies"].extend(matches)

    if document_type == DocumentType.CUSTOMER_PROFILE:
        name_pattern = r"(?:Customer\s+)?(?:Profile[:\s]+)?([A-Z][a-z]+\s+[A-Z][a-z]+)"
        name_matches = re.findall(name_pattern, text[:500])
        references["customers"].extend(name_matches[:1])

    for key in references:
        seen = set()
        unique = []
        for item in references[key]:
            if item not in seen:
                seen.add(item)
                unique.append(item)
        references[key] = unique

    return references


# =============================================================================
# CHUNKING
# =============================================================================

def chunk_text(text: str, chunk_size: int = 4000, chunk_overlap: int = 200) -> list[dict]:
    """Split text into overlapping chunks with stable IDs.

    Uses a simple character-based splitter that avoids splitting mid-word.
    This is equivalent to neo4j-graphrag's FixedSizeSplitter but without
    the async dependency, making it suitable for running as a standalone job.
    """
    chunks = []
    start = 0
    index = 0

    while start < len(text):
        end = start + chunk_size

        # Try not to split mid-word
        if end < len(text):
            space_pos = text.rfind(" ", start + chunk_size - 100, end + 100)
            if space_pos > start:
                end = space_pos

        chunk_text_content = text[start:end].strip()
        if chunk_text_content:
            chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "index": index,
                "text": chunk_text_content,
            })
            index += 1

        start = end - chunk_overlap
        if start >= len(text):
            break

    return chunks


# =============================================================================
# EMBEDDING GENERATION
# =============================================================================

def generate_embeddings_databricks(texts: list[str], endpoint: str = "databricks-gte-large-en") -> list[list[float]]:
    """Generate embeddings using the Databricks foundation model endpoint.

    This function runs on a Databricks cluster and uses the workspace client
    for authentication.
    """
    from databricks_langchain import DatabricksEmbeddings

    embedder = DatabricksEmbeddings(endpoint=endpoint)
    embeddings = []

    # Process in batches to avoid rate limits
    batch_size = 16
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_embeddings = embedder.embed_documents(batch)
        embeddings.extend(batch_embeddings)
        if i + batch_size < len(texts):
            print(f"  Embedded {i + batch_size}/{len(texts)} chunks...")

    return embeddings


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Generate pre-computed embeddings for workshop HTML files")
    parser.add_argument("--volume-path", required=True, help="Unity Catalog Volume path containing HTML files")
    parser.add_argument("--output-path", default=None, help="Output path for JSON file (defaults to volume-path/embeddings/document_chunks_embedded.json)")
    parser.add_argument("--endpoint", default="databricks-gte-large-en", help="Databricks embedding model endpoint")
    args = parser.parse_args()

    output_path = args.output_path or f"{args.volume_path}/embeddings/document_chunks_embedded.json"

    print("=" * 70)
    print("EMBEDDING GENERATION - Pre-computing document embeddings")
    print("=" * 70)
    print(f"Volume path:  {args.volume_path}")
    print(f"Output path:  {output_path}")
    print(f"Endpoint:     {args.endpoint}")
    print("")

    # Step 1: List HTML files
    print("[1/4] Listing HTML files...")
    html_path = f"{args.volume_path}/html"

    # Volumes are regular filesystem paths on Databricks clusters
    import os
    html_files = sorted(
        f for f in os.listdir(html_path) if f.endswith(".html")
    )
    print(f"  Found {len(html_files)} HTML files")
    print("")

    # Step 2: Process HTML files into documents and chunks
    print("[2/4] Processing HTML files into documents and chunks...")
    documents = []
    all_chunks = []

    for filename in html_files:
        filepath = f"{html_path}/{filename}"

        # Read file content (volumes are regular filesystem paths on Databricks)
        with open(filepath, "r", encoding="utf-8") as fh:
            content = fh.read()

        title, raw_text = extract_text_from_html(content)
        doc_type = classify_document_type(filename)
        entity_refs = extract_entity_references(raw_text, doc_type)

        doc_id = str(uuid.uuid4())
        doc = {
            "document_id": doc_id,
            "filename": filename,
            "document_type": doc_type.value,
            "title": title,
            "source_path": filepath,
            "char_count": len(raw_text),
            "entity_references": entity_refs,
        }
        documents.append(doc)

        chunks = chunk_text(raw_text)
        for chunk in chunks:
            chunk["document_id"] = doc_id
            chunk["metadata"] = {
                "document_title": title,
                "document_type": doc_type.value,
                "source_path": filepath,
            }
            all_chunks.append(chunk)

        print(f"  {filename}: {len(raw_text)} chars -> {len(chunks)} chunks")

    print(f"\n  Total: {len(documents)} documents, {len(all_chunks)} chunks")
    print("")

    # Step 3: Generate embeddings
    print("[3/4] Generating embeddings...")
    start_time = time.time()

    texts = [chunk["text"] for chunk in all_chunks]
    embeddings = generate_embeddings_databricks(texts, endpoint=args.endpoint)

    for i, chunk in enumerate(all_chunks):
        chunk["embedding"] = embeddings[i]

    elapsed = time.time() - start_time
    dimensions = len(embeddings[0]) if embeddings else 0
    print(f"  Generated {len(embeddings)} embeddings ({dimensions} dimensions) in {elapsed:.1f}s")
    print("")

    # Step 4: Write output JSON
    print("[4/4] Writing output JSON...")

    output = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "embedding_model": args.endpoint,
            "embedding_dimensions": dimensions,
            "chunk_size": 4000,
            "chunk_overlap": 200,
            "document_count": len(documents),
            "chunk_count": len(all_chunks),
        },
        "documents": documents,
        "chunks": all_chunks,
    }

    # Write to volume (volumes are regular filesystem paths on Databricks)
    json_content = json.dumps(output, indent=2)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as fh:
        fh.write(json_content)

    print(f"  Written to: {output_path}")
    print(f"  Size: {len(json_content) / 1024:.1f} KB")
    print("")

    print("=" * 70)
    print("EMBEDDING GENERATION COMPLETE")
    print("=" * 70)
    print(f"  Documents: {len(documents)}")
    print(f"  Chunks:    {len(all_chunks)}")
    print(f"  Model:     {args.endpoint}")
    print(f"  Dims:      {dimensions}")
    print("")
    print("Next steps:")
    print(f"  1. Download {output_path}")
    print("  2. Copy to Includes/data/embeddings/document_chunks_embedded.json")
    print("  3. Commit to the repository")
    print("=" * 70)


if __name__ == "__main__":
    main()
