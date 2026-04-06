# Databricks notebook source
# Workshop Configuration
# This notebook is imported via %run and makes CONFIG available to all lab notebooks.

CONFIG = {
    "course_name": "Graph Augmented AI Workshop",
    # GitHub source for data files (downloaded during setup)
    "github": {
        "repo": "neo4j-partners/graph-enrichment",
        "branch": "main",
        "data_path": "labs/Includes/data",
    },
    # Catalog and Schema
    # The setup notebook creates a catalog named {prefix}_{username} and a schema within it.
    "catalog": {
        "prefix": "neo4j_workshop",
        "schema_name": "raw_data",
        "volume_name": "source_files",
    },
    # Neo4j Secrets
    # The setup notebook stores Neo4j credentials in this Databricks secret scope.
    "secrets": {
        "scope_name": "neo4j-creds",
        "keys": {
            "username": "username",
            "password": "password",
            "url": "url",
            "volume_path": "volume_path",
        },
    },
    # Embedding metadata (must match the pre-computed embeddings JSON)
    "embeddings": {
        "model": "databricks-gte-large-en",
        "dimensions": 1024,
        "chunk_size": 4000,
        "chunk_overlap": 200,
    },
    # Neo4j Spark Connector
    "spark_connector": {
        "maven_coordinates": "org.neo4j:neo4j-connector-apache-spark_2.12:5.3.1_for_spark_3",
    },
}
