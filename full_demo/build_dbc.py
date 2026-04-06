#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# ///
"""
Build a .dbc archive from the labs/ directory.

A .dbc file is a ZIP archive containing Databricks notebooks. Each notebook
is stored as a JSON entry with its source code, language, and relative path.

Usage:
    uv run build_dbc.py                    # outputs labs.dbc
    uv run build_dbc.py -o my_workshop.dbc # custom output name
"""

import argparse
import json
import os
import zipfile

LABS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "labs")

# Map file extensions to Databricks language identifiers
LANG_MAP = {
    ".py": "PYTHON",
    ".sql": "SQL",
    ".scala": "SCALA",
    ".r": "R",
}


def build_dbc(labs_dir: str, output_path: str):
    """Package all notebook files into a .dbc archive."""
    notebooks = []

    for root, _dirs, files in os.walk(labs_dir):
        for filename in sorted(files):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in LANG_MAP:
                continue

            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, labs_dir)

            # Remove the file extension for the notebook path
            notebook_path = os.path.splitext(rel_path)[0]

            with open(filepath, "r") as f:
                source = f.read()

            notebooks.append({
                "path": notebook_path,
                "language": LANG_MAP[ext],
                "source": source,
            })

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for nb in notebooks:
            entry_path = nb["path"]
            entry = json.dumps({
                "version": "NotebookV1",
                "origId": 0,
                "name": os.path.basename(nb["path"]),
                "language": nb["language"],
                "commands": [
                    {
                        "version": "CommandV1",
                        "origId": 0,
                        "guid": "",
                        "subtype": "command",
                        "commandType": "auto",
                        "position": 1.0,
                        "command": nb["source"],
                    }
                ],
            })
            zf.writestr(entry_path, entry)

    print(f"Built {output_path}")
    print(f"  {len(notebooks)} notebooks:")
    for nb in notebooks:
        print(f"    {nb['path']} ({nb['language']})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build a .dbc archive from labs/")
    parser.add_argument("-o", "--output", default="labs.dbc", help="Output .dbc filename")
    args = parser.parse_args()
    build_dbc(LABS_DIR, args.output)
