#!/bin/sh
set -e

export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

ENDPOINT="${AWS_ENDPOINT_URL:-http://localhost:4566}"
BUCKET="${SEED_BUCKET:-locadev-demo}"

echo "Seeding S3 bucket s3://${BUCKET} at ${ENDPOINT}"

# MiniStack / LocalStack-compatible aws cli if present; else use awslocal-style curl fallbacks
if command -v awslocal >/dev/null 2>&1; then
  AWS="awslocal"
elif command -v aws >/dev/null 2>&1; then
  AWS="aws --endpoint-url=${ENDPOINT}"
else
  echo "No aws/awslocal CLI; skipping seed (gateway may still be up)"
  exit 0
fi

$AWS s3 mb "s3://${BUCKET}" 2>/dev/null || true

echo "demo seed readme" | $AWS s3 cp - "s3://${BUCKET}/demo/acme/project-001/readme.txt"
echo "demo seed notes" | $AWS s3 cp - "s3://${BUCKET}/demo/acme/project-001/notes.txt"
echo "demo seed report" | $AWS s3 cp - "s3://${BUCKET}/demo/globex/project-002/report.txt"

$AWS s3 ls "s3://${BUCKET}" --recursive
echo "S3 seed complete."
