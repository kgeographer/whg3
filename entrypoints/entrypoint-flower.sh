#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

# Ensure required environment variables are set
: "${CELERY_BROKER_URL:?Environment variable CELERY_BROKER_URL is not set}"
: "${FLOWER_BASIC_AUTH:?Environment variable FLOWER_BASIC_AUTH is not set}"

# Ensure Redis is available
echo "Waiting for Redis at ${REDIS_HOST}:${REDIS_PORT} to be ready..."
until nc -z "${REDIS_HOST}" "${REDIS_PORT}"; do
  echo "Redis not available yet" >&2
  sleep 1
done
echo "Redis is available" >&2

echo "Waiting for Celery workers to be available..."
until celery -A whg inspect ping; do
  echo "Celery workers not available" >&2
  sleep 1
done

echo "Celery workers are available" >&2

# Start Flower
exec celery -A whg --broker="${CELERY_BROKER_URL}" flower #--basic_auth="${FLOWER_BASIC_AUTH}"

