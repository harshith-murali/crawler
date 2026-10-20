import logging
import os
import time
import uuid
from pathlib import Path

import boto3

from .config import load_settings
from .crawler import run
from .http import Fetcher


def handler(event, context):
    """Invocation payload cannot override scope, providers or output paths."""
    logging.getLogger().setLevel(logging.INFO)
    settings = load_settings()
    run_id = uuid.uuid4().hex
    settings.output_file = f"/tmp/{run_id}/agent_inventory.csv"
    seconds = min(settings.max_runtime_seconds, context.get_remaining_time_in_millis() / 1000 - 30)
    if seconds <= 0:
        raise RuntimeError("insufficient Lambda runtime remaining")
    fetcher = Fetcher(settings, deadline=time.monotonic() + seconds)
    try:
        _, summary = run(settings, fetcher=fetcher)
    finally:
        fetcher.close()
    bucket = os.environ["RESULTS_BUCKET"]
    prefix = f"runs/{run_id}"
    client = boto3.client("s3")
    try:
        for path, mime in [
            (Path(settings.output_file), "text/csv; charset=utf-8"),
            (Path(settings.output_file).with_suffix(".summary.json"), "application/json"),
        ]:
            client.upload_file(
                str(path),
                bucket,
                f"{prefix}/{path.name}",
                ExtraArgs={"ContentType": mime, "ServerSideEncryption": "AES256"},
            )
    finally:
        for path in Path(settings.output_file).parent.iterdir():
            path.unlink()
        Path(settings.output_file).parent.rmdir()
    return {"bucket": bucket, "csv_key": f"{prefix}/agent_inventory.csv", "summary": summary}
