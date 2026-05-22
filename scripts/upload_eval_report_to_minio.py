import os
from datetime import datetime, timezone
from pathlib import Path

from minio import Minio
from minio.error import S3Error

REPORT_PATH = Path("eval_report.json")


def main() -> None:
    print("Starting MinIO upload...")

    if not REPORT_PATH.exists():
        raise FileNotFoundError(
            "eval_report.json not found. Run `python evals/run_rag_eval.py` first."
        )

    endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    access_key = os.getenv("MINIO_ROOT_USER", "minioadmin")
    secret_key = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
    bucket = os.getenv("MINIO_BUCKET", "maintainers-copilot")

    print(f"Endpoint: {endpoint}")
    print(f"Bucket: {bucket}")
    print(f"Report exists: {REPORT_PATH.exists()}")

    client = Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=False,
    )

    if not client.bucket_exists(bucket):
        print(f"Bucket {bucket} does not exist. Creating it...")
        client.make_bucket(bucket)
    else:
        print(f"Bucket {bucket} already exists.")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    object_name = f"evals/eval_report_{timestamp}.json"

    client.fput_object(
        bucket_name=bucket,
        object_name=object_name,
        file_path=str(REPORT_PATH),
        content_type="application/json",
    )

    print(f"Uploaded {REPORT_PATH} to minio://{bucket}/{object_name}")


if __name__ == "__main__":
    try:
        main()
    except S3Error as exc:
        raise SystemExit(f"MinIO upload failed: {exc}") from exc