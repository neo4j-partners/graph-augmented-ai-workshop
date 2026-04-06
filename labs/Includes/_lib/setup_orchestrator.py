"""
Setup orchestrator for the Graph Augmented AI Workshop.

This module handles all environment preparation:
- Catalog, schema, and volume creation
- Data file download from GitHub to the volume
- Neo4j secret scope creation and validation
- Neo4j connectivity verification

Called by the "0 - Required Setup" notebook via %run.
"""

import io
import os
import tarfile
import urllib.request


def get_username() -> str:
    """Get the current Databricks username."""
    return spark.sql("SELECT current_user()").first()[0]  # noqa: F821


def derive_catalog_name(prefix: str, username: str) -> str:
    """Derive a catalog name from prefix and username.

    Sanitizes the username to be a valid catalog identifier:
    - Takes the part before @ in the email
    - Replaces dots and hyphens with underscores
    """
    user_part = username.split("@")[0]
    user_part = user_part.replace(".", "_").replace("-", "_")
    return f"{prefix}_{user_part}"


def setup_catalog_and_schema(catalog_name: str, schema_name: str, volume_name: str) -> dict:
    """Create catalog, schema, and volume if they don't exist.

    Returns dict with catalog, schema, volume names and the full volume path.
    """
    print("=" * 70)
    print("STEP 1: Creating Catalog, Schema, and Volume")
    print("=" * 70)

    # Create catalog
    print(f"\n  Creating catalog: {catalog_name}")
    try:
        spark.sql(f"CREATE CATALOG IF NOT EXISTS `{catalog_name}`")  # noqa: F821
        print(f"  [OK] Catalog '{catalog_name}' ready")
    except Exception as e:
        print(f"  [FAIL] Could not create catalog: {e}")
        print("  You may need CREATE CATALOG permission. Ask your workspace admin.")
        raise

    # Use the catalog
    spark.sql(f"USE CATALOG `{catalog_name}`")  # noqa: F821

    # Create schema
    print(f"\n  Creating schema: {schema_name}")
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{schema_name}`")  # noqa: F821
    print(f"  [OK] Schema '{schema_name}' ready")

    # Use the schema
    spark.sql(f"USE SCHEMA `{schema_name}`")  # noqa: F821

    # Create volume
    print(f"\n  Creating volume: {volume_name}")
    spark.sql(f"CREATE VOLUME IF NOT EXISTS `{volume_name}`")  # noqa: F821
    print(f"  [OK] Volume '{volume_name}' ready")

    volume_path = f"/Volumes/{catalog_name}/{schema_name}/{volume_name}"
    print(f"\n  Volume path: {volume_path}")

    return {
        "catalog": catalog_name,
        "schema": schema_name,
        "volume": volume_name,
        "volume_path": volume_path,
    }


def download_data_files(volume_path: str, github_repo: str, github_branch: str = "main", data_path: str = "labs/Includes/data") -> dict:
    """Download data files from GitHub and write them to the volume.

    Downloads the repository tarball from GitHub and extracts only the data
    files (CSV, HTML, embeddings) directly into the target volume. This
    eliminates the need for participants to upload data files to the workspace.

    Args:
        volume_path: Target Unity Catalog volume path (e.g. /Volumes/catalog/schema/vol).
        github_repo: GitHub repo in "owner/repo" format.
        github_branch: Branch to download from.
        data_path: Path within the repo to the data directory.

    Returns:
        Dict with counts of files downloaded per category.
    """
    print("\n" + "=" * 70)
    print("STEP 2: Downloading Data Files from GitHub")
    print("=" * 70)

    url = f"https://github.com/{github_repo}/archive/refs/heads/{github_branch}.tar.gz"
    print(f"\n  Downloading from: {github_repo} ({github_branch} branch)")

    response = urllib.request.urlopen(url)
    tarball = io.BytesIO(response.read())
    print("  [OK] Repository archive downloaded")

    counts = {"csv": 0, "html": 0, "embeddings": 0}

    # Tarball root directory is {repo_name}-{branch}/
    repo_name = github_repo.split("/")[-1]
    data_prefix = f"{repo_name}-{github_branch}/{data_path}/"

    subdirs = {
        "csv": ".csv",
        "html": ".html",
        "embeddings": ".json",
    }

    with tarfile.open(fileobj=tarball, mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.name.startswith(data_prefix) or member.isdir():
                continue

            relative = member.name[len(data_prefix):]
            parts = relative.split("/")
            if len(parts) != 2:
                continue

            subdir, filename = parts
            if subdir not in subdirs or not filename.endswith(subdirs[subdir]):
                continue

            target_dir = os.path.join(volume_path, subdir)
            os.makedirs(target_dir, exist_ok=True)

            f = tar.extractfile(member)
            if f:
                target_path = os.path.join(target_dir, filename)
                with open(target_path, "wb") as out:
                    out.write(f.read())
                counts[subdir] += 1
                print(f"    [OK] {subdir}/{filename}")

    print(f"\n  Summary: {counts['csv']} CSV, {counts['html']} HTML, {counts['embeddings']} embedding files downloaded")
    return counts


def setup_neo4j_secrets(scope_name: str, neo4j_url: str, neo4j_username: str, neo4j_password: str, volume_path: str) -> bool:
    """Create Databricks secret scope and store Neo4j credentials.

    Uses the Databricks SDK WorkspaceClient to manage secrets, since
    dbutils.secrets only supports reading secrets, not writing them.

    Args:
        scope_name: Name of the secret scope to create.
        neo4j_url: Neo4j connection URI.
        neo4j_username: Neo4j username.
        neo4j_password: Neo4j password.
        volume_path: Volume path to store as a secret.

    Returns:
        True if all secrets were stored successfully.
    """
    from databricks.sdk import WorkspaceClient

    print("\n" + "=" * 70)
    print("STEP 3: Configuring Neo4j Secrets")
    print("=" * 70)

    w = WorkspaceClient()

    # Create scope
    print(f"\n  Creating secret scope: {scope_name}")
    try:
        w.secrets.create_scope(scope=scope_name)
        print(f"  [OK] Scope '{scope_name}' created")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"  [OK] Scope '{scope_name}' already exists")
        else:
            print(f"  [FAIL] Could not create scope: {e}")
            raise

    # Store secrets
    secrets_to_store = {
        "url": neo4j_url,
        "username": neo4j_username,
        "password": neo4j_password,
        "volume_path": volume_path,
    }

    for key, value in secrets_to_store.items():
        print(f"  Storing secret: {key}")
        try:
            w.secrets.put_secret(scope=scope_name, key=key, string_value=value)
            print(f"  [OK] {key} stored")
        except Exception as e:
            print(f"  [FAIL] Could not store {key}: {e}")
            raise

    return True


def verify_neo4j_connection(neo4j_url: str, neo4j_username: str, neo4j_password: str) -> bool:
    """Verify that Neo4j is reachable.

    Uses the Neo4j Python driver to test connectivity.
    """
    print("\n" + "=" * 70)
    print("STEP 4: Verifying Neo4j Connection")
    print("=" * 70)

    try:
        from neo4j import GraphDatabase

        print(f"\n  Connecting to: {neo4j_url}")
        driver = GraphDatabase.driver(neo4j_url, auth=(neo4j_username, neo4j_password))

        with driver.session(database="neo4j") as session:
            result = session.run("RETURN 'Connected' AS status")
            record = result.single()
            print(f"  [OK] Neo4j responded: {record['status']}")

        driver.close()
        return True

    except Exception as e:
        print(f"  [FAIL] Could not connect to Neo4j: {e}")
        print("\n  Check that:")
        print("    - The Neo4j URI is correct (should start with neo4j+s:// for Aura)")
        print("    - The username and password are correct")
        print("    - The Neo4j instance is running")
        return False


def print_summary(info: dict):
    """Print a summary of the setup results."""
    print("\n" + "=" * 70)
    print("SETUP COMPLETE")
    print("=" * 70)
    print(f"""
  Catalog:     {info['catalog']}
  Schema:      {info['schema']}
  Volume:      {info['volume']}
  Volume Path: {info['volume_path']}
  Neo4j URL:   {info['neo4j_url']}
  Scope:       {info['scope_name']}

  Data files copied:
    CSV:        {info['file_counts']['csv']}
    HTML:       {info['file_counts']['html']}
    Embeddings: {info['file_counts']['embeddings']}

  Neo4j connection: {'OK' if info['neo4j_connected'] else 'FAILED'}
""")
    print("=" * 70)

    if info["neo4j_connected"]:
        print("\n  You are ready to proceed to '1 - Neo4j Import'.")
    else:
        print("\n  Fix the Neo4j connection before proceeding.")
