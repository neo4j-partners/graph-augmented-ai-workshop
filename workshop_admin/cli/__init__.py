"""CLI for workshop_admin embedding pre-computation.

Thin wrapper around databricks-job-runner configured for this project.
"""

from databricks_job_runner import Runner, RunnerConfig


def build_params(config: RunnerConfig, script: str) -> list[str]:
    """Inject volume path and embedding endpoint into generate_embeddings.py."""
    params: list[str] = []

    if config.databricks_volume_path:
        params += ["--volume-path", config.databricks_volume_path]
        params += [
            "--output-path",
            config.databricks_volume_path
            + "/embeddings/document_chunks_embedded.json",
        ]

    endpoint = config.extras.get("EMBEDDING_ENDPOINT")
    if endpoint:
        params += ["--endpoint", endpoint]

    return params


runner = Runner(
    run_name_prefix="workshop_admin",
    build_params=build_params,
)
