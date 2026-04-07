#!/usr/bin/env python3
"""
Convert Databricks notebook source (.py) files and plain Python files to Jupyter (.ipynb) format.

Usage:
    # Convert a Databricks notebook source file
    python convert_py_to_ipynb.py labs/my_notebook.py

    # Convert a plain Python file (no # Databricks notebook source header)
    python convert_py_to_ipynb.py --plain libs/my_module.py

    # Convert multiple files
    python convert_py_to_ipynb.py file1.py file2.py --plain lib1.py lib2.py

    # Specify output directory
    python convert_py_to_ipynb.py -o output/ labs/my_notebook.py

Output .ipynb files are written alongside the source files (same directory, .ipynb extension)
unless -o/--output-dir is specified.
"""

import argparse
import json
import os
import re
import sys


def make_cell(cell_type, source):
    """Create a notebook cell."""
    cell = {
        "cell_type": cell_type,
        "metadata": {},
        "source": source,
    }
    if cell_type == "code":
        cell["execution_count"] = None
        cell["outputs"] = []
    return cell


def convert_databricks_py(filepath):
    """Convert a Databricks notebook source .py file to ipynb cells.

    Handles:
    - # MAGIC %md / %md-sandbox -> markdown cells
    - # MAGIC %run -> code cells with %run
    - # MAGIC %pip -> code cells with %pip
    - Regular code -> code cells
    - Cell boundaries: # COMMAND ----------
    """
    with open(filepath) as f:
        content = f.read()

    lines = content.split("\n")

    # Strip first line (# Databricks notebook source)
    if lines and lines[0].strip() == "# Databricks notebook source":
        lines = lines[1:]

    # Split into raw cells by # COMMAND ----------
    raw_cells = []
    current = []
    for line in lines:
        if line.strip() == "# COMMAND ----------":
            raw_cells.append(current)
            current = []
        else:
            current.append(line)
    raw_cells.append(current)

    cells = []
    for raw in raw_cells:
        # Strip leading/trailing blank lines
        while raw and raw[0].strip() == "":
            raw = raw[1:]
        while raw and raw[-1].strip() == "":
            raw = raw[:-1]

        if not raw:
            continue

        # Check if all non-blank lines are MAGIC
        non_blank = [l for l in raw if l.strip()]
        all_magic = all(l.startswith("# MAGIC") for l in non_blank)

        if all_magic:
            # Strip "# MAGIC " or "# MAGIC" prefix from all lines
            stripped = []
            for l in raw:
                if l.startswith("# MAGIC "):
                    stripped.append(l[8:])  # len("# MAGIC ") == 8
                elif l.strip() == "# MAGIC":
                    stripped.append("")
                else:
                    stripped.append(l)

            # Check if it's a %md cell
            if stripped and (
                stripped[0].strip().startswith("%md")
                or stripped[0].strip() == "%md"
            ):
                # Remove the %md or %md-sandbox line
                first = stripped[0].strip()
                if first == "%md" or first == "%md-sandbox":
                    stripped = stripped[1:]
                elif first.startswith("%md "):
                    stripped[0] = stripped[0].replace("%md ", "", 1)
                elif first.startswith("%md-sandbox"):
                    stripped[0] = stripped[0].replace("%md-sandbox", "", 1)

                # Strip leading blank lines after removing %md
                while stripped and stripped[0].strip() == "":
                    stripped = stripped[1:]

                source = [l + "\n" for l in stripped]
                if source:
                    source[-1] = source[-1].rstrip("\n")
                cells.append(make_cell("markdown", source))

            elif stripped and stripped[0].strip().startswith("%run"):
                # %run is a code cell
                source = [stripped[0]]
                cells.append(make_cell("code", source))

            elif stripped and stripped[0].strip().startswith("%pip"):
                # %pip is a code cell
                source = [l + "\n" for l in stripped]
                if source:
                    source[-1] = source[-1].rstrip("\n")
                cells.append(make_cell("code", source))

            else:
                # Other magic - treat as code
                source = [l + "\n" for l in stripped]
                if source:
                    source[-1] = source[-1].rstrip("\n")
                cells.append(make_cell("code", source))
        else:
            # Regular code cell
            source = [l + "\n" for l in raw]
            if source:
                source[-1] = source[-1].rstrip("\n")
            cells.append(make_cell("code", source))

    return cells


def convert_plain_python(filepath):
    """Convert a plain Python file into notebook cells.

    Splits on section separator comments (# === ... ===) if present,
    otherwise creates a single code cell.
    """
    with open(filepath) as f:
        content = f.read()

    # Split into logical sections based on separator comments
    sections = re.split(r"\n# =+\n# .+\n# =+\n", content)
    headers = re.findall(r"\n# =+\n# (.+)\n# =+\n", content)

    cells = []

    for section in sections:
        section = section.strip()
        if not section:
            continue
        source = [l + "\n" for l in section.split("\n")]
        if source:
            source[-1] = source[-1].rstrip("\n")
        cells.append(make_cell("code", source))

    return cells


def make_notebook(cells):
    """Create a complete notebook structure."""
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.11.0",
            },
        },
        "cells": cells,
    }


def write_notebook(cells, output_path):
    """Write cells as a .ipynb file."""
    nb = make_notebook(cells)
    with open(output_path, "w") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"  [OK] {output_path} ({len(cells)} cells)")


def is_databricks_notebook(filepath):
    """Check if a file is a Databricks notebook source file."""
    with open(filepath) as f:
        first_line = f.readline().strip()
    return first_line == "# Databricks notebook source"


def main():
    parser = argparse.ArgumentParser(
        description="Convert Databricks .py notebooks and plain Python files to .ipynb"
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Databricks notebook source .py files to convert (auto-detected)",
    )
    parser.add_argument(
        "--plain",
        nargs="*",
        default=[],
        help="Plain Python files to convert (no Databricks header)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        help="Output directory (default: same directory as source)",
    )
    args = parser.parse_args()

    if not args.files and not args.plain:
        parser.print_help()
        sys.exit(1)

    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)

    # Auto-detect: files without --plain flag are checked for Databricks header
    db_files = []
    plain_files = list(args.plain) if args.plain else []

    for f in args.files:
        if is_databricks_notebook(f):
            db_files.append(f)
        else:
            print(f"  [INFO] {f} has no Databricks header, treating as plain Python")
            plain_files.append(f)

    if db_files:
        print("Converting Databricks notebook source files:")
        for src in db_files:
            cells = convert_databricks_py(src)
            if args.output_dir:
                dst = os.path.join(
                    args.output_dir,
                    os.path.splitext(os.path.basename(src))[0] + ".ipynb",
                )
            else:
                dst = os.path.splitext(src)[0] + ".ipynb"
            write_notebook(cells, dst)

    if plain_files:
        print("Converting plain Python files:")
        for src in plain_files:
            cells = convert_plain_python(src)
            if args.output_dir:
                dst = os.path.join(
                    args.output_dir,
                    os.path.splitext(os.path.basename(src))[0] + ".ipynb",
                )
            else:
                dst = os.path.splitext(src)[0] + ".ipynb"
            write_notebook(cells, dst)

    print("\nDone!")


if __name__ == "__main__":
    main()
