"""Runner for the augmentation_agent wheel on Databricks.

This thin wrapper exists because spark_python_task requires a python_file
path — it cannot invoke ``python -m augmentation_agent`` directly.

The augmentation_agent wheel must be attached as a task library in the
job JSON (cli.submit handles this automatically).
"""

import os
import sys

# Parse KEY=VALUE parameters from cli.submit into environment variables.
# databricks_job_runner is not available on the cluster, so we inline the logic.
for _arg in sys.argv[1:]:
    if "=" in _arg and not _arg.startswith("-"):
        _key, _, _value = _arg.partition("=")
        os.environ.setdefault(_key, _value)

from augmentation_agent.__main__ import main

if __name__ == "__main__":
    main()
