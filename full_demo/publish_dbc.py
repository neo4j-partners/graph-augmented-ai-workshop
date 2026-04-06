#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["boto3"]
# ///
"""
Build the labs .dbc archive and publish it to S3.

Creates the S3 bucket if it doesn't exist, uploads the .dbc file as a
publicly readable object, and prints the URL for Databricks "Import from URL".

Usage:
    uv run publish_dbc.py          # build + upload
    uv run publish_dbc.py --build  # build only, skip upload

Requires configured AWS credentials (env vars, ~/.aws/credentials, or SSO).
"""

import argparse
import json
import os
import shutil
import tempfile
import zipfile

import boto3
from botocore.exceptions import ClientError

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

LABS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "labs")
BUCKET_NAME = "neo4jgraphenrichment"
S3_KEY = "labs.dbc"
REGION = "us-east-1"

LANG_MAP = {
    ".py": "PYTHON",
    ".sql": "SQL",
    ".scala": "SCALA",
    ".r": "R",
}

# ---------------------------------------------------------------------------
# DBC build (inlined so this script is fully standalone)
# ---------------------------------------------------------------------------


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
            zf.writestr(nb["path"], entry)

    print(f"Built {output_path}")
    print(f"  {len(notebooks)} notebooks:")
    for nb in notebooks:
        print(f"    {nb['path']} ({nb['language']})")


# ---------------------------------------------------------------------------
# S3
# ---------------------------------------------------------------------------


def ensure_bucket(s3, bucket: str, region: str):
    """Create the S3 bucket if it doesn't exist, with a public-read bucket policy."""
    try:
        s3.head_bucket(Bucket=bucket)
        print(f"  Bucket '{bucket}' exists")
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            print(f"  Creating bucket '{bucket}' in {region}...")
            if region == "us-east-1":
                s3.create_bucket(Bucket=bucket)
            else:
                s3.create_bucket(
                    Bucket=bucket,
                    CreateBucketConfiguration={"LocationConstraint": region},
                )
            print("  [OK] Bucket created")
        else:
            raise

    # Allow public bucket policies (required for public-read)
    s3.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": False,
            "RestrictPublicBuckets": False,
        },
    )

    # Set bucket policy for public read on all objects
    policy = json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket}/*",
            }
        ],
    })
    s3.put_bucket_policy(Bucket=bucket, Policy=policy)
    print("  [OK] Public-read bucket policy applied")


def upload(s3, bucket: str, key: str, filepath: str) -> str:
    """Upload file to S3 and return the public URL."""
    print(f"  Uploading {os.path.basename(filepath)} to s3://{bucket}/{key}...")
    s3.upload_file(
        filepath,
        bucket,
        key,
        ExtraArgs={"ContentType": "application/octet-stream"},
    )
    url = f"https://{bucket}.s3.amazonaws.com/{key}"
    print("  [OK] Uploaded")
    return url


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Build and publish labs.dbc to S3")
    parser.add_argument("--build", action="store_true", help="Build only, skip S3 upload")
    parser.add_argument("--bucket", default=BUCKET_NAME, help=f"S3 bucket name (default: {BUCKET_NAME})")
    parser.add_argument("--region", default=REGION, help=f"AWS region (default: {REGION})")
    args = parser.parse_args()

    with tempfile.NamedTemporaryFile(suffix=".dbc", delete=False) as tmp:
        dbc_path = tmp.name

    try:
        print("=" * 50)
        print("BUILDING DBC")
        print("=" * 50)
        build_dbc(LABS_DIR, dbc_path)

        if args.build:
            local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "labs.dbc")
            shutil.copy2(dbc_path, local_path)
            print(f"\n  Saved to {local_path}")
            return

        print("\n" + "=" * 50)
        print("PUBLISHING TO S3")
        print("=" * 50)
        s3 = boto3.client("s3", region_name=args.region)
        ensure_bucket(s3, args.bucket, args.region)
        url = upload(s3, args.bucket, S3_KEY, dbc_path)

        print("\n" + "=" * 50)
        print("DONE")
        print("=" * 50)
        print(f"\n  Import URL for participants:")
        print(f"  {url}")
        print("\n  Databricks: Workspace > Import > URL > paste the link above")

    finally:
        os.unlink(dbc_path)


if __name__ == "__main__":
    main()
