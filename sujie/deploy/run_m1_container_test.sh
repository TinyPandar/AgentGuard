#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
compose_file="$project_dir/deploy/m1.compose.yaml"

cleanup() {
  docker compose -f "$compose_file" down --remove-orphans
}
trap cleanup EXIT INT TERM

docker compose -f "$compose_file" build
docker compose -f "$compose_file" up -d --wait receiver gateway
docker compose -f "$compose_file" run --rm agent
docker compose -f "$compose_file" run --rm oracle
