"""CLI for the graph-enrichment solutions.

Thin wrapper around databricks-job-runner configured for this project.
"""

from databricks_job_runner import Runner, RunnerConfig


def build_params(config: RunnerConfig, script: str) -> list[str]:
    """Inject per-script parameters from .env config."""
    params: list[str] = []
    extras = config.extras

    if script == "generate_embeddings.py":
        if config.databricks_volume_path:
            params += ["--volume-path", config.databricks_volume_path]
            params += [
                "--output-path",
                config.databricks_volume_path
                + "/embeddings/document_chunks_embedded.json",
            ]
        endpoint = extras.get("EMBEDDING_ENDPOINT")
        if endpoint:
            params += ["--endpoint", endpoint]
        return params

    # Lab scripts — Neo4j creds + volume + supervisor
    if extras.get("NEO4J_URI") and extras.get("NEO4J_PASSWORD"):
        params += [
            "--neo4j-uri", extras["NEO4J_URI"],
            "--neo4j-username", extras.get("NEO4J_USERNAME", "neo4j"),
            "--neo4j-password", extras["NEO4J_PASSWORD"],
        ]
    if config.databricks_volume_path:
        params += ["--volume-path", config.databricks_volume_path]
    if extras.get("SUPERVISOR_AGENT_ENDPOINT"):
        params += ["--supervisor-endpoint", extras["SUPERVISOR_AGENT_ENDPOINT"]]
    return params


runner = Runner(
    run_name_prefix="graph_validation",
    build_params=build_params,
    wheel_package="augmentation_agent",
)
