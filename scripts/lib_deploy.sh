#!/usr/bin/env bash
# Shared helpers for deployment scripts. Intended to be sourced, not executed directly.
# shellcheck shell=bash

# Wait until the backend listens on 127.0.0.1:8001 and responds on /health.
# Override with LOCAL_HEALTH_RETRIES / LOCAL_HEALTH_INTERVAL_SECONDS.
wait_for_local_backend_health() {
  local attempt
  local retries="${LOCAL_HEALTH_RETRIES:-45}"
  local interval="${LOCAL_HEALTH_INTERVAL_SECONDS:-2}"
  for ((attempt = 1; attempt <= retries; attempt++)); do
    if curl -fsS http://127.0.0.1:8001/health >/dev/null 2>&1; then
      return 0
    fi
    sleep "${interval}"
  done
  echo "Local backend health check failed after ${retries} attempts (${interval}s interval)." >&2
  echo "Tip: increase LOCAL_HEALTH_RETRIES / LOCAL_HEALTH_INTERVAL_SECONDS and retry." >&2
  return 1
}
