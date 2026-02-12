"""AWS resource configuration.

Provides ARN patterns and resource identifiers for AWS deployments.
"""
from __future__ import annotations

import os


AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCOUNT_ID = os.getenv("AWS_ACCOUNT_ID", "")

# SQS queue URLs (populated in deployed environments)
SQS_TASK_QUEUE_URL = os.getenv("SQS_TASK_QUEUE_URL", "")
SQS_EVENT_QUEUE_URL = os.getenv("SQS_EVENT_QUEUE_URL", "")

# S3 buckets
S3_DATA_BUCKET = os.getenv("S3_DATA_BUCKET", "iprs-data")
S3_REPORTS_BUCKET = os.getenv("S3_REPORTS_BUCKET", "iprs-reports")
S3_ML_MODELS_BUCKET = os.getenv("S3_ML_MODELS_BUCKET", "iprs-ml-models")

# Secrets Manager
DB_SECRET_ARN = os.getenv("DB_SECRET_ARN", "")
