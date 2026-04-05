"""Runner for the augmentation_agent wheel on Databricks.

This thin wrapper exists because spark_python_task requires a python_file
path — it cannot invoke ``python -m augmentation_agent`` directly.

The augmentation_agent wheel must be attached as a task library in the
job JSON (cli.submit handles this automatically).
"""

from augmentation_agent.__main__ import main

if __name__ == "__main__":
    main()
