"""CLI for the graph-enrichment solutions.

Thin wrapper around databricks-job-runner configured for this project.
All .env extras are automatically passed to submitted jobs as KEY=VALUE
parameters. Scripts use pydantic Settings to read them.
"""

from databricks_job_runner import Runner

runner = Runner(
    run_name_prefix="graph_validation",
)
