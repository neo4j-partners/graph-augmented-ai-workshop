"""CLI for the graph-augmented-ai-workshop solutions.

Thin wrapper around databricks-job-runner configured for this project.
"""

from databricks_job_runner import Runner


def build_params(env: dict[str, str]) -> list[str]:
    """Inject Neo4j credentials and workshop-specific settings."""
    params: list[str] = []
    if env.get("NEO4J_URI") and env.get("NEO4J_PASSWORD"):
        params += [
            "--neo4j-uri", env["NEO4J_URI"],
            "--neo4j-username", env.get("NEO4J_USERNAME", "neo4j"),
            "--neo4j-password", env["NEO4J_PASSWORD"],
        ]
    if env.get("VOLUME_PATH"):
        params += ["--volume-path", env["VOLUME_PATH"]]
    if env.get("MAS_ENDPOINT_NAME"):
        params += ["--mas-endpoint", env["MAS_ENDPOINT_NAME"]]
    return params


runner = Runner(
    run_name_prefix="graph_validation",
    build_params=build_params,
    wheel_package="augmentation_agent",
)
